# -*- coding: utf-8 -*-
#----------------------------nett_hjelp.py--------------------------------------------------
# Hjelpefunksjoner for testene i Test/. IKKE en testfil.
#   - lag_nett(spec, sti)   : skriver et lite nett til xlsx (samme ark/kolonner som MakeGrid leser)
#   - pandapower_fra_grid() : bygger SAMME nett i pandapower, rett fra Grid-objektet
#   - resultater(grid)      : (|V|, vinkel i grader) fra grid.solution
#
# spec = {
#   "vbase": [kV pr. buss],                      (lengden bestemmer antall busser; bus 0 = slack)
#   "linjer": [(fra, til, R_ohm, X_ohm, B_pu), ...],
#   "trafoer": [(fra, til, R_pu, X_pu), ...]     (ratio settes til nominelt forhold lav/høy Vbase)
#   "last": {bus: (P_MW, Q_MVAr)},
#   "pv": {bus: (P_MW, V_pu, [(Qmax_MVAr, Qmin_MVAr), ...])},   (en tuppel pr. generator på bussen)
#   "V0": spenning på slack (pu)
# }
#----------------------------nett_hjelp.py--------------------------------------------------
import numpy as np
import pandas as pd

SBASE = 100.0
FREKVENS = 50.0


#----------Skriv et lite nett til xlsx----------
def lag_nett(spec, sti, uten_qgrenser=False, busnummer=None):
    n = len(spec["vbase"])
    nr = list(range(n)) if busnummer is None else list(busnummer)       # bus-id (kan være ulik indeks)
    last = spec.get("last", {})
    pv = spec.get("pv", {})
    bus = pd.DataFrame({
        "bus_id": nr, "name": [f"b{i}" for i in range(n)], "bidz": ["NO1"] * n,
        "Vbase": [float(v) for v in spec["vbase"]],
        "V [P.U]": [spec.get("V0", 1.0) if i == 0 else (pv[i][1] if i in pv else 1.0) for i in range(n)],
        "Angle [rad]": [0.0] * n, "S_base [MVA] ": [SBASE] * n,
        "P_gen": [float(pv[i][0]) if i in pv else 0.0 for i in range(n)], "Q_gen": [0.0] * n,
        "P_load": [float(last[i][0]) if i in last else 0.0 for i in range(n)],
        "Q_load": [float(last[i][1]) if i in last else 0.0 for i in range(n)],
    })
    lin = spec.get("linjer", [])
    line = pd.DataFrame({
        "line_id": list(range(len(lin))), "name": [f"L{i}" for i in range(len(lin))],
        "R": [float(l[2]) for l in lin], "X": [float(l[3]) for l in lin], "B": [float(l[4]) for l in lin],
        "bus0": [nr[l[0]] for l in lin], "bus1": [nr[l[1]] for l in lin], "length": [1.0] * len(lin),
        "Vbase": [float(spec["vbase"][l[0]]) for l in lin]})
    tr = spec.get("trafoer", [])
    trafo = pd.DataFrame({
        "name": [f"T{i}" for i in range(len(tr))],
        "ratio": [min(spec["vbase"][t[0]], spec["vbase"][t[1]]) / max(spec["vbase"][t[0]], spec["vbase"][t[1]]) for t in tr],
        "bus0": [nr[t[0]] for t in tr], "bus1": [nr[t[1]] for t in tr],
        "R": [float(t[2]) for t in tr], "X": [float(t[3]) for t in tr]})
    #----generatorer: slack (bus 0) + hver generator på PV-bussene----
    navn, gbus, pmax, qmax, qmin = ["G0"], [nr[0]], [1000.0], [1e5], [-1e5]
    for b, (p, v, grenser) in pv.items():
        for k, (qx, qn) in enumerate(grenser):
            navn.append(f"G{b}_{k}")
            gbus.append(nr[b])
            pmax.append(1000.0)
            qmax.append(qx)
            qmin.append(qn)
    gen = pd.DataFrame({"name": navn, "bus": gbus, "Pmax": pmax, "Qmax": qmax, "Qmin": qmin})
    if uten_qgrenser:
        gen = gen.drop(columns=["Qmax", "Qmin"])
    with pd.ExcelWriter(sti, engine="openpyxl") as w:
        bus.to_excel(w, sheet_name="bus", index=False)
        line.to_excel(w, sheet_name="line", index=False)
        trafo.to_excel(w, sheet_name="trafo", index=False)
        gen.to_excel(w, sheet_name="gen", index=False)
    return sti


#----------Samme nett i pandapower, bygget fra Grid-objektet (virker også på Trøndelagsnettet)----------
def pandapower_fra_grid(grid, med_qgrenser=False, fast_pq=None):
    #----med_qgrenser: PV-generatorene får Qmax/Qmin (summert pr. buss).
    #    fast_pq: {bussindeks: Q_gen i MVAr} -> disse bussene gjøres til faste PQ-busser (sgen) med gitt Q,
    #    slik at pandapowers egen Q-grense-løkke ikke er med i sammenligningen.----
    import pandapower as pp
    S = grid.Base.Sbase
    idx = {b.busNumber: i for i, b in enumerate(grid.bus)}
    fast_pq = fast_pq or {}
    net = pp.create_empty_network(f_hz=FREKVENS)
    for b in grid.bus:
        pp.create_bus(net, vn_kv=b.Vbase)
    pp.create_ext_grid(net, 0, vm_pu=grid.bus[0].Volt, va_degree=0.0)
    qmax, qmin = {}, {}
    for g in grid.gen:
        i = idx[int(g.bus)]
        if g.Q_max is not None and g.Q_min is not None:
            qmax[i] = qmax.get(i, 0.0) + g.Q_max * S
            qmin[i] = qmin.get(i, 0.0) + g.Q_min * S
        else:
            qmax.setdefault(i, np.nan)
            qmin.setdefault(i, np.nan)
    gen_busser = {idx[int(g.bus)] for g in grid.gen}
    for i, b in enumerate(grid.bus):
        if b.P_load or b.Q_load:
            pp.create_load(net, i, p_mw=b.P_load * S, q_mvar=b.Q_load * S)
        if i == 0:
            continue
        if i in fast_pq:
            pp.create_sgen(net, i, p_mw=b.P_gen * S, q_mvar=fast_pq[i])
        elif i in gen_busser:
            kw = {}
            if med_qgrenser and not np.isnan(qmax[i]):
                kw = {"max_q_mvar": qmax[i], "min_q_mvar": qmin[i]}
            pp.create_gen(net, i, p_mw=b.P_gen * S, vm_pu=b.Volt, **kw)
        elif b.P_gen:
            pp.create_sgen(net, i, p_mw=b.P_gen * S, q_mvar=b.Q_gen * S)
    for l in grid.line:
        i, j = idx[l.Frombus], idx[l.Tobus]
        zb = grid.bus[i].Vbase ** 2 / S
        pp.create_line_from_parameters(
            net, i, j, 1.0, r_ohm_per_km=l.R * zb, x_ohm_per_km=l.X * zb,
            c_nf_per_km=(l.B / zb) / (2 * np.pi * FREKVENS) * 1e9, max_i_ka=100.0)
    for t in grid.trafo:
        i, j = idx[t.Frombus], idx[t.Tobus]
        hv, lv = (i, j) if grid.bus[i].Vbase >= grid.bus[j].Vbase else (j, i)
        pp.create_transformer_from_parameters(
            net, hv_bus=hv, lv_bus=lv, sn_mva=S, vn_hv_kv=grid.bus[hv].Vbase, vn_lv_kv=grid.bus[lv].Vbase,
            vk_percent=abs(complex(t.R, t.X)) * 100, vkr_percent=t.R * 100, pfe_kw=0, i0_percent=0)
    return net


def resultater(grid):
    s = grid.solution
    return np.abs(np.array(s.volt, dtype=complex)).real, np.degrees(np.array(s.angle, dtype=float))


#----------Tilfeldig sammenhengende, maska nett (seedet -> deterministisk)----------
def tilfeldig_spec(n, seed, antall_pv=1, ekstra_linjer=None, med_shunt=False, trafoer=0):
    rng = np.random.default_rng(seed)
    vbase = [300.0] * n
    linjer = []
    for i in range(1, n):                         # tre -> garantert sammenhengende
        j = int(rng.integers(0, i))
        linjer.append((j, i, float(rng.uniform(1, 4)), float(rng.uniform(20, 40)),
                       float(rng.uniform(0.0, 0.03)) if med_shunt else 0.0))
    for _ in range(n // 2 if ekstra_linjer is None else ekstra_linjer):
        a, b = rng.choice(n, size=2, replace=False)
        linjer.append((int(a), int(b), float(rng.uniform(1, 4)), float(rng.uniform(20, 40)),
                       float(rng.uniform(0.0, 0.03)) if med_shunt else 0.0))
    #----trafoer: bytt noen "linjer" til trafoer mellom 300 og 132 kV (egen spenningsnivå-bus)----
    trafo_liste = []
    for k in range(trafoer):
        ny_bus = len(vbase)
        vbase.append(132.0)
        fra = int(rng.integers(1, n))
        trafo_liste.append((fra, ny_bus, 0.002, float(rng.uniform(0.04, 0.08))))
    nn = len(vbase)
    pvb = list(rng.choice(np.arange(1, n), size=antall_pv, replace=False)) if antall_pv else []
    pv = {int(b): (float(rng.uniform(20, 80)), float(rng.uniform(1.0, 1.03)), [(1e5, -1e5)]) for b in pvb}
    last = {i: (float(rng.uniform(5, 40)), float(rng.uniform(1, 12))) for i in range(1, nn) if i not in pv}
    return {"vbase": vbase, "linjer": linjer, "trafoer": trafo_liste, "last": last, "pv": pv, "V0": 1.0}
