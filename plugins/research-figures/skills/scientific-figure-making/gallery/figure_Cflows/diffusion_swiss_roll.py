"""Diffusion operator on a 2-D Swiss roll: transition matrix (left) and graph (right).

Schematic from the Cflows project (ChenLiu-1996/figures4papers). A noisy 2-D Swiss
roll is sampled, a Gaussian-kernel transition matrix P is built (rows sum to 1), and
the same P is shown two ways:
  - left:  P as a heatmap, with points ordered by the manifold coordinate t, so the
           manifold structure shows up as a band along the diagonal;
  - right: the point cloud coloured by t (viridis), with an edge between every pair
           whose transition probability exceeds a threshold and edge opacity equal
           to (twice) that probability.

Techniques worth borrowing:
  - reorder a kernel/affinity matrix by a latent coordinate before `imshow` so its
    structure is visible;
  - draw thousands of weighted edges as ONE `LineCollection` with per-segment RGBA
    colours (fast, small PDF) instead of one `ax.plot` call per edge;
  - white marker edges + alpha to separate overlapping scatter points;
  - axes turned off for a schematic panel.

The data are random but seeded (SEED), so the figure is reproducible.

Run:  python diffusion_swiss_roll.py  ->  figures/diffusion_swiss_roll.{png,pdf}
"""
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from scipy.spatial.distance import pdist, squareform

SEED = 0
FIG_DIR = Path(__file__).resolve().parent / 'figures'


def generate_swiss_roll_2d(n_samples=80, noise=0.1, rng=None):
    """Sample a noisy 2-D Swiss roll; returns coordinates (x, z) and manifold coordinate t."""
    rng = np.random.default_rng() if rng is None else rng
    t = 1.5 * np.pi * (1 + 2 * rng.random(n_samples))
    x = t * np.cos(t) + noise * rng.standard_normal(n_samples)
    z = t * np.sin(t) + noise * rng.standard_normal(n_samples)
    return x, z, t


def compute_diffusion_matrix(x, z, t, sigma=1.0):
    """Row-stochastic Gaussian-kernel transition matrix, with points sorted by t.

    Returns P (in sorted order) and `sorted_indices`, where sorted position k holds
    original point sorted_indices[k].
    """
    sorted_indices = np.argsort(t)
    points = np.column_stack([x[sorted_indices], z[sorted_indices]])
    t_sorted = t[sorted_indices]

    # Ambient (Euclidean) distance plus a manifold term along t, which keeps
    # neighbouring arms of the roll from being connected.
    distances = squareform(pdist(points))
    t_distances = np.abs(t_sorted[:, None] - t_sorted[None, :])
    combined_distances = distances + 0.5 * t_distances

    P = np.exp(-combined_distances**2 / (2 * sigma**2))
    P[P < 0.01] = 0  # sparsify

    # Normalize rows to make it a proper transition matrix
    row_sums = P.sum(axis=1)
    row_sums[row_sums == 0] = 1  # avoid division by zero
    P = P / row_sums[:, None]

    return P, sorted_indices


if __name__ == '__main__':
    plt.rcParams['pdf.fonttype'] = 42
    plt.rcParams['ps.fonttype'] = 42
    plt.rcParams['svg.fonttype'] = 'none'

    rng = np.random.default_rng(SEED)
    x, z, t = generate_swiss_roll_2d(n_samples=500, noise=0.5, rng=rng)
    P, sorted_indices = compute_diffusion_matrix(x, z, t, sigma=2)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

    # Left: transition matrix, rows/columns ordered by t. The colour scale runs to
    # P.max(); an isolated point (few neighbours -> large P) can wash out the band,
    # which is why the seed matters for how this panel looks.
    ax1.imshow(P, cmap='Reds', aspect='equal', origin='upper')
    ax1.axis('off')

    # Right: point cloud in original order. Map P back to the original point order
    # (inverse permutation), symmetrize with max(P_ij, P_ji) and keep strong edges.
    inverse = np.argsort(sorted_indices)
    P_orig = P[np.ix_(inverse, inverse)]
    P_sym = np.maximum(P_orig, P_orig.T)
    threshold = 0.02  # only draw edges above this transition probability
    i_idx, j_idx = np.nonzero(np.triu(P_sym > threshold, k=1))
    prob = P_sym[i_idx, j_idx]

    segments = np.stack([np.column_stack([x[i_idx], z[i_idx]]),
                         np.column_stack([x[j_idx], z[j_idx]])], axis=1)
    edge_colors = np.zeros((len(prob), 4))            # black ...
    edge_colors[:, 3] = np.clip(prob * 2, 0, 1)       # ... with alpha = 2 * probability
    ax2.add_collection(LineCollection(segments, colors=edge_colors, linewidths=2, zorder=1))

    ax2.scatter(x, z, c=t, cmap='viridis', s=100,
                alpha=0.5, edgecolors='white', linewidth=1, zorder=2)
    ax2.set_aspect('equal')
    ax2.axis('off')

    fig.patch.set_facecolor('white')
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0, wspace=0.02)

    FIG_DIR.mkdir(exist_ok=True)
    for ext in ('png', 'pdf'):
        fig.savefig(FIG_DIR / f'diffusion_swiss_roll.{ext}', dpi=300, bbox_inches='tight',
                    facecolor='white', edgecolor='none', pad_inches=0.2)
    plt.close(fig)
