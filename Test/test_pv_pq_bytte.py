# -*- coding: utf-8 -*-
#----------------------------test_pv_pq_bytte.py--------------------------------------------------
# Tester at Newton-Raphson klarer å
#   1) bytte en generatorbuss fra PV til PQ når Q overstiger Qmax eller understiger Qmin (klemming),
#   2) summere Q-grensene når flere generatorer står på samme buss,
#   3) slippe en buss TILBAKE til PV hvis den ble klemt for tidlig og spenningen senere tilsier det,
#   4) la være å klemme når grensene ikke brytes (eller mangler).
# Resultatene sjekkes mot pandapower (enforce_q_lims) og mot fysiske krav (Q = grense, V på riktig side).
#----------------------------test_pv_pq_bytte.py--------------------------------------------------
import sys

import numpy as np
import pytest

pp = pytest.importorskip("pandapower")

from GridMaker.Imports import MakeGrid                         # noqa: E402
from nett_hjelp import pandapower_fra_grid, resultater, SBASE  # noqa: E402

LAV, HOY = 1e5, -1e5       # "ingen grense"


#----------4-buss-nettet fra pandapower-validering: slack, PV (bus 1) og to laster. Bus 1 trenger ca. 226 MVAr.----------
def _fire_buss(qgrenser):
    return {"vbase": [300.0] * 4,
            "linjer": [(0, 1, 3.0, 30.0, 0.0), (1, 2, 3.0, 30.0, 0.0), (1, 3, 3.0, 30.0, 0.0), (0, 2, 3.0, 30.0, 0.0)],
            "last": {1: (50.0, 20.0), 2: (200.0, 70.0), 3: (150.0, 50.0)},
            "pv": {1: (150.0, 1.02, qgrenser)}, "V0": 1.0}


#----------Radialt nett der PV-bussen først ser et STORT Q-behov (flat start) som forsvinner når nettet konvergerer----------
def _tidlig_klemt(qmax):
    return {"vbase": [300.0] * 3, "linjer": [(0, 1, 1.0, 20.0, 0.0), (1, 2, 1.0, 20.0, 0.0)],
            "last": {1: (60.0, 20.0)}, "pv": {2: (30.0, 1.05, [(qmax, -1e5)])}, "V0": 1.0}


def _kjor(sti):
    g = MakeGrid(sti)
    g.loadflowsolutionNR()
    return g


def _q_gen(g, i):
    #----generatorenes samlede Q på bussen [MVAr] = netto Q-injeksjon + last----
    return (g.solution.qower[i] + g.bus[i].Q_load) * g.Base.Sbase


#==========1) PV -> PQ ved Qmax==========
def test_bytter_fra_pv_til_pq_naar_qmax_overstiges(nett):
    g = _kjor(nett(_fire_buss([(150.0, -150.0)])))               # bussen trenger ca. 226 MVAr > 150
    assert g.solution.konvergerte
    assert len(g.solution.pv_to_pq_generators) == 1               # bussen ble klemt
    assert _q_gen(g, 1) == pytest.approx(150.0, abs=1e-6)         # Q ligger på grensen
    assert g.solution.volt[1] < 1.02 - 1e-6                       # klemt ved Qmax -> spenningen kan ikke holdes


def test_klemt_losning_stemmer_med_pandapower_enforce_q_lims(nett):
    g = _kjor(nett(_fire_buss([(150.0, -150.0)])))
    net = pandapower_fra_grid(g, med_qgrenser=True)
    pp.runpp(net, enforce_q_lims=True, tolerance_mva=1e-10, init="flat", max_iteration=100)
    v, a = resultater(g)
    assert np.allclose(v, net.res_bus.vm_pu.values, atol=1e-8, rtol=0)
    assert np.allclose(a, net.res_bus.va_degree.values, atol=1e-6, rtol=0)


#==========1b) PV -> PQ ved Qmin==========
def test_bytter_fra_pv_til_pq_naar_qmin_understiges(nett):
    #----PV-bussen har LAVERE settpunkt enn naboene og må absorbere mye Q, men tillates bare å absorbere litt----
    spec = {"vbase": [300.0] * 3, "linjer": [(0, 1, 1.0, 20.0, 0.0), (1, 2, 1.0, 20.0, 0.0)],
            "last": {1: (60.0, 5.0)}, "pv": {2: (30.0, 0.97, [(1e5, -20.0)])}, "V0": 1.0}
    g = _kjor(nett(spec))
    assert g.solution.konvergerte
    assert len(g.solution.pv_to_pq_generators) == 1
    assert _q_gen(g, 2) == pytest.approx(-20.0, abs=1e-6)         # Q ligger på Qmin
    assert g.solution.volt[2] > 0.97 + 1e-6                       # klemt ved Qmin -> spenningen ligger OVER settpunktet
    net = pandapower_fra_grid(g, med_qgrenser=True)
    pp.runpp(net, enforce_q_lims=True, tolerance_mva=1e-10, init="flat", max_iteration=100)
    assert np.allclose(resultater(g)[0], net.res_bus.vm_pu.values, atol=1e-8, rtol=0)


#==========2) Flere generatorer på samme buss: grensene summeres==========
def test_q_grenser_summeres_for_generatorer_paa_samme_buss(nett):
    #----2 x 120 = 240 MVAr > behovet (ca. 226) -> ingen klemming----
    g_ok = _kjor(nett(_fire_buss([(120.0, -120.0), (120.0, -120.0)])))
    assert g_ok.solution.pv_to_pq_generators == []
    assert g_ok.solution.volt[1] == pytest.approx(1.02, abs=1e-9)
    #----2 x 100 = 200 MVAr < behovet -> klemming ved summen 200, ikke ved 100----
    g_klemt = _kjor(nett(_fire_buss([(100.0, -100.0), (100.0, -100.0)])))
    assert len(g_klemt.solution.pv_to_pq_generators) == 1
    assert _q_gen(g_klemt, 1) == pytest.approx(200.0, abs=1e-6)


#==========3) Tilbake til PV hvis bussen ble klemt for tidlig==========
def _spor_klassifisering(g):
    #----white-box: følger med på hva busclassifier og "slipp tilbake"-funksjonen returnerer under kjøringen----
    hendelser = {"pqq_sett": False, "sluppet": 0}

    def profil(frame, event, arg):
        if event == "return":
            if frame.f_code.co_name == "busclassifier" and arg and "PQQ" in arg:
                hendelser["pqq_sett"] = True
            if frame.f_code.co_name == "Q_klemt_buss_skal_tilbake_til_PV" and arg is not None:
                hendelser["sluppet"] += 1
    sys.setprofile(profil)
    try:
        g.loadflowsolutionNR()
    finally:
        sys.setprofile(None)
    return hendelser


def test_buss_som_klemmes_for_tidlig_slippes_tilbake_til_pv(nett):
    #----Qmax=180: ved flat start vil PV-bussen levere ca. 236 MVAr (brudd -> klemmes), men i den ferdige
    #    løsningen trengs bare ca. 129 MVAr. Bussen MÅ derfor slippes tilbake til PV, ellers blir svaret feil.----
    g = MakeGrid(nett(_tidlig_klemt(180.0)))
    h = _spor_klassifisering(g)
    assert h["pqq_sett"], "bussen ble aldri klemt (PQQ) -> testnettet utløser ikke tidlig klemming"
    assert h["sluppet"] >= 1, "bussen ble klemt, men aldri sluppet tilbake til PV"
    s = g.solution
    assert s.konvergerte
    assert s.pv_to_pq_generators == []                             # ferdig løsning: ingen klemte generatorer
    assert s.volt[2] == pytest.approx(1.05, abs=1e-9)             # tilbake på settpunktet
    assert 0 < _q_gen(g, 2) < 180.0                               # Q innenfor grensen
    #----og svaret er det samme som når det ikke finnes noen Q-grenser i det hele tatt----
    ref = _kjor(nett(_tidlig_klemt(1e5)))
    assert np.allclose(resultater(g)[0], resultater(ref)[0], atol=1e-6, rtol=0)      # NR konvergerer til 1e-6 pu mismatch
    assert np.allclose(resultater(g)[1], resultater(ref)[1], atol=1e-5, rtol=0)


def test_buss_som_trenger_grensen_blir_klemt_selv_etter_tidlig_klemming(nett):
    #----Qmax=100 < endelig behov (ca. 129): bussen skal være og forbli klemt (ikke sluppet i det uendelige)----
    g = _kjor(nett(_tidlig_klemt(100.0)))
    assert g.solution.konvergerte
    assert len(g.solution.pv_to_pq_generators) == 1
    assert _q_gen(g, 2) == pytest.approx(100.0, abs=1e-6)
    assert g.solution.volt[2] < 1.05 - 1e-6


#==========4) Ingen klemming når grensene ikke brytes eller mangler==========
def test_ingen_klemming_naar_grensene_er_vide(nett):
    g = _kjor(nett(_fire_buss([(LAV, HOY)])))
    assert g.solution.pv_to_pq_generators == []
    assert g.solution.volt[1] == pytest.approx(1.02, abs=1e-12)


def test_ingen_klemming_naar_q_grenser_mangler_i_excel(nett):
    g = _kjor(nett(_fire_buss([(LAV, HOY)]), uten_qgrenser=True))       # kolonnene Qmax/Qmin finnes ikke
    assert g.solution.konvergerte
    assert g.solution.pv_to_pq_generators == []
    assert all(x.Q_max is None and x.Q_min is None for x in g.gen)


#==========Invarianter for en vilkårlig løsning med klemming (Trøndelagsnettet)==========
def test_invarianter_etter_klemming_paa_trondelagsnettet(trondelag):
    g = MakeGrid(trondelag)
    g.loadflowsolutionNR()
    s = g.solution
    assert s.konvergerte
    S = g.Base.Sbase
    idx = {b.busNumber: i for i, b in enumerate(g.bus)}
    qmax, qmin = {}, {}
    for x in g.gen:
        i = idx[int(x.bus)]
        qmax[i] = qmax.get(i, 0.0) + x.Q_max
        qmin[i] = qmin.get(i, 0.0) + x.Q_min
    klemte = [navn for navn in s.pv_to_pq_generators]
    antall_klemt = 0
    for i, b in enumerate(g.bus):
        if i == 0 or i not in qmax:
            continue
        q = s.qower[i] + b.Q_load                                     # generatorenes Q [pu]
        tol = 1e-6
        paa_maks = abs(q - qmax[i]) < tol
        paa_min = abs(q - qmin[i]) < tol
        #----aldri utenfor grensene----
        assert qmin[i] - tol <= q <= qmax[i] + tol, f"buss {b.busNumber}: Q={q*S:.2f} utenfor [{qmin[i]*S:.2f},{qmax[i]*S:.2f}]"
        if paa_maks or paa_min:
            antall_klemt += 1
            #----klemt ved Qmax: spenningen ligger under/ved settpunktet; klemt ved Qmin: over/ved----
            if paa_maks:
                assert s.volt[i] <= 1.0 + 1e-6, f"buss {b.busNumber} klemt ved Qmax men V={s.volt[i]}"
            else:
                assert s.volt[i] >= 1.0 - 1e-6, f"buss {b.busNumber} klemt ved Qmin men V={s.volt[i]}"
        else:
            #----ikke klemt: PV-bussen holder settpunktet----
            assert s.volt[i] == pytest.approx(1.0, abs=1e-9), f"buss {b.busNumber} er PV men V={s.volt[i]}"
    assert antall_klemt == len(klemte)
