from GridMaker.Imports import np

#-------------utfører DC power flow----------------
def dc_power_flow(grid):


   #-----------lager Y DC matrisen-------------
   def Y_convert():
    Y=grid.admittansmatrise()
    # Tapsfri DC-modell: samme grenvekter brukes i matrise og effektflyt.
    Y_dc = np.zeros((len(grid.bus), len(grid.bus)))
    indices = {bus.busNumber: i for i, bus in enumerate(grid.bus)}
    for branch in [*grid.line, *grid.trafo]:
        i, j = indices[branch.Frombus], indices[branch.Tobus]
        if branch.X == 0:
            raise ValueError("DC-lastflyt krever reaktans ulik null på alle grener")
        weight = 1 / branch.X
        if branch in grid.trafo:
            weight *= branch.ratio
        Y_dc[i, i] += weight
        Y_dc[j, j] += weight
        Y_dc[i, j] -= weight
        Y_dc[j, i] -= weight
    return Y,Y_dc
   #-----------lager Y DC matrisen-------------
   Y,Y_dc = Y_convert()
   

   #---------oppretter klasser PV og PQ for bussene--------------------
   def busclassifier():
        bus=[]
        for i in range(len(grid.bus)):
            if i == 0:
                bus.append("ref")
                continue
            if np.all(np.isclose(Y[i,:], 0)):   #bussen henger ikke sammen med noe -> hopp over den
                bus.append("alene")
                continue
            PV=False
            for j in range(len(grid.gen)):
                if grid.gen[j].bus == grid.bus[i].busNumber:
                    PV=True
                    break
            if PV:
                bus.append("PV")
            else:
                bus.append("PQ")
        return bus
   #---------oppretter klasser PV og PQ for bussene--------------------
   busPVPQ=busclassifier()


   #-----------------------regner ut netto aktiv effekt--------------
   def power_scheduled():
        P_scheduled = []

        for i in range(len(grid.bus)):
            P = grid.bus[i].P_gen - grid.bus[i].P_load
            P_scheduled.append(P)
        return np.array(P_scheduled)
   #-----------------------regner ut netto aktiv effekt--------------
   P_scheduled = power_scheduled()


   #------------finner busser som skal være med i beregningen, dvs ikke referansebussen----------- 
   def busses_in_beregninen():

      active_buses = []
      for i in range(len(grid.bus)):

         if busPVPQ[i] != "ref" and busPVPQ[i] != "alene":
               active_buses.append(i)

      #---------fjerner referansebussen og frakoblede busser fra Y_dc og P_scheduled--------------
      Y_dc_reduced = Y_dc[np.ix_(active_buses, active_buses)]
      P_reduced = P_scheduled[active_buses]

      #------------effekten er allerede i pu fra Excel-importen---------------------------------
      P_reduced_pu = P_reduced

      #-------------løser dc power flow og finner spenningsvinklen-------------------------------
      delta_reduced = np.linalg.solve(Y_dc_reduced, P_reduced_pu)
      delta = np.full(len(grid.bus), float(grid.bus[0].Angle))

      for k in range(len(active_buses)):

         bus_index = active_buses[k]
         delta[bus_index] += delta_reduced[k]

      return delta

   #------------finner busser som skal være med i beregningen, dvs ikke referansebussen-----------      

   delta =busses_in_beregninen()

   #------------beregne aktiv effektflyt på linjene--------------- 
   def flow_in_line():
        flow = []

        for line in grid.line:

            for i in range(len(grid.bus)):

                if grid.bus[i].busNumber == line.Frombus:
                    from_bus = i

                if grid.bus[i].busNumber == line.Tobus:
                    to_bus = i
            #----------beregner linjeflyten i pu og konverterer til MW-------------
            P_ij = (delta[from_bus] - delta[to_bus])/line.X
            P_ij = P_ij * grid.Base.Sbase

            flow.append(P_ij)

        return flow
   #------------beregne aktiv effektflyt på linjene--------------- 
   line_flow = flow_in_line()

   # Beregner transformatorflyt i MW med samme modell som DC-matrisen.
   def flow_in_trafo():
      flow = []
      for trafo in grid.trafo:
         for i in range(len(grid.bus)):
            if grid.bus[i].busNumber == trafo.Frombus:
               from_bus = i
            if grid.bus[i].busNumber == trafo.Tobus:
               to_bus = i
         P_ij = (delta[from_bus] - delta[to_bus]) * trafo.ratio / trafo.X
         flow.append(P_ij * grid.Base.Sbase)
      return flow

   trafo_flow = flow_in_trafo()

   

   # Lagrer de beregnede vinklene på bussene.
   for i in range(len(grid.bus)):
      grid.bus[i].Angle = delta[i]

   #-------------Bygger formatering --------------------------------------------

   power = Y_dc @ delta               # netto busseffekt i pu, inkludert slack
   active_buses = [i for i, kind in enumerate(busPVPQ) if kind not in ("ref", "alene")]
   mismatch = P_scheduled[active_buses] - power[active_buses]
   konvergerte = bool(np.all(np.isfinite(delta)) and np.max(np.abs(mismatch), initial=0) <= 1e-6)
   qower = np.zeros(len(grid.bus))     # Q beregnes ikke av DC-modellen


   #-------------Bygger formatering --------------------------------------------

   #---------------Loader løsningen som et eget object under hovednettet-----------
   grid.solution = grid.__class__.Solution(
         volt        = np.array([b.Volt for b in grid.bus]),
         angle       = np.array([b.Angle for b in grid.bus]),
         iterasjoner = 1,
         mismatch    = mismatch,
         konvergerte = konvergerte,
         flow_in_line = np.array(line_flow),
         pv_to_pq_generators = None,
         power=power,
         qower=qower,
   )
   #---------------Loader løsningen som et eget object under hovednettet-----------
   

   # Skriver ut vinkler, effektflyt og kontroll av løsningen.
   def skriv_resultater():
      print("\nDC-lastflyt:")
      print("Løsning godkjent:", grid.solution.konvergerte)

      # Vinklene lagres i radianer og vises i grader.
      print("\nSpenningsvinkler:")
      for i in range(len(grid.bus)):
         vinkel = np.degrees(grid.solution.angle[i])
         print(f"Buss {grid.bus[i].busNumber}: {vinkel:.4f} grader")

      # Busseffekten lagres i pu og vises i MW.
      print("\nNetto aktiv effekt per buss:")
      for i in range(len(grid.bus)):
         effekt = grid.solution.power[i] * grid.Base.Sbase
         print(f"Buss {grid.bus[i].busNumber}: {effekt:.4f} MW")

      # Første buss er referansebussen som balanserer nettet.
      slack_effekt = grid.solution.power[0] * grid.Base.Sbase
      print(f"\nSlackbuss {grid.bus[0].busNumber}: {slack_effekt:.4f} MW")

      # Linje- og transformatorflyt er allerede beregnet i MW.
      print("\nAktiv effektflyt på linjene:")
      for i in range(len(grid.line)):
         line = grid.line[i]
         print(f"Linje {line.Frombus} -> {line.Tobus}: {line_flow[i]:.4f} MW")

      print("\nAktiv effektflyt gjennom transformatorene:")
      for i in range(len(grid.trafo)):
         trafo = grid.trafo[i]
         print(f"Trafo {trafo.Frombus} -> {trafo.Tobus}: {trafo_flow[i]:.4f} MW")

      # Viser største restfeil i effektligningene uten slackbussen.
      maks_avvik = 0.0
      for avvik in grid.solution.mismatch:
         if abs(avvik) > maks_avvik:
            maks_avvik = abs(avvik)
      print(f"\nStørste effektavvik: {maks_avvik:.3e} pu")

   skriv_resultater()
   return grid
#-------------utfører DC power flow----------------
