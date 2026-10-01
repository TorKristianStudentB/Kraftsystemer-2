from GridMaker.Imports import MakeGrid, Grid, np, validating,  lag_rapport, Path




#-----------------Her legges inn excelarket som inneholder nettet som skal leses-----------------
ExcelSheet = Path.cwd() / "Grid" / "Enkel_nett_teste_qmaxmin.xlsx"
#-----------------Her legges inn excelarket som inneholder nettet som skal leses-----------------


#----------Main Running---------------
if __name__ == "__main__":
   #---------lager nettet til klassen grid fra excelarket-------
   grid = MakeGrid(ExcelSheet)
   #---------lager nettet til klassen grid fra excelarket-------
   
   #---------Kjører lastflytanalyse med Newtons Rapshons metode- 
   grid.loadflowsolutionNR()
   #---------Kjører lastflytanalyse med Newtons Rapshons metode-

   #-----------------Lager rapport om løsningene----------------
   lag_rapport(grid, grid.solution.volt, grid.solution.angle, grid.solution.power, grid.solution.qower)
   #-----------------Lager rapport om løsningene----------------
#----------Main Running---------------