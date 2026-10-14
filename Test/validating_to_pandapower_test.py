import pandas as pd
import pytest as pyt
import numpy as np

#--------------validating againts pandapower------------------
def test_validating_answers_error_againts_pandapower_NR(grid_g):

   grid = grid_g

   A_volt = pd.DataFrame(columns=["NR"])
   A_angle = pd.DataFrame(columns=["NR"])

   #-------Opretter en A matrise til sammenlignign av resultater-----
   iterasjon = {}
   kjøretid = {}


   #---------Kjører lastflytanalyse med Newtons Rapshons metode- 
   grid.loadflowsolutionNR()
   A_volt["NR"] = grid.solution.volt
   A_angle["NR"] = grid.solution.angle
   #---------Kjører lastflytanalyse med Newtons Rapshons metode-

   grid = grid_g

   #---------Kjører lastflytanalyse med FDLF metode- 
   grid.validating_PP_NR()
   A_volt["PP_NR"] = grid.solution.volt
   A_angle["PP_NR"] = grid.solution.angle
   #---------Kjører lastflytanalyse med FDLF metode-

   assert np.allclose(A_volt["PP_NR"], A_volt["NR"], atol=1e-3)
   assert np.allclose(A_angle["PP_NR"], A_angle["NR"], atol=1e-3)

def test_validating_answers_error_againts_pandapower_DC(grid_g):

   grid = grid_g

   A_volt = pd.DataFrame(columns=["DC","PP_DC"])
   A_angle = pd.DataFrame(columns=["DC","PP_DC"])
      

   #---------Kjører lastflytanalyse med DC metode- 
   grid.DCPF()
   A_volt["DC"] = grid.solution.volt
   A_angle["DC"] = grid.solution.angle
   #---------Kjører lastflytanalyse med DC metode-

    #---------Kjører lastflytanalyse med FDLF metode- 
   grid.validating_PP_DC()
   A_volt["PP_DC"] = grid.solution.volt
   A_angle["PP_DC"] = grid.solution.angle
   #---------Kjører lastflytanalyse med FDLF metode-

   assert np.allclose(A_volt["PP_DC"], A_volt["DC"], atol=1e-3)
   assert np.allclose(A_angle["PP_DC"], A_angle["DC"], atol=1e-3)

def test_validating_answers_error_againts_pandapower_FD(grid_g):
   grid = grid_g

   A_volt = pd.DataFrame(columns=["FD","PP_FD"])
   A_angle = pd.DataFrame(columns=["NR","PP_FD"])

   #---------Kjører lastflytanalyse med FDLF metode- 
   grid.FDLF()
   A_volt["FD"] = grid.solution.volt
   A_angle["FD"] = grid.solution.angle
   #---------Kjører lastflytanalyse med FDLF metode-

   #---------Kjører lastflytanalyse med FDLF metode- 
   grid.validating_PP_FDPF()
   A_volt["PP_FD"] = grid.solution.volt
   A_angle["PP_FD"] = grid.solution.angle
   #---------Kjører lastflytanalyse med FDLF metode-
   
   assert np.allclose(A_volt["PP_FD"], A_volt["FD"], atol=1e-3)
   assert np.allclose(A_angle["PP_FD"], A_angle["FD"], atol=1e-3)
#--------------validating againts pandapower------------------






