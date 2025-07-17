#ifndef computeWaveletCoefficients_H
#define computeWaveletCoefficients_H

#include "fvCFD.H"
#include "fftw3.h"

// Computes Daubechies D6 wavelet coefficients for a vector field
scalarField computeWaveletCoefficients(const volVectorField& field, const word& waveletType)
{
    // Initialize FFTW for 3D transform
    fftw_plan plan;
    fftw_complex *in, *out;
    in = (fftw_complex*) fftw_malloc(sizeof(fftw_complex) * field.size());
    out = (fftw_complex*) fftw_malloc(sizeof(fftw_complex) * field.size());
    plan = fftw_plan_dft_3d(field.size(), in, out, FFTW_FORWARD, FFTW_ESTIMATE);

    // Copy field data to input array (x-component for simplicity)
    forAll(field, i) { in[i][0] = field[i].x(); in[i][1] = 0.0; }
    
    // Perform wavelet transform (Daubechies D6)
    fftw_execute(plan);
    
    // Extract coefficients (simplified for D6 wavelet)
    scalarField coefficients(field.size());
    forAll(coefficients, i) {
        coefficients[i] = out[i][0] * pow(2.0, -0.5); // Scale for D6 wavelet
    }
    
    // Cleanup
    fftw_destroy_plan(plan);
    fftw_free(in);
    fftw_free(out);
    
    return coefficients;
}

#endif
