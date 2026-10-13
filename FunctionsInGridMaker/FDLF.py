from GridMaker.Imports import np,pd,Path,sys,time

#-------------Fast decoupled load flow kode---------------
def FDLF(grid):

   #--------oppstart for effektivitet------------
   def oppstart():
         Y=grid.admittansmatrise()
         N=len(grid.bus)
         return Y,N
   #--------oppstart for effektivitet------------
   Y,N=oppstart()

   #----------starter en tidsklokke på kjøringen-----------
   start_time = time.perf_counter()
   #----------starter en tidsklokke på kjøringen-----------
   

   #---Oversetter generatorenes busnummer til indekser----------
   def finn_gen_indekser(grid):
      gen_indekser = []
      for g in grid.gen:
         for b in grid.bus:
               if b.busNumber == g.bus:
                  gen_indekser.append(b.kodens_identifikasjonssystem)
      return gen_indekser
   #---Oversetter generatorenes busnummer til indekser----------
   gen_indekser = finn_gen_indekser(grid)


   #-------------Klassifiser bussene: ref / PV / PQ-----------------
   def busklasser(gen_indekser,Y,N):
      antall_busser = N
      bus_typ = []
      for i in range(antall_busser):
         if i == 0:
               bus_typ.append("ref")
         elif np.all(np.isclose(Y[i,:], 0)):   #bussen henger ikke sammen med noe -> hopp over den
               bus_typ.append("alene")
               continue
         elif i in gen_indekser:
               bus_typ.append("PV")
         else:
               bus_typ.append("PQ")
      return bus_typ
   #-------------Klassifiser bussene: ref / PV / PQ-----------------
   bus_k = busklasser(gen_indekser,Y,N)


   #--------Lager listene for B' og B''----------------
   def lagBmBmm(bus_k):
      buss_B_m = []
      buss_B_mm = []

      for i, klasse in enumerate(bus_k):
         if klasse in ("PV", "PQ"):
               buss_B_m.append(i)

         if klasse == "PQ":
               buss_B_mm.append(i)

      return buss_B_m, buss_B_mm
   #--------Lager listene for B' og B''----------------
   buss_B_m, buss_B_mm = lagBmBmm(bus_k)


   #--------------bruker X fra BÅDE linjer og trafoer----------------
   def bygg_grener(grid):
      grener = []
      for l in grid.line:
         i = next(b.kodens_identifikasjonssystem for b in grid.bus if b.busNumber == l.Frombus)
         j = next(b.kodens_identifikasjonssystem for b in grid.bus if b.busNumber == l.Tobus)
         grener.append((i, j, l.X))
      for t in grid.trafo:
         i = next(b.kodens_identifikasjonssystem for b in grid.bus if b.busNumber == t.Frombus)
         j = next(b.kodens_identifikasjonssystem for b in grid.bus if b.busNumber == t.Tobus)
         grener.append((i, j, t.X))
      return grener
   #--------------bruker X fra BÅDE linjer og trafoer----------------
   grener = bygg_grener(grid)


   #-----------Formel (B', "P–δ"-matrisen), for hver gren (i,j) med reaktans X------------
   def bygg_B_m(grener, buss_B_m,N):
      antall_busser=N
      B = np.zeros((antall_busser, antall_busser))
      for i, j, X in grener:
         b = 1/X
         B[i,i] = B[i,i] + b
         B[j,j] = B[j,j] + b
         B[i,j] = B[i,j] - b
         B[j,i] = B[j,i] - b
      return B[np.ix_(buss_B_m, buss_B_m)]
   #-----------Formel (B', "P–δ"-matrisen), for hver gren (i,j) med reaktans X------------
   B_merke = bygg_B_m(grener, buss_B_m,N)


   #-----------Bygg B'': -Im(Y). Y henter vi ferdig fra grid selv-------------
   def bygg_dobbel_prime_B(buss_B_mm,Y):
       B_dobbeltmerke = (-Y.imag)[np.ix_(buss_B_mm, buss_B_mm)]
       return B_dobbeltmerke
   #-----------Bygg B'': -Im(Y). Y henter vi ferdig fra grid selv-------------
   B_dobbeltmerke = bygg_dobbel_prime_B(buss_B_mm,Y)


   #-----------Effektflyt-formlene P, samme som Tor bruker i NewtonRaphson.py---------------
   def flyt_P(i, j, Y):
      Vi = grid.bus[i].Volt
      Vj = grid.bus[j].Volt
      Yij = np.abs(Y[i,j])
      vinkel_Y = np.angle(Y[i,j])
      di = grid.bus[i].Angle
      dj = grid.bus[j].Angle
      return Vi*Vj*Yij*np.cos(di - dj - vinkel_Y)
   #-----------Effektflyt-formlene P, samme som Tor bruker i NewtonRaphson.py---------------
   

   #-----------Effektflyt-formlene Q, samme som Tor bruker i NewtonRaphson.py---------------
   def flyt_Q(i, j, Y):
      Vi = grid.bus[i].Volt
      Vj = grid.bus[j].Volt
      Yij = np.abs(Y[i,j])
      vinkel_Y = np.angle(Y[i,j])
      di = grid.bus[i].Angle
      dj = grid.bus[j].Angle
      return Vi*Vj*Yij*np.sin(di - dj - vinkel_Y)
   #-----------Effektflyt-formlene Q, samme som Tor bruker i NewtonRaphson.py---------------


   #-------------Hva P og Q SKAL være på hver buss (gitt av last og produksjon)-------------
   def finn_planlagt_PQ(grid):
      P_planlagt = []
      Q_planlagt = []
      for b in grid.bus:
         P_planlagt.append(b.P_gen - b.P_load)
         Q_planlagt.append(b.Q_gen - b.Q_load)
      return P_planlagt, Q_planlagt
   #-------------Hva P og Q SKAL være på hver buss (gitt av last og produksjon)-------------
   P_planlagt, Q_planlagt = finn_planlagt_PQ(grid)


   #------------den endelige løkken som løser alt-------------------------
   def finalsolver(Y,N):

      # ========== 10) Iterasjonsløkka ==========
      tol = 1e-6         # hvor liten feilen må bli før vi sier vi er ferdige
      max_iter = 100      # sikkerhetsstopp, i tilfelle den ikke konvergerer
      iterasjon = 0
      ferdig = False
      solution=True
      antall_busser=N
      while ferdig == False:

         # Formel (mismatch/"feilen" i effekt, for hver buss i):
         #   ΔP_i = P_i^planlagt − Σ_j P_ij
         #   ΔQ_i = Q_i^planlagt − Σ_j Q_ij
         feil_P = []
         feil_Q = []
         for i in range(antall_busser):
            P_beregnet = 0
            Q_beregnet = 0
            for j in range(antall_busser):
                  P_beregnet = P_beregnet + flyt_P(i, j, Y)
                  Q_beregnet = Q_beregnet + flyt_Q(i, j, Y)
            feil_P.append(P_planlagt[i] - P_beregnet)
            feil_Q.append(Q_planlagt[i] - Q_beregnet)

         # Formel (konvergenskriterium):
         #   maks( |ΔP_i| for i i buss_B_m,  |ΔQ_i| for i i buss_B_mm )  ≤  tol  ?
         storste_feil = 0
         for i in buss_B_m:
            if abs(feil_P[i]) > storste_feil:
                  storste_feil = abs(feil_P[i])
         for i in buss_B_mm:
            if abs(feil_Q[i]) > storste_feil:
                  storste_feil = abs(feil_Q[i])

         if storste_feil <= tol:
            konvergerte = True
            ferdig = True
            break

         if iterasjon >= max_iter:
            ferdig = True
            break

         # Formel (P-halvsteg, løs for Δδ):
         #   B' · Δδ = ΔP / V        (elementvis: for hver buss i i buss_B_m)
         #   δ_i(ny) = δ_i(gammel) + Δδ_i
         if len(buss_B_m) > 0:
            hoyreside = []
            for i in buss_B_m:
                  hoyreside.append(feil_P[i] / grid.bus[i].Volt)
            hoyreside = np.array(hoyreside)


            
            #----------sjekker om den divigerer, og gir ikke konvererer----------
            try:
                delta_vinkel = np.linalg.solve(B_merke, hoyreside)
            except np.linalg.LinAlgError:
                flagg = True
                solution = False
                ferdig = True
                break

            if not np.all(np.isfinite(delta_vinkel)):
                flagg = True
                solution = False
                ferdig = True
                break

            elif np.max(delta_vinkel)>=1e2 or np.max(delta_vinkel)<=-1e2:
                flagg = True
                solution = False
                ferdig = True
                break
            #----------sjekker om den divigerer, og gir ikke konvererer----------


            for idx, i in enumerate(buss_B_m):
                  grid.bus[i].Angle = grid.bus[i].Angle + delta_vinkel[idx]

         # Formel (regn ΔQ på nytt med de oppdaterte vinklene, deretter Q-halvsteg, løs for ΔV):
         #   ΔQ_i = Q_i^planlagt − Σ_j Q_ij      (på nytt, siden δ nettopp endret seg)
         #   B'' · ΔV = ΔQ / V       (elementvis: for hver buss i i buss_B_mm)
         #   V_i(ny) = V_i(gammel) + ΔV_i
         if len(buss_B_mm) > 0:
            feil_Q = []
            for i in range(antall_busser):
                  Q_beregnet = 0
                  for j in range(antall_busser):
                     Q_beregnet = Q_beregnet + flyt_Q(i, j, Y)
                  feil_Q.append(Q_planlagt[i] - Q_beregnet)

            hoyreside = []
            for i in buss_B_mm:
                  hoyreside.append(feil_Q[i] / grid.bus[i].Volt)
            hoyreside = np.array(hoyreside)

            #----------sjekker om den divigerer, og gir ikke konvererer----------
            try:
                  delta_volt = np.linalg.solve(B_dobbeltmerke, hoyreside)
            except np.linalg.LinAlgError:
                  solution = False
                  break

            if not np.all(np.isfinite(delta_vinkel)):
                  solution = False
                  break

            elif np.max(delta_vinkel)>=1e2 or np.max(delta_vinkel)<=-1e2:
                  solution = False
                  break
            #----------sjekker om den divigerer, og gir ikke konvererer----------

            for idx, i in enumerate(buss_B_mm):
                  grid.bus[i].Volt = grid.bus[i].Volt + delta_volt[idx]

         iterasjon = iterasjon + 1

      return solution, iterasjon,feil_P,feil_Q
   #------------den endelige løkken som løser alt-------------------------
   konvergerte, iterasjon, feil_P,feil_Q=finalsolver(Y,N)


   #--------------Regner ut effektflyten på linjene-----------------
   def flow_in_line():
      flow = []
      for l in grid.line:
         b0 = next(b.kodens_identifikasjonssystem for b in grid.bus if b.busNumber == l.Frombus)
         b1 = next(b.kodens_identifikasjonssystem for b in grid.bus if b.busNumber == l.Tobus)
         v0 = np.abs(grid.bus[b0].Volt)*np.exp(1j*grid.bus[b0].Angle)
         v1 = np.abs(grid.bus[b1].Volt)*np.exp(1j*grid.bus[b1].Angle)
         straum = (v0 - v1)*l.admittans()
         flow.append(v0*np.conj(straum))
      return np.array(flow)
   #--------------Regner ut effektflyten på linjene-----------------


   if konvergerte==False:
      #---------------Loader løsningen som et eget object under hovednettet-----------
      grid.solution = grid.__class__.Solution(
         volt        = None,
         angle       = None,
         iterasjoner = None,
         mismatch    = None,
         konvergerte = konvergerte,
         flow_in_line = None,
         pv_to_pq_generators = None,
         power = None,
         qower = None,
         type ="FD",
         kjoretid = time.perf_counter() - start_time
      )
      #---------------Loader løsningen som et eget object under hovednettet-----------
   else:
      #---------------Loader løsningen som et eget object under hovednettet-----------
      grid.solution = grid.__class__.Solution(
         volt        = np.array([b.Volt for b in grid.bus]),
         angle       = np.array([b.Angle for b in grid.bus]),
         iterasjoner = int(iterasjon),
         mismatch    = [feil_P,feil_Q],
         konvergerte = konvergerte,
         flow_in_line = flow_in_line(),
         pv_to_pq_generators = None,
         power = np.array([sum(flyt_P(i, j, Y) for j in range(len(grid.bus))) for i in range(len(grid.bus))]),
         qower = np.array([sum(flyt_Q(i, j, Y) for j in range(len(grid.bus))) for i in range(len(grid.bus))]),
         type ="FD",
         kjoretid = time.perf_counter() - start_time
      )
      #---------------Loader løsningen som et eget object under hovednettet-----------
#-------------Fast decoupled load flow kode---------------
   