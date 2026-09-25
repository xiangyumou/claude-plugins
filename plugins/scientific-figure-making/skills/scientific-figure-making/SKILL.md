---
name: scientific-figure-making
description: >-
  Publication-ready matplotlib figures for papers, slides and posters: grouped
  and per-metric bar charts, ablations, training/trend curves with uncertainty
  bands, scatter, heatmaps and multi-panel layouts, in the figures4papers house
  style (blue/green/red semantic palette, open spines, bold panel letters).
  Ships a tested helper module (scripts/pubfig.py) that sizes figures to venue
  column widths, embeds TrueType fonts, exports PDF/SVG/PNG and automatically
  flags overlapping, clipped or too-small text and legends covering data. Use
  when creating, restyling or finalizing matplotlib figures with a publication
  or presentation target. Not for interactive/web plots (Plotly, Altair,
  Bokeh), quick exploratory plots with no publication target, 3D/GIS-first
  work, or Illustrator/Figma layout.
---

# Scientific figure making

## Quick start

Copy `scripts/pubfig.py` (in this skill's folder) into the project, next to the plotting
script (e.g. `figures/pubfig.py`), so the project does not depend on the skill folder. Then:

```python
from pubfig import *

apply_publication_style("paper")                      # "paper" | "slide" | "poster"
fig, axes = create_subplots(1, 3, figsize=figsize("nature", "double", aspect=0.35))
for ax, (metric, vals) in zip(axes, results.items()):
    make_method_bars(ax, vals, methods, errors=sds, colors=method_colors, title=metric)
axes[0].set_ylabel("Score (mean ± SD, n = 5)")
add_figure_legend(fig, axes[:1])
label_panels(axes)
finalize_figure(fig, "figures/main_results")          # -> .pdf + .png, prints warnings
```

`scripts/examples.py` has four complete recipes (per-metric bars, ablation bars, training
curves, correlation heatmap). Start by copying the closest one.

## Workflow

1. **Pin down the target.** Venue, column span (single/double) and output formats decide
   `figsize` and the preset. If they are unknown, use `"paper"`, full text width and
   PDF + PNG, and say what you assumed. Ask only when the answer would change the figure's
   structure (which comparison, how many panels, what the error bars mean).
2. **Draw at final size.** `figsize(venue, span, aspect)` returns the printed size in inches,
   so the font sizes you set are the sizes readers see. Do not draw at 20-45 in wide and let
   LaTeX shrink the figure: 24 pt text becomes 3-4 pt.
3. **Plot with the helpers** (`make_method_bars`, `make_grouped_bar`, `make_trend`,
   `make_scatter`, `make_heatmap`) or plain matplotlib on the same axes. The helpers validate
   shapes and apply the house encodings.
4. **Finalize** with `finalize_figure`. It saves the files and prints `[pubfig] WARNING` lines
   for overlapping, clipped or too-small text, legends covering data, EPS transparency, and a
   saved width that exceeds the designed width.
5. **Look at the PNG.** Open the saved PNG with the image viewer or Read tool and inspect it.
   Fix every warning and anything that looks wrong, then re-run. The figure is not finished
   until the run prints no warnings and the image reads well.

## Rules

- **Sizes at print:** 7-9 pt text for papers (preset `"paper"`), 5 pt absolute minimum.
  Slides use `"slide"` (18 pt). `"poster"` reproduces the original figures4papers weight
  (24 pt, 3 pt spines).
- **Fonts:** Arial, then Helvetica, then Liberation Sans, then DejaVu Sans, choosing the
  first one installed. `pdf.fonttype = 42`: IEEE/ACM reject PDFs with Type 3 fonts, which
  are matplotlib's default.
- **Colour roles** (use the same role for the same method across all figures in a paper):

  | Role | PALETTE keys |
  |------|--------------|
  | Proposed / key method | `blue_main`, `blue_secondary` |
  | Competing methods, contrasts | `red_1`, `red_2`, `red_strong` |
  | Simple baselines, reference, background | `neutral`, `gray`, `gray_dark` |
  | Improved variants, positive effects | `green_1`, `green_2`, `green_3` |
  | Extra series | `teal`, `violet` |
  | One call-out only | `highlight` |

- **Never rely on hue alone.** Pair colours with line styles, markers or hatches so the
  figure survives grayscale printing and colour-vision deficiency.
- **Bars start at zero.** Tighten y-limits (`tighten_ylim`) only for lines, dots and boxes.
  If differences between bars are too small to see, switch to a dot plot, plot the deltas,
  or mark an explicit axis break.
- **Uncertainty:** show error bars or bands whenever there are repeated runs, and state what
  they are in the axis label or caption (SD, SEM or 95% CI, and n).
- **Heatmaps:** signed data (correlations, differences) use `center=0`, a diverging map
  (`RdBu_r`) and symmetric limits. Unsigned data use a sequential map (`magma`/`viridis`).
- **Ablation shades:** use `tint(color, amount)` rather than `alpha`. Tints keep edges crisp
  and survive EPS export.
- **Legends:** one shared legend per figure (`add_figure_legend`, outside the axes) or a
  legend-only panel (`add_legend_panel`). Never place a legend on top of data.
- **Multi-panel figures:** use bold lowercase panel letters (`label_panels`), the same fonts,
  line widths and colour roles in every panel, and shared axes where the units match.
- **Export:** PDF for LaTeX and vector journals, SVG for later editing (text stays
  editable), PNG at 300 dpi (600 for dense line art) for slides and previews. Avoid EPS
  unless the venue requires it.
- **Headless runs:** set `MPLBACKEND=Agg`, or call `matplotlib.use("Agg")` before importing
  pyplot.

## References

| File | Open when |
|------|-----------|
| [references/api.md](references/api.md) | You need exact helper signatures, presets, venue widths, or the checks' behaviour |
| [references/style-guide.md](references/style-guide.md) | Choosing a chart type, layout pattern, bar/line/heatmap encoding, or explaining the rationale |
| [references/demos.md](references/demos.md) | Matching a specific figures4papers figure (radar, trajectories, sphere schematics) |
