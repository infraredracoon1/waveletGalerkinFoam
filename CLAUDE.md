# CLAUDE.md: Development Guide for waveletGalerkinFoam

> AI assistant playbook for contributing to the waveletGalerkinFoam repository

## 1. Project Overview

**waveletGalerkinFoam** is a numerical validation framework for proving global existence and uniqueness of smooth solutions to the 3D incompressible Navier-Stokes equations—addressing **Case A of the Clay Millennium Problem**.

### Scientific Approach
- **Method**: Anisotropic wavelet-Galerkin discretization
- **Wavelets**: Daubechies D6 basis functions
- **Function Space**: Besov space B^1/4_∞,∞ with anisotropic exponents
- **Validation**: BKM integral tracking across Reynolds numbers 100–10^6
- **Innovation**: Wavelet-based multiscale analysis avoiding classical regularity barriers

### Key Milestones
- **2025 (Q3)**: Integration of src/, data/, and scripts/ directories with full simulation code
- **Ongoing**: Telemetry dashboard (production-grade, fully operational)
- **Target**: Peer-reviewed publication with reproducible numerical evidence

### Contact & Attribution
- **Author**: infraredracoon@gmail.com
- **License**: CC BY 4.0 (Creative Commons Attribution)
- **Repository**: https://github.com/infraredracoon1/waveletGalerkinFoam
- **Branch**: Feature documentation on `claude/claude-md-docs-bawyby`

---

## 2. Repository Structure

```
waveletGalerkinFoam/
├── README.md                              # Project overview, setup, validation results
├── LICENSE                                # CC BY 4.0
├── CLAUDE.md                              # This file—AI assistant development guide
│
├── .github/
│   ├── workflows/
│   │   └── telemetry-dashboard.yml       # CI/CD: test backend/frontend, deploy
│   └── scripts/
│       └── optimize-frontend.mjs         # HTML minification for dashboard
│
├── .claude/
│   └── skills/
│       └── telemetry-dashboard/          # Production monitoring system
│           ├── SKILL.md                  # Skill documentation & MCP endpoints
│           ├── bundle/
│           │   ├── frontend/             # React dashboard (9 tabs, real-time)
│           │   │   ├── index.html
│           │   │   ├── package.json
│           │   │   └── src/
│           │   ├── backend/              # FastAPI + WebSocket server
│           │   │   ├── main.py
│           │   │   ├── requirements.txt
│           │   │   └── ...
│           │   ├── ios/                  # Swift iOS application
│           │   └── docker/               # Docker Compose configuration
│           └── telemetry-dashboard-bundle-v1.6.0.zip
│
├── src/ (PLANNED—July 2025)
│   ├── main.C                            # Main simulation loop
│   ├── computeWaveletCoefficients.H     # Daubechies D6 computation
│   ├── computeBetaJ.H                   # β_j = (ω·Sω)/(|ω|²+ε)
│   └── projectDivergenceFree.H          # Helmholtz decomposition
│
├── data/ (PLANNED—July 2025)
│   ├── bkm_integral.csv                 # Validation results (Re: 100–10^6)
│   └── beta_j_results.csv               # Simulation output
│
├── docs/ (PLANNED—July 2025)
│   └── chartjs_config.json              # Web visualization specs
│
└── scripts/ (PLANNED—July 2025)
    └── postProcess.py                    # Plot generation (Matplotlib)
```

### Maturity Status
| Component | Status | Notes |
|-----------|--------|-------|
| Telemetry Dashboard | ✅ Production | Full-featured, tested via CI/CD |
| Simulation Core (src/) | 🚧 Planned | Expected July 2025 release |
| Post-processing (scripts/) | 🚧 Planned | Depends on src/ integration |
| Data & Results (data/) | 🚧 Planned | Validation CSVs with July 2025 release |

---

## 3. Technology Stack

### Simulation Core (Planned)
- **Language**: C++ with OpenFOAM extensions
- **Build System**: OpenFOAM wmake
- **Numerical Libraries**: FFTW3 (Fast Fourier Transform)
- **Framework Version**: OpenFOAM v2212
- **Language Standard**: C++17

### Telemetry Dashboard (Current)
- **Frontend**: React 18+, Node.js, WebSocket client
- **Backend**: Python 3.9+, FastAPI, uvicorn, WebSocket server
- **Mobile**: Swift, iOS 13.0+
- **Communication**: REST API + WebSocket (60 FPS)
- **Authentication**: JWT (JSON Web Tokens)
- **Rate Limiting**: Per-endpoint, per-client

### Testing & CI/CD
- **Pipeline**: GitHub Actions
- **Frontend Tests**: Node.js test runner (package.json scripts)
- **Backend Tests**: FastAPI endpoint validation, WebSocket streaming
- **Linting**: GitHub Actions workflow checks
- **Deployment**: GitHub Pages (frontend), Docker (full stack)

### Data & Visualization
- **Post-processing**: Python 3.9+, Pandas, Matplotlib
- **Web Charts**: Chart.js configuration
- **Formats**: CSV for results, JSON for config

---

## 4. Development Workflows

### Telemetry Dashboard (Current/Stable)

#### Frontend Development
1. **Navigate**: `cd .claude/skills/telemetry-dashboard/bundle/frontend`
2. **Install**: `npm install`
3. **Start dev server**: `npm start`
4. **Access**: http://localhost:3000
5. **Modify**: Edit React components in `src/`, HMR reloads automatically
6. **Test**: Run `npm test` before committing
7. **Build**: `npm run build` for production

**Dashboard Tabs (9 total)**
- Telemetry: System overview, sensor status
- Audio: Real-time FFT spectrum (44.1 kHz, 2048 points)
- Motion: Accelerometer, gyroscope, magnetometer
- Beamform: Directional audio detection
- Hypercardioid: Microphone polar patterns
- Constellations: Frequency constellation mapping
- Wave Detection: 360° directional analysis
- RAMPG Solver: Optimization metrics
- Export: JSON/CSV data download

#### Backend Development
1. **Navigate**: `cd .claude/skills/telemetry-dashboard/bundle/backend`
2. **Create virtual env**: `python3 -m venv venv && source venv/bin/activate`
3. **Install dependencies**: `pip install -r requirements.txt`
4. **Run server**: `python main.py` (default: http://localhost:8000)
5. **Test endpoints**: GitHub Actions validates all 6 sensor API routes
6. **WebSocket**: Test streaming with built-in `/ws` endpoint
7. **Modify**: Update FastAPI endpoints in `main.py`; server auto-reloads

**Key Endpoints**
- `GET /health`: Server status check
- `POST /calibrate/{sensor}`: Sensor calibration
- `GET /sensors/data`: Fetch current readings
- `WS /ws`: WebSocket stream (60 FPS updates)
- `GET /fft/{frequency_range}`: FFT analysis
- `POST /export`: Data export (JSON/CSV)

#### Testing & Deployment
1. **GitHub Actions** automatically runs on every push
   - Validates all backend endpoints
   - Tests WebSocket stability
   - Checks frontend linting
   - Deploys to GitHub Pages if tests pass
2. **Frontend optimization**: `.github/scripts/optimize-frontend.mjs` strips comments, collapses whitespace
3. **Docker deployment**: Use `bundle/docker/docker-compose.yml` for containerized stack

### Simulation Core (Planned—July 2025)

Once `src/` is populated:

1. **Setup Environment**
   ```bash
   source /opt/openfoam2212/etc/bashrc
   sudo apt-get install fftw3-dev python3-pandas python3-matplotlib
   ```

2. **Build Simulation**
   ```bash
   cd src
   wmake main.C
   ```

3. **Run with Initial Conditions**
   ```bash
   ./main --condition turbulent     # Turbulent flow
   ./main --condition vortex-ring   # Rotating vortex ring
   ./main --condition kolmogorov    # Kolmogorov-type flow
   ./main --condition oscillatory   # Forced oscillatory field
   ./main --condition extreme-grad  # Extreme gradient test
   ./main --condition non-periodic  # Non-periodic domain test
   ```

4. **Validation**
   - Monitor BKM integral convergence in `data/bkm_integral.csv`
   - Verify error bounds in Besov norm
   - Check across Reynolds numbers: Re ∈ [100, 10^6]

5. **Post-process Results**
   ```bash
   python ../scripts/postProcess.py --input data/bkm_integral.csv --output plots/
   ```

### General Development Workflow

#### Branch Strategy
- **Main branch**: Stable release code
- **Feature branches**: `feature/component-name` or `feature/issue-#123`
- **Documentation branches**: `claude/claude-md-docs-*` (already on one)
- **Always**: Branch from latest `main` or designated feature branch

#### Commit Messages
- **Format**: `<type>: <subject>` (e.g., `feat: add JWT rate limiting`, `fix: WebSocket timeout`)
- **Types**: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`
- **Subject**: Imperative mood, lowercase, no period, ≤50 chars
- **Body** (if needed): Explain *why*, not what
- **Reference issues**: Close issues with `Closes #123` in body

#### Pull Request Process
1. **Before pushing**:
   - Run linting locally (if configured)
   - Test changes manually or via test suite
   - Update README/CLAUDE.md if architectural changes
2. **Create PR**:
   - Clear title and description
   - Link related issues: `Closes #456`
   - Reference any breaking changes
3. **Await CI**:
   - GitHub Actions validates automatically
   - Address any failing checks before merge
4. **Review**:
   - Incorporate feedback; re-request review after changes
   - One approval required before merge

#### Testing Expectations
- **Backend**: All endpoints tested in CI via GitHub Actions
- **Frontend**: Run `npm test` before committing
- **Simulation** (future): Run full Reynolds number suite, verify BKM integral
- **Documentation**: Ensure code examples still execute

---

## 5. Code Conventions

### C++ (Simulation Core—Future)
```cpp
// Classes: PascalCase
class WaveletGalerkin {
    // Member functions: camelCase
    void computeCoefficients() { }
    
    // Member variables: camelCase with m_ prefix for private
    double m_tolerance;
};

// Free functions: camelCase
void projectDivergenceFree(Field& u) { }

// Constants: UPPER_SNAKE_CASE
const double REYNOLDS_MIN = 100.0;

// Comments: Explain *why* for non-obvious wavelet math
// Compute β_j = (ω · S ω) / (|ω|^2 + ε) to avoid division by zero
// near zero frequencies (ε = 1e-8)
```

### Python (Post-processing & Tests)
```python
# Modules, functions: snake_case (PEP 8)
def compute_bkm_integral(reynolds_number, wavelet_order):
    """Compute BKM integral for given Reynolds number."""
    pass

# Classes: PascalCase
class ValidationMetrics:
    def __init__(self):
        self.tolerance = 1e-6
        
# Constants: UPPER_SNAKE_CASE
MAX_REYNOLDS = 1e6
```

### React / JavaScript (Dashboard)
```javascript
// Components: PascalCase
function TelemetryDashboard() { return <div>...</div>; }

// Functions, variables: camelCase
const handleSensorUpdate = (data) => { };

// Constants: UPPER_SNAKE_CASE
const API_BASE_URL = 'http://localhost:8000';
const WS_TIMEOUT_MS = 5000;
```

### General Conventions
- **Naming**:
  - Prefer descriptive names: `computeWaveletCoefficients()` over `cwc()`
  - Avoid abbreviations except standard ones (FFT, BKM, Re for Reynolds)
- **Comments**: Only explain non-obvious logic, *why* decisions, mathematical nuances
- **Error Handling**:
  - Validate at system boundaries (user input, external APIs)
  - Use assertions for internal invariants
  - Never commit secrets in error messages
- **Testing**:
  - Unit tests for utilities and numerical functions
  - Integration tests for API endpoints (GitHub Actions)
  - Test data validity, not just code syntax
- **Documentation**:
  - Docstrings for public functions (describe parameters, return values)
  - Update CLAUDE.md for architectural changes
  - Keep README synchronized with project status

---

## 6. Key Components Deep Dive

### Telemetry Dashboard (Production-Ready)

**Purpose**: Real-time multi-sensor monitoring system with directional audio analysis, calibration, and cloud export.

**Supported Sensors**
1. **Accelerometer**: 3-axis motion (±16g typical)
2. **Gyroscope**: Angular velocity (±2000°/s typical)
3. **Magnetometer**: Earth's magnetic field (±50µT typical)
4. **Barometer**: Atmospheric pressure (300–1100 hPa)
5. **Microphone**: Audio input (44.1 kHz, 16-bit)
6. **Light Sensor**: Ambient illumination (0–65536 lux)

**Features**
- ✅ **Real-time streaming**: 60 FPS WebSocket updates
- ✅ **FFT analysis**: 2048-point FFT on audio (frequency resolution: ~21.5 Hz)
- ✅ **Beamforming**: Directional audio detection (linear phased arrays)
- ✅ **Hypercardioid patterns**: Microphone polar response simulation
- ✅ **Calibration**: Per-sensor offset/scale adjustment
- ✅ **JWT auth**: Stateless token-based access control
- ✅ **Rate limiting**: 1000 req/min per client (configurable)
- ✅ **MCP integration**: Claude model context protocol endpoints
- ✅ **Export**: JSON and CSV data download

**Making Changes**
- **Adding a sensor type**: Modify `backend/main.py` to add `/sensors/<type>` route; update `frontend/src/components/SensorPanel.jsx`
- **Changing update frequency**: Adjust WebSocket interval in `backend/main.py` (default: 60 FPS = 16.67 ms)
- **New dashboard tab**: Create React component in `frontend/src/components/`, add route in `frontend/src/App.jsx`
- **Coordination**: Frontend/backend/iOS changes must stay synchronized (same schema for sensor data)

**Testing**
- GitHub Actions runs `telemetry-dashboard.yml` on every push
- Tests validate: all 6 REST endpoints, WebSocket stability, JSON schema compliance
- Manual: Start backend/frontend locally, test in browser at http://localhost:3000

### Simulation Core (Planned—July 2025)

**Purpose**: Prove global existence and regularity for 3D incompressible Navier-Stokes using wavelet-Galerkin method.

**Numerical Method**
- **Discretization**: Anisotropic wavelet-Galerkin (Daubechies D6)
- **Space**: Triadic dyadic cubes with anisotropic frequency exponents
- **Initial conditions**: Configurable (turbulent, vortex rings, Kolmogorov, extreme gradients)
- **Time integration**: Implicit or explicit scheme (TBD with full code)
- **Validation metric**: BKM integral (Beale–Kato–Majda criterion for regularity)

**Key Computations**
- **`computeWaveletCoefficients.H`**: Daubechies D6 basis functions and inner products
  - Input: Velocity field `u` on dyadic grid
  - Output: Wavelet expansion coefficients in Besov space
- **`computeBetaJ.H`**: Stress tensor coefficient β_j
  - Formula: β_j = (ω · S ω) / (|ω|² + ε)
  - Controls energy cascade and nonlinear feedback
- **`projectDivergenceFree.H`**: Helmholtz decomposition
  - Enforces ∇ · u = 0 at each time step
  - Uses spectral projection in Fourier space

**Validation Approach**
- Run across Reynolds numbers: Re ∈ {100, 500, 1000, 5000, 10⁴, 10⁵, 10⁶}
- Track BKM integral `I(t) = ∫₀ᵗ (||∇u||²_L∞ + ||p||_L∞) dτ`
- Verify error bounds in Besov norm: ||u||_{B^1/4_{∞,∞}} < C(T, Re)
- Compare with analytical solutions on extreme gradient test case
- Expected output: `data/bkm_integral.csv` (time, Reynolds, integral value)

**Modification Guidelines**
- **Changing wavelet type** (e.g., D4, D8): Affects compression ratio and smoothness; re-validate error bounds
- **New initial condition**: Add case to `main.C`; ensure divergence-free
- **Different time scheme**: Verify stability (Courant condition); test on benchmark cases
- **Adding dissipation** (e.g., hyperviscosity): Document rationale; check energy conservation

---

## 7. Contribution Guidelines

### Before Starting Work
1. **Check GitHub Issues**: Search for related work or requests
2. **Coordinate**: For major changes (algorithm changes, new initial conditions, refactoring), open an issue first
3. **Understand scope**: Is this a bug fix (small), feature (medium), or redesign (large)?

### For Simulation Enhancements
- **Mathematical correctness**: Consult wavelet-Galerkin literature; cite references in comments
- **Validation**: Test across *all* Reynolds numbers before submitting PR
- **Documentation**: Include error analysis, BKM integral plots, comparison with prior work
- **No shortcuts**: Don't skip validation to merge faster

### For Dashboard Improvements
- **Backward compatibility**: Existing sensor APIs must not break
- **Multi-platform testing**: Test on browser (dev server), Docker, and iOS (if modified)
- **WebSocket stability**: High-frequency data streams must not drop frames
- **Authentication**: Any new endpoint requires JWT or equivalent
- **Rate limits**: Ensure limits don't block legitimate clients

### PR Process
1. **Clear description**: What does this change do? Why?
2. **Link issues**: `Closes #123` if addressing an issue
3. **Test results**: Describe how you tested (manual + automated)
4. **Breaking changes**: If any, justify in PR body
5. **Code review**: Address feedback; re-request review after changes
6. **CI/CD**: Wait for GitHub Actions to pass before merge
7. **Attribution**: Respect CC BY 4.0 license; acknowledge prior work

### What We Don't Accept
- ❌ Hardcoded secrets (API keys, tokens) in code
- ❌ Large PRs without prior issue discussion
- ❌ Bypassing validation (e.g., skipping full Reynolds number suite)
- ❌ Removing or disabling tests
- ❌ License changes without discussion

---

## 8. Getting Started

### For Dashboard Development (Immediate)

**Quick Start (Telemetry Dashboard)**
```bash
# Clone and navigate
git clone https://github.com/infraredracoon1/waveletGalerkinFoam
cd waveletGalerkinFoam
git checkout claude/claude-md-docs-bawyby

# Start backend
cd .claude/skills/telemetry-dashboard/bundle/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
# Server runs on http://localhost:8000

# In a new terminal: Start frontend
cd .claude/skills/telemetry-dashboard/bundle/frontend
npm install
npm start
# Dashboard opens at http://localhost:3000
```

**Expected**: Dashboard with 9 tabs, WebSocket connected, sensors streaming data.

### For Simulation Development (July 2025+)

**Setup (When src/ is Available)**
```bash
# Install dependencies
source /opt/openfoam2212/etc/bashrc
sudo apt-get install fftw3-dev python3-pandas python3-matplotlib

# Build
cd waveletGalerkinFoam/src
wmake main.C

# Run validation suite
./main --condition turbulent
./main --condition vortex-ring
./main --condition extreme-grad
# ... (check data/bkm_integral.csv after each run)

# Post-process and plot
cd ..
python scripts/postProcess.py --input data/bkm_integral.csv --output results/
```

**Expected**: CSV with BKM integral values, error bounds within tolerance, plots matching literature.

### For CI/CD Debugging

**Check GitHub Actions**
1. Navigate to .github/workflows/telemetry-dashboard.yml
2. Look for test failures (backend API routes, WebSocket streaming)
3. Reproduce locally:
   ```bash
   # Test backend manually
   curl http://localhost:8000/health
   python -c "import asyncio; from main import app; asyncio.run(test_websocket())"
   ```
4. Fix and push—GitHub Actions re-runs automatically

---

## 9. Security & Secrets Management

### Core Principles
- **Never commit secrets** to git (API keys, tokens, credentials)
- **Never display secrets** in logs, error messages, or documentation
- **Always use environment variables** for sensitive configuration
- **Validate inputs** at system boundaries only

### Sensitive Data Types in This Project
- **API Key**: FastAPI token secret (`.env: API_SECRET_KEY`)
- **JWT Secret**: Signing key for dashboard auth (`.env: JWT_SECRET`)
- **Database credentials** (future): If persistence layer is added
- **OAuth tokens**: GitHub, sensor hardware IDs
- **Calibration keys**: Device-specific sensor calibration data

### Best Practices for AI Assistants
- ⚠️ **DO NOT** echo secret values in code comments or chat
- ⚠️ **DO NOT** commit `.env` files; use `.env.example` with placeholders
- ⚠️ **DO NOT** hardcode secrets; always reference `os.getenv('SECRET_NAME')`
- ⚠️ **DO NOT** include secrets in error messages: `logger.error(f"Auth failed: {secret}")` ← BAD
- ⚠️ **DO NOT** list secrets in README, CLAUDE.md, or issue descriptions

### Development (Local)
```bash
# Create .env file (gitignored)
cat > .claude/skills/telemetry-dashboard/bundle/backend/.env <<EOF
API_SECRET_KEY="dev-secret-key-not-for-production"
JWT_SECRET="dev-jwt-secret"
DATABASE_URL="sqlite:///./test.db"  # Local dev only
EOF

# Load in Python
from dotenv import load_dotenv
import os
load_dotenv()
secret = os.getenv('API_SECRET_KEY')
```

### CI/CD (GitHub Actions)
1. **Store secrets** in GitHub repository settings:
   - Settings → Secrets and variables → Actions
   - Add: `API_SECRET_KEY`, `JWT_SECRET`, etc.
2. **Reference in workflows**:
   ```yaml
   - run: python main.py
     env:
       API_SECRET_KEY: ${{ secrets.API_SECRET_KEY }}
       JWT_SECRET: ${{ secrets.JWT_SECRET }}
   ```
3. **Never log secrets**:
   ```bash
   # BAD: env outputs secrets
   echo $API_SECRET_KEY
   
   # GOOD: no output
   python main.py  # Uses env var internally
   ```

### Deployment (Production)
- Use environment-specific config: `dev.env`, `staging.env`, `production.env`
- Rotate secrets regularly (every 90 days minimum)
- Audit access logs for unauthorized attempts
- Keep dependencies updated (run `pip audit`, check for CVEs)
- Enable rate limiting on all endpoints
- Validate all input before processing

---

## 10. Known Limitations & Future Work

### Current State
- ✅ **Telemetry Dashboard**: Fully operational, production-grade
- 🚧 **Simulation Core**: In development, delivery July 2025
- ✅ **CI/CD Pipeline**: GitHub Actions validation active
- 📚 **Documentation**: README and CLAUDE.md in place

### Planned Integrations (July 2025)
- `src/`: Full C++ wavelet-Galerkin implementation with OpenFOAM
- `data/`: BKM integral validation results, CSV format
- `scripts/`: Post-processing pipeline (Matplotlib visualization)
- `docs/`: Chart.js configuration for web visualization

### Known Issues
- See GitHub Issues for open items: https://github.com/infraredracoon1/waveletGalerkinFoam/issues
- Report bugs with reproducible steps and expected behavior

### Future Enhancements
- **Extended Reynolds range**: Expand validation to Re up to 10^7
- **Improved calibration workflows**: Automated sensor offset detection
- **Real-time dashboard streaming**: Live BKM integral visualization during simulation
- **Parallel execution**: Multi-GPU wavelet decomposition
- **Machine learning integration**: Neural operator surrogate models

---

## 11. Resources & References

### Project Links
- **GitHub**: https://github.com/infraredracoon1/waveletGalerkinFoam
- **Contact**: infraredracoon@gmail.com
- **License**: CC BY 4.0 (Creative Commons Attribution)

### Technical Documentation
- **OpenFOAM**: https://www.openfoam.com/documentation
- **FFTW3**: http://www.fftw.org
- **FastAPI**: https://fastapi.tiangolo.com
- **React**: https://react.dev
- **GitHub Actions**: https://docs.github.com/en/actions

### Scientific Background
- Wavelet-Galerkin methods for Navier-Stokes (see README citations)
- Besov space regularity theory
- BKM criterion for blow-up prevention

### Clay Millennium Problem
- **Official Problem Statement**: https://www.claymath.org/millennium-problems/navier%E2%80%93stokes-equation
- **Context**: Global existence and smoothness for 3D incompressible Navier-Stokes

---

## Quick Reference: Common Commands

```bash
# Development
git checkout claude/claude-md-docs-bawyby
git pull origin claude/claude-md-docs-bawyby

# Dashboard frontend
cd .claude/skills/telemetry-dashboard/bundle/frontend
npm install && npm start

# Dashboard backend
cd .claude/skills/telemetry-dashboard/bundle/backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt && python main.py

# Test & commit
git add <files>
git commit -m "feat: description of change"
git push -u origin claude/claude-md-docs-bawyby

# Simulation (future)
cd src && wmake main.C && ./main --condition turbulent
cd .. && python scripts/postProcess.py --input data/bkm_integral.csv
```

---

**Last Updated**: August 2025  
**Maintained by**: infraredracoon@gmail.com  
**License**: CC BY 4.0
