


#Denne koden klassifiserer en buss på PV om det ikke er noe verdier på generatoren, ikke om den er tilkoblet


from GridMaker.Imports import pd,np,pp,excelfilepath
from GridMaker.ReadExcelGrid import MakeGrid   # direkte, ikke via Imports (unngår sirkulær import)

#---------------validerer nettet med pandapower--------------
def validating_PP_NR(excel_file,grid):
   IMPEDANCE_UNIT="ohm"   # linjenes R og X står i ohm i excelarket (trafoenes R og X står allerede i pu)
   #---------KONVERTER R OG X TIL P.U.------------------------
   def impedance_to_pu(r, x, vbase_kv, sbase_mva):

      r = float(r)
      x = float(x)

      # Verdiene er allerede i p.u.
      if IMPEDANCE_UNIT == "pu":
         return r, x

      # Verdiene er i ohm
      elif IMPEDANCE_UNIT == "ohm":

         zbase = (vbase_kv ** 2) / sbase_mva

         r_pu = r / zbase
         x_pu = x / zbase

         return r_pu, x_pu

      else:
         raise ValueError(
               "IMPEDANCE_UNIT må være enten 'pu' eller 'ohm'"
         )
   #---------KONVERTER R OG X TIL P.U.------------------------


   #---------HOVEDFUNKSJON-----------------------------------
   def run_excel_with_pandapower(excel_file):


      # --------------------------------------------------
      # 1. Les Excel
      # --------------------------------------------------


      df = pd.read_excel(
         excel_file,
         sheet_name=None
      )

      bus_df = df["bus"]
      line_df = df["line"]
      gen_df = df["gen"]
      trafo_df = df["trafo"]

      # --------------------------------------------------
      # 2. Les systembase fra Excel
      # --------------------------------------------------


      sbase_values = (
         bus_df["S_base [MVA] "]
         .dropna()
         .unique()
      )

      if len(sbase_values) == 0:
         raise ValueError(
               "Fant ingen verdi i kolonnen 'S_base [MVA]'."
         )

      if len(sbase_values) != 1:
         raise ValueError(
               f"Fant flere S_base-verdier i nettet: {sbase_values}"
         )

      SBASE_MVA = float(sbase_values[0])

      # --------------------------------------------------
      # 3. Lag tomt pandapower-nett
      # --------------------------------------------------

      net = pp.create_empty_network(
         sn_mva=SBASE_MVA
      )


      # --------------------------------------------------
      # 4. Lag busser
      # --------------------------------------------------

      bus_map = {}

      for _, row in bus_df.iterrows():

         bus_number = int(row["bus_id"])

         pp_bus = pp.create_bus(
               net,
               vn_kv=float(row["Vbase"]),
               name=row["name"]
         )

         bus_map[bus_number] = pp_bus


      # --------------------------------------------------
      # 5. Lag laster
      # --------------------------------------------------

      for _, row in bus_df.iterrows():

         bus_number = int(row["bus_id"])

         p_load = float(row["P_load"])
         q_load = float(row["Q_load"])

         if p_load != 0 or q_load != 0:

               pp.create_load(
                  net,
                  bus=bus_map[bus_number],
                  p_mw=p_load,
                  q_mvar=q_load,
                  name=f"Load bus {bus_number}"
               )


      # --------------------------------------------------
      # 6. Slack + generatorer
      # --------------------------------------------------


      #----Q-grenser pr. buss (summen av generatorene på bussen), samme som i NR-koden----
      q_grenser = {}
      if "Qmax" in gen_df.columns and "Qmin" in gen_df.columns:
         for _, g_row in gen_df.iterrows():
            b_nr = int(g_row["bus"])
            q_max, q_min = q_grenser.get(b_nr, (0.0, 0.0))
            q_grenser[b_nr] = (q_max + float(g_row["Qmax"]), q_min + float(g_row["Qmin"]))

      slack_created = False

      for _, row in bus_df.iterrows():

         bus_number = int(row["bus_id"])

         p_gen = float(row["P_gen"])

         if p_gen == 0:
               continue

         vm_pu = float(row["V [P.U]"])

         # Første generatorbuss blir foreløpig slack
         if not slack_created:

               angle_rad = float(row["Angle [rad]"])

               pp.create_ext_grid(
                  net,
                  bus=bus_map[bus_number],
                  vm_pu=vm_pu,
                  va_degree=np.degrees(angle_rad),
                  name=f"Slack bus {bus_number}"
               )



               slack_created = True

         # Resten blir PV-busser
         else:

               pp.create_gen(
                  net,
                  bus=bus_map[bus_number],
                  p_mw=p_gen,
                  vm_pu=vm_pu,
                  max_q_mvar=q_grenser[bus_number][0] if bus_number in q_grenser else np.nan,
                  min_q_mvar=q_grenser[bus_number][1] if bus_number in q_grenser else np.nan,
                  name=f"Generator bus {bus_number}"
               )


      # --------------------------------------------------
      # 7. Lag linjer
      # --------------------------------------------------


      for _, row in line_df.iterrows():

         from_bus_number = int(row["bus0"])
         to_bus_number = int(row["bus1"])

         vbase_kv = float(row["Vbase"])

         r_pu, x_pu = impedance_to_pu(
               row["R"],
               row["X"],
               vbase_kv,
               SBASE_MVA
         )

         pp.create_impedance(
               net,

               from_bus=bus_map[from_bus_number],
               to_bus=bus_map[to_bus_number],

               rft_pu=r_pu,
               xft_pu=x_pu,

               rtf_pu=r_pu,
               xtf_pu=x_pu,

               sn_mva=SBASE_MVA,

               name=row["name"]
         )



      # --------------------------------------------------
      # 8. Lag transformatorer
      # --------------------------------------------------

      for _, row in trafo_df.iterrows():

         bus0_number = int(row["bus0"])
         bus1_number = int(row["bus1"])

         bus0 = bus_map[bus0_number]
         bus1 = bus_map[bus1_number]

         # Finn spenningsnivåene fra bus-tabellen
         v0 = float(
               bus_df.loc[
                  bus_df["bus_id"] == bus0_number,
                  "Vbase"
               ].iloc[0]
         )

         v1 = float(
               bus_df.loc[
                  bus_df["bus_id"] == bus1_number,
                  "Vbase"
               ].iloc[0]
         )

         # Finn HV- og LV-side
         if v0 >= v1:

               hv_bus = bus0
               lv_bus = bus1

               vn_hv_kv = v0
               vn_lv_kv = v1

         else:

               hv_bus = bus1
               lv_bus = bus0

               vn_hv_kv = v1
               vn_lv_kv = v0


         # Konverter trafoimpedans
         #----trafoenes R og X står allerede i pu i excelarket (MakeGrid konverterer dem heller ikke), så de brukes direkte----
         r_pu, x_pu = float(row["R"]), float(row["X"])

         z_pu = np.sqrt(
               r_pu**2 + x_pu**2
         )

         vk_percent = z_pu * 100
         vkr_percent = r_pu * 100


         pp.create_transformer_from_parameters(
               net,

               hv_bus=hv_bus,
               lv_bus=lv_bus,

               sn_mva=SBASE_MVA,

               vn_hv_kv=vn_hv_kv,
               vn_lv_kv=vn_lv_kv,

               vk_percent=vk_percent,
               vkr_percent=vkr_percent,

               pfe_kw=0,
               i0_percent=0,

               shift_degree=0,

               name=row["name"]
         )



      # --------------------------------------------------
      # 10. Kjør Newton-Raphson
      # --------------------------------------------------

      pp.runpp(
         net,
         algorithm="nr",
         init="flat",
         calculate_voltage_angles=True,
         enforce_q_lims=True,
         max_iteration=100,
         numba=False
      )




      # --------------------------------------------------
      # 11. Resultater
      # --------------------------------------------------

      results = net.res_bus[
         [
               "vm_pu",
               "va_degree",
               "p_mw",
               "q_mvar"
         ]
      ].copy()

      reverse_bus_map = {
         pp_index: bus_number
         for bus_number, pp_index in bus_map.items()
      }

      results.insert(
         0,
         "bus_id",
         [
               reverse_bus_map[index]
               for index in results.index
         ]
      )

      #------------------------------------------------
      #------------------------------------------------
      # FYLL INN DENNE UNDER; SÅ SKAL KODEN FUNGERE :)
      #------------------------------------------------
      #------------------------------------------------

      #---------------Loader løsningen som et eget object under hovednettet-----------
      grid.solution = grid.__class__.Solution(
            volt=np.array(results["vm_pu"]),
            angle=np.radians(np.array(results["va_degree"])),   # radianer, som NR, DC og FD
            iterasjoner=None,
            mismatch=None,
            konvergerte=None,
            flow_in_line=None,
            pv_to_pq_generators=None,
            power=np.array(results["p_mw"]),
            qower=np.array(results["q_mvar"]),
            type="PP_NR"
      )
   #---------HOVEDFUNKSJON-----------------------------------
   run_excel_with_pandapower(excel_file)
#---------------validerer nettet med pandapower--------------
