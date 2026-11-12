import copy
import time

import numpy as np
import pandas as pd
import pyomo.environ as pyo


# ---------- Preventiv DC-SCOPF ----------
# Normalnettet og enkeltutfall av alle fysiske linjer inngår i modellen.

def dc_scopf(grid, solver="appsi_highs", kopi=False):
    """Preventiv DC-SCOPF med pu internt og resultater i grid.solution.

    kopi=True bevarer originalnettet. Normalnettets resultater har samme
    enheter som gruppens dcopf(). Utfallsresultater ligger i kontingenser.
    Bruk gruppens dcopf() separat for vanlig OPF og kostnadssammenligning.
    """
    if kopi:
        grid = copy.deepcopy(grid)
    start_time = time.perf_counter()

    # ---------- Hent nettdata ----------
    # MakeGrid har allerede konvertert effekt og reaktans til pu.
    # Modellen bruker pu; resultater konverteres til MW, kostnad til EUR/h.

    sbase = float(grid.Base.Sbase)

    busser = [b.busNumber for b in grid.bus]
    referansebuss = busser[0]

    last = {
        b.busNumber: float(b.P_load)
        for b in grid.bus
    }

    generatorer = list(range(len(grid.gen)))

    gen_buss = {
        g: grid.gen[g].bus
        for g in generatorer
    }

    pmax = {
        g: float(grid.gen[g].P_max)
        for g in generatorer
    }

    kostnad = {
        g: float(grid.gen[g].cost_per_MW)
        for g in generatorer
    }

    generatorer_paa_buss = {
        i: [g for g in generatorer if gen_buss[g] == i]
        for i in busser
    }

    # ---------- Samle linjer og transformatorer ----------

    grener = {}
    utfallslinjer = []

    for linje in grid.line:
        gren_id = f"L{linje.lineNumber}"

        if gren_id in grener:
            raise ValueError(f"Duplisert gren-ID: {gren_id}")

        grener[gren_id] = {
            "fra": linje.Frombus,
            "til": linje.Tobus,
            "x": float(linje.X),
            "tapp": 1.0,
            "grense": float(linje.S_max) / sbase,
        }

        # Kun fysiske linjer inngår i listen over utfall.
        if not getattr(linje, "kunstig_line", False):
            utfallslinjer.append(gren_id)

    spenningsbase = {
        b.busNumber: float(b.Vbase)
        for b in grid.bus
    }

    for trafo in grid.trafo:
        gren_id = f"T{trafo.transformer_id}"

        if gren_id in grener:
            raise ValueError(f"Duplisert gren-ID: {gren_id}")

        v_fra = spenningsbase[trafo.Frombus]
        v_til = spenningsbase[trafo.Tobus]

        # Samme tappbehandling som i deres DCPF.
        nominelt_forhold = min(v_fra, v_til) / max(v_fra, v_til)
        tapp_pu = float(trafo.ratio) / nominelt_forhold

        grener[gren_id] = {
            "fra": trafo.Frombus,
            "til": trafo.Tobus,
            "x": float(trafo.X),
            "tapp": tapp_pu,
            "grense": float(trafo.S_max) / sbase,
        }

    # ---------- Kontroller grunnleggende data ----------

    if len(set(busser)) != len(busser):
        raise ValueError("Dupliserte bussnummer i grid.")

    for g in generatorer:
        if gen_buss[g] not in busser:
            raise ValueError(f"Generator {g} har ukjent buss.")

        if not np.isfinite(pmax[g]) or pmax[g] < 0:
            raise ValueError(f"Ugyldig Pmax for generator {g}.")

        if not np.isfinite(kostnad[g]):
            raise ValueError(f"Ugyldig kostnad for generator {g}.")

    for gren_id, gren in grener.items():
        if gren["fra"] not in busser or gren["til"] not in busser:
            raise ValueError(f"{gren_id} har ukjent buss.")

        verdier = [gren["x"], gren["tapp"], gren["grense"]]

        if not all(np.isfinite(v) and v > 0 for v in verdier):
            raise ValueError(
                f"{gren_id} har ugyldig reaktans, tapp eller grense."
            )

        # Grenvekt i pu, identisk med gruppens DC-OPF.
        gren["koeffisient"] = (
            gren["tapp"] / gren["x"]
        )

    # ---------- Normalnett og linjeutfall ----------
    # N0 betyr normalnettet.
    # Ellers er tilfellenavnet lik linjen som er utkoblet.

    tilfeller = ["N0", "L1165", "L1288"]

    aktive_grener = {
        c: [l for l in grener if l != c]
        for c in tilfeller
    }

    # ---------- Oppdag øydrift ----------
    # Denne første versjonen krever et sammenhengende nett.
    # Et øydannende utfall blir rapportert, ikke hoppet over.

    def er_sammenhengende(c):
        naboer = {i: [] for i in busser}

        for l in aktive_grener[c]:
            fra = grener[l]["fra"]
            til = grener[l]["til"]

            naboer[fra].append(til)
            naboer[til].append(fra)

        besokt = {referansebuss}
        gjenstaar = [referansebuss]

        while gjenstaar:
            i = gjenstaar.pop()

            for j in naboer[i]:
                if j not in besokt:
                    besokt.add(j)
                    gjenstaar.append(j)

        return len(besokt) == len(busser)

    oytilfeller = [
        c for c in tilfeller
        if not er_sammenhengende(c)
    ]

    if oytilfeller:
        raise ValueError(
            "Disse tilfellene deler nettet i øyer: "
            f"{oytilfeller}. De må håndteres særskilt."
        )

    # ---------- Modell ----------

    m = pyo.ConcreteModel()

    m.G = pyo.Set(initialize=generatorer)
    m.B = pyo.Set(initialize=busser)
    m.C = pyo.Set(initialize=tilfeller)

    # Én produksjonsfordeling, felles for alle tilfeller.
    # Foreløpig antas Pmin = 0 pu.
    m.PG = pyo.Var(
        m.G,
        domain=pyo.NonNegativeReals,
        bounds=lambda m, g: (0, pmax[g]),
    )

    # Egne bussvinkler for hvert tilfelle.
    m.theta = pyo.Var(
        m.C,
        m.B,
        domain=pyo.Reals,
    )

    # ---------- Kostnadsfunksjon ----------

    m.obj = pyo.Objective(
        expr=sum(kostnad[g] * m.PG[g] * sbase for g in m.G),
        sense=pyo.minimize,
    )

    m.cons = pyo.ConstraintList()

    # Lagre flytuttrykkene slik at de også kan leses etterpå.
    flytuttrykk = {}

    # ---------- Betingelser for hvert tilfelle ----------

    for c in tilfeller:

        # Referansebussen bestemmer bare vinkelreferansen.
        # Den tilfører ikke ekstra, ubegrenset produksjon.
        m.cons.add(m.theta[c, referansebuss] == float(grid.bus[0].Angle))

        # Flyt og grenser for alle grener som er i drift.
        for l in aktive_grener[c]:
            gren = grener[l]

            fra = gren["fra"]
            til = gren["til"]

            flyt = gren["koeffisient"] * (
                m.theta[c, fra] - m.theta[c, til]
            )

            flytuttrykk[c, l] = flyt

            m.cons.add(flyt <= gren["grense"])
            m.cons.add(flyt >= -gren["grense"])

        # Effektbalanse på hver buss.
        for i in busser:
            produksjon = sum(
                m.PG[g] for g in generatorer_paa_buss[i]
            )

            utgaaende = sum(
                flytuttrykk[c, l]
                for l in aktive_grener[c]
                if grener[l]["fra"] == i
            )

            inngaaende = sum(
                flytuttrykk[c, l]
                for l in aktive_grener[c]
                if grener[l]["til"] == i
            )

            m.cons.add(
                produksjon - last[i] == utgaaende - inngaaende
            )

    # ---------- Løs modellen ----------

    optimizer = pyo.SolverFactory(solver)

    if not optimizer.available(exception_flag=False):
        raise RuntimeError(
            "HiGHS er ikke tilgjengelig. "
            "Installer pyomo og highspy i ditt venv."
        )

    resultat = optimizer.solve(m, load_solutions=False)

    if (
        resultat.solver.termination_condition
        != pyo.TerminationCondition.optimal
    ):
        status = str(resultat.solver.termination_condition)
        grid.solution = grid.__class__.Solution(
            volt=None, angle=None, flow_in_line=None, iterasjoner=None,
            mismatch=None, konvergerte=False, pv_to_pq_generators=None,
            power=None, qower=None,
            type="DCSCOPF",
            kjoretid=time.perf_counter() - start_time,
        )
        grid.solution.status = status
        grid.solution.kostnad = None
        grid.solution.kontingenser = {}
        print(f"DC-SCOPF fant ingen optimal løsning ({status}).")
        return grid

    m.solutions.load_from(resultat)

    # ---------- Hent resultatene ----------

    produksjon = {
        g: pyo.value(m.PG[g])
        for g in generatorer
    }

    vinkler = {
        c: {
            i: pyo.value(m.theta[c, i])
            for i in busser
        }
        for c in tilfeller
    }

    flyt = {
        c: {
            l: (
                pyo.value(flytuttrykk[c, l])
                if l in aktive_grener[c]
                else 0.0
            )
            for l in grener
        }
        for c in tilfeller
    }

    belastning = {
        c: {
            l: 100 * abs(flyt[c][l]) / grener[l]["grense"]
            for l in grener
        }
        for c in tilfeller
    }

    # ---------- Samme resultatformat som gruppens DC-OPF ----------
    # Kun normalnettets dispatch og vinkler skrives tilbake til grid.
    gren_ider = list(grener)
    p_gen = np.array([produksjon[g] for g in generatorer])
    normal_vinkler = np.array([vinkler["N0"][i] for i in busser])
    normal_flyt = np.array([flyt["N0"][l] * sbase for l in gren_ider])
    normal_belastning = np.array([belastning["N0"][l] for l in gren_ider])

    for bus in grid.bus:
        bus.P_gen = sum(produksjon[g] for g in generatorer_paa_buss[bus.busNumber])
        bus.Angle = vinkler["N0"][bus.busNumber]
    for g, gen in enumerate(grid.gen):
        gen.P_opf = p_gen[g]  # pu, som i gruppens dcopf()

    grid.solution = grid.__class__.Solution(
        volt=np.ones(len(busser)), angle=normal_vinkler,
        flow_in_line=normal_flyt[:len(grid.line)], iterasjoner=1,
        mismatch=None, konvergerte=True, pv_to_pq_generators=None,
        power=np.array([b.P_gen - b.P_load for b in grid.bus]),
        qower=np.zeros(len(busser)),
        type="DCSCOPF",
        kjoretid=time.perf_counter() - start_time,
    )
    sol = grid.solution
    sol.status = "optimal"
    sol.kostnad = pyo.value(m.obj)  # EUR/h med kostnader i EUR/MWh
    sol.P_gen_MW = p_gen * sbase
    sol.gen_kostnad = np.array([kostnad[g] for g in generatorer])
    sol.gren_navn = gren_ider
    sol.gren_kunstig = [bool(getattr(l, "kunstig_line", False))
                       for l in grid.line] + [False] * len(grid.trafo)
    sol.flyt_MW = normal_flyt
    sol.belastning = normal_belastning
    sol.lmp = None  # SCOPF-dualer krever egen tolkning; beregnes ikke her.
    sol.skyggepris = None
    sol.modell = m
    sol.kontingenser = {
        c: {
            "utkoblet_linje": c,
            "angle": np.array([vinkler[c][i] for i in busser]),
            "flyt_MW": np.array([flyt[c][l] * sbase for l in gren_ider]),
            "belastning": np.array([belastning[c][l] for l in gren_ider]),
        }
        for c in tilfeller if c != "N0"
    }
    return grid


# ---------- Resultatutskrift i samme stil som DC-OPF ----------

def vis_resultater_SCOPF(grid):
    s = grid.solution
    if s is None or s.type != "DCSCOPF" or not s.konvergerte:
        status = getattr(s, "status", "ikke løst")
        print(f"Ingen DC-SCOPF-løsning å vise ({status})")
        return

    print("\nPreventiv DC-SCOPF")
    print(f"\nTotal kostnad: {s.kostnad:,.0f} €/h")
    print(f"Total produksjon: {s.P_gen_MW.sum():.1f} MW   |   "
          f"Kjøretid: {s.kjoretid * 1000:.1f} ms")

    # Vis fysisk buss, også når generatoren står på en kunstig buss.
    fysisk_buss = {
        int(l.Frombus): int(l.Tobus)
        for l in grid.line if getattr(l, "kunstig_line", False)
    }
    gen_tabell = pd.DataFrame({
        "generator": [g.name for g in grid.gen],
        "buss": [fysisk_buss.get(int(g.bus), int(g.bus)) for g in grid.gen],
        "kostnad €/MWh": s.gen_kostnad,
        "P [MW]": np.round(s.P_gen_MW, 1),
        "P_max [MW]": [g.P_max * grid.Base.Sbase for g in grid.gen],
    })
    print("\nDispatch (generatorer som produserer):")
    print(gen_tabell[gen_tabell["P [MW]"] > 0].to_string(index=False))

    # Samme grenbetegnelser og rekkefølge som gruppens DC-OPF.
    gren_navn = [
        f"Linje {l.lineNumber} ({int(l.Frombus)}-{int(l.Tobus)})"
        for l in grid.line
    ] + [
        f"Trafo {int(t.Frombus)}-{int(t.Tobus)}"
        for t in grid.trafo
    ]
    fysisk = np.array([not k for k in s.gren_kunstig], dtype=bool)
    gren_tabell = pd.DataFrame({
        "gren": gren_navn,
        "flyt [MW]": np.round(s.flyt_MW, 1),
        "belastning %": np.round(s.belastning, 1),
    })
    print("\nGrener sortert etter belastning (normalnett):")
    print(gren_tabell.loc[fysisk].sort_values(
        "belastning %", ascending=False
    ).to_string(index=False))

    # Én rad per utfall; kunstige generatorlinjer holdes utenfor tabellen.
    rader = []
    for c, resultat in s.kontingenser.items():
        kandidater = [
            i for i, k in enumerate(s.gren_navn)
            if fysisk[i] and k != c
        ]
        if not kandidater:
            continue
        i = max(kandidater, key=lambda j: resultat["belastning"][j])
        overlast = sum(
            resultat["belastning"][j] > 100 + 1e-6
            for j in kandidater
        )
        utkoblet = s.gren_navn.index(c)
        rader.append({
            "linje ute": gren_navn[utkoblet],
            "høyest belastet gren": gren_navn[i],
            "flyt [MW]": round(float(resultat["flyt_MW"][i]), 1),
            "belastning %": round(float(resultat["belastning"][i]), 1),
            "antall overlast": int(overlast),
        })
    print(f"\nLinjeutfall ({len(rader)} tilfeller), sortert etter belastning:")
    if rader:
        print(pd.DataFrame(rader).sort_values(
            "belastning %", ascending=False
        ).to_string(index=False))

    # LMP og skyggepriser er ikke beregnet for SCOPF.
    # Disse kolonnene vises derfor ikke med tomme eller misvisende verdier.
