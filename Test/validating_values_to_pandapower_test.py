import pandas as pd
import pytest as pyt
import numpy as np

#--------------validating againts pandapower------------------
def validating_answers_error_againts_pandapower(grid_g):

   grid = grid_g

   A_volt = pd.DataFrame(columns=["NR", "DC", "FD","PP_NR", "PP_NR2", "PP_DC", "PP_FD"])
   A_angle = pd.DataFrame(columns=["NR", "DC", "FD","PP_NR", "PP_NR2","PP_DC", "PP_FD"])
   #-------Opretter en A matrise til sammenlignign av resultater-----
   iterasjon = {}
   kjøretid = {}


   #---------Kjører lastflytanalyse med Newtons Rapshons metode- 
   grid.loadflowsolutionNR()
   A_volt["NR"] = grid.solution.volt
   A_angle["NR"] = grid.solution.angle
   iterasjon["NR"] = grid.solution.iterasjoner
   kjøretid["NR"] = grid.solution.kjoretid
   #---------Kjører lastflytanalyse med Newtons Rapshons metode-


   #---------Kjører lastflytanalyse med DC metode- 
   grid.DCPF()
   A_volt["DC"] = grid.solution.volt
   A_angle["DC"] = grid.solution.angle
   iterasjon["DC"] = grid.solution.iterasjoner
   kjøretid["DC"] = grid.solution.kjoretid
   #---------Kjører lastflytanalyse med DC metode-

   #---------Kjører lastflytanalyse med FDLF metode- 
   grid.FDLF()
   A_volt["FD"] = grid.solution.volt
   A_angle["FD"] = grid.solution.angle
   iterasjon["FD"] = grid.solution.iterasjoner
   kjøretid["FD"] = grid.solution.kjoretid
   #---------Kjører lastflytanalyse med FDLF metode-

   #---------Kjører lastflytanalyse med FDLF metode- 
   grid.validating_PP_NR()
   A_volt["PP_NR"] = grid.solution.volt
   A_angle["PP_NR"] = grid.solution.angle
   #---------Kjører lastflytanalyse med FDLF metode-

   #---------Kjører lastflytanalyse med FDLF metode- 
   grid.validating_PP_NR2()
   A_volt["PP_NR2"] = grid.solution.volt
   A_angle["PP_NR2"] = grid.solution.angle
   #---------Kjører lastflytanalyse med FDLF metode-


   #---------Kjører lastflytanalyse med FDLF metode- 
   grid.validating_PP_DC()
   A_volt["PP_DC"] = grid.solution.volt
   A_angle["PP_DC"] = grid.solution.angle
   #---------Kjører lastflytanalyse med FDLF metode-

   
   #---------Kjører lastflytanalyse med FDLF metode- 
   grid.validating_PP_FDPF()
   A_volt["PP_FD"] = grid.solution.volt
   A_angle["PP_FD"] = grid.solution.angle
   #---------Kjører lastflytanalyse med FDLF metode-
      

   assert np.allclose(A_volt["PP_NR"], A_volt["NR"], atol=1e-3)
   assert np.allclose(A_volt["PP_FD"], A_volt["FD"], atol=1e-3)
   assert np.allclose(A_volt["PP_DC"], A_volt["DC"], atol=1e-3)
#--------------validating againts pandapower------------------
