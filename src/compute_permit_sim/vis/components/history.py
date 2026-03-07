"""Shared history UI components — used in both Simulate and Batch sidebar tabs.

All three run types (basic SimulationRun, MonteCarloResult, SweepResult) use
identical row layout via RunHistoryItem / BatchHistoryItem and are rendered
together in a single UnifiedHistoryList.

Design principles:
- Selection highlight and link-button styling come from CSS classes
  (``.history-item-selected``, ``.history-link-btn``) — no hex or font-size inline.
- Structural flex properties (flex: 1, gap: ...) remain inline per coding.md rules.
- CSV/Excel/JSON download helpers are shared from results.py.
"""

from __future__ import annotations

import solara
import solara.lab

from compute_permit_sim.schemas import SimulationRun
from compute_permit_sim.schemas.batch import MonteCarloResult, SweepResult
from compute_permit_sim.services.config_manager import save_scenario
from compute_permit_sim.vis.components.dialogs import RunConfigDialog
from compute_permit_sim.vis.components.results import DownloadCSV, DownloadExcel
from compute_permit_sim.vis.export import export_run_to_csv, export_run_to_excel
from compute_permit_sim.vis.state.history import BatchResult, session_history

# ---------------------------------------------------------------------------
# Basic run history (individual SimulationRun items)
# ---------------------------------------------------------------------------


@solara.component
def RunHistoryItem(run: SimulationRun, is_selected: bool) -> None:
    """Basic-run row in the unified history stream.

    Row layout mirrors ``BatchHistoryItem`` exactly:
        type-icon | ⓘ | id-label | save | Excel | CSV | copy-link
    """
    # use_state must be called unconditionally at the top — before any rendering
    show_save, set_show_save = solara.use_state(False)
    save_name, set_save_name = solara.use_state(f"scenario_{run.id}")

    # Derive short display ID from sim_id (preferred) or composite id
    display_id = (
        run.sim_id
        if run.sim_id
        else (run.id.split("_")[1] if "_" in run.id else run.id)
    )

    try:
        parts = run.id.split("_")
        ts_str = f"{parts[0]}-{parts[1]}"
    except IndexError:
        ts_str = "Unknown"

    def view_run() -> None:
        from compute_permit_sim.vis.state.run_state import (  # noqa: PLC0415
            RunState,
            mc_run,
            sweep_run,
        )

        mc_run.set(RunState[MonteCarloResult](phase="idle"))
        sweep_run.set(RunState[SweepResult](phase="idle"))
        session_history.selected_run.value = run

    def perform_save() -> None:
        fname = save_name if save_name.endswith(".json") else f"{save_name}.json"
        save_scenario(run.config, fname)
        set_show_save(False)

    row_classes = ["hover-bg"]
    if is_selected:
        row_classes.append("history-item-selected")

    with solara.Row(style="padding: 2px; align-items: center;", classes=row_classes):
        # Type icon — distinguishes basic runs from MC/Sweep in the unified stream
        solara.Button(
            icon_name="mdi-play-circle-outline", icon=True, small=True, disabled=True
        )
        RunConfigDialog(
            config=run.config,
            title=f"Run: {display_id}",
            subtitle=f"Created: {ts_str}",
            metrics=run.metrics,
        )
        # Short ID label — flex-grow identical to BatchHistoryItem label button
        solara.Button(
            display_id,
            on_click=view_run,
            text=True,
            style="text-transform: none; text-align: left; flex-grow: 1;",
            color="primary" if is_selected else None,
        )
        # Save as scenario template — same dialog as BatchHistoryItem
        with solara.Tooltip("Save as Scenario Template"):
            solara.Button(
                icon_name="mdi-content-save",
                on_click=lambda: set_show_save(True),
                icon=True,
                small=True,
            )
        with solara.v.Dialog(
            v_model=show_save, on_v_model=set_show_save, max_width=400, persistent=False
        ):
            with solara.v.Card(style="overflow: visible;"):
                with solara.v.CardTitle():
                    solara.Text("Save Scenario")
                with solara.v.CardText(style="padding: 16px;"):
                    solara.InputText(
                        label="Filename", value=save_name, on_value=set_save_name
                    )
                with solara.v.CardActions():
                    solara.v.Spacer()
                    solara.Button(
                        "Cancel", on_click=lambda: set_show_save(False), text=True
                    )
                    solara.Button("Save", on_click=perform_save, color="primary")

        # Export actions — matching BatchHistoryItem order (Excel → CSV → copy)
        fname_base = run.sim_id or run.id

        DownloadExcel(
            "Export to Excel",
            lambda: export_run_to_excel(run, output_path=""),
            f"{fname_base}.xlsx",
        )
        DownloadCSV(
            "Export to CSV (Step Data)",
            lambda: export_run_to_csv(run, output_path=""),
            f"{fname_base}.csv",
        )
        # Copy-link button — same mdi-content-copy icon as BatchHistoryItem copy-ID;
        # copies a shareable URL that preloads this exact run via UrlManager.
        url = f"?id={run.url_id}"
        btn_html = (
            f'<button class="history-link-btn" '
            f"onclick=\"navigator.clipboard.writeText(window.location.origin + window.location.pathname + '{url}'); alert('Link copied!');\" "
            f'title="Copy shareable link">'
            f'<i class="mdi mdi-content-copy" style="font-size:20px;"></i>'
            f"</button>"
        )
        solara.HTML(tag="div", unsafe_innerHTML=btn_html)


# ---------------------------------------------------------------------------
# Batch result history (MonteCarloResult / SweepResult items)
# ---------------------------------------------------------------------------


@solara.component
def BatchHistoryItem(result: BatchResult, is_current: bool) -> None:
    """One-line history row for an MC or Sweep batch result.

    Mirrors ``RunHistoryItem`` exactly: type-icon | ⓘ | id-label | save | Excel | CSV | JSON.
    The short ``result.id`` is displayed as the label; full details are in the ⓘ dialog.
    """
    from compute_permit_sim.vis.state.run_state import RunState, mc_run, sweep_run

    if isinstance(result, MonteCarloResult):
        type_icon = "mdi-chart-bell-curve-cumulative"
        dialog_title = f"MC Run: {result.id}"
        batch_summary = (
            f"**{result.n_runs} Monte Carlo runs** · {result.scenario_name}  \n"
            f"Avg compliance: **{result.avg_compliance.mean:.1%}** ±{result.avg_compliance.std:.1%}  \n"
            f"P10–P90: {result.p10_compliance:.0%} – {result.p90_compliance:.0%}"
        )
        safe = result.scenario_name.lower().replace(" ", "_")
        csv_fname = f"mc_{safe}_{result.id}.csv"
        xlsx_fname = f"mc_{safe}_{result.id}.xlsx"

        def view() -> None:
            session_history.selected_run.value = None  # clear basic run highlight
            sweep_run.set(RunState[SweepResult](phase="idle"))
            mc_run.set(RunState[MonteCarloResult](phase="ready", result=result))

        def dl_csv() -> bytes | str:
            from compute_permit_sim.vis.export import (
                export_monte_carlo_to_csv,  # noqa: PLC0415
            )

            return export_monte_carlo_to_csv([result], output_path="")

        def dl_excel() -> bytes | str:
            from compute_permit_sim.vis.export import (
                export_monte_carlo_to_excel,  # noqa: PLC0415
            )

            return export_monte_carlo_to_excel(result, output_path="")

    else:  # SweepResult
        type_icon = "mdi-trending-up"
        dialog_title = f"Sweep Run: {result.id}"
        tp = result.tipping_point()
        tp_str = f"tp≈{tp:.3f}" if tp is not None else "not reached"
        min_v = result.points[0].param_value if result.points else 0.0
        max_v = result.points[-1].param_value if result.points else 0.0
        batch_summary = (
            f"**{len(result.points)}-point sweep** · {result.scenario_name}  \n"
            f"Parameter: **{result.param_label}**  \n"
            f"Range: {min_v:.3f} – {max_v:.3f} | tipping point: {tp_str}"
        )
        safe_p = result.param_path.replace(".", "_")
        safe_s = result.scenario_name.lower().replace(" ", "_")
        csv_fname = f"sweep_{safe_s}_{safe_p}_{result.id}.csv"
        xlsx_fname = f"sweep_{safe_s}_{safe_p}_{result.id}.xlsx"

        def view() -> None:
            session_history.selected_run.value = None  # clear basic run highlight
            mc_run.set(RunState[MonteCarloResult](phase="idle"))
            sweep_run.set(RunState[SweepResult](phase="ready", result=result))

        def dl_csv() -> bytes | str:
            from compute_permit_sim.vis.export import (
                export_sweep_to_csv,  # noqa: PLC0415
            )

            return export_sweep_to_csv(result, output_path="")

        def dl_excel() -> bytes | str:
            from compute_permit_sim.vis.export import (
                export_sweep_to_excel,  # noqa: PLC0415
            )

            return export_sweep_to_excel(result, output_path="")

    # use_state calls must be unconditional (Solara hook rules) — always before any return
    show_save, set_show_save = solara.use_state(False)
    save_name, set_save_name = solara.use_state(f"scenario_{result.id}")

    def perform_save() -> None:
        fname = save_name if save_name.endswith(".json") else f"{save_name}.json"
        save_scenario(result.config, fname)
        set_show_save(False)

    row_classes = ["hover-bg"]
    if is_current:
        row_classes.append("history-item-selected")

    with solara.Row(style="padding: 2px; align-items: center;", classes=row_classes):
        # Small type icon distinguishes MC / Sweep from basic runs
        solara.Button(icon_name=type_icon, icon=True, small=True, disabled=True)
        # Config dialog — same ⓘ button as RunHistoryItem; batch_summary shows type-specific stats
        RunConfigDialog(
            config=result.config,
            title=dialog_title,
            batch_summary=batch_summary,
        )
        # Short ID label - flex-grow lets the download icons stay right-aligned
        solara.Button(
            result.id,
            on_click=view,
            text=True,
            style="text-transform: none; text-align: left; flex-grow: 1;",
            color="primary" if is_current else None,
        )
        # Save base config as scenario template (same dialog as RunHistoryItem)
        with solara.Tooltip("Save base config as Scenario Template"):
            solara.Button(
                icon_name="mdi-content-save",
                on_click=lambda: set_show_save(True),
                icon=True,
                small=True,
            )
        with solara.v.Dialog(
            v_model=show_save,
            on_v_model=set_show_save,
            max_width=400,
            persistent=False,
        ):
            with solara.v.Card(style="overflow: visible;"):
                with solara.v.CardTitle():
                    solara.Text("Save Scenario")
                with solara.v.CardText(style="padding: 16px;"):
                    solara.InputText(
                        label="Filename", value=save_name, on_value=set_save_name
                    )
                with solara.v.CardActions():
                    solara.v.Spacer()
                    solara.Button(
                        "Cancel", on_click=lambda: set_show_save(False), text=True
                    )
                    solara.Button("Save", on_click=perform_save, color="primary")

        # Export actions — matching RunHistoryItem order
        DownloadExcel("Export to Excel", dl_excel, xlsx_fname)
        DownloadCSV("Export to CSV", dl_csv, csv_fname)
        # Copy-ID clipboard button — same pattern as RunHistoryItem copy-link
        result_id = result.id
        btn_html = (
            f'<button class="history-link-btn" '
            f"onclick=\"navigator.clipboard.writeText('{result_id}'); alert('ID copied: {result_id}');\" "
            f'title="Copy run ID">'
            f'<i class="mdi mdi-content-copy" style="font-size:20px;"></i>'
            f"</button>"
        )
        solara.HTML(tag="div", unsafe_innerHTML=btn_html)


@solara.component
def UnifiedHistoryList() -> None:
    """Single, uniformly styled history stream — batch results then basic runs.

    Owns the sole ``run-history-compact`` wrapper so every item type (MC, Sweep,
    basic run) receives identical CSS context. Replaces the paired
    (BatchHistoryList + RunHistoryList) pattern which caused double-nested
    ``run-history-compact`` for batch items and mismatched styling.
    """
    from compute_permit_sim.vis.state.run_state import mc_run, sweep_run

    batch_results = session_history.batch_results.value
    run_history = session_history.run_history.value
    mc_current = mc_run.value.result
    sweep_current = sweep_run.value.result

    # Use Markdown for empty state — matches RunHistoryList convention and avoids
    # alternating root container types (Column A vs Column B) which reacton rejects.
    if not batch_results and not run_history:
        solara.Markdown("_No runs yet._")
        return

    with solara.Column(classes=["run-history-compact"]):
        for result in batch_results:
            is_current = (result is mc_current) or (result is sweep_current)
            BatchHistoryItem(result, is_current)
        for run in run_history:
            is_selected = (session_history.selected_run.value is not None) and (
                session_history.selected_run.value.id == run.id
            )
            RunHistoryItem(run, is_selected)
