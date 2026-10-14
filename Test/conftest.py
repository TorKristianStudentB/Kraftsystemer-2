from GridMaker.Imports import MakeGrid,Path,pyt,os


#--------gir trøndelagsnettet som xlsx verktøykasse til testene-------------
@pyt.fixture
def excelfile():
    filsti=Path(os.getcwd())
    return filsti / "Grid/test_trøndelagsnettet.xlsx"
#--------gir trøndelagsnettet som xlsx verktøykasse til testene-------------


#--------Gidder ikke å kalle Makegrid hele tiden i testene------------
@pyt.fixture
def grid_g(excelfile):
    return MakeGrid(excelfile)
#--------Gidder ikke å kalle Makegrid hele tiden i testene------------


#--------Gidder ikke å kalle Makegrid hele tiden i testene------------
@pyt.fixture
def grid_h(excelfile):
    return MakeGrid(excelfile)
#--------Gidder ikke å kalle Makegrid hele tiden i testene------------


#--------referansestrukturen til excelarket----------
@pyt.fixture
def struktur_excel_arket():
       #Referansestruktur hentet fra Grid/test_trøndelagsnettet.xlsx (ark -> overskrifter i rad 1)
    REF_STRUKTUR = {
          "bus": ["bus_id", "name", "bidz", "Vbase", "lat", "lon", "S_base [MVA] ",
                   "V [P.U]", "Angle [rad]", "P_gen", "Q_gen", "P_load", "Q_load"],
          "gen": ["name", "type", "type2", "Pmax", "Qmax", "Qmin", "bus", "lat", "lon"],
          "line": ["line_id", "area0", "bus0", "bus1", "length", "Vbase", "lat", "lon",
                   "R_per_m", "X_per_m", "B_per_m", "name", "eic code","S_max"],
          "trafo": ["transformer_id", "bus0", "bus1", "ratio", "R", "X", "name","S_max"],
          "link": ["index", "name", "area0", "area1", "bus0", "bus1", "lat", "lon", "Pinj"],
       }
    return REF_STRUKTUR
#--------referansestrukturen til excelarket----------  



