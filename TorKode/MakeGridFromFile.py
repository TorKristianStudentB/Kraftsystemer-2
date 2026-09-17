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
from NewtonsRaphson import NewtonRaphson
#--------funksjonshenting---------




#----------------Fetching the lates grid xlsx file start-----------------------
FolderName = "Grid"
FileName = "GridVersjon1.xlsx"

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
      self.Base = None     # BaseValues object
      self.bus = []        # list of bus objects
      self.line = []       # list of line objects
      self.trafo = []      # list of trafo objects
      self.gen = []        # list of generators objects
      self.solution = []        # Konvergerte verdier i nettet


   def thevenin(self,bus1,bus2):
      return theveninZth(self,bus1,bus2)

   def admittansmatrise(self):
      return cutsem(self)
   
   def loadflowsolutionNR(self):
      return NewtonRaphson(self)
   

#-----------De løste verdiene i nettet etter en lastflytanalyse-----------
   class solution:   
      def __init__(self, volt, angle, iterasjoner, mismatch, konvergerte):
         self.volt = volt               
         self.angle = angle                
         self.iterasjoner = iterasjoner    
         self.mismatch = mismatch          
         self.konvergerte = konvergerte  
#-----------De løste verdiene i nettet etter en lastflytanalyse-----------


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
      Bidz : str
      Vbase : float 

      def __init__(self, busNumber,name,Volt,Angle,P_gen,Q_gen,P_load,Q_load,bidz,Vbase):
        self.busNumber = busNumber
        self.Name = name
        self.Volt = Volt
        self.Angle = Angle
        self.P_gen = P_gen
        self.Q_gen = Q_gen
        self.P_load = P_load
        self.Q_load = Q_load
        self.bidz = bidz
        self.Vbase = Vbase

      def type(self):

         
         return 

#----------bus end------------------------


#----------lines start----------------------
   class line:   
      lineNumber:int
      R:float
      X:float
      B:float
      Frombus:int
      Tobus:int
      lenght:float

      def __init__(self,lineNumber,Name,R,X,B,Frombus,Tobus,lenght):
            self.lineNumber = lineNumber
            self.Name = Name
            self.R = R
            self.X = X
            self.B = B
            self.Frombus = Frombus
            self.Tobus = Tobus
            self.lenght = lenght


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

      def __init__(self, name, type, ratio, Frombus, Tobus, R, X):
         self.Name = name
         self.Type = type
         self.ratio = ratio
         self.Frombus = Frombus
         self.Tobus = Tobus
         self.R = R
         self.X = X

      def admittans(self):
            return 1/complex(self.R, self.X)



#----------Trafo end------------------------

#----------Gen Start-----------------------
   class gen:
      name: str
      P_max: float
      type: float
      Q_max:float
      Q_min:float

      def __init__(self, P_max,bus,name,Q_max,Q_min):
         self.P_max    = P_max
         self.bus      = bus
         self.name     = name
         self.Q_max    = Q_max
         self.Q_min    = Q_min
#----------Making a grid from xslx end----



#---------Start: Funskjon som fyller inn i objektet grid fra excel arket n490--------
def MakeGrid(df):

   #---------Oppretter objektet grid og leser excel arket-------
   grid = Grid("Grid")
   busDF   = df["bus"]
   lineDF  = df["line"]
   trafoDF = df["trafo"]
   genDF   = df["gen"]
   #---------Oppretter objektet grid og leser excel arket-------

   #---------------Leser globale verdier base-----------
   Sbase = float(busDF["S_base [MVA] "].iloc[0])
   Vbase = float(busDF["Vbase"].iloc[0])
   grid.Base = Grid.BaseValues(Sbase, Vbase)
   #---------------Leser globale verdier base-----------

   #--------------oppretter bus fra excel arket----------
   for i in range(len(busDF)):
      b = Grid.bus(
         busNumber = int(busDF["bus_id"].iloc[i]),
         name      = str(busDF["name"].iloc[i]),
         Volt      = float(busDF["V [P.U]"].iloc[i]),
         Angle     = float(busDF["Angle [rad]"].iloc[i]),
         P_gen     = float(busDF["P_gen"].iloc[i]),
         Q_gen     = float(busDF["Q_gen"].iloc[i]),
         P_load    = float(busDF["P_load"].iloc[i]),
         Q_load    = float(busDF["Q_load"].iloc[i]),
         bidz      = str(busDF["bidz"].iloc[i]),
         Vbase     = float(busDF["Vbase"].iloc[i]),
      )
      grid.bus.append(b)

   #--------------oppretter bus fra excel arket----------

   
   #--------------oppretter linjer fra excel arket----------
   for i in range(len(lineDF)):

      b = Grid.line(
         lineNumber = int(lineDF["line_id"].iloc[i]),
         Name       = str(lineDF["name"].iloc[i]),
         R          = float(lineDF["R"].iloc[i]),
         X          = float(lineDF["X"].iloc[i]),
         B          = float(lineDF["B"].iloc[i]),
         Frombus    = int(lineDF["bus0"].iloc[i]),
         Tobus      = int(lineDF["bus1"].iloc[i]),
         lenght     = float(lineDF["length"].iloc[i]),
      )
      grid.line.append(b)
   #--------------oppretter linjer fra excel arket----------

   #--------------oppretter Trafoer fra excel arket----------
   for i in range(len(trafoDF)):
      tr = Grid.trafo(
         name    = str(trafoDF["name"].iloc[i]),
         type    = "tap",
         ratio   = float(trafoDF["ratio"].iloc[i]),
         Frombus = int(trafoDF["bus0"].iloc[i]),
         Tobus   = int(trafoDF["bus1"].iloc[i]),
         R       = float(trafoDF["R"].iloc[i]),
         X       = float(trafoDF["X"].iloc[i]),
      )
      grid.trafo.append(tr)
   #--------------oppretter Trafoer fra excel arket----------


   #--------------oppretter generator data fra excel arket---
   for i in range(len(genDF)):
         b = Grid.gen(
            P_max     = int(genDF["Pmax"].iloc[i]),
            name      = str(genDF["name"].iloc[i]),
            bus       = float(genDF["bus"].iloc[i]),
            Q_max     = float(genDF["Qmax(test)"].iloc[i]),#Få tak i PQ diagrammet
            Q_min     = float(genDF["Qmin(test)"].iloc[i]),#Få tak i PQ diagrammet
         )
         grid.gen.append(b)
   #--------------oppretter generator data fra excel arket---

   return grid

#---------END: Funskjon som fyller inn i objektet grid fra excel arket n490--------


#----------Running---------------
if __name__ == "__main__":
   grid = MakeGrid(df)
   