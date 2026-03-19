---
description: Generate one or more figures for the paper or a report — enforces the thin-caller pattern where all plot logic lives in vis/plotting.py.
---

# Gen-Figures Workflow

Use this workflow whenever you need to produce `.png` figures for the paper, a report,
or any committed output. Do **not** improvise — follow these steps in order.

## Step 1 — Check `vis/plotting.py` first

Open `project.md` and read the **Plots** section inventory table.  
Find the function that matches the figure you need.

- **Exists?** → go to Step 3.
- **Doesn't exist?** → you must add it to `vis/plotting.py` first (Step 2), then proceed.

**Never write raw `plt.figure()` or `plt.subplots()` in a script or agent_workspace file.**
Use `create_figure()` from `vis/plotting.py` at minimum, and prefer a proper named function.

## Step 2 — Add a missing function to `vis/plotting.py` (if needed)

1. Follow the `create_figure()` style exactly — see existing functions for the pattern.
2. Accept typed result objects (`SweepResult`, `MonteCarloResult`, `pd.DataFrame`) — no raw dicts.
3. Return `matplotlib.Figure` (never call `plt.show()` or `plt.savefig()` inside the function).
4. Add it to the inventory table in `project.md` → Plots section.
5. Run `uv run ruff check . --fix && uv run mypy .` — fix any issues before proceeding.

## Step 3 — Check `scripts/README.md` for an existing script

Open `scripts/README.md`.  
If a script already generates the figures you need (or close to it), **run that script** rather than writing a new one.

```bash
uv run python scripts/<existing_script>.py --out-dir agent_workspace/figures
```

If the existing script's parameters or scenarios need adjustment, edit it in place — don't create a duplicate.

## Step 4 — Write a thin-caller script (if no existing script covers it)

Create a new script in `scripts/` following the naming convention `gen_<section_or_topic>_figs.py`.

The script must follow the **thin-caller pattern**:
- All imports from `vis.plotting`, `services.*`, `schemas.*`
- No matplotlib setup — no `plt.figure()`, `plt.subplots()`, `matplotlib.use()`
- Each figure: call the `vis/plotting.py` function → `fig.savefig(out_dir / "name.png", dpi=150, bbox_inches="tight")`
- Accept `--out-dir` as a CLI argument (default: `agent_workspace/figures`)
- Print progress lines so it's easy to monitor

Minimal template:
```python
"""Generate <topic> figures for the paper.

Thin caller only — all plot logic lives in vis/plotting.py.
Output: agent_workspace/figures/<fig_name>.png

Usage:
    uv run python scripts/gen_<topic>_figs.py [--out-dir PATH]
"""
from __future__ import annotations
import argparse
from pathlib import Path


def main(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    from compute_permit_sim.services.config_manager import load_scenario
    from compute_permit_sim.services.sweep import run_sweep
    from compute_permit_sim.vis.plotting import plot_sweep_curve  # add as needed

    base = load_scenario("basic/<scenario>.json")
    result = run_sweep(base, "audit.base_prob", [...], n_runs=50)
    fig = plot_sweep_curve(result)
    fig.savefig(out_dir / "fig_<name>.png", dpi=150, bbox_inches="tight")
    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=Path("agent_workspace/figures"))
    args = parser.parse_args()
    main(args.out_dir)
```

## Step 5 — Update `scripts/README.md`

After writing or modifying a script, update the index in `scripts/README.md`:

```
| gen_<topic>_figs.py | Generates <figures> for Section X. Scenarios: <...>. |
```

## Step 6 — Run and verify

// turbo
```bash
uv run python scripts/<script_name>.py --out-dir agent_workspace/figures
```

Check that:
- All expected `.png` files are created in `out_dir`
- No matplotlib warnings or errors in output
- Figures look correct (open them and inspect)

## Step 7 — Commit the script

```bash
git add scripts/<script_name>.py scripts/README.md
git commit -m "scripts: add <topic> figure generator"
```
