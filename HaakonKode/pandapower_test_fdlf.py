import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pandapower as pp
import pandapower.topology as top


# ============================================================
# 1. IMPORT NORDIC490 GRID
# ============================================================

project_path = Path(__file__).resolve().parent.parent

# MakeGridFromFile.py imports its helper modules as top-level modules.
sys.path.append(str(project_path))
sys.path.append(str(project_path / "TorKode"))

from TorKode.MakeGridFromFile import MakeGrid


df = pd.read_excel(
    project_path / "Grid" / "Nordic490_komplett.xlsx",
    sheet_name=None
)

# Make column name match what MakeGridFromFile.py expects.
if "S_base [MVA]" in df["bus"].columns and "S_base [MVA] " not in df["bus"].columns:
    df["bus"] = df["bus"].rename(columns={
        "S_base [MVA]": "S_base [MVA] "
    })

grid = MakeGrid(df)

SBASE = grid.Base.Sbase

# Use the same system base in pandapower.
net = pp.create_empty_network(sn_mva=SBASE)


# ============================================================
# 2. CREATE BUSES
# ============================================================

# Map original Grid bus numbers -> pandapower bus indices.
bus_map = {}

for bus in grid.bus:
    idx = pp.create_bus(
        net,
        vn_kv=bus.Vbase,
        name=bus.Name,
    )

    bus_map[bus.busNumber] = idx

print("Created buses:", len(net.bus))


# ============================================================
# 3. CREATE LINES + LINE CHARGING
# ============================================================
#
# MakeGridFromFile.py has already converted R and X to p.u.
# The line model in admittansmatrise.py is:
#
#   y = 1 / (R + jX)
#   y_shunt = jB
#
# with B/2 at each end of the line.
#
# Pandapower impedance elements use the same p.u. R/X values.
# The shunt susceptance is represented by two shunts.
# ============================================================

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
        # In pandapower, positive q_mvar means reactive power absorbed.
        # B > 0 is capacitive and therefore injects reactive power.
        q_half_mvar = -(line.B / 2) * SBASE

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
# 4. CREATE TRANSFORMERS
# ============================================================
#
# The original admittansmatrise.py uses:
#
#       y = 1 / (R + jX)
#
# and a tap ratio a = 1 / ratio.
#
# Here the transformer is represented using pandapower's
# transformer model with the same p.u. R/X and SBASE.
#
# No magnetizing branch or phase shift exists in the source
# model, so pfe_kw = 0, i0_percent = 0 and shift_degree = 0.
# ============================================================

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
#
# MakeGridFromFile.py converts all P/Q bus values to p.u.
# Pandapower expects MW/MVAr here, so convert back:
#
#       P_MW   = P_pu * SBASE
#       Q_MVAr = Q_pu * SBASE
# ============================================================

for bus in grid.bus:

    if bus.P_load != 0 or bus.Q_load != 0:
        pp.create_load(
            net,
            bus=bus_map[bus.busNumber],
            p_mw=bus.P_load * SBASE,
            q_mvar=bus.Q_load * SBASE,
            name=f"Load bus {bus.busNumber}",
        )

print("Created loads:", len(net.load))


# ============================================================
# 6. FIND GENERATOR BUSSES
# ============================================================
#
# Use grid.gen to determine which busses are generator busses,
# matching the existing Newton-Raphson implementation.
#
# grid.gen contains:
#       P_max, bus, Q_max, Q_min
#
# while the actual P_gen/Q_gen on the bus are stored in grid.bus.
# ============================================================

generator_bus_ids = {
    int(g.bus)
    for g in grid.gen
}

generator_buses = [
    bus for bus in grid.bus
    if bus.busNumber in generator_bus_ids
]

if not generator_buses:
    raise ValueError("No generator buses found!")


# ============================================================
# 7. AGGREGATE GENERATOR Q LIMITS
# ============================================================

q_limits_by_bus = {}

for g in grid.gen:

    # Missing Q limits mean that no Q-limit constraint is supplied
    # for this generator.
    if g.Q_max is None or g.Q_min is None:
        continue

    bus_id = int(g.bus)

    qmax, qmin = q_limits_by_bus.get(
        bus_id,
        (0.0, 0.0)
    )

    q_limits_by_bus[bus_id] = (
        qmax + g.Q_max,
        qmin + g.Q_min
    )


# ============================================================
# 8. CREATE SLACK BUS
# ============================================================
#
# The reference NR implementation treats grid.bus[0] as the
# reference bus. Use the same convention here.
# ============================================================

slack_bus = grid.bus[0]

pp.create_ext_grid(
    net,
    bus=bus_map[slack_bus.busNumber],
    vm_pu=slack_bus.Volt,
    va_degree=np.degrees(slack_bus.Angle),
    name="Slack bus",
)

print("Slack bus:", slack_bus.busNumber)


# ============================================================
# 9. CREATE OTHER GENERATORS AS PV BUSES
# ============================================================
#
# Actual P_gen is stored in p.u. in grid.bus, so convert to MW.
#
# Q limits are also p.u. after MakeGrid's conversion, so convert
# them back to MVAr when passing them to pandapower.
# ============================================================

for bus in generator_buses:

    if bus.busNumber == slack_bus.busNumber:
        continue

    qmax, qmin = q_limits_by_bus.get(
        bus.busNumber,
        (None, None)
    )

    gen_kwargs = {
        "net": net,
        "bus": bus_map[bus.busNumber],
        "p_mw": bus.P_gen * SBASE,
        "vm_pu": bus.Volt,
        "name": f"Generator bus {bus.busNumber}",
    }

    if qmax is not None and qmin is not None:
        gen_kwargs["max_q_mvar"] = qmax * SBASE
        gen_kwargs["min_q_mvar"] = qmin * SBASE

    pp.create_gen(**gen_kwargs)

print("Created generators:", len(net.gen))


# ============================================================
# 10. NETWORK SUMMARY
# ============================================================

print("\n--- NETWORK SUMMARY ---")
print("SBASE:", SBASE, "MVA")
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
assert len(net.ext_grid) > 0, "No external grid created!"


# ============================================================
# 11. FIND AND DISABLE BUSES NOT CONNECTED TO THE SLACK
# ============================================================

unsupplied = top.unsupplied_buses(net)

if unsupplied:
    net.bus.loc[list(unsupplied), "in_service"] = False

print(
    "\nBuses disabled as unsupplied (not connected to slack):",
    sorted(unsupplied)
)
print(
    "Active bus count:",
    net.bus["in_service"].sum()
)


# ============================================================
# 12. RUN FAST DECOUPLED LOAD FLOW
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
# 13. DISPLAY CALCULATED POWER FLOW RESULTS (NO3)
# ============================================================

if net.converged:

    # --------------------------------------------------------
    # Aggregate calculated generator results per bus
    # --------------------------------------------------------

    gen_results = net.res_gen.copy()
    gen_results["bus"] = net.gen["bus"]

    ext_results = net.res_ext_grid.copy()
    ext_results["bus"] = net.ext_grid["bus"]

    all_gen = pd.concat(
        [
            gen_results[["bus", "p_mw", "q_mvar"]],
            ext_results[["bus", "p_mw", "q_mvar"]],
        ],
        ignore_index=True,
    )

    gen_by_bus = all_gen.groupby("bus")[["p_mw", "q_mvar"]].sum()


    # --------------------------------------------------------
    # Aggregate calculated load results per bus
    # --------------------------------------------------------

    load_results = net.res_load.copy()
    load_results["bus"] = net.load["bus"]

    load_by_bus = load_results.groupby(
        "bus"
    )[["p_mw", "q_mvar"]].sum()


    # --------------------------------------------------------
    # Build NO3 results
    # --------------------------------------------------------

    results = []

    for bus in grid.bus:

        if bus.bidz != "NO3":
            continue

        idx = bus_map[bus.busNumber]

        if not net.bus.at[idx, "in_service"]:
            continue

        vm_pu = net.res_bus.at[idx, "vm_pu"]
        angle_degree = net.res_bus.at[idx, "va_degree"]

        p_gen = (
            gen_by_bus.loc[idx, "p_mw"]
            if idx in gen_by_bus.index
            else 0.0
        )

        q_gen = (
            gen_by_bus.loc[idx, "q_mvar"]
            if idx in gen_by_bus.index
            else 0.0
        )

        p_load = (
            load_by_bus.loc[idx, "p_mw"]
            if idx in load_by_bus.index
            else 0.0
        )

        q_load = (
            load_by_bus.loc[idx, "q_mvar"]
            if idx in load_by_bus.index
            else 0.0
        )

        results.append(
            {
                "bus_id": bus.busNumber,
                "name": bus.Name,
                "bidz": bus.bidz,
                "Vbase": bus.Vbase,
                "V [P.U.]": vm_pu,
                "Angle [degree]": angle_degree,
                "P_gen [MW]": p_gen,
                "Q_gen [MVAr]": q_gen,
                "P_load [MW]": p_load,
                "Q_load [MVAr]": q_load,
            }
        )


    # --------------------------------------------------------
    # Print results
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