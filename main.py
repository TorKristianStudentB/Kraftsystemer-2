from GridMaker.Imports import MakeGrid, Grid, np, validating,  lag_rapport, Path




#-----------------Her legges inn excelarket som inneholder nettet som skal leses-----------------
ExcelSheet = Path.cwd() / "Grid" / "test_trøndelagsnettet.xlsx1"
#-----------------Her legges inn excelarket som inneholder nettet som skal leses-----------------


#----------Main Running---------------
if __name__ == "__main__":
   #---------lager nettet til klassen grid fra excelarket-------
   grid = MakeGrid(ExcelSheet)
   #---------lager nettet til klassen grid fra excelarket-------
   
   #---------Kjører lastflytanalyse med DCPF  metode- 
   grid.DCPF()

   #---------Kjører lastflytanalyse med DCPF  metode-

   #-----------------Lager rapport om løsningene----------------
   #lag_rapport(grid, grid.solution.volt, grid.solution.angle, grid.solution.power, grid.solution.qower)
   #-----------------Lager rapport om løsningene----------------

#----------Main Running---------------
for line in grid.line:
    print(
        f"Linje {line.Frombus} -> {line.Tobus}: "
        f"R = {line.R*line.lenght:.8f} pu, X = {line.X*line.lenght:.8f} pu"
    )