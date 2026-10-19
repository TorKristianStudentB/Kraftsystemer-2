import pandas as pd
import pytest as pyt
import numpy as np

#--------------validating againts pandapower------------------
def test_validating_answers_error_againts_pandapower_NR(grid_g,grid_h):

   grid = grid_g


   A_volt = pd.DataFrame(columns=["NR","PP_NR"])
   A_angle = pd.DataFrame(columns=["NR","PP_NR"])
   A_power = pd.DataFrame(columns=["NR","PP_NR"])
   A_qower = pd.DataFrame(columns=["NR","PP_NR"])

   #-------Opretter en A matrise til sammenlignign av resultater-----
   iterasjon = {}
   kjøretid = {}


   #---------Kjører lastflytanalyse med Newtons Rapshons metode- 
   grid.loadflowsolutionNR()
   A_volt["NR"] = grid.solution.volt
   A_angle["NR"] = grid.solution.angle
   A_power["NR"] = grid.solution.power
   A_qower["NR"] = grid.solution.qower
   #---------Kjører lastflytanalyse med Newtons Rapshons metode-

   
   grid = grid_h


   #---------Kjører lastflytanalyse med FDLF metode- 
   grid.validating_PP_NR()
   A_volt["PP_NR"] = grid.solution.volt
   A_angle["PP_NR"] = grid.solution.angle
   A_power["PP_NR"] = grid.solution.power
   A_qower["PP_NR"] = grid.solution.qower
   #---------Kjører lastflytanalyse med FDLF metode-

   #--------------Printer hvilke bus det er feil i---------------
   for j in range(len(grid.solution.volt)):
         e_volt=A_volt["PP_NR"][j]-A_volt["NR"][j]
         e_angle=A_angle["PP_NR"][j]-A_angle["NR"][j]
         e_power=A_power["PP_NR"][j]-A_power["NR"][j]
         e_qower=A_qower["PP_NR"][j]-A_qower["NR"][j]
         if e_volt > 1e-1:
             print(f"spennings node: {j} er utenfor valideringstesten")
         if e_angle > 1e-1:
            print(f"Angle node: {j} er utenfor valideringstesten")
         if e_power > 1e-1:
            print(f"Power node: {j} er utenfor valideringstesten")
         if e_qower > 1e-1:
            print(f"Qower node: {j} er utenfor valideringstesten")
   #--------------Printer hvilke bus det er feil i---------------
   

   assert np.allclose(A_volt["PP_NR"], A_volt["NR"], atol=1e-1,rtol=0)
   assert np.allclose(A_angle["PP_NR"], A_angle["NR"], atol=1e-1,rtol=0)
   assert np.allclose(A_power["PP_NR"], A_power["NR"], atol=1,rtol=0)
   assert np.allclose(A_qower["PP_NR"], A_qower["NR"], atol=1,rtol=0)

def test_validating_answers_error_againts_pandapower_DC(grid_g,grid_h):

   grid = grid_g

   A_volt = pd.DataFrame(columns=["DC","PP_DC"])
   A_angle = pd.DataFrame(columns=["DC","PP_DC"])
   A_power = pd.DataFrame(columns=["DC","PP_DC"])

   #---------Kjører lastflytanalyse med DC metode- 
   grid.DCPF()
   A_volt["DC"] = grid.solution.volt
   A_angle["DC"] = grid.solution.angle
   A_power["DC"] = grid.solution.power
   #---------Kjører lastflytanalyse med DC metode-

   grid = grid_h

   #---------Kjører lastflytanalyse med FDLF metode- 
   grid.validating_PP_DC()
   A_volt["PP_DC"] = grid.solution.volt
   A_angle["PP_DC"] = grid.solution.angle
   A_power["PP_DC"] = grid.solution.power
   #---------Kjører lastflytanalyse med FDLF metode-

   assert np.allclose(A_volt["PP_DC"], A_volt["DC"], atol=1e-3,rtol=0)
   assert np.allclose(A_angle["PP_DC"], A_angle["DC"], atol=1e-3,rtol=0)
   assert np.allclose(A_power["PP_DC"], A_power["DC"], atol=1,rtol=0)

def test_validating_answers_error_againts_pandapower_FD(grid_g,grid_h):
   grid = grid_g

   A_volt = pd.DataFrame(columns=["FD","PP_FD"])
   A_angle = pd.DataFrame(columns=["FD","PP_FD"])
   A_power = pd.DataFrame(columns=["FD","PP_FD"])
   A_qower = pd.DataFrame(columns=["FD","PP_FD"])

   #---------Kjører lastflytanalyse med FDLF metode- 
   grid.FDLF()
   A_volt["FD"] = grid.solution.volt
   A_angle["FD"] = grid.solution.angle
   A_power["FD"] = grid.solution.power
   A_qower["FD"] = grid.solution.qower
   #---------Kjører lastflytanalyse med FDLF metode-
   
   grid = grid_h

   #---------Kjører lastflytanalyse med FDLF metode- 
   grid.validating_PP_FDPF()
   A_volt["PP_FD"] = grid.solution.volt
   A_angle["PP_FD"] = grid.solution.angle
   A_power["PP_FD"] = grid.solution.power
   A_qower["PP_FD"] = grid.solution.qower
   #---------Kjører lastflytanalyse med FDLF metode-
   
   assert np.allclose(A_volt["PP_FD"], A_volt["FD"], atol=1e-3,rtol=0)
   assert np.allclose(A_angle["PP_FD"], A_angle["FD"], atol=1e-3,rtol=0)
   assert np.allclose(A_power["PP_FD"], A_power["FD"], atol=1,rtol=0)
   assert np.allclose(A_qower["PP_FD"], A_qower["FD"], atol=1,rtol=0)
#--------------validating againts pandapower------------------






