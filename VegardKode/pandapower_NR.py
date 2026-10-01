import copy
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pandapower as pp


# ============================================================
# FILSTIER / IMPORTER
# ============================================================

# Kraftsystemer-2
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# MakeGridFromFile.py ligger i TorKode
TORKODE_FOLDER = PROJECT_ROOT / "TorKode"
sys.path.append(str(TORKODE_FOLDER))

from MakeGridFromFile import MakeGrid


# ============================================================
# PANDAPOWER NEWTON-RAPHSON
# ============================================================

def PandapowerNewtonRaphson(grid):

    g = copy.deepcopy(grid)

    Sbase = float(g.Base.Sbase)
    Y = g.admittansmatrise()

    net = pp.create_empty_network(sn_mva=Sbase)


    # --------------------------------------------------------
    # Klassifiser busser
    #
    # index 0       -> slack/ref
    # generatorbuss -> PV
    # resten        -> PQ
    # --------------------------------------------------------

    bus_types = []

    for i, bus in enumerate(g.bus):

        if i == 0:
            bus_types.append("ref")

        elif np.all(np.isclose(Y[i, :], 0)):
            bus_types.append("alene")

        elif any(
            int(gen.bus) == int(bus.busNumber)
            for gen in g.gen
        ):
            bus_types.append("PV")

        else:
            bus_types.append("PQ")


    # --------------------------------------------------------
    # Opprett busser
    #
    # bus_map:
    # busNumber -> pandapower bus index
    # --------------------------------------------------------

    bus_map = {}

    for i, bus in enumerate(g.bus):

        bus_map[int(bus.busNumber)] = pp.create_bus(
            net,
            vn_kv=float(bus.Vbase),
            name=str(bus.Name),
            in_service=(bus_types[i] != "alene")
        )


    # --------------------------------------------------------
    # Laster
    #
    # MakeGrid har allerede gjort P/Q om til pu,
    # så vi ganger med Sbase for å få MW/MVAr igjen.
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # Slack
    # --------------------------------------------------------

    slack = g.bus[0]

    pp.create_ext_grid(
        net,
        bus=bus_map[int(slack.busNumber)],
        vm_pu=float(abs(slack.Volt)),
        va_degree=float(np.degrees(slack.Angle))
    )


    # --------------------------------------------------------
    # Generatorer
    # --------------------------------------------------------

    for i, bus in enumerate(g.bus):

        # PV-buss
        if bus_types[i] == "PV":

            p_gen = float(np.nan_to_num(bus.P_gen)) * Sbase

            pp.create_gen(
                net,
                bus=bus_map[int(bus.busNumber)],
                p_mw=p_gen,
                vm_pu=float(abs(bus.Volt))
            )


        # PQ-buss med eventuell fast produksjon
        elif bus_types[i] == "PQ":

            p_gen = float(np.nan_to_num(bus.P_gen)) * Sbase
            q_gen = float(np.nan_to_num(bus.Q_gen)) * Sbase

            if p_gen != 0 or q_gen != 0:

                pp.create_sgen(
                    net,
                    bus=bus_map[int(bus.busNumber)],
                    p_mw=p_gen,
                    q_mvar=q_gen
                )


    # --------------------------------------------------------
    # Linjer
    #
    # Egen Y-bus bruker pi-modell:
    #
    #       y + jB/2       -y
    #       -y          y + jB/2
    #
    # der:
    #
    # y = 1 / (R + jX)
    #
    # R og X er allerede i pu etter MakeGrid.
    #
    # B brukes direkte i admittansmatrise.py, så vi gjør
    # det samme her for å sammenligne identiske modeller.
    # --------------------------------------------------------

    for line in g.line:

        # Serieimpedans R + jX
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

        # ----------------------------------------------------
        # Shuntsusceptans
        #
        # Egen Y-bus:
        #
        # yshunt = jB
        #
        # og legger jB/2 på hver diagonal.
        #
        # Pandapower shunt bruker q_mvar.
        #
        # +jB i Y-bus tilsvarer kapasitiv Q:
        #
        # Q = -B * V^2
        #
        # Ved V = 1 pu blir derfor:
        #
        # q_mvar = -(B/2) * Sbase
        # ----------------------------------------------------

        B = float(np.nan_to_num(line.B))

        if B != 0:

            q_shunt_mvar = -(B / 2.0) * Sbase

            pp.create_shunt(
                net,
                bus=bus_map[int(line.Frombus)],
                q_mvar=q_shunt_mvar,
                p_mw=0.0
            )

            pp.create_shunt(
                net,
                bus=bus_map[int(line.Tobus)],
                q_mvar=q_shunt_mvar,
                p_mw=0.0
            )


    # --------------------------------------------------------
    # Transformatorer
    #
    # OBS:
    # Egen admittansmatrise bruker trafo.ratio.
    #
    # Denne pandapower-modellen bruker foreløpig bare R og X,
    # altså IKKE ratio.
    #
    # Dette må oppdateres separat dersom pandapower og egen
    # Y-bus skal være helt identiske.
    # --------------------------------------------------------

    for trafo in g.trafo:

        pp.create_impedance(
            net,
            from_bus=bus_map[int(trafo.Frombus)],
            to_bus=bus_map[int(trafo.Tobus)],
            rft_pu=float(trafo.R),
            xft_pu=float(trafo.X),
            rtf_pu=float(trafo.R),
            xtf_pu=float(trafo.X),
            sn_mva=Sbase
        )


    # --------------------------------------------------------
    # Kjør Newton-Raphson
    # --------------------------------------------------------

    print("\nStarter Newton-Raphson med pandapower...")

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


    # --------------------------------------------------------
    # Print resultat
    # --------------------------------------------------------

    print("\n======================================================================")
    print("NEWTON-RAPHSON RESULTAT FRA PANDAPOWER")
    print("======================================================================")

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

            print(
                f"{bus.busNumber:>6}"
                f"{'alene':>7}"
            )

            continue

        pp_bus = bus_map[int(bus.busNumber)]
        result = net.res_bus.loc[pp_bus]

        print(
            f"{bus.busNumber:>6}"
            f"{bus_types[i]:>7}"
            f"{result['vm_pu']:>12.5f}"
            f"{result['va_degree']:>16.5f}"
            f"{result['p_mw']:>14.4f}"
            f"{result['q_mvar']:>14.4f}"
        )


    # --------------------------------------------------------
    # Slack-resultat
    # --------------------------------------------------------

    print("\nSLACK")

    print(
        net.res_ext_grid[
            ["p_mw", "q_mvar"]
        ]
    )


    # --------------------------------------------------------
    # PV-generatorresultater
    # --------------------------------------------------------

    if len(net.gen) > 0:

        print("\nPV-GENERATORER")

        print(
            net.res_gen[
                [
                    "p_mw",
                    "q_mvar",
                    "vm_pu",
                    "va_degree"
                ]
            ]
        )


    return net


# ============================================================
# KJØR FILA DIREKTE
# ============================================================

if __name__ == "__main__":

    excel_file = (
        PROJECT_ROOT
        / "Grid"
        / "test_trøndelagsnettet.xlsx"
    )

    print("Leser:", excel_file)

    df = pd.read_excel(
        excel_file,
        sheet_name=None
    )

    print("Lager grid-objekt...")

    grid = MakeGrid(df)

    print(
        f"Grid laget: "
        f"{len(grid.bus)} busser, "
        f"{len(grid.line)} linjer, "
        f"{len(grid.trafo)} trafoer, "
        f"{len(grid.gen)} generatorer"
    )

    # --------------------------------------------------------
    # Kjør pandapower
    # --------------------------------------------------------

    net = PandapowerNewtonRaphson(grid)


    # --------------------------------------------------------
    # Debug: vis linjedata som faktisk ligger i objektene
    # --------------------------------------------------------

    print("\nLINJEDATA:")

    for line in grid.line:

        print(
            f"{line.Frombus:>6} -> "
            f"{line.Tobus:<6} "
            f"R={line.R:.10e}  "
            f"X={line.X:.10e}  "
            f"B={line.B:.10e}"
        )