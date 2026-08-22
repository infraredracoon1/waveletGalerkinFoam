"""Holographic tensor projection layer for wave mode compression.

Uses tensor holography principle (AdS/CFT-inspired) to project high-dimensional
multi-modal data into lower-dimensional compressed representation while
maintaining physical consistency via holographic bound validation.
"""
import numpy as np
from typing import Dict, Any, Optional, Tuple
from tensor_holo_solver import TensorHoloSolver


class HolographicProjector:
    """Holographic tensor projection engine with rank validation."""

    def __init__(self, tensor_rank: int = 6, max_rank: int = 10):
        """Initialize with target tensor rank and holographic bound."""
        self.tensor_rank = max(2, min(tensor_rank, max_rank))
        self.max_rank = max_rank
        self.solver = TensorHoloSolver()
        self.precomputed_basis = {}

    def reshape_to_tensor(
        self,
        modes: Dict[str, Any],
        fft_mag: np.ndarray,
        n_time_samples: int = 30
    ) -> Tuple[np.ndarray, Dict[str, int]]:
        """
        Reshape multi-modal decomposition into 6D tensor.

        Dimensions:
        0: frequency bins (64)
        1: spherical l modes (0-3, 4 values)
        2: helical m chiral modes (-3 to +3, 7 values)
        3: resonance peaks (up to 5)
        4: backscatter components (magnitude + phase, 2 values)
        5: time history (last N samples)

        Returns: (6D tensor, dimension_dict)
        """
        n_freqs = min(len(fft_mag), 64)
        n_l_modes = 4  # l=0,1,2,3
        n_m_modes = 7  # m=-3,-2,-1,0,+1,+2,+3
        n_resonances = 5  # top 5 peaks
        n_backscatter = 2  # magnitude + phase
        n_time = min(n_time_samples, 30)

        tensor = np.zeros((n_freqs, n_l_modes, n_m_modes, n_resonances, n_backscatter, n_time), dtype=np.float32)

        # Freq dimension: normalized FFT magnitude
        tensor[:, 0, 3, 0, 0, 0] = fft_mag[:n_freqs] / (np.max(fft_mag) + 1e-9)

        # Spherical modes (l dimension)
        spherical = modes.get("spherical", {})
        for l in range(n_l_modes):
            key = f"l{l}"
            if key in spherical:
                mag = spherical[key].get("magnitude", 0.0)
                tensor[:, l, 3, 0, 0, 0] = mag * np.linspace(1, 0.5, n_freqs)

        # Helical modes (m dimension)
        helical = modes.get("helical", {})
        for m_idx, m in enumerate(range(-3, 4)):
            key = f"m{m:+d}"
            if key in helical:
                mag = helical[key].get("magnitude", 0.0)
                tensor[:, 0, m_idx, 0, 0, 0] = mag * np.linspace(1, 0.3, n_freqs)

        # Resonance peaks (resonance dimension)
        resonances = modes.get("resonance", [])
        for res_idx, res in enumerate(resonances[:n_resonances]):
            bin_idx = res.get("bin_index", 0)
            mag = res.get("magnitude", 0.0)
            if bin_idx < n_freqs:
                tensor[bin_idx, 0, 3, res_idx, 0, 0] = mag

        # Backscatter (backscatter dimension)
        backscatter = modes.get("backscatter", {})
        correlation = backscatter.get("correlation", 0.0)
        phase_shift = backscatter.get("phase_shift_rad", 0.0)
        tensor[0, 0, 3, 0, 0, 0] = correlation
        tensor[0, 0, 3, 0, 1, 0] = phase_shift / (2 * np.pi)  # normalize to [0,1]

        # Symmetry (stored in time dimension for projection efficiency)
        symmetry = modes.get("symmetry", {})
        sym_ratio = symmetry.get("symmetric_ratio", 0.5)
        tensor[0, 0, 3, 0, 0, 1] = sym_ratio

        dims = {
            "frequencies": n_freqs,
            "spherical_modes": n_l_modes,
            "helical_modes": n_m_modes,
            "resonances": n_resonances,
            "backscatter_components": n_backscatter,
            "time_history": n_time
        }

        return tensor, dims

    def compute_compression_ratio(self, original_tensor: np.ndarray, tensor_rank: int) -> float:
        """
        Estimate compression ratio for rank-R tensor approximation.
        Full tensor: product of all dims. Rank-R: R * sum(dims).
        """
        full_size = np.prod(original_tensor.shape)
        compressed_size = tensor_rank * sum(original_tensor.shape)
        return float(compressed_size / (full_size + 1e-9))

    def validate_holographic_bounds(self, tensor_rank: int) -> Dict[str, Any]:
        """
        Validate holographic principle bounds.
        Holographic bound: rank ≤ max_rank (typically 10) for stability.
        """
        solver_result = self.solver.solve({"tensor_rank": tensor_rank})
        bound_maintained = solver_result.get("holographic_bound") == "MAINTAINED"

        return {
            "tensor_rank": tensor_rank,
            "holographic_bound": solver_result.get("holographic_bound", "UNKNOWN"),
            "bound_maintained": bound_maintained,
            "status": "✅ Stable" if bound_maintained else "⚠️  Approaching limit" if tensor_rank >= 9 else "🔴 Exceeded"
        }

    def project_modes(
        self,
        modes: Dict[str, Any],
        fft_mag: np.ndarray,
        tensor_rank: Optional[int] = None,
        time_history: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Compute holographic projection of multi-modal data.
        Returns full modes + compressed projection + validation.
        """
        if tensor_rank is None:
            tensor_rank = self.tensor_rank

        # Reshape to 6D tensor
        original_tensor, dims = self.reshape_to_tensor(modes, fft_mag)

        # Validate bounds
        bound_check = self.validate_holographic_bounds(tensor_rank)

        # Compute compression ratio
        compression_ratio = self.compute_compression_ratio(original_tensor, tensor_rank)

        # Simulate rank-R projection via truncated SVD on flattened tensor
        # (In production, use proper Tucker or CP decomposition)
        flat_tensor = original_tensor.reshape(-1)
        u, s, vh = np.linalg.svd(flat_tensor.reshape(1, -1), full_matrices=False)
        compressed_energy = np.sum(s[:min(tensor_rank, len(s))] ** 2) / (np.sum(s ** 2) + 1e-9)

        return {
            "modes": modes,
            "holographic_projection": {
                "tensor_rank": tensor_rank,
                "dimensions": dims,
                "compression_ratio": round(float(compression_ratio), 3),
                "energy_preserved_pct": round(float(compressed_energy * 100), 1),
                "bound_status": bound_check["status"],
                "holographic_bound": bound_check["holographic_bound"],
                "bound_maintained": bound_check["bound_maintained"]
            }
        }


# Global projector instance (singleton for efficiency)
_projector = None


def get_projector(tensor_rank: int = 6) -> HolographicProjector:
    """Get or create global holographic projector."""
    global _projector
    if _projector is None or _projector.tensor_rank != tensor_rank:
        _projector = HolographicProjector(tensor_rank=tensor_rank)
    return _projector


def project_all_modes(
    modes: Dict[str, Any],
    fft_mag: np.ndarray,
    tensor_rank: int = 6
) -> Dict[str, Any]:
    """Convenience function: project modes with holographic bounds validation."""
    projector = get_projector(tensor_rank)
    return projector.project_modes(modes, fft_mag, tensor_rank)
