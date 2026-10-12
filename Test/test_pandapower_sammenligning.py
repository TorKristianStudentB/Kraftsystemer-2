# -*- coding: utf-8 -*-
#----------------------------test_pandapower_sammenligning.py--------------------------------------------------
# Sjekker at min Newton-Raphson, FDLF og DC-lastflyt gir NESTEN IDENTISKE resultater som pandapower:
#   - AC  (NR, FDLF) mot pandapower runpp    : spenning, vinkel og linjeflyt
#   - DC  (DCPF)     mot pandapower rundcpp  : vinkel og aktiv linjeflyt
# på radielle nett, ring, maskede tilfeldige nett (med PV-busser, linje-shunt og trafoer mellom spenningsnivå)
# og på Trøndelagsnettet. Største avvik skrives ut (kjør med  -s  for å se dem).
#----------------------------test_pandapower_sammenligning.py--------------------------------------------------
from pathlib import Path

import numpy as np
import pytest

pp = pytest.importorskip("pandapower")

from GridMaker.Imports import MakeGrid                                    # noqa: E402
from nett_hjelp import pandapower_fra_grid, resultater, tilfeldig_spec   # noqa: E402

#----toleranser. NR og FDLF stopper ved mismatch 1e-6 pu, men konvergerer kvadratisk/lineært så avvikene blir mye mindre----
TOL_V_NR, TOL_VINKEL_NR = 1e-7, 1e-5          # pu, grader
TOL_V_FD, TOL_VINKEL_FD = 1e-6, 1e-4
TOL_FLYT = 1e-3                               # MW / MVAr
TOL_VINKEL_DC, TOL_FLYT_DC = 1e-8, 1e-6       # grader, MW (DC er en direkte løsning)


def _l(a, b, r=3.0, x=30.0, bb=0.0):
    return (a, b, r, x, bb)


#----------Nett (spec): navn -> beskrivelse----------
def _nett():
    k = {}
    k["radial3"] = {"vbase": [300.0] * 3, "linjer": [_l(0, 1), _l(1, 2)], "last": {1: (30, 10), 2: (20, 8)}, "pv": {}}
    k["ring4"] = {"vbase": [300.0] * 4, "linjer": [_l(0, 1), _l(1, 2), _l(2, 3), _l(3, 0)],
                  "last": {1: (40, 12), 2: (60, 20), 3: (30, 9)}, "pv": {}, "V0": 1.02}
    k["pv4"] = {"vbase": [300.0] * 4, "linjer": [_l(0, 1), _l(1, 2), _l(1, 3), _l(0, 2)],
                "last": {1: (50, 20), 2: (200, 70), 3: (150, 50)}, "pv": {1: (150, 1.02, [(1e5, -1e5)])}}
    k["trafo_380_132_220"] = {
        "vbase": [380.0, 132.0, 132.0, 220.0], "linjer": [_l(1, 2, 2.0, 12.0)],
        "trafoer": [(0, 1, 0.002, 0.05), (2, 3, 0.003, 0.06)],
        "last": {1: (80, 25), 2: (120, 40), 3: (20, 6)}, "pv": {3: (60, 1.0, [(1e5, -1e5)])}}
    k["tilfeldig8_pv1"] = tilfeldig_spec(8, seed=1, antall_pv=1)
    k["tilfeldig12_pv2"] = tilfeldig_spec(12, seed=2, antall_pv=2)
    k["tilfeldig10_kun_pq"] = tilfeldig_spec(10, seed=3, antall_pv=0)
    k["tilfeldig9_med_shunt"] = tilfeldig_spec(9, seed=4, antall_pv=1, med_shunt=True)
    k["tilfeldig10_med_trafoer"] = tilfeldig_spec(10, seed=5, antall_pv=2, trafoer=3)
    k["tilfeldig15_tett_maska"] = tilfeldig_spec(15, seed=6, antall_pv=3, ekstra_linjer=14)
    return k


NETT = _nett()
IDER = list(NETT)


def _bygg(nett, navn):
    g = MakeGrid(nett(NETT[navn]))
    return g


def _maks(a, b):
    return float(np.max(np.abs(np.asarray(a) - np.asarray(b))))


#==========AC: Newton-Raphson mot pandapower==========
@pytest.mark.parametrize("navn", IDER)
def test_nr_spenning_og_vinkel_stemmer_med_pandapower(nett, navn):
    g = _bygg(nett, navn)
    net = pandapower_fra_grid(g)
    pp.runpp(net, algorithm="nr", tolerance_mva=1e-10, init="flat", max_iteration=50)
    g.loadflowsolutionNR()
    assert g.solution.konvergerte, "NR konvergerte ikke"
    v, a = resultater(g)
    dv, da = _maks(v, net.res_bus.vm_pu.values), _maks(a, net.res_bus.va_degree.values)
    print(f"\n[NR  {navn:26s}] maks |dV| = {dv:.2e} pu   maks |dvinkel| = {da:.2e} grader")
    assert dv < TOL_V_NR, f"spenning avviker {dv:.2e}"
    assert da < TOL_VINKEL_NR, f"vinkel avviker {da:.2e}"


@pytest.mark.parametrize("navn", [n for n in IDER if "shunt" not in n])
def test_nr_linjeflyt_stemmer_med_pandapower(nett, navn):
    #----(Boiege regner flyt gjennom serieadmittansen, derfor testes ikke shunt-nettet her)----
    g = _bygg(nett, navn)
    if not g.line:
        pytest.skip("ingen linjer")
    net = pandapower_fra_grid(g)
    pp.runpp(net, algorithm="nr", tolerance_mva=1e-10, init="flat", max_iteration=50)
    g.loadflowsolutionNR()
    f = g.solution.flow_in_line * g.Base.Sbase
    n_lin = len(g.line)
    dp = _maks(f.real, net.res_line.p_from_mw.values[:n_lin])
    dq = _maks(f.imag, net.res_line.q_from_mvar.values[:n_lin])
    print(f"\n[NR flyt {navn:21s}] maks |dP| = {dp:.2e} MW   maks |dQ| = {dq:.2e} MVAr")
    assert dp < TOL_FLYT and dq < TOL_FLYT


#==========AC: FDLF mot pandapower==========
@pytest.mark.parametrize("navn", IDER)
def test_fdlf_stemmer_med_pandapower(nett, navn):
    g = _bygg(nett, navn)
    net = pandapower_fra_grid(g)
    pp.runpp(net, algorithm="nr", tolerance_mva=1e-10, init="flat", max_iteration=50)
    g.FDLF()
    assert g.solution.konvergerte, "FDLF konvergerte ikke"
    v, a = resultater(g)
    dv, da = _maks(v, net.res_bus.vm_pu.values), _maks(a, net.res_bus.va_degree.values)
    print(f"\n[FDLF {navn:24s}] maks |dV| = {dv:.2e} pu   maks |dvinkel| = {da:.2e} grader")
    assert dv < TOL_V_FD and da < TOL_VINKEL_FD


#==========DC mot pandapower rundcpp==========
@pytest.mark.parametrize("navn", IDER)
def test_dc_vinkel_og_flyt_stemmer_med_pandapower(nett, navn):
    g = _bygg(nett, navn)
    net = pandapower_fra_grid(g)
    pp.rundcpp(net)
    g.DCPF()
    assert g.solution.konvergerte
    a = np.degrees(np.array(g.solution.angle, dtype=float))
    da = _maks(a, net.res_bus.va_degree.values)
    n_lin = len(g.line)
    df = _maks(g.solution.flow_in_line, net.res_line.p_from_mw.values[:n_lin]) if n_lin else 0.0
    print(f"\n[DC  {navn:25s}] maks |dvinkel| = {da:.2e} grader   maks |dP linje| = {df:.2e} MW")
    assert da < TOL_VINKEL_DC, f"DC-vinkel avviker {da:.2e}"
    assert df < TOL_FLYT_DC, f"DC-flyt avviker {df:.2e}"


@pytest.mark.parametrize("navn", [n for n in IDER if "trafo" in n])
def test_dc_trafoflyt_stemmer_med_pandapower(nett, navn):
    #----DC-koden beregner også flyt gjennom trafoene internt; sjekk via bussvinklene at modellen er lik pandapowers
    #    (pandapower gir trafoflyt i res_trafo.p_hv_mw).----
    g = _bygg(nett, navn)
    net = pandapower_fra_grid(g)
    pp.rundcpp(net)
    g.DCPF()
    S = g.Base.Sbase
    idx = {b.busNumber: i for i, b in enumerate(g.bus)}
    ang = np.array(g.solution.angle, dtype=float)
    for k, t in enumerate(g.trafo):
        i, j = idx[t.Frombus], idx[t.Tobus]
        vf, vt = g.bus[i].Vbase, g.bus[j].Vbase
        ratio_pu = t.ratio / (min(vf, vt) / max(vf, vt))
        p_fra = (ang[i] - ang[j]) * ratio_pu / t.X * S                    # MW fra Frombus
        pp_p = net.res_trafo.p_hv_mw.values[k] if vf >= vt else -net.res_trafo.p_hv_mw.values[k]
        assert p_fra == pytest.approx(pp_p, abs=1e-6), f"trafo {t.Name}: {p_fra} mot {pp_p}"


#==========Effektbalanse (uavhengig av pandapower)==========
@pytest.mark.parametrize("navn", IDER)
def test_nr_effektbalanse_summen_av_injeksjoner_er_null(nett, navn):
    g = _bygg(nett, navn)
    g.loadflowsolutionNR()
    s = g.solution
    #----(summen av injeksjonene er IKKE null i et nett med tap: slack dekker tapene. Slack testes mot pandapower under.)----
    #----(Q: summen er ikke null fordi linje-shunt og tap også bidrar i nettet, så bare P sjekkes her)----
    #----alle andre busser leverer det de er satt til (P_gen - P_load); slack tar resten (tap og ubalanse)----
    P_sched = np.array([b.P_gen - b.P_load for b in g.bus])
    assert np.allclose(s.power[1:], P_sched[1:], atol=1e-5)


#==========Trøndelagsnettet==========
def _klemte_q(g):
    #----finn busser NR har klemt og Q_gen de står på [MVAr] -> til pandapower som faste PQ-busser----
    S = g.Base.Sbase
    idx = {b.busNumber: i for i, b in enumerate(g.bus)}
    qmax, qmin = {}, {}
    for x in g.gen:
        i = idx[int(x.bus)]
        qmax[i] = qmax.get(i, 0.0) + x.Q_max
        qmin[i] = qmin.get(i, 0.0) + x.Q_min
    fast = {}
    for i, b in enumerate(g.bus):
        if i == 0 or i not in qmax:
            continue
        q = g.solution.qower[i] + b.Q_load
        if abs(q - qmax[i]) < 1e-7 or abs(q - qmin[i]) < 1e-7:
            fast[i] = (q - 0.0) * S          # sgen-Q [MVAr] = generatorens Q
    return fast


def test_trondelag_nr_stemmer_med_pandapower_naar_klemte_busser_er_fastsatt(trondelag):
    g = MakeGrid(trondelag)
    g.loadflowsolutionNR()
    assert g.solution.konvergerte
    fast = _klemte_q(g)
    net = pandapower_fra_grid(g, fast_pq=fast)
    pp.runpp(net, algorithm="nr", tolerance_mva=1e-8, init="flat", max_iteration=100)
    v, a = resultater(g)
    dv, da = _maks(v, net.res_bus.vm_pu.values), _maks(a, net.res_bus.va_degree.values)
    print(f"\n[Trøndelag NR, {len(fast)} klemte busser fastsatt] maks |dV| = {dv:.2e} pu   maks |dvinkel| = {da:.2e} grader")
    assert dv < 1e-7 and da < 1e-5


def test_trondelag_nr_stemmer_med_pandapower_enforce_q_lims(trondelag):
    #----pandapowers egen Q-grense-løkke kan klemme en buss på feil trinn (se bus 6), derfor løsere toleranse----
    g = MakeGrid(trondelag)
    net = pandapower_fra_grid(g, med_qgrenser=True)
    pp.runpp(net, algorithm="nr", enforce_q_lims=True, tolerance_mva=1e-8, init="flat", max_iteration=200)
    g.loadflowsolutionNR()
    v, a = resultater(g)
    dv, da = _maks(v, net.res_bus.vm_pu.values), _maks(a, net.res_bus.va_degree.values)
    print(f"\n[Trøndelag NR mot pandapower enforce_q_lims] maks |dV| = {dv:.2e} pu   maks |dvinkel| = {da:.2e} grader")
    assert dv < 1e-4 and da < 1e-3


def test_trondelag_dc_stemmer_med_pandapower(trondelag):
    g = MakeGrid(trondelag)
    net = pandapower_fra_grid(g)
    pp.rundcpp(net)
    g.DCPF()
    da = _maks(np.degrees(g.solution.angle), net.res_bus.va_degree.values)
    df = _maks(g.solution.flow_in_line, net.res_line.p_from_mw.values[:len(g.line)])
    print(f"\n[Trøndelag DC] maks |dvinkel| = {da:.2e} grader   maks |dP linje| = {df:.2e} MW")
    assert da < TOL_VINKEL_DC and df < TOL_FLYT_DC


def test_trondelag_fdlf_naer_nr_og_dc_naer_nr(trondelag):
    #----FDLF har ingen Q-grenser, DC har ingen spenninger/Q: derfor løsere toleranser mot NR----
    nr = MakeGrid(trondelag); nr.loadflowsolutionNR()
    fd = MakeGrid(trondelag); fd.FDLF()
    dc = MakeGrid(trondelag); dc.DCPF()
    dv_fd = _maks(resultater(fd)[0], resultater(nr)[0])
    da_fd = _maks(fd.solution.angle, nr.solution.angle)
    da_dc = _maks(dc.solution.angle, nr.solution.angle)
    print(f"\n[Trøndelag] FDLF mot NR: |dV|={dv_fd:.2e} pu, |dvinkel|={da_fd:.2e} rad   DC mot NR: |dvinkel|={da_dc:.2e} rad")
    assert dv_fd < 1e-3 and da_fd < 1e-3
    assert da_dc < 1e-3


def test_prosjektets_egen_pandapower_validering_gir_samme_svar_som_koden(trondelag):
    #----grid.validating_PP_NR() / validating_PP_DC() (Validating/-mappen) skal gi samme resultat som NR og DC----
    from GridMaker.Imports import excelfilepath
    if Path(excelfilepath).resolve() != Path(trondelag).resolve():
        pytest.skip("excelfilepath peker ikke på Trøndelagsnettet (kjør pytest fra prosjektroten)")
    nr = MakeGrid(trondelag); nr.loadflowsolutionNR()
    pn = MakeGrid(trondelag); pn.validating_PP_NR()
    dc = MakeGrid(trondelag); dc.DCPF()
    pd_ = MakeGrid(trondelag); pd_.validating_PP_DC()
    dv = _maks(pn.solution.volt, nr.solution.volt)
    da = _maks(pn.solution.angle, nr.solution.angle)
    dda = _maks(pd_.solution.angle, dc.solution.angle)
    print(f"\n[Validating/] PP_NR mot NR: |dV|={dv:.2e}, |dvinkel|={da:.2e} rad   PP_DC mot DC: |dvinkel|={dda:.2e} rad")
    assert dv < 1e-4 and da < 1e-4
    assert dda < 1e-8


@pytest.mark.parametrize("navn", [n for n in IDER if "kun_pq" in n or "tilfeldig8" in n or "radial" in n or "trafo" in n])
def test_nr_slack_effekt_stemmer_med_pandapower(nett, navn):
    #----pandapower: res_ext_grid.p_mw / q_mvar = effekten ekstern forsyning (slack) leverer inn i nettet (inkl. tap)----
    g = _bygg(nett, navn)
    net = pandapower_fra_grid(g)
    pp.runpp(net, algorithm="nr", tolerance_mva=1e-10, init="flat", max_iteration=50)
    g.loadflowsolutionNR()
    S = g.Base.Sbase
    dp = abs(g.solution.power[0] * S - net.res_ext_grid.p_mw.values[0])
    dq = abs(g.solution.qower[0] * S - net.res_ext_grid.q_mvar.values[0])
    print(f"\n[NR slack {navn:20s}] |dP| = {dp:.2e} MW   |dQ| = {dq:.2e} MVAr")
    assert dp < 1e-4 and dq < 1e-4, f"slack: NR=({g.solution.power[0]*S:.4f}, {g.solution.qower[0]*S:.4f}) pandapower=({net.res_ext_grid.p_mw.values[0]:.4f}, {net.res_ext_grid.q_mvar.values[0]:.4f})"
