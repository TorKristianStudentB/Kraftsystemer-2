# -*- coding: utf-8 -*-
#----------------------------test_hard_funksjonstest.py--------------------------------------------------
# Tester alle funksjonene HARDT, uavhengig av pandapower der det går:
#   MakeGrid       : enheter (pu), valgfrie kolonner, bus-id som ikke er 0..n-1, isolert buss
#   cutsem         : Y-matrisen mot en uavhengig bygget Y (linjer, shunt, trafoer med/uten off-nominell tapp)
#   Newton-Raphson : fysikk (KCL i hver buss), effektbalanse, bussnumre, isolert buss, ingen PV, store nett,
#                    ikke-konvergens uten krasj, enkle ytterpunkter
#   DC             : KCL for aktiv effekt, antisymmetriske flyter, lineæritet
#   FDLF           : samme løsning som NR når det ikke er Q-grenser
#   Thevenin       : mot Z-matrisen (Zth = Zii + Zjj - 2 Zij) for mange tilfeldige nett og alle node-par
#   Solution       : felter, former, typer
#----------------------------test_hard_funksjonstest.py--------------------------------------------------
import itertools
import time

import numpy as np
import pytest

from GridMaker.Imports import MakeGrid, cutsem, theveninZth         # noqa: E402
from nett_hjelp import tilfeldig_spec, resultater, SBASE            # noqa: E402

ZBASE_300 = 300.0 ** 2 / SBASE


def _l(a, b, r=3.0, x=30.0, bb=0.0):
    return (a, b, r, x, bb)


def _kjor(nett, spec, metode="NR", **kw):
    g = MakeGrid(nett(spec, **kw))
    {"NR": g.loadflowsolutionNR, "DC": g.DCPF, "FD": g.FDLF}[metode]()
    return g


#==========MakeGrid==========
def test_makegrid_konverterer_til_pu(nett):
    spec = {"vbase": [300.0, 300.0], "linjer": [_l(0, 1, 9.0, 90.0)], "last": {1: (50.0, 20.0)},
            "pv": {}, "V0": 1.0}
    g = MakeGrid(nett(spec))
    assert g.Base.Sbase == 100.0
    assert g.bus[1].P_load == pytest.approx(0.5)                        # 50 MW / 100 MVA
    assert g.bus[1].Q_load == pytest.approx(0.2)
    assert g.line[0].R == pytest.approx(9.0 / ZBASE_300)                # ohm / Zbase
    assert g.line[0].X == pytest.approx(90.0 / ZBASE_300)
    assert g.line[0].admittans() == pytest.approx(1 / complex(9.0 / ZBASE_300, 90.0 / ZBASE_300))


def test_makegrid_valgfrie_kolonner_gir_none(nett):
    g = MakeGrid(nett({"vbase": [300.0] * 2, "linjer": [_l(0, 1)], "last": {1: (10, 2)}, "pv": {}}, uten_qgrenser=True))
    assert all(x.Q_max is None and x.Q_min is None for x in g.gen)
    assert g.bus[0].V_max is None and g.bus[0].eic_code is None and g.bus[0].cords is None
    assert g.line[0].eic_code is None


def test_makegrid_busnummer_er_ikke_indeks(nett):
    spec = {"vbase": [300.0] * 3, "linjer": [_l(0, 1), _l(1, 2)], "last": {1: (30, 10), 2: (20, 8)}, "pv": {}}
    g = MakeGrid(nett(spec, busnummer=[30, 45, 7]))
    assert [b.busNumber for b in g.bus] == [30, 45, 7]
    assert [b.kodens_identifikasjonssystem for b in g.bus] == [0, 1, 2]
    assert (g.line[0].Frombus, g.line[0].Tobus) == (30, 45)


#==========cutsem (Y-matrisen)==========
def _y_uavhengig(g):
    #----bygger Y fra fysikken (pi-modell, trafo med tapp i pu), uten å bruke cutsem----
    n = len(g.bus)
    Y = np.zeros((n, n), dtype=complex)
    idx = {b.busNumber: i for i, b in enumerate(g.bus)}
    for l in g.line:
        i, j = idx[l.Frombus], idx[l.Tobus]
        y = 1 / complex(l.R, l.X)
        Y[i, i] += y + 0.5j * l.B
        Y[j, j] += y + 0.5j * l.B
        Y[i, j] -= y
        Y[j, i] -= y
    for t in g.trafo:
        i, j = idx[t.Frombus], idx[t.Tobus]
        hv, lv = (i, j) if g.bus[i].Vbase >= g.bus[j].Vbase else (j, i)
        tap = t.ratio / (g.bus[lv].Vbase / g.bus[hv].Vbase)             # pu-tapp (nominell = 1)
        y = 1 / complex(t.R, t.X)
        Y[hv, hv] += y * tap ** 2                                       # tap på høyspentsiden (a = 1/tap)
        Y[lv, lv] += y
        Y[hv, lv] -= y * tap
        Y[lv, hv] -= y * tap
    return Y


@pytest.mark.parametrize("seed,pv,trafoer,shunt", [(1, 1, 0, False), (2, 2, 3, False), (3, 1, 2, True), (4, 0, 4, True)])
def test_y_matrisen_stemmer_med_uavhengig_bygget_y(nett, seed, pv, trafoer, shunt):
    g = MakeGrid(nett(tilfeldig_spec(10, seed, antall_pv=pv, trafoer=trafoer, med_shunt=shunt)))
    Y = cutsem(g)
    assert Y.shape == (len(g.bus), len(g.bus))
    assert np.allclose(Y, _y_uavhengig(g), atol=1e-9, rtol=1e-9)
    assert np.allclose(Y, Y.T, atol=1e-12)                              # symmetrisk (ingen faseskift)


def test_y_for_rene_linjer_uten_shunt_har_radsum_null(nett):
    g = MakeGrid(nett(tilfeldig_spec(12, 7, antall_pv=1, med_shunt=False)))
    assert np.allclose(cutsem(g).sum(axis=1), 0, atol=1e-9)


def test_nominell_trafo_har_tapp_1_og_off_nominell_endrer_y(nett):
    spec = {"vbase": [380.0, 132.0], "linjer": [], "trafoer": [(0, 1, 0.002, 0.05)], "last": {1: (10, 2)}, "pv": {}}
    g = MakeGrid(nett(spec))
    Y = cutsem(g)
    y = 1 / complex(0.002, 0.05)
    assert Y[0, 0] == pytest.approx(y) and Y[1, 1] == pytest.approx(y) and Y[0, 1] == pytest.approx(-y)
    g.trafo[0].ratio *= 1.05                                           # 5 % tapp
    Y2 = cutsem(g)
    assert Y2[0, 1] == pytest.approx(-y * 1.05)
    assert Y2[0, 0] == pytest.approx(y * 1.05 ** 2)
    assert Y2[1, 1] == pytest.approx(y)


#==========Newton-Raphson, fysikk==========
def _kcl_feil(g):
    #----for hver buss unntatt slack: sum av kompleks effekt ut på linjene = netto injeksjon (P+jQ) fra løsningen. Kun nett uten trafo og shunt.----
    s = g.solution
    V = np.array(s.volt) * np.exp(1j * np.array(s.angle))
    idx = {b.busNumber: i for i, b in enumerate(g.bus)}
    ut = np.zeros(len(g.bus), dtype=complex)
    for l in g.line:
        i, j = idx[l.Frombus], idx[l.Tobus]
        y = l.admittans()
        ut[i] += V[i] * np.conj((V[i] - V[j]) * y)
        ut[j] += V[j] * np.conj((V[j] - V[i]) * y)
    inj = np.array(s.power) + 1j * np.array(s.qower)
    return np.max(np.abs(ut[1:] - inj[1:]))          # slack (bus 0) testes for seg, se test_nr_slack_effekt_...


@pytest.mark.parametrize("seed,pv", [(11, 0), (12, 1), (13, 3), (14, 2)])
def test_nr_oppfyller_kirchhoff_i_hver_buss(nett, seed, pv):
    g = _kjor(nett, tilfeldig_spec(14, seed, antall_pv=pv))
    assert g.solution.konvergerte
    assert _kcl_feil(g) < 1e-5


@pytest.mark.parametrize("seed,pv,trafoer", [(11, 0, 0), (12, 1, 0), (15, 2, 3)])
def test_nr_slack_effekt_er_det_nettet_faktisk_leverer_inkludert_tap(nett, seed, pv, trafoer):
    #----slackens injeksjon er S0 = V0 * conj((Y V)[0]) = last + tap. NR må gi dette i power[0] / qower[0].
    #    (Å sette slack = -sum(de andre injeksjonene) ignorerer tapene i nettet.)----
    g = _kjor(nett, tilfeldig_spec(10, seed, antall_pv=pv, trafoer=trafoer))
    s = g.solution
    V = np.array(s.volt) * np.exp(1j * np.array(s.angle))
    S0 = V[0] * np.conj((cutsem(g) @ V)[0])
    assert s.power[0] == pytest.approx(S0.real, abs=1e-6), f"slack P: NR={s.power[0]:.6f} fysikk={S0.real:.6f} pu"
    assert s.qower[0] == pytest.approx(S0.imag, abs=1e-6), f"slack Q: NR={s.qower[0]:.6f} fysikk={S0.imag:.6f} pu"
    assert S0.real > -np.sum(np.array(s.power[1:]))                      # tap > 0: slack leverer mer enn lasten alene


def test_nr_slack_tar_lasten_naar_ingen_generatorer_og_lite_tap(nett):
    #----rent radialt nett med en last: slack leverer lasten pluss tap (alltid litt mer)----
    g = _kjor(nett, {"vbase": [300.0] * 3, "linjer": [_l(0, 1), _l(1, 2)], "last": {2: (50, 10)}, "pv": {}})
    assert g.solution.konvergerte
    p_slack = g.solution.power[0] * SBASE
    assert 50 < p_slack < 51
    assert g.solution.power[2] * SBASE == pytest.approx(-50, abs=1e-4)


def test_nr_uten_last_gir_flat_spenning(nett):
    g = _kjor(nett, {"vbase": [300.0] * 4, "linjer": [_l(0, 1), _l(1, 2), _l(2, 3)], "last": {}, "pv": {}, "V0": 1.03})
    v, a = resultater(g)
    assert np.allclose(v, 1.03, atol=1e-9) and np.allclose(a, 0, atol=1e-9)
    assert np.allclose(g.solution.power, 0, atol=1e-9) and np.allclose(g.solution.qower, 0, atol=1e-9)


def test_nr_enkeltlinje_to_busser(nett):
    g = _kjor(nett, {"vbase": [300.0] * 2, "linjer": [_l(0, 1, 3.0, 30.0)], "last": {1: (30, 10)}, "pv": {}})
    assert g.solution.konvergerte
    S = 0.3 + 0.1j
    V1 = g.solution.volt[1] * np.exp(1j * g.solution.angle[1])
    I = np.conj(S / V1)
    assert (1.0 - V1) == pytest.approx(I * complex(3.0, 30.0) / ZBASE_300, abs=1e-6)     # V0 - V1 = I*Z


def test_nr_bruker_busnummer_riktig_naar_de_ikke_er_indeks(nett):
    spec = tilfeldig_spec(8, 21, antall_pv=2)
    normal = _kjor(nett, spec)
    forskjovet = _kjor(nett, spec, busnummer=[100, 7, 55, 3, 99, 12, 41, 8])
    assert np.allclose(resultater(normal)[0], resultater(forskjovet)[0], atol=1e-12)
    assert np.allclose(resultater(normal)[1], resultater(forskjovet)[1], atol=1e-10)


def test_nr_isolert_buss_hoppes_over_uten_krasj(nett):
    spec = {"vbase": [300.0] * 4, "linjer": [_l(0, 1), _l(1, 2)], "last": {1: (30, 10), 2: (20, 8)}, "pv": {}}   # buss 3 er alene
    g = _kjor(nett, spec)
    assert g.solution.konvergerte
    assert g.solution.volt[3] == pytest.approx(1.0) and g.solution.angle[3] == pytest.approx(0.0)


def test_nr_stort_nett_konvergerer_raskt_nok(nett):
    t0 = time.time()
    g = _kjor(nett, tilfeldig_spec(30, 31, antall_pv=5, trafoer=3))
    assert g.solution.konvergerte
    assert g.solution.iterasjoner <= 8
    assert time.time() - t0 < 60


def test_nr_gir_konvergerte_false_uten_krasj_naar_lasten_er_umulig(nett):
    spec = {"vbase": [300.0] * 3, "linjer": [_l(0, 1, 3.0, 30.0), _l(1, 2, 3.0, 30.0)],
            "last": {2: (100000.0, 30000.0)}, "pv": {}}                  # 100 GW over to 300 kV-linjer
    g = _kjor(nett, spec)
    assert g.solution.konvergerte is False
    assert g.solution.iterasjoner > 0


#==========DC==========
@pytest.mark.parametrize("seed,trafoer", [(41, 0), (42, 3), (43, 2)])
def test_dc_kirchhoff_for_aktiv_effekt(nett, seed, trafoer):
    g = _kjor(nett, tilfeldig_spec(12, seed, antall_pv=2, trafoer=trafoer), "DC")
    s = g.solution
    idx = {b.busNumber: i for i, b in enumerate(g.bus)}
    ut = np.zeros(len(g.bus))
    ang = np.array(s.angle)
    for l, p in zip(g.line, s.flow_in_line):
        ut[idx[l.Frombus]] += p / SBASE
        ut[idx[l.Tobus]] -= p / SBASE
    for t in g.trafo:
        i, j = idx[t.Frombus], idx[t.Tobus]
        tap = t.ratio / (min(g.bus[i].Vbase, g.bus[j].Vbase) / max(g.bus[i].Vbase, g.bus[j].Vbase))
        p = (ang[i] - ang[j]) * tap / t.X
        ut[i] += p
        ut[j] -= p
    assert np.allclose(ut, s.power, atol=1e-9)                       # sum av flyt ut av bussen = netto P-injeksjon
    assert abs(np.sum(s.power)) < 1e-9                               # tapsfri: injeksjonene summerer til null
    assert s.konvergerte


def test_dc_er_lineaer_i_lasten(nett):
    spec1 = tilfeldig_spec(10, 51, antall_pv=1)
    spec2 = {**spec1, "last": {b: (2 * p, 2 * q) for b, (p, q) in spec1["last"].items()},
             "pv": {b: (2 * p, v, gr) for b, (p, v, gr) in spec1["pv"].items()}}
    a1 = np.array(_kjor(nett, spec1, "DC").solution.angle)
    a2 = np.array(_kjor(nett, spec2, "DC").solution.angle)
    assert np.allclose(a2, 2 * a1, atol=1e-12)


def test_dc_uten_last_gir_null_vinkler_og_null_flyt(nett):
    g = _kjor(nett, {"vbase": [300.0] * 3, "linjer": [_l(0, 1), _l(1, 2)], "last": {}, "pv": {}}, "DC")
    assert np.allclose(g.solution.angle, 0) and np.allclose(g.solution.flow_in_line, 0)


def test_dc_isolert_buss_og_slackvinkel(nett):
    spec = {"vbase": [300.0] * 4, "linjer": [_l(0, 1), _l(1, 2)], "last": {2: (30, 5)}, "pv": {}}
    g = _kjor(nett, spec, "DC")
    assert g.solution.angle[0] == pytest.approx(0) and g.solution.angle[3] == pytest.approx(0)
    assert g.solution.angle[2] < g.solution.angle[1] < 0               # lasten trekker vinkelen ned langs linja


#==========FDLF==========
@pytest.mark.parametrize("seed,pv,trafoer", [(61, 1, 0), (62, 3, 2), (63, 0, 3)])
def test_fdlf_gir_samme_loesning_som_nr(nett, seed, pv, trafoer):
    spec = tilfeldig_spec(12, seed, antall_pv=pv, trafoer=trafoer)
    nr, fd = _kjor(nett, spec, "NR"), _kjor(nett, spec, "FD")
    assert fd.solution.konvergerte
    assert np.allclose(resultater(fd)[0], resultater(nr)[0], atol=1e-6)
    assert np.allclose(resultater(fd)[1], resultater(nr)[1], atol=1e-4)
    assert fd.solution.type == "FD" and nr.solution.type == "NR"


def test_fdlf_isolert_buss(nett):
    spec = {"vbase": [300.0] * 4, "linjer": [_l(0, 1), _l(1, 2)], "last": {1: (30, 10), 2: (20, 8)}, "pv": {}}
    assert _kjor(nett, spec, "FD").solution.konvergerte


#==========Thevenin==========
def _zth_zmatrise(g, i_bus, j_bus):
    n = len(g.bus)
    idx = {b.busNumber: k for k, b in enumerate(g.bus)}
    Y = np.zeros((n, n), dtype=complex)
    for l in g.line:
        a, b = idx[l.Frombus], idx[l.Tobus]
        y = l.admittans()
        Y[a, a] += y; Y[b, b] += y; Y[a, b] -= y; Y[b, a] -= y
    i, j = idx[i_bus], idx[j_bus]
    behold = [k for k in range(n) if k != j]                          # j som referanse
    Z = np.linalg.inv(Y[np.ix_(behold, behold)])
    return Z[behold.index(i), behold.index(i)]


@pytest.mark.parametrize("seed,n,ekstra", [(71, 7, 3), (72, 9, 9), (73, 11, 14), (74, 8, 0)])
def test_thevenin_stemmer_med_z_matrisen_for_alle_par(nett, seed, n, ekstra):
    g = MakeGrid(nett(tilfeldig_spec(n, seed, antall_pv=0, ekstra_linjer=ekstra)))
    for a, b in itertools.combinations([x.busNumber for x in g.bus], 2):
        z = theveninZth(g, a, b)
        assert z == pytest.approx(_zth_zmatrise(g, a, b), rel=1e-8, abs=1e-12), (a, b)


def test_thevenin_formler_serie_parallell_trekant(nett):
    z1, z2, z3 = complex(1, 12), complex(2, 18), complex(3, 25)
    zb = ZBASE_300
    serie = MakeGrid(nett({"vbase": [300.0] * 3, "linjer": [_l(0, 1, z1.real, z1.imag), _l(1, 2, z2.real, z2.imag)],
                           "last": {}, "pv": {}}))
    assert theveninZth(serie, 0, 2) == pytest.approx((z1 + z2) / zb)
    par = MakeGrid(nett({"vbase": [300.0] * 2, "linjer": [_l(0, 1, z1.real, z1.imag), _l(0, 1, z2.real, z2.imag)],
                         "last": {}, "pv": {}}))
    assert theveninZth(par, 0, 1) == pytest.approx(z1 * z2 / (z1 + z2) / zb)
    tri = MakeGrid(nett({"vbase": [300.0] * 3, "linjer": [_l(0, 1, z1.real, z1.imag), _l(1, 2, z2.real, z2.imag),
                                                             _l(2, 0, z3.real, z3.imag)], "last": {}, "pv": {}}))
    assert theveninZth(tri, 0, 1) == pytest.approx(z1 * (z2 + z3) / (z1 + z2 + z3) / zb)


def test_thevenin_gir_feil_for_noder_uten_forbindelse(nett):
    g = MakeGrid(nett({"vbase": [300.0] * 4, "linjer": [_l(0, 1), _l(2, 3)], "last": {}, "pv": {}}))
    with pytest.raises(Exception):
        theveninZth(g, 0, 3)


#==========Solution-objektet==========
@pytest.mark.parametrize("metode,typenavn", [("NR", "NR"), ("DC", "DC"), ("FD", "FD")])
def test_solution_har_riktige_felt_former_og_typer(nett, metode, typenavn):
    spec = tilfeldig_spec(9, 81, antall_pv=2, trafoer=1)
    g = _kjor(nett, spec, metode)
    s = g.solution
    n = len(g.bus)
    assert s.type == typenavn
    assert np.shape(s.volt) == (n,) and np.shape(s.angle) == (n,)
    assert np.shape(s.power) == (n,) and np.shape(s.qower) == (n,)
    assert np.shape(s.flow_in_line) == (len(g.line),)
    assert isinstance(bool(s.konvergerte), bool) and s.iterasjoner >= 1
    assert np.all(np.isfinite(np.array(s.volt, dtype=float))) and np.all(np.isfinite(np.array(s.angle, dtype=float)))
    assert np.iscomplexobj(s.flow_in_line) == (metode != "DC")          # DC: reell MW, AC: kompleks pu


def test_grid_er_ikke_loest_foer_lastflyt(nett):
    assert MakeGrid(nett(tilfeldig_spec(6, 91))).solution is None


def test_metodene_oppdaterer_selve_grid_objektet(nett):
    g = MakeGrid(nett(tilfeldig_spec(8, 92, antall_pv=1)))
    v0 = [b.Volt for b in g.bus]
    r = g.loadflowsolutionNR()
    assert r is g                                                     # returnerer samme objekt
    assert [b.Volt for b in g.bus] != v0                              # og har oppdatert bussene
