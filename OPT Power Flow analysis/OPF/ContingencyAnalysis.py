"""Contingency analysis for the DC-OPF operating point.

Place this file in the project's OPF folder. The function evaluates each
single physical transmission-line outage with the existing Grid.DCPF()
implementation. Generator dispatch is kept fixed; no re-optimization occurs.

This implementation assumes the current non-reduced network representation
(GridMaker.Imports.forenklet == False), where DCPF.solution.flow_in_line
contains one flow for each entry in grid.line.
"""

from pathlib import Path
import copy
import math
import sys
import time

import pandas as pd


# Make the project root importable when this module is run/imported from OPF.
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = next(
    (folder for folder in (_SCRIPT_DIR, *_SCRIPT_DIR.parents)
     if (folder / "GridMaker").is_dir()),
    None,
)
if _PROJECT_ROOT is None:
    raise ModuleNotFoundError(
        f"Fant ikke mappen 'GridMaker' i noen foreldremappe til {_SCRIPT_DIR}. "
        "Plasser ContingencyAnalysis.py under prosjektets OPF-mappe."
    )
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _line_label(line):
    """Return a readable and reasonably unique line label."""
    return (
        f"Linje {line.lineNumber} "
        f"({int(line.Frombus)}-{int(line.Tobus)})"
    )


def _connected_components(grid):
    """Find connected bus components using all in-service lines and trafos."""
    bus_ids = [bus.busNumber for bus in grid.bus]
    if len(set(bus_ids)) != len(bus_ids):
        raise ValueError("Dupliserte busNumber i nettet.")

    adjacency = {bus_id: set() for bus_id in bus_ids}

    for branch in [*grid.line, *grid.trafo]:
        from_bus = branch.Frombus
        to_bus = branch.Tobus
        if from_bus not in adjacency or to_bus not in adjacency:
            raise ValueError(
                f"Gren mellom {from_bus} og {to_bus} peker på en buss som ikke finnes."
            )
        adjacency[from_bus].add(to_bus)
        adjacency[to_bus].add(from_bus)

    components = []
    unvisited = set(bus_ids)
    while unvisited:
        start = unvisited.pop()
        component = {start}
        stack = [start]
        while stack:
            current = stack.pop()
            for neighbour in adjacency[current]:
                if neighbour in unvisited:
                    unvisited.remove(neighbour)
                    component.add(neighbour)
                    stack.append(neighbour)
        components.append(sorted(component))

    return components


def _copy_grid_for_dcpf(grid):
    """Copy only network data, deliberately omitting the stored Pyomo model.

    DC-OPF stores its Pyomo model in grid.solution.modell. Deep-copying the
    entire Grid would also copy that model for every contingency, which is
    unnecessary. DCPF only needs Base, bus, line, trafo and gen.
    """
    copied = grid.__class__(getattr(grid, "Name", "contingency_copy"))
    copied.Base = copy.deepcopy(grid.Base)
    copied.bus = copy.deepcopy(grid.bus)
    copied.line = copy.deepcopy(grid.line)
    copied.trafo = copy.deepcopy(grid.trafo)
    copied.gen = copy.deepcopy(grid.gen)
    copied.solution = None
    # Do not copy _admittans_lagret: its matrix belongs to the original topology.
    return copied


def _run_dcpf(grid):
    """Run the existing DCPF method and return its Solution object."""
    grid.DCPF()  # DCPF writes its result to grid.solution.
    solution = getattr(grid, "solution", None)
    if solution is None:
        raise RuntimeError("DCPF opprettet ikke grid.solution.")
    if not getattr(solution, "konvergerte", False):
        raise RuntimeError("DCPF konvergerte ikke for dette nettilfellet.")
    if solution.flow_in_line is None:
        raise RuntimeError("DCPF returnerte ingen linjeflyter.")
    if len(solution.flow_in_line) != len(grid.line):
        raise RuntimeError(
            "Antall DCPF-linjeflyter stemmer ikke med antall linjer. "
            "Kontroller at forenklet=False."
        )
    return solution


def contingency_analysis(grid, loading_limit=100.0, verbose=True):
    """Evaluate every single physical line outage at the fixed DC-OPF dispatch.

    Parameters
    ----------
    grid:
        Grid object after a successful call to dcopf(grid).
    loading_limit:
        Overload threshold in percent. Default is 100.0.
    verbose:
        Print the base-case check and ranked contingency summary.

    Returns
    -------
    dict
        ``summary`` is a pandas DataFrame with one row per physical line outage.
        ``details`` contains line-by-line post-contingency results and island data.
        ``basecase`` contains the DCPF base-case validation.

    Notes
    -----
    The original Grid is not modified. A light copy of its network data is used
    for each DCPF run. Generator dispatch (bus.P_gen and gen.P_opf) is copied
    unchanged from the DC-OPF solution.
    """
    start_time = time.perf_counter()

    # Check the operating point supplied to the analysis.
    solution = getattr(grid, "solution", None)
    if solution is None or getattr(solution, "type", None) != "DCOPF":
        raise ValueError(
            "Kjør først dcopf(grid). contingency_analysis krever et DC-OPF-resultat."
        )
    if not getattr(solution, "konvergerte", False):
        raise ValueError("DC-OPF-resultatet er ikke konvergert.")

    try:
        loading_limit = float(loading_limit)
    except (TypeError, ValueError) as exc:
        raise ValueError("loading_limit må være et tall i prosent.") from exc
    if not math.isfinite(loading_limit) or loading_limit <= 0:
        raise ValueError("loading_limit må være et positivt, endelig tall.")

    # This mapping is only valid for the full, non-Kron-reduced grid.
    from GridMaker.Imports import forenklet
    if forenklet:
        raise NotImplementedError(
            "ContingencyAnalysis krever forenklet=False. Ved Kron-reduksjon "
            "representerer DCPF.solution.flow_in_line ekvivalente grener, "
            "ikke én-til-én de fysiske linjene i grid.line."
        )

    if not grid.line:
        raise ValueError("Nettet inneholder ingen linjer å undersøke.")
    if grid.Base is None or grid.Base.Sbase is None:
        raise ValueError("grid.Base.Sbase mangler.")

    # Confirm the intact network is connected before beginning the study.
    base_components = _connected_components(grid)
    if len(base_components) != 1:
        raise ValueError(
            "Normalnettet er ikke sammenhengende. Contingency analysis kan "
            f"ikke starte. Komponenter: {base_components}"
        )

    # Only physical transmission lines are outage candidates and overload targets.
    physical_line_indices = [
        i for i, line in enumerate(grid.line)
        if not getattr(line, "kunstig_line", False)
    ]
    if not physical_line_indices:
        raise ValueError("Fant ingen fysiske linjer (kunstig_line=False).")

    for i in physical_line_indices:
        line = grid.line[i]
        limit = float(line.S_max)
        if not math.isfinite(limit) or limit <= 0:
            raise ValueError(
                f"Ugyldig S_max for {_line_label(line)}: {line.S_max}"
            )

    # ---------- N0: validate the OPF dispatch using an independent DCPF run ----------
    base_grid = _copy_grid_for_dcpf(grid)
    base_solution = _run_dcpf(base_grid)

    base_flows = [float(flow) for flow in base_solution.flow_in_line]
    base_line_results = []
    for i in physical_line_indices:
        line = grid.line[i]
        flow_mw = base_flows[i]
        loading_pct = abs(flow_mw) / float(line.S_max) * 100.0
        base_line_results.append({
            "line_index": i,
            "line": _line_label(line),
            "flow_MW": flow_mw,
            "limit_MW": float(line.S_max),
            "loading_pct": loading_pct,
            "overloaded": loading_pct > loading_limit + 1e-6,
        })

    base_worst = max(base_line_results, key=lambda row: row["loading_pct"])

    # Compare DCPF N0 line flows with the line part of the DC-OPF branch flows.
    # This is a consistency diagnostic; it does not change the dispatch.
    opf_flows = getattr(solution, "flyt_MW", None)
    max_basecase_flow_difference = None
    if opf_flows is not None and len(opf_flows) >= len(grid.line):
        max_basecase_flow_difference = max(
            abs(base_flows[i] - float(opf_flows[i]))
            for i in range(len(grid.line))
        ) if grid.line else 0.0

    basecase = {
        "status": "converged",
        "max_loading_pct": base_worst["loading_pct"],
        "worst_line": base_worst["line"],
        "worst_flow_MW": base_worst["flow_MW"],
        "n_overloaded_lines": sum(row["overloaded"] for row in base_line_results),
        "line_results": base_line_results,
        "max_abs_flow_difference_vs_DCOPF_MW": max_basecase_flow_difference,
    }

    # ---------- One independent network copy per physical line outage ----------
    summary_rows = []
    details = {}

    for outage_index in physical_line_indices:
        outage_line = grid.line[outage_index]
        outage_label = _line_label(outage_line)
        case_start = time.perf_counter()

        outage_grid = _copy_grid_for_dcpf(grid)
        # Remove only this physical line. Artificial generator connections remain.
        outage_grid.line = [
            line for i, line in enumerate(outage_grid.line)
            if i != outage_index
        ]
        # Explicitly discard any inherited cached matrix if the Grid class has one.
        outage_grid.__dict__.pop("_admittans_lagret", None)

        components = _connected_components(outage_grid)
        if len(components) > 1:
            component_text = " | ".join(
                ", ".join(str(bus_id) for bus_id in component)
                for component in components
            )
            row = {
                "linje ute": outage_label,
                "status": "islanding",
                "maks belastning [%]": None,
                "mest belastet linje": None,
                "flyt [MW]": None,
                "antall overlastede linjer": None,
                "overlastede linjer": "Kan ikke beregnes – nettet deles i øyer",
                "øyer": component_text,
                "kjøretid [ms]": (time.perf_counter() - case_start) * 1000.0,
            }
            summary_rows.append(row)
            details[outage_label] = {
                "status": "islanding",
                "components": components,
                "line_results": [],
            }
            continue

        try:
            outage_solution = _run_dcpf(outage_grid)
        except Exception as exc:
            error_text = f"{type(exc).__name__}: {exc}"
            summary_rows.append({
                "linje ute": outage_label,
                "status": "DCPF-feil",
                "maks belastning [%]": None,
                "mest belastet linje": None,
                "flyt [MW]": None,
                "antall overlastede linjer": None,
                "overlastede linjer": error_text,
                "øyer": None,
                "kjøretid [ms]": (time.perf_counter() - case_start) * 1000.0,
            })
            details[outage_label] = {
                "status": "DCPF-feil",
                "error": error_text,
                "components": components,
                "line_results": [],
            }
            continue

        post_flows = [float(flow) for flow in outage_solution.flow_in_line]
        line_results = []
        for i, line in enumerate(outage_grid.line):
            if getattr(line, "kunstig_line", False):
                continue
            limit = float(line.S_max)
            if not math.isfinite(limit) or limit <= 0:
                raise ValueError(
                    f"Ugyldig S_max for {_line_label(line)} etter utfall: {line.S_max}"
                )
            flow_mw = post_flows[i]
            loading_pct = abs(flow_mw) / limit * 100.0
            line_results.append({
                "line": _line_label(line),
                "flow_MW": flow_mw,
                "limit_MW": limit,
                "loading_pct": loading_pct,
                "overloaded": loading_pct > loading_limit + 1e-6,
            })

        if line_results:
            worst = max(line_results, key=lambda row: row["loading_pct"])
            max_loading = worst["loading_pct"]
            worst_line = worst["line"]
            worst_flow = worst["flow_MW"]
        else:
            max_loading = None
            worst_line = None
            worst_flow = None

        overloaded = [row for row in line_results if row["overloaded"]]
        overloaded_text = "; ".join(
            f"{row['line']}: {row['loading_pct']:.1f}%"
            for row in sorted(
                overloaded, key=lambda row: row["loading_pct"], reverse=True
            )
        ) or "Ingen"

        elapsed_ms = (time.perf_counter() - case_start) * 1000.0
        summary_rows.append({
            "linje ute": outage_label,
            "status": "konvergert",
            "maks belastning [%]": max_loading,
            "mest belastet linje": worst_line,
            "flyt [MW]": worst_flow,
            "antall overlastede linjer": len(overloaded),
            "overlastede linjer": overloaded_text,
            "øyer": None,
            "kjøretid [ms]": elapsed_ms,
        })
        details[outage_label] = {
            "status": "konvergert",
            "components": components,
            "line_results": line_results,
        }

    summary = pd.DataFrame(summary_rows)
    if not summary.empty:
        # Put the most critical (highest loading) cases first. Islanding and
        # DCPF errors are placed first because they require separate attention.
        status_priority = summary["status"].map({
            "islanding": 0,
            "DCPF-feil": 1,
            "konvergert": 2,
        })
        summary = (
            summary.assign(_status_priority=status_priority)
            .sort_values(
                ["_status_priority", "maks belastning [%]"],
                ascending=[True, False],
                na_position="last",
            )
            .drop(columns="_status_priority")
            .reset_index(drop=True)
        )

    result = {
        "basecase": basecase,
        "summary": summary,
        "details": details,
        "loading_limit_pct": loading_limit,
        "n_contingencies": len(physical_line_indices),
        "runtime_s": time.perf_counter() - start_time,
    }

    if verbose:
        vis_contingency_resultater(result)

    return result


def vis_contingency_resultater(result):
    """Print the N0 validation and ranked single-line-outage results."""
    base = result["basecase"]
    print("\nDC power flow – normalnett (N0)")
    print(f"Status: {base['status']}")
    print(
        f"Høyeste belastning: {base['max_loading_pct']:.1f}% "
        f"på {base['worst_line']} ({base['worst_flow_MW']:.1f} MW)"
    )
    print(f"Antall overbelastede fysiske linjer: {base['n_overloaded_lines']}")

    flow_difference = base["max_abs_flow_difference_vs_DCOPF_MW"]
    if flow_difference is not None:
        print(
            "Største absolutte forskjell mellom DC-OPF- og DCPF-linjeflyt: "
            f"{flow_difference:.6g} MW"
        )

    print("\nContingency analysis – enkeltutfall av fysiske linjer")
    print(f"Antall undersøkte linjeutfall: {result['n_contingencies']}")
    print(f"Overlastgrense: {result['loading_limit_pct']:.1f}%")
    if result["summary"].empty:
        print("Ingen fysiske linjeutfall å rapportere.")
    else:
        print(result["summary"].to_string(index=False))

    n_islanding = sum(
        row["status"] == "islanding"
        for row in result["summary"].to_dict("records")
    )
    n_errors = sum(
        row["status"] == "DCPF-feil"
        for row in result["summary"].to_dict("records")
    )
    print(
        f"\nKjøretid for contingency analysis: {result['runtime_s'] * 1000:.1f} ms"
    )
    if n_islanding or n_errors:
        print(
            f"Merk: {n_islanding} utfall ga øydrift, og {n_errors} utfall ga DCPF-feil."
        )
