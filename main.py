from GridMaker.Imports import MakeGrid, Path, pd, validating_PP_NR, validating_PP_DC




#-----------------Her legges inn excelarket som inneholder nettet som skal leses-----------------
ExcelSheet = Path.cwd() / "Grid" / "test_trøndelagsnettet.xlsx"
#-----------------Her legges inn excelarket som inneholder nettet som skal leses-----------------


#----------Main Running---------------
if __name__ == "__main__":


   #-------Opretter en A matrise til sammenlignign av resultater-----
   A_volt = pd.DataFrame(columns=["NR", "DC", "FD","PP_NR", "PP_DC"])
   A_angle = pd.DataFrame(columns=["NR", "DC", "FD","PP_NR", "PP_DC"])
   #-------Opretter en A matrise til sammenlignign av resultater-----


   #---------lager nettet til klassen grid fra excelarket-------
   grid = MakeGrid(ExcelSheet)
   #---------lager nettet til klassen grid fra excelarket-------
   

   #---------Kjører lastflytanalyse med Newtons Rapshons metode- 
   grid.loadflowsolutionNR()
   A_volt["NR"] = grid.solution.volt
   A_volt["NR"] = grid.solution.angle
   print("Newtons Raphson til Tor: vellyket")
   #---------Kjører lastflytanalyse med Newtons Rapshons metode-


   #---------Kjører lastflytanalyse med DC metode- 
   grid.DCPF()
   A_volt["DC"] = grid.solution.volt
   A_angle["DC"] = grid.solution.angle
   print("DCLF til Sverre: vellyket")
   #---------Kjører lastflytanalyse med DC metode-


   #---------Kjører lastflytanalyse med FDLF metode- 
   grid.FDLF()
   A_volt["FD"] = grid.solution.volt
   A_angle["FD"] = grid.solution.angle
   print("FDLD til Theo: vellyket")
   #---------Kjører lastflytanalyse med FDLF metode-

   #----------vegard legger du inn--------------------
   #---------Kjører lastflytanalyse med pandapower NR metode- 
   validating_PP_NR(ExcelSheet)
   A_volt["PP_NR"] = grid.solution.volt
   A_angle["PP_NR"] = grid.solution.angle
   print("PP_NR til Vegard & Håkon: vellyket")
   #---------Kjører lastflytanalyse med pandapower NR metode-


   #---------Kjører lastflytanalyse med pandapower DC metode- 
   validating_PP_DC()
   A_volt["PP_DC"] = grid.solution.volt
   A_angle["PP_DC"] = grid.solution.angle
   print("PP_DC til Andreas: vellyket")
   #---------Kjører lastflytanalyse med pandapower DC metode-   
   
   #--------Printer resultatene i A--------------
   print(A_volt)
   print(A_angle)
   #--------Printer resultatene i A--------------
#----------Main Running---------------