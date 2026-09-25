r"""Method illustration for the Dispersion paper: four ways to spread embeddings apart.

One row of four schematic panels, each with a one-entry "legend" naming the mechanism:
  1. Dispersion loss   -- three points on a shaded sphere pushed apart along great circles;
  2. Decorrelation     -- points on an anisotropic (blue) ellipsoid mapped radially onto the
                          sphere rim, i.e. whitening the covariance;
  3. l2-repel          -- 3D scatter with pairwise repulsion arrows (gradient of a Gaussian
                          kernel) plus norm-reduction arrows towards the origin;
  4. Orthogonalization -- like panel 1, but only acute angles are pushed apart, the obtuse
                          pair is left alone (dashed teal geodesic).

Source: ChenLiu-1996/figures4papers (CC BY-NC 4.0), figure_Dispersion.

Techniques worth borrowing:
  - fake 3D spheres/ellipsoids on a 2D axis: Lambert-shade analytic surface normals on a
    pixel grid and `imshow` them (`shaded_sphere`); NaN outside the shape + a colormap
    `bad` colour masks the background;
  - great-circle arcs between points on a hemisphere via SLERP, projected to 2D, with
    `FancyArrowPatch` arrowheads at both ends (`draw_geodesic`);
  - `Arrow3D`: a FancyArrowPatch that re-projects itself in `do_3d_projection`, giving
    proper arrowheads on 3D axes (quiver heads look poor at this size);
  - minimal 3D axes: hidden panes/ticks, custom quiver axes and axis letters (`nice_axes`);
  - "legend" entries whose marker is a mathtext arrow (marker=r'$\rightarrow$'), aligned to
    one baseline across panels after layout (`align_legends`).

Run:  python plot_illustration.py   ->  figures/illustration.png, figures/illustration.pdf
"""
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch
from mpl_toolkits.mplot3d import proj3d


EPSILON = 1e-6
OUT_DIR = Path(__file__).resolve().parent / "figures"

RED = '#b64342'       # dispersion arrows / labels
NAVY = '#0c2458'      # embedding points
TEAL = '#42949e'      # "do nothing" geodesic
VIOLET = '#9a4d8e'    # norm-reduction arrows

LABEL_BOX = dict(facecolor="white", alpha=1, edgecolor="none", boxstyle="round,pad=0.2")


def pairwise_sqdist(X: np.ndarray) -> np.ndarray:
    X2 = np.sum(X**2, axis=1, keepdims=True)
    D2 = X2 + X2.T - 2 * (X @ X.T)
    return np.maximum(D2, 0.0)


def safe_scale(V, s=0.6, eps=EPSILON):
    """Normalise rows of V to unit length, then set the length to 1/s."""
    n = np.linalg.norm(V, axis=1, keepdims=True)
    return V / (eps + n) / s


def shaded_sphere(num_points_grid, half_width, ambient, gain=0.9, light_dir=(-0.5, 0.5, 0.8)):
    """Lambert-shaded unit sphere seen from +z on a square grid of side 2*half_width.

    Returns the grid (x, y) and a gray image that is 1 (white) outside the sphere.
    Show it with origin='lower' so +y is up (the default light comes from the top left).
    """
    xs = np.linspace(-half_width, half_width, num_points_grid)
    ys = np.linspace(-half_width, half_width, num_points_grid)
    x, y = np.meshgrid(xs, ys)
    r2 = x**2 + y**2
    mask = r2 <= 1.0
    z = np.zeros_like(x)
    z[mask] = np.sqrt(1.0 - r2[mask])

    # On a unit sphere the surface normal is the position vector itself.
    nx, ny, nz = x.copy(), y.copy(), z.copy()
    norm = np.sqrt(nx**2 + ny**2 + nz**2) + EPSILON
    nx, ny, nz = nx / norm, ny / norm, nz / norm

    light_dir = np.asarray(light_dir, dtype=float)
    light_dir /= np.linalg.norm(light_dir)
    intensity = np.maximum(0.0, nx*light_dir[0] + ny*light_dir[1] + nz*light_dir[2])

    img = np.ones_like(x)
    img[mask] = np.clip(ambient + gain*intensity[mask], 0, 1)
    return x, y, img


def nice_axes(ax, L):
    """Bare 3D axes: three black quiver arrows with letters, no panes/ticks/grid.

    The letters are relabelled for a right-handed view (x towards the viewer, y to the
    right, z up): the arrow labelled "x" points along data -y, "y" along data +x.
    """
    y_scale = 1
    z_scale = 1.2
    ax.quiver(0, 0, 0, 0, -L, 0, color="black", linewidth=2, arrow_length_ratio=0.1)
    ax.quiver(0, 0, 0, y_scale*L, 0, 0, color="black", linewidth=2, arrow_length_ratio=0.1)
    ax.quiver(0, 0, 0, 0, 0, z_scale*L, color="black", linewidth=2, arrow_length_ratio=0.1)
    ax.text(0, -L*1.2, 0, "x", color="black", fontsize=36)
    ax.text(y_scale*L*1.05, -0.2, 0, "y", color="black", fontsize=36)
    ax.text(-0.2, 0, z_scale*L*1.05, "z", color="black", fontsize=36)
    ax.grid(False)
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.pane.set_visible(False)
        axis.line.set_color((1, 1, 1, 0))
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_zticks([])
    return ax


def _to3d_xy(xy):
    """Lift 2D points (seen from +z) onto the upper unit hemisphere."""
    x, y = xy[:, 0], xy[:, 1]
    z = np.sqrt(np.clip(1.0 - x*x - y*y, 0.0, 1.0))
    P = np.stack([x, y, z], axis=1)
    # normalize (robust against tiny numerical drift)
    P /= np.linalg.norm(P, axis=1, keepdims=True) + EPSILON
    return P


def _slerp_arc(p, q, n=200):
    p = p / (np.linalg.norm(p) + EPSILON)
    q = q / (np.linalg.norm(q) + EPSILON)
    dot = np.clip(np.dot(p, q), -1.0, 1.0)
    theta = np.arccos(dot)
    if theta < EPSILON:  # nearly identical points
        return np.repeat(p[None, :], n, axis=0)
    # great-circle via SLERP
    t = np.linspace(0.0, 1.0, n)
    s = np.sin
    arc = (s((1-t)*theta)[:, None]*p + s(t*theta)[:, None]*q) / (s(theta) + EPSILON)
    # normalize for safety
    arc /= np.linalg.norm(arc, axis=1, keepdims=True) + EPSILON
    return arc


def draw_geodesic(ax, a2d, b2d, linestyle='-', draw_arrow=True, alpha=0.8,
                  num_arc_points=300, color='blue', lw=2.0, arrow_scale=30, shorten=0.04):
    """Great-circle arc between two points given in 2D (top view), optionally double-headed.

    `shorten` is the fraction of the arc trimmed at each end so the arc stops short of the
    points; with arrows, the line is trimmed twice as much to leave room for the heads.
    """
    A3, B3 = _to3d_xy(np.array([a2d])), _to3d_xy(np.array([b2d]))
    arc = _slerp_arc(A3[0], B3[0], n=num_arc_points)
    x_full, y_full = arc[:, 0], arc[:, 1]

    if draw_arrow:
        k0 = int(2 * shorten * num_arc_points)
    else:
        k0 = int(shorten * num_arc_points)
    k1 = num_arc_points - k0
    x, y = x_full[k0:k1], y_full[k0:k1]
    ax.plot(x, y, color=color, lw=lw, solid_capstyle='round', alpha=alpha, linestyle=linestyle)

    if draw_arrow:
        # Arrowheads at both ends, pointing outwards along the arc (i.e. "push apart").
        k0 = int(shorten * num_arc_points)
        k1 = num_arc_points - k0
        x, y = x_full[k0:k1], y_full[k0:k1]
        for tail, head in (((x[1], y[1]), (x[0], y[0])), ((x[-2], y[-2]), (x[-1], y[-1]))):
            ax.add_patch(FancyArrowPatch(tail, head, arrowstyle='-|>', color=color,
                                         mutation_scale=arrow_scale, lw=0))
    return ax


class Arrow3D(FancyArrowPatch):
    """2D FancyArrowPatch whose end points are re-projected from 3D at draw time."""

    def __init__(self, xs, ys, zs, *args, **kwargs):
        super().__init__((0, 0), (0, 0), *args, **kwargs)
        self._verts3d = xs, ys, zs

    def do_3d_projection(self, renderer=None):
        xs3d, ys3d, zs3d = self._verts3d
        xs, ys, zs = proj3d.proj_transform(xs3d, ys3d, zs3d, self.axes.get_proj())
        self.set_positions((xs[0], ys[0]), (xs[1], ys[1]))
        return np.min(zs)


def plot_decorrelation(ax):
    num_points_on_ellipsoid = 18
    image_scale = 2

    # Gray unit sphere on a [-2, 2]^2 grid (the ellipsoid below needs the larger canvas).
    x, y, img_s = shaded_sphere(512, image_scale, ambient=0.2)
    ax.imshow(img_s, cmap='gray', origin='lower',
              extent=[-image_scale, image_scale, -image_scale, image_scale],
              vmin=0, vmax=1, alpha=1)

    # Flat ellipsoid (semi-axes a, b, c) rotated by 30 deg in the xy-plane.
    a, b, c = 1.50, 0.60, 0.40
    theta = np.deg2rad(30)
    ct, st = np.cos(theta), np.sin(theta)

    xL = ct*x + st*y          # world -> ellipsoid-local coordinates
    yL = -st*x + ct*y
    vL = (xL/a)**2 + (yL/b)**2
    mask_e = vL <= 1.0
    zL = np.zeros_like(xL)
    zL[mask_e] = c * np.sqrt(1.0 - vL[mask_e])

    # Ellipsoid normal is the gradient (x/a^2, y/b^2, z/c^2); rotate it back to world.
    nxL = xL/(a*a)
    nyL = yL/(b*b)
    nzL = np.zeros_like(zL)
    nzL[mask_e] = zL[mask_e]/(c*c)
    nrm = np.sqrt(nxL**2 + nyL**2 + nzL**2) + EPSILON
    nxL, nyL, nzL = nxL/nrm, nyL/nrm, nzL/nrm
    nxE = ct*nxL - st*nyL
    nyE = st*nxL + ct*nyL
    nzE = nzL

    light_dir = np.array([0.5, 0.5, -0.8])
    light_dir /= np.linalg.norm(light_dir)
    intensity_e = np.maximum(0.0, nxE*light_dir[0] + nyE*light_dir[1] + nzE*light_dir[2])
    img_e = np.full_like(x, np.nan, dtype=float)
    img_e[mask_e] = np.clip(0.5 + 0.9*intensity_e[mask_e], 0, 1)
    # NaN pixels outside the ellipsoid render as white; at alpha=0.4 this also softens the
    # sphere underneath so it matches the lighter spheres of the other panels.
    cmap = cm.Blues.with_extremes(bad="white")
    ax.imshow(img_e, cmap=cmap, origin='lower',
              extent=[-image_scale, image_scale, -image_scale, image_scale],
              vmin=0, vmax=1, alpha=0.4)

    # Pick points on the ellipsoid rim, uniformly in the parametric angle.
    phi = np.linspace(0, 2*np.pi, num_points_on_ellipsoid, endpoint=False)
    xL_rim = a*np.cos(phi)
    yL_rim = b*np.sin(phi)
    zL_rim = np.zeros_like(phi)

    # rotate back to world
    xw = ct*xL_rim - st*yL_rim
    yw = st*xL_rim + ct*yL_rim
    zw = zL_rim
    Pellip = np.stack([xw, yw, zw], axis=1)

    # matching sphere rim points: same world direction in xy, unit radius, z=0
    rxy = np.sqrt(xw**2 + yw**2) + EPSILON
    Psphere = np.stack([xw/rxy, yw/rxy, np.zeros_like(rxy)], axis=1)

    ax.scatter(Pellip[:, 0], Pellip[:, 1], s=80, color=NAVY, alpha=0.5)
    ax.scatter(Psphere[:, 0], Psphere[:, 1], s=80, facecolors=RED, alpha=0.5, linewidths=2)

    for p0, p1 in zip(Pellip, Psphere):
        ax.annotate("", xy=(p1[0], p1[1]), xytext=(p0[0], p0[1]),
                    arrowprops=dict(arrowstyle="->", color=RED, lw=3, mutation_scale=20))

    ax.set_xlim([-1.6, 1.6])
    ax.set_ylim([-2, 1.6])
    ax.set_axis_off()

    arrow_cov = Line2D([], [], color=RED, alpha=0.8,
                       marker=r'$\rightarrow$', linestyle="None", markersize=35, label="Decorrelation")
    ax.legend(handles=[arrow_cov], frameon=False, loc="lower center", fontsize=24, bbox_to_anchor=(0.5, 0.1))
    return ax


def _three_points_on_sphere(ax):
    """Shared base of panels 1 and 4: shaded sphere, three fixed points, spokes to the pole."""
    _, _, img = shaded_sphere(512, 1, ambient=0.3)
    ax.imshow(img, cmap='gray', origin='lower', extent=[-1, 1, -1, 1], vmin=0, vmax=1, alpha=0.5)
    ax.set_ylim([-2.1, 1.5])
    ax.set_axis_off()

    pts = np.array([
        [-0.2, 0.6],
        [0.9, 0.0],
        [-0.75, -0.4],
    ])
    ax.scatter(pts[:, 0], pts[:, 1], s=80, color=NAVY, alpha=0.5)
    for p in pts:
        # Geodesic to the pole (0, 0) projects to a straight dashed "radius".
        draw_geodesic(ax, p, [0, 0], linestyle='--', draw_arrow=False, color='black', lw=1,
                      alpha=0.8, shorten=0)
    return pts


def plot_orthogonalization(ax):
    pts = _three_points_on_sphere(ax)
    # Only the acute pairs are pushed apart; the obtuse pair is left alone.
    draw_geodesic(ax, pts[0], pts[1], color=RED, lw=4)
    draw_geodesic(ax, pts[0], pts[2], color=RED, lw=4)
    draw_geodesic(ax, pts[1], pts[2], linestyle='--', draw_arrow=False, color=TEAL, lw=4, alpha=0.5)

    ax.text(0.45, 0.4, "acute angle,\ndisperse", color=RED, fontsize=24, ha="center", va="center", bbox=LABEL_BOX)
    ax.text(-0.6, 0.15, "acute angle,\ndisperse", color=RED, fontsize=24, ha="center", va="center", bbox=LABEL_BOX)
    ax.text(0.15, -0.36, "obtuse angle,\ndo nothing", color=TEAL, fontsize=24, ha="center", va="center",
            bbox=LABEL_BOX)

    arrow_disp = Line2D([], [], color=RED, alpha=0.8,
                        marker=r'$\leftrightarrow$', linestyle="None", markersize=38, label="Orthogonalization")
    ax.legend(handles=[arrow_disp], frameon=False, loc="lower center", fontsize=24, bbox_to_anchor=(0.5, 0.15))
    return ax


def plot_l2_repel(ax):
    tau = 0.5

    # Hand-placed 3D embeddings (schematic, not data).
    Z = np.array([
        [ 3.0, -3.0, 0.0],
        [ 1.0, -3.0, 0.0],
        [-3.0, -2.0, -1.0],
        [-2.0, -1.0, 1.0],
        [-2.0, -1.0, 4.0],
        [ 0.0, 2.0, 2.0],
        [ 4.0, 0.0, 2.0],
        [ 4.0, -2.0, 0.0],
    ])

    num_points, d = Z.shape

    # Repulsion = negative gradient of sum_j exp(-||z_i - z_j||^2 / (d * tau)) w.r.t. z_i
    # (up to a constant; only the direction is drawn).
    D2 = pairwise_sqdist(Z) / d
    W = np.exp(-D2 / tau)

    G_disp = np.zeros_like(Z)
    for i in range(num_points):
        diff = Z[i] - Z
        G_disp[i] = (2.0 / tau) * (W[i][:, None] * diff).sum(axis=0)

    A_disp = safe_scale(G_disp)
    Vn = -Z / (np.linalg.norm(Z, axis=1, keepdims=True) + EPSILON)   # towards the origin

    ax.view_init(elev=30, azim=-60)
    ax = nice_axes(ax, 6)
    ax.set_xlim([-3, 5])
    ax.set_ylim([-3, 5])
    ax.set_zlim([-6, 4])
    ax.scatter(Z[:, 0], Z[:, 1], Z[:, 2], s=80, color=NAVY, alpha=0.5)

    for i in range(num_points):
        p0 = Z[i]
        p1 = Z[i] + A_disp[i] * 1.25
        arrow = Arrow3D([p0[0], p1[0]], [p0[1], p1[1]], [p0[2], p1[2]],
                        mutation_scale=16, lw=4, arrowstyle='->', color=RED, alpha=0.8)
        ax.add_artist(arrow)

    for i in range(num_points):
        p0 = Z[i]
        p1 = Z[i] + Vn[i] * 1.2
        arrow = Arrow3D([p0[0], p1[0]], [p0[1], p1[1]], [p0[2], p1[2]],
                        mutation_scale=10, lw=3, arrowstyle='->', color=VIOLET, alpha=0.8)
        ax.add_artist(arrow)

    for i in range(num_points):
        ax.plot([Z[i, 0], 0], [Z[i, 1], 0], [Z[i, 2], 0],
                linestyle="--", color="black", linewidth=1, alpha=0.8)

    arrow_disp = Line2D([], [], color=RED, alpha=0.8,
                        marker=r'$\rightarrow$', linestyle="None", markersize=35,
                        label=r"$\ell_2$-repel")
    arrow_norm = Line2D([], [], color=VIOLET, alpha=0.8,
                        marker=r'$\rightarrow$', linestyle="None", markersize=35,
                        label="norm regularization")
    ax.legend(handles=[arrow_disp, arrow_norm], frameon=False, loc="lower center",
              fontsize=24, bbox_to_anchor=(0.5, 0))

    # Colour key above the z-axis (placed above zlim on purpose; 3D text is not clipped).
    ax.text(0.8, 0.0, 8.0, "pairwise dispersion", color=RED, fontsize=24, ha="left", va="center", bbox=LABEL_BOX)
    ax.text(0.8, 0.0, 6.5, "norm reduction", color=VIOLET, fontsize=24, ha="left", va="center", bbox=LABEL_BOX)

    return ax


def plot_angular_spread(ax):
    pts = _three_points_on_sphere(ax)
    # Every pair is pushed apart along its great circle.
    draw_geodesic(ax, pts[0], pts[1], color=RED, lw=4)
    draw_geodesic(ax, pts[0], pts[2], color=RED, lw=4)
    draw_geodesic(ax, pts[1], pts[2], color=RED, lw=4)

    ax.text(0.45, 0.4, "disperse", color=RED, fontsize=24, ha="center", va="center", bbox=LABEL_BOX)
    ax.text(-0.6, 0.15, "disperse", color=RED, fontsize=24, ha="center", va="center", bbox=LABEL_BOX)
    ax.text(0.15, -0.36, "disperse", color=RED, fontsize=24, ha="center", va="center", bbox=LABEL_BOX)

    arrow_disp = Line2D([], [], color=RED, alpha=0.8,
                        marker=r'$\leftrightarrow$', linestyle="None", markersize=38, label="Dispersion loss")
    ax.legend(handles=[arrow_disp], frameon=False, loc="lower center", fontsize=24, bbox_to_anchor=(0.5, 0.145))
    return ax


def align_legends(fig, axes, top):
    """Hang every panel's legend from the same figure height, centred under its panel."""
    for ax in axes:
        pos = ax.get_position()
        leg = ax.get_legend()
        leg.set_loc("upper center")
        leg.set_bbox_to_anchor((pos.x0 + pos.width / 2, top), transform=fig.transFigure)


def main():
    # mathtext (no LaTeX install needed) covers the arrows and \ell_2 used here.
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ["Helvetica", "Arial", "Liberation Sans", "DejaVu Sans"]
    plt.rcParams['pdf.fonttype'] = 42
    plt.rcParams['ps.fonttype'] = 42
    plt.rcParams['svg.fonttype'] = 'none'

    fig = plt.figure(figsize=(24, 8))
    axes = [
        fig.add_subplot(1, 4, 1),
        fig.add_subplot(1, 4, 2),
        fig.add_subplot(1, 4, 3, projection="3d"),
        fig.add_subplot(1, 4, 4),
    ]
    plot_angular_spread(axes[0])
    plot_decorrelation(axes[1])
    plot_l2_repel(axes[2])
    plot_orthogonalization(axes[3])

    OUT_DIR.mkdir(exist_ok=True)
    fig.tight_layout(pad=2)
    align_legends(fig, axes, top=0.29)
    for ext in ("png", "pdf"):
        fig.savefig(OUT_DIR / f"illustration.{ext}", dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    main()
