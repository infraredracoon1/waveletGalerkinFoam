# Telemetry Dashboard — Deployment Guide (v1.1.0)

A working implementation of the dashboard described in the skill's `SKILL.md`:
a FastAPI backend, a zero-dependency HTML/JS dashboard frontend, Docker
configs, and iOS source stubs.

## Known limitations (read this first)

- **Sensors are simulated.** This bundle was built and run in a Linux
  container with no accelerometer/gyroscope/microphone/etc. hardware.
  `backend/main.py` generates physically plausible signals (noise/drift
  around real-world baselines: ~1g on Z, ~101.3 kPa pressure, etc.) instead
  of reading real hardware. Swap `read_sensors()` for real hardware access
  when deploying on a device that actually has sensors.
- **The iOS app is source-only.** `ios/SensorManager.swift` and
  `ios/TelemetryApp.swift` have not been compiled or run — there is no
  macOS/Xcode toolchain in this environment. Open the `ios/` folder in Xcode
  on a Mac to build and test it for real before trusting it.
- **"RAMPG Solver" tab** — the original doc described this vaguely as
  "optimization metrics and performance data." It's implemented here as a
  real backend CPU/memory performance panel (driven by `/health` polling),
  since that's the genuine telemetry this bundle has to show — not a
  fabricated metric.

## Run natively

```bash
./launch.sh
```

Requires Python 3.9+ and Node.js 18+. Creates a venv, installs backend
dependencies, and starts both servers:
- Frontend: http://localhost:3000
- Backend:  http://localhost:8000

## Run with Docker

```bash
cd docker
docker compose up -d --build
```

- Frontend: http://localhost:3000
- Backend:  http://localhost:8000

Stop with `docker compose down` (run from the `docker/` directory).

## Configuration

Environment variables (native or Docker):

```bash
export TELEMETRY_BACKEND_PORT=9000     # native launch.sh only
export TELEMETRY_FRONTEND_PORT=4000    # native launch.sh only
export TELEMETRY_UPDATE_RATE=30        # WebSocket ticks/sec
export TELEMETRY_SAMPLE_RATE=44100     # simulated audio sample rate
export TELEMETRY_FFT_SIZE=2048         # requested FFT size (bins are capped to 64 for transport)
```

Runtime config can also be read/changed via `GET`/`POST /api/config` while
the backend is running (see below), and applied live from the dashboard's
Export tab.

## API reference

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Status, sensor readiness, uptime, CPU/memory |
| GET | `/api/sensors` | One current sensor reading (all 6 sensor types) |
| GET | `/api/stats` | Rolling min/max/mean over the in-memory history |
| POST | `/api/calibrate?sensor=accelerometer\|magnetometer\|barometer` | Simulated calibration |
| GET | `/api/config` | Current runtime config |
| POST | `/api/config?updateRate=...&sampleRate=...&fftSize=...` | Update runtime config |
| GET | `/api/export?format=json\|csv` | Export accumulated history |
| WS | `/ws/sensors` | Streams one JSON reading per tick |

## Troubleshooting

**Port already in use**
```bash
lsof -i :3000 -sTCP:LISTEN | awk 'NR>1{print $2}' | xargs -r kill
```

**Dashboard shows "unreachable" / stays "connecting…"**
- Confirm the backend is actually running: `curl http://localhost:8000/health`
- If frontend and backend are on different hosts/ports, set
  `window.TELEMETRY_BACKEND` at the top of `frontend/index.html`'s inline
  script before serving it.

**Docker build fails to reach PyPI/npm**
- This environment sits behind an outbound proxy for some networks; if
  `docker compose build` can't reach package registries, build on a host
  with normal internet access, or vendor the wheels/packages first.
