from GridMaker.Imports import MakeGrid,excelfilepath,pd,combinations, Grid,df,metode,forenklet,np

#-------------Endrer excelarket midlertidig for å sjekke at det konvergerer-------------
def N_minus_en_kriteriet(df,metode):


   #------------tester først på hovednettet--------------
   def oppstart_paa_hovednettet():
      grid_main = MakeGrid(df)
      grid_main.loadflowsolutionNR()
      busNumber=[b.busNumber for b in grid_main.bus]
      return grid_main,busNumber
   grid_main,busNumber = oppstart_paa_hovednettet()
   #------------tester først på hovednettet--------------


   #------------Finner overtredelser i et løst nett, returnerer en liste med tekster------------
   def overtredelse(grid,metode):


      #-------------kjører riktig metode først--------
      def metode_kjøring_konverger_test(metode):
         if metode=="NR": grid.loadflowsolutionNR()
         if metode=="FDLF":grid.FDLF()
         if metode=="DCPF":grid.DCPF()

         return grid.solution.konvergerte
      #-------------kjører riktig metode først--------
      konvergerte=metode_kjøring_konverger_test(metode)

      if konvergerte:
         liste = []
         Sbase = grid.Base.Sbase
         toleranse = 1e-3   #MW/MVAr, ellers gir flyttallsfeil falske overtredelser når NR legger Q akkurat på grensen
         volt = grid.solution.volt
         power = grid.solution.power
         qower = grid.solution.qower
         flyt = grid.solution.flow_in_line


         #-----------busnumrene løsningen gjelder for (færre enn i grid hvis nettet er Krons-redusert)----------
         if forenklet:
            nett = grid.admittansmatrise()[1]
            busnumre_i_losning = [b.busNumber for b in nett.bus]
         else:
            busnumre_i_losning = [b.busNumber for b in grid.bus]
         bus_fra_nummer = {b.busNumber: b for b in grid.bus}
         #-----------busnumrene løsningen gjelder for (færre enn i grid hvis nettet er Krons-redusert)----------


         #-----------Krons-redusert: regner ut spenningene på de fjernede bussene (null injeksjon), slik at flyt per linje og trafo kan sjekkes----------
         def gjenopprett_full_losning():
            from FunctionsInGridMaker.admittansmatrise import cutsem
            Y_full = cutsem(grid)
            k = nett.k_noder_egen_identifikasjon
            behold = [i for i in range(len(grid.bus)) if i not in k]
            Vb = np.array(volt)*np.exp(1j*np.array(grid.solution.angle))

            #---------Y_kk · Vk + Y_kb · Vb = 0  (ingen effekt inn på de fjernede bussene)-------
            Vk = -np.linalg.solve(Y_full[np.ix_(k,k)], Y_full[np.ix_(k,behold)] @ Vb)
            #---------Y_kk · Vk + Y_kb · Vb = 0  (ingen effekt inn på de fjernede bussene)-------

            for idx in range(len(behold)):
               grid.bus[behold[idx]].Volt = float(np.abs(Vb[idx]))
               grid.bus[behold[idx]].Angle = float(np.angle(Vb[idx]))
            for idx in range(len(k)):
               grid.bus[k[idx]].Volt = float(np.abs(Vk[idx]))
               grid.bus[k[idx]].Angle = float(np.angle(Vk[idx]))
         #-----------Krons-redusert: regner ut spenningene på de fjernede bussene (null injeksjon), slik at flyt per linje og trafo kan sjekkes----------


         #-----------kompleks effektflyt inn i hver linje fra Frombus, regnet fra spenningene på bussene----------
         def linjeflyt_fra_spenninger():
            flow = []
            for l in grid.line:
               b0 = next(b.kodens_identifikasjonssystem for b in grid.bus if b.busNumber == l.Frombus)
               b1 = next(b.kodens_identifikasjonssystem for b in grid.bus if b.busNumber == l.Tobus)
               v0 = np.abs(grid.bus[b0].Volt)*np.exp(1j*grid.bus[b0].Angle)
               v1 = np.abs(grid.bus[b1].Volt)*np.exp(1j*grid.bus[b1].Angle)
               straum = (v0 - v1)*l.admittans()
               flow.append(v0*np.conj(straum))
            return np.array(flow)
         #-----------kompleks effektflyt inn i hver linje fra Frombus, regnet fra spenningene på bussene----------


         #-----------flyten i Krons-redusert nett er per ekvivalent gren, så linjer og trafoer regnes på det fulle nettet (ikke mulig for DC)----------
         if forenklet:
            if metode == "DCPF":
               flyt = None
               flyt_trafo = None
            else:
               gjenopprett_full_losning()
               flyt = linjeflyt_fra_spenninger()
               flyt_trafo = grid.flow_in_trafo()
         else:
            flyt_trafo = grid.flow_in_trafo()
         #-----------flyten i Krons-redusert nett er per ekvivalent gren, så linjer og trafoer regnes på det fulle nettet (ikke mulig for DC)----------


         #-----------spenning under V_min eller over V_max på hver buss----------
         if volt is not None:
            for k in range(len(busnumre_i_losning)):
               bus = bus_fra_nummer[busnumre_i_losning[k]]
               navn = f"Bus {bus.busNumber} ({bus.Name})"
               if bus.V_min is not None:
                  if volt[k] < bus.V_min:
                     liste.append(f"{navn}: V = {volt[k]:.4f} pu utenfor [{bus.V_min}, {bus.V_max}]")
               if bus.V_max is not None:
                  if volt[k] > bus.V_max:
                     liste.append(f"{navn}: V = {volt[k]:.4f} pu utenfor [{bus.V_min}, {bus.V_max}]")
         #-----------spenning under V_min eller over V_max på hver buss----------


         #-----------tilsynelatende effekt over S_max på hver buss----------
         if power is not None and qower is not None:
            for k in range(len(busnumre_i_losning)):
               bus = bus_fra_nummer[busnumre_i_losning[k]]
               navn = f"Bus {bus.busNumber} ({bus.Name})"
               S = (power[k]**2 + qower[k]**2)**0.5 * Sbase
               if S > bus.S_max + toleranse:
                  liste.append(f"{navn}: S = {S:.1f} MVA over S_max = {bus.S_max:.1f}")
         #-----------tilsynelatende effekt over S_max på hver buss----------

         #-----------tilsynelatende effekt over S_max på hver trafo---------
         if flyt_trafo is not None:
            if len(flyt_trafo) == len(grid.trafo):
               for i in range(len(grid.trafo)):
                  S_trafo = abs(flyt_trafo[i])
                  if isinstance(flyt_trafo[i], complex):
                     S_trafo = S_trafo * Sbase
                  if S_trafo > grid.trafo[i].S_max + toleranse:
                     liste.append(f"Trafo {grid.trafo[i].transformer_id} ({grid.trafo[i].Name}): S = {S_trafo:.1f} MVA over S_max = {grid.trafo[i].S_max:.1f}")
         #-----------tilsynelatende effekt over S_max på hver trafo---------


         #-----------generatorene på bussen: P_gen over P_max, Q_gen over Q_max eller under Q_min----------
         if power is not None and qower is not None:
            for k in range(len(busnumre_i_losning)):
               bus = bus_fra_nummer[busnumre_i_losning[k]]
               navn = f"Bus {bus.busNumber} ({bus.Name})"
               P_max_sum = 0
               Q_max_sum = 0
               Q_min_sum = 0
               antall_generatorer = 0

               #---summerer grensene til alle generatorene som står på bussen----
               for j in range(len(grid.gen)):
                  if grid.gen[j].bus == bus.busNumber:
                     P_max_sum = P_max_sum + grid.gen[j].P_max
                     if grid.gen[j].Q_max is not None:
                        Q_max_sum = Q_max_sum + grid.gen[j].Q_max
                     if grid.gen[j].Q_min is not None:
                        Q_min_sum = Q_min_sum + grid.gen[j].Q_min
                     antall_generatorer = antall_generatorer + 1
               #---summerer grensene til alle generatorene som står på bussen----

               if antall_generatorer > 0:
                  P_gen = (power[k] + bus.P_load) * Sbase
                  Q_gen = (qower[k] + bus.Q_load) * Sbase
                  if P_max_sum > 0:
                     if P_gen > P_max_sum * Sbase + toleranse:
                        liste.append(f"{navn}: P_gen = {P_gen:.1f} MW over P_max = {P_max_sum * Sbase:.1f}")
                  if Q_max_sum > 0:
                     if Q_gen > Q_max_sum * Sbase + toleranse:
                        liste.append(f"{navn}: Q_gen = {Q_gen:.1f} MVAr over Q_max = {Q_max_sum * Sbase:.1f}")
                  if Q_min_sum < 0:   #Q_min = 0 i excelarket betyr ingen grense
                     if Q_gen < Q_min_sum * Sbase - toleranse:
                        liste.append(f"{navn}: Q_gen = {Q_gen:.1f} MVAr under Q_min = {Q_min_sum * Sbase:.1f}")
         #-----------generatorene på bussen: P_gen over P_max, Q_gen over Q_max eller under Q_min----------


         #-----------flyt i linjene over S_max, kompleks flyt er i pu og reell flyt (DC) er allerede i MW----------
         if flyt is not None:
            if len(flyt) == len(grid.line):
               for i in range(len(grid.line)):
                  S_linje = abs(flyt[i])
                  if isinstance(flyt[i], complex):
                     S_linje = S_linje * Sbase
                  if S_linje > grid.line[i].S_max + toleranse:
                     liste.append(f"Linje {grid.line[i].lineNumber} ({grid.line[i].Name}): S = {S_linje:.1f} MVA over S_max = {grid.line[i].S_max:.1f}")
         #-----------flyt i linjene over S_max, kompleks flyt er i pu og reell flyt (DC) er allerede i MW----------

         return liste

      else:
         return [f"konvergerte ikke med metode {metode}"]
   #------------Finner overtredelser i et løst nett, returnerer en liste med tekster------------


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



   #-----------lage en par liste for trafoene, de blir ikke tatt ut, men de holder nettet sammenhengende-----------
   def bygge_trafo_par_listen(grid):
      Par_trafo=[]
      Trafo_index_paa_par=[]
      grid = grid_main

      for i in range(len(grid.trafo)):
         a=grid.trafo[i].Frombus
         b=grid.trafo[i].Tobus
         Par_trafo.append([a,b])
         Trafo_index_paa_par.append(grid.trafo[i].transformer_id)

      return Par_trafo,Trafo_index_paa_par
   #-----------lage en par liste for trafoene, de blir ikke tatt ut, men de holder nettet sammenhengende-----------
   Par_trafo,Trafo_index_paa_par = bygge_trafo_par_listen(grid_main)



   # ------------Sjekker om nettet blir splittet til øy True False------------
   def er_splittet(par):
      forelder = {n: n for n in busNumber}

      def finn(x):
         while forelder[x] != x:
               forelder[x] = forelder[forelder[x]]
               x = forelder[x]
         return x

      for a, b in par:
         rot_a = finn(a)
         rot_b = finn(b)

         if rot_a != rot_b:
               forelder[rot_a] = rot_b

      return len({finn(n) for n in busNumber}) > 1
   #------------Sjekker om nettet blir splittet til øy True False------------



   #------------ Finner linjer som kan fjernes uten å lage en øy ------------
   def Hvilke_linje_trafo_uten_at_det_blir_oy(Par,index_paa_par,Par_andre):
      linjer_som_kan_fjernes = []

      for i, linje in enumerate(Par): #i er indeksen til Par
         resterende_linjer = Par[:i] + Par[i+1:] + Par_andre   #Par_andre er den andre typen (linjer/trafoer), den blir stående


         if not er_splittet(resterende_linjer):
            linjer_som_kan_fjernes.append(index_paa_par[i])

      return linjer_som_kan_fjernes
   #------------ Finner linjer som kan fjernes uten å lage en øy ------------
   linjer_som_kan_fjernes_før_det_blir_øy=Hvilke_linje_trafo_uten_at_det_blir_oy(Par,index_paa_par,Par_trafo)
   Trafoer_som_kan_fjernes_før_det_bir_øy=Hvilke_linje_trafo_uten_at_det_blir_oy(Par_trafo,Trafo_index_paa_par,Par)


   #------------Hoved løseren, den bruker en solverene for å sjekke N-1 kriteriet------------
   def finalsolver(linjer_som_kan_fjernes_før_det_blir_øy,Trafoer_som_kan_fjernes_før_det_bir_øy):

      Hvilke_generatorer_skal_testes_som_utkoblet="all"
      overtredelser_N_minus_en = {}


      #--------------------Leser excelarket på nytt, fjerner linjene og tester at lastflyten konvergerer----------
      def test_nett_uten_linjer_og_trafo(linjer_som_kan_fjernes_før_det_blir_øy,Trafoer_som_kan_fjernes_før_det_bir_øy,df):

         #--------------kjører en for løkke for alle linjer som skal tas us-------------
         for i, line_id in enumerate(linjer_som_kan_fjernes_før_det_blir_øy):

            #-----------fjerner nå den ene elemetnet i excelarket, og så leser grid på nytt----------
            df1 = {navn: ark.copy(deep=True) for navn, ark in df.items()}
            df1["line"] = df1["line"][df1["line"]["line_id"] != line_id]
            grid = MakeGrid(df1)
            #-----------fjerner nå den ene elemetnet i excelarket, og så leser grid på nytt----------

            #---------------sjekker overtredelser på linjene----------------
            overtredelser_N_minus_en[(line_id, metode)] = overtredelse(grid,metode)
            #---------------sjekker overtredelser på linjene----------------
         #--------------kjører en for løkke for alle linjer som skal tas us-------------


         #--------------kjører en for løkke for alle trafoer som skal tas us-------------
         for i, trafo_id in enumerate(Trafoer_som_kan_fjernes_før_det_bir_øy):

            #-----------fjerner nå den ene elemetnet i excelarket, og så leser grid på nytt----------
            df1 = {navn: ark.copy(deep=True) for navn, ark in df.items()}
            df1["trafo"] = df1["trafo"][df1["trafo"]["transformer_id"] != trafo_id]
            grid = MakeGrid(df1)
            #-----------fjerner nå den ene elemetnet i excelarket, og så leser grid på nytt----------

            #---------------sjekker overtredelser på Trafoene----------------
            overtredelser_N_minus_en[(trafo_id, metode)] = overtredelse(grid,metode)
            #---------------sjekker overtredelser på Trafoene-----------------


         #--------------kjører en for løkke for alle trafoer som skal tas us-------------
      #--------------------Leser excelarket på nytt, fjerner linjene og tester at lastflyten konvergerer----------
      test_nett_uten_linjer_og_trafo(linjer_som_kan_fjernes_før_det_blir_øy,Trafoer_som_kan_fjernes_før_det_bir_øy,df)

      if not forenklet:
         #-----------------Tester hvor det fjernes generatorer også---------------
         def remove_generators_and_test(name):

            #-------hvis det ikke er alle, så skal denne her finne radnummeret-------
            enkel_generator_utkobling=False
            for i in range(len(df["gen"])):
               if df["gen"]["name"].iloc[i]==name:
                  generator_utkoblet_radnummer=i
                  enkel_generator_utkobling=True
                  break
            #-------hvis det ikke er alle, så skal denne her finne radnummeret-------


            if name=="all":
               for i in range(len(df["gen"])):

                  #-----------fjerner nå den ene elemetnet i excelarket, og så leser grid på nytt----------
                  df1 = {navn: ark.copy(deep=True) for navn, ark in df.items()}
                  df1["gen"] = df1["gen"].drop(index=df1["gen"].index[i])
                  grid = MakeGrid(df1)
                  #-----------fjerner nå den ene elemetnet i excelarket, og så leser grid på nytt----------

                  #---------------sjekker overtredelser----------------
                  generator_name=df["gen"]["name"].iloc[i]
                  overtredelser_N_minus_en[(f"generator {generator_name} ute", metode)] = overtredelse(grid,metode)
                  #---------------sjekker overtredelser----------------


            elif enkel_generator_utkobling:
               #-----------fjerner nå den ene elemetnet i excelarket, og så leser grid på nytt----------
               df1 = {navn: ark.copy(deep=True) for navn, ark in df.items()}
               df1["gen"] = df1["gen"].drop(index=df1["gen"].index[generator_utkoblet_radnummer])
               grid = MakeGrid(df1)
               #-----------fjerner nå den ene elemetnet i excelarket, og så leser grid på nytt----------

               #---------------sjekker overtredelser----------------
               generator_name=df["gen"]["name"].iloc[generator_utkoblet_radnummer]
               overtredelser_N_minus_en[(f"generator {generator_name} ute", metode)] = overtredelse(grid,metode)
               #---------------sjekker overtredelser----------------
         #-----------------Tester hvor det fjernes generatorer også---------------
         remove_generators_and_test(Hvilke_generatorer_skal_testes_som_utkoblet)



      return overtredelser_N_minus_en
   #------------Hoved løseren, den bruker en solverene for å sjekke N-1 kriteriet------------
   overtredelser_N_minus_en  =  finalsolver(linjer_som_kan_fjernes_før_det_blir_øy,Trafoer_som_kan_fjernes_før_det_bir_øy)


   #-----------hvis den ene siden av overtredelser er tom, grunnet valgt dictonary, så fungerer alt
   if all(not v for v in overtredelser_N_minus_en.values()):
      print(True)

   #-----------Hvis det ikke fungerte,gi ut overtredelsene-------------------------------
   else:
      print(overtredelser_N_minus_en)

   return overtredelser_N_minus_en
#-------------Endrer excelarket midlertidig for å sjekke at det konvergerer-------------
