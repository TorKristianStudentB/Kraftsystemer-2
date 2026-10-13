# -*- coding: utf-8 -*-
#----------------------------test_grensetest_trappevis.py--------------------------------------------------
# GRENSETEST: skyver nettets begrensninger trappevis, og skriver ut hvert trappetrinn helt til det går galt.
#   1) lastøkning        : all last og generering ganges opp trinn for trinn (NR, FDLF og DC)
#   2) Q-kapasitet       : generatorenes Qmax/Qmin krympes trinn for trinn (NR)
#   3) svakere nett      : linjenes R og X økes trinn for trinn (NR)
# "Går galt" betyr:
#   AC (NR/FDLF): lastflyten konvergerer ikke, kaster en feil, gir NaN, eller spenningen kollapser (< 0,5 pu)
#   DC          : vinkelforskjellen over en linje passerer 90 grader (da gir ikke DC-modellen mening lenger)
# Tabellen skrives ut selv uten  -s . Testene feiler IKKE fordi nettet til slutt går galt (det er poenget), men
# krever at første trinn er ok, at svikten kommer pent (ingen henging), og at den ikke "ordner seg" etterpå.
#----------------------------test_grensetest_trappevis.py--------------------------------------------------
import time

import numpy as np
import pytest

from GridMaker.Imports import MakeGrid                    # noqa: E402
from nett_hjelp import tilfeldig_spec                      # noqa: E402

VCOLLAPSE = 0.5          # pu: under dette regnes spenningen som kollapset
MAKS_VINKEL = np.pi / 2  # rad: DC-grense


#----------Skalering av et Grid-objekt----------
def _skaler(g, f_last=1.0, f_q=1.0, f_x=1.0):
    for b in g.bus:
        b.P_load *= f_last
        b.Q_load *= f_last
        b.P_gen *= f_last
    for x in g.gen:
        if x.Q_max is not None:
            x.Q_max *= f_q
        if x.Q_min is not None:
            x.Q_min *= f_q
    for l in g.line:
        l.R *= f_x
        l.X *= f_x


#----------Vakt: NR i Master har tak på 50 000 iterasjoner (koden), så et trinn som divergerer sakte ville kjørt "evig".
#    Vi teller kallene til jacobian() og avbryter etter MAKS_NEWTON_STEG, og regner det som "konvergerte ikke".----
import sys

MAKS_NEWTON_STEG = 120


class NewtonTak(Exception):
    pass


def _kjor_med_vakt(funksjon, metode):
    if metode != "NR":
        return funksjon()
    teller = {"n": 0}

    def profil(frame, event, arg):
        if event == "call" and frame.f_code.co_name == "jacobian":
            teller["n"] += 1
            if teller["n"] > MAKS_NEWTON_STEG:
                raise NewtonTak()
    sys.setprofile(profil)
    try:
        return funksjon()
    finally:
        sys.setprofile(None)


#----------Ett trinn: kjør metoden og vurder om det gikk galt----------
def _trinn(sti, metode, **skala):
    g = MakeGrid(sti)
    _skaler(g, **skala)
    last_mw = sum(b.P_load for b in g.bus) * g.Base.Sbase
    rad = {"last_mw": last_mw, "ok": True, "arsak": "", "iter": 0, "vmin": np.nan, "klemt": 0, "maks_flyt": np.nan}
    t0 = time.time()
    try:
        _kjor_med_vakt({"NR": g.loadflowsolutionNR, "FD": g.FDLF, "DC": g.DCPF}[metode], metode)
    except NewtonTak:
        rad.update(ok=False, arsak=f"konvergerte ikke (avbrutt etter {MAKS_NEWTON_STEG} Newton-steg; taket i koden er 50000)")
        rad["tid"] = time.time() - t0
        return rad
    except Exception as e:                                         # singulær Jacobi osv.
        rad.update(ok=False, arsak=f"krasj: {type(e).__name__}")
        rad["tid"] = time.time() - t0
        return rad
    s = g.solution
    rad["tid"] = time.time() - t0
    rad["iter"] = s.iterasjoner
    v = np.abs(np.array(s.volt, dtype=complex)).real
    rad["vmin"] = float(np.min(v))
    rad["klemt"] = len(s.pv_to_pq_generators) if s.pv_to_pq_generators else 0
    fl = np.array(s.flow_in_line)
    rad["maks_flyt"] = float(np.max(np.abs(fl))) * (1.0 if metode == "DC" else g.Base.Sbase) if fl.size else 0.0
    ang = np.array(s.angle, dtype=float)
    idx = {b.busNumber: i for i, b in enumerate(g.bus)}
    maks_dvinkel = max((abs(ang[idx[l.Frombus]] - ang[idx[l.Tobus]]) for l in g.line), default=0.0)
    rad["dvinkel_grader"] = float(np.degrees(maks_dvinkel))
    if not (np.all(np.isfinite(v)) and np.all(np.isfinite(ang))):
        rad.update(ok=False, arsak="NaN/uendelig i løsningen")
    elif metode == "DC":
        if maks_dvinkel > MAKS_VINKEL:
            rad.update(ok=False, arsak=f"vinkelforskjell {np.degrees(maks_dvinkel):.0f} grader > 90")
    elif not s.konvergerte:
        rad.update(ok=False, arsak="konvergerte ikke")
    elif rad["vmin"] < VCOLLAPSE:
        rad.update(ok=False, arsak=f"spenningskollaps ({rad['vmin']:.2f} pu)")
    return rad


#----------Kjør en hel trapp og skriv den ut----------
def _trapp(capsys, tittel, sti, metode, faktorer, nokkel, enhet_tekst, ekstra_etter=2):
    rader, svikt = [], None
    with capsys.disabled():
        print(f"\n{'=' * 98}\n GRENSETEST: {tittel}   [{metode}]\n{'=' * 98}")
        print(f" {'trinn':>5} {nokkel:>9} {'last MW':>10} {'ok':>4} {'iter':>5} {'Vmin pu':>8} {'klemte':>7} "
              f"{'maks flyt':>10} {'maks dvinkel':>13}  {'tid s':>6}  merknad")
        for k, f in enumerate(faktorer):
            r = _trinn(sti, metode, **{nokkel: f})
            rader.append((f, r))
            print(f" {k:>5} {f:>9.3f} {r['last_mw']:>10.1f} {('ja' if r['ok'] else 'NEI'):>4} {r['iter']:>5} "
                  f"{r['vmin']:>8.4f} {r['klemt']:>7} {r['maks_flyt']:>10.1f} {r.get('dvinkel_grader', float('nan')):>12.1f}°  "
                  f"{r.get('tid', 0):>6.2f}  {r['arsak'] if not r['ok'] else ''}")
            if not r['ok']:
                svikt = k
                print(f" >>> GIKK GALT på trinn {k} ({nokkel} = {f:.3f}): {r['arsak']}")
                break
        else:
            print(f" >>> Det gikk IKKE galt innenfor trinnene som ble prøvd (siste {nokkel} = {faktorer[-1]:.3f}).")
        #----etter-sjekk: skal fortsatt feile på de neste (større) trinnene, ikke "ordne seg" tilfeldig----
        etter = []
        if svikt is not None:
            for f in faktorer[svikt + 1: svikt + 1 + ekstra_etter]:
                r = _trinn(sti, metode, **{nokkel: f})
                etter.append(r)
                print(f"       etter-sjekk {nokkel}={f:.3f}: {'OK' if r['ok'] else 'feiler fortsatt (' + r['arsak'] + ')'}")
    return rader, svikt, etter


def _geometrisk(start, steg, antall):
    return [start * steg ** k for k in range(antall)]


#==========1) Lastøkning==========
@pytest.mark.parametrize("metode", ["NR", "FD", "DC"])
def test_trappevis_lastokning_paa_tilfeldig_nett(nett, capsys, metode):
    sti = nett(tilfeldig_spec(12, seed=2, antall_pv=2))
    rader, svikt, etter = _trapp(capsys, "lastøkning, tilfeldig 12-buss nett", sti, metode,
                                 _geometrisk(1.0, 1.35, 22), "f_last", "x")
    assert rader[0][1]["ok"], "første trinn (opprinnelig last) skal gå bra"
    assert svikt is not None, "nettet tålte alle trinn: øk antall trinn eller steget"
    assert svikt >= 1, "nettet gikk galt allerede ved opprinnelig last"
    assert all(not r["ok"] for r in etter), "løsningen 'ordnet seg' igjen etter svikt (ikke monoton)"


def test_trappevis_lastokning_paa_trondelagsnettet_nr(trondelag, capsys):
    rader, svikt, etter = _trapp(capsys, "lastøkning, Trøndelagsnettet", trondelag, "NR",
                                 _geometrisk(1.0, 1.3, 16), "f_last", "x")
    assert rader[0][1]["ok"], "første trinn (opprinnelig last) skal gå bra"
    assert svikt is None or svikt >= 1
    #----alle trinn FØR svikt skal ha konvergert med realistisk spenning (> 0,5 pu)----
    assert all(r["ok"] and r["vmin"] > VCOLLAPSE for _, r in rader[: svikt if svikt is not None else len(rader)])


@pytest.mark.parametrize("metode", ["FD", "DC"])
def test_trappevis_lastokning_paa_trondelagsnettet_fd_og_dc(trondelag, capsys, metode):
    rader, svikt, _ = _trapp(capsys, "lastøkning, Trøndelagsnettet", trondelag, metode,
                             _geometrisk(1.0, 1.4, 14), "f_last", "x")
    assert rader[0][1]["ok"]


#==========2) Q-kapasitet krymper==========
def test_trappevis_q_kapasitet_krymper_paa_trondelagsnettet(trondelag, capsys):
    faktorer = [1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.05, 0.0]
    rader, svikt, _ = _trapp(capsys, "generatorenes Qmax/Qmin krympes (faktor på Q-kapasitet)", trondelag, "NR",
                             faktorer, "f_q", "x", ekstra_etter=1)
    assert rader[0][1]["ok"]
    #----jo mindre Q-kapasitet, jo flere busser må klemmes (ikke færre)----
    klemt = [r["klemt"] for _, r in rader if r["ok"]]
    assert klemt == sorted(klemt) or max(klemt) - klemt[-1] <= 2, f"antall klemte busser burde øke: {klemt}"


def test_trappevis_q_kapasitet_krymper_paa_tilfeldig_nett(nett, capsys):
    #----generatorer med begrenset Q: gi nettet en realistisk Q-grense først (30 % av Pmax), så krymp----
    spec = tilfeldig_spec(12, seed=2, antall_pv=3)
    spec["pv"] = {b: (p, v, [(0.5 * p * 3, -0.3 * p * 3)]) for b, (p, v, _) in spec["pv"].items()}
    faktorer = [1.0, 0.7, 0.5, 0.35, 0.25, 0.15, 0.1, 0.05, 0.0]
    rader, svikt, _ = _trapp(capsys, "Q-kapasitet krymper, tilfeldig 12-buss nett", nett(spec), "NR", faktorer,
                             "f_q", "x", ekstra_etter=1)
    assert rader[0][1]["ok"]


#==========3) Svakere nett (høyere impedans)==========
def test_trappevis_svakere_nett_paa_tilfeldig_nett(nett, capsys):
    sti = nett(tilfeldig_spec(12, seed=2, antall_pv=2))
    rader, svikt, etter = _trapp(capsys, "linjeimpedans ganges opp (svakere nett)", sti, "NR",
                                 _geometrisk(1.0, 1.5, 20), "f_x", "x")
    assert rader[0][1]["ok"]
    assert svikt is not None and svikt >= 1
    assert all(not r["ok"] for r in etter)


def test_trappevis_svakere_nett_paa_trondelagsnettet(trondelag, capsys):
    rader, svikt, _ = _trapp(capsys, "linjeimpedans ganges opp, Trøndelagsnettet", trondelag, "NR",
                             _geometrisk(1.0, 1.6, 14), "f_x", "x", ekstra_etter=1)
    assert rader[0][1]["ok"]
