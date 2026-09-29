import os
from pathlib import Path
import pandas as pd
import random
import sys
import numpy as np



#--------------------Hente filstien til megselv, må øke til mer--------
current_path = os.getcwd()
current_path=Path(current_path)
KodePath=current_path.parent 
KodePath=KodePath / "Grid"
sys.path.append(str(KodePath))
#--------------------Hente filstien til megselv, må øke til mer--------

#--------funksjonshenting---------
from theveninZth import theveninZth
from admittansmatrise import cutsem
from NewtonsRaphson2 import NewtonRaphson
#--------funksjonshenting---------

#----------------Fetching the lates grid xlsx file start-----------------------
FolderName = "Server_host"
FileName = "MainGrid.xlsx"

def read_xlsx(FolderName, FileName):
    folder = Path(FolderName)
    files = list(folder.rglob(FileName))
    if not files:
        raise FileNotFoundError(f"Could not find '{FileName}' in '{FolderName}'")
    file = files[0]
    print(f"Reading: {file}")

    return pd.read_excel(file, sheet_name=None)
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
      self.solution = None # solution object etter lastflyt





   def thevenin(self,bus1,bus2):
      return theveninZth(self,bus1,bus2)

   def admittansmatrise(self):
      return cutsem(self)

   def loadflowsolutionNR(self):
      return NewtonRaphson(self)

#-----------De løste verdiene i nettet etter en lastflytanalyse-----------
   class Solution:
      def __init__(self, volt, angle, flow_in_line, iterasjoner, mismatch, konvergerte):
         self.volt = volt
         self.angle = angle
         self.iterasjoner = iterasjoner
         self.mismatch = mismatch
         self.konvergerte = konvergerte
         self.flow_in_line = flow_in_line
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

      def __init__(self, busNumber,name,Volt,Angle,P_gen,Q_gen,P_load,Q_load,bidz,Vbase,V_max,V_min,eic_code,kodens_identifikasjonssystem):
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
        self.V_max = V_max
        self.V_min = V_min
        self.eic_code = eic_code
        self.kodens_identifikasjonssystem = kodens_identifikasjonssystem


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

      def __init__(self,lineNumber,Name,R,X,B,Frombus,Tobus,lenght,eic_code):
            self.lineNumber = lineNumber
            self.Name = Name
            self.R = R
            self.X = X
            self.B = B
            self.Frombus = Frombus
            self.Tobus = Tobus
            self.lenght = lenght
            self.eic_code = eic_code


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

      def __init__(self, name, type, ratio, Frombus, Tobus, R, X, eic_code):
         self.Name = name
         self.Type = type
         self.ratio = ratio
         self.Frombus = Frombus
         self.Tobus = Tobus
         self.R = R
         self.X = X
         self.eic_code = eic_code

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

      def __init__(self, P_max,bus,name,Q_max,Q_min,eic_code):
         self.P_max    = P_max
         self.bus      = bus
         self.name     = name
         self.Q_max    = Q_max
         self.Q_min    = Q_min
         self.eic_code = eic_code
#----------Making a grid from xslx end----


#---------Start: Funskjon som fyller inn i objektet grid fra excel arket n490--------
def MakeGrid(df):


   #---------Leser excel arket og bruker pandas DF-------
   def lese_excel_arket():
      grid = Grid("Grid")
      busDF   = df["bus"]
      lineDF  = df["line"]
      trafoDF = df["trafo"]
      genDF   = df["gen"]
      linkDF  = df["link"] if "link" in df else None   # lenke-fanen er valgfri
      return grid, busDF, lineDF, trafoDF, genDF, linkDF
   grid, busDF, lineDF, trafoDF, genDF, linkDF = lese_excel_arket()
   #---------Leser excel arket og bruker pandas DF-------


   #----------Sjekker linkene og setter effekten på P-load =P_load-Pinj, trenger derfor ikke lenkene i nettmodellen-------
   def link():
      if linkDF is not None:
         if linkDF is None or "Pinj" not in linkDF.columns:   # ingen lenker aa injisere
            return
         Nordics=["NO1","NO2","NO3","NO4","NO5","SE1","SE2","SE3","SE4","FI","DK2"]
         for i in range(len(linkDF)):
            if linkDF["area0"].iloc[i] in Nordics and linkDF["area1"].iloc[i] in Nordics:
               bus0=linkDF["bus0"].iloc[i]
               bus1=linkDF["bus1"].iloc[i]
               Pinj=linkDF["Pinj"].iloc[i]
               busDF["P_load"].iloc[bus0]=busDF["P_load"].iloc[bus0] - Pinj
               busDF["P_load"].iloc[bus1]=busDF["P_load"].iloc[bus1] + Pinj
            else:
                  if linkDF["area0"].iloc[i] in Nordics:
                     bus0=linkDF["bus0"].iloc[i]
                     Pinj=linkDF["Pinj"].iloc[i]
                     busDF["P_load"].iloc[bus0]=busDF["P_load"].iloc[bus0] - Pinj
                  else:
                     bus1=linkDF["bus1"].iloc[i]
                     Pinj=linkDF["Pinj"].iloc[i]
                     busDF["P_load"].iloc[bus1]=busDF["P_load"].iloc[bus1] - Pinj
   link()
   #----------Sjekker linkene og setter effekten på P-load =P_load-Pinj, trenger derfor ikke lenkene i nettmodellen-------
       

   #----------Sjekker om det er Q og V begrensinger i excelarket-------------
   def betingelser_for_Q_og_V():
      Q_max=False
      Q_min=False
      V_min=False
      V_max=False

      if "Qmax" in genDF.columns:
         Q_max=True
      if "Qmin" in genDF.columns:
               Q_min=True
      if "Vmax" in busDF.columns:
               V_max=True
      if "Vmin" in busDF.columns:
               V_min=True
      return Q_max,Q_min,V_max,V_min
   Q_max,Q_min,V_max,V_min=betingelser_for_Q_og_V()
   #----------Sjekker om det er Q og V begrensinger i excelarket-------------


   #--------------Sjekker om excelarket har eic koder-----------------------
   def eickode():
       eic_code_bus=False
       eic_code_line=False
       eic_code_trafo=False
       eic_code_gen=False

       if "eic code" in busDF.columns:
           eic_code_bus = True
       if "eic code" in lineDF.columns:
            eic_code_line = True
       if "eic code" in trafoDF.columns:
            eic_code_trafo = True
       if "eic code" in genDF.columns:
            eic_code_gen = True
       return eic_code_bus,eic_code_line,eic_code_trafo,eic_code_gen
   eic_code_bus,eic_code_line,eic_code_trafo,eic_code_gen = eickode()
   #--------------Sjekker om excelarket har eic koder-----------------------


   #-------------for å konvertere R og X til PU verdier før det lastes til nettet---------
   def konverter_til_PU():
        Sbase = busDF["S_base [MVA] "].iloc[0]    # fordi MVA
        Zbase = lineDF["Vbase"]**2 / Sbase        # per linje (Series)
        lineDF["R"] = lineDF["R"] / Zbase
        lineDF["X"] = lineDF["X"] / Zbase
        busDF["P_gen"] = busDF["P_gen"] / Sbase
        busDF["Q_gen"] = busDF["Q_gen"] / Sbase
        busDF["P_load"] = busDF["P_load"] / Sbase
        busDF["Q_load"] = busDF["Q_load"] / Sbase

        if Q_max==True:
            genDF["Qmax"] = genDF["Qmax"] / Sbase
        if Q_min==True:
            genDF["Qmin"] = genDF["Qmin"] / Sbase
   konverter_til_PU()
   #-------------for å konvertere R og X til PU verdier før det lastes til nettet---------


   #---------Finner busser som står alene-----------------------
   def finn_elementer_alene():

      busser_i_line = set(lineDF["bus0"]).union(set(lineDF["bus1"]))
      busser_i_trafo = set(trafoDF["bus0"]).union(set(trafoDF["bus1"]))
      busser_alene = []
      for bus in busDF["bus_id"]:
         if bus not in busser_i_line and bus not in busser_i_trafo:
            busser_alene.append(int(bus))
      return busser_alene
   busser_alene = finn_elementer_alene()
   #---------Finner busser som står alene-----------------------



   #---------Sette verdier inn i grid objektet over-------------
   def Legge_verdier_i_objektet():
         
   
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
               V_max = float(busDF["Vmax"].iloc[i]) if V_max else None,
               V_min = float(busDF["Vmin"].iloc[i]) if V_min else None,
               eic_code = str(busDF["eic code"].iloc[i]) if eic_code_bus else None,
               kodens_identifikasjonssystem = i,
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
               eic_code = str(lineDF["eic code"].iloc[i]) if eic_code_line else None,
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
               eic_code = str(trafoDF["eic code"].iloc[i]) if eic_code_trafo else None,
            )
            grid.trafo.append(tr)
         #--------------oppretter Trafoer fra excel arket----------


         #--------------oppretter generator data fra excel arket---
         for i in range(len(genDF)):
               b = Grid.gen(
                  P_max     = int(genDF["Pmax"].iloc[i]),
                  name      = str(genDF["name"].iloc[i]),
                  bus       = float(genDF["bus"].iloc[i]),
                  Q_max = float(genDF["Qmax"].iloc[i]) if Q_max else None,
                  Q_min = float(genDF["Qmin"].iloc[i]) if Q_min else None,
                  eic_code = str(genDF["eic code"].iloc[i]) if eic_code_gen else None,
               )
               grid.gen.append(b)
         #--------------oppretter generator data fra excel arket---
   Legge_verdier_i_objektet()
   #---------Sette verdier inn i grid objektet over-------------

         
   return grid
#---------END: Funskjon som fyller inn i objektet grid fra excel arket n490--------


#----------Running---------------
if __name__ == "__main__":
   df = pd.read_excel(r"C:\Users\Eier\OneDrive\Master\Kraftsystemer\Kraftsystemer-2\Grid\test_trøndelagsnettet.xlsx", sheet_name=None)
   grid = MakeGrid(df)
