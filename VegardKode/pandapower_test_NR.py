import pandas as pd
import pandapower as pp
from pathlib import Path
import numpy as np


#Denne koden henter inn et datasett fra en excelfil, forutsatt at den har de kolonnenavnene spesifisert i koden. Videre utfører den Newton Raphson med PandaSolver og lagrer den i en CSV-fil.

# ==========================================================
# INNSTILLINGER
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

EXCEL_FILE = (
    PROJECT_ROOT
    / "Grid"
    / "Nordic490_komplett.xlsx"
)

# VIKTIG!
# Velg hvordan R og X er oppgitt i Excel:
# "pu"  = per unit
# "ohm" = ohm
IMPEDANCE_UNIT = "pu"


# ==========================================================
# KONVERTER R OG X TIL P.U.
# ==========================================================

def impedance_to_pu(r, x, vbase_kv, sbase_mva):

    r = float(r)
    x = float(x)

    # Verdiene er allerede i p.u.
    if IMPEDANCE_UNIT == "pu":
        return r, x

    # Verdiene er i ohm
    elif IMPEDANCE_UNIT == "ohm":

        zbase = (vbase_kv ** 2) / sbase_mva

        r_pu = r / zbase
        x_pu = x / zbase

        return r_pu, x_pu

    else:
        raise ValueError(
            "IMPEDANCE_UNIT må være enten 'pu' eller 'ohm'"
        )


# ==========================================================
# HOVEDFUNKSJON
# ==========================================================

def run_excel_with_pandapower(excel_file):

    print("Starter programmet")

    # --------------------------------------------------
    # 1. Les Excel
    # --------------------------------------------------

    print("Leser Excel-fil...")

    df = pd.read_excel(
        excel_file,
        sheet_name=None
    )

    print("Excel-fil lest inn")
    print("Ark i filen:", df.keys())

    bus_df = df["bus"]
    line_df = df["line"]
    gen_df = df["gen"]
    trafo_df = df["trafo"]

    print("Antall busser:", len(bus_df))
    print("Antall linjer:", len(line_df))
    print("Antall generatorer i gen-arket:", len(gen_df))
    print("Antall transformatorer:", len(trafo_df))


    # --------------------------------------------------
    # 2. Les systembase fra Excel
    # --------------------------------------------------

    print("\nLeser systembase...")

    sbase_values = (
        bus_df["S_base [MVA]"]
        .dropna()
        .unique()
    )

    if len(sbase_values) == 0:
        raise ValueError(
            "Fant ingen verdi i kolonnen 'S_base [MVA]'."
        )

    if len(sbase_values) != 1:
        raise ValueError(
            f"Fant flere S_base-verdier i nettet: {sbase_values}"
        )

    SBASE_MVA = float(sbase_values[0])

    print("Systembase:", SBASE_MVA, "MVA")


    # --------------------------------------------------
    # 3. Lag tomt pandapower-nett
    # --------------------------------------------------

    print("\nLager tomt pandapower-nett...")

    net = pp.create_empty_network(
        sn_mva=SBASE_MVA
    )

    print("Tomt pandapower-nett opprettet")


    # --------------------------------------------------
    # 4. Lag busser
    # --------------------------------------------------

    print("\nOppretter busser...")

    bus_map = {}

    for _, row in bus_df.iterrows():

        bus_number = int(row["bus_id"])

        pp_bus = pp.create_bus(
            net,
            vn_kv=float(row["Vbase"]),
            name=row["name"]
        )

        bus_map[bus_number] = pp_bus

    print("Busser ferdig opprettet")
    print("Antall busser i pandapower:", len(net.bus))


    # --------------------------------------------------
    # 5. Lag laster
    # --------------------------------------------------

    print("\nOppretter laster...")

    for _, row in bus_df.iterrows():

        bus_number = int(row["bus_id"])

        p_load = float(row["P_load"])
        q_load = float(row["Q_load"])

        if p_load != 0 or q_load != 0:

            pp.create_load(
                net,
                bus=bus_map[bus_number],
                p_mw=p_load,
                q_mvar=q_load,
                name=f"Load bus {bus_number}"
            )

    print("Laster ferdig opprettet")
    print("Antall laster:", len(net.load))


    # --------------------------------------------------
    # 6. Slack + generatorer
    # --------------------------------------------------

    print("\nOppretter slack og generatorer...")

    slack_created = False

    for _, row in bus_df.iterrows():

        bus_number = int(row["bus_id"])

        p_gen = float(row["P_gen"])

        if p_gen == 0:
            continue

        vm_pu = float(row["V [P.U]"])

        # Første generatorbuss blir foreløpig slack
        if not slack_created:

            angle_rad = float(row["Angle [rad]"])

            pp.create_ext_grid(
                net,
                bus=bus_map[bus_number],
                vm_pu=vm_pu,
                va_degree=np.degrees(angle_rad),
                name=f"Slack bus {bus_number}"
            )

            print("Slack-buss:", bus_number)

            slack_created = True

        # Resten blir PV-busser
        else:

            pp.create_gen(
                net,
                bus=bus_map[bus_number],
                p_mw=p_gen,
                vm_pu=vm_pu,
                name=f"Generator bus {bus_number}"
            )

    print("Generatorer ferdig opprettet")
    print("Antall PV-generatorer:", len(net.gen))


    # --------------------------------------------------
    # 7. Lag linjer
    # --------------------------------------------------

    print("\nOppretter linjer...")
    print("Impedansenhet:", IMPEDANCE_UNIT)

    for _, row in line_df.iterrows():

        from_bus_number = int(row["bus0"])
        to_bus_number = int(row["bus1"])

        vbase_kv = float(row["Vbase"])

        r_pu, x_pu = impedance_to_pu(
            row["R"],
            row["X"],
            vbase_kv,
            SBASE_MVA
        )

        pp.create_impedance(
            net,

            from_bus=bus_map[from_bus_number],
            to_bus=bus_map[to_bus_number],

            rft_pu=r_pu,
            xft_pu=x_pu,

            rtf_pu=r_pu,
            xtf_pu=x_pu,

            sn_mva=SBASE_MVA,

            name=row["name"]
        )

    print("Linjer ferdig opprettet")
    print("Antall linjeimpedanser:", len(net.impedance))


    # --------------------------------------------------
    # 8. Lag transformatorer
    # --------------------------------------------------

    print("\nOppretter transformatorer...")

    for _, row in trafo_df.iterrows():

        bus0_number = int(row["bus0"])
        bus1_number = int(row["bus1"])

        bus0 = bus_map[bus0_number]
        bus1 = bus_map[bus1_number]

        # Finn spenningsnivåene fra bus-tabellen
        v0 = float(
            bus_df.loc[
                bus_df["bus_id"] == bus0_number,
                "Vbase"
            ].iloc[0]
        )

        v1 = float(
            bus_df.loc[
                bus_df["bus_id"] == bus1_number,
                "Vbase"
            ].iloc[0]
        )

        # Finn HV- og LV-side
        if v0 >= v1:

            hv_bus = bus0
            lv_bus = bus1

            vn_hv_kv = v0
            vn_lv_kv = v1

        else:

            hv_bus = bus1
            lv_bus = bus0

            vn_hv_kv = v1
            vn_lv_kv = v0


        # Konverter trafoimpedans
        r_pu, x_pu = impedance_to_pu(
            row["R"],
            row["X"],
            vn_hv_kv,
            SBASE_MVA
        )

        z_pu = np.sqrt(
            r_pu**2 + x_pu**2
        )

        vk_percent = z_pu * 100
        vkr_percent = r_pu * 100


        pp.create_transformer_from_parameters(
            net,

            hv_bus=hv_bus,
            lv_bus=lv_bus,

            sn_mva=SBASE_MVA,

            vn_hv_kv=vn_hv_kv,
            vn_lv_kv=vn_lv_kv,

            vk_percent=vk_percent,
            vkr_percent=vkr_percent,

            pfe_kw=0,
            i0_percent=0,

            shift_degree=0,

            name=row["name"]
        )

    print("Transformatorer ferdig opprettet")
    print("Antall transformatorer:", len(net.trafo))


    # --------------------------------------------------
    # 9. Kontroller nettet
    # --------------------------------------------------

    print("\nNettet er bygget:")
    print("Busser:", len(net.bus))
    print("Laster:", len(net.load))
    print("Generatorer:", len(net.gen))
    print("Slack:", len(net.ext_grid))
    print("Linjer/impedanser:", len(net.impedance))
    print("Transformatorer:", len(net.trafo))


    # --------------------------------------------------
    # 10. Kjør Newton-Raphson
    # --------------------------------------------------

    print("\nStarter Newton-Raphson...")

    pp.runpp(
        net,
        algorithm="nr",
        init="flat",
        calculate_voltage_angles=True,
        numba=False
    )

    print("Newton-Raphson ferdig")


    # --------------------------------------------------
    # 11. Resultater
    # --------------------------------------------------

    print("\n======================================")
    print("RESULTATER")
    print("======================================")

    print("\nKonvergert:", net.converged)

    results = net.res_bus[
        [
            "vm_pu",
            "va_degree",
            "p_mw",
            "q_mvar"
        ]
    ].copy()

    reverse_bus_map = {
        pp_index: bus_number
        for bus_number, pp_index in bus_map.items()
    }

    results.insert(
        0,
        "bus_id",
        [
            reverse_bus_map[index]
            for index in results.index
        ]
    )

    print("\nBus-resultater:")
    print(results)


    # --------------------------------------------------
    # 12. Lagre resultatene i CSV
    # --------------------------------------------------

    OUTPUT_CSV = (
        PROJECT_ROOT
        / "VegardKode"
        / "pandapower_bus_results_NR.csv"
    )

    results.to_csv(
        OUTPUT_CSV,
        index=False
    )

    print("\nResultater lagret til:")
    print(OUTPUT_CSV)

    return net


# ==========================================================
# KJØR PROGRAMMET
# ==========================================================

if __name__ == "__main__":

    net = run_excel_with_pandapower(
        EXCEL_FILE
    )