from GridMaker.Imports import np,time

#-------------utfører DC power flow----------------
def dc_power_flow(grid):

   #----------starter en tidsklokke på kjøringen-----------
   start_time = time.perf_counter()
   #----------starter en tidsklokke på kjøringen-----------

   #--------oppstart for effektivitet------------
   def oppstart():
       Y=grid.admittansmatrise()
       N=len(grid.bus)
       return Y,N
   #--------oppstart for effektivitet------------
   Y,N=oppstart()


   #-----------trafoens tapp i pu-------
   def ratio_pu(trafo):
      vbase_fra = next(b.Vbase for b in grid.bus if b.busNumber == trafo.Frombus)
      vbase_til = next(b.Vbase for b in grid.bus if b.busNumber == trafo.Tobus)
      return trafo.ratio / (min(vbase_fra, vbase_til) / max(vbase_fra, vbase_til))
   #-----------trafoens tapp i pu-------


   #-----------lager Y DC matrisen-------------
   def Y_convert(Y,N):
    # Tapsfri DC-modell: samme grenvekter brukes i matrise og effektflyt.
    Y_dc = np.zeros((N, N))
    indices = {bus.busNumber: i for i, bus in enumerate(grid.bus)}
    for branch in [*grid.line, *grid.trafo]:
        i, j = indices[branch.Frombus], indices[branch.Tobus]
        if branch.X == 0:
            raise ValueError("DC-lastflyt krever reaktans ulik null på alle grener")
        weight = 1 / branch.X
        if branch in grid.trafo:
            weight *= ratio_pu(branch)
        Y_dc[i, i] += weight
        Y_dc[j, j] += weight
        Y_dc[i, j] -= weight
        Y_dc[j, i] -= weight
    return Y,Y_dc
   #-----------lager Y DC matrisen-------------
   Y , Y_dc = Y_convert(Y,N)
   

   #---------oppretter klasser PV og PQ for bussene--------------------
   def busclassifier(Y):
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
   busPVPQ=busclassifier(Y)


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
      flagg=False
      solution=True
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
      #----------sjekker om den divigerer, og gir ikke konvererer----------
      try:
         delta_reduced = np.linalg.solve(Y_dc_reduced, P_reduced_pu)
      except np.linalg.LinAlgError:
         flagg = True
         solution = False
         delta = None
         return delta
      #----------sjekker om den divigerer, og gir ikke konvererer----------


      delta = np.full(len(grid.bus), float(grid.bus[0].Angle))

      for k in range(len(active_buses)):

         bus_index = active_buses[k]
         delta[bus_index] += delta_reduced[k]

      return delta
   #------------finner busser som skal være med i beregningen, dvs ikke referansebussen-----------      
   delta = busses_in_beregninen()


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


   #-------Beregner transformatorflyt i MW med samme modell som DC-matrisen----------
   def flow_in_trafo():
      flow = []
      for trafo in grid.trafo:
         for i in range(len(grid.bus)):
            if grid.bus[i].busNumber == trafo.Frombus:
               from_bus = i
            if grid.bus[i].busNumber == trafo.Tobus:
               to_bus = i
         P_ij = (delta[from_bus] - delta[to_bus]) * ratio_pu(trafo) / trafo.X
         flow.append(P_ij * grid.Base.Sbase)
      return flow
   #-------Beregner transformatorflyt i MW med samme modell som DC-matrisen----------
   trafo_flow = flow_in_trafo()


   #---------Lagrer vinkler-------------------
   def lagrer_beregneden_vinklene_paa_bussen():
      for i in range(len(grid.bus)):
         grid.bus[i].Angle = delta[i]
   #---------Lagrer vinkler-------------------
   lagrer_beregneden_vinklene_paa_bussen()


   #-------------Bygger formatering --------------------------------------------
   def bygg_formateringen():
      power = Y_dc @ delta               # netto busseffekt i pu, inkludert slack
      active_buses = [i for i, kind in enumerate(busPVPQ) if kind not in ("ref", "alene")]
      mismatch = P_scheduled[active_buses] - power[active_buses]
      konvergerte = bool(np.all(np.isfinite(delta)) and np.max(np.abs(mismatch), initial=0) <= 1e-6)
      qower = np.zeros(len(grid.bus))     # Q beregnes ikke av DC-modellen
      return power,mismatch,konvergerte,qower
   power,mismatch,konvergerte,qower = bygg_formateringen()
   #-------------Bygger formatering --------------------------------------------



   if delta is False:
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
               type = "DC",
               kjoretid = time.perf_counter() - start_time
         )
      #---------------Loader løsningen som et eget object under hovednettet-----------
   else:
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
            type = "DC",
            kjoretid = time.perf_counter() - start_time
      )
      #---------------Loader løsningen som et eget object under hovednettet-----------
#-------------utfører DC power flow----------------