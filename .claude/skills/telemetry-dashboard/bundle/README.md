# Telemetry Dashboard — Deployment Guide (v1.5.0)

A working implementation of the dashboard described in the skill's `SKILL.md`:
a FastAPI backend, a zero-dependency HTML/JS dashboard frontend, Docker
configs, and iOS source stubs.

## Licensing — safe for commercial use and independent research

This bundle's own code is **MIT-licensed** (`LICENSE`) — permissive, no
copyleft, commercial use and modification explicitly allowed. Every
dependency it actually pulls in (FastAPI, Starlette, Uvicorn, Pydantic,
NumPy, psutil, the GitHub Actions used to test/deploy it) was checked
directly against its installed package metadata in this session and is
MIT or BSD-3-Clause — see `THIRD_PARTY_LICENSES.md` for the full,
package-by-package audit. Two things sit outside open-source licensing and
are called out there rather than glossed over: Base44's own Terms of
Service (if you deploy there) and Apple's Developer Program Agreement (if
you build/ship the iOS app) — neither is something any tool here can
review or agree to for you.

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
- **GitHub Pages hosts the frontend only.** Pages serves static files; it
  cannot run the Python backend or hold the WebSocket connection open. See
  "Deploy the frontend to GitHub Pages" below for how the page handles that.

## Deploy the frontend to GitHub Pages

`.github/workflows/telemetry-dashboard.yml` (repo root) does two things on
every push that touches this bundle:

1. **`test` job** — actually installs the backend's dependencies, starts
   `uvicorn` and the Node static server for real on the runner, then curls
   every REST endpoint (health, sensors, stats, calibrate, export, and the
   full wave-pattern-mute flow: capture → confirms muted → clear → confirms
   unmuted → threshold config) and opens the `/ws/sensors` WebSocket with a
   short Python script to confirm it streams a valid reading. This is a real
   run of the app, not just a build check.
2. **`deploy` job** (runs after `test` passes) — copies `frontend/index.html`
   through `.github/scripts/optimize-frontend.mjs` (strips HTML comments and
   excess whitespace; conservative on purpose — this page is ~19KB and Pages
   already serves it gzipped, so there's little to gain from aggressive
   minification), then publishes it with a plain `git push` to a `gh-pages`
   branch.

   This bundle originally used the "Actions" Pages source
   (`actions/configure-pages` + `actions/deploy-pages`), but every attempt
   failed with `Resource not accessible by integration` when the action
   tried to *create* the Pages site — this repo's default `GITHUB_TOKEN`
   doesn't have permission for that call, regardless of the job's declared
   `pages: write` permission. Pushing to a `gh-pages` branch sidesteps it
   entirely: it only needs `contents: write`, which the token already has.

**One-time manual step required** (no API in this toolchain can do this for
you): in the repo's **Settings → Pages**, set **Source** to **Deploy from a
branch**, branch **`gh-pages`**, folder **`/ (root)`**, and save. After
that, every push runs the workflow above and the site updates automatically
at the URL GitHub shows on that same settings page (typically
`https://<user>.github.io/<repo>/`).

**Since Pages can't run the backend**, the deployed page starts with no
reachable backend and shows "no backend reachable" instead of hanging on
"connecting…". Run the backend anywhere it can be reached from the browser
(natively, Docker, a host like Render/Fly.io/Railway) and point the deployed
page at it either:

- by URL: `https://<user>.github.io/<repo>/?backend=https://your-backend-host:8000`, or
- by typing the backend URL into the field next to the connection status in
  the page header and clicking **Connect** (remembered in that browser via
  `localStorage` for next time).

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
| GET | `/api/mute/status` | Wave pattern match state: has_target, threshold, muted, score |
| POST | `/api/mute/capture` | Capture the current audio FFT as the reference pattern |
| POST | `/api/mute/clear` | Clear the reference pattern and unmute |
| POST | `/api/mute/config?threshold=0.9` | Set the match threshold (0-1 cosine similarity) |
| GET | `/api/export?format=json\|csv` | Export accumulated history |
| WS | `/ws/sensors` | Streams one JSON reading per tick |

## Wave pattern matching → mute

The Audio tab can capture the current FFT shape as a reference pattern
(`POST /api/mute/capture`). On every subsequent tick, the backend computes
the cosine similarity between the live FFT and that reference; once the
score reaches the configured threshold (default 0.9), the audio channel
(`fft` and `rms` in `/api/sensors` and the WebSocket stream) is muted —
zeroed out — until the live signal drifts away from the captured pattern.
This is a pattern-triggered noise gate: it mutes matching sounds, not loud
ones. `POST /api/mute/clear` removes the reference and unmutes
immediately. The iOS `SensorManager` mirrors `muted`/`match_score` from the
WebSocket stream and exposes `captureMutePattern()` / `clearMutePattern()`
(source-only, uncompiled — see Known limitations above).

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
