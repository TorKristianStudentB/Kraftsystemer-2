from GridMaker.Imports import MakeGrid,excelfilepath,pd,combinations

#-------------Endrer excelarket midlertidig for å sjekke at det konvergerer-------------
def endre_excelark_for_N_minus_en_kriteriet(excelfilepath):

   #------------tester først på hovednettet--------------
   def oppstart_paa_hovednettet():
      grid_main = MakeGrid(excelfilepath)
      try:
         grid_main.loadflowsolution()
         print("Hovednettet uten N-1 kriteriet konvergerte")
      except Exception as e:
         print(f"Det oppstod en feil på hovednettet uten N-1 igangsatt: {e}")
      return grid_main
   grid_main = oppstart_paa_hovednettet()
   #------------tester først på hovednettet--------------
   

   #-----------lage en par liste-----------
   def bygge_linje_par_listen(grid):
      Par=[]
      grid = grid_main
      for i in range(len(grid.line)):
         a=grid.line[i].Frombus
         b=grid.line[i].Tobus
         Par.append([a,b])
      return Par
   #-----------lage en par liste-----------
   Par = bygge_linje_par_listen(grid_main)


   # ------------ Sjekker om nettet blir splittet ------------
   def er_splittet(par):
    forelder = {}

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
   def Hvilke_linje_uten_at_det_blir_oy(Par):
      linjer_som_kan_fjernes = []

      for i, linje in enumerate(Par):
         resterende_linjer = Par[:i] + Par[i+1:]

         if not er_splittet(resterende_linjer):
            linjer_som_kan_fjernes.append(linje)

      return linjer_som_kan_fjernes
   #------------ Finner linjer som kan fjernes uten å lage en øy ------------
   linjer_som_kan_fjernes_før_det_blir_øy=Hvilke_linje_uten_at_det_blir_oy(Par)


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
                     serier.append([list(Par[i]) for i in kombinasjon])
   
      return serier
   #---------------Finner serier med linjer man kan fjerne før det blir øy----------
   Serier_av_linjer_som_kan_fjernes_før_det_blir_øy = Hvilke_serier_av_linje_uten_at_det_blir_oy(Par)




   for i in range(len(grid_main.line)):
      df=pd.read_excel(excelfilepath, sheet_name=None)
      
