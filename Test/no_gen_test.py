from GridMaker.Imports import pyt

#---------------Kjører og ser om null i generator får samme svar som 0.0000001---------
def test_no_gen_NR(grid_g,grid_h):

    g = grid_g
    h = grid_h

    for b in g.bus:
        b.P_gen = 0
        b.Q_gen = 0


    for c in h.bus:
        c.P_gen = 0.0001
        c.Q_gen = 0.0001

    g.loadflowsolutionNR()
    h.loadflowsolutionNR()


    assert g.solution.konvergerte == True
    assert h.solution.konvergerte == True


def test_no_gen_FDLF(grid_g,grid_h):

    g = grid_g
    h = grid_h

    for b in g.bus:
        b.P_gen = 0
        b.Q_gen = 0

        g.FDLF()
        h.FDLF()

    for c in h.bus:
        c.P_gen = 0.0001
        c.Q_gen = 0.0001

    g.FDLF()
    h.FDLF()

    assert g.solution.konvergerte == True
    assert h.solution.konvergerte == True

    
def test_no_gen_DCPF(grid_g,grid_h):

    g = grid_g
    h = grid_h

    for b in g.bus:
        b.P_gen = 0
        b.Q_gen = 0

    for c in h.bus:
        c.P_gen = 0.0001
        c.Q_gen = 0.0001

        

    g.DCPF()
    h.DCPF()

    assert g.solution.konvergerte == True
    assert h.solution.konvergerte == True
#---------------Kjører og ser om null i generator får samme svar som 0.0000001---------
