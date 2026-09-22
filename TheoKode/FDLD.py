import numpy as np


# [ΔP] = [ H  N ] [Δδ] (NR)
# [ΔQ] = [ M  L ] [ΔV] (NR)
# -->
# ΔP = H · Δδ (FD)
# ΔQ = L · ΔV (FD)

# P_ij = (V_i · V_j / X) · sin(δ_i − δ_j)
# -> d(P_ij)/d(δi) = (V_i · V_j / X)*cos(δ_i − δ_j)
# V_i = V_j = 1, cos(δ_i − δ_j) (approx=) 1
# -> d(P_ij)/d(δi) = ((V_i)^2)/X = 1/X
# -> d(P_ij)/d(δj) = -((V_j)^2)/X = -1/X


#B′_ii = Σ_j 1/X_ij      (summen over alle linjer koblet til buss i)
#B′_ij = −1/X_ij         (hvis i og j har en linje mellom seg)
#B′_ij = 0               (hvis de ikke er koblet direkte)


B_merke = np.array([[14, -4], [-4, 9]])
dP = np.array([0.24,0.01])

d_delta = np.linalg.solve(B_merke,dP)

print(d_delta)


#---------oppretter klasser PV og PQ for bussene--------------------
#    def busclassifier():
#       bus=[]
#       for i in range(len(grid.bus)):
#         if i == 0:
#             bus.append("ref")
#             continue
#         if np.all(np.isclose(Y[i,:], 0)):   #bussen henger ikke sammen med noe -> hopp over den
#             bus.append("alene")
#             continue
#         PV=False
#         for j in range(len(grid.gen)):
#             if grid.gen[j].bus == grid.bus[i].busNumber:
#                 PV=True
#                 break
#         if PV:
#             bus.append("PV")
#         else:
#             bus.append("PQ")
#       return bus
#    #---------oppretter klasser PV og PQ for bussene--------------------
#    busPVPQ=busclassifier()

x = [1,2,3]
y = [2]

def busklasser(x,y):

    bus_typ = []
    for i in range(len(x)):
        if i == 0:
            bus_typ.append("ref")
            continue
        elif i in y:
            bus_typ.append("PV")

        else:
            bus_typ.append("PQ")

    return bus_typ

bus_k = busklasser(x,y)


def lagBmBmm(bus_k,A = True):
    buss_B_m = []
    buss_B_mm = []
    for i,klasse in enumerate(bus_k):
        if klasse != "ref":
            buss_B_m.append(i)
        if klasse == "PQ":
            buss_B_mm.append(i)
    if A == True:
        return buss_B_m
    else:
        return buss_B_mm

buss_B_m = lagBmBmm(bus_k)
buss_B_mm = lagBmBmm(bus_k, False)

linjer = [(0, 1, 0.1),
          (0, 2, 0.2),
          (1, 2, 0.25)]

def bygg_B_m(x,linjer,buss_B_m):
    length = x
    B = np.zeros((length,length))
    for i,j,X in linjer:
        b = 1/X
        B[i,i] = B[i,i] + b
        B[j,j] = B[j,j] + b
        B[i,j] = B[i,j] - b
        B[j,i] = B[j,i] - b

    B = B[np.ix_(buss_B_m,buss_B_m)]
    
    return B

def bygg_Y_mat()

linjer = [(0,1,0.1),(0,2,0.2),(1,2,0.25)]

print(bygg_B_m(3,linjer,buss_B_m))




        

