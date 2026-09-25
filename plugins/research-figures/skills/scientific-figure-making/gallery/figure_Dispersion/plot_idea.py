"""Idea sketch for the Dispersion paper: embeddings spread out vs collapsed on a sphere.

Three shaded spheres seen from above, each with 16 points projected onto the upper
hemisphere and dashed "radius" lines to the centre:
  (left)   points spread over the whole sphere (initial state, light fill),
  (middle) points collapsed into a narrow cone of directions (pi/4 wide),
  (right)  points dispersed again over the whole sphere.

Source: ChenLiu-1996/figures4papers (CC BY-NC 4.0), figure_Dispersion.

Techniques worth borrowing:
  - fake 3D shading on a 2D axis: compute the normal of the unit hemisphere on a pixel
    grid, Lambert-shade it against a light direction, and `imshow` it in gray at low
    alpha -- no 3D axes needed, and the result stays crisp and light-weight;
  - uniform-area sampling in a disk (r = sqrt(U)) restricted to an angular window;
  - points drawn above the dashed spokes (zorder) so the markers stay clean.

Run:  python plot_idea.py   ->  figures/idea.png, figures/idea.pdf
"""
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


EPSILON = 1e-6
OUT_DIR = Path(__file__).resolve().parent / "figures"


def sample_points_in_ball(rng, num_points, theta_range=2*np.pi):
    """Uniform points in a disk of radius sqrt(0.95), within an angular window centred on +y."""
    r = np.sqrt(rng.uniform(0, 0.95, num_points))
    theta = rng.uniform(np.pi/2 - theta_range/2, np.pi/2 + theta_range/2, num_points)
    x = r * np.cos(theta)
    y = r * np.sin(theta)
    return np.stack([x, y], axis=1)


def plot_ball_with_points(ax, pts, facecolor):
    num_points_grid = 512

    # Height of the unit hemisphere z = sqrt(1 - x^2 - y^2) on a pixel grid.
    xs = np.linspace(-1, 1, num_points_grid)
    ys = np.linspace(-1, 1, num_points_grid)
    x, y = np.meshgrid(xs, ys)
    r2 = x**2 + y**2
    mask = r2 <= 1.0
    z = np.zeros_like(x)
    z[mask] = np.sqrt(1.0 - r2[mask])

    # On a unit sphere the surface normal is the position vector itself.
    nx, ny, nz = x.copy(), y.copy(), z.copy()
    norm = np.sqrt(nx**2 + ny**2 + nz**2) + EPSILON
    nx, ny, nz = nx / norm, ny / norm, nz / norm

    # Lambert shading, light from top left (origin='lower', so +y is up).
    light_dir = np.array([-0.5, 0.5, 0.8])
    light_dir /= np.linalg.norm(light_dir)
    intensity = np.maximum(0.0, nx*light_dir[0] + ny*light_dir[1] + nz*light_dir[2])
    shade = np.clip(-0.5 + 2.0*intensity, 0, 1)

    img = np.ones((num_points_grid, num_points_grid))  # white outside the disk
    img[mask] = shade[mask]

    ax.imshow(img, cmap='gray', origin='lower', extent=[-1, 1, -1, 1], vmin=0, vmax=1, alpha=0.3)
    ax.set_xlim([-2, 2])
    ax.set_ylim([-2, 2])
    ax.set_axis_off()

    # Points on the sphere, drawn above the dashed spokes to the centre.
    ax.scatter(pts[:, 0], pts[:, 1], s=80, facecolor=facecolor, edgecolor='black', alpha=0.8, zorder=3)
    for i in range(pts.shape[0]):
        ax.plot([pts[i, 0], 0], [pts[i, 1], 0],
                linestyle="--", color="black", linewidth=1, alpha=0.8, zorder=2)

    return ax


def main():
    num_points = 16
    # Legacy-seeded generator: reproduces the exact points of the published figure.
    rng = np.random.RandomState(1)

    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ["Helvetica", "Arial", "Liberation Sans", "DejaVu Sans"]
    plt.rcParams['pdf.fonttype'] = 42
    plt.rcParams['ps.fonttype'] = 42
    plt.rcParams['svg.fonttype'] = 'none'

    fig = plt.figure(figsize=(18, 6))

    ax = fig.add_subplot(1, 3, 1)
    pts = sample_points_in_ball(rng, num_points=num_points)
    plot_ball_with_points(ax, pts, facecolor='#cde5f8')

    ax = fig.add_subplot(1, 3, 2)
    pts = sample_points_in_ball(rng, num_points=num_points, theta_range=np.pi/4)
    plot_ball_with_points(ax, pts, facecolor='#6a98cb')

    ax = fig.add_subplot(1, 3, 3)
    pts = sample_points_in_ball(rng, num_points=num_points)
    plot_ball_with_points(ax, pts, facecolor='#6a98cb')

    OUT_DIR.mkdir(exist_ok=True)
    fig.tight_layout(pad=2)
    for ext in ("png", "pdf"):
        fig.savefig(OUT_DIR / f"idea.{ext}", dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    main()
