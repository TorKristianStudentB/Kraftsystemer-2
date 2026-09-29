import math
import sys
from pathlib import Path
import numpy as np

import pandapower as pp
import pandapower.topology as top

# ============================================================
# 1. IMPORT NORDIC490 GRID
# ============================================================

project_path = Path(__file__).resolve().parent.parent
sys.path.append(str(project_path))

from TorKode.MakeGridFromFile import MakeGrid, df

grid = MakeGrid(df)

net = pp.create_empty_network()

# Map original Nordic490 bus numbers -> pandapower bus indices
bus_map = {}

SBASE = grid.Base.Sbase  # 100 MVA, used as the common power base throughout


# ============================================================
# 2. CREATE BUSES
# ============================================================

for bus in grid.bus:
    idx = pp.create_bus(
        net,
        vn_kv=bus.Vbase,
        name=bus.Name,
    )
    bus_map[bus.busNumber] = idx

print("Created buses:", len(net.bus))


# ============================================================
# 3. CREATE LINES (+ charging susceptance as split shunts)
# ============================================================
# Series R/X kept as impedance elements, same as before. Line charging (B)
# is now represented: standard pi-model splits the total shunt susceptance
# B into B/2 at each end bus. In pandapower a shunt's q_mvar is reactive
# power ABSORBED at rated voltage, so a capacitive susceptance (B > 0),
# which INJECTS reactive power, needs a negative q_mvar.

for line in grid.line:
    pp.create_impedance(
        net,
        from_bus=bus_map[line.Frombus],
        to_bus=bus_map[line.Tobus],
        rft_pu=line.R,
        xft_pu=line.X,
        rtf_pu=line.R,
        xtf_pu=line.X,
        sn_mva=SBASE,
        name=f"Line {line.Frombus}-{line.Tobus}",
    )

    if line.B != 0:
        q_half_mvar = -(line.B / 2) * SBASE  # negative = capacitive injection
        pp.create_shunt(
            net,
            bus=bus_map[line.Frombus],
            q_mvar=q_half_mvar,
            name=f"Line charging {line.Frombus}-{line.Tobus} (from side)",
        )
        pp.create_shunt(
            net,
            bus=bus_map[line.Tobus],
            q_mvar=q_half_mvar,
            name=f"Line charging {line.Frombus}-{line.Tobus} (to side)",
        )

print("Created line impedances:", len(net.impedance))
print("Created line-charging shunts:", len(net.shunt))


# ============================================================
# 4. CREATE TRANSFORMERS (proper ratio, not plain impedance)
# ============================================================
# Every trafo in this dataset connects two different voltage levels, and
# its "ratio" column is exactly Vbase(Frombus)/Vbase(Tobus) - i.e. Frombus
# is consistently the LV side and Tobus the HV side. Rather than hardcode
# that direction, the HV/LV assignment below is resolved from each bus's
# actual vn_kv, so it self-corrects if that convention ever changes.
#
# ASSUMPTION: the sheet gives no per-transformer rated power, so each
# transformer is treated as rated at the grid's SBASE (100 MVA) and its
# pu R/X are converted to vk_percent / vkr_percent on that basis. No
# magnetizing/iron-loss data is available, so i0_percent and pfe_kw are
# left at 0. Since the ratio column matches the nominal bus voltage ratio
# exactly, this is modeled as a fixed transformer at nominal tap (no
# explicit tap deviation).

for trafo in grid.trafo:
    from_idx = bus_map[trafo.Frombus]
    to_idx = bus_map[trafo.Tobus]

    vn_from = net.bus.at[from_idx, "vn_kv"]
    vn_to = net.bus.at[to_idx, "vn_kv"]

    if vn_from >= vn_to:
        hv_bus, lv_bus = from_idx, to_idx
        vn_hv, vn_lv = vn_from, vn_to
    else:
        hv_bus, lv_bus = to_idx, from_idx
        vn_hv, vn_lv = vn_to, vn_from

    vk_percent = math.sqrt(trafo.R ** 2 + trafo.X ** 2) * 100
    vkr_percent = trafo.R * 100

    pp.create_transformer_from_parameters(
        net,
        hv_bus=hv_bus,
        lv_bus=lv_bus,
        sn_mva=SBASE,
        vn_hv_kv=vn_hv,
        vn_lv_kv=vn_lv,
        vk_percent=vk_percent,
        vkr_percent=vkr_percent,
        pfe_kw=0,
        i0_percent=0,
        shift_degree=0,
        name=f"Trafo {trafo.Frombus}-{trafo.Tobus}",
    )

print("Created transformers:", len(net.trafo))


# ============================================================
# 5. CREATE LOADS
# ============================================================
# NOTE: Q_load is 0 for every bus in the source sheet, so this load flow
# currently has essentially no reactive load anywhere in the system. That
# is a data limitation, not something fixable in this script - results
# should be expected to diverge from the reference voltages until real
# reactive load data is available.

for bus in grid.bus:
    if bus.P_load != 0 or bus.Q_load != 0:
        pp.create_load(
            net,
            bus=bus_map[bus.busNumber],
            p_mw=bus.P_load,
            q_mvar=bus.Q_load,
            name=f"Load bus {bus.busNumber}",
        )

print("Created loads:", len(net.load))


# ============================================================
# 6. PICK SLACK BUS, THEN CREATE GENERATORS AT ALL OTHER
#    GENERATING BUSES (fixes the previous double-counting,
#    where the slack bus also got a PV generator)
# ============================================================
# Reactive limits per bus are aggregated from the 'gen' sheet's
# Q_max/Q_min (summed across all generating units at that bus), when
# available, so PV buses aren't left with unlimited Q support.

q_limits_by_bus = {}
for g in grid.gen:
    bus_id = int(g.bus)
    qmax, qmin = q_limits_by_bus.get(bus_id, (0.0, 0.0))
    q_limits_by_bus[bus_id] = (qmax + g.Q_max, qmin + g.Q_min)

generator_buses = [bus for bus in grid.bus if bus.P_gen > 0]

if not generator_buses:
    raise ValueError("No generator buses found!")

# Same selection as before (first generating bus) - arbitrary but kept
# consistent with the original script; revisit if a specific reference
# bus should be the slack instead.
slack_bus = generator_buses[0]

pp.create_ext_grid(
    net,
    bus=bus_map[slack_bus.busNumber],
    vm_pu=slack_bus.Volt,
    name="Temporary Slack",
)

print("Temporary slack bus:", slack_bus.busNumber)

for bus in generator_buses:
    if bus.busNumber == slack_bus.busNumber:
        continue  # already represented by the ext_grid above

    qmax, qmin = q_limits_by_bus.get(bus.busNumber, (None, None))

    pp.create_gen(
        net,
        bus=bus_map[bus.busNumber],
        p_mw=bus.P_gen,
        vm_pu=bus.Volt,
        max_q_mvar=qmax,
        min_q_mvar=qmin,
        name=f"Generator bus {bus.busNumber}",
    )

print("Created generators:", len(net.gen))


# ============================================================
# 7. NETWORK CHECK
# ============================================================

print("\n--- NETWORK SUMMARY ---")
print("Buses:", len(net.bus))
print("Impedances:", len(net.impedance))
print("Transformers:", len(net.trafo))
print("Shunts (line charging):", len(net.shunt))
print("Loads:", len(net.load))
print("Generators:", len(net.gen))
print("External grids:", len(net.ext_grid))

assert len(net.bus) > 0, "No buses created!"
assert len(net.impedance) > 0, "No line impedances created!"
assert len(net.trafo) > 0, "No transformers created!"
assert len(net.load) > 0, "No loads created!"
assert len(net.gen) > 0, "No generators created!"


# ============================================================
# 8. FIND AND DISABLE BUSES NOT CONNECTED TO THE SLACK
# ============================================================
# Done programmatically instead of hardcoding bus indices, so it stays
# correct if the underlying grid data changes. In this dataset these turn
# out to be HVDC converter-station buses (present in the 'link' sheet,
# not the AC 'line'/'trafo' sheets), so excluding them from the AC load
# flow is expected, not a bug.

unsupplied = top.unsupplied_buses(net)
if unsupplied:
    net.bus.loc[list(unsupplied), "in_service"] = False

print("\nBuses disabled as unsupplied (not connected to slack):", sorted(unsupplied))
print("Active bus count:", net.bus["in_service"].sum())


# ============================================================
# 9. RUN FAST DECOUPLED LOAD FLOW
# ============================================================

try:
    pp.runpp(
        net,
        algorithm="fdxb",
        calculate_voltage_angles=True,
        init="flat",
        max_iteration=50,
        tolerance_mva=1e-6,
    )
    print("\nSolver converged:", net.converged)

except Exception as e:
    print("\nLoad flow failed:")
    print(type(e).__name__, e)
    raise




# ============================================================
# 10. DISPLAY CALCULATED POWER FLOW RESULTS (NO3)
# ============================================================

import pandas as pd
import numpy as np

if net.converged:

    # --------------------------------------------------------
    # 1. Aggregate calculated generator results per bus
    # --------------------------------------------------------

    gen_results = net.res_gen.copy()
    gen_results["bus"] = net.gen["bus"]

    ext_results = net.res_ext_grid.copy()
    ext_results["bus"] = net.ext_grid["bus"]

    # Combine normal generators and slack generation
    all_gen = pd.concat([
        gen_results[["bus", "p_mw", "q_mvar"]],
        ext_results[["bus", "p_mw", "q_mvar"]]
    ], ignore_index=True)

    gen_by_bus = all_gen.groupby("bus")[["p_mw", "q_mvar"]].sum()

    # --------------------------------------------------------
    # 2. Aggregate calculated load results per bus
    # --------------------------------------------------------

    load_results = net.res_load.copy()
    load_results["bus"] = net.load["bus"]

    load_by_bus = load_results.groupby("bus")[["p_mw", "q_mvar"]].sum()

    # --------------------------------------------------------
    # 3. Build NO3 results using pandapower results
    # --------------------------------------------------------

    results = []

    for bus in grid.bus:

        if bus.bidz != "NO3":
            continue

        idx = bus_map[bus.busNumber]

        if not net.bus.at[idx, "in_service"]:
            continue

        # Calculated voltage and angle
        vm_pu = net.res_bus.at[idx, "vm_pu"]
        angle_rad = np.deg2rad(
            net.res_bus.at[idx, "va_degree"]
        )

        # Calculated generation (including slack if applicable)
        p_gen = gen_by_bus.loc[idx, "p_mw"] \
            if idx in gen_by_bus.index else 0.0

        q_gen = gen_by_bus.loc[idx, "q_mvar"] \
            if idx in gen_by_bus.index else 0.0

        # Calculated load
        p_load = load_by_bus.loc[idx, "p_mw"] \
            if idx in load_by_bus.index else 0.0

        q_load = load_by_bus.loc[idx, "q_mvar"] \
            if idx in load_by_bus.index else 0.0

        results.append({
            "bus_id": bus.busNumber,
            "name": bus.Name,
            "bidz": bus.bidz,
            "Vbase": bus.Vbase,
            "V [P.U.]": vm_pu,
            "Angle [rad]": angle_rad,
            "P_gen [MW]": p_gen,
            "Q_gen [MVAr]": q_gen,
            "P_load [MW]": p_load,
            "Q_load [MVAr]": q_load
        })

    # --------------------------------------------------------
    # 4. Print results
    # --------------------------------------------------------

    no3_results = pd.DataFrame(results)

    print("\n--- NO3 CALCULATED POWER FLOW RESULTS ---")

    print(
        no3_results.to_string(
            index=False,
            float_format=lambda x: f"{x:.5f}"
        )
    )

else:
    print("Load flow did not converge.")