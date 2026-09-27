import numpy as np
#-----------Fant ut av denne dritten her-----------
def theveninZth(grid, bus1, bus2):
    i = grid.finne_bus_indeks(grid,bus1)
    j = grid.finne_bus_indeks(grid,bus2)
    Y = grid.admittansmatrise()
    Zbus = np.linalg.inv(Y)
    Zth = Zbus[i,i] + Zbus[j,j] - Zbus[i,j] - Zbus[j,i]

    return Zth
#-----------Fant ut av denne dritten her-----------

      