import numpy as np

def NewtonRaphson(grid): #Furuseth er ref

   #---------oppretter klasser PV og PQ for bussene--------------------
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
   #---------oppretter klasser PV og PQ for bussene--------------------
         
   busPVPQ=busclassifier(grid)

   #-----------lastflytligningen for aktiv effekt---------------------
   def powerflowequationP(V_i,V_j,Y,delta_i,delta_j,grid):
      V_i=np.abs(V_i)
      V_j=np.abs(V_i)
      Yij=np.abs(Y[i,j])
      delta_i=delta_i
      delta_j=delta_j
      theta_ij=np.angel(Y[i,j])
      return V_i*V_j*Yij*np.cos(delta_i-delta_j-theta_ij)
   #-----------lastflytligningen for aktiv effekt---------------------

   #-----------lastflytligningen for reaktiv effekt---------------------
   def powerflowequationQ(V_i,V_j,Y,delta_i,delta_j,grid):
      V_i=np.abs(V_i)
      V_j=np.abs(V_i)
      Yij=np.abs(Y[i,j])
      delta_i=delta_i
      delta_j=delta_j
      theta_ij=np.angel(Y[i,j])
      return V_i*V_j*Yij*np.sin(delta_i-delta_j-theta_ij)
   #-----------lastflytligningen for reaktiv effekt---------------------

   #-------------Løser P=Pgen-Pload og Q=Qgen-Qload for gridet------------------------
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
   #-------------Løser P=Pgen-Pload og Q=Qgen-Qload for gridet------------------------


   P_scheduled, Q_scheduled=power_scheduled(busPVPQ,grid)

   #-----------------Her er Newtons Raphson metoden, her er kjernen-------------------
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

      
      #---------------Lager jacobian matrisen----------------
      def jacobian():  #er har jeg håndregnet ut generelle definisjoner på de deriverte, jobber er å få bygd opp matrisen på et hvilke som helst system.
        
         J = np.zeros((rows, rows))
         Y=grid.admittansmatrise()
          
          #----------den paritell deriverte pi med hensyn på angle i-------------------
          def dpi_ddeltai(i):
            a=0
            for j in range(len(grid.bus)-1):
               if j!=i:
                  a=a-np.abs(grid.bus[i].Volt)*np.abs(grid.bus[j].Volt)*np.abs(Y[i,j])*np.sin(grid.bus[i].Angle-grid.bus[i].Angle-np.angle(Y[i,j]))  
            return a
         #----------den paritell deriverte pi med hensyn på angle i-------------------

         #----------den paritell deriverte pi med hensyn på angle j-------------------
         def dpi_ddeltaj(i,j):
            a = np.abs(grid.bus[i].Volt)*np.abs(grid.bus[j].Volt)*np.abs(Y[i,j])*np.sin(grid.bus[i].Angle-grid.bus[j].angle-np.angle(Y[i,j]))
            return a
         #----------den paritell deriverte pi med hensyn på angle j-------------------

         #----------den paritell deriverte pi med hensyn på volt i-------------------
         def dpi_dvi(i):
            a=0
            for j in range(len(grid.bus)-1):
               if j!=i:
                  a=a+np.abs(grid.bus[i].Volt)*np.abs(grid.bus[j].Volt)*np.abs(Y[i,j])*np.cos(grid.bus[i].Angle-grid.bus[i].Angle-np.angle(Y[i,j]))  
               if j==i:
                  a=a+2*np.abs(grid.bus[i].Volt)*np.abs(Y[i,j])*np.cos(grid.bus[i].Angle-grid.bus[j].angle-np.angle(Y[i,j]))
            return a
         #----------den paritell deriverte pi med hensyn på volt i-------------------
         

         #----------den paritell deriverte pi med hensyn på volt j-------------------
         def dpi_dvj(i):
            a = np.abs(grid.bus[i].Volt)*np.abs(Y[i,j])*np.cos(grid.bus[i].Angle-grid.bus[j].angle-np.angle(Y[i,j]))
            return a
         #----------den paritell deriverte pi med hensyn på volt j-------------------


         #----------den paritell deriverte qi med hensyn på angle i-------------------
          def dqi_ddeltai(i):
            a=0
            for j in range(len(grid.bus)-1):
               if j!=i:
                  a=a + np.abs(grid.bus[i].Volt)*np.abs(grid.bus[j].Volt)*np.abs(Y[i,j])*np.cos(grid.bus[i].Angle-grid.bus[i].Angle-np.angle(Y[i,j]))  
            return a
         #----------den paritell deriverte qi med hensyn på angle i-------------------

         #----------den paritell deriverte qi med hensyn på angle j-------------------
         def dqi_ddeltaj(i,j):
            a = -1 * np.abs(grid.bus[i].Volt)*np.abs(grid.bus[j].Volt)*np.abs(Y[i,j])*np.cos(grid.bus[i].Angle-grid.bus[j].angle-np.angle(Y[i,j]))
            return a
         #----------den paritell deriverte qi med hensyn på angle j-------------------

         #----------den paritell deriverte qi med hensyn på volt i-------------------
         def dqi_dvi(i):
            a=0
            for j in range(len(grid.bus)-1):
               if j!=i:
                  a=a+np.abs(grid.bus[i].Volt)*np.abs(grid.bus[j].Volt)*np.abs(Y[i,j])*np.sin(grid.bus[i].Angle-grid.bus[i].Angle-np.angle(Y[i,j]))  
               if j==i:
                  a=a+2*np.abs(grid.bus[i].Volt)*np.abs(Y[i,j])*np.sin(grid.bus[i].Angle-grid.bus[j].angle-np.angle(Y[i,j]))
            return a
         #----------den paritell deriverte qi med hensyn på volt i-------------------
         

         #----------den paritell deriverte qi med hensyn på volt j-------------------
         def dqi_dvj(i):
            a = np.abs(grid.bus[i].Volt)*np.abs(Y[i,j])*np.sin(grid.bus[i].Angle-grid.bus[j].angle-np.angle(Y[i,j]))
            return a
         #----------den paritell deriverte qi med hensyn på volt j-------------------


         #-----------------bygge jacobian matrisen utifra funksjonene over----------
         for i in range(rows):
            k=0#dummy variabel siden pq legger til 2 rader istedenfor 1 i pv
            for j in range(rows):
               if buPVPQ[i]=="PV"
                  if busPVPQ[j]=="PV":
                     if j==k:
                        J[k,j]=dpi_ddeltai(k):
                     else:
                        J[k,j]=dpi_ddeltaj(k,j)
                  k=k+1
                  else:
                     if j==k:
                        J[k,j]=dpi_ddeltai(i):
                        J[k+1,j]=dqi_ddeltai(i)
                     else:
                        J[k,j]=dpi_ddeltaj(i,j)
                        J[k+1,j]=dqi_ddeltaj(i,j)
                     k=k+2
               else:
                     if j==k:
                        J[k,j]=dpi_ddeltai(k):
                        J[k,j+1]=dpi_dvi
                     else:
                        J[k,j]=dpi_ddeltaj(k,j)
                        J[k,j+1]=dpi_dvj(k,j)
                  k=k+1
                  else:
                     if j==k:
                        J[k,j]=dpi_ddeltai(i):
                        J[k,j+1]=dpi_dvi(i)
                        J[k+1,j]=dqi_ddeltai(i)
                        J[k+1,j+1]=dqi_dvi(i)
                     else:
                        J[k,j]=dpi_ddeltaj(i,j)
                        J[k,j]=dqi_ddeltaj(i,j)
                     k=k+2
               else:

          #-----------------bygge jacobian matrisen utifra funksjonene over----------


                  
      return J




      #---------------Lager jacobian matrisen----------------


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



   return solution
    #-----------------Her er Newtons Raphson metoden, her er kjernen-------------------