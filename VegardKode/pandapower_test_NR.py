import pandapower as pp

## Newton Raphson ved bruk av PandaPower sin automatiske solver ##


# Lag tomt nett
net = pp.create_empty_network()

# Lag busser
bus1 = pp.create_bus(net, vn_kv=110, name="Bus 1")
bus2 = pp.create_bus(net, vn_kv=110, name="Bus 2")

# Slack bus / eksternt nett
pp.create_ext_grid(net, bus=bus1, vm_pu=1.0)

# Last
pp.create_load(net, bus=bus2, p_mw=50, q_mvar=10)

# Linje
pp.create_line_from_parameters(
    net,
    from_bus=bus1,
    to_bus=bus2,
    length_km=10,
    r_ohm_per_km=0.05,
    x_ohm_per_km=0.4,
    c_nf_per_km=0,
    max_i_ka=1
)

# Kjør Newton-Raphson lastflyt
pp.runpp(net, algorithm="nr")

print(net.res_bus)