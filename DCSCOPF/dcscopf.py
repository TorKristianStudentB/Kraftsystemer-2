from GridMaker.Imports import np, pd, time, excelfilepath
import pyomo.environ as pyo

#----------kostnad per generatortype [€/MWh], brukes hvis gen-arket ikke har en "cost"-kolonne----------
KOSTNAD_PER_TYPE = {"Run-Of-River": 5, "Hydro": 15, "Reservoir": 20, "Pumped Storage": 30, "OCGT": 80}
STANDARD_KOSTNAD = 50
#----------kostnad per generatortype [€/MWh], brukes hvis gen-arket ikke har en "cost"-kolonne----------


#-------------utfører DC optimal power flow----------------
def dcopf(grid, solver="appsi_highs"):

   #----------starter en tidsklokke på kjøringen-----------
   start_time = time.perf_counter()
   #----------starter en tidsklokke på kjøringen-----------


   #--------oppstart for effektivitet------------
   def oppstart():
      Sbase = grid.Base.Sbase
      N = len(grid.bus)
      indices = {bus.busNumber: i for i, bus in enumerate(grid.bus)}   # busNumber -> indeks
      return Sbase, N, indices
   #--------oppstart for effektivitet------------
   Sbase, N, indices = oppstart()


   #-----------trafoens tapp i pu (samme som i DCPF.py)-------
   def ratio_pu(trafo):
      vbase_fra = grid.bus[indices[trafo.Frombus]].Vbase
      vbase_til = grid.bus[indices[trafo.Tobus]].Vbase
      return trafo.ratio / (min(vbase_fra, vbase_til) / max(vbase_fra, vbase_til))
   #-----------trafoens tapp i pu (samme som i DCPF.py)-------


   #-----------samler linjer og trafoer i én grenliste: (navn, fra, til, b, Fmax i pu)-------
   #-----------linjene legges inn først, flow_in_line i Solution forutsetter denne rekkefølgen-------
   def bygg_grener():
      grener = []
      for line in grid.line:
         if line.X == 0:
            raise ValueError("DC-OPF krever reaktans ulik null på alle grener")
         grener.append((f"Linje {line.lineNumber}", indices[line.Frombus], indices[line.Tobus],
                        1 / line.X, line.S_max / Sbase))
      for trafo in grid.trafo:
         if trafo.X == 0:
            raise ValueError("DC-OPF krever reaktans ulik null på alle grener")
         grener.append((f"Trafo {trafo.Name}", indices[trafo.Frombus], indices[trafo.Tobus],
                        ratio_pu(trafo) / trafo.X, trafo.S_max / Sbase))   # samme grenvekt som DCPF
      return grener
   #-----------samler linjer og trafoer i én grenliste-------
   grener = bygg_grener()


   #---------finner busser som ikke henger sammen med noe (samme som "alene" i DCPF)--------------
   def finn_busser_alene():
      tilkoblet = {fra for _, fra, _, _, _ in grener} | {til for _, _, til, _, _ in grener}
      return [i for i in range(N) if i not in tilkoblet]
   #---------finner busser som ikke henger sammen med noe--------------
   busser_alene = finn_busser_alene()
   gen_buss = [indices[int(gen.bus)] for gen in grid.gen]   # gen.bus er float i grid-objektet


   #-----------kostnader per generator i €/MWh (gen-objektet har ikke type, så den leses fra excel)-------
   def hent_kostnader():
      genDF = pd.read_excel(excelfilepath, sheet_name="gen")
      if len(genDF) != len(grid.gen):
         raise ValueError("Antall generatorer i excel og grid stemmer ikke")
      if "cost" in genDF.columns:
         return genDF["cost"].astype(float).to_numpy()
      return np.array([KOSTNAD_PER_TYPE.get(t, STANDARD_KOSTNAD) for t in genDF["type2"]], dtype=float)
   #-----------kostnader per generator-------
   kostnad = hent_kostnader()


   #-----------bygger optimeringsmodellen i pyomo-------
   def bygg_modellen():
      m = pyo.ConcreteModel()

      #--------mengder: generatorer, busser (uten de som står alene) og grener--------
      m.G = pyo.Set(initialize=range(len(grid.gen)))
      m.B = pyo.Set(initialize=[i for i in range(N) if i not in busser_alene])
      m.L = pyo.Set(initialize=range(len(grener)))

      #--------variabler: produksjon [pu] og spenningsvinkel [rad], bus 0 er referansebussen--------
      def P_grenser(m, g):
         if gen_buss[g] in busser_alene:
            return (0.0, 0.0)
         return (0.0, grid.gen[g].P_max)
      m.P = pyo.Var(m.G, bounds=P_grenser)
      m.theta = pyo.Var(m.B)
      m.theta[0].fix(float(grid.bus[0].Angle))

      #--------flyt på gren l: F = b * (theta_fra - theta_til) [pu]--------
      def flyt_regel(m, l):
         _, fra, til, b, _ = grener[l]
         return b * (m.theta[fra] - m.theta[til])
      m.flyt = pyo.Expression(m.L, rule=flyt_regel)

      #--------objektfunksjon: min sum c_g * P_g [€/h]--------
      m.kostnad = pyo.Objective(expr=sum(kostnad[g] * m.P[g] * Sbase for g in m.G), sense=pyo.minimize)

      #--------effektbalanse per buss: produksjon - flyt ut + flyt inn = last--------
      def balanse_regel(m, i):
         produksjon = sum(m.P[g] for g in m.G if gen_buss[g] == i)
         flyt_ut    = sum(m.flyt[l] for l in m.L if grener[l][1] == i)
         flyt_inn   = sum(m.flyt[l] for l in m.L if grener[l][2] == i)
         return produksjon - flyt_ut + flyt_inn == grid.bus[i].P_load
      m.balanse = pyo.Constraint(m.B, rule=balanse_regel)

      #--------flytgrenser: -Fmax <= F <= Fmax--------
      def flytgrense_regel(m, l):
         Fmax = grener[l][4]
         return (-Fmax, m.flyt[l], Fmax)
      m.flytgrense = pyo.Constraint(m.L, rule=flytgrense_regel)

      #--------duals (LMP og skyggepriser), må lages før løsning--------
      m.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)
      return m
   #-----------bygger optimeringsmodellen i pyomo-------
   m = bygg_modellen()


   #-----------løser modellen, sjekker om den fant en løsning-----------
   def los_modellen():
      try:
         resultat = pyo.SolverFactory(solver).solve(m)
         return resultat.solver.termination_condition == pyo.TerminationCondition.optimal
      except (RuntimeError, ValueError) as feil:   # appsi kaster feil når ingen løsning finnes
         print(f"DCOPF fant ingen løsning. Feilmelding {feil}")
         return False
   #-----------løser modellen, sjekker om den fant en løsning-----------
   konvergerte = los_modellen()


   if not konvergerte:
      #---------------Loader løsningen som et eget object under hovednettet-----------
      grid.solution = grid.__class__.Solution(
            volt        = None,
            angle       = None,
            iterasjoner = None,
            mismatch    = None,
            konvergerte = False,
            flow_in_line = None,
            pv_to_pq_generators = None,
            power=None,
            qower=None,
            type = "DCOPF",
            kjoretid = time.perf_counter() - start_time
      )
      #---------------Loader løsningen som et eget object under hovednettet-----------
      return grid


   #-----------henter ut resultatene fra modellen-----------
   def hent_resultatene():
      P_gen   = np.array([pyo.value(m.P[g]) for g in m.G])                                # pu
      vinkler = np.array([pyo.value(m.theta[i]) if i in m.B else float(grid.bus[0].Angle)
                          for i in range(N)])                                              # rad
      flyt    = np.array([pyo.value(m.flyt[l]) * Sbase for l in m.L])                      # MW
      Fmax    = np.array([grener[l][4] * Sbase for l in m.L])                              # MW
      belastning = 100 * np.abs(flyt) / Fmax                                               # %
      return P_gen, vinkler, flyt, belastning
   #-----------henter ut resultatene fra modellen-----------
   P_gen, vinkler, flyt, belastning = hent_resultatene()


   #-----------LMP [€/MWh] og skyggepris på grenene, dualene er i €/h per pu, derfor / Sbase-----------
   def hent_duals():
      try:
         lmp = np.array([m.dual[m.balanse[i]] / Sbase if i in m.B else np.nan for i in range(N)])
         skyggepris = np.array([m.dual[m.flytgrense[l]] / Sbase for l in m.L]) + 0.0   # + 0.0 fjerner -0.0
         return lmp, skyggepris
      except KeyError:
         print("Solveren returnerte ingen duals")
         return None, None
   #-----------LMP og skyggepris-----------
   lmp, skyggepris = hent_duals()


   #---------Lagrer dispatch og vinkler på bussene og generatorene-------------------
   def lagrer_paa_bussene():
      for bus in grid.bus:
         bus.P_gen = 0.0
      for g, gen in enumerate(grid.gen):
         grid.bus[gen_buss[g]].P_gen += P_gen[g]
         gen.P_opf = P_gen[g]
      for i in range(N):
         grid.bus[i].Angle = vinkler[i]
   #---------Lagrer dispatch og vinkler på bussene og generatorene-------------------
   lagrer_paa_bussene()


   #---------------Loader løsningen som et eget object under hovednettet-----------
   grid.solution = grid.__class__.Solution(
         volt        = np.ones(N),
         angle       = vinkler,
         iterasjoner = 1,
         mismatch    = None,
         konvergerte = True,
         flow_in_line = flyt[:len(grid.line)],        # MW, samme format som DCPF (kun linjer)
         pv_to_pq_generators = None,
         power       = np.array([bus.P_gen - bus.P_load for bus in grid.bus]),
         qower       = np.zeros(N),                   # Q beregnes ikke av DC-modellen
         type        = "DCOPF",
         kjoretid    = time.perf_counter() - start_time
   )
   grid.solution.kostnad     = pyo.value(m.kostnad)   # €/h
   grid.solution.P_gen_MW    = P_gen * Sbase          # MW per generator
   grid.solution.gen_kostnad = kostnad                # €/MWh per generator
   grid.solution.gren_navn   = [gren[0] for gren in grener]
   grid.solution.flyt_MW     = flyt                   # alle grener (linjer + trafoer)
   grid.solution.belastning  = belastning             # % av S_max
   grid.solution.lmp         = lmp                    # €/MWh per buss
   grid.solution.skyggepris  = skyggepris             # €/MWh per MW ekstra kapasitet
   grid.solution.modell      = m                      # pyomo-modellen, f.eks. m.balanse.pprint()
   #---------------Loader løsningen som et eget object under hovednettet-----------

   return grid
#-------------utfører DC optimal power flow----------------


#-------------skriver ut resultatene fra DCOPF i tabellform----------------
def vis_resultater_DCOPF(grid):
   s = grid.solution
   if s is None or s.type != "DCOPF" or not s.konvergerte:
      print("Ingen DCOPF-løsning å vise")
      return

   print(f"\nTotal kostnad: {s.kostnad:,.0f} €/h")
   print(f"Total produksjon: {s.P_gen_MW.sum():.1f} MW   |   Kjøretid: {s.kjoretid*1000:.1f} ms")

   gen_tabell = pd.DataFrame({
      "generator":     [gen.name for gen in grid.gen],
      "buss":          [int(gen.bus) for gen in grid.gen],
      "kostnad €/MWh": s.gen_kostnad,
      "P [MW]":        np.round(s.P_gen_MW, 1),
      "P_max [MW]":    [gen.P_max * grid.Base.Sbase for gen in grid.gen],
   })
   print("\nDispatch (generatorer som produserer):")
   print(gen_tabell[gen_tabell["P [MW]"] > 0].to_string(index=False))

   gren_tabell = pd.DataFrame({
      "gren":         s.gren_navn,
      "flyt [MW]":    np.round(s.flyt_MW, 1),
      "belastning %": np.round(s.belastning, 1),
   })
   if s.skyggepris is not None:
      gren_tabell["skyggepris"] = np.round(s.skyggepris, 2)
   print("\nGrener sortert etter belastning:")
   print(gren_tabell.sort_values("belastning %", ascending=False).to_string(index=False))

   if s.lmp is not None:
      print("\nLMP per buss [€/MWh]:")
      print(pd.DataFrame({"buss": [bus.busNumber for bus in grid.bus],
                          "LMP":  np.round(s.lmp, 2)}).to_string(index=False))
#-------------skriver ut resultatene fra DCOPF i tabellform----------------
#----------Main Running---------------
if __name__ == "__main__":
   from GridMaker.Imports import MakeGrid

   grid = MakeGrid(excelfilepath)
   dcopf(grid)
   vis_resultater_DCOPF(grid)
