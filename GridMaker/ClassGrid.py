from GridMaker.Imports import theveninZth, cutsem, NewtonRaphson, dc_power_flow, FDLF


#----------Making grid class---------------
class Grid:

   #-----------------Her legges funksjonene inn, og husk å legge dem i imports-----------
   def thevenin(self,bus1,bus2):
         grid.loadflowsolutionNR()
         Zth=theveninZth(self,bus1,bus2)
         return f"Zth={Zth} og Vth={grid.bus[1].Volt-grid.bus[2].Volt}"
   
   def admittansmatrise(self):
         return cutsem(self)
   
   def loadflowsolutionNR(self):
         return NewtonRaphson(self)
   
   def DCPF(self):
       return dc_power_flow(self)

   def FDLF(self):
       return FDLF(self)
   #-----------------Her legges funksjonene inn, og husk å legge dem i imports-----------

   def __init__(self,Name):
      self.Name=Name
      self.Base = None     # BaseValues object
      self.bus = []        # list of bus objects
      self.line = []       # list of line objects
      self.trafo = []      # list of trafo objects
      self.gen = []        # list of generators objects
      self.solution = None # solution object etter lastflyt

#-----------De løste verdiene i nettet etter en lastflytanalyse-----------
   class Solution:
      def __init__(self, volt, angle, flow_in_line, iterasjoner, mismatch, konvergerte, pv_to_pq_generators,power,qower):
         self.volt = volt
         self.angle = angle
         self.iterasjoner = iterasjoner
         self.mismatch = mismatch
         self.konvergerte = konvergerte
         self.flow_in_line = flow_in_line
         self.pv_to_pq_generators = pv_to_pq_generators
         self.power = power
         self.qower = qower
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

      def __init__(self, busNumber,name,Volt,Angle,P_gen,Q_gen,P_load,Q_load,bidz,Vbase,V_max,V_min,eic_code,kodens_identifikasjonssystem, cords, place):
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
        self.cords = cords
        self.place = place


      def finne_bus_indeks(self, busNumber):
            for bus in self.bus:
               if bus.busNumber == busNumber:
                     return bus.kodens_identifikasjonssystem
            return None
                           


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
#----------Making grid class---------------

