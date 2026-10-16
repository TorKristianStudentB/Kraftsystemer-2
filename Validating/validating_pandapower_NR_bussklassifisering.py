

#Denne koden klassifiserer en buss som PV om det er en generatoren er tilkoblet, selv om generatoren er av eller har null i verdier.

import sys
from pathlib import Path
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from GridMaker.Imports import pd,np,pp
from GridMaker.ReadExcelGrid import MakeGrid   # direkte import for å unngå sirkulær import


#-------------Pandapower NR validering-------------
def validating_PP_NR(grid):

   #----------starter en tidsklokke på kjøringen-----------
   start_time = time.perf_counter()
   #----------starter en tidsklokke på kjøringen-----------

   #---------Kjører pandapower NR---------
   def run_excel_with_pandapower():


      #---------Systembase og Y-bus---------
      SBASE_MVA = float(grid.Base.Sbase)
      Y = grid.admittansmatrise()

      net = pp.create_empty_network(
         sn_mva=SBASE_MVA
      )


      #---------Klassifiserer bussene som i egen NR---------
      bus_types = []

      for i, bus in enumerate(grid.bus):

         if i == 0:
            bus_types.append("ref")

         elif np.all(np.isclose(Y[i, :], 0)):
            bus_types.append("alene")

         elif any(
            gen.bus == bus.busNumber
            for gen in grid.gen
         ):
            bus_types.append("PV")

         else:
            bus_types.append("PQ")


      #---------Oppretter busser i pandapower---------
      bus_map = {}

      for i, bus in enumerate(grid.bus):

         bus_map[int(bus.busNumber)] = pp.create_bus(
            net,
            vn_kv=float(bus.Vbase),
            name=str(bus.Name),
            in_service=(bus_types[i] != "alene")
         )


      #---------Laster---------
      # grid bruker pu, pandapower bruker MW/MVAr
      for i, bus in enumerate(grid.bus):

         if bus_types[i] == "alene":
            continue

         p_load = float(bus.P_load) * SBASE_MVA
         q_load = float(bus.Q_load) * SBASE_MVA

         if p_load != 0 or q_load != 0:

            pp.create_load(
               net,
               bus=bus_map[int(bus.busNumber)],
               p_mw=p_load,
               q_mvar=q_load,
               name=f"Load bus {bus.busNumber}"
            )


      #---------Referansebuss---------
      # Samme referanse som i egen NR
      slack = grid.bus[0]

      pp.create_ext_grid(
         net,
         bus=bus_map[int(slack.busNumber)],
         vm_pu=float(abs(slack.Volt)),
         va_degree=float(np.degrees(slack.Angle)),
         name=f"Slack bus {slack.busNumber}"
      )


      #---------Generatorer---------
      for i, bus in enumerate(grid.bus):

         if bus_types[i] == "alene":
            continue


         #-----PV-busser-----
         if bus_types[i] == "PV":

            gens_here = [
               gen
               for gen in grid.gen
               if gen.bus == bus.busNumber
            ]

            p_gen = float(bus.P_gen) * SBASE_MVA


            # Summerer Q-grensene for generatorene på bussen
            has_q_limits = (
               len(gens_here) > 0
               and all(
                  gen.Q_min is not None
                  and gen.Q_max is not None
                  for gen in gens_here
               )
            )


            if has_q_limits:

               q_min = sum(
                  float(gen.Q_min)
                  for gen in gens_here
               ) * SBASE_MVA

               q_max = sum(
                  float(gen.Q_max)
                  for gen in gens_here
               ) * SBASE_MVA


               pp.create_gen(
                  net,
                  bus=bus_map[int(bus.busNumber)],
                  p_mw=p_gen,
                  vm_pu=float(abs(bus.Volt)),
                  min_q_mvar=q_min,
                  max_q_mvar=q_max,
                  name=", ".join(
                     str(gen.name)
                     for gen in gens_here
                  )
               )

            else:

               pp.create_gen(
                  net,
                  bus=bus_map[int(bus.busNumber)],
                  p_mw=p_gen,
                  vm_pu=float(abs(bus.Volt)),
                  name=", ".join(
                     str(gen.name)
                     for gen in gens_here
                  )
               )


         #-----PQ-busser med produksjon-----
         elif bus_types[i] == "PQ":

            p_gen = float(bus.P_gen) * SBASE_MVA
            q_gen = float(bus.Q_gen) * SBASE_MVA

            if p_gen != 0 or q_gen != 0:

               pp.create_sgen(
                  net,
                  bus=bus_map[int(bus.busNumber)],
                  p_mw=p_gen,
                  q_mvar=q_gen,
                  name=f"Generator bus {bus.busNumber}"
               )


      #---------Linjer---------
      # R og X ligger allerede i pu etter MakeGrid
      line_pp_indices = []

      for line in grid.line:

         idx = pp.create_impedance(
            net,
            from_bus=bus_map[int(line.Frombus)],
            to_bus=bus_map[int(line.Tobus)],
            rft_pu=float(line.R),
            xft_pu=float(line.X),
            rtf_pu=float(line.R),
            xtf_pu=float(line.X),
            sn_mva=SBASE_MVA,
            name=str(line.Name)
         )

         line_pp_indices.append(idx)


         # Linjesusceptans fordeles på begge ender
         B = float(line.B)

         if B != 0:

            q_shunt = -(B / 2) * SBASE_MVA

            pp.create_shunt(
               net,
               bus=bus_map[int(line.Frombus)],
               q_mvar=q_shunt,
               p_mw=0
            )

            pp.create_shunt(
               net,
               bus=bus_map[int(line.Tobus)],
               q_mvar=q_shunt,
               p_mw=0
            )


      #---------Transformatorer---------
      bus_by_number = {
         int(bus.busNumber): bus
         for bus in grid.bus
      }


      for trafo in grid.trafo:

         from_nr = int(trafo.Frombus)
         to_nr = int(trafo.Tobus)

         if (
            bus_by_number[from_nr].Vbase
            >= bus_by_number[to_nr].Vbase
         ):

            hv_nr = from_nr
            lv_nr = to_nr

         else:

            hv_nr = to_nr
            lv_nr = from_nr


         R = float(trafo.R)
         X = float(trafo.X)

         pp.create_transformer_from_parameters(
            net,

            hv_bus=bus_map[hv_nr],
            lv_bus=bus_map[lv_nr],

            sn_mva=SBASE_MVA,

            vn_hv_kv=float(
               bus_by_number[hv_nr].Vbase
            ),

            vn_lv_kv=float(
               bus_by_number[lv_nr].Vbase
            ),

            vk_percent=np.sqrt(R**2 + X**2) * 100,
            vkr_percent=R * 100,

            pfe_kw=0,
            i0_percent=0,

            shift_degree=0,

            name=str(trafo.Name)
         )


      #---------Kjører pandapower Newton-Raphson---------
      pp.runpp(
         net,
         algorithm="nr",
         init="flat",
         calculate_voltage_angles=True,
         enforce_q_lims=True,
         tolerance_mva=1e-6,
         max_iteration=100,
         numba=False
      )


      #---------Henter bussresultater---------
      # Lagrer i samme bussrekkefølge som grid.bus
      volt = []
      angle = []
      power = []
      qower = []

      for i, bus in enumerate(grid.bus):

         if bus_types[i] == "alene":

            volt.append(float(abs(bus.Volt)))
            angle.append(float(bus.Angle))

            power.append(0.0)
            qower.append(0.0)

            continue


         pp_bus = bus_map[int(bus.busNumber)]
         result = net.res_bus.loc[pp_bus]


         volt.append(
            float(result["vm_pu"])
         )

         angle.append(
            np.radians(
               float(result["va_degree"])
            )
         )


         # Bytter fortegn til samme konvensjon som egen NR
         # og gjør MW/MVAr tilbake til pu
         power.append(
            -float(result["p_mw"]) / SBASE_MVA
         )

         shunt_indices = net.shunt.index[net.shunt["bus"] == pp_bus]
         q_shunt_bus = net.res_shunt.loc[shunt_indices, "q_mvar"].sum()

         qower.append(
            (-float(result["q_mvar"]) + float(q_shunt_bus)) / SBASE_MVA
         )


      #---------Linjeflyt---------
      flow_in_line = []

      for idx in line_pp_indices:

         result = net.res_impedance.loc[idx]

         S = complex(
            float(result["p_from_mw"]) / SBASE_MVA,
            float(result["q_from_mvar"]) / SBASE_MVA
         )

         flow_in_line.append(S)


      #---------Antall iterasjoner---------
      try:

         iterasjoner = int(
            net["_ppc"]["iterations"]
         )

      except Exception:

         iterasjoner = None


      #---------Generatorer som treffer Q-grense---------
      pv_to_pq_generators = []

      if len(net.gen) > 0:

         for idx, gen_result in net.res_gen.iterrows():

            q = float(
               gen_result["q_mvar"]
            )

            q_min = net.gen.loc[
               idx,
               "min_q_mvar"
            ]

            q_max = net.gen.loc[
               idx,
               "max_q_mvar"
            ]


            if (
               not np.isnan(q_max)
               and np.isclose(
                  q,
                  q_max,
                  atol=1e-6
               )
            ):

               pv_to_pq_generators.append(
                  str(
                     net.gen.loc[
                        idx,
                        "name"
                     ]
                  )
               )


            elif (
               not np.isnan(q_min)
               and np.isclose(
                  q,
                  q_min,
                  atol=1e-6
               )
            ):

               pv_to_pq_generators.append(
                  str(
                     net.gen.loc[
                        idx,
                        "name"
                     ]
                  )
               )


      #---------Lagrer pandapower-løsningen i grid---------
      grid.solution = grid.__class__.Solution(
         volt=np.array(volt),

         angle=np.array(angle),

         iterasjoner=iterasjoner,

         mismatch=None,

         konvergerte=bool(net.converged),

         flow_in_line=np.array(flow_in_line),

         pv_to_pq_generators=pv_to_pq_generators,

         power=np.array(power),

         qower=np.array(qower),

         type="PP_NR",

         kjoretid = time.perf_counter() - start_time,
      )


   #---------Kjører valideringen---------
   run_excel_with_pandapower()
#---------------Pandapower NR validering--------------