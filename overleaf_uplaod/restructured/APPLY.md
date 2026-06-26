# Applying the Section 4 restructure to Overleaf

All numbers below are from the committed `Neutral Reference` scenario at the
1D-sweep protocol (**n = 30**), regenerated via the paper pipeline. Figure and
table are in `outputs/paper/figures/fig_lever_sensitivity.png` and
`outputs/paper/tables/lever_sensitivity.tex`.

## Files in this folder
- `4-results.tex` — **replaces** `sections/4-results.tex` wholesale.
- `appendix-e-sensitivity-surfaces.tex` — **new** file → `appendices/`.
- `appendix-d-additions.tex` — a block to **paste into** `appendices/appendix-d-dynamic-scenarios.tex`.

## Steps (in Overleaf)
1. **Upload the new figure.** Put `fig_lever_sensitivity.png` in the project's `figures/`.
2. **Replace `sections/4-results.tex`** with this folder's `4-results.tex`. This already:
   - keeps 4.1 (violin + both outcome tables) verbatim,
   - **cuts** the old `tab:sensitivity_summary` table,
   - inserts the new 4.2 (tornado figure + inline `tab:lever-sensitivity`),
   - rewires 4.3 to cite 4.2.
3. **Add Appendix E.** Upload `appendix-e-sensitivity-surfaces.tex` to `appendices/`, and in `main.tex` add after the appendix-d line (currently line 159):
   ```latex
   \include{appendices/appendix-e-sensitivity-surfaces}
   ```
4. **Move the dynamic block.** Paste the body of `appendix-d-additions.tex` into
   `appendices/appendix-d-dynamic-scenarios.tex`, inside/after the
   "Scenario 4 — Reputation Ratchet" subsection. It keeps `\label{sec:sensitivity_dynamic}`.
5. **Fix the one §3 cross-reference.** In `sections/3-simulation_design.tex`, line ~59:
   - change `appear in Section~\ref{sec:sensitivity_dynamic}`
   - to `appear in Appendix~\ref{sec:sensitivity_dynamic}`
6. **Compile and check the log** for `undefined references`. There should be none
   after step 5 (verified by label scan: nothing outside §4 references the moved
   figures except this one §3 line).

## Notes / judgment calls (not blockers)
- **4.3 tail:** the committed source ended mid-word ("...the regulator sets. T").
  The replacement completes that thought and cites the new lever ranking. If your
  live Overleaf 4.3 is more complete, splice the new citation clause instead of
  replacing the paragraph.
- **§3 framing sentence (optional):** §3 line ~35 says sensitivity analyses perturb
  "one or two parameters from *these* [four] baselines." Still true for the appendix
  surfaces; you may add a half-sentence noting 4.2 sweeps from a separate neutral
  reference. Not required for correctness.
- **§3.5 (optional, style):** the Neutral Reference is a committed config like the
  named scenarios; if you want §3 to own every calibration, add a short
  "Neutral Reference" paragraph there. The construction is currently described in 4.2.

## Two data items to confirm with the group (separate from the restructure)
- **§5, line ~114** asserts penalties lose deterrent effect above **\$120M**. The new
  price sweep (reference \$129, swept 70–190) sits in that region and could
  substantiate/refine it — confirm the number still reflects current data.
- The headline §4.1 numbers (Minimal 34.5%, Strict 88.1%, Smart 100%) were
  re-verified to reproduce exactly on the current commit; no change needed.
