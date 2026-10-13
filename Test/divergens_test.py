from GridMaker.Imports import pyt,np

#---------tester om divirgens på solverene gir konvergens false istedenfor error-------
def test_divergens_krasjer(grid_g):

    g = grid_g

    for b in g.bus:
        b.P_load = b.P_load *10000 #setter inn helt syke høye verdier, må jo divirgere da!!!!
        b.Q_load = b.Q_load *10000 #setter inn helt syke høye verdier, må jo divirgere da!!!!

    g.loadflowsolutionNR()


    assert g.solution.konvergerte == False
#---------tester om divirgens på solverene gir konvergens false istedenfor error-------
