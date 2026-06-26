"""Tests for the paper reproduction pipeline.

These guard the contract that every figure and table in the manuscript can be
regenerated from committed configuration: registry entries must point at real
JSON files, and the table exporters must emit the paper's exact schemas.
"""

import json
import math
import os

import pytest

from compute_permit_sim.services import paper_pipeline as pp
from compute_permit_sim.services.config_manager import load_scenario
from compute_permit_sim.services.monte_carlo import run_monte_carlo
from compute_permit_sim.vis.export import (
    _latex_label,
    export_compliance_summary_to_latex,
    export_lever_sensitivity_to_latex,
    export_workload_to_latex,
)

# Figures referenced by the manuscript (sections/4-results.tex + appendices).
PAPER_FIGURES = {
    "fig_compliance_distribution.png",
    "minimal_permit_cap.png",
    "minimal_audit_prob.png",
    "heatmap_minimal.png",
    "strict_fixed_price.png",
    "strict_valuation_max.png",
    "heatmap_strict.png",
    "smart_fixed_price.png",
    "heatmap_smart.png",
    "dynamic_reputation_escalation.png",
    "dynamic_penalty.png",
    "heatmap_dynamic.png",
}


def test_registries_cover_all_paper_figures() -> None:
    generated = (
        set(pp.SWEEP_FIGURES.values())
        | set(pp.GRID_FIGURES.values())
        | {"fig_compliance_distribution.png"}
    )
    missing = PAPER_FIGURES - generated
    assert not missing, f"No committed config generates: {sorted(missing)}"


def test_all_registry_configs_exist_and_parse() -> None:
    for d, registry in (
        (pp._sweep_dir(), pp.SWEEP_FIGURES),
        (pp._grid_dir(), pp.GRID_FIGURES),
    ):
        for filename in registry:
            path = os.path.join(d, filename)
            assert os.path.isfile(path), f"missing config: {path}"
            with open(path, encoding="utf-8") as f:
                cfg = json.load(f)
            # Scenario files must themselves load and validate.
            load_scenario(cfg["scenario_file"])


def test_grid_configs_declare_8x8() -> None:
    for filename in pp.GRID_FIGURES:
        with open(os.path.join(pp._grid_dir(), filename), encoding="utf-8") as f:
            cfg = json.load(f)
        assert cfg["x"]["n_values"] == 8 and cfg["y"]["n_values"] == 8


def test_sweep_values_inclusive_endpoints() -> None:
    values = pp._sweep_values(1.0, 19.0, 1.0)
    assert values[0] == 1.0 and values[-1] == 19.0 and len(values) == 19


def test_linspace_endpoints() -> None:
    values = pp._linspace(0.05, 0.50, 8)
    assert values[0] == 0.05 and values[-1] == 0.50 and len(values) == 8


@pytest.fixture(scope="module")
def mc_results():
    return [
        run_monte_carlo(load_scenario(s), n_runs=3, store_raw=True)
        for s in pp.MC_SCENARIOS
    ]


def test_compliance_summary_schema(mc_results) -> None:
    tex = export_compliance_summary_to_latex(mc_results)
    assert r"\label{tab:compliance-summary}" in tex
    for col in ("Q/N", r"Avg.\ Comp.", "SD", "P10", "P90", "Audit Rate", r"Det.\ Rate"):
        assert col in tex
    # One data row per scenario, each with 7 column separators.
    data_rows = [
        ln for ln in tex.splitlines() if ln.count("&") == 7 and "textbf" not in ln
    ]
    assert len(data_rows) == len(mc_results)


def test_workload_schema(mc_results) -> None:
    tex = export_workload_to_latex(mc_results)
    assert r"\label{tab:audit-burden}" in tex
    data_rows = [
        ln for ln in tex.splitlines() if ln.count("&") == 4 and "textbf" not in ln
    ]
    assert len(data_rows) == len(mc_results)


def test_detection_rate_nan_renders_na(mc_results) -> None:
    smart = mc_results[2]
    if math.isnan(smart.detection_rate_given_audit.mean):
        assert "n/a" in export_compliance_summary_to_latex(mc_results)


def test_violin_requires_raw_seeds() -> None:
    from compute_permit_sim.vis.plotting import plot_compliance_violin

    bare = run_monte_carlo(load_scenario(pp.MC_SCENARIOS[0]), n_runs=2)
    with pytest.raises(ValueError, match="raw_seeds"):
        plot_compliance_violin([bare])


# ---------------------------------------------------------------------------
# Baseline single-lever sensitivity (Section 4 headline)
# ---------------------------------------------------------------------------


def test_baseline_sensitivity_configs_exist_and_parse() -> None:
    base = load_scenario(pp.BASELINE_SCENARIO)
    assert base.market.permit_cap == base.n_agents, "baseline must be universal access"
    assert base.market.fixed_price is not None, "universal access needs a fixed price"
    for filename in pp.BASELINE_SENSITIVITY_SWEEPS:
        path = os.path.join(pp._sweep_dir(), filename)
        assert os.path.isfile(path), f"missing config: {path}"
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
        assert cfg["scenario_file"] == pp.BASELINE_SCENARIO


def test_baseline_lands_mid_band() -> None:
    """The whole point of the constructed baseline: ~50-70% compliance."""
    mc = run_monte_carlo(load_scenario(pp.BASELINE_SCENARIO), n_runs=30)
    assert 0.45 <= mc.avg_compliance.mean <= 0.75, (
        f"baseline compliance {mc.avg_compliance.mean:.3f} left the mid band; "
        "the single-lever experiment needs slope room in both directions"
    )


def test_latex_label_escapes_and_translates() -> None:
    assert _latex_label("Penalty φ (M$)") == r"Penalty $\phi$ (M\$)"
    assert _latex_label("Base Audit Rate π₀") == r"Base Audit Rate $\pi_0$"
    assert _latex_label("Permit Price p̄ (M$)") == r"Permit Price $\bar{p}$ (M\$)"
    assert "−" not in _latex_label("1 − detection")  # minus sign normalised


@pytest.fixture(scope="module")
def lever_sweeps():
    from compute_permit_sim.services.sweep import run_sweep

    base = load_scenario(pp.BASELINE_SCENARIO)
    return [
        run_sweep(
            base,
            "market.fixed_price",
            [80.0, 130.0, 180.0],
            param_label="Permit Price p̄ (M$)",
            n_runs=3,
        ),
        run_sweep(
            base,
            "collateral_amount",
            [0.0, 150.0, 300.0],
            param_label="Collateral K (M$)",
            n_runs=3,
        ),
    ]


def test_lever_sensitivity_table_schema(lever_sweeps) -> None:
    tex = export_lever_sensitivity_to_latex(lever_sweeps, baseline_compliance=0.59)
    assert r"\label{tab:lever-sensitivity}" in tex
    for col in ("Lever", "Range", "Low end", "High end", "Span (pp)"):
        assert col in tex
    # One data row per lever, each with 4 column separators.
    data_rows = [
        ln for ln in tex.splitlines() if ln.count("&") == 4 and "textbf" not in ln
    ]
    assert len(data_rows) == len(lever_sweeps)
    # Labels must be LaTeX-safe: no raw "M$" currency leaking through.
    assert "M$)" not in tex and r"M\$)" in tex


def test_lever_sensitivity_table_sorted_by_span(lever_sweeps) -> None:
    """Price (wide span) must rank above collateral (narrower) in the table."""
    tex = export_lever_sensitivity_to_latex(lever_sweeps, baseline_compliance=0.59)
    rows = [ln for ln in tex.splitlines() if ln.count("&") == 4 and "textbf" not in ln]
    assert "bar{p}" in rows[0], "widest-span lever should be the first data row"


def test_tornado_plot_returns_figure(lever_sweeps) -> None:
    from matplotlib.figure import Figure

    from compute_permit_sim.vis.plotting import plot_lever_tornado

    fig = plot_lever_tornado(lever_sweeps, baseline_compliance=0.59)
    assert isinstance(fig, Figure)


def test_tornado_plot_rejects_non_sweep() -> None:
    from compute_permit_sim.vis.plotting import plot_lever_tornado

    with pytest.raises(TypeError):
        plot_lever_tornado(["not a sweep"], baseline_compliance=0.59)
