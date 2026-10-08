#--------------her legges alle funksjonene og bibliotekene som brukes-----------
import os
from pathlib import Path
import pandas as pd
import random
import sys
import numpy as np
import pandapower as pp
from FunctionsInGridMaker.FDLF import FDLF
from FunctionsInGridMaker.theveninZth import theveninZth
from FunctionsInGridMaker.admittansmatrise import cutsem
from FunctionsInGridMaker.NewtonsRaphson import NewtonRaphson
from FunctionsInGridMaker.DCPF import dc_power_flow
from FunctionsInGridMaker.pandapower_FDLF import pandapower_FDLF
from GridMaker.ClassGrid import Grid
from GridMaker.ReadExcelGrid import MakeGrid
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from datetime import datetime
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle
from matplotlib.lines import Line2D
from GridMaker.Visualisering_og_rapport import lag_rapport
from Validating.Validating_pandapower import validating

#--------------her legges alle funksjonene og bibliotekene som brukes-----------
