"""Advanced wave mode decomposition and analysis.

Provides 5 orthogonal decompositions of audio FFT data:
1. Spherical harmonics (monopole, dipole, quadrupole, etc.)
2. Helical chiral modes (azimuthal structure)
3. Resonance detection (spectral peaks with Q factors)
4. Backscatter analysis (pattern correlation)
5. Symmetric/asymmetric mode energy
"""
import math
import numpy as np
from scipy import signal
from typing import Dict, List, Tuple, Any, Optional


def compute_spherical_modes(fft_mag: List[float], fft_phase: Optional[List[float]] = None) -> Dict[str, Any]:
    """
    Decompose FFT into spherical harmonics (l=0,1,2,3 monopole to octupole).
    Uses Legendre polynomial projection to extract angular momentum modes.
    """
    fft_mag = np.asarray(fft_mag, dtype=float)
    if len(fft_mag) < 4:
        return {}

    if fft_phase is None:
        fft_phase = np.zeros_like(fft_mag)
    else:
        fft_phase = np.asarray(fft_phase, dtype=float)

    modes = {}
    n_bins = len(fft_mag)

    for l in range(4):
        if l > n_bins // 2:
            break
        legendre = np.polynomial.legendre.legval(
            2.0 * np.arange(n_bins) / n_bins - 1.0,
            [0.0] * l + [1.0]
        )

        magnitude = float(np.dot(fft_mag, legendre ** 2) / (np.sum(legendre ** 2) + 1e-9))
        phase = float(np.arctan2(
            np.dot(fft_mag * np.sin(fft_phase), legendre),
            np.dot(fft_mag * np.cos(fft_phase), legendre)
        ))

        modes[f"l{l}"] = {
            "magnitude": round(magnitude, 4),
            "phase_rad": round(phase, 4),
            "name": ["monopole", "dipole", "quadrupole", "octupole"][min(l, 3)]
        }

    return modes


def compute_helical_modes(ch1_fft: List[float], ch2_fft: Optional[List[float]] = None) -> Dict[str, Any]:
    """
    Decompose azimuthal (chiral) structure from multi-channel audio.
    If only one channel, use synthetic phase offset for m=±1 modes.
    """
    ch1_fft = np.asarray(ch1_fft, dtype=float)

    if ch2_fft is None:
        ch2_fft = ch1_fft * np.exp(1j * np.pi / 4)  # synthetic 45° phase shift
    else:
        ch2_fft = np.asarray(ch2_fft, dtype=float)

    modes = {}

    for m in range(-3, 4):
        phase_shift = m * np.arange(len(ch1_fft)) * 2 * np.pi / len(ch1_fft)

        ch1_rotated = ch1_fft * np.exp(1j * phase_shift)
        ch2_rotated = ch2_fft * np.exp(1j * phase_shift)

        magnitude = float(np.sqrt(np.mean(np.abs(ch1_rotated) ** 2) + np.mean(np.abs(ch2_rotated) ** 2)))
        correlation = float(np.abs(np.dot(ch1_rotated, ch2_rotated.conj())) / (np.sqrt(np.sum(np.abs(ch1_rotated) ** 2) * np.sum(np.abs(ch2_rotated) ** 2)) + 1e-9))
        helicity = "right" if m > 0 else "left" if m < 0 else "symmetric"

        modes[f"m{m:+d}"] = {
            "magnitude": round(magnitude, 4),
            "correlation": round(correlation, 4),
            "helicity": helicity
        }

    return modes


def detect_resonances(fft_mag: List[float], threshold: float = 0.1, q_min: float = 1.0, q_max: float = 100.0) -> List[Dict[str, Any]]:
    """
    Detect resonance peaks in FFT magnitude with quality factor (Q) computation.
    Q = f_center / bandwidth, where bandwidth is FWHM.
    """
    fft_mag = np.asarray(fft_mag, dtype=float)
    n_bins = len(fft_mag)

    peaks, properties = signal.find_peaks(fft_mag, height=np.max(fft_mag) * threshold, distance=2)

    resonances = []
    for peak_idx in peaks[:5]:
        if peak_idx < 1 or peak_idx >= n_bins - 1:
            continue

        peak_height = fft_mag[peak_idx]
        half_height = peak_height / 2.0

        left_idx = peak_idx
        while left_idx > 0 and fft_mag[left_idx] > half_height:
            left_idx -= 1

        right_idx = peak_idx
        while right_idx < n_bins - 1 and fft_mag[right_idx] > half_height:
            right_idx += 1

        bandwidth = (right_idx - left_idx) if right_idx > left_idx else 1.0
        q_factor = float(peak_idx / (bandwidth + 1e-9)) if bandwidth > 0 else 1.0

        if q_min <= q_factor <= q_max:
            resonances.append({
                "bin_index": int(peak_idx),
                "magnitude": round(float(peak_height), 4),
                "q_factor": round(q_factor, 2),
                "bandwidth": round(float(bandwidth), 2)
            })

    return sorted(resonances, key=lambda x: x["magnitude"], reverse=True)[:5]


def compute_backscatter(fft_mag: List[float], reference_pattern: Optional[List[float]] = None) -> Dict[str, Any]:
    """
    Analyze backscatter (reflection/reverberation) via correlation with reference pattern.
    If no reference, use self-correlation (autocorrelation decay).
    """
    fft_mag = np.asarray(fft_mag, dtype=float)

    if reference_pattern is None:
        reference_pattern = fft_mag
    else:
        reference_pattern = np.asarray(reference_pattern, dtype=float)

    if len(reference_pattern) != len(fft_mag):
        reference_pattern = np.interp(
            np.linspace(0, 1, len(fft_mag)),
            np.linspace(0, 1, len(reference_pattern)),
            reference_pattern
        )

    correlation = float(np.dot(fft_mag, reference_pattern) / (np.sqrt(np.sum(fft_mag ** 2) * np.sum(reference_pattern ** 2)) + 1e-9))

    fft_phase = np.angle(np.fft.rfft(fft_mag))[:len(fft_mag)]
    ref_phase = np.angle(np.fft.rfft(reference_pattern))[:len(reference_pattern)]
    phase_shift = float(np.mean(np.abs(fft_phase - ref_phase[:len(fft_phase)])))

    forward_energy = float(np.sum(fft_mag[:len(fft_mag)//2]))
    backward_energy = float(np.sum(fft_mag[len(fft_mag)//2:]))
    ratio = forward_energy / (backward_energy + 1e-9)

    return {
        "correlation": round(correlation, 4),
        "phase_shift_rad": round(phase_shift, 4),
        "forward_backward_ratio": round(ratio, 2),
        "scattered": "yes" if correlation < 0.8 else "no"
    }


def compute_symmetry_ratio(fft_mag: List[float]) -> Dict[str, Any]:
    """
    Decompose FFT into symmetric (even) and antisymmetric (odd) components.
    Even: cosine terms (real FFT part), Odd: sine terms (imaginary FFT part).
    """
    fft_mag = np.asarray(fft_mag, dtype=float)
    n = len(fft_mag)

    rfft = np.fft.rfft(fft_mag)
    real_part = np.real(rfft)
    imag_part = np.imag(rfft)

    even_energy = float(np.sqrt(np.sum(real_part ** 2)))
    odd_energy = float(np.sqrt(np.sum(imag_part ** 2)))
    total_energy = float(np.sqrt(even_energy ** 2 + odd_energy ** 2))

    ratio = even_energy / (total_energy + 1e-9)

    return {
        "symmetric_energy": round(even_energy, 4),
        "antisymmetric_energy": round(odd_energy, 4),
        "total_energy": round(total_energy, 4),
        "symmetric_ratio": round(ratio, 4),
        "dominant_mode": "symmetric" if ratio > 0.6 else "antisymmetric" if ratio < 0.4 else "mixed"
    }


def analyze_all_modes(fft_mag: List[float], fft_phase: Optional[List[float]] = None, reference_pattern: Optional[List[float]] = None) -> Dict[str, Any]:
    """
    Compute all 5 wave mode decompositions in one call.
    Returns a unified modes dictionary for WebSocket payload.
    """
    return {
        "spherical": compute_spherical_modes(fft_mag, fft_phase),
        "helical": compute_helical_modes(fft_mag),
        "resonance": detect_resonances(fft_mag),
        "backscatter": compute_backscatter(fft_mag, reference_pattern),
        "symmetry": compute_symmetry_ratio(fft_mag)
    }
