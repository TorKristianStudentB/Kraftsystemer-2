import numpy as np

#----------------------------Her er Newtons Raphson metoden--------------------------------------------------
def NewtonRaphson(grid): #Furuseth=busindeks=0 er ref, i andre nett er bus med busindeks=0 ref
   Y=grid.admittansmatrise() #la den her for at ting går fortere

   #---------oppretter klasser PV og PQ for bussene--------------------
   def busclassifier():
      bus=[]
      for i in range(len(grid.bus)):
        if i == 0:
            bus.append("ref")
            continue
        PV=False
        for j in range(len(grid.gen)):
            if grid.gen[j].bus == grid.bus[i].busNumber:
                PV=True
                break
        if PV:
            bus.append("PV")
        else:
            bus.append("PQ")
      return bus
   #---------oppretter klasser PV og PQ for bussene--------------------
   busPVPQ=busclassifier()


   #-----------Finner dimenjsonen på ax=b systemet som løses med NR---
   def dimensjon_of_system():
      pos = []
      size = 0
      for i in range(len(grid.bus)):
         if busPVPQ[i] == "PV":
               pos.append(size); size += 1
         elif busPVPQ[i] == "PQ":
               pos.append(size); size += 2
         else:
               pos.append(None)   # slack / referansebus
      return size, pos
   #-----------Finner dimenjsonen på ax=b systemet som løses med NR--- 
   size,pos=dimensjon_of_system()


   #-----------lastflytligningen for aktiv effekt---------------------
   def powerflowequationP(i,j):

      V_i=np.abs(grid.bus[i].Volt)
      V_j=np.abs(grid.bus[j].Volt)
      Yij=np.abs(Y[i,j])
      delta_i=grid.bus[i].Angle
      delta_j=grid.bus[j].Angle
      theta_ij=np.angle(Y[i,j])
      return V_i*V_j*Yij*np.cos(delta_i-delta_j-theta_ij)
   #-----------lastflytligningen for aktiv effekt---------------------


   #-----------lastflytligningen for reaktiv effekt---------------------
   def powerflowequationQ(i,j):
      V_i=np.abs(grid.bus[i].Volt)
      V_j=np.abs(grid.bus[j].Volt)
      Yij=np.abs(Y[i,j])
      delta_i=grid.bus[i].Angle
      delta_j=grid.bus[j].Angle
      theta_ij=np.angle(Y[i,j])
      return V_i*V_j*Yij*np.sin(delta_i-delta_j-theta_ij)
   #-----------lastflytligningen for reaktiv effekt---------------------


   #-------------Løser P=Pgen-Pload og Q=Qgen-Qload for gridet------------------------
   def power_scheduled(busPVPQ):
      P_scheduled=[]
      Q_scheduled=[]
      
      for i in range(len(grid.bus)):
            
            P_mid=grid.bus[i].P_gen-grid.bus[i].P_load
            P_scheduled.append(P_mid)
            Q_mid=grid.bus[i].Q_gen-grid.bus[i].Q_load
            Q_scheduled.append(Q_mid)

      return np.array(P_scheduled), np.array(Q_scheduled)
   #-------------Løser P=Pgen-Pload og Q=Qgen-Qload for gridet------------------------
   P_scheduled, Q_scheduled=power_scheduled(busPVPQ)  

   
   #---------------Lager jacobian matrisen, bruker busclassifier til å strukturere den----------------
   def jacobian():
    Y = grid.admittansmatrise()
    n = len(grid.bus)

    #----------pi derivert mhp. angle i-------------------
    def dpi_ddeltai(i):
        a = 0
        for j in range(n):
            if j != i:
                a = a - np.abs(grid.bus[i].Volt)*np.abs(grid.bus[j].Volt)*np.abs(Y[i,j])*np.sin(grid.bus[i].Angle-grid.bus[j].Angle-np.angle(Y[i,j]))
        return a

    #----------pi derivert mhp. angle j-------------------
    def dpi_ddeltaj(i, j):
        a = np.abs(grid.bus[i].Volt)*np.abs(grid.bus[j].Volt)*np.abs(Y[i,j])*np.sin(grid.bus[i].Angle-grid.bus[j].Angle-np.angle(Y[i,j]))
        return a

    #----------pi derivert mhp. volt i-------------------
    def dpi_dvi(i):
        a = 0
        for j in range(n):
            if j != i:
                a = a + np.abs(grid.bus[j].Volt)*np.abs(Y[i,j])*np.cos(grid.bus[i].Angle-grid.bus[j].Angle-np.angle(Y[i,j]))
            if j == i:
                a = a + 2*np.abs(grid.bus[i].Volt)*np.abs(Y[i,j])*np.cos(grid.bus[i].Angle-grid.bus[j].Angle-np.angle(Y[i,j]))
        return a

    #----------pi derivert mhp. volt j-------------------
    def dpi_dvj(i, j):
        a = np.abs(grid.bus[i].Volt)*np.abs(Y[i,j])*np.cos(grid.bus[i].Angle-grid.bus[j].Angle-np.angle(Y[i,j]))
        return a

    #----------qi derivert mhp. angle i-------------------
    def dqi_ddeltai(i):
        a = 0
        for j in range(n):
            if j != i:
                a = a + np.abs(grid.bus[i].Volt)*np.abs(grid.bus[j].Volt)*np.abs(Y[i,j])*np.cos(grid.bus[i].Angle-grid.bus[j].Angle-np.angle(Y[i,j]))
        return a

    #----------qi derivert mhp. angle j-------------------
    def dqi_ddeltaj(i, j):
        a = -1 * np.abs(grid.bus[i].Volt)*np.abs(grid.bus[j].Volt)*np.abs(Y[i,j])*np.cos(grid.bus[i].Angle-grid.bus[j].Angle-np.angle(Y[i,j]))
        return a

    #----------qi derivert mhp. volt i-------------------
    def dqi_dvi(i):
        a = 0
        for j in range(n):
            if j != i:
                a = a + np.abs(grid.bus[j].Volt)*np.abs(Y[i,j])*np.sin(grid.bus[i].Angle-grid.bus[j].Angle-np.angle(Y[i,j]))
            if j == i:
                a = a + 2*np.abs(grid.bus[i].Volt)*np.abs(Y[i,j])*np.sin(grid.bus[i].Angle-grid.bus[j].Angle-np.angle(Y[i,j]))
        return a

    #----------qi derivert mhp. volt j-------------------
    def dqi_dvj(i, j):
        a = np.abs(grid.bus[i].Volt)*np.abs(Y[i,j])*np.sin(grid.bus[i].Angle-grid.bus[j].Angle-np.angle(Y[i,j]))
        return a

    #-----------------bygge jacobian matrisen utifra funksjonene over----------
    # posisjon (rad/kolonne) for hver bus: PV -> 1 plass, PQ -> 2 plasser, slack -> ingen
    
    size, pos = dimensjon_of_system()

    J = np.zeros((size, size))

    for i in range(n):
        if pos[i] is None:
            continue
        ri = pos[i]
        for j in range(n):
            if pos[j] is None:
                continue
            cj = pos[j]
            if i == j:
                J[ri, cj] = dpi_ddeltai(i)
                if busPVPQ[i] == "PQ":
                    J[ri,   cj+1] = dpi_dvi(i)
                    J[ri+1, cj]   = dqi_ddeltai(i)
                    J[ri+1, cj+1] = dqi_dvi(i)
            else:
                J[ri, cj] = dpi_ddeltaj(i, j)
                if busPVPQ[i] == "PQ":
                    J[ri+1, cj]   = dqi_ddeltaj(i, j)
                if busPVPQ[j] == "PQ":
                    J[ri,   cj+1] = dpi_dvj(i, j)
                if busPVPQ[i] == "PQ" and busPVPQ[j] == "PQ":
                    J[ri+1, cj+1] = dqi_dvj(i, j)

    return J
   #---------------Lager jacobian matrisen, bruker busclassifier til å strukturere den----------------


   #----------------Bygger dP og Dq vektoren, også b vektoren i Ax=b---------------
   def calculate_deltaPQ(busPVPQ,P_scheduled, Q_scheduled):
         deltaPQ=[]

         #---------------løser de store utrykkkene for P og Q-----------------
         N=len(grid.bus)
         for i in range(len(grid.bus)):
            if busPVPQ[i]=="PV":
               P_inwork=0
               for j in range(N):
                  P_inwork=P_inwork+powerflowequationP(i,j)
               deltaPQ.append(P_scheduled[i]-P_inwork)
            elif busPVPQ[i]=="PQ":
               P_inwork=0
               Q_inwork=0
               for j in range(N):
                  P_inwork=P_inwork+powerflowequationP(i,j)
                  Q_inwork=Q_inwork+powerflowequationQ(i,j)
               deltaPQ.append(P_scheduled[i]-P_inwork)
               deltaPQ.append(Q_scheduled[i]-Q_inwork)
         #---------------løser de store utrykkkene for P og Q-----------------

         deltaPQ = np.array(deltaPQ)
         
         return deltaPQ
   #----------------Bygger dP og Dq vektoren, også b vektoren i Ax=b---------------   


   #------------Løser systemet med NR----------------------------------------------
   def finalsolver(busPVPQ,P_scheduled, Q_scheduled):
      i=0
      ferdig=False
      solution=False

      J=jacobian()

      print("busPVPQ:", busPVPQ)
      print("J:")
      print(J)
      print("shape:", J.shape)
      print("rank:", np.linalg.matrix_rank(J))
      print("det:", np.linalg.det(J))
      print("deltaPQ:", deltaPQ)

      while ferdig!=True:          
         deltaPQ=calculate_deltaPQ(busPVPQ,P_scheduled, Q_scheduled)
         deltax=np.linalg.solve(J,deltaPQ)
         k=0
         for j in range(len(grid.bus)):
            if busPVPQ[j]=="PV":
               grid.bus[j].Angle=grid.bus[j].Angle+deltax[k]
               k=k+1
            elif busPVPQ[j]=="PQ":
               grid.bus[j].Angle=grid.bus[j].Angle+deltax[k]
               grid.bus[j].Volt=grid.bus[j].Volt+deltax[k+1]
               k=k+2

         error = np.max(np.abs(deltaPQ))
         if error <= 1e-6:
             solution=True
             ferdig=True

         if i >= 50000:
             ferdig=True
             solution=False
         i=i+1 

      return solution,i, deltaPQ
   #------------Løser systemet med NR----------------------------------------------
   Konvergerte , iterasjon , deltaPQ=finalsolver(busPVPQ,P_scheduled, Q_scheduled)


   #---------------Loader løsningen som et eget object under hovednettet-----------
   grid.solution = Grid.Solution(
        volt        = [b.Volt for b in grid.bus],
        angle       = [b.Angle for b in grid.bus],
        iterasjoner = iterasjon,
        mismatch    = deltaPQ,
        konvergerte = Konvergerte,
    )
   #---------------Loader løsningen som et eget object under hovednettet-----------


   return grid
   
#----------------------------Her er Newtons Raphson metoden--------------------------------------------------