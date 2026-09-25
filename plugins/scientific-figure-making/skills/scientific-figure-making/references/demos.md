# figures4papers demos

The house style comes from the plotting scripts in
[ChenLiu-1996/figures4papers](https://github.com/ChenLiu-1996/figures4papers) (CC BY-NC 4.0).
Browse them when a figure has to match one of these projects closely, or for chart types
that `pubfig` does not wrap (radar, trajectories, schematics). This needs network access;
without it, `scripts/examples.py` and [style-guide.md](style-guide.md) are enough.

| Folder | What to borrow |
|--------|----------------|
| [figure_ImmunoStruct](https://github.com/ChenLiu-1996/figures4papers/tree/main/figure_ImmunoStruct) | Per-metric bar panels, 600 dpi dense bars |
| [figure_CellSpliceNet](https://github.com/ChenLiu-1996/figures4papers/tree/main/figure_CellSpliceNet) | Bar comparison and ablation |
| [figure_Brainteaser](https://github.com/ChenLiu-1996/figures4papers/tree/main/figure_Brainteaser) | Stacked / composition bars |
| [figure_VIGIL](https://github.com/ChenLiu-1996/figures4papers/tree/main/figure_VIGIL) | Radar (polar) comparisons, line plots, concept plots |
| [figure_ophthal_review](https://github.com/ChenLiu-1996/figures4papers/tree/main/figure_ophthal_review) | Trend lines over time |
| [figure_RNAGenScape](https://github.com/ChenLiu-1996/figures4papers/tree/main/figure_RNAGenScape) | Heatmaps |
| [figure_Dispersion](https://github.com/ChenLiu-1996/figures4papers/tree/main/figure_Dispersion) | Shaded-sphere schematics, performance plots |
| [figure_Cflows](https://github.com/ChenLiu-1996/figures4papers/tree/main/figure_Cflows) | Comparison, ablation, trajectory plots |

## Adapting a demo script

The originals draw on very large canvases (for example `figsize=(45, 12)` with 24 pt text
and 36 pt value labels), use `font.family = "helvetica"`, and save with
`tight_layout(pad=2)` at 300 dpi. When you port one:

1. Replace its rcParams block with `apply_publication_style(...)`: `"paper"` for a figure
   that goes into a paper, `"poster"` only if it really is printed that large.
2. Replace `figsize` with `figsize(venue, span, aspect)`. Keep the aspect ratio of the
   original if the layout depends on it.
3. Map its hex colours to `PALETTE` keys (they are the same values) and to the colour roles in
   SKILL.md.
4. Replace alpha-shaded ablations with `tint`, remove y-axis truncation on bars, and save via
   `finalize_figure` so the checks run.
