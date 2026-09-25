"""pubfig: publication-figure helpers for the scientific-figure-making skill.

Copy this file next to the plotting script (e.g. ``figures/pubfig.py``) so the
project stays self-contained, then::

    from pubfig import *

    apply_publication_style("paper")
    fig, axes = create_subplots(1, 3, figsize=figsize("nature", "double", aspect=0.35))
    ...
    finalize_figure(fig, "figures/main_results")   # -> .pdf + .png, prints layout checks

Requires numpy and matplotlib >= 3.7. Full reference: references/api.md.
"""

from __future__ import annotations

import shutil
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from cycler import cycler
from matplotlib import font_manager
from matplotlib.colors import TwoSlopeNorm, to_rgb
from matplotlib.container import BarContainer
from matplotlib.text import Text

__all__ = [
    "PALETTE", "DEFAULT_COLORS", "VENUE_WIDTHS_IN", "PRESETS", "FigureStyle",
    "figsize", "tint", "apply_publication_style", "create_subplots",
    "make_grouped_bar", "make_method_bars", "annotate_bars", "make_trend",
    "make_scatter", "make_heatmap", "add_figure_legend", "add_legend_panel",
    "label_panels", "tighten_ylim", "check_figure", "finalize_figure",
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PALETTE = {
    # Blues: the proposed / key method.
    "blue_main": "#0F4D92",
    "blue_secondary": "#3775BA",
    # Greens: improved variants, positive effects (light -> strong).
    "green_1": "#DDF3DE",
    "green_2": "#AADCA9",
    "green_3": "#8BCF8B",
    # Reds: competing methods, contrasts (light -> strong).
    "red_1": "#F6CFCB",
    "red_2": "#E9A6A1",
    "red_strong": "#B64342",
    # Neutrals: simple baselines, reference levels, background.
    "neutral": "#CFCECE",
    "gray": "#767676",
    "gray_dark": "#4D4D4D",
    "black": "#272727",
    # Accents: extra series and a single call-out.
    "teal": "#42949E",
    "violet": "#9A4D8E",
    "highlight": "#FFD700",
}

# Line/marker cycle: all dark enough to read as thin lines on white, and adjacent
# entries differ in lightness as well as hue (safer for colour-vision deficiency).
DEFAULT_COLORS = [
    PALETTE["blue_main"],
    PALETTE["red_strong"],
    PALETTE["teal"],
    PALETTE["violet"],
    PALETTE["gray_dark"],
    PALETTE["blue_secondary"],
]

# (single column, full text width) in inches. Approximate; confirm against the
# venue's current author guidelines when it matters.
VENUE_WIDTHS_IN = {
    "nature": (89 / 25.4, 183 / 25.4),
    "science": (5.7 / 2.54, 18.4 / 2.54),
    "cell": (85 / 25.4, 174 / 25.4),
    "pnas": (8.7 / 2.54, 17.8 / 2.54),
    "ieee": (3.5, 7.16),
    "acm": (3.33, 7.0),
    "icml": (3.25, 6.75),
    "cvpr": (3.25, 6.875),
    "acl": (3.03, 6.3),
    "neurips": (5.5, 5.5),  # single-column template
    "iclr": (5.5, 5.5),     # single-column template
    "slide": (6.4, 12.0),   # half / most of a 16:9 slide (13.33 in wide)
}


@dataclass(frozen=True)
class FigureStyle:
    """Sizes are in points at the *final* printed size of the figure."""

    font_size: float = 8.0
    axes_linewidth: float = 1.0
    line_width: float = 1.5
    tick_length: float = 3.5
    use_tex: bool = False
    font_family: tuple[str, ...] = ("Arial", "Helvetica", "Liberation Sans", "DejaVu Sans")


PRESETS = {
    # Figure drawn at column / text width; 7-9 pt text as journals require.
    "paper": FigureStyle(),
    # Slides and talks.
    "slide": FigureStyle(font_size=18, axes_linewidth=2.0, line_width=3.0, tick_length=6.0),
    # Posters, and the original figures4papers look (24 pt / 3 pt spines on large canvases).
    "poster": FigureStyle(font_size=24, axes_linewidth=3.0, line_width=4.0, tick_length=8.0),
}

SUPPORTED_FORMATS = {"pdf", "svg", "eps", "png", "jpg", "jpeg", "tif", "tiff"}

# ---------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------


def _color(c):
    """Accept PALETTE keys as well as any matplotlib colour."""
    return PALETTE.get(c, c) if isinstance(c, str) else c


def _colors(colors, n):
    if colors is None:
        return [DEFAULT_COLORS[i % len(DEFAULT_COLORS)] for i in range(n)]
    colors = [_color(c) for c in colors]
    if len(colors) < n:
        raise ValueError(f"need {n} colors, got {len(colors)}")
    return colors


def _as_1d(a, name):
    arr = np.asarray(a, dtype=float)
    if arr.ndim != 1:
        raise ValueError(f"{name} must be 1-D, got shape {arr.shape}")
    return arr


def _as_2d(a, name):
    try:
        arr = np.asarray(a, dtype=float)
    except ValueError as exc:  # ragged input
        raise ValueError(f"{name} must be rectangular (all rows the same length)") from exc
    if arr.ndim == 1:
        arr = arr[None, :]
    if arr.ndim != 2:
        raise ValueError(f"{name} must be 1-D or 2-D, got shape {arr.shape}")
    return arr


def _opt(seq, i):
    return None if seq is None else seq[i]


def figsize(venue="nature", span="double", aspect=0.62, *, width_in=None, width_mm=None,
            height_in=None):
    """Return (width, height) in inches for a figure drawn at its final size.

    span: "single" (one column), "double" (full text width) or a float fraction of
    the full width. aspect = height / width, ignored when height_in is given.
    """
    if width_in is None and width_mm is not None:
        width_in = width_mm / 25.4
    if width_in is None:
        try:
            single, double = VENUE_WIDTHS_IN[venue.lower()]
        except KeyError:
            raise ValueError(f"unknown venue {venue!r}; known: {sorted(VENUE_WIDTHS_IN)}") from None
        if span == "single":
            width_in = single
        elif span == "double":
            width_in = double
        else:
            width_in = double * float(span)
    return (width_in, height_in if height_in is not None else width_in * aspect)


def tint(color, amount):
    """Blend a colour with white: amount=1 -> the colour, 0 -> white.

    Prefer this over alpha for ablation shades: edges stay crisp and the output
    has no transparency (safe for EPS and for overlapping artists).
    """
    rgb = np.array(to_rgb(_color(color)))
    return tuple(1 - amount * (1 - rgb))


# ---------------------------------------------------------------------------
# Style and layout
# ---------------------------------------------------------------------------


def _resolve_font(preferences):
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in preferences:
        if name in installed:
            return name
    return "DejaVu Sans"


def apply_publication_style(style="paper"):
    """Set rcParams for publication figures. `style` is a preset name or FigureStyle.

    Returns the FigureStyle actually applied. Call once, before creating figures.
    """
    if style is None:
        style = "paper"
    if isinstance(style, str):
        style = PRESETS[style]
    fs, lw, tl = style.font_size, style.axes_linewidth, style.tick_length
    use_tex = style.use_tex
    if use_tex and shutil.which("latex") is None:
        warnings.warn("use_tex=True but no `latex` on PATH; falling back to mathtext")
        use_tex = False

    mpl.rcParams.update({
        # Fonts: the first *installed* preference, so matplotlib never silently
        # substitutes and never spams findfont warnings.
        "font.family": "sans-serif",
        "font.sans-serif": [_resolve_font(style.font_family), "DejaVu Sans"],
        "font.size": fs,
        "axes.titlesize": fs,
        "axes.labelsize": fs,
        "xtick.labelsize": fs,
        "ytick.labelsize": fs,
        "legend.fontsize": fs,
        "legend.title_fontsize": fs,
        "figure.titlesize": fs * 1.1,
        "mathtext.default": "regular",
        "text.usetex": use_tex,
        # Axes: open frame, thick-ish spines, outward ticks.
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": lw,
        "axes.labelpad": fs * 0.4,
        "axes.titlepad": fs * 0.6,
        "axes.prop_cycle": cycler(color=DEFAULT_COLORS),
        "axes.axisbelow": True,
        "xtick.major.width": lw,
        "ytick.major.width": lw,
        "xtick.minor.width": lw * 0.75,
        "ytick.minor.width": lw * 0.75,
        "xtick.major.size": tl,
        "ytick.major.size": tl,
        "xtick.minor.size": tl * 0.6,
        "ytick.minor.size": tl * 0.6,
        "lines.linewidth": style.line_width,
        "lines.markersize": style.line_width * 3,
        "errorbar.capsize": tl * 0.8,
        "hatch.linewidth": lw * 0.6,
        "legend.frameon": False,
        "legend.handlelength": 1.6,
        "legend.borderaxespad": 0.3,
        # Output: white background, editable/embeddable text.
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.dpi": 300,
        "pdf.fonttype": 42,  # TrueType, not Type 3 (IEEE/ACM reject Type 3)
        "ps.fonttype": 42,
        "svg.fonttype": "none",
    })
    return style


def create_subplots(nrows=1, ncols=1, figsize=None, *, layout="constrained", **kwargs):
    """plt.subplots with constrained layout.

    Returns (fig, ax) for a 1x1 grid, otherwise (fig, axes) with axes flattened to 1-D.
    """
    fig, axes = plt.subplots(nrows, ncols, figsize=figsize, layout=layout, **kwargs)
    if nrows * ncols == 1:
        return fig, axes
    return fig, np.asarray(axes).ravel()


# ---------------------------------------------------------------------------
# Plot helpers
# ---------------------------------------------------------------------------


def make_grouped_bar(ax, categories, series, labels, *, errors=None, colors=None, hatches=None,
                     ylabel=None, group_width=0.8, edgecolor="black", edge_linewidth=None,
                     annotate=False, fmt="{:.2f}", show_xticks=True):
    """Grouped bars: one group per category, one bar per series.

    series: shape (n_series, n_categories). errors: same shape (symmetric half-widths,
    e.g. SD / SEM / 95% CI - say which in the caption). Returns list of BarContainers.
    """
    values = _as_2d(series, "series")
    n_series, n_cat = values.shape
    if len(categories) != n_cat:
        raise ValueError(f"{len(categories)} categories but series has {n_cat} columns")
    if len(labels) != n_series:
        raise ValueError(f"{len(labels)} labels but {n_series} series")
    err = None
    if errors is not None:
        err = _as_2d(errors, "errors")
        if err.shape != values.shape:
            raise ValueError(f"errors shape {err.shape} != series shape {values.shape}")
    colors = _colors(colors, n_series)
    lw = mpl.rcParams["axes.linewidth"] if edge_linewidth is None else edge_linewidth
    width = group_width / n_series
    x = np.arange(n_cat)
    containers = []
    for i in range(n_series):
        bars = ax.bar(
            x + (i - (n_series - 1) / 2) * width, values[i], width,
            label=labels[i], color=colors[i], edgecolor=edgecolor, linewidth=lw,
            hatch=_opt(hatches, i), yerr=_opt(err, i),
            error_kw={"elinewidth": lw, "capthick": lw, "ecolor": edgecolor},
            zorder=2,
        )
        containers.append(bars)
        if annotate:
            annotate_bars(ax, bars, fmt=fmt)
    if show_xticks:
        ax.set_xticks(x, categories)
    else:
        ax.set_xticks([])
    if ylabel:
        ax.set_ylabel(ylabel)
    return containers


def make_method_bars(ax, values, labels, *, errors=None, colors=None, hatches=None, ylabel=None,
                     title=None, annotate=False, fmt="{:.2f}", **kwargs):
    """One bar per method, no x tick labels (methods identified by the legend).

    The figures4papers per-metric panel: one call per metric axis, then one shared legend.
    """
    values = _as_1d(values, "values")
    err = None if errors is None else [[e] for e in _as_1d(errors, "errors")]
    containers = make_grouped_bar(
        ax, [""], [[v] for v in values], labels, errors=err, colors=colors, hatches=hatches,
        ylabel=ylabel, annotate=annotate, fmt=fmt, show_xticks=False, **kwargs,
    )
    if title:
        ax.set_title(title)
    return containers


def annotate_bars(ax, bars, fmt="{:.2f}", fontsize=None, padding=2):
    """Write each bar's value above it (above the error bar when there is one)."""
    fontsize = mpl.rcParams["font.size"] * 0.85 if fontsize is None else fontsize
    return ax.bar_label(bars, labels=[fmt.format(v) for v in bars.datavalues],
                        padding=padding, fontsize=fontsize)


def _band_limits(y, band):
    if isinstance(band, tuple):
        lo, hi = (np.asarray(b, dtype=float) for b in band)
    else:
        half = np.asarray(band, dtype=float)
        lo, hi = y - half, y + half
    if lo.shape != y.shape or hi.shape != y.shape:
        raise ValueError("each band must match the length of x")
    return lo, hi


def make_trend(ax, x, y_series, labels, *, bands=None, colors=None, linestyles=None, markers=None,
               band_alpha=0.2, xlabel=None, ylabel=None, **line_kw):
    """Several lines against a shared x, with optional uncertainty bands.

    bands: None, or one entry per series. An entry is None, an array (symmetric
    half-width, e.g. SD / SEM / CI half-width) or a tuple (lower, upper).
    Returns list of Line2D.
    """
    x = _as_1d(x, "x")
    ys = _as_2d(y_series, "y_series")
    if ys.shape[1] != len(x):
        raise ValueError(f"each series needs {len(x)} points, got {ys.shape[1]}")
    if len(labels) != len(ys):
        raise ValueError(f"{len(labels)} labels but {len(ys)} series")
    if bands is not None and len(bands) != len(ys):
        raise ValueError(f"{len(bands)} bands but {len(ys)} series")
    colors = _colors(colors, len(ys))
    lines = []
    for i, y in enumerate(ys):
        (line,) = ax.plot(x, y, color=colors[i], linestyle=_opt(linestyles, i) or "-",
                          marker=_opt(markers, i), label=labels[i], zorder=3, **line_kw)
        lines.append(line)
        band = _opt(bands, i)
        if band is not None:
            lo, hi = _band_limits(y, band)
            ax.fill_between(x, lo, hi, color=colors[i], alpha=band_alpha, linewidth=0, zorder=2)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    return lines


def make_scatter(ax, x, y, *, label=None, color=None, size=None, alpha=0.7, marker="o",
                 edgecolor="white", linewidth=None, **kwargs):
    """Single-series scatter. Returns the PathCollection."""
    x, y = _as_1d(x, "x"), _as_1d(y, "y")
    if len(x) != len(y):
        raise ValueError(f"x has {len(x)} points, y has {len(y)}")
    size = mpl.rcParams["lines.markersize"] ** 2 if size is None else size
    linewidth = mpl.rcParams["axes.linewidth"] * 0.4 if linewidth is None else linewidth
    return ax.scatter(x, y, s=size, c=_color(color) or DEFAULT_COLORS[0], alpha=alpha,
                      marker=marker, edgecolors=edgecolor, linewidths=linewidth, label=label,
                      zorder=3, **kwargs)


def make_heatmap(ax, matrix, x_labels=None, y_labels=None, *, cmap=None, center=None, vmin=None,
                 vmax=None, cbar=True, cbar_label=None, annotate=False, fmt="{:.2f}", square=True):
    """Matrix heatmap. Returns (image, colorbar or None).

    Signed data (correlations, differences, log-ratios): pass center=0 for a
    diverging map ("RdBu_r") with limits symmetric about the centre.
    Unsigned data: leave center=None for a sequential map ("magma").
    """
    m = _as_2d(matrix, "matrix")
    norm = None
    if center is not None:
        cmap = cmap or "RdBu_r"
        span = np.nanmax(np.abs(m - center)) or 1.0
        norm = TwoSlopeNorm(vcenter=center,
                            vmin=center - span if vmin is None else vmin,
                            vmax=center + span if vmax is None else vmax)
        vmin = vmax = None
    else:
        cmap = cmap or "magma"
    im = ax.imshow(m, cmap=cmap, norm=norm, vmin=vmin, vmax=vmax,
                   aspect="equal" if square else "auto", interpolation="nearest")
    ax.set_xticks(np.arange(m.shape[1]), x_labels if x_labels is not None else [])
    ax.set_yticks(np.arange(m.shape[0]), y_labels if y_labels is not None else [])
    if x_labels is not None and max((len(str(s)) for s in x_labels), default=0) > 3:
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    cb = None
    if cbar:
        cb = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cb.outline.set_linewidth(mpl.rcParams["axes.linewidth"] * 0.6)
        if cbar_label:
            cb.set_label(cbar_label)
    if annotate:
        fs = mpl.rcParams["font.size"] * 0.8
        for (r, c), v in np.ndenumerate(m):
            if np.isnan(v):
                continue
            rgb = im.cmap(im.norm(v))[:3]
            luminance = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
            ax.text(c, r, fmt.format(v), ha="center", va="center", fontsize=fs,
                    color="white" if luminance < 0.5 else "black")
    return im, cb


# ---------------------------------------------------------------------------
# Legends, labels, limits
# ---------------------------------------------------------------------------


def _collect_handles(axes):
    seen, handles, labels = set(), [], []
    for ax in axes:
        for h, lab in zip(*ax.get_legend_handles_labels()):
            if lab not in seen and not lab.startswith("_"):
                seen.add(lab)
                handles.append(h)
                labels.append(lab)
    return handles, labels


def add_figure_legend(fig, axes=None, *, loc="outside upper center", ncols=None, **kwargs):
    """One legend for the whole figure, outside the data (needs constrained layout).

    Usually the best choice for multi-panel figures sharing the same series.
    """
    handles, labels = _collect_handles(fig.axes if axes is None else axes)
    return fig.legend(handles, labels, loc=loc, ncols=ncols or len(labels), **kwargs)


def add_legend_panel(ax_legend, source_axes=None, *, loc="center", **kwargs):
    """Turn an axis into a legend-only panel (figures4papers pattern)."""
    if source_axes is None:
        source_axes = [a for a in ax_legend.figure.axes if a is not ax_legend]
    handles, labels = _collect_handles(source_axes)
    ax_legend.set_axis_off()
    return ax_legend.legend(handles, labels, loc=loc, **kwargs)


def label_panels(axes, labels="abcdefghijklmnopqrstuvwxyz", *, fontsize=None, weight="bold"):
    """Bold panel letters (a, b, c, ...) at the top-left of each axis."""
    fontsize = mpl.rcParams["font.size"] * 1.15 if fontsize is None else fontsize
    for ax, lab in zip(np.atleast_1d(axes), labels):
        ax.set_title(lab, loc="left", fontsize=fontsize, fontweight=weight)


def tighten_ylim(ax, data, *, margin=0.1, include_zero=False):
    """Fit the y-range to the data so differences are visible.

    Meant for line / dot / box plots. On bar charts a truncated axis exaggerates
    differences (bar length no longer encodes the value), so this warns.
    """
    data = np.asarray(data, dtype=float).ravel()
    lo, hi = np.nanmin(data), np.nanmax(data)
    if include_zero:
        lo, hi = min(lo, 0.0), max(hi, 0.0)
    elif any(isinstance(c, BarContainer) for c in ax.containers) and lo > 0:
        warnings.warn("tighten_ylim on a bar chart truncates the bars; prefer a dot plot, "
                      "include_zero=True, or an explicit axis break", stacklevel=2)
    span = (hi - lo) or abs(hi) or 1.0
    ax.set_ylim(lo - margin * span if lo != 0 or not include_zero else 0, hi + margin * span)


# ---------------------------------------------------------------------------
# Checks and export
# ---------------------------------------------------------------------------


def _drawn_texts(fig):
    """All visible, non-empty Text artists, skipping tick labels outside the view."""
    hidden = set()
    for ax in fig.axes:
        for axis, lim in ((ax.xaxis, ax.get_xlim()), (ax.yaxis, ax.get_ylim())):
            lo, hi = sorted(lim)
            tol = (hi - lo) * 1e-6
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                if not lo - tol <= tick.get_loc() <= hi + tol:
                    hidden.update((id(tick.label1), id(tick.label2)))
    # Text inside 3D axes reports its box at the unprojected position, so it is skipped.
    return [t for t in fig.findobj(Text)
            if t.get_visible() and t.get_text().strip() and id(t) not in hidden
            and getattr(t.axes, "name", "") != "3d"]


def _overlap(a, b, tol=1.0):
    return (min(a.x1, b.x1) - max(a.x0, b.x0) > tol) and (min(a.y1, b.y1) - max(a.y0, b.y0) > tol)


def _inside(box, xy):
    return np.any((xy[:, 0] > box.x0) & (xy[:, 0] < box.x1) & (xy[:, 1] > box.y0) & (xy[:, 1] < box.y1))


def _legend_covers_data(ax, legend, renderer):
    box = legend.get_window_extent(renderer)
    for line in ax.lines:
        xy = line.get_transform().transform(line.get_xydata())
        if len(xy) > 1:  # densify so segments crossing the legend are caught
            t = np.linspace(0, 1, 20)[:, None, None]
            xy = (xy[:-1] * (1 - t) + xy[1:] * t).reshape(-1, 2)
        if _inside(box, xy):
            return True
    for coll in ax.collections:
        offsets = coll.get_offsets()
        if len(offsets) and _inside(box, coll.get_offset_transform().transform(offsets)):
            return True
    return any(_overlap(p.get_window_extent(renderer), box) for p in ax.patches)


def check_figure(fig, min_font_pt=5.0, *, check_clipping=True):
    """Return a list of layout problems: clipped / overlapping / tiny text, legends on data.

    Font sizes are only meaningful if the figure was drawn at its final size.
    check_clipping=False skips the "outside the figure" test (bbox_inches="tight"
    recovers such text; finalize_figure then checks the saved width instead).
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    fig_box = fig.bbox
    issues = []
    texts = _drawn_texts(fig)
    # Text.get_window_extent: for annotations, measure the label only, not the arrow.
    boxes = [Text.get_window_extent(t, renderer) for t in texts]

    small = sorted({round(t.get_fontsize(), 1) for t in texts if t.get_fontsize() < min_font_pt})
    if small:
        issues.append(f"text smaller than {min_font_pt} pt at final size: {small} pt")
    for t, b in zip(texts, boxes):
        outside = (b.x0 < fig_box.x0 - 1 or b.y0 < fig_box.y0 - 1
                   or b.x1 > fig_box.x1 + 1 or b.y1 > fig_box.y1 + 1)
        if check_clipping and outside:
            issues.append(f"text {t.get_text()!r} extends outside the figure")
    overlaps = [(texts[i].get_text(), texts[j].get_text())
                for i in range(len(texts)) for j in range(i + 1, len(texts))
                if _overlap(boxes[i], boxes[j])]
    for a, b in overlaps[:10]:
        issues.append(f"overlapping text: {a!r} and {b!r}")
    if len(overlaps) > 10:
        issues.append(f"... and {len(overlaps) - 10} more overlapping text pairs")
    for i, ax in enumerate(fig.axes):
        legend = ax.get_legend()
        if legend is not None and ax.axison and _legend_covers_data(ax, legend, renderer):
            name = ax.get_title() or ax.get_title(loc="left") or ax.get_ylabel()
            issues.append(f"legend covers data in fig.axes[{i}]" + (f" ({name!r})" if name else ""))
    return issues


def _has_transparency(fig):
    return any(a.get_alpha() is not None and a.get_alpha() < 1
               for a in fig.findobj(lambda o: hasattr(o, "get_alpha")))


def finalize_figure(fig, out_path, formats=None, dpi=300, *, tight=True, pad_inches=0.02,
                    check=True, min_font_pt=5.0, close=True, transparent=False):
    """Check the layout, then save to one or more formats. Returns the saved Paths.

    formats: None -> the extension of out_path if it has a supported one, else pdf + png.
    Problems found by check_figure are printed as "[pubfig] WARNING ..." lines: fix them
    and re-run rather than ignoring them.
    """
    out = Path(out_path)
    ext = out.suffix.lower().lstrip(".")
    if ext in SUPPORTED_FORMATS:
        stem = out.with_suffix("")
        formats = formats or [ext]
    else:
        stem = out
        formats = formats or ["pdf", "png"]
    formats = [f.lower().lstrip(".") for f in formats]
    bad = set(formats) - SUPPORTED_FORMATS
    if bad:
        raise ValueError(f"unsupported formats {sorted(bad)}; use {sorted(SUPPORTED_FORMATS)}")
    stem.parent.mkdir(parents=True, exist_ok=True)

    if fig.get_layout_engine() is None:
        fig.tight_layout()
    if check:
        for issue in check_figure(fig, min_font_pt=min_font_pt, check_clipping=not tight):
            print(f"[pubfig] WARNING {stem.name}: {issue}")
        if "eps" in formats and _has_transparency(fig):
            print(f"[pubfig] WARNING {stem.name}: EPS has no transparency; alpha artists will be "
                  "rasterized or flattened. Use tint() colours or export PDF instead.")

    paths = []
    for fmt in formats:
        path = stem.with_suffix(f".{fmt}")
        fig.savefig(path, dpi=dpi, bbox_inches="tight" if tight else None,
                    pad_inches=pad_inches, transparent=transparent)
        paths.append(path)
    if tight:
        box = fig.get_tightbbox(fig.canvas.get_renderer())
        w, h = box.width + 2 * pad_inches, box.height + 2 * pad_inches
    else:
        w, h = fig.get_size_inches()
    print(f"[pubfig] saved {', '.join(str(p) for p in paths)} ({w:.2f} x {h:.2f} in)")
    design_w = fig.get_size_inches()[0]
    if check and w > design_w * 1.03:
        print(f"[pubfig] WARNING {stem.name}: saved width {w:.2f} in exceeds the designed "
              f"{design_w:.2f} in (text sticks out of the layout); scaled to column width, "
              "all text will shrink. Fix the overflowing labels.")
    if close:
        plt.close(fig)
    return paths
