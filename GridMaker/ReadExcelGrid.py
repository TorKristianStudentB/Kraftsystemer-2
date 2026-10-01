from GridMaker.Imports import pd,Grid 

#---------Start: Funskjon som fyller inn i objektet grid fra excel arket n490--------
def MakeGrid(ExcelSheet):
   df=pd.read_excel(ExcelSheet, sheet_name=None)


   #---------Leser excel arket og bruker pandas DF-------
   def lese_excel_arket():
      grid = Grid("Grid")
      busDF   = df["bus"]
      lineDF  = df["line"]
      trafoDF = df["trafo"]
      genDF   = df["gen"]
      linkDF  = df["link"] if "link" in df else None   # lenke-fanen er valgfri
      return grid, busDF, lineDF, trafoDF, genDF, linkDF
   #---------Leser excel arket og bruker pandas DF-------
   grid, busDF, lineDF, trafoDF, genDF, linkDF = lese_excel_arket()


   #----------Sjekker linkene og setter effekten på P-load =P_load-Pinj, trenger derfor ikke lenkene i nettmodellen-------
   def link():
      if linkDF is not None:
         if linkDF is None or "Pinj" not in linkDF.columns:   # ingen lenker aa injisere
            return
         Nordics=["NO1","NO2","NO3","NO4","NO5","SE1","SE2","SE3","SE4","FI","DK2"]
         for i in range(len(linkDF)):
            if linkDF["area0"].iloc[i] in Nordics and linkDF["area1"].iloc[i] in Nordics:
               bus0=linkDF["bus0"].iloc[i]
               bus1=linkDF["bus1"].iloc[i]
               Pinj=linkDF["Pinj"].iloc[i]
               busDF["P_load"].iloc[bus0]=busDF["P_load"].iloc[bus0] - Pinj
               busDF["P_load"].iloc[bus1]=busDF["P_load"].iloc[bus1] + Pinj
            else:
                  if linkDF["area0"].iloc[i] in Nordics:
                     bus0=linkDF["bus0"].iloc[i]
                     Pinj=linkDF["Pinj"].iloc[i]
                     busDF["P_load"].iloc[bus0]=busDF["P_load"].iloc[bus0] - Pinj
                  else:
                     bus1=linkDF["bus1"].iloc[i]
                     Pinj=linkDF["Pinj"].iloc[i]
                     busDF["P_load"].iloc[bus1]=busDF["P_load"].iloc[bus1] - Pinj
   #----------Sjekker linkene og setter effekten på P-load =P_load-Pinj, trenger derfor ikke lenkene i nettmodellen-------
   link()      


   #----------Sjekker om det er Q og V begrensinger i excelarket-------------
   def betingelser_for_Q_og_V():
      Q_max=False
      Q_min=False
      V_min=False
      V_max=False
      P_max=False
      cordinater=False
      plassering=False

      if "Pmax" in genDF.columns:
               P_max=True
      if "Qmax" in genDF.columns:
         Q_max=True
      if "Qmin" in genDF.columns:
               Q_min=True
      if "Vmax" in busDF.columns:
               V_max=True
      if "Vmin" in busDF.columns:
               V_min=True
      if "lat" in busDF.columns and "lon" in busDF.columns:
               cordinater=True
      if "x" in busDF.columns and "y" in busDF.columns:
               plassering=True
      return Q_max,Q_min,V_max,V_min,P_max,cordinater,plassering
   #----------Sjekker om det er Q og V begrensinger i excelarket-------------
   Q_max , Q_min , V_max , V_min , P_max , cordinater , plassering = betingelser_for_Q_og_V()


   #--------------Sjekker om excelarket har eic koder-----------------------
   def eickode():
       eic_code_bus=False
       eic_code_line=False
       eic_code_trafo=False
       eic_code_gen=False

       if "eic code" in busDF.columns:
           eic_code_bus = True
       if "eic code" in lineDF.columns:
            eic_code_line = True
       if "eic code" in trafoDF.columns:
            eic_code_trafo = True
       if "eic code" in genDF.columns:
            eic_code_gen = True
       return eic_code_bus,eic_code_line,eic_code_trafo,eic_code_gen
   #--------------Sjekker om excelarket har eic koder-----------------------
   eic_code_bus , eic_code_line , eic_code_trafo , eic_code_gen = eickode()
 

   #-------------for å konvertere R og X til PU verdier før det lastes til nettet---------
   def konverter_til_PU():
        Sbase = busDF["S_base [MVA] "].iloc[0]    # fordi MVA
        Zbase = lineDF["Vbase"]**2 / Sbase        # per linje (Series)
        lineDF["R"] = lineDF["R"] / Zbase
        lineDF["X"] = lineDF["X"] / Zbase
        busDF["P_gen"] = busDF["P_gen"] / Sbase
        busDF["Q_gen"] = busDF["Q_gen"] / Sbase
        busDF["P_load"] = busDF["P_load"] / Sbase
        busDF["Q_load"] = busDF["Q_load"] / Sbase

        if P_max==True:
            genDF["Pmax"] = genDF["Pmax"] / Sbase
        if Q_max==True:
            genDF["Qmax"] = genDF["Qmax"] / Sbase
        if Q_min==True:
            genDF["Qmin"] = genDF["Qmin"] / Sbase
   #-------------for å konvertere R og X til PU verdier før det lastes til nettet---------
   konverter_til_PU()


   #---------Finner busser som står alene-----------------------
   def finn_elementer_alene():

      busser_i_line = set(lineDF["bus0"]).union(set(lineDF["bus1"]))
      busser_i_trafo = set(trafoDF["bus0"]).union(set(trafoDF["bus1"]))
      busser_alene = []
      for bus in busDF["bus_id"]:
         if bus not in busser_i_line and bus not in busser_i_trafo:
            busser_alene.append(int(bus))
      return busser_alene
   #---------Finner busser som står alene-----------------------
   busser_alene = finn_elementer_alene()


   #---------Sette verdier inn i grid objektet over-------------
   def Legge_verdier_i_objektet():
         
   
         #---------------Leser globale verdier base-----------
         Sbase = float(busDF["S_base [MVA] "].iloc[0])
         Vbase = float(busDF["Vbase"].iloc[0])
         grid.Base = Grid.BaseValues(Sbase, Vbase)
         #---------------Leser globale verdier base-----------


         #--------------oppretter bus fra excel arket----------
         for i in range(len(busDF)):
            b = Grid.bus(
               busNumber = int(busDF["bus_id"].iloc[i]),
               name      = str(busDF["name"].iloc[i]),
               Volt      = float(busDF["V [P.U]"].iloc[i]),
               Angle     = float(busDF["Angle [rad]"].iloc[i]),
               P_gen     = float(busDF["P_gen"].iloc[i]),
               Q_gen     = float(busDF["Q_gen"].iloc[i]),
               P_load    = float(busDF["P_load"].iloc[i]),
               Q_load    = float(busDF["Q_load"].iloc[i]),
               bidz      = str(busDF["bidz"].iloc[i]),
               Vbase     = float(busDF["Vbase"].iloc[i]),
               V_max = float(busDF["Vmax"].iloc[i]) if V_max else None,
               V_min = float(busDF["Vmin"].iloc[i]) if V_min else None,
               eic_code = str(busDF["eic code"].iloc[i]) if eic_code_bus else None,
               kodens_identifikasjonssystem = i,
               cords = [float(busDF["lat"].iloc[i]),float(busDF["lon"].iloc[i])] if cordinater else None,
               place = [float(busDF["x"].iloc[i]),float(busDF["y"].iloc[i])] if plassering else None,
            )
            grid.bus.append(b)

         #--------------oppretter bus fra excel arket----------

         
         #--------------oppretter linjer fra excel arket----------
         for i in range(len(lineDF)):

            b = Grid.line(
               lineNumber = int(lineDF["line_id"].iloc[i]),
               Name       = str(lineDF["name"].iloc[i]),
               R          = float(lineDF["R"].iloc[i]),
               X          = float(lineDF["X"].iloc[i]),
               B          = float(lineDF["B"].iloc[i]),
               Frombus    = int(lineDF["bus0"].iloc[i]),
               Tobus      = int(lineDF["bus1"].iloc[i]),
               lenght     = float(lineDF["length"].iloc[i]),
               eic_code = str(lineDF["eic code"].iloc[i]) if eic_code_line else None,
            )
            grid.line.append(b)
         #--------------oppretter linjer fra excel arket----------

         #--------------oppretter Trafoer fra excel arket----------
         for i in range(len(trafoDF)):
            tr = Grid.trafo(
               name    = str(trafoDF["name"].iloc[i]),
               type    = "tap",
               ratio   = float(trafoDF["ratio"].iloc[i]),
               Frombus = int(trafoDF["bus0"].iloc[i]),
               Tobus   = int(trafoDF["bus1"].iloc[i]),
               R       = float(trafoDF["R"].iloc[i]),
               X       = float(trafoDF["X"].iloc[i]),
               eic_code = str(trafoDF["eic code"].iloc[i]) if eic_code_trafo else None,
            )
            grid.trafo.append(tr)
         #--------------oppretter Trafoer fra excel arket----------


         #--------------oppretter generator data fra excel arket---
         for i in range(len(genDF)):
               b = Grid.gen(
                  P_max     = int(genDF["Pmax"].iloc[i]),
                  name      = str(genDF["name"].iloc[i]),
                  bus       = float(genDF["bus"].iloc[i]),
                  Q_max = float(genDF["Qmax"].iloc[i]) if Q_max else None,
                  Q_min = float(genDF["Qmin"].iloc[i]) if Q_min else None,
                  eic_code = str(genDF["eic code"].iloc[i]) if eic_code_gen else None,
               )
               grid.gen.append(b)
         #--------------oppretter generator data fra excel arket---
   #---------Sette verdier inn i grid objektet over-------------
   Legge_verdier_i_objektet()

         
   return grid
#---------END: Funskjon som fyller inn i objektet grid fra excel arket n490--------

