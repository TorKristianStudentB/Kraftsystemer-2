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
      self.bus = []       # list of bus objects
      self.line = []       # list of line objects


   def theveninZth(a,b):
      #lagre a og b som bus indeks som er funnet
      #finn alle linjene tilkoblet bus a og bus b
      #lagre andre siden av bussene i indeksen som er funnet
      #så indeksen er [a,b] hvor a er start og b er slutt
      #Så går vi kun ut av a(start), og looper gjennom endepunktene på andre siden av de  linjene som er koblet til a
      #Dette blir så [a,b,[a,[b,c]],[c,[d]],[d,[b]]]
      #Siden b er funnet i indeks 1, så er den grenen ferdig, så vi fortsetter nå kun fra c
      #c går til d, og d går til b, som da sier at den er ferdig.
      #Det lages så to lister, serier og parrareller, som er tomme foreløbig
      #Vi leser så fra denne [a,b,[a,[b,c]],[c,[d]],[d,[b]]]
      #serier [[a,b],[a,c,d,b]]
      #parrareller [[a,b],[a,c,d,b]]
      

      return Zth
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

