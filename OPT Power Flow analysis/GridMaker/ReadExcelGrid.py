from GridMaker.Imports import pd,df
from GridMaker.ClassGrid import Grid,np,forenklet   # direkte, ikke via Imports (unngår sirkulær import)

#---------Start: Funskjon som fyller inn i objektet grid fra excel arket n490--------
def MakeGrid(df):


   #---------jobber på en kopi, slik at pu-konverteringen ikke endrer df som sendes inn-------
   df = {navn: ark.copy(deep=True) for navn, ark in df.items()}
   #---------jobber på en kopi, slik at pu-konverteringen ikke endrer df som sendes inn-------


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


   #---------radnumrene må være 0,1,2,... (N-1 fjerner rader, og nye rader legges til med len(df) som indeks)-------
   for ark in (busDF, lineDF, trafoDF, genDF):
      ark.reset_index(drop=True, inplace=True)
   #---------radnumrene må være 0,1,2,... (N-1 fjerner rader, og nye rader legges til med len(df) som indeks)-------


   #---------uten forenklet får hver generator sin egen buss, og busarket trenger da P_gen og Q_gen-------
   if not forenklet:
      busDF["P_gen"] = 0.0
      busDF["Q_gen"] = 0.0
   #---------uten forenklet får hver generator sin egen buss, og busarket trenger da P_gen og Q_gen-------


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
      if "Vmax" in busDF.columns or "V_max" in busDF.columns:   #bus-arket bruker V_max og V_min
               V_max=True
      if "Vmin" in busDF.columns or "V_min" in busDF.columns:
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
        lineDF["R_per_m"] = lineDF["R_per_m"] / Zbase * lineDF["length"]
        lineDF["X_per_m"] = lineDF["X_per_m"] / Zbase * lineDF["length"]
        lineDF["B_per_m"] = lineDF["B_per_m"] * Zbase * lineDF["length"] #annerledes fordi det er sussceptans
        genDF["P_gen"] = genDF["P_gen"] / Sbase
        genDF["Q_gen"] = genDF["Q_gen"] / Sbase
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



   #---------veldig kjekk når jeg fjerner linje, og så kan bruke denne her etterpå.
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


   #-------------finner gjennomsnittspris per bus hvis forenklet modell er True-----------
   def finne_pris_per_bus_og_P_gen_og_Q_Gen_gitt_forenklet_er_true():

      price_per_bus = []
      P_sum_bus=[]
      Q_sum_bus=[]

      for i in df["bus"]["bus_id"]:
         generatorer = df["gen"].loc[df["gen"]["bus"] == i, "P_gen"]
         generatorer_Q = df["gen"].loc[df["gen"]["bus"] == i, "Q_gen"]
         P_sum_bus.append(generatorer.sum())
         Q_sum_bus.append(generatorer_Q.sum())

         if not generatorer.empty:
            W = generatorer / generatorer.sum()
            price = df["gen"].loc[df["gen"]["bus"] == i, "cost_per_MW"]
            price_per_bus.append(price @ W)
         else:
              price_per_bus.append(None)

      return price_per_bus , P_sum_bus , Q_sum_bus
   #-------------finner gjennomsnittspris per bus hvis forenklet modell er True-----------
   price_per_bus , P_sum_bus , Q_sum_bus = finne_pris_per_bus_og_P_gen_og_Q_Gen_gitt_forenklet_er_true()
                    
                 
                 
       



   #---------Sette verdier inn i grid objektet over-------------
   def Legge_verdier_i_objektet():


         #ny kode her for å ha muligheten for åå gjøre det mer komplekst
         if not forenklet:
            #---------lage kunstige busser og linjer for hver generator------------
            def lage_busser_og_linjer_for_generator_hvor_load_er_null_og_positiv_gen(genDF,busDF,lineDF):
         
         
               #------------først lage bussene---------
               def lage_nye_busser_for_hver_generator(i):
                  busDF.loc[len(busDF)] = {
                     "bus_id": busDF["bus_id"].max()+1,#peker på den nye bussen, har ikke med +1 nå på grunn av det
                     "name": genDF["name"].iloc[i],
                     "bidz": busDF.loc[busDF["bus_id"] == genDF["bus"].iloc[i],"bidz"].iloc[0], #denne må du knytte til ritkgi bus og så bidz
                     "Vbase":busDF.loc[busDF["bus_id"] == genDF["bus"].iloc[i],"Vbase"].iloc[0],
                     "lat":genDF["lat"].iloc[i],
                     "lon":genDF["lon"].iloc[i],
                     "S_base [MVA] ": busDF.loc[busDF["bus_id"] == genDF["bus"].iloc[i],"S_base [MVA] "].iloc[0],
                     "V [P.U]":1,
                     "Angle [rad]":0,
                     "S_max":busDF.loc[busDF["bus_id"] == genDF["bus"].iloc[i],"S_max"].iloc[0],
                     "P_gen":genDF["P_gen"].iloc[i],        #generatorens egen produksjon (allerede i pu)
                     "Q_gen":genDF["Q_gen"].iloc[i],
                     "V_max":busDF.loc[busDF["bus_id"] == genDF["bus"].iloc[i],"V_max"].iloc[0],
                     "V_min":busDF.loc[busDF["bus_id"] == genDF["bus"].iloc[i],"V_min"].iloc[0],
                     "P_load":0,
                     "Q_load":0,
                     }
                  return busDF["bus_id"].max() #returner bus_id til den nye bussen
               #------------først lage bussene---------
               
         
               #------------Lage linjer tilkoblet generatoren og bussen------
               def lage_nye_linjer_mellom_generator_og_buss(i):
                  lineDF.loc[len(lineDF)] = {
                     "Vbase":busDF.loc[busDF["bus_id"] == genDF["bus"].iloc[i],"Vbase"].iloc[0],
                     "line_id": lineDF["line_id"].max()+1,
                     "name": genDF["name"].iloc[i] + " – " + busDF.loc[busDF["bus_id"] == genDF["bus"].iloc[i],"name"].iloc[0],
                     "R_per_m": lineDF["R_per_m"].min(),
                     "X_per_m": lineDF["X_per_m"].min(),
                     "B_per_m": lineDF["B_per_m"].min(),
                     "bus0": busDF["bus_id"].max(),
                     "bus1": busDF.loc[busDF["bus_id"] == genDF["bus"].iloc[i],"bus_id"].iloc[0],
                     "length": 500,
                     "eic code": None,
                     "S_max":np.sqrt(genDF["Pmax"].iloc[i]**2+ genDF["Qmax"].iloc[i]**2) * busDF["S_base [MVA] "].iloc[0],   #S_max er i MVA, Pmax og Qmax er i pu
                     }     
                  return lineDF["line_id"].max()#returner den nye line id
               #------------Lage linjer tilkoblet generatoren og bussen------
            
               bus_id_kunstige=[]
               line_id_kunstige=[]

               for i in range(len(genDF)):
                     bus_id_kunstige.append(lage_nye_busser_for_hver_generator(i))
                     line_id_kunstige.append(lage_nye_linjer_mellom_generator_og_buss(i))
               return bus_id_kunstige,line_id_kunstige
            #---------lage kunstige busser og linjer for hver generator------------
            bus_id_kunstige,line_id_kunstige=lage_busser_og_linjer_for_generator_hvor_load_er_null_og_positiv_gen(genDF,busDF,lineDF) 
         else:
              bus_id_kunstige=[]
              line_id_kunstige=[]



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
                  P_gen     = float(busDF["P_gen"].iloc[i]) if not forenklet else P_sum_bus[i], 
                  Q_gen     = float(busDF["Q_gen"].iloc[i]) if not forenklet else Q_sum_bus[i],
                  P_load    = float(busDF["P_load"].iloc[i]),
                  Q_load    = float(busDF["Q_load"].iloc[i]),
                  bidz      = str(busDF["bidz"].iloc[i]),
                  Vbase     = float(busDF["Vbase"].iloc[i]),
                  V_max = float(busDF["V_max" if "V_max" in busDF.columns else "Vmax"].iloc[i]) if V_max else None,
                  V_min = float(busDF["V_min" if "V_min" in busDF.columns else "Vmin"].iloc[i]) if V_min else None,
                  eic_code = str(busDF["eic code"].iloc[i]) if eic_code_bus else None,
                  kodens_identifikasjonssystem = i,
                  cords = [float(busDF["lat"].iloc[i]),float(busDF["lon"].iloc[i])] if cordinater else None,
                  place = [float(busDF["x"].iloc[i]),float(busDF["y"].iloc[i])] if plassering else None,
                  S_max = float(busDF["S_max"].iloc[i]),
                  kunstig_buss = busDF["bus_id"].iloc[i] in bus_id_kunstige if not forenklet else None,
                  price =  price_per_bus[i] if forenklet else None
               )
               grid.bus.append(b)

         #--------------oppretter bus fra excel arket----------

         
         #--------------oppretter linjer fra excel arket----------
         for i in range(len(lineDF)):
               b = Grid.line(
                  Vbase      = int(lineDF["Vbase"].iloc[i]),
                  lineNumber = int(lineDF["line_id"].iloc[i]),
                  Name       = str(lineDF["name"].iloc[i]),
                  R          = float(lineDF["R_per_m"].iloc[i]),
                  X          = float(lineDF["X_per_m"].iloc[i]),
                  B          = float(lineDF["B_per_m"].iloc[i]),
                  Frombus    = int(lineDF["bus0"].iloc[i]),
                  Tobus      = int(lineDF["bus1"].iloc[i]),
                  lenght     = float(lineDF["length"].iloc[i]),
                  eic_code = str(lineDF["eic code"].iloc[i]) if eic_code_line else None,
                  S_max = float(lineDF["S_max"].iloc[i]),
                  kunstig_line = lineDF["line_id"].iloc[i] in line_id_kunstige,
               )
               grid.line.append(b)
         #--------------oppretter linjer fra excel arket----------

         #--------------oppretter Trafoer fra excel arket----------
         for i in range(len(trafoDF)):
            tr = Grid.trafo(
               transformer_id = float(trafoDF["transformer_id"].iloc[i]),
               name    = str(trafoDF["name"].iloc[i]),
               type    = "tap",
               ratio   = float(trafoDF["ratio"].iloc[i]),
               Frombus = int(trafoDF["bus0"].iloc[i]),
               Tobus   = int(trafoDF["bus1"].iloc[i]),
               R       = float(trafoDF["R"].iloc[i]),
               X       = float(trafoDF["X"].iloc[i]),
               eic_code = str(trafoDF["eic code"].iloc[i]) if eic_code_trafo else None,
               S_max = float(trafoDF["S_max"].iloc[i]),
            )
            grid.trafo.append(tr)
         #--------------oppretter Trafoer fra excel arket----------


         #--------------oppretter generator data fra excel arket---
         for i in range(len(genDF)):
               b = Grid.gen(
                  P_max     = float(genDF["Pmax"].iloc[i]),   #float, ellers kuttes desimalene i pu-verdien
                  name      = str(genDF["name"].iloc[i]),
                  bus       = float(genDF["bus"].iloc[i]) if forenklet else float(bus_id_kunstige[i]),   #uten forenklet står generatoren på sin egen kunstige buss
                  Q_max = float(genDF["Qmax"].iloc[i]) if Q_max else None,
                  Q_min = float(genDF["Qmin"].iloc[i]) if Q_min else None,
                  eic_code = str(genDF["eic code"].iloc[i]) if eic_code_gen else None,
                  cost_per_MW = float(genDF["cost_per_MW"].iloc[i])
               )
               grid.gen.append(b)
         #--------------oppretter generator data fra excel arket---
   #---------Sette verdier inn i grid objektet over-------------
   Legge_verdier_i_objektet()



         
   return grid
#---------END: Funskjon som fyller inn i objektet grid fra excel arket n490--------

