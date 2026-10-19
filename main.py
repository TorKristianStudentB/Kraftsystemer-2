from GridMaker.Imports import excelfilepath, MakeGrid, Path, pd,np

#----------Main Running---------------
if __name__ == "__main__":

   #---------lager nettet til klassen grid fra excelarket-------
   grid = MakeGrid(excelfilepath)
   #---------lager nettet til klassen grid fra excelarket-------

   A_volt = pd.DataFrame(columns=["NR", "DC", "FD", "PP_NR", "PP_DC", "PP_FD"])
   A_angle = pd.DataFrame(columns=["NR", "DC", "FD", "PP_NR", "PP_DC", "PP_FD"])

   grid.loadflowsolutionNR()
   A_volt["NR"]=np.array(grid.solution.volt)
   A_angle["NR"]=np.array(grid.solution.angle)

   #---------lager nettet til klassen grid fra excelarket-------
   grid = MakeGrid(excelfilepath)
   #---------lager nettet til klassen grid fra excelarket-------

   grid.DCPF()
   A_volt["DC"]=np.array(grid.solution.volt)
   A_angle["DC"]=np.array(grid.solution.angle)

   grid = MakeGrid(excelfilepath)

   grid.FDLF()
   A_volt["FD"]=np.array(grid.solution.volt)
   A_angle["FD"]=np.array(grid.solution.angle)

   grid = MakeGrid(excelfilepath)

   grid.validating_PP_DC()
   A_volt["PP_DC"]=np.array(grid.solution.volt)
   A_angle["PP_DC"]=np.array(grid.solution.angle)

   grid = MakeGrid(excelfilepath)

   grid.validating_PP_FDPF()
   A_volt["PP_FD"]=np.array(grid.solution.volt)
   A_angle["PP_FD"]=np.array(grid.solution.angle)

   grid = MakeGrid(excelfilepath)

   grid.validating_PP_NR()
   A_volt["PP_NR"]=np.array(grid.solution.volt)
   A_angle["PP_NR"]=np.array(grid.solution.angle)

   

   print(f"spenning: \n {A_volt}")

   print(f"vinkel: \n {A_angle}")


   #solvere = {"Newton-Raphson": "loadflowsolutionNR", "DC": "DCPF", "Fast decoupled": "FDLF", "PP Newton-Raphson": "validating_PP_NR", "PP DC": "validating_PP_DC", "PP Fast decoupled": "validating_PP_FDPF"}
   metode="Newton Raphson"
   print(f"Dette er kort om resultater med {metode} og N-1 resultatene om nettet\n")
   grid.resultater("Newton Raphson")

   