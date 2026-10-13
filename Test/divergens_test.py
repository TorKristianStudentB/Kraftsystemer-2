from GridMaker.Imports import MakeGrid 
import pytest as pyt
import numpy as np

@pyt.mark.parametrize("metode",["NR"])
def test_divergens_krasjer(trondelag,metode):

    g = MakeGrid(trondelag)

    for b in g.bus:
        b.P_load = b.P_load *10000
        b.Q_load = b.Q_load *10000

    g.loadflowsolutionNR()


    assert g.solution.konvergerte == False
    assert np.all(np.isnan(g.solution.volt))
    

