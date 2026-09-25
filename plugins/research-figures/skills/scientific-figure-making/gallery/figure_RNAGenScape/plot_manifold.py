"""RNAGenScape: schematic of a smooth property landscape (3D surface).

Illustration for the RNAGenScape paper: the property of interest drawn as a
smooth "landscape" over a 2D latent manifold (a sum of Gaussian bumps),
coloured with a diverging map so high regions read warm and low regions cool.

Techniques worth borrowing
* A clean 3D schematic: ``plot_surface`` with no edges, then hide ticks, panes
  and axis lines so only the surface remains.
* ``set_box_aspect([1, 1, 0.5])`` flattens the relief; ``view_init`` fixes the
  camera, and ``zoom`` (plus ``clip_on=False`` on the surface, because the
  3D axes box is square) trims the empty margin a 3D axes leaves around the plot.
* The same ``function`` is reused by plot_hole_manifold.py, so both schematics
  show the same landscape.

Run:  python plot_manifold.py  ->  figures/manifold.{png,pdf}

Source: ChenLiu-1996/figures4papers (CC BY-NC 4.0).
"""
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

FIG_DIR = Path(__file__).resolve().parent / 'figures'


def function(x, y):
    """Sum of Gaussian bumps (one small dip); the landscape height."""
    z = 0.6 * np.exp(-((x - 1)**2 + (y + 1)**2))
    z += 0.5 * np.exp(-((x - 1)**2 + (y - 4)**2))
    z += 0.3 * np.exp(-((x - 2)**2 + (y - 2)**2))
    z += 0.2 * np.exp(-((x + 3)**2 + (y + 1)**2))
    z += 0.3 * np.exp(-((x + 1)**2 + (y + 1)**2))
    z -= 0.1 * np.exp(-((x + 1)**2 + (y - 2)**2))
    z += 0.3 * np.exp(-((x + 2)**2 + (y - 2)**2))
    z += 0.3 * np.exp(-((x + 2)**2 + (y - 1)**2))
    return z


if __name__ == '__main__':
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'Liberation Sans', 'DejaVu Sans']
    plt.rcParams['pdf.fonttype'] = 42
    plt.rcParams['ps.fonttype'] = 42
    plt.rcParams['svg.fonttype'] = 'none'

    # Generate coordinates
    x = np.linspace(-3, 3, 200)
    y = np.linspace(-3, 3, 200)
    x, y = np.meshgrid(x, y)
    z = function(x, y)

    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(1, 1, 1, projection='3d')

    # Smooth surface: no edges, colour by height.
    ax.plot_surface(
        x, y, z,
        cmap='coolwarm',
        edgecolor='none',
        linewidth=0,
        antialiased=True,
        alpha=0.95,
        clip_on=False,  # the 3D axes box is square; let the zoomed surface overflow it
    )

    # Strip everything but the surface.
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_zticks([])
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.pane.set_visible(False)
        axis.line.set_color((0.0, 0.0, 0.0, 0.0))
    ax.set_box_aspect([1, 1, 0.5], zoom=1.25)
    ax.view_init(elev=20, azim=50)

    # Let the 3D axes fill the canvas (tight_layout cannot trim a 3D axes' margin).
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    FIG_DIR.mkdir(exist_ok=True)
    for ext in ('png', 'pdf'):
        fig.savefig(FIG_DIR / f'manifold.{ext}', dpi=100)
    plt.close(fig)
