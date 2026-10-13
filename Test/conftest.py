from pathlib import Path
import pytest as pyt

ROOT = Path(__file__).resolve().parent.parent
TRONDELAG = ROOT / "Grid" / "test_trøndelagsnettet.xlsx"


@pyt.fixture
def trondelag():
    return TRONDELAG