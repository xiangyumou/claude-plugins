# pubfig API

Everything here is implemented in [`scripts/pubfig.py`](../scripts/pubfig.py) (numpy +
matplotlib >= 3.7). Colour arguments accept `PALETTE` keys (`"blue_main"`) or any matplotlib
colour. Shape errors raise `ValueError` with the offending sizes.

## Constants

| Name | Content |
|------|---------|
| `PALETTE` | Semantic colours: `blue_main #0F4D92`, `blue_secondary #3775BA`, `green_1/2/3 #DDF3DE #AADCA9 #8BCF8B`, `red_1/2 #F6CFCB #E9A6A1`, `red_strong #B64342`, `neutral #CFCECE`, `gray #767676`, `gray_dark #4D4D4D`, `black #272727`, `teal #42949E`, `violet #9A4D8E`, `highlight #FFD700` |
| `DEFAULT_COLORS` | Line cycle `[blue_main, red_strong, teal, violet, gray_dark, blue_secondary]`: dark enough for thin lines, and neighbours differ in lightness |
| `VENUE_WIDTHS_IN` | `{venue: (single_col_in, full_width_in)}` for `nature, science, cell, pnas, ieee, acm, icml, cvpr, acl, neurips, iclr, slide`. Approximate; check the venue's current author guidelines when it matters |
| `PRESETS` | `"paper"` 8 pt / 1.0 pt spines / 1.5 pt lines; `"slide"` 18 / 2 / 3; `"poster"` 24 / 3 / 4 (the original figures4papers weight) |

## Style and layout

**`FigureStyle(font_size=8, axes_linewidth=1.0, line_width=1.5, tick_length=3.5, use_tex=False, font_family=("Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"))`**
All sizes are in points at the final printed size. A frozen dataclass: derive variants with
`dataclasses.replace(PRESETS["paper"], font_size=7)`.

**`apply_publication_style(style="paper") -> FigureStyle`**
Takes a preset name or a `FigureStyle`. Sets these rcParams:
- Fonts: the first installed font from `font_family`, so there are no silent substitutions
  or findfont warnings. `mathtext.default = "regular"`.
- Axes: top and right spines off, frameless legends, the `DEFAULT_COLORS` cycle, tick sizes
  and widths scaled to the spines.
- Output: `pdf.fonttype = ps.fonttype = 42`, `svg.fonttype = "none"`, `savefig.dpi = 300`,
  white background.

If `use_tex=True` but no `latex` is on PATH, it warns and falls back to mathtext.

**`figsize(venue="nature", span="double", aspect=0.62, *, width_in=None, width_mm=None, height_in=None) -> (w, h)`**
`span` is `"single"`, `"double"` or a fraction of the full width. `aspect` is height /
width. An explicit `width_in` or `width_mm` overrides the venue.

**`create_subplots(nrows=1, ncols=1, figsize=None, *, layout="constrained", **kw)`**
Returns `(fig, ax)` for a 1x1 grid, otherwise `(fig, axes)` with `axes` flattened to 1-D.
Extra keyword arguments go to `plt.subplots` (e.g. `sharey=True`, `width_ratios=[3, 1]`).

**`tint(color, amount) -> rgb`**
Blends the colour with white: `amount=1` gives the colour, `0` gives white. Use it for
ablation shades instead of alpha.

## Plot helpers

**`make_grouped_bar(ax, categories, series, labels, *, errors=None, colors=None, hatches=None, ylabel=None, group_width=0.8, edgecolor="black", edge_linewidth=None, annotate=False, fmt="{:.2f}", show_xticks=True) -> list[BarContainer]`**
- `series` has shape `(n_series, n_categories)`, one row per legend entry.
- `errors` has the same shape and holds symmetric half-widths.
- `hatches` is a per-series list (e.g. `[None, "///"]`).
- Edge width defaults to the spine width.
- `annotate=True` writes values above the bars, or above the error caps when there are
  error bars.

**`make_method_bars(ax, values, labels, *, errors=None, colors=None, hatches=None, ylabel=None, title=None, annotate=False, fmt="{:.2f}", **kw)`**
One bar per method and no x tick labels; the legend identifies the methods. This is the
figures4papers per-metric panel: call it once per metric axis, then add one shared legend.

**`annotate_bars(ax, bars, fmt="{:.2f}", fontsize=None, padding=2)`**
Wraps `ax.bar_label`. Font size defaults to 0.85 × the base size.

**`make_trend(ax, x, y_series, labels, *, bands=None, colors=None, linestyles=None, markers=None, band_alpha=0.2, xlabel=None, ylabel=None, **line_kw) -> list[Line2D]`**
- `bands` holds one entry per series. Each entry is `None`, an array (symmetric
  half-width: SD, SEM or CI half-width) or a tuple `(lower, upper)`.
- Extra keyword arguments go to `ax.plot` (e.g. `markevery=5`).

**`make_scatter(ax, x, y, *, label=None, color=None, size=None, alpha=0.7, marker="o", edgecolor="white", linewidth=None, **kw)`**
A single series. The default size follows `lines.markersize`.

**`make_heatmap(ax, matrix, x_labels=None, y_labels=None, *, cmap=None, center=None, vmin=None, vmax=None, cbar=True, cbar_label=None, annotate=False, fmt="{:.2f}", square=True) -> (image, colorbar)`**
- `center=None` uses a sequential map (`magma` by default).
- `center=<value>` uses a diverging map (`RdBu_r` by default) through `TwoSlopeNorm`. The
  limits are symmetric about the centre unless `vmin`/`vmax` are given.
- Spines and ticks are removed. Long x labels are rotated 45°.
- Annotation text switches between black and white according to cell luminance.

## Legends, labels, limits

- **`add_figure_legend(fig, axes=None, *, loc="outside upper center", ncols=None, **kw)`**:
  one figure-level legend placed outside the axes (needs constrained layout). Entries are
  deduplicated by label. `ncols` defaults to a single row.
- **`add_legend_panel(ax_legend, source_axes=None, *, loc="center", **kw)`**: turns the axis
  off and fills it with the legend (figures4papers pattern).
- **`label_panels(axes, labels="abc…", *, fontsize=None, weight="bold")`**: bold letters at
  the top-left of each axis, drawn as the left-aligned title. They coexist with centred
  titles.
- **`tighten_ylim(ax, data, *, margin=0.1, include_zero=False)`**: fits the y-range to
  `data`. Warns when used on a bar chart without `include_zero=True`.

## Checks and export

**`check_figure(fig, min_font_pt=5.0, *, check_clipping=True) -> list[str]`**
Draws the figure and reports:
- text smaller than `min_font_pt`;
- text outside the figure;
- overlapping text (tick labels, labels, titles, annotations, legend text, colorbar labels;
  tick labels outside the view limits are ignored);
- axes legends that cover line vertices or segments, scatter points or bars.

Legend-only panels (axis off) and figure-level legends are skipped.

**`finalize_figure(fig, out_path, formats=None, dpi=300, *, tight=True, pad_inches=0.02, check=True, min_font_pt=5.0, close=True, transparent=False) -> list[Path]`**
- Formats: `None` uses the extension of `out_path` when it is supported (pdf, svg, eps, png,
  jpg, jpeg, tif, tiff), otherwise PDF + PNG. Unknown formats raise.
- Creates parent directories. Runs `tight_layout` only if the figure has no layout engine.
- With `check=True` it prints:
  - `check_figure` issues. The clipping test is skipped when `tight=True`, because
    `bbox_inches="tight"` recovers overhanging text.
  - An EPS + transparency warning.
  - A warning when the saved width exceeds the designed width by more than 3% (overhanging
    text made the figure grow, so everything shrinks when it is scaled to the column).
- Prints the saved paths and the final size in inches.
