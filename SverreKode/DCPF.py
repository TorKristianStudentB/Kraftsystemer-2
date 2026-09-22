import numpy as np

def dc_power_flow(grid):

    Y=grid.admittansmatrise()

#Ydcmatrisen
    Y_dc=-np.imag(Y)


    def busclassifier():
        bus=[]
        for i in range(len(grid.bus)):
            if i == 0:
                bus.append("ref")
                continue
            if np.all(np.isclose(Y[i,:], 0)):   #bussen henger ikke sammen med noe -> hopp over den
                bus.append("alene")
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

#regner ut netto aktiv effekt
    def power_scheduled():
        P_scheduled = []

        for i in range(len(grid.bus)):
            P = grid.bus[i].P_gen - grid.bus[i].P_load
            P_scheduled.append(P)

        return np.array(P_scheduled)

    P_scheduled = power_scheduled()


#finner busser som skal være med i beregningen, dvs ikke referansebussen
    active_buses = []

    for i in range(len(grid.bus)):

        if busPVPQ[i] != "ref" and busPVPQ[i] != "alene":
            active_buses.append(i)

#fjerner referansebussen og frakoblede busser fra Y_dc og P_scheduled
    Y_dc_reduced = Y_dc[np.ix_(active_buses, active_buses)]
    P_reduced = P_scheduled[active_buses]

#konverterer aktiv effekt til pu
    P_reduced_pu = P_reduced / grid.Base.Sbase

#løser dc power flow og finner spenningsvinklen
    delta_reduced = np.linalg.solve(Y_dc_reduced, P_reduced_pu)
    delta = np.zeros(len(grid.bus))

    for k in range(len(active_buses)):

        bus_index = active_buses[k]
        delta[bus_index] = delta_reduced[k]
        


    #beregne aktiv effektflyt på linjene
    def flow_in_line():
        flow = []

        for line in grid.line:

            for i in range(len(grid.bus)):

                if grid.bus[i].busNumber == line.Frombus:
                    from_bus = i

                if grid.bus[i].busNumber == line.Tobus:
                    to_bus = i
#beregner linjeflyten i pu og konverterer til MW
            P_ij = (delta[from_bus] - delta[to_bus])/line.X

            P_ij = P_ij * grid.Base.Sbase

            flow.append(P_ij)

        return flow

    line_flow = flow_in_line()

#beregne nødvendig netto aktiv effekt fra slack bussen

    p_slack = 0 

    for i in range(len(grid.bus)):

        if busPVPQ[i] != "ref" and busPVPQ[i] != "alene":
            p_slack = p_slack - P_scheduled[i]


    for i in range(len(grid.bus)):

        grid.bus[i].Angle = delta[i]

    #lagre løsningen

    grid.solution = grid.__class__.solution(
        volt =[b.Volt for b in grid.bus],
        angle = [b.Angle for b in grid.bus],
        iterations = 1,
        mismatch = np.array([]),
        konvergerte = True,
        flow_in_line = line_flow
    )

    return grid