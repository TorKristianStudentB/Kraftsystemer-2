import sys
from pathlib import Path
import numpy as np
import pandas as pd

# ========== 1) Gjør TorKode importerbar, og hent Grid-verktøyene ==========
# (ingen formel her, bare oppsett)
TorKode_sti = Path(__file__).resolve().parent.parent / "TorKode"
sys.path.append(str(TorKode_sti))
from MakeGridFromFile import Grid, MakeGrid

# ========== 2) Bygg grid-objektet fra Excel-filen ==========
# (ingen formel her, bare oppsett)
grid_fil = Path(__file__).resolve().parent.parent / "Grid" / "test_trøndelagsnettet.xlsx"
df = pd.read_excel(grid_fil, sheet_name=None)
grid = MakeGrid(df)


# ========== 3) Oversett generatorenes busnummer til indekser ==========
# Formel: ingen. Ren oppslagslogikk:
#   for hver generator g: finn indeks i slik at bus[i].busNumber == g.bus
def finn_gen_indekser(grid):
    gen_indekser = []
    for g in grid.gen:
        for b in grid.bus:
            if b.busNumber == g.bus:
                gen_indekser.append(b.kodens_identifikasjonssystem)
    return gen_indekser

gen_indekser = finn_gen_indekser(grid)
antall_busser = len(grid.bus)


# ========== 4) Klassifiser bussene: ref / PV / PQ ==========
# Formel: ingen. Klassifiseringsregel:
#   buss 0            -> ref   (δ og V kjent, løser ingen likning)
#   buss med generator -> PV   (P og V kjent, løser P-likning)
#   ellers             -> PQ   (P og Q kjent, løser P- og Q-likning)
def busklasser(antall_busser, gen_indekser):
    bus_typ = []
    for i in range(antall_busser):
        if i == 0:
            bus_typ.append("ref")
        elif i in gen_indekser:
            bus_typ.append("PV")
        else:
            bus_typ.append("PQ")
    return bus_typ

bus_k = busklasser(antall_busser, gen_indekser)


# ========== 5) Lag listene med hvilke busser som skal være med i B' og B'' ==========
# Formel: ingen. Definisjon av hvem som er med hvor:
#   busser_B'  = alle busser som IKKE er ref      (PV og PQ)
#   busser_B'' = alle busser som ER PQ            (bare PQ)
def lagBmBmm(bus_k, A=True):
    buss_B_m = []
    buss_B_mm = []
    for i, klasse in enumerate(bus_k):
        if klasse != "ref":
            buss_B_m.append(i)
        if klasse == "PQ":
            buss_B_mm.append(i)
    return buss_B_m if A else buss_B_mm

buss_B_m = lagBmBmm(bus_k)          # PV og PQ -> rader/kolonner i B' (vinkel-delen)
buss_B_mm = lagBmBmm(bus_k, False)  # bare PQ  -> rader/kolonner i B'' (spennings-delen)


# ========== 6) Bygg B': bruker X fra BÅDE linjer og trafoer ==========
# En "gren" er en linje eller en trafo, begge har Frombus, Tobus og X.
def bygg_grener(grid):
    grener = []
    for l in grid.line:
        i = next(b.kodens_identifikasjonssystem for b in grid.bus if b.busNumber == l.Frombus)
        j = next(b.kodens_identifikasjonssystem for b in grid.bus if b.busNumber == l.Tobus)
        grener.append((i, j, l.X))
    for t in grid.trafo:
        i = next(b.kodens_identifikasjonssystem for b in grid.bus if b.busNumber == t.Frombus)
        j = next(b.kodens_identifikasjonssystem for b in grid.bus if b.busNumber == t.Tobus)
        grener.append((i, j, t.X))
    return grener

grener = bygg_grener(grid)

# Formel (B', "P–δ"-matrisen), for hver gren (i,j) med reaktans X:
#   b_ij = 1 / X_ij
#   B'_ii = B'_ii + b_ij        (diagonal, summen over alle grener koblet til i)
#   B'_jj = B'_jj + b_ij        (diagonal, summen over alle grener koblet til j)
#   B'_ij = B'_ij − b_ij        (utenfor diagonal)
#   B'_ji = B'_ji − b_ij        (utenfor diagonal, matrisen er symmetrisk)
# Til slutt: fjern rad/kolonne for busser som ikke skal være med (ref):
#   B'  =  B[ buss_B_m , buss_B_m ]
def bygg_B_m(antall_busser, grener, buss_B_m):
    B = np.zeros((antall_busser, antall_busser))
    for i, j, X in grener:
        b = 1/X
        B[i,i] = B[i,i] + b
        B[j,j] = B[j,j] + b
        B[i,j] = B[i,j] - b
        B[j,i] = B[j,i] - b
    return B[np.ix_(buss_B_m, buss_B_m)]

B_merke = bygg_B_m(antall_busser, grener, buss_B_m)


# ========== 7) Bygg B'': -Im(Y). Y henter vi ferdig fra grid selv ==========
# Formel (B'', "Q–V"-matrisen):
#   Y = admittansmatrisen til hele nettet (kompleks, N×N)
#   B'' = −Im(Y)                       (tar med R og shunt, i motsetning til B')
#   B'' =  (−Im(Y)) [ buss_B_mm , buss_B_mm ]     (bare PQ-busser)
Y = grid.admittansmatrise()     # samme Y-matrise som Tor bruker i NewtonRaphson2.py
B_dobbeltmerke = (-Y.imag)[np.ix_(buss_B_mm, buss_B_mm)]


# ========== 8) Effektflyt-formlene, samme som Tor bruker i NewtonRaphson2.py ==========
# Formel (effekt fra buss i til buss j, gitt dagens V og δ):
#   P_ij = V_i · V_j · |Y_ij| · cos(δ_i − δ_j − θ_ij)
#   Q_ij = V_i · V_j · |Y_ij| · sin(δ_i − δ_j − θ_ij)
#   der  |Y_ij| = np.abs(Y[i,j])   og   θ_ij = np.angle(Y[i,j])
def flyt_P(i, j):
    Vi = grid.bus[i].Volt
    Vj = grid.bus[j].Volt
    Yij = np.abs(Y[i,j])
    vinkel_Y = np.angle(Y[i,j])
    di = grid.bus[i].Angle
    dj = grid.bus[j].Angle
    return Vi*Vj*Yij*np.cos(di - dj - vinkel_Y)

def flyt_Q(i, j):
    Vi = grid.bus[i].Volt
    Vj = grid.bus[j].Volt
    Yij = np.abs(Y[i,j])
    vinkel_Y = np.angle(Y[i,j])
    di = grid.bus[i].Angle
    dj = grid.bus[j].Angle
    return Vi*Vj*Yij*np.sin(di - dj - vinkel_Y)


# ========== 9) Hva P og Q SKAL være på hver buss (gitt av last og produksjon) ==========
# Formel:
#   P_i^planlagt = P_i^gen − P_i^load
#   Q_i^planlagt = Q_i^gen − Q_i^load
def finn_planlagt_PQ(grid):
    P_planlagt = []
    Q_planlagt = []
    for b in grid.bus:
        P_planlagt.append(b.P_gen - b.P_load)
        Q_planlagt.append(b.Q_gen - b.Q_load)
    return P_planlagt, Q_planlagt

P_planlagt, Q_planlagt = finn_planlagt_PQ(grid)


# ========== 10) Iterasjonsløkka ==========
tol = 1e-6         # hvor liten feilen må bli før vi sier vi er ferdige
max_iter = 100      # sikkerhetsstopp, i tilfelle den ikke konvergerer
iterasjon = 0
ferdig = False
konvergerte = False

while ferdig == False:

    # Formel (mismatch/"feilen" i effekt, for hver buss i):
    #   ΔP_i = P_i^planlagt − Σ_j P_ij
    #   ΔQ_i = Q_i^planlagt − Σ_j Q_ij
    feil_P = []
    feil_Q = []
    for i in range(antall_busser):
        P_beregnet = 0
        Q_beregnet = 0
        for j in range(antall_busser):
            P_beregnet = P_beregnet + flyt_P(i, j)
            Q_beregnet = Q_beregnet + flyt_Q(i, j)
        feil_P.append(P_planlagt[i] - P_beregnet)
        feil_Q.append(Q_planlagt[i] - Q_beregnet)

    # Formel (konvergenskriterium):
    #   maks( |ΔP_i| for i i buss_B_m,  |ΔQ_i| for i i buss_B_mm )  ≤  tol  ?
    storste_feil = 0
    for i in buss_B_m:
        if abs(feil_P[i]) > storste_feil:
            storste_feil = abs(feil_P[i])
    for i in buss_B_mm:
        if abs(feil_Q[i]) > storste_feil:
            storste_feil = abs(feil_Q[i])

    if storste_feil <= tol:
        konvergerte = True
        ferdig = True
        break

    if iterasjon >= max_iter:
        ferdig = True
        break

    # Formel (P-halvsteg, løs for Δδ):
    #   B' · Δδ = ΔP / V        (elementvis: for hver buss i i buss_B_m)
    #   δ_i(ny) = δ_i(gammel) + Δδ_i
    if len(buss_B_m) > 0:
        hoyreside = []
        for i in buss_B_m:
            hoyreside.append(feil_P[i] / grid.bus[i].Volt)
        hoyreside = np.array(hoyreside)

        delta_vinkel = np.linalg.solve(B_merke, hoyreside)

        for idx, i in enumerate(buss_B_m):
            grid.bus[i].Angle = grid.bus[i].Angle + delta_vinkel[idx]

    # Formel (regn ΔQ på nytt med de oppdaterte vinklene, deretter Q-halvsteg, løs for ΔV):
    #   ΔQ_i = Q_i^planlagt − Σ_j Q_ij      (på nytt, siden δ nettopp endret seg)
    #   B'' · ΔV = ΔQ / V       (elementvis: for hver buss i i buss_B_mm)
    #   V_i(ny) = V_i(gammel) + ΔV_i
    if len(buss_B_mm) > 0:
        feil_Q = []
        for i in range(antall_busser):
            Q_beregnet = 0
            for j in range(antall_busser):
                Q_beregnet = Q_beregnet + flyt_Q(i, j)
            feil_Q.append(Q_planlagt[i] - Q_beregnet)

        hoyreside = []
        for i in buss_B_mm:
            hoyreside.append(feil_Q[i] / grid.bus[i].Volt)
        hoyreside = np.array(hoyreside)

        delta_volt = np.linalg.solve(B_dobbeltmerke, hoyreside)

        for idx, i in enumerate(buss_B_mm):
            grid.bus[i].Volt = grid.bus[i].Volt + delta_volt[idx]

    iterasjon = iterasjon + 1


# ========== 11) Resultat ==========
print("Konvergerte:", konvergerte)
print("Antall iterasjoner:", iterasjon)
for b in grid.bus:
    print(f"buss {b.busNumber:4d}  V={b.Volt:.4f} pu   vinkel={b.Angle:.4f} rad")
