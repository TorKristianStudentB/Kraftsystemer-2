# -*- coding: utf-8 -*-
#----------------------------conftest.py--------------------------------------------------
# Felles oppsett for testene i Test/:
#   - legger prosjektroten på sys.path, slik at "from GridMaker.Imports import ..." virker uansett om du kjører
#       pytest                      (fra prosjektroten)
#       python -m pytest Test       (fra prosjektroten)
#   - lager lastflyt-fixtures som bygger små nett til xlsx i en midlertidig mappe.
# Kjør alle testene (fra Kraftsystemer-2):   .venv\Scripts\python.exe -m pytest Test -v
#----------------------------conftest.py--------------------------------------------------
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
TEST_MAPPE = Path(__file__).resolve().parent
if str(TEST_MAPPE) not in sys.path:
    sys.path.insert(0, str(TEST_MAPPE))

TRONDELAG = ROOT / "Grid" / "test_trøndelagsnettet.xlsx"


@pytest.fixture
def nett(tmp_path):
    #----nett(spec, ...) -> (sti til xlsx). Eksempel: grid = MakeGrid(nett(spec))----
    from nett_hjelp import lag_nett
    teller = {"n": 0}

    def lag(spec, **kw):
        teller["n"] += 1
        return lag_nett(spec, tmp_path / f"nett{teller['n']}.xlsx", **kw)
    return lag


@pytest.fixture
def trondelag():
    #----sti til Trøndelagsnettet i Grid/; testene hoppes over hvis fila mangler----
    if not TRONDELAG.exists():
        pytest.skip(f"fant ikke {TRONDELAG}")
    return TRONDELAG
