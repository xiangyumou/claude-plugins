# Style guide

This guide covers the reasoning behind the rules in SKILL.md and the patterns to reach for.
It is based on the figures4papers scripts (see [the gallery](../gallery/README.md)), with corrections for
print sizing, accessibility and honest encoding.

## 1. Pick the chart for the comparison

| Question the figure answers | Chart | Helper |
|---|---|---|
| Which method wins on each metric? | One panel per metric, one bar per method, shared legend | `make_method_bars` |
| How do methods compare across datasets/conditions? | Grouped bars | `make_grouped_bar` |
| What does each component contribute? | Ablation bars: shades of one colour plus hatches | `make_grouped_bar` + `tint` |
| Small differences between high scores (e.g. 91.2 vs 92.0) | Dot plot with CI, or bars of the delta vs baseline | `make_scatter` / `make_grouped_bar` on deltas |
| How does something change over time/steps/size? | Lines with uncertainty bands | `make_trend` |
| How do two variables relate? | Scatter (plus fit line if claimed) | `make_scatter` |
| Pairwise structure (correlation, confusion, attention) | Heatmap | `make_heatmap` |
| Profiles over many metrics, few methods | Radar (figures4papers `figure_VIGIL`); consider grouped bars first, since radar areas mislead | plain matplotlib polar axes |

## 2. Size and typography

- **Design at the printed size.** Typical widths: one column is about 3.3-3.5 in (85-89
  mm), full width about 6.75-7.2 in (174-183 mm), and NeurIPS/ICLR text width is 5.5 in. The
  `figsize()` presets encode these widths.
- **Text:** 7-9 pt in papers (Nature asks for 5-7 pt, and never below 5 pt). Keep panel
  letters about 1.15× the body size and bold. Use one font family throughout.
- **Why not the original 45×12 in canvases?** At 24 pt on a 45 in canvas, scaling the figure
  into a 7 in column leaves about 3.7 pt text. The original look (heavy spines, big type) is
  kept proportionally in the `"poster"` preset and in the paper preset's slightly heavy 1 pt
  spines.
- **Aspect:** 0.3-0.4 for a row of 3-4 metric panels, 0.6-0.8 for a single panel. Wide rows
  read left to right as a narrative, which is the useful part of the original "ultra-wide"
  habit.
- **LaTeX labels:** mathtext (`$\alpha$`) needs no LaTeX install. Set `use_tex=True` only when
  the labels need real LaTeX and it is installed.

## 3. Colour

- **Semantics beat decoration.** The same method gets the same colour in every figure of the
  paper:
  - blue for the proposed method;
  - reds for competing methods;
  - grays for trivial baselines and reference levels;
  - greens for improved variants or positive effects;
  - `highlight` for at most one call-out.
- **Fills vs lines:** the light tones (`green_1`, `red_1`, `neutral`) are fill colours for
  bars with black edges. They are too faint for thin lines, which is why `DEFAULT_COLORS`
  contains only dark tones.
- **Colour-vision deficiency:** red and green are the classic confusable pair. Keep them
  apart in lightness (e.g. `red_strong` vs `green_2`), and always add a second channel:
  linestyle (`-`, `--`, `:`), marker (`o`, `s`, `^`) or hatch (`///`, `xx`, `..`).
- **Ablation shading:** `tint("blue_secondary", a)` with `a` in 0.25 → 1.0 expresses "more
  complete means darker". Tints replace the original alpha shading, which also faded the
  edges and broke EPS export.
- **Colormaps:** use perceptually uniform maps only. Sequential (`magma`, `viridis`) for
  magnitudes; diverging (`RdBu_r`, centred) for signed values. Never `jet` or `rainbow`.

## 4. Layout patterns

- **Shared legend:** a single `add_figure_legend` above the panels. Use it when all panels
  show the same series.
- **Legend-only panel:** an extra axis turned off (`add_legend_panel`). Use it when the legend
  is long or the grid has a free cell.
- **No x tick labels on method bars:** when each bar is a method, the legend names them; the
  panel title names the metric.
- **Panel letters and alignment:** bold a, b, c at the top left of each panel. Use
  `sharey=True` when the units match, so readers can compare heights across panels.
- **Consistency over embellishment:** every panel in a figure shares fonts, spine widths,
  colour roles and y-label style. There are no per-panel special cases.
- **Constrained layout** (the default in `create_subplots`) handles colorbars and outside
  legends. Do not also call `tight_layout`.

## 5. Encodings

**Bars**
- Black edges at the spine width. Bars start at zero.
- Value labels (`annotate=True`) only when exact numbers matter and there are few bars. At
  paper size, a crowded row of labels is worse than none.
- Error bars: say what they are (SD, SEM or 95% CI) and give n in the axis label or caption.
- Hatches for sub-variants so they stay distinct in grayscale.
- Truncating the y-axis makes bar length lie. If the differences are invisible from zero,
  change the chart (dot plot, deltas) instead of the axis.

**Lines**
- 2-4 primary curves per axis, and at most about 6.
- Bands via `fill_between` at alpha 0.15-0.25. With many seeds, show mean ± SD or a 95% CI,
  not every run.
- Markers (with `markevery` on dense data) and line styles as a second channel.
- `tighten_ylim` is appropriate here.

**Scatter**
- Lower the alpha for dense clouds, and use white marker edges to separate overlapping
  points.
- Give a fit line or correlation only if the text makes that claim; report r or R² and n.

**Heatmaps**
- Annotate cells only for small matrices (up to about 10×10).
- Use the matching colormap type (section 3), and label the colorbar with quantity and unit.

**Schematics** (e.g. the shaded spheres in `figure_Dispersion`)
- Turn the axes off, use muted fills and saturated warm arrows for the relation being
  explained.

## 6. Export

| Format | Use | Notes |
|---|---|---|
| PDF | LaTeX papers, most journals | Vector; TrueType fonts embedded (`pdf.fonttype 42`) |
| SVG | Later editing in Illustrator/Inkscape | Text stays editable (`svg.fonttype none`); the editor needs the font installed |
| PNG | Slides, web, previews, the visual check | 300 dpi default, 600 for dense line art |
| TIFF | Journals that ask for raster | 300-600 dpi, check colour mode requirements |
| EPS | Only if required | No transparency: use `tint` colours, avoid alpha bands |

Keep stable basenames (e.g. `figures/fig2_ablation`) and regenerate the figure from the
script rather than editing the exported files by hand.

## 7. Final checklist

- [ ] Drawn at the final width with the right preset; the run prints no `[pubfig] WARNING`
      lines.
- [ ] The PNG was viewed: no clipped or overlapping labels, the legend is off the data, and
      the panel letters are present.
- [ ] Each method has the same colour and role in every figure; a second channel (style,
      marker or hatch) exists.
- [ ] Bars start at zero; error bars and bands are defined (what they are, n).
- [ ] Axis labels have units; the heatmap colormap matches the data (sequential or
      diverging).
- [ ] PDF has embedded TrueType fonts (the default here); the file names are stable.
