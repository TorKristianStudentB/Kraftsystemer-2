#------------nettet som brukes fra excelarket---------------
from pathlib import Path
import os
import pandas as pd
NameExcelFile="test_trøndelagsnettet.xlsx"
excelfilepath = (Path(os.getcwd())) / "Grid" / NameExcelFile
df = pd.read_excel(excelfilepath,sheet_name=None)
#------------nettet som brukes fra excelarket---------------



#----------forevalgt metode------------
metode="NR"
forenklet = False
#----------forevalgt metode------------



#--------------her legges alle funksjonene og bibliotekene som brukes-----------
import random
import sys
import time
from itertools import combinations
from collections import Counter
import openpyxl
import pytest as pyt
import numpy as np
import pandapower as pp
from FunctionsInGridMaker.FDLF import FDLF
from FunctionsInGridMaker.theveninZth import theveninZth
from FunctionsInGridMaker.admittansmatrise import cutsem
from FunctionsInGridMaker.NewtonsRaphson import NewtonRaphson
from FunctionsInGridMaker.DCPF import dc_power_flow
from GridMaker.ClassGrid import Grid
from GridMaker.ReadExcelGrid import MakeGrid
from FunctionsInGridMaker.N_minus_en import  N_minus_en_kriteriet
from Validating.validating_pandapower_DC import validating_PP_DC
from Validating.validating_pandapower_NR_bussklassifisering import validating_PP_NR
from Validating.validating_pandapower_FDPF import validating_PP_FDPF
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from datetime import datetime
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle
from matplotlib.lines import Line2D
#--------------her legges alle funksjonene og bibliotekene som brukes-----------
