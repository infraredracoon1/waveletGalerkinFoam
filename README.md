# waveletGalerkinFoam

This repository contains the code, data, and manuscript for a proof of global existence and uniqueness of smooth solutions to the 3D incompressible Navier-Stokes equations, addressing Case A of the Clay Millennium Problem. The approach uses an anisotropic wavelet-Galerkin method with Daubechies D6 wavelets in the homogeneous Besov space \(\dot{B}^{1/4}_{\infty,\infty}\), controlling vorticity via the Beale-Kato-Majda criterion. The proof is purely analytical, with numerical validation in OpenFOAM for Reynolds numbers up to \(10^6\) across diverse initial conditions, including extreme gradient (\(\sin(1000\pi x)\)) and non-periodic flows (\(x/(1+x^2), y/(1+y^2), 0)\). We invite scrutiny of vorticity bounds (Appendix A.1) and wavelet projections (Section 6.4). Licensed under CC BY 4.0.

Contact: infraredracoon@gmail.com

## Overview

The manuscript (`manuscript.tex`) provides a rigorous analytical proof, supported by numerical simulations in OpenFOAM v2212. The code implements a wavelet-Galerkin solver with Daubechies D6 wavelets, computing BKM integrals and \(\beta_j\) functionals for various initial conditions. Numerical results validate the analytical bound \(\int_0^T \|\omega\|_{L^\infty} \, dt \leq C T^{9/16}\). The repository is structured for reproducibility, with a `Makefile` automating compilation, plotting, and simulation.

## Repository Structure

- **`src/`**: OpenFOAM solver code.
  - `main.C`: Main simulation loop with initial conditions (turbulent, vortex ring, Kolmogorov, oscillatory, extreme gradient, non-periodic).
  - `computeWaveletCoefficients.H`: Computes Daubechies D6 wavelet coefficients.
  - `computeBetaJ.H`: Computes \(\beta_j = \frac{\omega \cdot S \omega}{|\omega|^2 + \epsilon}\) in wavelet space.
  - `projectDivergenceFree.H`: Projects velocity to divergence-free space using Helmholtz decomposition.
- **`data/`**:
  - `bkm_integral.csv`: BKM integral results for \(\text{Re} = 100\) to \(10^6\), with 5% error bars (3% truncation, 2% statistical).
- **`docs/`**:
  - `chartjs_config.json`: Chart.js configuration for web visualization of BKM integrals.
  - `bkm_plot.png`: Generated plot of BKM integrals (via `postProcess.py`).
- **`scripts/`**:
  - `postProcess.py`: Generates `bkm_plot.png` from `bkm_integral.csv` using Python/Matplotlib.
- **`manuscript.tex`**: LaTeX manuscript with proof, derivations, and numerical validation.
- **`Makefile`**: Automates compilation of manuscript, plot, and solver.

## Setup Instructions

### Prerequisites
- **System**: Linux (Ubuntu 20.04+ recommended).
- **Dependencies**:
  - `pdflatex`: For compiling `manuscript.tex`.
  - `python3` with `pandas>=2.0`, `matplotlib>=3.8`: For `postProcess.py`.
  - `OpenFOAM v2212`: For solver compilation.
  - `fftw3-dev`: For wavelet transforms.
  - `make`: For automation.
- Install dependencies:
  ```bash
  sudo apt-get update
  sudo apt-get install openfoam2212 fftw3-dev texlive-full
  pip install pandas matplotlib
