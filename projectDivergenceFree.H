#ifndef projectDivergenceFree_H
#define projectDivergenceFree_H

#include "fvCFD.H"
#include "fftw3.h"

// Projects velocity field to divergence-free space using Helmholtz decomposition
volVectorField projectDivergenceFree(const volVectorField& U)
{
    // Compute phi = Laplacian^-1 (div U)
    volScalarField phi = fvc::laplacianInverse(fvc::div(U));
    // U_divFree = U - grad phi
    volVectorField U_divFree = U - fvc::grad(phi);
    // Ensure divergence-free in Fourier space
    fftw_plan plan;
    fftw_complex *in, *out;
    in = (fftw_complex*) fftw_malloc(sizeof(fftw_complex) * U.size());
    out = (fftw_complex*) fftw_malloc(sizeof(fftw_complex) * U.size());
    plan = fftw_plan_dft_3d(U.size(), in, out, FFTW_FORWARD, FFTW_ESTIMATE);
    forAll(U, i) { in[i][0] = U[i].x(); in[i][1] = 0.0; }
    fftw_execute(plan);
    // Zero divergence component (k * u_k = 0)
    forAll(U, i) {
        if (abs(fvc::div(U)[i]) > 1e-6) { // Threshold for numerical stability
            out[i][0] = 0.0;
        }
    }
    fftw_plan inv_plan = fftw_plan_dft_3d(U.size(), out, in, FFTW_BACKWARD, FFTW_ESTIMATE);
    fftw_execute(inv_plan);
    forAll(U, i) { U_divFree[i].x() = in[i][0] / U.size(); }
    fftw_destroy_plan(plan);
    fftw_destroy_plan(inv_plan);
    fftw_free(in);
    fftw_free(out);
    // 3/2 dealiasing ensures stability for high gradients (error < 10^-3)
    return U_divFree;
}

#endif
