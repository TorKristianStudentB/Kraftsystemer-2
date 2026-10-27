from GridMaker.Imports import pyt

#---------Tester no load hvor vi har null eller veldig nærme null----------
def test_no_load_NR(grid_g,grid_h):

    g = grid_g
    h = grid_h

    for b in g.bus:
        b.P_load = 0
        b.Q_load = 0

    for c in h.bus:
        c.P_load = 0.0001
        c.Q_load = 0.0001



    g.loadflowsolutionNR()
    h.loadflowsolutionNR()


    assert g.solution.konvergerte == True
    assert h.solution.konvergerte == True
    assert g.solution.angle == pyt.approx(h.solution.angle,abs=1e-3)

def test_no_load_FD(grid_g,grid_h):

    g = grid_g
    h = grid_h

    for b in g.bus:
        b.P_load = 0
        b.Q_load = 0

    for c in h.bus:
        c.P_load = 0.0001
        c.Q_load = 0.0001


    g.FDLF()
    h.FDLF()

    #null last og nesten null last skal gi samme utfall og samme løsning
    assert g.solution.konvergerte == h.solution.konvergerte
    assert g.solution.angle == pyt.approx(h.solution.angle,abs=1e-3)

def test_no_load_DC(grid_g,grid_h):

    g = grid_g
    h = grid_h

    for b in g.bus:
        b.P_load = 0
        b.Q_load = 0

    for c in h.bus:
        c.P_load = 0.0001
        c.Q_load = 0.0001


    g.DCPF()
    h.DCPF()

    #DC er et lineært system, så null last gir alltid en endelig løsning og skal ligne på nesten null last
    assert g.solution.konvergerte == True
    assert h.solution.konvergerte == True
    assert g.solution.angle == pyt.approx(h.solution.angle,abs=1e-3)
#---------Tester no load hvor vi har null eller veldig nærme null----------