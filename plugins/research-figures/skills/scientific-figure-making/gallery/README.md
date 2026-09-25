# Figure gallery

These are the plotting scripts behind figures from published papers (Nature Machine
Intelligence, ICML, NeurIPS and others), taken from
[ChenLiu-1996/figures4papers](https://github.com/ChenLiu-1996/figures4papers) and reviewed
and fixed for this skill (see [Changes](#changes-from-upstream)). Use them when a figure
needs a chart type or trick that `pubfig` does not wrap, such as a radar, stacked
composition bars, 3D schematics, an annotated timeline or a table-heatmap. Open the PNG
first to see whether it matches what you need, then read the script.

Each script is self-contained: it has the data inline, uses plain matplotlib, and has a module
docstring that says what to borrow. Run it from any directory:

```bash
python gallery/figure_VIGIL/plot_comparison_radar.py   # -> gallery/figure_VIGIL/figures/comparison_radar.{png,pdf}
```

Requirements: matplotlib ≥ 3.7 and numpy. A few scripts need more:
- scipy: `Cflows/diffusion_swiss_roll.py`, `VIGIL/plot_concept.py`
- seaborn: `ophthal_review/plot_composition.py`
- python-dateutil: `ophthal_review/plot_trend.py`
- a LaTeX install (`text.usetex`): `RNAGenScape/plot_comparison.py` and `plot_sweep.py`; without one they exit with a message.

## Index by chart type

| Need | Script → output | What to borrow |
|------|-----------------|----------------|
| **Per-metric method bars** | [ImmunoStruct/plot_bars.py](figure_ImmunoStruct/plot_bars.py) → `bars_comparison_{IEDB,Cancer}` | One panel per metric, one colour per method, legend in a 4th axis-less panel |
| | [CellSpliceNet/plot_comparison.py](figure_CellSpliceNet/plot_comparison.py) → `comparison_{worm,human}` | SD error bars; blue "ours" vs a fading red ramp; negative values with a zero line |
| | [Cflows/plot_comparison_GeneRegulatory.py](figure_Cflows/plot_comparison_GeneRegulatory.py) | Pastel baselines vs saturated "ours"; mathtext set notation in x labels; 2-column legend panel |
| **Grouped bars** | [Cflows/plot_comparison_Trajectory.py](figure_Cflows/plot_comparison_Trajectory.py) | Groups placed by index offsets with a gap; shared ×10ⁿ offset shown once per axis |
| | [Brainteaser/plot_rewriting.py](figure_Brainteaser/plot_rewriting.py) | Two factors at once (colour = model, hatch = condition) with separate colour/hatch legends |
| **Ablation bars** | [CellSpliceNet/plot_ablation.py](figure_CellSpliceNet/plot_ablation.py) | Dashed full-model baseline, red drop arrows with deltas, in-bar labels that switch white/black |
| | [ImmunoStruct/plot_bars.py](figure_ImmunoStruct/plot_bars.py) → `bars_ablation_*` | Horizontal bars with labels decoded from binary component masks; one-hue tints |
| | [Cflows/plot_comparison_Ablation.py](figure_Cflows/plot_comparison_Ablation.py) | Three tints of one blue; ↑/↓ "better" arrows in the y labels |
| **Stacked / composition bars** | [Brainteaser/plot_brute_force.py](figure_Brainteaser/plot_brute_force.py) | 100 % stacked bars, colour = model and hatch = segment, outlined value labels, row labels |
| **Small multiples** | [Brainteaser/plot_correctness_by_category.py](figure_Brainteaser/plot_correctness_by_category.py), [by_subcategory](figure_Brainteaser/plot_correctness_by_subcategory.py) | 2-row grids with a legend in the free cells; colour families for model families |
| | [Brainteaser/plot_selfcorrection_math.py](figure_Brainteaser/plot_selfcorrection_math.py) | ↑/↓ arrows in panel titles; legend spanning two empty cells |
| **Line plots** | [VIGIL/plot_ablation.py](figure_VIGIL/plot_ablation.py) | Evenly spaced x for uneven settings; labelled guide line; twin-axis panel in one hue at two lightnesses |
| | [VIGIL/plot_posttraining.py](figure_VIGIL/plot_posttraining.py) | Lines that fade in along x; hand-built legend entries |
| | [RNAGenScape/plot_sweep.py](figure_RNAGenScape/plot_sweep.py) | Two panels over uneven step counts, "better" arrow in the label, 0–100 axis |
| **Timeline / cumulative area** | [ophthal_review/plot_trend.py](figure_ophthal_review/plot_trend.py) | Overlaid cumulative areas, release-event arrows raised to avoid collisions, hatch fills without outlines |
| **Radar** | [VIGIL/plot_comparison_radar.py](figure_VIGIL/plot_comparison_radar.py) | Hand-built 12-spoke radar, per-benchmark offset with equal ring spacing, upright ring labels |
| **Heatmaps / tables** | [ophthal_review/plot_composition.py](figure_ophthal_review/plot_composition.py) | Annotated count heatmap, totals in tick labels, grouped rows with separators and rotated group names |
| | [RNAGenScape/plot_comparison.py](figure_RNAGenScape/plot_comparison.py) → `results_comparison_optimization` | Table-heatmap with per-column, direction-aware colour scales and an "Improvement" row |
| | [Cflows/diffusion_swiss_roll.py](figure_Cflows/diffusion_swiss_roll.py) | Kernel heatmap sorted by a latent coordinate beside a weighted graph (one `LineCollection`) |
| **Single-value bars** | [RNAGenScape/plot_comparison.py](figure_RNAGenScape/plot_comparison.py) → `results_comparison_speed` | Legend instead of x ticks, `bar_label` values, zero baseline |
| **3D surfaces** | [RNAGenScape/plot_manifold.py](figure_RNAGenScape/plot_manifold.py), [plot_hole_manifold.py](figure_RNAGenScape/plot_hole_manifold.py) | Clean surface schematic (panes and ticks stripped); per-face masking for holes |
| **Sphere schematics** | [Dispersion/plot_idea.py](figure_Dispersion/plot_idea.py) | Fake 3D shaded spheres via `imshow` with points and dashed spokes |
| | [Dispersion/plot_illustration.py](figure_Dispersion/plot_illustration.py) | Great-circle arcs, shaded sphere and ellipsoid, a 3D arrow class, legends aligned across panels |
| **Concept sketch** | [VIGIL/plot_concept.py](figure_VIGIL/plot_concept.py) | Filled densities with a double-headed gap arrow; contour "manifolds" with a blended path |

`assets/` holds the upstream README's showcase images (paper schematics and teasers). No
script here produces them.

## Adapting a script

These figures are drawn on very large canvases (for example `figsize=(28, 6)` with 24 pt
text) and scaled down in the paper. To reuse one:

1. Keep the plotting logic you need and drop its rcParams block. Call
   `apply_publication_style("paper")` instead, or `"poster"` if it really is printed that large.
2. Replace `figsize` with `figsize(venue, span, aspect)`. If the layout depends on the
   original's aspect ratio, keep that ratio.
3. Map its hex colours to `PALETTE` keys (they are the same values) and to the colour roles in
   SKILL.md.
4. Save with `finalize_figure` so the checks run.

## Data caveats found in review

These are left as in the source, and marked in comments. Check them before you reuse the
numbers:

- **ImmunoStruct:** the Mean PPVn error bars are SEM (std/√5), while the other metrics show SD.
- **Brainteaser self-correction:** some per-model counts don't add up to the stated 14.
- **VIGIL radar:** two backbones have identical POPE_Adv scores, which may be a copy-paste slip.

## Changes from upstream

Reviewed 2026-09-25 against upstream commit `3c181f8`. Every script:

- runs from any directory;
- saves both PNG and PDF, with TrueType fonts embedded;
- uses a font fallback list;
- produces no deprecation warnings;
- has a module docstring.

Fixes that change what the figure shows:

- **ophthal_review trend:** Bard and GPT-4V release markers were silently dropped (a duplicate dict key and a month key without its leading zero).
- **VIGIL ablation:** a line was drawn twice with a duplicated legend.
- **VIGIL radar:** the rings were irregular and unlabelled.
- **Bar charts:**
  - Truncated bar axes in ImmunoStruct now start at zero.
  - RNAGenScape speed bars are on a linear zero-based axis instead of log.
  - Cflows now uses consistent tick formats.
  - CellSpliceNet prints "0.00" instead of "−0.00".
- **Row labels:** added to the Brainteaser grids and group labels to the ophthal_review heatmap.
- **Removed:** a crashing dead branch in the RNAGenScape comparison script.
- **Reproducibility:** randomness is now seeded (Cflows swiss roll).

Licence: CC BY-NC 4.0 (see the plugin's `LICENSE` and the skill's `NOTICE.md`).
