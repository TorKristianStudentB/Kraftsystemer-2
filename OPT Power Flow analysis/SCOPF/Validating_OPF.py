
from pathlib import Path
import sys
import copy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from GridMaker.Imports import MakeGrid, df
from SCOPF.dc_scopf import dc_scopf

# Punkt 3: Finn optimal generatorproduksjon
grid = dc_scopf(MakeGrid(df))
assert grid.solution.konvergerte

Sbase = grid.Base.Sbase
rader = []

# Punkt 4: Verifiser med DCPF
tilfeller = [None] + [
    i for i, l in enumerate(grid.line)
    if not getattr(l, "kunstig_line", False)
]

for utfall in tilfeller:
    test = copy.deepcopy(grid)
    test.solution = None

    navn = "N0"
    if utfall is not None:
        linje = test.line.pop(utfall)
        navn = f"Linje {linje.lineNumber}"
    
    test.__dict__.pop("_admittans_lagret", None)
    test.DCPF()

    if not test.solution.konvergerte:
        raise RuntimeError(f"DCPF feilet: {navn}")

    belastninger = []

    # Linjebelastninger
    for i, linje in enumerate(test.line):
        if getattr(linje, "kunstig_line", False):
            continue

        P = test.solution.flow_in_line[i]
        belastninger.append((
            f"Linje {linje.lineNumber}",
            abs(P) / linje.S_max * 100
        ))

    # Transformatorbelastninger – samme formel som punkt 3
    vinkler = {
        b.busNumber: b.Angle for b in test.bus
    }
    vbase = {
        b.busNumber: b.Vbase for b in test.bus
    }

    for trafo in test.trafo:
        i, j = trafo.Frombus, trafo.Tobus
        nominelt = min(vbase[i], vbase[j]) / max(vbase[i], vbase[j])
        tapp_pu = trafo.ratio / nominelt

        P = tapp_pu / trafo.X * (vinkler[i] - vinkler[j]) * Sbase

        belastninger.append((
            f"Trafo {i}-{j}",
            abs(P) / trafo.S_max * 100
        ))

    verst = max(belastninger, key=lambda x: x[1])

    rader.append((navn, verst[0], verst[1]))

# Skriv ut resultatene
print("\n--- PUNKT 4: N-1 VERIFICATION ---")

for utfall, gren, belastning in rader:
    print(f"{utfall:15} {gren:20} {belastning:7.2f} %")

# Kontroller N-1-kriteriet
godkjent = all(b <= 100.0001 for _, _, b in rader)

if godkjent:
    print("\nN-1 VERIFIKASJON VELLYKKET")
    print("Alle linjeutfall er undersøkt.")
    print("Ingen linjer eller transformatorer er overbelastet.")
else:
    print("\nN-1 VERIFIKASJON IKKE VELLYKKET")
    print("Minst ett tilfelle gir overbelastning.")

    for utfall, gren, belastning in rader:
        if belastning > 100.0001:
            print(f"{utfall}: {gren} er belastet {belastning:.2f} %")




