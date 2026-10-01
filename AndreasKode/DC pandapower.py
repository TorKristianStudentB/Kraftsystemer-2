import pandas as pd
import pandapower as pp
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))
from GridMaker.Imports import MakeGrid

grid = MakeGrid(ROOT / "Grid" / "test_trøndelagsnettet.xlsx")

Sbase = grid.Base.Sbase

for b in grid.bus:
        print(b.busNumber, b.Name, b.Vbase, "kV", "P_gen=", b.P_gen * Sbase, "P_load=", b.P_load * Sbase)
net = pp.create_empty_network(name="Trøndelag", sn_mva=Sbase)



bus_id_map = {}
for b in grid.bus:
    pp_bus = pp.create_bus(net, vn_kv=b.Vbase, name=b.Name)
    bus_id_map[b.busNumber] = pp_bus
    if b.P_load > 0:
        pp.create_load(net, pp_bus, p_mw=b.P_load * Sbase, q_mvar=b.Q_load * Sbase)
    if b.P_gen > 0:
        pp.create_sgen(net, pp_bus, p_mw=b.P_gen * Sbase, q_mvar=b.Q_gen * Sbase)

Vbase = {b.busNumber: b.Vbase for b in grid.bus}

for l in grid.line:
    Zbase = Vbase[l.Frombus]**2 / Sbase
    pp.create_line_from_parameters(
        net, from_bus=bus_id_map[l.Frombus], to_bus=bus_id_map[l.Tobus],
        length_km=1.0,
        r_ohm_per_km=l.R * Zbase,
        x_ohm_per_km=l.X * Zbase,
        c_nf_per_km=0.0, max_i_ka=1.0, name=l.Name,
    )


for t in grid.trafo:
    hv, lv = (t.Frombus, t.Tobus) if Vbase[t.Frombus] >= Vbase[t.Tobus] else (t.Tobus, t.Frombus)

    pp.create_transformer_from_parameters(
        net,
        hv_bus=bus_id_map[hv],
        lv_bus=bus_id_map[lv],
        sn_mva=Sbase,
        vn_hv_kv=Vbase[hv],
        vn_lv_kv=Vbase[lv],
        vk_percent=abs(complex(t.R, t.X)) * 100,
        vkr_percent=t.R * 100,
        pfe_kw=0,
        i0_percent=0,
        name=t.Name,
    )

# Setter den største generatoren som slack-bus
slack = next(b for b in grid.bus if b.busNumber == 30)
pp.create_ext_grid(net, bus_id_map[slack.busNumber])

pp.rundcpp(net)

print(net.res_bus[["va_degree"]])
print(net.res_line[["p_from_mw", "p_to_mw"]])#, "loading_percent"]])
                    
                

                    