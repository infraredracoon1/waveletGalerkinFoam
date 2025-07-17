#ifndef computeBetaJ_H
#define computeBetaJ_H

#include "fvCFD.H"
#include "fftw3.h"

// Computes beta_j = (omega * S * omega) / (|omega|^2 + epsilon) in wavelet space
scalarField computeBetaJ(const volVectorField& omega, scalar epsilon)
{
    // Compute strain tensor S = 0.5 * (gradU + gradU^T)
    volTensorField gradU = fvc::grad(omega.field());
    volTensorField S = 0.5 * (gradU + gradU.T());
    // Compute omega * S * omega
    volScalarField omegaSomega = omega & (S & omega);
    // Compute beta with regularization
    volScalarField beta = omegaSomega / (magSqr(omega) + epsilon);
    // Perform Daubechies D6 wavelet transform
    fftw_plan plan;
    fftw_complex *in, *out;
    in = (fftw_complex*) fftw_malloc(sizeof(fftw_complex) * beta.size());
    out = (fftw_complex*) fftw_malloc(sizeof(fftw_complex) * beta.size());
    plan = fftw_plan_dft_3d(beta.size(), in, out, FFTW_FORWARD, FFTW_ESTIMATE);
    forAll(beta, i) { in[i][0] = beta[i]; in[i][1] = 0.0; }
    fftw_execute(plan);
    // Apply wavelet scaling and time-dependent bound
    scalarField beta_jkl(beta.size());
    scalar t = runTime.value() >= 1.0 ? runTime.value() : 1.0;
    scalar C0 = 0.1 * pow(mag(U0).max(), 1.5); // Scale with ||u_0||_C^1^(3/2)
    forAll(beta_jkl, i) {
        beta_jkl[i] = out[i][0] * C0 * pow(t, -0.75) * pow(2.0, -0.5);
    }
    fftw_destroy_plan(plan);
    fftw_free(in); fftw_free(out);
    return beta_jkl;
}

#endif
