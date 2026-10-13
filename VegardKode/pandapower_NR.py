import copy
import sys
from pathlib import Path

import numpy as np
import pandapower as pp


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "FunctionsInGridMaker"))
sys.path.insert(0, str(PROJECT_ROOT / "GridMaker"))

from ReadExcelGrid import MakeGrid


def PandapowerNewtonRaphson(grid):
    g = copy.deepcopy(grid)

    Sbase = float(g.Base.Sbase)
    Y = g.admittansmatrise()

    net = pp.create_empty_network(sn_mva=Sbase)


    # Busstyper
    bus_types = []

    for i, bus in enumerate(g.bus):
        if i == 0:
            bus_types.append("ref")

        elif np.all(np.isclose(Y[i, :], 0)):
            bus_types.append("alene")

        elif any(int(gen.bus) == int(bus.busNumber) for gen in g.gen):
            bus_types.append("PV")

        else:
            bus_types.append("PQ")


    # Busser
    bus_map = {}

    for i, bus in enumerate(g.bus):
        bus_map[int(bus.busNumber)] = pp.create_bus(
            net,
            vn_kv=float(bus.Vbase),
            name=str(bus.Name),
            in_service=bus_types[i] != "alene"
        )


    # Laster
    for i, bus in enumerate(g.bus):
        if bus_types[i] == "alene":
            continue

        p_load = float(np.nan_to_num(bus.P_load)) * Sbase
        q_load = float(np.nan_to_num(bus.Q_load)) * Sbase

        if p_load != 0 or q_load != 0:
            pp.create_load(
                net,
                bus=bus_map[int(bus.busNumber)],
                p_mw=p_load,
                q_mvar=q_load
            )


    # Slack
    slack = g.bus[0]

    pp.create_ext_grid(
        net,
        bus=bus_map[int(slack.busNumber)],
        vm_pu=float(abs(slack.Volt)),
        va_degree=float(np.degrees(slack.Angle))
    )


    # Generatorer
    for i, bus in enumerate(g.bus):
        if bus_types[i] == "alene":
            continue

        p_gen = float(np.nan_to_num(bus.P_gen)) * Sbase
        q_gen = float(np.nan_to_num(bus.Q_gen)) * Sbase

        if bus_types[i] == "PV":
            pp.create_gen(
                net,
                bus=bus_map[int(bus.busNumber)],
                p_mw=p_gen,
                vm_pu=float(abs(bus.Volt))
            )

        elif bus_types[i] == "PQ" and (p_gen != 0 or q_gen != 0):
            pp.create_sgen(
                net,
                bus=bus_map[int(bus.busNumber)],
                p_mw=p_gen,
                q_mvar=q_gen
            )


    # Linjer
    for line in g.line:
        pp.create_impedance(
            net,
            from_bus=bus_map[int(line.Frombus)],
            to_bus=bus_map[int(line.Tobus)],
            rft_pu=float(line.R),
            xft_pu=float(line.X),
            rtf_pu=float(line.R),
            xtf_pu=float(line.X),
            sn_mva=Sbase
        )

        B = float(np.nan_to_num(line.B))

        if B != 0:
            q_shunt = -(B / 2) * Sbase

            pp.create_shunt(
                net,
                bus=bus_map[int(line.Frombus)],
                q_mvar=q_shunt,
                p_mw=0
            )

            pp.create_shunt(
                net,
                bus=bus_map[int(line.Tobus)],
                q_mvar=q_shunt,
                p_mw=0
            )


    # Transformatorer
    bus_by_number = {
        int(bus.busNumber): bus
        for bus in g.bus
    }

    for trafo in g.trafo:
        from_nr = int(trafo.Frombus)
        to_nr = int(trafo.Tobus)

        if bus_by_number[from_nr].Vbase >= bus_by_number[to_nr].Vbase:
            hv_nr, lv_nr = from_nr, to_nr
        else:
            hv_nr, lv_nr = to_nr, from_nr

        R = float(trafo.R)
        X = float(trafo.X)
        a = 1 / float(trafo.ratio)

        pp.create_transformer_from_parameters(
            net,
            hv_bus=bus_map[hv_nr],
            lv_bus=bus_map[lv_nr],
            sn_mva=Sbase,
            vn_hv_kv=float(bus_by_number[hv_nr].Vbase),
            vn_lv_kv=float(bus_by_number[lv_nr].Vbase),
            vk_percent=np.sqrt(R**2 + X**2) * 100,
            vkr_percent=R * 100,
            pfe_kw=0,
            i0_percent=0,
            shift_degree=0,
            tap_side="hv",
            tap_neutral=0,
            tap_min=0,
            tap_max=1,
            tap_pos=1,
            tap_step_percent=(a - 1) * 100,
            tap_step_degree=0,
            tap_changer_type="Ratio",
            name=str(trafo.Name)
        )


    # Newton-Raphson
    pp.runpp(
        net,
        algorithm="nr",
        init="flat",
        calculate_voltage_angles=True,
        enforce_q_lims=False,
        tolerance_mva=1e-6,
        max_iteration=100,
        numba=False
    )


    # Resultater
    print("\nNEWTON-RAPHSON RESULTAT FRA PANDAPOWER")
    print("Konvergert:", net.converged)

    print(
        f"\n{'Bus':>6}"
        f"{'Type':>7}"
        f"{'V [pu]':>12}"
        f"{'Vinkel [deg]':>16}"
        f"{'P [MW]':>14}"
        f"{'Q [MVAr]':>14}"
    )
    print("-" * 69)

    for i, bus in enumerate(g.bus):
        if bus_types[i] == "alene":
            print(f"{bus.busNumber:>6}{'alene':>7}")
            continue

        result = net.res_bus.loc[bus_map[int(bus.busNumber)]]

        print(
            f"{bus.busNumber:>6}"
            f"{bus_types[i]:>7}"
            f"{result['vm_pu']:>12.5f}"
            f"{result['va_degree']:>16.5f}"
            f"{result['p_mw']:>14.4f}"
            f"{result['q_mvar']:>14.4f}"
        )

    return net


if __name__ == "__main__":
    excel_file = PROJECT_ROOT / "Grid" / "test_trøndelagsnettet.xlsx"

    grid = MakeGrid(excel_file)

    print(
        f"Grid: {len(grid.bus)} busser, "
        f"{len(grid.line)} linjer, "
        f"{len(grid.trafo)} trafoer, "
        f"{len(grid.gen)} generatorer"
    )

    net = PandapowerNewtonRaphson(grid)