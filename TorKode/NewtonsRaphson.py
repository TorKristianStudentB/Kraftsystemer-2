import numpy as np

def NewtonRaphson(grid): #Furuseth er ref

   def busclassifier_with_voltage_and_delta_vektor(grid):
      bus=[]
      for i in range(len(grid.bus)):
         PV=False
         if i==0:
            bus.append("ref")
         for j in range(len(grid.gen)):
            if grid.gen[j].bus==grid.bus[i].busNumber and i!=0:
               bus.append("PV")
               PV=True
         if PV==False:
            bus.append("PQ")
      return bus
         
   busPVPQ=busclassifier(grid)


   def powerflowequationP(V_i,V_j,Y,delta_i,delta_j,grid):
      V_i=np.abs(V_i)
      V_j=np.abs(V_i)
      Yij=np.abs(Y[i,j])
      delta_i=delta_i
      delta_j=delta_j
      theta_ij=np.angel(Y[i,j])
      return V_i*V_j*Yij*np.cos(delta_i-delta_j-theta_ij)

   
   def powerflowequationQ(V_i,V_j,Y,delta_i,delta_j,grid):
      V_i=np.abs(V_i)
      V_j=np.abs(V_i)
      Yij=np.abs(Y[i,j])
      delta_i=delta_i
      delta_j=delta_j
      theta_ij=np.angel(Y[i,j])
      return V_i*V_j*Yij*np.sin(delta_i-delta_j-theta_ij)

   def power_scheduled(busPVPQ,grid):
      P_scheduled=[]
      Q_scheduled=[]
      for i in range(len(grid.bus)):
         if busPVPQ[i]=="PV":
            P_mid=grid.bus[i].P_gen-grid.bus[i].P_load
            P_scheduled.append(P_mid)
         if busPVPQ[i]=="PQ":
            P_mid=grid.bus[i].P_gen-grid.bus[i].P_load
            P_scheduled.append(P_mid)
            Q_mid=grid.bus[i].Q_gen-grid.bus[i].Q_load
            Q_scheduled.append(Q_mid)
      return P_scheduled, Q_scheduled
   
   P_scheduled, Q_scheduled=power_scheduled(busPVPQ,grid)

   def totalsolver(grid,busPVPQ,P_scheduled, Q_scheduled):
      iterasjon=0
      deltaPQ=[]
      unkowns=[]

      N=len(grid.bus)
      rows=0
      for i in range(len(busPVPQ)):
         if busPVPQ[i]=="PV":
            rows=rows+1
         if busPVPQ[i]=="PQ":
            rows=rows+2

      
      
      def jacobian():  #er har jeg håndregnet ut generelle definisjoner på de deriverte, jobber er å få bygd opp matrisen på et hvilke som helst system.
         Y=grid.admittansmatrise()

          def dpi_ddeltai(i):      #i er da definert for hvilke pi/deltai vi jobber med
            a=0
            for j in range(len(grid.bus)-1):
               if j!=i:
                  a=a-np.abs(grid.bus[i].Volt)*np.abs(grid.bus[j].Volt)*np.abs(Y[i,j])*np.cos(grid.bus[i].Angle-grid.bus[i].Angle-np.angle(Y[i,j]))  
            return a

         





      def calculate_deltaunkown_one_iterasjon(grid,rows,N,deltaPQ,iterasjon):
         return 0


      def calculate_deltaPQ_one_iterasjon(grid,rows,N,deltaPQ,iterasjon):
         if iterasjon==0:
            for i in range(rows):
                        if busPVPQ[i]=="PV":
                           P_inwork=0
                           for i in range(N):
                              P_inwork=P_inwork+powerflowequationP(1,1,grid.admittansmatrise(),0,0,grid)
                           deltaPQ.append(P_inwork)
                        if busPVPQ[i]=="PQ":
                           P_inwork=0
                           Q_inwork=0
                           for i in range(N):
                              P_inwork=P_inwork+powerflowequationP(1,1,grid.admittansmatrise(),0,0,grid)
                              Q_inwork=Q_inwork+powerflowequationQ(1,1,grid.admittansmatrise(),0,0,grid)
                           deltaPQ.append(P_inwork)
                           deltaPQ.append(Q_inwork)
            else:



            return deltaPQ
                              


            
            
         for i in range(rows):
            if busPVPQ[i]=="PV":
               for i in range(N):
                  def powerflowequationP():





      

      







   
      



   


   return bus