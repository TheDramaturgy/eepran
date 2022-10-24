import core.topology 
import core.link 
import core.node 
import core.model 
import core.drc
import logging
import time

# ---- Logging Configuration -----
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter(
        '%(asctime)s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

# ----- Topology Definition -----
topo = core.topology.Topology("data/T2_200_BS_usage.csv")

topo.add_hardware(identifier=1, cpu=64, power_consumption=225)
topo.add_hardware(identifier=2, cpu=56, power_consumption=400)
topo.add_base_station(identifier=1, num_rf_chains=25, num_sectors=3, 
                      transmission_power=40, static_power_consumption=260,
                      rf_chain_power_consumption=1, power_amplifier_efficiency=0.25)


topo.load_nodes_for_eepran('data/EEPRAN_T2_200_nodes.json')
topo.load_links_for_eepran('data/EEPRAN_T2_200_links.json')

topo.generate_routes(origin_node='node0')
topo.export_routes('data/routes_200.json')
# topo.import_routes_from_json('data/routes_5.json')

model, centralization_constraint = core.model.build_eepran_model(topo)

model.solve()

# ---------------------------------------------------------------
# -------------------- Solution Presentation --------------------
# ---------------------------------------------------------------

print('----------------------------------------')
print('Objective Value: {} [w]'.format(model.solution.get_objective_value()))
print('Centralization: {}'.format(model.solution.get_value(centralization_constraint.left_expr)))
print('----------------------------------------')

# Print selected decision variables
logging.debug('----- Activated Decision Variables:')
for key in model.x:
    if model.x[key].solution_value != 0:
        logging.debug("route={}, drc={}, bs={} -> {}".format(key.route_id, key.drc_id, key.bs_key, 
                                                             model.x[key].solution_value))

logging.debug('---- Centralization Locations:')
for key in model.z:
    if model.z[key].solution_value != 0:
        logging.debug('node={}, function={} -> {}'.format(key.node_key, key.function_key, 
                                                          model.z[key].solution_value))


logging.debug('---- Selected DRCs:')
drc_dict = {}
for drc in core.drc.get_drc_list():
    drc_dict[drc.identifier] = drc

for key in model.x:
    if model.x[key].solution_value != 0:
        route = topo.get_route(key.route_id)
        logging.debug('{}:'.format(key.bs_key))
        logging.debug('    CU({} -> {})'.format(route.sequence[0], drc_dict[key.drc_id].fs_cu))
        logging.debug('    DU({} -> {})'.format(route.sequence[1], drc_dict[key.drc_id].fs_du))

