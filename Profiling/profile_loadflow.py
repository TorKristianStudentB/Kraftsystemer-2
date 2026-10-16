"""
Profiler for the project's own DCPF/FDLF and pandapower reference solvers.

Run from the repository root:
    python -m Profiling.profile_loadflow

This script does not modify the solver implementations. It measures each solver
call externally, profiles Python-level function costs with cProfile, and writes
CSV/text/profile outputs under Profiling/results/.
"""

from __future__ import annotations

import cProfile
import contextlib
import csv
import io
import pstats
import statistics
import time
from pathlib import Path as FilePath

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

NORDIC_GRID_PATH = (
    PROJECT_ROOT / "Grid" / "Nordic490_komplett.xlsx"
)

def load_makegrid_without_circular_import():
    """Load MakeGrid without modifying any GridMaker files."""
    import importlib
    import types

    module_name = "GridMaker.ReadExcelGrid"

    # Temporary placeholder to break the circular import.
    placeholder = types.ModuleType(module_name)
    placeholder.MakeGrid = None

    sys.modules[module_name] = placeholder

    try:
        imports_module = importlib.import_module("GridMaker.Imports")
    finally:
        # Remove the placeholder so the real module can be imported.
        sys.modules.pop(module_name, None)

        import GridMaker
        if hasattr(GridMaker, "ReadExcelGrid"):
            delattr(GridMaker, "ReadExcelGrid")

    read_excel_module = importlib.import_module(module_name)

    return read_excel_module.MakeGrid
# Number of timed repetitions per solver. Increase for more stable timing.
REPEATS = 3
TOP_FUNCTIONS = 25
RESULTS_DIR = FilePath(__file__).resolve().parent / "results"

import pandas as pd
import tempfile
import shutil

def prepare_nordic_grid(source_path):
    """Create a temporary copy with column names expected by MakeGrid."""
    temp_dir = tempfile.mkdtemp(prefix="nordic_profile_")
    temp_path = Path(temp_dir) / "Nordic490_profile.xlsx"

    shutil.copy2(source_path, temp_path)

    line_df = pd.read_excel(temp_path, sheet_name="line")

    line_df.rename(columns={
        "R_per_meter": "R_per_m",
        "X_per_meter": "X_per_m",
        "B_per_meter": "B_per_m",
    }, inplace=True)

    with pd.ExcelWriter(
        temp_path,
        engine="openpyxl",
        mode="a",
        if_sheet_exists="replace"
    ) as writer:
        line_df.to_excel(writer, sheet_name="line", index=False)

    return temp_path


def load_solver_specs():
    """Import solver methods only when profiling starts."""
    from GridMaker.ClassGrid import Grid

    return [
        ("Own DCPF", lambda grid: grid.DCPF()),
        ("Own FDLF", lambda grid: grid.FDLF()),
        ("Pandapower DC", lambda grid: grid.validating_PP_DC()),
        ("Pandapower FDLF", lambda grid: grid.validating_PP_FDPF()),
    ]


def run_quietly(function, grid):
    """Run a solver while suppressing its console output."""
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        return function(grid)


def timed_run(function, grid):
    """Measure wall-clock duration around the complete solver call."""
    start = time.perf_counter()
    run_quietly(function, grid)
    return time.perf_counter() - start


def profile_run(function, grid, output_path):
    """Profile one complete solver call and save its cProfile data."""
    profiler = cProfile.Profile()
    sink = io.StringIO()

    start = time.perf_counter()
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        profiler.enable()
        function(grid)
        profiler.disable()
    elapsed = time.perf_counter() - start

    profiler.dump_stats(str(output_path))

    stats_stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stats_stream)
    stats.sort_stats("cumulative").print_stats(TOP_FUNCTIONS)
    profile_text = stats_stream.getvalue()

    return elapsed, profile_text


def save_text(path, text):
    path.write_text(text, encoding="utf-8")


def main():
    MakeGrid = load_makegrid_without_circular_import()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if not NORDIC_GRID_PATH.exists():
        raise FileNotFoundError(
            f"Nordic grid not found: {NORDIC_GRID_PATH}"
        )

    grid_path = prepare_nordic_grid(NORDIC_GRID_PATH)

    solver_specs = load_solver_specs()
    timing_rows = []
    profile_summaries = []

    
    print(f"Original grid file: {NORDIC_GRID_PATH}")
    print(f"Prepared grid file: {grid_path}")
    print(f"Repetitions per solver: {REPEATS}")
    print("Loading a fresh grid before each solver run.")
    print("Import/grid construction is outside the solver timing.")

    
    for solver_name, solver_function in solver_specs:
        print(f"\nProfiling: {solver_name}")

        # Warm-up: reduces first-call effects (imports/caches), not included
        # in reported timings. Use a fresh grid for this run.
        warmup_grid = MakeGrid(str(grid_path))
        try:
            run_quietly(solver_function, warmup_grid)
        except Exception as exc:
            print(f"  Warm-up failed: {type(exc).__name__}: {exc}")
            timing_rows.append({
                "solver": solver_name,
                "status": "warm-up failed",
                "repeats": 0,
                "mean_seconds": "",
                "median_seconds": "",
                "min_seconds": "",
                "max_seconds": "",
                "profiled_seconds": "",
            })
            continue

        durations = []
        failed = None

        for repetition in range(1, REPEATS + 1):
            # Build the custom grid before starting the timer.
            grid = MakeGrid(str(grid_path))
            try:
                duration = timed_run(solver_function, grid)
                durations.append(duration)
                print(f"  Run {repetition}: {duration:.6f} s")
            except Exception as exc:
                failed = f"{type(exc).__name__}: {exc}"
                print(f"  Run {repetition} failed: {failed}")
                break

        profile_duration = ""
        if failed is None and durations:
            # Profile a separate fresh run; cProfile adds overhead, so this
            # duration is reported separately and not mixed into the timings.
            grid = MakeGrid(str(grid_path))
            safe_name = (
                solver_name.lower()
                .replace(" ", "_")
                .replace("/", "_")
            )
            profile_path = RESULTS_DIR / f"{safe_name}.prof"
            summary_path = RESULTS_DIR / f"{safe_name}_profile.txt"

            try:
                profile_duration, summary = profile_run(
                    solver_function, grid, profile_path
                )
                save_text(summary_path, summary)
                profile_summaries.append(
                    f"\n{'=' * 80}\n{solver_name}\n{'=' * 80}\n{summary}"
                )
                print(f"  Profile saved: {profile_path}")
                print(f"  Summary saved: {summary_path}")
                print(f"  Profiled run (with profiler overhead): {profile_duration:.6f} s")
            except Exception as exc:
                failed = f"Profiling failed: {type(exc).__name__}: {exc}"
                print(f"  {failed}")

        if durations:
            timing_rows.append({
                "solver": solver_name,
                "status": failed or "ok",
                "repeats": len(durations),
                "mean_seconds": f"{statistics.mean(durations):.9f}",
                "median_seconds": f"{statistics.median(durations):.9f}",
                "min_seconds": f"{min(durations):.9f}",
                "max_seconds": f"{max(durations):.9f}",
                "profiled_seconds": (
                    f"{profile_duration:.9f}" if profile_duration != "" else ""
                ),
            })
        else:
            timing_rows.append({
                "solver": solver_name,
                "status": failed or "failed",
                "repeats": 0,
                "mean_seconds": "",
                "median_seconds": "",
                "min_seconds": "",
                "max_seconds": "",
                "profiled_seconds": "",
            })

    csv_path = RESULTS_DIR / "timings.csv"
    fieldnames = [
        "solver", "status", "repeats", "mean_seconds", "median_seconds",
        "min_seconds", "max_seconds", "profiled_seconds",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(timing_rows)

    summary_path = RESULTS_DIR / "all_profiles_summary.txt"
    save_text(summary_path, "\n".join(profile_summaries))

    print("\n" + "=" * 80)
    print("TIMING SUMMARY (unprofiled runs)")
    print("=" * 80)
    print(f"{'Solver':<22} {'Median (s)':>14} {'Mean (s)':>14} {'Status':>18}")
    for row in timing_rows:
        median = row["median_seconds"] or "—"
        mean = row["mean_seconds"] or "—"
        print(f"{row['solver']:<22} {median:>14} {mean:>14} {row['status']:>18}")

    print(f"\nResults written to: {RESULTS_DIR}")
    print(f"Timing CSV: {csv_path}")
    print(f"Combined profile summary: {summary_path}")
    print("\nNote: cProfile reports Python-level costs; time in NumPy/pandapower")
    print("native code may appear as time attributed to the calling Python function.")


if __name__ == "__main__":
    main()
