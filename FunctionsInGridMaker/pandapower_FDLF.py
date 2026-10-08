"""
Fast Decoupled Load Flow med pandapower, bygget på prosjektets Grid-objekt.

Bruk fra resten av prosjektet:
    grid.pandapower_FDLF()        (via Grid-klassen, se ClassGrid.py)

Kjøre filen direkte (gir output i terminalen):
    python FunctionsInGridMaker/pandapower_FDLF.py
    python FunctionsInGridMaker/pandapower_FDLF.py Grid/Nordic490_komplett.xlsx

Filen leser IKKE Excel selv. Grid-objektet er laget av
GridMaker.ReadExcelGrid.MakeGrid(), og alle verdier er allerede i p.u.
"""
import copy
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pandapower as pp
import pandapower.topology as top


# ======================================================================
# Bustyper
# ======================================================================
def hent_bustyper(grid):
    """
    Returnerer en liste med "ref" / "PV" / "PQ", i samme rekkefølge som grid.bus.

    Bruker bus.bus_type hvis gruppa har innført den (satt av
    Grid.classify_buses()). Ellers brukes samme regel som NR/DCPF/FDLF:
        rad 0 i bus-arket -> ref
        buss med generator i grid.gen -> PV
        resten -> PQ
    """
    if all(getattr(b, "bus_type", None) for b in grid.bus):
        return [b.bus_type for b in grid.bus]

    gen_busser = {int(g.bus) for g in grid.gen}
    typer = []
    for i, b in enumerate(grid.bus):
        if i == 0:
            typer.append("ref")
        elif b.busNumber in gen_busser:
            typer.append("PV")
        else:
            typer.append("PQ")
    return typer


# ======================================================================
# Bygge pandapower-nettet fra Grid-objektet
# ======================================================================
def _lag_busser(net, grid):
    bus_map = {}
    for bus in grid.bus:
        bus_map[bus.busNumber] = pp.create_bus(net, vn_kv=bus.Vbase, name=bus.Name)
    return bus_map


def _lag_linjer(net, grid, bus_map, sbase):
    """Linjer som impedanser (p.u.) + halve linjeladningen (B/2) som shunt i hver ende."""
    for line in grid.line:
        fra, til = bus_map[line.Frombus], bus_map[line.Tobus]
        pp.create_impedance(
            net, from_bus=fra, to_bus=til,
            rft_pu=line.R, xft_pu=line.X, rtf_pu=line.R, xtf_pu=line.X,
            sn_mva=sbase, name=f"Line {line.Frombus}-{line.Tobus}",
        )
        if line.B != 0:
            # I pandapower betyr positiv q_mvar at shunten absorberer Q.
            # B > 0 er kapasitiv, altså injeksjon -> negativt fortegn.
            q_halv = -(line.B / 2) * sbase
            pp.create_shunt(net, bus=fra, q_mvar=q_halv, name=f"Line charging {line.Frombus}-{line.Tobus} (fra)")
            pp.create_shunt(net, bus=til, q_mvar=q_halv, name=f"Line charging {line.Frombus}-{line.Tobus} (til)")


def _lag_trafoer(net, grid, bus_map, sbase):
    """Trafoer fra R/X (p.u.). Høyspent-siden finnes ut fra bussenes vn_kv."""
    for trafo in grid.trafo:
        fra, til = bus_map[trafo.Frombus], bus_map[trafo.Tobus]
        vn_fra = net.bus.at[fra, "vn_kv"]
        vn_til = net.bus.at[til, "vn_kv"]

        if vn_fra >= vn_til:
            hv, lv, vn_hv, vn_lv = fra, til, vn_fra, vn_til
        else:
            hv, lv, vn_hv, vn_lv = til, fra, vn_til, vn_fra

        pp.create_transformer_from_parameters(
            net, hv_bus=hv, lv_bus=lv, sn_mva=sbase,
            vn_hv_kv=vn_hv, vn_lv_kv=vn_lv,
            vk_percent=math.hypot(trafo.R, trafo.X) * 100,
            vkr_percent=trafo.R * 100,
            pfe_kw=0, i0_percent=0, shift_degree=0,
            name=f"Trafo {trafo.Frombus}-{trafo.Tobus}",
        )


def _lag_laster(net, grid, bus_map, sbase):
    for bus in grid.bus:
        if bus.P_load != 0 or bus.Q_load != 0:
            pp.create_load(
                net, bus=bus_map[bus.busNumber],
                p_mw=bus.P_load * sbase, q_mvar=bus.Q_load * sbase,
                name=f"Load bus {bus.busNumber}",
            )


def _q_grenser_per_bus(grid):
    """Summerer Q-grensene til generatorene som står på samme buss (p.u.)."""
    grenser = {}
    for g in grid.gen:
        if g.Q_max is None or g.Q_min is None:
            continue
        qmax, qmin = grenser.get(int(g.bus), (0.0, 0.0))
        grenser[int(g.bus)] = (qmax + g.Q_max, qmin + g.Q_min)
    return grenser


def _lag_slack_og_generatorer(net, grid, bus_map, sbase, bustyper):
    q_grenser = _q_grenser_per_bus(grid)
    antall_pv = 0

    for bus, typ in zip(grid.bus, bustyper):
        idx = bus_map[bus.busNumber]

        if typ == "ref":
            pp.create_ext_grid(
                net, bus=idx, vm_pu=bus.Volt,
                va_degree=np.degrees(bus.Angle), name="Slack bus",
            )
            print("Slack bus:", bus.busNumber, f"({bus.Name})")

        elif typ == "PV":
            kwargs = dict(
                net=net, bus=idx, p_mw=bus.P_gen * sbase,
                vm_pu=bus.Volt, name=f"Generator bus {bus.busNumber}",
            )
            if bus.busNumber in q_grenser:
                qmax, qmin = q_grenser[bus.busNumber]
                kwargs["max_q_mvar"] = qmax * sbase
                kwargs["min_q_mvar"] = qmin * sbase
            pp.create_gen(**kwargs)
            antall_pv += 1

    if len(net.ext_grid) == 0:
        raise ValueError("Fant ingen slack-buss (bus_type 'ref').")
    if antall_pv == 0:
        print("ADVARSEL: ingen PV-busser (ingen generatorer i grid.gen).")


def bygg_pandapower_nett(grid, bustyper):
    """Bygger hele pandapower-nettet. Returnerer (net, bus_map)."""
    sbase = grid.Base.Sbase
    net = pp.create_empty_network(sn_mva=sbase)

    bus_map = _lag_busser(net, grid)
    _lag_linjer(net, grid, bus_map, sbase)
    _lag_trafoer(net, grid, bus_map, sbase)
    _lag_laster(net, grid, bus_map, sbase)
    _lag_slack_og_generatorer(net, grid, bus_map, sbase, bustyper)
    return net, bus_map


def skriv_nettoppsummering(net, sbase):
    print("\n--- NETWORK SUMMARY ---")
    print("SBASE:", sbase, "MVA")
    print("Buses:", len(net.bus))
    print("Impedances (linjer):", len(net.impedance))
    print("Transformers:", len(net.trafo))
    print("Shunts (line charging):", len(net.shunt))
    print("Loads:", len(net.load))
    print("Generators (PV):", len(net.gen))
    print("External grids (slack):", len(net.ext_grid))

    if len(net.bus) == 0:
        raise ValueError("Ingen busser ble laget.")
    if len(net.trafo) == 0:
        print("ADVARSEL: nettet har ingen trafoer.")
    if len(net.load) == 0:
        print("ADVARSEL: nettet har ingen laster.")


def koble_ut_forsynte_busser(net):
    """Busser uten forbindelse til slack settes ut av drift. Returnerer listen."""
    uforsynte = sorted(top.unsupplied_buses(net))
    if uforsynte:
        net.bus.loc[uforsynte, "in_service"] = False
    print("\nBuses disabled as unsupplied (not connected to slack):", uforsynte)
    print("Active bus count:", int(net.bus["in_service"].sum()))
    return uforsynte


# ======================================================================
# Kjøre lastflyt
# ======================================================================
def kjor_fdlf(net):
    try:
        pp.runpp(
            net, algorithm="fdxb", calculate_voltage_angles=True,
            init="flat", max_iteration=50, tolerance_mva=1e-6,
        )
    except Exception as e:
        print("\nLoad flow failed:")
        print(type(e).__name__, e)
        raise
    print("\nSolver converged:", net.converged)
    return bool(net.converged)


# ======================================================================
# Hente resultater
# ======================================================================
def _summer_per_bus(df, bus_serie):
    """Summerer p_mw og q_mvar per pandapower-bus. Tom DataFrame hvis ingen elementer."""
    if df.empty:
        return pd.DataFrame(columns=["p_mw", "q_mvar"])
    d = df[["p_mw", "q_mvar"]].copy()
    d["bus"] = bus_serie
    return d.groupby("bus")[["p_mw", "q_mvar"]].sum()


def hent_effekt_per_bus(net):
    """Returnerer (gen_per_bus, last_per_bus, shunt_per_bus) i MW / MVAr."""
    gen = pd.concat(
        [
            net.res_gen[["p_mw", "q_mvar"]].assign(bus=net.gen["bus"]),
            net.res_ext_grid[["p_mw", "q_mvar"]].assign(bus=net.ext_grid["bus"]),
        ],
        ignore_index=True,
    )
    gen_per_bus = gen.groupby("bus")[["p_mw", "q_mvar"]].sum()
    last_per_bus = _summer_per_bus(net.res_load, net.load["bus"])
    shunt_per_bus = _summer_per_bus(net.res_shunt, net.shunt["bus"])
    return gen_per_bus, last_per_bus, shunt_per_bus


def _verdi(df, idx, kolonne):
    return df.at[idx, kolonne] if idx in df.index else 0.0


def beregn_mismatch(grid, net, bus_map, bustyper, slack_nummer, sbase):
    """
    dP (alle ikke-slack busser) og dQ (bare PQ) i p.u., som i NR:
        dP = P_spesifisert - P_beregnet     dQ = Q_spesifisert - Q_beregnet
    Linjeladning (shunt) regnes som last her, siden den ikke ligger i Q_load.
    """
    gen, last, shunt = hent_effekt_per_bus(net)
    mismatch = []

    for bus, typ in zip(grid.bus, bustyper):
        idx = bus_map[bus.busNumber]
        if bus.busNumber == slack_nummer or not net.bus.at[idx, "in_service"]:
            continue

        p_calc = (_verdi(gen, idx, "p_mw") - _verdi(last, idx, "p_mw") - _verdi(shunt, idx, "p_mw")) / sbase
        mismatch.append((bus.P_gen - bus.P_load) - p_calc)

        if typ == "PQ":
            q_calc = (_verdi(gen, idx, "q_mvar") - _verdi(last, idx, "q_mvar") - _verdi(shunt, idx, "q_mvar")) / sbase
            mismatch.append((bus.Q_gen - bus.Q_load) - q_calc)

    return np.array(mismatch)


def lagre_i_grid(grid, net, bus_map, bustyper, konvergerte, sbase):
    """Skriver resultatet til grid.solution, i samme format som NR."""
    n = len(grid.bus)

    if not konvergerte:
        grid.solution = grid.__class__.Solution(
            volt=np.full(n, np.nan), angle=np.full(n, np.nan),
            flow_in_line=np.array([]), iterasjoner=None, mismatch=np.array([]),
            konvergerte=False, pv_to_pq_generators=[],
            power=np.array([]), qower=np.array([]),
        )
        return

    volt = np.full(n, np.nan)
    angle = np.full(n, np.nan)
    for bus in grid.bus:
        idx = bus_map[bus.busNumber]
        if net.bus.at[idx, "in_service"]:
            k = bus.kodens_identifikasjonssystem
            volt[k] = net.res_bus.at[idx, "vm_pu"]
            angle[k] = np.radians(net.res_bus.at[idx, "va_degree"])   # Grid bruker radianer

    try:
        iterasjoner = int(net._ppc.get("iterations", 0))
    except (AttributeError, TypeError, ValueError):
        iterasjoner = None

    slack_nummer = next(b.busNumber for b, t in zip(grid.bus, bustyper) if t == "ref")
    mismatch = beregn_mismatch(grid, net, bus_map, bustyper, slack_nummer, sbase)

    grid.solution = grid.__class__.Solution(
        volt=volt, angle=angle, flow_in_line=np.array([]),
        iterasjoner=iterasjoner, mismatch=mismatch, konvergerte=True,
        pv_to_pq_generators=[], power=np.array([]), qower=np.array([]),
    )


def skriv_resultater(grid, net, bus_map, omrade):
    """Skriver resultattabell til terminalen (bare busser i valgt budområde, eller alle hvis None)."""
    gen, last, _ = hent_effekt_per_bus(net)
    rader = []

    for bus in grid.bus:
        if omrade is not None and bus.bidz != omrade:
            continue
        idx = bus_map[bus.busNumber]
        if not net.bus.at[idx, "in_service"]:
            continue
        rader.append({
            "bus_id": bus.busNumber,
            "name": bus.Name,
            "bidz": bus.bidz,
            "Vbase": bus.Vbase,
            "V [P.U.]": net.res_bus.at[idx, "vm_pu"],
            "Angle [degree]": net.res_bus.at[idx, "va_degree"],
            "P_gen [MW]": _verdi(gen, idx, "p_mw"),
            "Q_gen [MVAr]": _verdi(gen, idx, "q_mvar"),
            "P_load [MW]": _verdi(last, idx, "p_mw"),
            "Q_load [MVAr]": _verdi(last, idx, "q_mvar"),
        })

    if omrade is not None and not rader:
        print(f"\n(Ingen busser med bidz == '{omrade}', skriver ut alle busser)")
        return skriv_resultater(grid, net, bus_map, None)

    tittel = omrade if omrade is not None else "ALL BUSES"
    print(f"\n--- {tittel} CALCULATED POWER FLOW RESULTS ---")
    print(pd.DataFrame(rader).to_string(index=False, float_format=lambda x: f"{x:.5f}"))


# ======================================================================
# Hovedfunksjonen, kalles av Grid.FDLF_pandapower()
# ======================================================================
def pandapower_FDLF(grid, omrade="NO3", kopi=True):
    """
    Kjører FDLF med pandapower på et Grid-objekt.

    omrade : budområde som skrives ut ("NO3"), eller None for alle busser.
    kopi   : True  -> jobber på en deepcopy, så originalgridet er urørt
                      (viktig når flere løsere skal sammenlignes).
             False -> skriver resultatet rett på grid.solution.

    Returnerer Grid-objektet med resultatet i .solution.
    """
    if kopi:
        grid = copy.deepcopy(grid)

    sbase = grid.Base.Sbase
    bustyper = hent_bustyper(grid)

    net, bus_map = bygg_pandapower_nett(grid, bustyper)
    skriv_nettoppsummering(net, sbase)
    koble_ut_forsynte_busser(net)

    konvergerte = kjor_fdlf(net)
    lagre_i_grid(grid, net, bus_map, bustyper, konvergerte, sbase)

    if konvergerte:
        skriv_resultater(grid, net, bus_map, omrade)
    else:
        print("Load flow did not converge.")

    return grid


# ======================================================================
# Kjøres bare når du trykker Run på DENNE filen
# ======================================================================
if __name__ == "__main__":
    PROSJEKTROT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(PROSJEKTROT))          # så "GridMaker" finnes uansett hvor du kjører fra

    from GridMaker.Imports import MakeGrid        # må importeres via Imports (sirkulær import)

    excel = sys.argv[1] if len(sys.argv) > 1 else PROSJEKTROT / "Grid" / "test_trøndelagsnettet.xlsx"
    print("Leser nett fra:", excel)

    grid = MakeGrid(str(excel))
    losning = pandapower_FDLF(grid)

    s = losning.solution
    print("\n--- OPPSUMMERING ---")
    print("Konvergerte:", s.konvergerte)
    print("Iterasjoner:", s.iterasjoner)
    if s.konvergerte and len(s.mismatch) > 0:
        print("Maks |mismatch| [p.u.]:", np.max(np.abs(s.mismatch)))