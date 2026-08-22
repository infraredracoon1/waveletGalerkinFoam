# Third-party license audit

This bundle's own code (`backend/main.py`, `frontend/`, `docker/`, `launch.sh`,
`ios/*.swift`) is MIT-licensed — see `LICENSE`. This file audits what it
depends on, so it's usable both by a commercial deployer and by an
independent researcher without hidden surprises. Checked directly against
each package's installed `dist-info/METADATA` in this session — not taken
from memory.

## Python (backend/requirements.txt)

| Package | Version | License | Verified via |
|---|---|---|---|
| fastapi | 0.115.0 | MIT | `Classifier: License :: OSI Approved :: MIT License` |
| starlette | 0.38.6 | BSD-3-Clause | `License-Expression: BSD-3-Clause` |
| uvicorn | 0.30.6 | BSD-3-Clause | `License-Expression: BSD-3-Clause` |
| pydantic | 2.13.4 | MIT | `License-Expression: MIT` |
| click | 8.4.2 | BSD-3-Clause | `License-Expression: BSD-3-Clause` |
| anyio | 4.14.2 | MIT | `License-Expression: MIT` |
| h11 | 0.16.0 | MIT | `License: MIT` |
| psutil | 6.0.0 | BSD-3-Clause | `License: BSD-3-Clause` |
| numpy | 1.26.4 | BSD-3-Clause | Copyright header + BSD-3 notice |
| websockets | 17.0.1 | BSD-3-Clause | `License-Expression: BSD-3-Clause` (CI test dependency only, not shipped) |

All permissive, all explicitly allow commercial use and redistribution with
attribution (retain the copyright/license notice — none require you to open
your own code, i.e. no copyleft here).

**NumPy vendoring note:** NumPy's own code is BSD-3-Clause. Its compiled
wheel additionally bundles a couple of low-level numerical libraries
(OpenBLAS/LAPACK: BSD-3-Clause; a GCC runtime component under
`GPL-3.0-with-GCC-exception`; `libquadmath` under `LGPL-2.1-or-later`). The
GCC runtime exception and LGPL both specifically permit this kind of
linking/redistribution without imposing their terms on your application —
this is the same standard NumPy wheel used commercially across the
industry, not something specific to this bundle.

## JavaScript (frontend/)

No npm dependencies — `frontend/server.js` uses only Node's built-in `http`/
`fs`/`path` modules, and `frontend/index.html` is vanilla JS with no
libraries. Node.js itself is MIT-licensed (with a small number of bundled
components under their own permissive licenses, e.g. V8 under BSD).

## Docker base images

- `python:3.11-slim` — Python itself is under the PSF License (permissive,
  commercial-use-friendly); the Debian userland it sits on is a mix of
  open-source licenses standard for any Debian-based container.
- `node:20-alpine` — Node.js is MIT; Alpine Linux's base packages (musl libc,
  busybox) are a standard open-source mix, same as any Alpine-based image
  used commercially today.

Neither base image imposes terms on your own application code layered on
top of them; this is the same footing as virtually every commercial
container deployment.

## GitHub Actions used in `.github/workflows/telemetry-dashboard.yml`

`actions/checkout`, `actions/setup-python`, `actions/setup-node`,
`actions/upload-artifact`, `actions/configure-pages`,
`actions/upload-pages-artifact`, `actions/deploy-pages` — all official
GitHub Actions, MIT-licensed.

## iOS (`ios/*.swift`, source-only/uncompiled — see README)

Uses only Apple's own frameworks (Foundation, CoreMotion, Combine,
SwiftUI). These aren't open-source-licensed third-party code; using them
requires accepting Apple's Developer Program License Agreement (the same
requirement for literally any iOS app, and independent of anything in this
bundle). That's a platform terms-of-service matter, not an open-source
licensing one — review Apple's current agreement yourself before building
or publishing.

## Platforms this bundle can be deployed to

- **GitHub / GitHub Pages / GitHub Actions**: covered by GitHub's own Terms
  of Service for using the platform; the code you push remains under this
  bundle's MIT license (or the parent repo's license — see below).
- **Base44**: a separate proprietary SaaS app-builder. Deploying there means
  accepting Base44's own Terms of Service (pricing, hosting, data handling,
  etc.). Nothing in this document is or can be a legal assessment of
  Base44's own ToS — that's between you and Base44; read their current
  terms before commercial use.
- **Docker / any host** (Render, Fly.io, Railway, your own server, etc.):
  the MIT license on this bundle's code places no restriction on commercial
  hosting anywhere.

## Relationship to the parent repository's license

The `waveletGalerkinFoam` repository's root `LICENSE` is
**CC BY 4.0** (Creative Commons Attribution), which explicitly permits
commercial use and adaptation with attribution. This bundle additionally
carries its own `LICENSE` (MIT) because Creative Commons itself
[recommends against using CC licenses for software](https://creativecommons.org/faq/#can-i-apply-a-creative-commons-license-to-software)
(no patent grant, no source-availability mechanics, ambiguity around what
counts as "the work" for code). MIT is the standard, unambiguous choice for
a software component like this one, and is compatible with — a strict
subset of — what CC BY 4.0 already permits. Whichever license the parent
repository ends up carrying for the rest of its (CFD/wavelet-Galerkin)
content is unrelated to and unaffected by this bundle's own MIT license.

## Bottom line

Every dependency this bundle's own code (backend, frontend, Docker, iOS
source) actually pulls in is permissively licensed (MIT/BSD-3-Clause) and
explicitly commercial-use-friendly, with attribution as the only
obligation. The two things outside pure open-source licensing to be aware
of before commercial or research deployment are platform Terms of Service
(Base44's ToS if you deploy there; Apple's Developer Agreement if you build
and ship the iOS app) — neither of which any tool available in this session
can review or agree to on your behalf.
