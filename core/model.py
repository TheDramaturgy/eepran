from collections import defaultdict, namedtuple
from docplex.mp.constr import AbstractConstraint
from docplex.mp.model import Model
from core.topology import *
from core.link import *
from core.node import *
from core.route import *
import core.drc as package_drc
import time

def build_eepran_model(topo: Topology, centralization_cap: int = 0) -> {Model, AbstractConstraint}:
    model = Model(name='EEP-Ran Problem', log_output=True)
    logging.info('Model Creation Time:')

    # -----------
    # Define Data
    # -----------

    data_defining_start = time.time()

    splits = package_drc.get_drc_list()
    drc_dict = {}
    for drc in splits:
        drc_dict[drc.identifier] = drc
    vnf_cpu_usage = package_drc.get_vnf_dict()
    virtual_network_functions = vnf_cpu_usage.keys()
    maximum_centralization = len(virtual_network_functions) * len(topo.get_base_station_keys())
    
    EMPTY_EXPR = model.linear_expr()
    INTEGER_FEASIBILITY_TOLERANCE = 1 / maximum_centralization

    data_defining_end = time.time()
    logging.info('    Data Definition: {}s'.format(data_defining_end - data_defining_start))

    # --------------------------
    # Define Decision Variable X
    # --------------------------

    var_definition_start = time.time()

    # list with keys for decision variables
    DecisionVariableKey = namedtuple('DecisionVariableKey', ['route_id', 'drc_id', 'bs_key'])
    decision_var_keys = [
        DecisionVariableKey(route.identifier, drc.identifier, bs_key)
        for route in topo.get_routes()
        for drc in splits
        for bs_key in topo.get_base_station_keys()
        if route.is_destination(bs_key)
        and drc.num_needed_nodes() == route.qty_nodes()
        and route.delay_backhaul <= drc.delay_bh
        and route.delay_midhaul <= drc.delay_mh
        and route.delay_fronthaul <= drc.delay_fh
    ]

    # list with keys for ceil variables in psi_2
    CeilVariableKey = namedtuple('CeilVariableKey', ['node_key', 'function_key'])
    ceil_var_keys = [CeilVariableKey(node_key, function_key) 
                     for node_key in topo.get_node_keys() 
                     for function_key in virtual_network_functions
                     if topo.get_node(node_key).has_hardware()]
    
    model.x = model.binary_var_dict(
        keys=decision_var_keys, 
        name=lambda vk: 'x_path{}_drc{}_{}'.format(vk.route_id, vk.drc_id, vk.bs_key)
    )
    model.y = model.integer_var_dict(keys=topo.get_hardware_keys(), name='y')
    model.z = model.integer_var_dict(keys=ceil_var_keys, name='z')

    var_definition_end = time.time()
    logging.info('    Variables Definition: {}s'.format(var_definition_end - var_definition_start))

    # -------------------------
    # Define Objective Function
    # -------------------------

    objective_function_start = time.time()

    # ----- Optimized -----
    ran_power_consumption = model.linear_expr()
    base_station_power_expression = model.linear_expr()
    dynamic_power_expression = model.linear_expr()
    static_power_consumptions = {}
    psi_1 = {}
    for key in decision_var_keys:
        route = topo.get_route(key.route_id)

        for function in virtual_network_functions:
            if route.has_backhaul() and function in drc_dict[key.drc_id].fs_cu:
                node_key = route.get_backhaul_node_key()
                hw_key = route.get_backhaul_hardware_key()

                hw = topo.get_hardware_by_key(hw_key)
                node = topo.get_node(node_key)
                dynamic_power_consumption = hw.power_consumption * (1 - node.static_percentage)

                dynamic_power_expression.add_term(
                    model.x[key], 
                    (vnf_cpu_usage[function] * dynamic_power_consumption / hw.num_cpu_cores)
                )

                psi_1.setdefault(hw_key, model.linear_expr()).add_term(
                    model.x[key],
                    1.0 / maximum_centralization
                )

                if hw_key not in static_power_consumptions.keys():
                    static_power_consumptions[hw_key] = hw.power_consumption * node.static_percentage

            if route.has_midhaul() and function in drc_dict[key.drc_id].fs_du:
                node_key = route.get_midhaul_node_key()
                hw_key = route.get_midhaul_hardware_key()

                hw = topo.get_hardware_by_key(hw_key)
                node = topo.get_node(node_key)
                dynamic_power_consumption = hw.power_consumption * (1 - node.static_percentage)

                dynamic_power_expression.add_term(
                    model.x[key], 
                    (vnf_cpu_usage[function] * dynamic_power_consumption / hw.num_cpu_cores)
                )

                psi_1.setdefault(hw_key, model.linear_expr()).add_term(
                    model.x[key],
                    1.0 / maximum_centralization
                )

                if hw_key not in static_power_consumptions.keys():
                    static_power_consumptions[hw_key] = hw.power_consumption * node.static_percentage

        
        # Base Station Consumption
        node_key = route.get_fronthaul_node_key()
        node = topo.get_node(node_key)

        base_station_key = route.get_target_base_station()
        base_station_id = node.get_base_station_identifier(base_station_key)
        base_station = topo.get_base_station(base_station_id)

        bs_power_consumption = base_station.num_sectors * (
            (base_station.transmission_power / base_station.power_amplifier_efficiency) + 
            base_station.num_rf_chains * base_station.rf_chain_power_consumption +
            base_station.static_power_consumption 
        )

        base_station_power_expression.add_term(
            model.x[key],
            (1.0 - drc_dict[key.drc_id].bs_relief) * bs_power_consumption
        )

    ran_power_consumption.add(base_station_power_expression)
    ran_power_consumption.add(dynamic_power_expression)
    for hw_key in topo.get_hardware_keys():
        model.add_constraint(model.y[hw_key] - psi_1[hw_key] >= 0.0, 
                                'low_ceil_restriction_{}'.format(hw_key))
        model.add_constraint(model.y[hw_key] - psi_1[hw_key] <= 1.0 - INTEGER_FEASIBILITY_TOLERANCE, 
                                'high_ceil_restriction_{}'.format(hw_key))

        ran_power_consumption.add_term(model.y[hw_key], static_power_consumptions[hw_key])

    # Network Power Consumption and Capacity Constraint
    link_usage_expressions = {}
    for key in decision_var_keys:
        route = topo.get_route(key.route_id)

        for link_key in route.get_backhaul_links():
            link_usage_expressions.setdefault(link_key, model.linear_expr()).add_term(
                model.x[key],
                drc_dict[key.drc_id].bandwidth_bh
            ) 

        for link_key in route.get_midhaul_links():
            link_usage_expressions.setdefault(link_key, model.linear_expr()).add_term(
                model.x[key],
                drc_dict[key.drc_id].bandwidth_mh
            )

        for link_key in route.get_fronthaul_links():
            link_usage_expressions.setdefault(link_key, model.linear_expr()).add_term(
                model.x[key],
                drc_dict[key.drc_id].bandwidth_fh
            )
        
    net_power_consumption = model.linear_expr()
    for link_key, expression in link_usage_expressions.items():
        link = topo.get_link(link_key)

        # Capacity Constraint
        model.add_constraint(expression / link.port_capacity <= link.max_ports, 
                                'qty_ports_link_{}'.format(link_key))

        # Network Power Consumption
        is_node1_switch = 1 if link.is_node1_switch else 0
        is_node2_switch = 1 if link.is_node2_switch else 0
        net_power_consumption += (
            (expression / link.port_capacity) * (
                (2 * link.pluggable_transceiver_power_consumption) +
                (link.switch_port_power_consumption * (is_node1_switch + is_node2_switch))
            )
        )

    # ----- Original -----
    # # RAN Power Consumption
    # ran_power_consumption = model.linear_expr()
    # base_station_power_expression = model.linear_expr()
    # dynamic_power_expression = model.linear_expr()
    # for node_key in topo.get_node_keys():
    #     node = topo.get_node(node_key)
    #     qty_hardwares = len(node.get_hardware_keys())
    #     dynamic_power_function = model.linear_expr()

    #     # vBBU Power Consumption
    #     for idx in range(qty_hardwares):
    #         hw_id = node.get_hardware_type_identifiers()[idx]
    #         hw_key = node.get_hardware_keys()[idx]
    #         hw = topo.get_hardware_by_id(hw_id)
    #         dynamic_power_consumption = hw.power_consumption * (1 - node.static_percentage)
    #         psi_1 = model.linear_expr()
        
    #         for function in virtual_network_functions:
    #             for key in decision_var_keys:
    #                 if topo.get_route(key.route_id).contains(hw_key) and (
    #                         (topo.get_route(key.route_id).is_cu(hw_key) and 
    #                         function in drc_dict[key.drc_id].fs_cu) or
    #                         (topo.get_route(key.route_id).is_du(hw_key) and 
    #                         function in drc_dict[key.drc_id].fs_du)) :
    #                     dynamic_power_function += (
    #                         model.x[key] * vnf_cpu_usage[function] * 
    #                         dynamic_power_consumption / hw.num_cpu_cores
    #                     )

    #                     if key == DecisionVariableKey(2, 6, 'node1_bs1'):
    #                         print('----------------(!)--------------------')
    #                         print((
    #                         model.x[key] * vnf_cpu_usage[function] * 
    #                         dynamic_power_consumption / hw.num_cpu_cores
    #                         ))
                        
    #                 if topo.get_route(key.route_id).contains(hw_key) and (
    #                         (topo.get_route(key.route_id).is_cu(hw_key) and 
    #                         function in drc_dict[key.drc_id].fs_cu) or
    #                         (topo.get_route(key.route_id).is_du(hw_key) and 
    #                         function in drc_dict[key.drc_id].fs_du)):
    #                     psi_1 += model.x[key] / maximum_centralization
            
    #         model.add_constraint(model.y[hw_key] - psi_1 >= 0.0, 
    #                             'low_ceil_restriction_{}'.format(hw_key))
    #         model.add_constraint(model.y[hw_key] - psi_1 <= 1.0 - INTEGER_FEASIBILITY_TOLERANCE, 
    #                             'high_ceil_restriction_{}'.format(hw_key))

    #         static_power_consumption = hw.power_consumption * node.static_percentage
    #         ran_power_consumption += (model.y[hw_key] * static_power_consumption) 
        
    #     ran_power_consumption += dynamic_power_function
    #     dynamic_power_expression += dynamic_power_function

    #     # BS power Consumption
    #     if node.has_base_station():
    #         qty_base_stations = len(node.get_base_station_identifiers())
    #         for idx in range(qty_base_stations):
    #             base_station_id = node.get_base_station_identifiers()[idx]
    #             base_station_key = node.get_base_station_keys()[idx]
    #             base_station = topo.get_base_station(base_station_id)
    #             bs_power_consumption = base_station.num_sectors * (
    #                 (base_station.transmission_power / base_station.power_amplifier_efficiency) + 
    #                 base_station.num_rf_chains * base_station.rf_chain_power_consumption +
    #                 base_station.static_power_consumption 
    #             )
    #             for key in decision_var_keys:
    #                 if not topo.get_route(key.route_id).is_destination(base_station_key):
    #                     continue
    #                 ran_power_consumption += model.sum(
    #                     model.x[key] * (1.0 - drc_dict[key.drc_id].bs_relief) * bs_power_consumption 
    #                 )
    #                 base_station_power_expression += model.sum(
    #                     model.x[key] * (1.0 - drc_dict[key.drc_id].bs_relief) * bs_power_consumption 
    #                 )
    
    # # Network Power Consumption and Capacity Constraint
    # net_power_consumption = model.linear_expr()
    # for link_key in topo.get_links():
    #     link = topo.get_link(link_key)
    #     link_usage = model.linear_expr()

    #     link_usage += model.sum(
    #         model.x[key] * drc_dict[key.drc_id].bandwidth_bh
    #         for key in decision_var_keys 
    #         if topo.get_route(key.route_id).is_backhaul(link_key)
    #     ) 

    #     link_usage += model.sum(
    #         model.x[key] * drc_dict[key.drc_id].bandwidth_mh
    #         for key in decision_var_keys 
    #         if topo.get_route(key.route_id).is_midhaul(link_key)
    #     )

    #     link_usage += model.sum(
    #         model.x[key] * drc_dict[key.drc_id].bandwidth_fh
    #         for key in decision_var_keys 
    #         if topo.get_route(key.route_id).is_fronthaul(link_key)
    #     )

    #     # Capacity Constraint
    #     if not link_usage.equals(EMPTY_EXPR):
    #         model.add_constraint(link_usage / link.port_capacity <= link.max_ports, 
    #                             'qty_ports_link_{}'.format(link_key))

    #     is_node1_switch = 1 if link.is_node1_switch else 0
    #     is_node2_switch = 1 if link.is_node2_switch else 0

    #     net_power_consumption += (
    #         (link_usage / link.port_capacity) * (
    #             (2 * link.pluggable_transceiver_power_consumption) +
    #             (link.switch_port_power_consumption * (is_node1_switch + is_node2_switch))
    #         )
    #     )
    
    model.minimize(ran_power_consumption + net_power_consumption)

    objective_function_end = time.time()

    logging.info('    Objective Definition: {}s'.format(objective_function_end - objective_function_start))


    # --------------------------------
    # Define Centralization Constraint
    # --------------------------------

    centralization_function_start = time.time()

    centralization = model.linear_expr()
    for node_key in topo.get_node_keys():
        node = topo.get_node(node_key)
        if not node.has_hardware():
            continue

        # Sums BS's running the same FS in a single CR
        for function in virtual_network_functions:
            virtual_network_function_count = model.linear_expr()

            qty_hardwares = len(node.get_hardware_keys())
            for idx in range(qty_hardwares):
                hw_id = node.get_hardware_type_identifiers()[idx]
                hw_key = node.get_hardware_keys()[idx]
                hw = topo.get_hardware_by_id(hw_id)

                virtual_network_function_count += model.sum(
                    model.x[key] for key in decision_var_keys
                    if topo.get_route(key.route_id).contains(hw_key) and (
                        (topo.get_route(key.route_id).is_cu(hw_key) and 
                        function in drc_dict[key.drc_id].fs_cu) or
                        (topo.get_route(key.route_id).is_du(hw_key) and 
                        function in drc_dict[key.drc_id].fs_du)
                    )
                )

            ceil_var_key = CeilVariableKey(node_key, function)

            # Psi_2 Ceil Function Restriction
            model.add_constraint(
                model.z[ceil_var_key] - (virtual_network_function_count / maximum_centralization) >=
                0.0, 'low_ceil_restriction_{}_{}'.format(node_key, function)
            )
            model.add_constraint(
                model.z[ceil_var_key] - (virtual_network_function_count / maximum_centralization) <= 
                1.0 - INTEGER_FEASIBILITY_TOLERANCE, 
                'high_ceil_restriction_{}_{}'.format(node_key, function)
            )

            # centralization is calculated by CR (not by Hardware)
            centralization += model.sum(virtual_network_function_count - model.z[ceil_var_key])
    centralization_constraint = model.add_constraint(centralization >= centralization_cap, 
                                                     'centralization_constraint')
    
    centralization_function_end = time.time()
    logging.info('    Centralization Definition: {}s'.format(centralization_function_end - centralization_function_start))

    # ------------------------------
    # Define Single Route Constraint
    # ------------------------------

    single_route_start = time.time()

    # each bs must use a single route/drc combination
    for bs_key in topo.get_base_station_keys():
        paths_count = model.sum(model.x[key] 
                                for key in decision_var_keys 
                                if key.bs_key == bs_key)
        model.add_constraint(paths_count == 1, 'single_route_{}'.format(bs_key))

    single_route_end = time.time()
    logging.info('    Single Route Definition: {}s'.format(single_route_end - single_route_start))

    # -------------------------------
    # Define Link Capacity Constraint
    # -------------------------------

    # -> Defined in objective function

    # capacity_expressions = {}
    # # define a expression for each link
    # for link in link_list:
    #     source, destination = _min_max(link.from_node, link.to_node)
    #     capacity_expressions[(source, destination)] = model.linear_expr()

    # # sums every drc bandwidth load flowing through a link
    # for key in var_keys:
    #     link: tuple[int]
    #     for link in key.route.p1:
    #         source, destination = _min_max(link[0], link[1])
    #         capacity_expressions[(source, destination)].add_term(model.x[key], key.drc.bandwidth_bh)

    #     for link in key.route.p2:
    #         source, destination = _min_max(link[0], link[1])
    #         capacity_expressions[(source, destination)].add_term(model.x[key], key.drc.bandwidth_mh)

    #     for link in key.route.p3:
    #         source, destination = _min_max(link[0], link[1])
    #         capacity_expressions[(source, destination)].add_term(model.x[key], key.drc.bandwidth_fh)

    # # the load on every link must not exceed its capacity
    # link: Link
    # for link in link_list:
    #     source, destination = _min_max(link.from_node, link.to_node)
    #     model.add_constraint(capacity_expressions[(source, destination)] <= link.capacity, 'link capacity constraint')

    # ----------------------------
    # Define Link Delay Constraint
    # ----------------------------

    # -> Granted by decision_var_keys definition

    # delay on link must not exceed the drc requirements
    # for key in decision_var_keys:
    #     if topo.get_route(key.route_id).qty_nodes() == 3:
    #         model.add_constraint(model.x[key] * topo.get_route(key.route_id).delay_backhaul <= 
    #                              drc_dict[key.drc_id].delay_bh, 'link_delay_bh')
    #     if topo.get_route(key.route_id).qty_nodes() >= 2:
    #         model.add_constraint(model.x[key] * topo.get_route(key.route_id).delay_midhaul <= 
    #                              drc_dict[key.drc_id].delay_mh, 'link_delay_mh')
    #     model.add_constraint(model.x[key] * topo.get_route(key.route_id).delay_fronthaul <= 
    #                          drc_dict[key.drc_id].delay_fh, 'link_delay_fh')


    # ------------------------------
    # Processing Capacity Constraint
    # ------------------------------

    # for cr in computing_core.cr_dict:
    #     # Do not count the core
    #     if cr == 0:
    #         continue

    #     hardware: Hardware
    #     for hardware in computing_core.cr_dict[cr]:
    #         # sums the load of all FS's running on the CR
    #         processing_expression = model.linear_expr()
    #         for fs in fs_list:
    #             processing_expression += model.sum(model.x[key] * fs_list[fs]
    #                                                for key in var_keys
    #                                                if key.route.contains(hardware) and (
    #                                                        (key.route.is_cu(hardware) and fs in key.drc.fs_cu) or
    #                                                        (key.route.is_du(hardware) and fs in key.drc.fs_du) or
    #                                                        (key.route.is_ru(hardware) and fs in key.drc.fs_ru)))
    #         model.add_constraint(processing_expression <= hardware.cpu, 'processing capacity constraint')

    # for node_key in topo.get_node_keys():
    #     node = topo.get_node(node_key)
    #     if not node.has_hardware():
    #         continue

    #     qty_hardwares = len(node.get_hardware_keys())
    #     for idx in range(qty_hardwares):
    #         hw_id = node.get_hardware_type_identifiers()[idx]
    #         hw_key = node.get_hardware_keys()[idx]
    #         hw = topo.get_hardware_by_id(hw_id)

    #         # sums the load of all FS's running on the CR
    #         processing_expression = model.linear_expr()
    #         for function in virtual_network_functions:
    #             processing_expression += model.sum(
    #                 model.x[key] * vnf_cpu_usage[function]
    #                 for key in decision_var_keys
    #                 if (
    #                     topo.get_route(key.route_id).contains(hw_key) and (
    #                         (topo.get_route(key.route_id).is_cu(hw_key) and 
    #                         function in drc_dict[key.drc_id].fs_cu) or
    #                         (topo.get_route(key.route_id).is_du(hw_key) and 
    #                         function in drc_dict[key.drc_id].fs_du)
    #                     )
    #                 )
    #             )

    #         model.add_constraint(processing_expression <= hw.num_cpu_cores, 
    #                              'processing_capacity_{}'.format(hw_key))

    processing_function_start = time.time()

    hardware_processing_expressions = {}
    for var_key in decision_var_keys:
        route = topo.get_route(var_key.route_id)
        for hw_key in route.get_hardware_keys():
            hardware_processing_expressions.setdefault(hw_key, model.linear_expr())
            hardware_processing_expressions[hw_key] += model.sum(
                model.x[var_key] * vnf_cpu_usage[function] 
                for function in virtual_network_functions 
                if (route.is_cu(hw_key) and function in drc_dict[var_key.drc_id].fs_cu) 
                or (route.is_du(hw_key) and function in drc_dict[var_key.drc_id].fs_du) 
            )

    for key, expr in hardware_processing_expressions.items():
        hw = topo.get_hardware_by_key(key)
        model.add_constraint(expr <= hw.num_cpu_cores, 'processing_capacity_{}'.format(key))

    processing_function_end = time.time()
    logging.info('    Processing Definition: {}s'.format(processing_function_end - processing_function_start))
    
    model.export_as_lp('data/model.lp')

    return model, centralization_constraint