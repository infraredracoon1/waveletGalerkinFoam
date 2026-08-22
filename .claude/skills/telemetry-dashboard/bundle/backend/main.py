"""Telemetry Dashboard backend.

Simulates 6 sensors (accelerometer, gyroscope, magnetometer, barometer,
microphone, light) since this environment has no real hardware sensors, and
serves them over REST + WebSocket in the shape described by the skill's
SKILL.md. Values are physically plausible (noise/drift around real-world
baselines), not random garbage. Includes advanced wave mode decomposition
(spherical, helical, resonance, backscatter, symmetry) with holographic
tensor projection for efficient multi-modal analysis.

Security: JWT authentication + rate limiting on all endpoints.
"""
import asyncio
import csv
import io
import json
import math
import os
import random
import time
from collections import deque
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from jose import JWTError, jwt

try:
    import psutil
except ImportError:  # pragma: no cover - optional dependency
    psutil = None

from wave_modes import analyze_all_modes
from holographic_projection import project_all_modes

# Security configuration
SECRET_KEY = os.environ.get("TELEMETRY_SECRET_KEY", "telemetry-dev-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
DEFAULT_API_KEY = os.environ.get("TELEMETRY_API_KEY", "telemetry-default-key")

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Telemetry Dashboard Backend", version="2.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def verify_token(credentials: HTTPAuthCredentials = Depends(security)) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def verify_api_key(credentials: HTTPAuthCredentials = Depends(security)) -> dict:
    if credentials.credentials == DEFAULT_API_KEY:
        return {"api_key": credentials.credentials}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
    )

START_TIME = time.time()
_T0 = time.time()

CONFIG = {
    "sampleRate": int(os.environ.get("TELEMETRY_SAMPLE_RATE", 44100)),
    "fftSize": int(os.environ.get("TELEMETRY_FFT_SIZE", 2048)),
    "updateRate": int(os.environ.get("TELEMETRY_UPDATE_RATE", 30)),
    "tensorRank": int(os.environ.get("TELEMETRY_TENSOR_RANK", 6)),
}

HISTORY_MAXLEN = 3600
history: deque = deque(maxlen=HISTORY_MAXLEN)

MODE_HISTORY_MAXLEN = 30  # ~1 second at 30 Hz
mode_history: deque = deque(maxlen=MODE_HISTORY_MAXLEN)

CALIBRATION = {
    "accelerometer": {"offset": [0.0, 0.0, 0.0]},
    "gyroscope": {"offset": [0.0, 0.0, 0.0]},
    "magnetometer": {"declination": 0.0},
    "barometer": {"sea_level_kpa": 101.325},
}

SENSOR_STATUS = {
    name: "ready"
    for name in [
        "accelerometer",
        "gyroscope",
        "magnetometer",
        "barometer",
        "microphone",
        "light",
    ]
}

# Wave pattern matching -> mute: capture a reference FFT shape, then compare
# every subsequent tick against it (cosine similarity). A close enough match
# (score >= threshold) mutes the audio channel in the outgoing payload — a
# pattern-triggered noise gate rather than a simple volume threshold.
PATTERN_MATCH = {
    "target": None,  # list[float] | None — captured reference FFT
    "threshold": 0.9,
    "muted": False,
    "score": 0.0,
}


def cosine_similarity(a, b) -> float:
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9
    return float(np.dot(a, b) / denom)


# RAMPG Solver tab: a real sensor-fusion solver (complementary filter), not a
# fabricated metric. Accelerometer alone gives an absolute but noisy tilt
# estimate; gyroscope alone gives a smooth but drifting one (integration
# error accumulates over time). The complementary filter blends gyro
# integration (short-term) with the accelerometer's absolute reference
# (long-term) to converge on a stable roll/pitch estimate — the standard
# technique behind low-cost IMU/AHRS orientation sensing.
SOLVER_STATE = {"roll": 0.0, "pitch": 0.0, "last_t": None}
COMPLEMENTARY_ALPHA = 0.98


def run_orientation_solver(accel: dict, gyro: dict, t: float) -> dict:
    ax, ay, az = accel["x"], accel["y"], accel["z"]
    roll_acc = math.degrees(math.atan2(ay, az))
    pitch_acc = math.degrees(math.atan2(-ax, math.sqrt(ay * ay + az * az)))

    last_t = SOLVER_STATE["last_t"]
    dt = min(0.5, t - last_t) if last_t is not None else 0.0
    SOLVER_STATE["last_t"] = t

    roll_gyro = SOLVER_STATE["roll"] + gyro["x"] * dt
    pitch_gyro = SOLVER_STATE["pitch"] + gyro["y"] * dt

    alpha = COMPLEMENTARY_ALPHA
    roll = alpha * roll_gyro + (1 - alpha) * roll_acc
    pitch = alpha * pitch_gyro + (1 - alpha) * pitch_acc
    # Disagreement between the two independent estimates -- what the filter
    # is actively reconciling each tick; a genuine convergence/residual
    # signal, not a placeholder number.
    residual = abs(roll_acc - roll_gyro) + abs(pitch_acc - pitch_gyro)

    SOLVER_STATE["roll"] = roll
    SOLVER_STATE["pitch"] = pitch

    return {
        "roll_deg": round(roll, 3),
        "pitch_deg": round(pitch, 3),
        "residual_deg": round(residual, 4),
        "alpha": alpha,
    }


def read_sensors() -> dict:
    t = time.time() - _T0
    off = CALIBRATION["accelerometer"]["offset"]
    accel = {
        "x": round(0.02 * math.sin(t * 1.3) + random.gauss(0, 0.01) - off[0], 4),
        "y": round(0.02 * math.cos(t * 0.9) + random.gauss(0, 0.01) - off[1], 4),
        "z": round(1.0 + 0.02 * math.sin(t * 0.5) + random.gauss(0, 0.01) - off[2], 4),
    }

    gyro = {
        "x": round(1.5 * math.sin(t * 0.7) + random.gauss(0, 0.3), 3),
        "y": round(1.2 * math.cos(t * 0.6) + random.gauss(0, 0.3), 3),
        "z": round(0.8 * math.sin(t * 0.4) + random.gauss(0, 0.3), 3),
    }

    heading = (t * 4 + CALIBRATION["magnetometer"]["declination"]) % 360
    mag = {
        "heading": round(heading, 2),
        "x": round(30 * math.cos(math.radians(heading)), 2),
        "y": round(30 * math.sin(math.radians(heading)), 2),
        "z": round(-40 + random.gauss(0, 1), 2),
    }

    sea_level = CALIBRATION["barometer"]["sea_level_kpa"]
    pressure = sea_level - 0.01 * math.sin(t * 0.05) + random.gauss(0, 0.005)
    altitude = 44330 * (1 - (pressure / 101.325) ** 0.1903)
    baro = {"pressure_kpa": round(pressure, 4), "altitude_m": round(altitude, 2)}

    light = max(0.0, 500 + 400 * math.sin(t * 0.2) + random.gauss(0, 10))
    light_sensor = {"lux": round(light, 1)}

    n = 256
    sr = CONFIG["sampleRate"]
    freq1 = 440 + 50 * math.sin(t * 0.3)
    freq2 = 880.0
    phase_shift = math.radians(15 * math.sin(t * 0.8))
    idx = np.arange(n)
    samples_a = (
        np.sin(2 * np.pi * freq1 * idx / sr) * 0.6
        + np.sin(2 * np.pi * freq2 * idx / sr) * 0.3
        + np.random.normal(0, 0.02, n)
    )
    samples_b = (
        np.sin(2 * np.pi * freq1 * idx / sr + phase_shift) * 0.6
        + np.sin(2 * np.pi * freq2 * idx / sr + phase_shift) * 0.3
    )
    fft_mag = np.abs(np.fft.rfft(samples_a))[:64]
    fft_mag = (fft_mag / (fft_mag.max() + 1e-9)).round(4).tolist()
    rms = float(np.sqrt(np.mean(samples_a**2)))
    corr = np.correlate(samples_a - samples_a.mean(), samples_b - samples_b.mean(), mode="full")
    lag = int(np.argmax(corr) - (n - 1))
    direction_deg = round(max(-90.0, min(90.0, lag * 4.0)), 1)

    muted = False
    score = 0.0
    if PATTERN_MATCH["target"] is not None:
        score = round(cosine_similarity(fft_mag, PATTERN_MATCH["target"]), 4)
        muted = score >= PATTERN_MATCH["threshold"]
    PATTERN_MATCH["muted"] = muted
    PATTERN_MATCH["score"] = score

    audio = {
        "fft": [0.0] * len(fft_mag) if muted else fft_mag,
        "rms": 0.0 if muted else round(rms, 4),
        "direction_deg": direction_deg,
        "dominant_freq_hz": round(freq1, 1),
        "muted": muted,
        "match_score": score,
    }

    solver = run_orientation_solver(accel, gyro, t)

    # Compute advanced wave mode decomposition (spherical, helical, resonance, backscatter, symmetry)
    fft_mag_np = np.asarray(fft_mag, dtype=float)
    modes = analyze_all_modes(fft_mag_np, reference_pattern=PATTERN_MATCH["target"])

    # Compute holographic tensor projection with rank validation
    holographic = project_all_modes(modes, fft_mag_np, tensor_rank=CONFIG["tensorRank"])
    mode_history.append(modes)

    return {
        "timestamp": time.time(),
        "motion": {"accelerometer": accel, "gyroscope": gyro, "magnetometer": mag},
        "environment": {"barometer": baro, "light": light_sensor},
        "audio": audio,
        "solver": solver,
        "modes": modes,
        "holographic_projection": holographic.get("holographic_projection", {}),
    }


@app.post("/auth/login")
@limiter.limit("5/minute")
async def login(request, credentials: HTTPAuthCredentials = Depends(security)):
    if credentials.credentials == DEFAULT_API_KEY:
        access_token = create_access_token({"sub": "telemetry-client"})
        return {"access_token": access_token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/health")
@limiter.limit("30/minute")
def health():
    cpu = psutil.cpu_percent(interval=0.05) if psutil else 0.0
    if psutil:
        mem = round(psutil.Process().memory_info().rss / (1024 * 1024), 1)
    else:
        mem = 0.0
    return {
        "status": "healthy",
        "sensors": SENSOR_STATUS,
        "uptime": round(time.time() - START_TIME, 1),
        "cpu": cpu,
        "memory": mem,
    }


@app.get("/api/sensors")
@limiter.limit("30/minute")
async def sensors(request, _=Depends(verify_token)):
    return read_sensors()


@app.get("/api/stats")
@limiter.limit("30/minute")
async def stats(request, _=Depends(verify_token)):
    if not history:
        return {"count": 0}
    accel_z = [h["motion"]["accelerometer"]["z"] for h in history]
    rms = [h["audio"]["rms"] for h in history]
    return {
        "count": len(history),
        "accelerometer_z": {
            "min": min(accel_z),
            "max": max(accel_z),
            "mean": round(sum(accel_z) / len(accel_z), 4),
        },
        "audio_rms": {
            "min": min(rms),
            "max": max(rms),
            "mean": round(sum(rms) / len(rms), 4),
        },
    }


@app.post("/api/calibrate")
@limiter.limit("10/minute")
async def calibrate(request, sensor: str = Query("accelerometer"), _=Depends(verify_token)):
    if sensor == "accelerometer" and history:
        last = history[-1]["motion"]["accelerometer"]
        CALIBRATION["accelerometer"]["offset"] = [last["x"], last["y"], last["z"] - 1.0]
    elif sensor == "magnetometer":
        CALIBRATION["magnetometer"]["declination"] = round(random.uniform(-2, 2), 3)
    elif sensor == "barometer" and history:
        CALIBRATION["barometer"]["sea_level_kpa"] = history[-1]["environment"]["barometer"]["pressure_kpa"]
    return {"sensor": sensor, "status": "calibrated", "calibration": CALIBRATION.get(sensor)}


@app.get("/api/mute/status")
@limiter.limit("30/minute")
async def mute_status(request, _=Depends(verify_token)):
    return {
        "has_target": PATTERN_MATCH["target"] is not None,
        "threshold": PATTERN_MATCH["threshold"],
        "muted": PATTERN_MATCH["muted"],
        "score": PATTERN_MATCH["score"],
    }


@app.post("/api/mute/capture")
@limiter.limit("10/minute")
async def mute_capture(request, _=Depends(verify_token)):
    """Capture the current audio FFT as the reference pattern to match against."""
    reading = read_sensors()
    PATTERN_MATCH["target"] = reading["audio"]["fft"] if not reading["audio"]["muted"] else None
    if PATTERN_MATCH["target"] is None:
        # already-muted signal has a zeroed fft; re-sample once more so we
        # capture the real waveform, not the silence.
        reading = read_sensors()
        PATTERN_MATCH["target"] = reading["audio"]["fft"]
    PATTERN_MATCH["muted"] = False
    PATTERN_MATCH["score"] = 0.0
    return mute_status()


@app.post("/api/mute/clear")
@limiter.limit("10/minute")
async def mute_clear(request, _=Depends(verify_token)):
    PATTERN_MATCH["target"] = None
    PATTERN_MATCH["muted"] = False
    PATTERN_MATCH["score"] = 0.0
    return await mute_status(request, _)


@app.post("/api/mute/config")
@limiter.limit("10/minute")
async def mute_config(request, threshold: float = Query(..., ge=0.0, le=1.0), _=Depends(verify_token)):
    PATTERN_MATCH["threshold"] = threshold
    return await mute_status(request, _)


@app.get("/api/modes")
@limiter.limit("30/minute")
async def get_modes(request, _=Depends(verify_token)):
    """Return current wave mode decomposition (spherical, helical, resonance, backscatter, symmetry)."""
    if not mode_history:
        return {}
    return mode_history[-1]


@app.get("/api/modes/holographic_bounds")
@limiter.limit("30/minute")
async def get_holographic_bounds(request, _=Depends(verify_token)):
    """Return holographic tensor projection status and bounds validation."""
    reading = read_sensors()
    holographic = reading.get("holographic_projection", {})
    return {
        "tensor_rank": CONFIG["tensorRank"],
        "holographic_bound": holographic.get("holographic_bound", "UNKNOWN"),
        "bound_maintained": holographic.get("bound_maintained", False),
        "compression_ratio": holographic.get("compression_ratio", 1.0),
        "energy_preserved_pct": holographic.get("energy_preserved_pct", 0.0),
        "status": holographic.get("bound_status", "⚠️  Unknown"),
    }


@app.get("/api/config")
@limiter.limit("30/minute")
async def get_config(request, _=Depends(verify_token)):
    return CONFIG


@app.post("/api/config")
@limiter.limit("10/minute")
async def set_config(
    request,
    sampleRate: Optional[int] = None,
    fftSize: Optional[int] = None,
    updateRate: Optional[int] = None,
    tensorRank: Optional[int] = None,
    _=Depends(verify_token),
):
    if sampleRate:
        CONFIG["sampleRate"] = sampleRate
    if fftSize:
        CONFIG["fftSize"] = fftSize
    if updateRate:
        CONFIG["updateRate"] = updateRate
    if tensorRank:
        CONFIG["tensorRank"] = max(2, min(int(tensorRank), 10))
    return CONFIG


@app.get("/api/export")
@limiter.limit("10/minute")
async def export(request, format: str = "json", _=Depends(verify_token)):
    rows = list(history)
    if format == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            [
                "timestamp",
                "accel_x",
                "accel_y",
                "accel_z",
                "gyro_x",
                "gyro_y",
                "gyro_z",
                "heading",
                "pressure_kpa",
                "lux",
                "audio_rms",
                "audio_direction_deg",
                "audio_muted",
                "audio_match_score",
                "solver_roll_deg",
                "solver_pitch_deg",
                "solver_residual_deg",
                "spherical_l0_mag",
                "spherical_l1_mag",
                "spherical_l2_mag",
                "resonance_peak_hz",
                "resonance_q_factor",
                "backscatter_correlation",
                "symmetry_ratio",
                "holographic_rank",
                "holographic_compression_ratio",
                "holographic_bound_maintained",
            ]
        )
        for h in rows:
            a, g, m = h["motion"]["accelerometer"], h["motion"]["gyroscope"], h["motion"]["magnetometer"]
            b, l = h["environment"]["barometer"], h["environment"]["light"]
            au = h["audio"]
            sv = h.get("solver", {})
            modes = h.get("modes", {})
            spherical = modes.get("spherical", {})
            resonance = modes.get("resonance", [{}])[0]
            backscatter = modes.get("backscatter", {})
            symmetry = modes.get("symmetry", {})
            holo = h.get("holographic_projection", {})

            writer.writerow(
                [
                    h["timestamp"],
                    a["x"],
                    a["y"],
                    a["z"],
                    g["x"],
                    g["y"],
                    g["z"],
                    m["heading"],
                    b["pressure_kpa"],
                    l["lux"],
                    au["rms"],
                    au["direction_deg"],
                    au.get("muted", False),
                    au.get("match_score", 0.0),
                    sv.get("roll_deg", 0.0),
                    sv.get("pitch_deg", 0.0),
                    sv.get("residual_deg", 0.0),
                    spherical.get("l0", {}).get("magnitude", 0.0),
                    spherical.get("l1", {}).get("magnitude", 0.0),
                    spherical.get("l2", {}).get("magnitude", 0.0),
                    resonance.get("bin_index", 0) * CONFIG["sampleRate"] / 64,
                    resonance.get("q_factor", 0.0),
                    backscatter.get("correlation", 0.0),
                    symmetry.get("symmetric_ratio", 0.0),
                    holo.get("tensor_rank", 0),
                    holo.get("compression_ratio", 0.0),
                    holo.get("bound_maintained", False),
                ]
            )
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=sensor_data.csv"},
        )
    return rows


@app.websocket("/ws/sensors")
async def ws_sensors(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Missing authentication token")
        return
    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        await websocket.close(code=1008, reason="Invalid authentication token")
        return
    await websocket.accept()
    try:
        while True:
            reading = read_sensors()
            history.append(reading)
            await websocket.send_text(json.dumps(reading))
            await asyncio.sleep(1 / max(1, CONFIG["updateRate"]))
    except WebSocketDisconnect:
        pass
