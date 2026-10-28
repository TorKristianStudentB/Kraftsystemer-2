from GridMaker.Imports import MakeGrid, Path, pd,np,df,metode

#----------Main Running---------------
if __name__ == "__main__":

   df1 = {navn: ark.copy(deep=True) for navn, ark in df.items()}
   df2 = {navn: ark.copy(deep=True) for navn, ark in df.items()}
   df3 = {navn: ark.copy(deep=True) for navn, ark in df.items()}

   #---------lager nettet til klassen grid fra excelarket-------
   grid = MakeGrid(df1)
   #---------lager nettet til klassen grid fra excelarket-------


   print("Dette er overordnet spenning og vinkel mellom alle 6 metodene:")
   A_volt = pd.DataFrame(columns=["NR", "DC", "FD"])
   A_angle = pd.DataFrame(columns=["NR", "DC", "FD"])


   grid.loadflowsolutionNR()
   A_volt["NR"]=np.array(grid.solution.volt)
   A_angle["NR"]=np.array(grid.solution.angle)

   #---------lager nettet til klassen grid fra excelarket-------
   grid = MakeGrid(df2)
   #---------lager nettet til klassen grid fra excelarket-------

   grid.DCPF()

   A_volt["DC"]=np.array(grid.solution.volt)
   A_angle["DC"]=np.array(grid.solution.angle)

   grid = MakeGrid(df3)

   grid.FDLF()
   A_volt["FD"]=np.array(grid.solution.volt)
   A_angle["FD"]=np.array(grid.solution.angle)
   
   print(f"spenning: \n {A_volt}")

   print(f"vinkel: \n {A_angle}")






   