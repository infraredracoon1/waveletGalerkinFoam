"""Telemetry Dashboard backend.

Simulates 6 sensors (accelerometer, gyroscope, magnetometer, barometer,
microphone, light) since this environment has no real hardware sensors, and
serves them over REST + WebSocket in the shape described by the skill's
SKILL.md. Values are physically plausible (noise/drift around real-world
baselines), not random garbage.
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
from typing import Optional

import numpy as np
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

try:
    import psutil
except ImportError:  # pragma: no cover - optional dependency
    psutil = None

app = FastAPI(title="Telemetry Dashboard Backend", version="1.6.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

START_TIME = time.time()
_T0 = time.time()

CONFIG = {
    "sampleRate": int(os.environ.get("TELEMETRY_SAMPLE_RATE", 44100)),
    "fftSize": int(os.environ.get("TELEMETRY_FFT_SIZE", 2048)),
    "updateRate": int(os.environ.get("TELEMETRY_UPDATE_RATE", 30)),
}

HISTORY_MAXLEN = 3600
history: deque = deque(maxlen=HISTORY_MAXLEN)

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

    return {
        "timestamp": time.time(),
        "motion": {"accelerometer": accel, "gyroscope": gyro, "magnetometer": mag},
        "environment": {"barometer": baro, "light": light_sensor},
        "audio": audio,
        "solver": solver,
    }


@app.get("/health")
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
def sensors():
    return read_sensors()


@app.get("/api/stats")
def stats():
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
def calibrate(sensor: str = Query("accelerometer")):
    if sensor == "accelerometer" and history:
        last = history[-1]["motion"]["accelerometer"]
        CALIBRATION["accelerometer"]["offset"] = [last["x"], last["y"], last["z"] - 1.0]
    elif sensor == "magnetometer":
        CALIBRATION["magnetometer"]["declination"] = round(random.uniform(-2, 2), 3)
    elif sensor == "barometer" and history:
        CALIBRATION["barometer"]["sea_level_kpa"] = history[-1]["environment"]["barometer"]["pressure_kpa"]
    return {"sensor": sensor, "status": "calibrated", "calibration": CALIBRATION.get(sensor)}


@app.get("/api/mute/status")
def mute_status():
    return {
        "has_target": PATTERN_MATCH["target"] is not None,
        "threshold": PATTERN_MATCH["threshold"],
        "muted": PATTERN_MATCH["muted"],
        "score": PATTERN_MATCH["score"],
    }


@app.post("/api/mute/capture")
def mute_capture():
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
def mute_clear():
    PATTERN_MATCH["target"] = None
    PATTERN_MATCH["muted"] = False
    PATTERN_MATCH["score"] = 0.0
    return mute_status()


@app.post("/api/mute/config")
def mute_config(threshold: float = Query(..., ge=0.0, le=1.0)):
    PATTERN_MATCH["threshold"] = threshold
    return mute_status()


@app.get("/api/config")
def get_config():
    return CONFIG


@app.post("/api/config")
def set_config(
    sampleRate: Optional[int] = None,
    fftSize: Optional[int] = None,
    updateRate: Optional[int] = None,
):
    if sampleRate:
        CONFIG["sampleRate"] = sampleRate
    if fftSize:
        CONFIG["fftSize"] = fftSize
    if updateRate:
        CONFIG["updateRate"] = updateRate
    return CONFIG


@app.get("/api/export")
def export(format: str = "json"):
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
            ]
        )
        for h in rows:
            a, g, m = h["motion"]["accelerometer"], h["motion"]["gyroscope"], h["motion"]["magnetometer"]
            b, l = h["environment"]["barometer"], h["environment"]["light"]
            au = h["audio"]
            sv = h.get("solver", {})
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
    await websocket.accept()
    try:
        while True:
            reading = read_sensors()
            history.append(reading)
            await websocket.send_text(json.dumps(reading))
            await asyncio.sleep(1 / max(1, CONFIG["updateRate"]))
    except WebSocketDisconnect:
        pass
