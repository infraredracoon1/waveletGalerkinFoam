#include "fvCFD.H"
#include "fftw3.h"
#include "projectDivergenceFree.H"
#include "computeWaveletCoefficients.H"
#include "computeBetaJ.H"
#include <random>

int main(int argc, char *argv[])
{
    // Initialize OpenFOAM case
    #include "setRootCase.H"
    // Setup simulation
    #include "createTime.H"
    #include "createMesh.H"
    #include "createFields.H"

    // Read Reynolds number and compute viscosity
    scalar Re = readScalar(runTime.controlDict().lookup("Re"));
    scalar nu = 1.0 / Re;
    word caseName = runTime.rootPath().name();
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_real_distribution<> dis(-0.1, 0.1);

    // Apply initial condition
    if (caseName == "turbulentFlow")
    {
        forAll(U, cellI)
        {
            scalar x = mesh.C()[cellI].x(), y = mesh.C()[cellI].y();
            U[cellI].x() = 0.5 * (1.0 - y*y) + dis(gen);
            U[cellI].y() = dis(gen);
            U[cellI].z() = dis(gen);
        }
    }
    else if (caseName == "vortexRing")
    {
        forAll(U, cellI)
        {
            scalar x = mesh.C()[cellI].x(), y = mesh.C()[cellI].y(), z = mesh.C()[cellI].z();
            scalar r = sqrt(x*x + z*z), theta = atan2(z, x);
            scalar Gamma = 1.0, sigma = 0.1;
            U[cellI].x() = 0.0;
            U[cellI].y() = Gamma * exp(-r*r/(sigma*sigma)) * sin(theta);
            U[cellI].z() = Gamma * exp(-r*r/(sigma*sigma)) * cos(theta);
        }
    }
    else if (caseName == "kolmogorovFlow")
    {
        forAll(U, cellI)
        {
            scalar z = mesh.C()[cellI].z();
            U[cellI].x() = sin(2.0 * M_PI * z);
            U[cellI].y() = 0.0;
            U[cellI].z() = 0.0;
        }
    }
    else if (caseName == "oscillatoryFlow")
    {
        forAll(U, cellI)
        {
            scalar x = mesh.C()[cellI].x(), y = mesh.C()[cellI].y();
            U[cellI].x() = sin(10.0 * M_PI * x);
            U[cellI].y() = cos(10.0 * M_PI * y);
            U[cellI].z() = 0.0;
        }
    }
    else if (caseName == "extremeGradientFlow")
    {
        forAll(U, cellI)
        {
            scalar x = mesh.C()[cellI].x(), y = mesh.C()[cellI].y();
            U[cellI].x() = sin(1000.0 * M_PI * x);
            U[cellI].y() = cos(1000.0 * M_PI * y);
            U[cellI].z() = 0.0;
        }
    }
    else if (caseName == "nonPeriodicFlow")
    {
        forAll(U, cellI)
        {
            scalar x = mesh.C()[cellI].x(), y = mesh.C()[cellI].y();
            U[cellI].x() = x / (1.0 + x*x);
            U[cellI].y() = y / (1.0 + y*y);
            U[cellI].z() = 0.0;
        }
    }

    // Main simulation loop
    while (runTime.loop())
    {
        Info << "Time = " << runTime.timeName() << nl << endl;
        // Project to divergence-free space
        U = projectDivergenceFree(U);
        // Compute wavelet coefficients
        scalarField u_jkl = computeWaveletCoefficients(U, "D6");
        // Compute vorticity
        volVectorField omega = fvc::curl(U);
        // Compute epsilon
        scalar epsilon = (runTime.value() >= 1.0) ? sqrt(runTime.value()) : 1.0;
        // Compute beta_j
        scalarField beta_jkl = computeBetaJ(omega, epsilon);
        // PISO solver for pressure-velocity coupling
        #include "pisoLoop.H"
        // Compute BKM integral
        scalar bkm_integral = mag(fvc::curl(U))().weightedAverage(mesh.V()).value();
        Info << "BKM Integral: " << bkm_integral << endl;
        runTime.write();
    }

    runTime.writeFields();
    return 0;
}
