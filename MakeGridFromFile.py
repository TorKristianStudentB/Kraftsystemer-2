from pathlib import Path
import pandas as pd
import random

FolderName="Grid"

#----------------Fetching the lates grid xlsx file start-----------------------
def read_latest_xlsx(FolderName):
    folder = Path(FolderName)
    # Find all xlsx files in the folder and subfolders
    files = list(folder.rglob("*.xlsx"))
    if not files:
        raise FileNotFoundError(f"No .xlsx files found in '{FolderName}'")
    # Find the newest file
    latest_file = max(files, key=lambda f: f.stat().st_mtime)
    print(f"Reading: {latest_file}")
    return pd.read_excel(latest_file,sheet_name=None)

df = read_latest_xlsx(FolderName)

#----------------Fetching the lates grid xlsx file end-----------------------


#----------Making a grid from xslx start----
class Grid:

   def __init__(self,Name):
      self.Name=Name
      self.Base = None      # BaseValues object
      self.Buses = []       # list of Bus objects
      self.Lines = []       # list of Line objects

#----------Base values start----------------
   class BaseValues:
      def __init__(self,Sbase,Vbase):
         self.Sbase = Sbase
         self.Vbase = Vbase

#----------Base values end------------------


#----------Bus start------------------------
   class Bus:
      BusNumber:int
      Volt:float
      Angle:float
      P_gen:float
      Q_gen:float
      P_load:float
      Q_load:float
      def __init__(self, BusNumber,Name,Volt,Angle,P_gen,Q_gen,P_load,Q_load):
        self.name = BusNumber
        self.Name = Name
        self.Volt = Volt
        self.Angle = Angle
        self.P_gen = P_gen
        self.Q_gen = Q_gen
        self.P_load = P_load
        self.Q_load = Q_load

      
#----------Bus end------------------------





#----------Lines start----------------------
   class Line:   
      LineNumber:int
      R:float
      X:float
      B:float
      FromBus:int
      ToBus:int

      def __init__(self,LineNumber,Name,R,X,B,FromBus,ToBus):
            self.LineNumber = LineNumber
            self.Name = Name
            self.R = R
            self.X = X
            self.B = B
            self.FromBus = FromBus
            self.ToBus = ToBus
   
#----------Lines end----------------------
#----------Making a grid from xslx end----




def MakeGrid(df):
   grid = Grid("Grid")

   BusData = df["BusData"]
   BranchData = df["BranchData"]

   #reading the base values (stored in the first row of BusData)
   Sbase = BusData["S_base [MVA] "].iloc[0]
   Vbase = BusData["V_base"].iloc[0]
   grid.Base = Grid.BaseValues(Sbase, Vbase)

   #reading the busses and implementing it in the grid
   for i in range(len(BusData)):
      BusNumber = int(BusData["Bus Num"].iloc[i])
      bus = Grid.Bus(
         BusNumber = BusNumber,
         Name      = f"Bus {BusNumber}",
         Volt      = float(BusData["V [V]"].iloc[i]),
         Angle     = float(BusData["Angle [rad]"].iloc[i]),
         P_gen     = float(BusData["P_gen"].iloc[i]),
         Q_gen     = float(BusData["Q_gen"].iloc[i]),
         P_load    = float(BusData["P_load"].iloc[i]),
         Q_load    = float(BusData["Q_load"].iloc[i]),
      )
      grid.Buses.append(bus)

   #reading the lines/branches and implementing it in the grid
   for i in range(len(BranchData)):
      FromBus = int(BranchData["From Line"].iloc[i])
      ToBus   = int(BranchData["To Line"].iloc[i])
      line = Grid.Line(
         LineNumber = i + 1,
         Name       = f"Line {FromBus}-{ToBus}",
         R          = float(BranchData["R [pu]"].iloc[i]),
         X          = float(BranchData["X [pu]"].iloc[i]),
         B          = float(BranchData["Full-Line B [pu]"].iloc[i]),
         FromBus    = FromBus,
         ToBus      = ToBus,
      )
      grid.Lines.append(line)

   return grid


#----------Running---------------
if __name__ == "__main__":
   grid = MakeGrid(df)

