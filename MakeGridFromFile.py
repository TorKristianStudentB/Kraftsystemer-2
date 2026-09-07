from pathlib import Path
import pandas as pd

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
print(df)

#----------------Fetching the lates grid xlsx file end-----------------------





#----------Making a grid from xslx start----
class Grid:

#----------Base values start----------------
   class BaseValues:
      def __init__(self,Sbase,Vbase):
         self.base = Sbase
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

      def get_impedance(self):
         return self.R+self.X*1j
      
      def PrintLineNumber(self):
         return self.LineNumber
   
#----------Lines end----------------------
#----------Making a grid from xslx end----


      

   
         