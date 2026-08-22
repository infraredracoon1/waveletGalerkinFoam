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

app = FastAPI(title="Telemetry Dashboard Backend", version="1.1.0")
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
    audio = {
        "fft": fft_mag,
        "rms": round(rms, 4),
        "direction_deg": direction_deg,
        "dominant_freq_hz": round(freq1, 1),
    }

    return {
        "timestamp": time.time(),
        "motion": {"accelerometer": accel, "gyroscope": gyro, "magnetometer": mag},
        "environment": {"barometer": baro, "light": light_sensor},
        "audio": audio,
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
            ]
        )
        for h in rows:
            a, g, m = h["motion"]["accelerometer"], h["motion"]["gyroscope"], h["motion"]["magnetometer"]
            b, l = h["environment"]["barometer"], h["environment"]["light"]
            au = h["audio"]
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
