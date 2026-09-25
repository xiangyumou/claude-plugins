# Attribution

This skill is adapted from the `scientific-figure-making` skill and the `figure_*` plotting
scripts in [ChenLiu-1996/figures4papers](https://github.com/ChenLiu-1996/figures4papers)
by Chen Liu, licensed under [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/).
The same licence applies to this adaptation; it may not be used for commercial purposes.

Changes from the original (2026-09-25):
- Added a working implementation of the documented API (`scripts/pubfig.py`) and runnable
  recipes (`scripts/examples.py`); the original described the API without code.
- Figures are sized to venue column widths with `paper` / `slide` / `poster` presets instead
  of very large canvases; TrueType font embedding (`pdf.fonttype 42`); fixed font fallback order.
- Automatic layout checks (overlapping / clipped / tiny text, legends over data, EPS alpha).
- Resolved contradictions in colour roles; added guidance on zero-based bars, uncertainty,
  diverging colormaps for signed data, and colour-vision accessibility.
- Merged `design-theory.md`, `common-patterns.md` and `tutorials.md` into `style-guide.md`.
- `gallery/` contains the upstream `figure_*` scripts and `assets/`, reviewed and modified;
  the changes are listed in [gallery/README.md](gallery/README.md#changes-from-upstream).
