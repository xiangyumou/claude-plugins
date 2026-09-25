"""RNAGenScape: smooth manifold vs. manifold with holes (two 3D surfaces).

Schematic for the RNAGenScape paper: the same landscape as plot_manifold.py,
drawn twice side by side. The right copy has 30 gray circular patches
("holes", regions of the manifold with no data) scattered at random, keeping
clear of the global peak.

Techniques worth borrowing
* Per-face colouring: compute RGBA ``facecolors`` from a custom
  ``LinearSegmentedColormap`` yourself, then overwrite the masked cells with
  gray. This recolours arbitrary regions of one surface without splitting it.
* Rejection sampling of non-overlapping disks with a seeded
  ``np.random.default_rng`` so the patch layout is reproducible.
* Thin dark wireframe (``linewidth=0.05``) over a pale sequential map for a
  "mesh" look; ticks, panes and axis lines hidden.

Run:  python plot_hole_manifold.py  ->  figures/manifold_holes.{png,pdf}

Source: ChenLiu-1996/figures4papers (CC BY-NC 4.0).
"""
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

FIG_DIR = Path(__file__).resolve().parent / 'figures'


def function(x, y):
    """Sum of Gaussian bumps (one small dip); same landscape as plot_manifold.py."""
    z = 0.6 * np.exp(-((x - 1)**2 + (y + 1)**2))
    z += 0.5 * np.exp(-((x - 1)**2 + (y - 4)**2))
    z += 0.3 * np.exp(-((x - 2)**2 + (y - 2)**2))
    z += 0.2 * np.exp(-((x + 3)**2 + (y + 1)**2))
    z += 0.3 * np.exp(-((x + 1)**2 + (y + 1)**2))
    z -= 0.1 * np.exp(-((x + 1)**2 + (y - 2)**2))
    z += 0.3 * np.exp(-((x + 2)**2 + (y - 2)**2))
    z += 0.3 * np.exp(-((x + 2)**2 + (y - 1)**2))
    return z


def sample_patch_centers(x, y, avoid, rng, num_patches=30, r=0.3, r_forbid=0.9,
                         max_attempts=5000):
    """Random disk centres of radius r: inside the domain, at least r_forbid from
    `avoid` and at least 1.6 r apart from each other (so disks barely touch)."""
    pad = r + 0.1
    centers = []
    attempts = 0
    while len(centers) < num_patches and attempts < max_attempts:
        attempts += 1
        cx = rng.uniform(x.min() + pad, x.max() - pad)
        cy = rng.uniform(y.min() + pad, y.max() - pad)
        if (cx - avoid[0])**2 + (cy - avoid[1])**2 < r_forbid**2:
            continue
        if all((cx - px)**2 + (cy - py)**2 >= (1.6 * r)**2 for px, py in centers):
            centers.append((cx, cy))
    return centers


if __name__ == '__main__':
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'Liberation Sans', 'DejaVu Sans']
    plt.rcParams['pdf.fonttype'] = 42
    plt.rcParams['ps.fonttype'] = 42
    plt.rcParams['svg.fonttype'] = 'none'

    x = np.linspace(-3, 3, 200)
    y = np.linspace(-3, 3, 200)
    X, Y = np.meshgrid(x, y)
    Z = function(X, Y)

    # Keep the holes away from the global peak.
    peak_i, peak_j = np.unravel_index(np.argmax(Z), Z.shape)
    x_peak, y_peak = X[peak_i, peak_j], Y[peak_i, peak_j]

    r = 0.3
    rng = np.random.default_rng(42)
    centers = sample_patch_centers(x, y, (x_peak, y_peak), rng, r=r)

    mask = np.zeros_like(Z, dtype=bool)
    for cx, cy in centers:
        mask |= (X - cx)**2 + (Y - cy)**2 <= r**2

    cmap = LinearSegmentedColormap.from_list(
        "softgreen", ["#e9f5ec", "#d9f0e1", "#c9e5d3", "#a9cbb8", "#7f9e8a", "#4f5c4f"], N=256
    )

    # Explicit per-vertex colours so the masked region can be painted gray.
    norm = plt.Normalize(Z.min(), Z.max())
    facecolors = cmap(norm(Z))
    facecolors_with_gray = facecolors.copy()
    facecolors_with_gray[mask] = [0.7, 0.7, 0.7, 0.5]

    fig = plt.figure(figsize=(14, 6))
    for i, (fc, title) in enumerate([(facecolors, "Smooth Manifold"),
                                     (facecolors_with_gray, "Manifold with Gray Patches")], 1):
        ax = fig.add_subplot(1, 2, i, projection="3d")
        ax.plot_surface(
            X, Y, Z,
            facecolors=fc,
            rstride=4, cstride=4,  # 50 x 50 faces: visible mesh, small PDF
            linewidth=0.05, edgecolor="k",
            antialiased=True, shade=False, alpha=0.95,
            clip_on=False,  # the 3D axes box is square; let the zoomed surface overflow it
        )
        ax.set_title(title, fontsize=14)
        ax.set_xticks([]); ax.set_yticks([]); ax.set_zticks([])
        for a in (ax.xaxis, ax.yaxis, ax.zaxis):
            a.pane.set_visible(False)
            a.line.set_color((0, 0, 0, 0))
        ax.set_box_aspect([1, 1, 0.5], zoom=1.25)
        ax.view_init(elev=20, azim=50)

    # Let the 3D axes fill the canvas (tight_layout cannot trim a 3D axes' margin).
    fig.subplots_adjust(left=0, right=1, bottom=0, top=0.95, wspace=0)
    FIG_DIR.mkdir(exist_ok=True)
    for ext in ('png', 'pdf'):
        fig.savefig(FIG_DIR / f'manifold_holes.{ext}', dpi=300)
    plt.close(fig)
