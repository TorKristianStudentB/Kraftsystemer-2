from GridMaker.Imports import pp,np,excelfilepath
from GridMaker.ReadExcelGrid import MakeGrid   # direkte, ikke via Imports (unngår sirkulær import)

#--------------validerer med pandapower på DC--------------------
def validating_PP_DC(grid):   

   # definerer regionen som NO3 for å få trøndelagsområdet.
   region_buses = [b for b in grid.bus if b.bidz == "NO3"]
   region_bus_ids = [b.busNumber for b in region_buses]
   region_lines = [l for l in grid.line if l.Frombus in region_bus_ids and l.Tobus in region_bus_ids]
   region_trafos = [t for t in grid.trafo if t.Frombus in region_bus_ids and t.Tobus in region_bus_ids]


   net = pp.create_empty_network(name="Nordic490 -NO3")

   bus_id_map = {}
   for b in region_buses:
      pp_bus = pp.create_bus(net, vn_kv=b.Vbase, name=b.Name)
      bus_id_map[b.busNumber] = pp_bus
      #----effekt ligger i pu i grid-objektet (MakeGrid deler på Sbase), pandapower vil ha MW -> ganger med Sbase----
      if b.P_load > 0:
         pp.create_load(net, pp_bus, p_mw=b.P_load*grid.Base.Sbase, q_mvar=b.Q_load*grid.Base.Sbase)
      if b.P_gen > 0:
         pp.create_sgen(net, pp_bus, p_mw=b.P_gen*grid.Base.Sbase, q_mvar=b.Q_gen*grid.Base.Sbase)

   Sbase = 100  # MVA, fra bus-arket

   for l in region_lines:
      bus = next(b for b in region_buses if b.busNumber == l.Frombus)
      Zbase = bus.Vbase**2 / Sbase
      pp.create_line_from_parameters(
         net, from_bus=bus_id_map[l.Frombus], to_bus=bus_id_map[l.Tobus],
         length_km=1.0,
         r_ohm_per_km=l.R * Zbase,
         x_ohm_per_km=l.X * Zbase,
         c_nf_per_km=0.0, max_i_ka=1.0, name=l.Name,
      )


   for t in region_trafos:
      hv_bus = next(b for b in region_buses if b.busNumber == t.Frombus)
      lv_bus = next(b for b in region_buses if b.busNumber == t.Tobus)

      pp.create_transformer_from_parameters(
         net,
         hv_bus=bus_id_map[hv_bus.busNumber],
         lv_bus=bus_id_map[lv_bus.busNumber],
         sn_mva=Sbase,
         vn_hv_kv=hv_bus.Vbase,
         vn_lv_kv=lv_bus.Vbase,
         vk_percent=abs(complex(t.R, t.X)) * 100,
         vkr_percent=t.R * 100,
         pfe_kw=0,
         i0_percent=0,
         name=t.Name,
      )

   # Setter den største generatoren som slack-bus
   slack = next(b for b in region_buses if b.busNumber == 30)
   pp.create_ext_grid(net, bus_id_map[slack.busNumber])

   pp.rundcpp(net)




   #------------------------------------------------
   #------------------------------------------------
   # FYLL INN DENNE UNDER; SÅ SKAL KODEN FUNGERE :)
   #------------------------------------------------
   #------------------------------------------------

   #---------------Loader løsningen som et eget object under hovednettet-----------
   grid.solution = grid.__class__.Solution(
         volt=np.ones(len(net.res_bus[["va_degree"]])),
         angle=np.radians(np.array(net.res_bus["va_degree"])),   # radianer, som NR, DC og FD
         iterasjoner=0,
         mismatch=None,
         konvergerte=0,
         flow_in_line=np.array(net.res_line["p_from_mw"]),
         pv_to_pq_generators=None,
         power=None,
         qower=None,
         type="PP_DC"
   )
   #---------------Loader løsningen som et eget object under hovednettet-----------
#--------------validerer med pandapower på DC--------------------                            