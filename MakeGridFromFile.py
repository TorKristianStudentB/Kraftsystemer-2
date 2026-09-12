import os
from pathlib import Path
import pandas as pd
import random
import sys
import numpy as np



#--------------------Hente filstien til megselv, må øke til mer--------
current_path = os.getcwd()
current_path=Path(current_path)
TorKodePath=current_path
TorKodePath=TorKodePath / "TorKode"
sys.path.append(str(TorKodePath))
#--------------------Hente filstien til megselv, må øke til mer--------

#--------funksjonshenting---------
from theveninZth import theveninZth
from admittansmatrise import cutsem
#--------funksjonshenting---------




#----------------Fetching the lates grid xlsx file start-----------------------
FolderName = "Grid"
FileName = "GridVersion1.xlsx"

def read_xlsx(FolderName, FileName):
    folder = Path(FolderName)
    # Find file with the specific name
    files = list(folder.rglob(FileName))
    if not files:
        raise FileNotFoundError(
            f"Could not find '{FileName}' in '{FolderName}'"
        )
    file = files[0]
    print(f"Reading: {file}")
    return pd.read_excel(file, sheet_name=None)

df = read_xlsx(FolderName, FileName)

#----------------Fetching the lates grid xlsx file end-----------------------


#----------Making a grid from xslx start----
class Grid:

   def __init__(self,Name):
      self.Name=Name
      self.Base = None      # BaseValues object
      self.bus = []       # list of bus objects
      self.line = []       # list of line objects


   def thevenin(self,bus1,bus2):
      return theveninZth(self,bus1,bus2)

   def admittansmatrise(self):
      return cutsem(self)

#----------Base values start----------------
   class BaseValues:
      def __init__(self,Sbase,Vbase):
         self.Sbase = Sbase
         self.Vbase = Vbase

#----------Base values end------------------


#----------bus start------------------------
   class bus:
      busNumber:int
      Volt:float
      Angle:float
      P_gen:float
      Q_gen:float
      P_load:float
      Q_load:float
      def __init__(self, busNumber,Name,Volt,Angle,P_gen,Q_gen,P_load,Q_load):
        self.name = busNumber
        self.Name = Name
        self.Volt = Volt
        self.Angle = Angle
        self.P_gen = P_gen
        self.Q_gen = Q_gen
        self.P_load = P_load
        self.Q_load = Q_load

      
#----------bus end------------------------


#----------lines start----------------------
   class line:   
      lineNumber:int
      R:float
      X:float
      B:float
      Frombus:int
      Tobus:int

      def __init__(self,lineNumber,Name,R,X,B,Frombus,Tobus):
            self.lineNumber = lineNumber
            self.Name = Name
            self.R = R
            self.X = X
            self.B = B
            self.Frombus = Frombus
            self.Tobus = Tobus


      def admittans(self):
         return 1/complex(self.R, self.X)

   
#----------lines end----------------------
      

#----------Trafo start----------------------
   class trafo:   
      name:str
      type:str
      ratio:float
      Frombus:float
      Tobus:int
      R:float
      X:float
      voltP:float
      voltS:float

      def __init__(self, name, type, ratio, Frombus, Tobus, R, X, voltP, voltS):
         self.Name = name
         self.Type = type
         self.Ratio = ratio
         self.Frombus = Frombus
         self.Tobus = Tobus
         self.R = R
         self.X = X
         self.voltP = voltP
         self.voltS = voltS
         

      def admittans(self):
            return 1/complex(self.R, self.X)

#----------Trafo end------------------------
#----------Making a grid from xslx end----




def MakeGrid(df):
   grid = Grid("Grid")

   busData = df["BusData"]
   BranchData = df["BranchData"]

   #reading the base values (stored in the first row of busData)
   Sbase = busData["S_base [MVA] "].iloc[0]
   Vbase = busData["V_base"].iloc[0]
   grid.Base = Grid.BaseValues(Sbase, Vbase)

   #reading the busses and implementing it in the grid
   for i in range(len(busData)):
      busNumber = int(busData["Bus Num"].iloc[i])
      bus = Grid.bus(
         busNumber = busNumber,
         Name      = f"bus {busNumber}",
         Volt      = float(busData["V [V]"].iloc[i]),
         Angle     = float(busData["Angle [rad]"].iloc[i]),
         P_gen     = float(busData["P_gen"].iloc[i]),
         Q_gen     = float(busData["Q_gen"].iloc[i]),
         P_load    = float(busData["P_load"].iloc[i]),
         Q_load    = float(busData["Q_load"].iloc[i]),
      )
      grid.bus.append(bus)

   #reading the lines/branches and implementing it in the grid
   for i in range(len(BranchData)):
      Frombus = int(BranchData["From Line"].iloc[i])
      Tobus   = int(BranchData["To Line"].iloc[i])
      line = Grid.line(
         lineNumber = i + 1,
         Name       = f"line {Frombus}-{Tobus}",
         R          = float(BranchData["R [pu]"].iloc[i]),
         X          = float(BranchData["X [pu]"].iloc[i]),
         B          = float(BranchData["Full-Line B [pu]"].iloc[i]),
         Frombus    = Frombus,
         Tobus      = Tobus,
      )
      grid.line.append(line)

   return grid


#----------Running---------------
if __name__ == "__main__":
   grid = MakeGrid(df)

