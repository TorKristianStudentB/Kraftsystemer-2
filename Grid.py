import numpy as np

class Grid:

   class BaseValues:
   def _init_(self,Sbase,Vbase):
         self.base = Sbase
         self.Vbase = Vbase

   class Bus:
    def __init__(self, BusNumber,Name,Volt,Angle,P_gen,Q_gen,P_load,Q_load):
        self.name = BusNumber
        self.Name = Name
        self.Volt = Volt
        self.Angle = Angle
        self.P_gen = P_gen
        self.Q_gen = Q_gen
        self.P_load = P_load
        self.Q_load = Q_load

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
   

        
line1 = Line("test1",2,3,4,5,5,5)
print(line1.PrintLineNumber)

   
         