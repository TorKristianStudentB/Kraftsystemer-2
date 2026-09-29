from GridMaker.Imports import np

#-------------utfører DC power flow----------------
def dc_power_flow(grid):


   #-----------lager Y DC matrisen-------------
   def Y_convert():
    Y=grid.admittansmatrise()
    Y_dc=-np.imag(Y)
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

      #------------konverterer aktiv effekt til pu-----------------------------------------------
      P_reduced_pu = P_reduced / grid.Base.Sbase

      #-------------løser dc power flow og finner spenningsvinklen-------------------------------
      delta_reduced = np.linalg.solve(Y_dc_reduced, P_reduced_pu)
      delta = np.zeros(len(grid.bus))

      for k in range(len(active_buses)):

         bus_index = active_buses[k]
         delta[bus_index] = delta_reduced[k]
   #------------finner busser som skal være med i beregningen, dvs ikke referansebussen-----------      


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

   

   #-------------beregne nødvendig netto aktiv effekt fra slack bussen----------
   def netto_aktiv_effekt():
     p_slack = 0 
     for i in range(len(grid.bus)):
        if busPVPQ[i] != "ref" and busPVPQ[i] != "alene":
            p_slack = p_slack - P_scheduled[i]

     for i in range(len(grid.bus)):
        grid.bus[i].Angle = delta[i]
   #-------------beregne nødvendig netto aktiv effekt fra slack bussen----------
   netto_aktiv_effekt()


   #---------------Loader løsningen som et eget object under hovednettet-----------
   grid.solution = grid.__class__.Solution(
         volt        = np.array([b.Volt for b in grid.bus]),
         angle       = np.array([b.Angle for b in grid.bus]),
         iterasjoner = 1,
         mismatch    = 0,
         konvergerte = True,
         flow_in_line = np.array(line_flow),
         pv_to_pq_generators = None,
         power=None,
         qower=None,
         type="DCPF"
   )
   #---------------Loader løsningen som et eget object under hovednettet-----------
   

   return grid
#-------------utfører DC power flow----------------