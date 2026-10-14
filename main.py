from GridMaker.Imports import excelfilepath, MakeGrid, Path, pd

#----------Main Running---------------
if __name__ == "__main__":

   #---------lager nettet til klassen grid fra excelarket-------
   grid = MakeGrid(excelfilepath)
   #---------lager nettet til klassen grid fra excelarket-------


   #solvere = {"Newton-Raphson": "loadflowsolutionNR", "DC": "DCPF", "Fast decoupled": "FDLF", "PP Newton-Raphson": "validating_PP_NR", "PP DC": "validating_PP_DC", "PP Fast decoupled": "validating_PP_FDPF"}
   grid.resultater("DC")
   