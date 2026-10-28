from GridMaker.Imports import np,theveninZth, excelfilepath, FDLF,df,forenklet,metode


#----------Making grid class---------------
class Grid:

   #-----------------Her legges funksjonene inn, og husk å legge dem i imports-----------
   def thevenin(self,bus1,bus2):
         grid.loadflowsolutionNR()
         Zth=theveninZth(self,bus1,bus2)
         return f"Zth={Zth} og Vth={grid.bus[1].Volt-grid.bus[2].Volt}"
   
   def admittansmatrise(self):
      import copy
      from FunctionsInGridMaker.admittansmatrise import Krons_reduksjon,cutsem

      #-------teller hvor mange ganger funksjonen kalles på dette nettet-------
      self.antall_kall_admittansmatrise = getattr(self, "antall_kall_admittansmatrise", 0) + 1
      #-------teller hvor mange ganger funksjonen kalles på dette nettet-------

      #-------regner ut bare første gang, deretter brukes den lagrede verdien-------
      if getattr(self, "_admittans_lagret", None) is None:
         if forenklet:
            self._admittans_lagret = Krons_reduksjon(self)
         else:
            self._admittans_lagret = cutsem(self)
      #-------regner ut bare første gang, deretter brukes den lagrede verdien-------

      #-------gir ut kopier slik at kallerne ikke kan endre den lagrede verdien-------
      lagret = self._admittans_lagret
      if forenklet:
         Y, nett = lagret
         return Y.copy(), copy.deepcopy(nett)
      else:
         return lagret.copy()
      #-------gir ut kopier slik at kallerne ikke kan endre den lagrede verdien-------

   def loadflowsolutionNR(self):
         from FunctionsInGridMaker.NewtonsRaphson import NewtonRaphsonKrons,NewtonRaphson
         if forenklet:
            Y,grid=self.admittansmatrise()
            grid=NewtonRaphsonKrons(grid,Y)
            self.solution=grid.solution
         else:
             return NewtonRaphson(self)
   
   def DCPF(self):
      from FunctionsInGridMaker.DCPF import dc_power_flow
      return dc_power_flow(self)

   def FDLF(self):
      from FunctionsInGridMaker.FDLF import FDLF
      return FDLF(self)

   def validating_PP_DC(self):
       from Validating.validating_pandapower_DC import validating_PP_DC   # lat import: valideringsfilene importerer selv GridMaker
       return validating_PP_DC(self)

   def validating_PP_FDPF(self):
       from Validating.validating_pandapower_FDPF import validating_PP_FDPF   # lat import (se over)
       return validating_PP_FDPF(self)

   def validating_PP_NR(self):
          from Validating.validating_pandapower_NR_bussklassifisering import validating_PP_NR   # lat import (se over)
          return validating_PP_NR(self) 

   def N_minus_en(self, metode=metode):
       from FunctionsInGridMaker.N_minus_en import N_minus_en_kriteriet   # lat import (se over)
       return N_minus_en_kriteriet(df,metode)

   def sjekke__bus_over_P_gen_max(self):

      for bus in self.bus:
         P_max_sum = 0

         #---summerer alle maks effekt fra alle generatorene----
         for gen in self.gen:
               if gen.bus == bus.busNumber:
                  P_max_sum += gen.P_max

         if bus.P_gen > P_max_sum:
               return True

      return False
                                    
   def sjekke_over_Q_gen_max(self):
   
            for bus in self.bus:
               Q_max_sum = 0
   
               #---summerer alle maks effekt fra alle generatorene----
               for gen in self.gen:
                     if gen.bus == bus.busNumber:
                        Q_max_sum += gen.Q_max
   
               if bus.Q_gen > Q_max_sum:
                     return True
   
            return False

   def flow_in_trafo(self):
      flow=[]
      for t in range(len(self.trafo)):
            b0=self.trafo[t].Frombus
            b1=self.trafo[t].Tobus
            b0 = next(bus.kodens_identifikasjonssystem for bus in self.bus if bus.busNumber == b0)
            b1 = next(bus.kodens_identifikasjonssystem for bus in self.bus if bus.busNumber == b1)
            v0=np.abs(self.bus[b0].Volt)*np.exp(1j*self.bus[b0].Angle)
            v1=np.abs(self.bus[b1].Volt)*np.exp(1j*self.bus[b1].Angle)

            #----ratio er det fysiske forholdet, a=1 for nominell trafo, tappen ligger på høyspentsiden----
            v_lav=min(self.bus[b0].Vbase, self.bus[b1].Vbase)
            v_hoy=max(self.bus[b0].Vbase, self.bus[b1].Vbase)
            ratio_pu=self.trafo[t].ratio/(v_lav/v_hoy)
            a=1/ratio_pu
            y=self.trafo[t].admittans()

            if self.bus[b0].Vbase>=self.bus[b1].Vbase:   # Frombus er høyspentsiden (tappsiden)
               straum=(y/a**2)*v0 - (y/a)*v1
            else:                                        # Frombus er lavspentsiden
               straum=y*v0 - (y/a)*v1
            flow.append(v0*np.conj(straum))              # effektflyt inn i trafoen fra Frombus
      return np.array(flow)
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
      def __init__(self,volt, angle, flow_in_line, iterasjoner, mismatch, konvergerte, pv_to_pq_generators,power,qower,type,kjoretid):
        

         self.volt = volt
         self.angle = angle
         self.iterasjoner = iterasjoner
         self.mismatch = mismatch
         self.konvergerte = konvergerte
         self.flow_in_line = flow_in_line
         self.pv_to_pq_generators = pv_to_pq_generators
         self.power = power
         self.qower = qower
         self.type = type
         self.kjoretid = kjoretid
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

      def __init__(self, busNumber,name,Volt,Angle,P_gen,Q_gen,P_load,Q_load,bidz,Vbase,V_max,V_min,eic_code,kodens_identifikasjonssystem, cords, place,S_max,kunstig_buss,price):
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
        self.S_max = S_max
        self.kunstig_buss = kunstig_buss
        self.price = price


      def finne_bus_indeks(self, busNumber):
            for bus in self.bus:
               if bus.busNumber == busNumber:
                     return bus.kodens_identifikasjonssystem
            return None

#----------lines start----------------------
   class line:   
      lineNumber:int
      R:float
      X:float
      B:float
      Frombus:int
      Tobus:int
      lenght:float

      def __init__(self,Vbase,lineNumber,Name,R,X,B,Frombus,Tobus,lenght,eic_code,S_max,kunstig_line):
            self.Vbase = Vbase
            self.lineNumber = lineNumber
            self.Name = Name
            self.R = R
            self.X = X
            self.B = B
            self.Frombus = Frombus
            self.Tobus = Tobus
            self.lenght = lenght
            self.eic_code = eic_code
            self.S_max = S_max
            self.kunstig_line = kunstig_line

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

      def __init__(self,transformer_id,name, type, ratio, Frombus, Tobus, R, X, eic_code,S_max):
         self.transformer_id = transformer_id
         self.Name = name
         self.Type = type
         self.ratio = ratio
         self.Frombus = Frombus
         self.Tobus = Tobus
         self.R = R
         self.X = X
         self.eic_code = eic_code
         self.S_max = S_max

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

      def __init__(self, P_max,bus,name,Q_max,Q_min,eic_code, cost_per_MW):
         self.P_max    = P_max
         self.bus      = bus
         self.name     = name
         self.Q_max    = Q_max
         self.Q_min    = Q_min
         self.eic_code = eic_code
         self.cost_per_MW = cost_per_MW
#----------Making grid class---------------

