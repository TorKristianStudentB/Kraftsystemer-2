from GridMaker.Imports import excelfilepath, MakeGrid, Path, pd

#----------Main Running---------------
if __name__ == "__main__":


   #-------Opretter en A matrise til sammenlignign av resultater-----
   A_volt = pd.DataFrame(columns=["NR", "DC", "FD"])#,"PP_NR", "PP_NR2", "PP_DC", "PP_FD"])
   A_angle = pd.DataFrame(columns=["NR", "DC", "FD"])#,"PP_NR", "PP_NR2","PP_DC", "PP_FD"])
   #-------Opretter en A matrise til sammenlignign av resultater-----
   iterasjon = {}
   kjøretid = {}


   #---------lager nettet til klassen grid fra excelarket-------
   grid = MakeGrid(excelfilepath)
   #---------lager nettet til klassen grid fra excelarket-------
   

   #---------Kjører lastflytanalyse med Newtons Rapshons metode- 
   grid.loadflowsolutionNR()
   A_volt["NR"] = grid.solution.volt
   A_angle["NR"] = grid.solution.angle
   iterasjon["NR"] = grid.solution.iterasjoner
   kjøretid["NR"] = grid.solution.kjoretid
   print(grid.solution.pv_to_pq_generators)
   print("NR til Tor: vellyket")
   #---------Kjører lastflytanalyse med Newtons Rapshons metode-

   #---------Retarter gridet, så ikke neste solver får andre startbetingelser-------
   grid = MakeGrid(excelfilepath)
   #---------Retarter gridet, så ikke neste solver får andre startbetingelser-------

   #---------Kjører lastflytanalyse med DC metode- 
   grid.DCPF()
   A_volt["DC"] = grid.solution.volt
   A_angle["DC"] = grid.solution.angle
   iterasjon["DC"] = grid.solution.iterasjoner
   kjøretid["DC"] = grid.solution.kjoretid
   print("DCLF til Sverre: vellyket")
   #---------Kjører lastflytanalyse med DC metode-

   #---------Retarter gridet, så ikke neste solver får andre startbetingelser-------
   grid = MakeGrid(excelfilepath)
   #---------Retarter gridet, så ikke neste solver får andre startbetingelser-------

   #---------Kjører lastflytanalyse med FDLF metode- 
   grid.FDLF()
   A_volt["FD"] = grid.solution.volt
   A_angle["FD"] = grid.solution.angle
   iterasjon["FD"] = grid.solution.iterasjoner
   kjøretid["FD"] = grid.solution.kjoretid
   print("FDLD til Theo: vellyket")
   #---------Kjører lastflytanalyse med FDLF metode-

   
   #--------Printer resultatene i A--------------
   print(f"spenningen på alt er:\n{A_volt}")
   print("\n")
   print(f"vinkelen er : \n {A_angle}")
   print("\nAntall iterasjoner:")
   for solver, antall in iterasjon.items():
    print(f"{solver}: {antall}")

   print("\nKjøretid:")
   for solver, sekunder in kjøretid.items():
    print(f"{solver}: {sekunder:.6f} sekunder")
   #--------Printer resultatene i A--------------

   
#----------Main Running---------------