from GridMaker.Imports import MakeGrid 
import pytest as pyt

@pyt.mark.parametrize("metode",["NR","FD","DC"])
def test_no_gen(trondelag,metode):

    g = MakeGrid(trondelag)
    h = MakeGrid(trondelag)

    for b in g.bus:
        b.P_gen = 0
        b.Q_gen = 0

    for c in h.bus:
        c.P_gen = 0.0001
        c.Q_gen = 0.0001

    if metode == "NR":

        g.loadflowsolutionNR()
        h.loadflowsolutionNR()

    elif metode =="FD":

        g.FDLF()
        h.FDLF()

    elif metode == "DC":

        g.DCPF()
        h.DCPF()

    assert g.solution.konvergerte == True
    assert h.solution.konvergerte == True
    assert g.solution.volt == pyt.approx(h.solution.volt,abs=1e-6)
    assert g.solution.angle == pyt.approx(h.solution.angle,abs=1e-3)
    

