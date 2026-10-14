from GridMaker.Imports import MakeGrid,excelfilepath,pd,combinations, Grid

#-------------Endrer excelarket midlertidig for å sjekke at det konvergerer-------------
def N_minus_en_kriteriet(excelfilepath):


   #------------tester først på hovednettet--------------
   def oppstart_paa_hovednettet():
      grid_main = MakeGrid(excelfilepath)
      try:
         grid_main.loadflowsolutionNR()
         print("Hovednettet uten N-1 kriteriet konvergerte")
      except Exception as e:
         print(f"Det oppstod en feil på hovednettet uten N-1 igangsatt: {e}")
      return grid_main
   grid_main = oppstart_paa_hovednettet()
   #------------tester først på hovednettet--------------
   

   #-----------lage en par liste-----------
   def bygge_linje_par_listen(grid):
      Par=[]
      index_paa_par=[]
      grid = grid_main
      for i in range(len(grid.line)):
         a=grid.line[i].Frombus
         b=grid.line[i].Tobus
         Par.append([a,b])
         index_paa_par.append(grid.line[i].lineNumber)
      return Par,index_paa_par
   #-----------lage en par liste-----------
   Par, index_paa_par= bygge_linje_par_listen(grid_main)
   noder=[b.busNumber for b in grid_main.bus]


   # ------------ Sjekker om nettet blir splittet ------------
   def er_splittet(par):
      forelder = {n: n for n in noder}   #alle busser med, så en buss som mister alle linjene blir en øy

      def finn(x):
         forelder.setdefault(x, x)

         while forelder[x] != x:
            forelder[x] = forelder[forelder[x]]
            x = forelder[x]

         return x

      for a, b in par:
         rot_a = finn(a)
         rot_b = finn(b)

         if rot_a != rot_b:
            forelder[rot_a] = rot_b

      return len({finn(n) for n in forelder}) > 1
   # ------------ Sjekker om nettet blir splittet ------------


   #------------ Finner linjer som kan fjernes uten å lage en øy ------------
   def Hvilke_linje_uten_at_det_blir_oy(Par,index_paa_par):
      linjer_som_kan_fjernes = []

      for i, linje in enumerate(Par): #i er indeksen til Par
         resterende_linjer = Par[:i] + Par[i+1:]


         if not er_splittet(resterende_linjer):
            linjer_som_kan_fjernes.append(index_paa_par[i])

      return linjer_som_kan_fjernes
   #------------ Finner linjer som kan fjernes uten å lage en øy ------------
   linjer_som_kan_fjernes_før_det_blir_øy=Hvilke_linje_uten_at_det_blir_oy(Par,index_paa_par)


   #---------------Finner serier med linjer man kan fjerne før det blir øy----------
   def Hvilke_serier_av_linje_uten_at_det_blir_oy(Par):

      serier = []
      for antall in range(1, len(Par) + 1):
            for kombinasjon in combinations(range(len(Par)), antall):
   
               resterende_linjer = [
                     linje for i, linje in enumerate(Par)
                     if i not in kombinasjon
               ]
   
               if not er_splittet(resterende_linjer):
                     serier.append(list(kombinasjon))
   
      return serier 
   #---------------Finner serier med linjer man kan fjerne før det blir øy----------
   Serier_av_linjer_som_kan_fjernes_før_det_blir_øy = Hvilke_serier_av_linje_uten_at_det_blir_oy(Par)



   #---------Leser excel arket og bruker pandas DF-------
   def lese_excel_arket():
      grid = Grid(f"Grid")
      df = pd.read_excel(excelfilepath, sheet_name=None)
      busDF   = df["bus"]
      lineDF  = df["line"]
      trafoDF = df["trafo"]
      genDF   = df["gen"]
      linkDF  = df["link"] if "link" in df else None   # lenke-fanen er valgfri
      return grid,busDF, lineDF, trafoDF, genDF, linkDF
   #---------Leser excel arket og bruker pandas DF-------


   #-----------Hentet fra ReadExcelGrid------------
   def pakker_inn_her_så_jeg_kan_hente_for_N_minus_en(grid,busDF, lineDF, trafoDF, genDF, linkDF):
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
         lineDF["R_per_m"] = lineDF["R_per_m"] / Zbase * lineDF["length"]
         lineDF["X_per_m"] = lineDF["X_per_m"] / Zbase * lineDF["length"]
         lineDF["B_per_m"] = lineDF["B_per_m"] * Zbase * lineDF["length"] #annerledes fordi det er sussceptans
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
   #-----------Hentet fra ReadExcelGrid------------

   #------------Hoved løseren, den bruker en solverene for å sjekke N-1 kriteriet------------
   def finalsolver(excelfile, linjer_som_kan_fjernes_før_det_blir_øy, Serier_av_linjer_som_kan_fjernes_før_det_blir_øy):

      #--------------------Leser excelarket på nytt, fjerner linjene og tester at lastflyten konvergerer----------
      def test_nett_uten_linjer(fjernes_id):
         grid, busDF, lineDF, trafoDF, genDF, linkDF = lese_excel_arket()
         lineDF = lineDF[~lineDF["line_id"].isin(fjernes_id)]   #leser på nytt hver gang, så PU-omregningen ikke gjøres to ganger
         grid = pakker_inn_her_så_jeg_kan_hente_for_N_minus_en(grid, busDF, lineDF, trafoDF, genDF, linkDF)
         try:
            grid.loadflowsolutionNR()
            grid.FDLF()
            grid.DCPF()
         except Exception as e:
            print(f"N-1 kriteriet kom ikke i mål uten linje {fjernes_id}. Feilmelding {e}")
            return False
         return True
      #--------------------Leser excelarket på nytt, fjerner linjene og tester at lastflyten konvergerer----------


      #--------------------Denne kjører og fjerner linjer som ikke gir øyer i excelarket, en og en og trappevis----------
      def N_minus_en_kriteriet_for_trappevis_fjerning_og_kun_enkelt_fjerning_linjer():
         feilet_kun_en = []
         feilet_trappevis = []
         fjernet = []

         for linje_id in linjer_som_kan_fjernes_før_det_blir_øy:

            #-------tester når vi fjerner kun en linje som gjør at vi ikke får øy----
            if not test_nett_uten_linjer([linje_id]):
               feilet_kun_en.append(linje_id)
            #-------tester når vi fjerner kun en linje som gjør at vi ikke får øy----

            #-------tester når vi fjerner en og en linje trappevis, uten å få øy----
            fjernet.append(linje_id)
            if not test_nett_uten_linjer(fjernet):
               feilet_trappevis.append(linje_id)
               break
            #-------tester når vi fjerner en og en linje trappevis, uten å få øy----

         return feilet_kun_en, feilet_trappevis
      #--------------------Denne kjører og fjerner linjer som ikke gir øyer i excelarket, en og en og trappevis----------
      feilet_kun_en, feilet_trappevis = N_minus_en_kriteriet_for_trappevis_fjerning_og_kun_enkelt_fjerning_linjer()


      #--------------------Denne fjerner så trappevis serier linjer som ikke lager øyer i excelarket-----------------------------
      def N_minus_en_kriteriet_for_trappevis_fjerning_av_serier_linjer():
         feilet_serier = []

         for serie in Serier_av_linjer_som_kan_fjernes_før_det_blir_øy:   #serie er posisjoner i Par
            fjernet = []

            for posisjon in serie:
               fjernet.append(index_paa_par[posisjon])   #gjør om til line_id

               #-------tester når vi fjerner en og en linje i serien som gjør at vi ikke får øy----
               if not test_nett_uten_linjer(fjernet):
                  feilet_serier.append(list(fjernet))
                  break
               #-------tester når vi fjerner en og en linje i serien som gjør at vi ikke får øy----

         return feilet_serier
      #--------------------Denne fjerner så trappevis serier linjer som ikke lager øyer i excelarket-----------------------------
      feilet_serier = N_minus_en_kriteriet_for_trappevis_fjerning_av_serier_linjer()

      return feilet_kun_en, feilet_trappevis, feilet_serier
   #------------Hoved løseren, den bruker en solverene for å sjekke N-1 kriteriet------------
   feilet_kun_en, feilet_trappevis, feilet_serier =  finalsolver(excelfilepath, linjer_som_kan_fjernes_før_det_blir_øy, Serier_av_linjer_som_kan_fjernes_før_det_blir_øy)

   if feilet_kun_en == [] and feilet_trappevis ==[] and feilet_serier==[]:   #tomme lister = ingenting feilet
      return True
   else:
      return False
#-------------Endrer excelarket midlertidig for å sjekke at det konvergerer-------------
