import json
import pandas
import itertools
import re
import logging
import time
from core.link import *
from core.graph import *
from core.node import *
from core.route import *

class Topology:
    def __init__(self, usage_csv: str):
        self.__usage_df = pandas.read_csv(usage_csv)
        self.__base_station_keys = None
        self.__base_stations = {}
        self.__node_levels = {}
        self.__hardware_keys = None
        self.__hardwares = {}
        self.__nodes = {}
        self.__routes = []
        self.__id_to_route = {}
        self.__links = None
        self.__graph = None


    def __process_links_from_generator(self, node_names: list, port_capacities: list,
                                 num_links: list, delays: list, 
                                 pluggable_transceivers_power_consumption: list,
                                 switch_ports_power_consumption: list) -> None:
        # Sorting the values guarantee that we find all links from a level before changing to 
        # next in one iteration over links_df
        self.__links_df.sort_values(by=self.__links_df.columns[0], inplace=True)

        # Parameter values will be attributed according 
        # to node level in the hierarchical topology
        self.__node_levels = {0: [0], 1: []}
        current_node_level = 1
        for idx, row in self.__links_df.iterrows():
            upper_node_level = self.__node_levels[current_node_level-1]
            if row.values[0] not in upper_node_level:
                # -- We changed level --
                current_node_level += 1
                upper_node_level = self.__node_levels[current_node_level-1]
                self.__node_levels[current_node_level] = []

            # -- We are in current level --
            # Adding destination node to current level list
            self.__node_levels[current_node_level].append([node for node in row.values 
                                                                 if node not in upper_node_level])

            # Adding new link to the list
            capacity_idx = min(current_node_level-1, len(port_capacities)-1)
            num_links_idx = min(current_node_level-1, len(num_links)-1)
            delay_idx = min(current_node_level-1, len(delays)-1)
            ptpc_idx = min(current_node_level-1, len(pluggable_transceivers_power_consumption)-1)
            sppc_idx = min(current_node_level-1, len(switch_ports_power_consumption)-1)
            new_link = Link(port_capacities[capacity_idx], num_links[num_links_idx], 
                            delays[delay_idx], node_names[row[0]], True, 
                            node_names[row[1]], True,
                            pluggable_transceivers_power_consumption[ptpc_idx],
                            switch_ports_power_consumption[sppc_idx])

            link_key_1 = (node_names[row[0]], node_names[row[1]])
            link_key_2 = (node_names[row[1]], node_names[row[0]])

            self.__links[str(link_key_1)] = new_link
            self.__links[str(link_key_2)] = new_link
            

    def __process_links_from_nodes(self) -> None:
        for key in self.__nodes.keys():
            node = self.__nodes[key]
            if not node.has_base_station():
                continue
            
            for hw in node.get_hardware_keys():
                link_key_1 = (key, hw)
                link_key_2 = (hw, key)
                new_link = Link(10, 8, 0.0, key, True, hw, False, 10.0, 4.2)
                self.__links[str(link_key_1)] = new_link
                self.__links[str(link_key_2)] = new_link
            
            for bs in node.get_base_station_keys():
                link_key_1 = (key, bs)
                link_key_2 = (bs, key)
                new_link = Link(10, 8, 0.0, key, True, bs, False, 10.0, 4.2)
                self.__links[str(link_key_1)] = new_link
                self.__links[str(link_key_2)] = new_link


    def __construct_graph(self) -> None:
        self.__graph = Graph()

        links = set(link for link in self.__links.values())
        for link in links:
            self.__graph.add_edge(link.node1, link.node2, link.delay)

    
    def __find_crosshaul_routes(self, path: list) -> list:
        """
        Generates routes for all possible combinations of crosshaul of the given path.
        """
        # Converting Nodes to Indexes
        # Example:
        #   ['node1', 'node2', 'node4', 'node5'] -> [0, 1, 2, 3]
        path_indexes = [idx for idx, _ in enumerate(path)]

        # Size 2 combinations in chain format
        # Example:
        #   [0, 1, 2, 3] -> [(0, 1), (1, 2), (2, 3)]
        subsets = [subset for subset in itertools.combinations(path_indexes, 2)
                        if subset[1] - subset[0] == 1]

        # All combinations of the subsets
        # Example:
        #   [(0, 1), (1, 2), (2, 3)] -> [[(0, 1)], [(1, 2)], ..., [(0, 1), (1, 2)],
        #    [(0, 1), (2, 3)], ..., [(0, 1), (1, 2), (2, 3)]]
        subsets = [list(subset) for L in range(len(subsets)+1) 
                        for subset in itertools.combinations(subsets, L)]
        subsets = subsets[1:]

        # Get only the subsets that forms a chain
        # Example:
        # [[(0, 1)], [(1, 2)], ..., [(0, 1), (1, 2)], [(1, 2), (2, 3)], 
        #  ..., [(1, 2), (2, 3), (3, 4)], [(0, 1), (1, 2), (2, 3), (3, 4)]]
        chained_subsets = []
        for subset in subsets:
            should_remain = True
            for idx in range(len(subset)-1):
                if(subset[idx][-1] != subset[idx+1][0]):
                    should_remain = False
            if should_remain:
                chained_subsets.append(subset)

        # Combine chained subsets into paths from start to end
        # Example:
        #   path_len_2 = [[(0, 1)], [(1, 2), (2, 3), (3, 4)]]
        #   path_len_3 = [[(0, 1)], [(1, 2), (2, 3)], [(3, 5)]]
        routes_len_1 = [[route] for route in chained_subsets if len(route) == len(path)-1]
        routes_len_2 = []
        routes_len_3 = []
        for subset_a in chained_subsets:
            for subset_b in chained_subsets:
                if (subset_a[-1][-1] == subset_b[0][0] and 
                        len(subset_a) + len(subset_b) == len(path)-1):
                    routes_len_2.append([subset_a, subset_b])
                for subset_c in chained_subsets:
                    if (subset_a[-1][-1] == subset_b[0][0] and 
                            subset_b[-1][-1] == subset_c[0][0] and
                            len(subset_a) + len(subset_b) + len(subset_c) == len(path)-1):
                        routes_len_3.append([subset_a, subset_b, subset_c])

        # Converting Indexes back to Nodes
        routes_len_1 = [[[(path[i], path[j]) for i, j in xhaul] 
                            for xhaul in route] for route in routes_len_1]
        routes_len_2 = [[[(path[i], path[j]) for i, j in xhaul] 
                            for xhaul in route] for route in routes_len_2]
        routes_len_3 = [[[(path[i], path[j]) for i, j in xhaul] 
                            for xhaul in route] for route in routes_len_3]
        
        return routes_len_3 + routes_len_2 + routes_len_1

    
    def __process_crosshaul_routes(self, routes: list) -> list:
        """
        Make all crosshauls (except Fronthaul) of each route end in a hardware, 
        and set empty list for suppressed crosshauls.
        """

        # Midhaul
        for route in routes.copy():
            if len(route) < 2:
                continue
            
            routes.remove(route)

            midhaul = route[-2]
            endpoint_node_key = midhaul[-1][-1]
            endpoint_node = self.__nodes[endpoint_node_key]
            for hw in endpoint_node.get_hardware_keys():
                new_route = route.copy()
                new_route[-2] = midhaul + [(endpoint_node_key, hw)]
                routes.append(new_route)
        
        # Backhaul
        for route in routes.copy():
            if len(route) < 3:
                continue

            routes.remove(route)
            
            backhaul = route[-3]
            endpoint_node_key = backhaul[-1][-1]
            endpoint_node = self.__nodes[endpoint_node_key]
            for hw in endpoint_node.get_hardware_keys():
                new_route = route.copy()
                new_route[-3] = backhaul + [(endpoint_node_key, hw)]
                routes.append(new_route)

        # Empty Crosshauls
        for route in routes.copy():
            if len(route) < 2:
                routes.remove(route)
                new_route = [[], [], route[-1]]
                routes.append(new_route)
            elif len(route) < 3:
                routes.remove(route)
                new_route = [[], route[-2], route[-1]]
                routes.append(new_route)

        return routes


    def set_links_from_generator(self, links_csv: str, node_names: list,  port_capacities: list,
                                 num_links: list, delays: list, 
                                 pluggable_transceivers_power_consumption: list,
                                 switch_ports_power_consumption: list) -> None:
        """
        Import link information created by the generator for hierarchical topology.

        Parameters
        ----------

        links_csv : str
            The path to the csv file with links information, created by the generator.
        capacities : list
            A list of link capacity values in hierarchical level order, from core to leaf nodes.
        delays : list
            A list of link delay values in hierarchical level order, from core to leaf nodes.

        """
        self.__links = {}
        self.__links_df = pandas.read_csv(links_csv)
        self.__process_links_from_generator(node_names, port_capacities, num_links,
                                            delays, pluggable_transceivers_power_consumption,
                                            switch_ports_power_consumption)
        self.__process_links_from_nodes()
    

    def load_nodes_for_eepran(self, nodes_path: str, id_pattern: str = 'node{}') -> None:
        """
        Load nodes information created by the topology generator and processed for EEPRAN.

        Parameters
        ----------

        nodes_path : str
            The path to the json file with nodes information, created by the topology generator
            and processed for the EEPRAN.
        id_pattern : str
            The pattern used to identify the nodes. Default: 'node{}'

        """

        load_nodes_start = time.time()

        self.__nodes = {}
        json_input = ''
        with open(nodes_path, 'r') as node_file:
            json_input = node_file.read()

        data = json.loads(json_input)
        for node in data['nodes']:
            # Skip the core
            if node['Number'] == 0:
                continue
            
            self.__nodes[id_pattern.format(node['Number'])] = Node(
                number=node['Number'], hardwares=node['Hardwares'], 
                static_percentage=node['StaticPercentage'],
                base_stations=node['BaseStations']
            )

        load_nodes_end = time.time()
        logging.info('Node Information Loaded: {}s'.format(load_nodes_end - load_nodes_start))
    
    def load_links_for_eepran(self, links_path: str, node_id_pattern: str = 'node{}') -> None:
        """
        Load links information created by the topology generator and processed for EEPRAN.

        Parameters
        ----------

        links_path : str
            The path to the json file with links information, created by the topology generator
            and processed for the EEPRAN.
        node_id_pattern : str
            The pattern used to identify the nodes, same used in topology.load_nodes_for_eepran(). 
            Default: 'node{}'

        """

        load_links_start = time.time()

        self.__links = {}
        json_input = ''
        with open(links_path, 'r') as link_file:
            json_input = link_file.read()

        data = json.loads(json_input)
        for link in data['links']:
            node1_name = node_id_pattern.format(link['Node1'])
            node2_name = node_id_pattern.format(link['Node2'])

            new_link = Link(
                port_capacity=link['PortCapacity'],
                max_ports=link['NumLinks'],
                delay=link['Delay'],
                node1=node1_name,
                is_node1_switch=True,
                node2=node2_name,
                is_node2_switch=True,
                pluggable_transceiver_power_consumption=link['PluggableTransceiverPower'],
                switch_port_power_consumption=link['SwitchPortPower']
            )

            link_key1 = (node1_name, node2_name)
            link_key2 = (node2_name, node1_name)

            self.__links[str(link_key1)] = new_link
            self.__links[str(link_key2)] = new_link
        
        self.__process_links_from_nodes()

        logging.debug("Processed Links:")
        for link in set(self.__links.values()):
            logging.debug("    {}".format(link))
        
        load_links_end = time.time()
        logging.info('Link Information Loaded: {}s'.format(load_links_end - load_links_start))
            

    def add_hardware(self, identifier: int, cpu: int, power_consumption: float) -> None:      
        self.__hardwares[identifier] = Hardware(cpu, power_consumption)


    def add_base_station(self, identifier: int, num_rf_chains: int, num_sectors: int, 
                        transmission_power: float, static_power_consumption: float, 
                        rf_chain_power_consumption: float,
                        power_amplifier_efficiency: float) -> None:
        self.__base_stations[identifier] = BaseStation(num_rf_chains, num_sectors, 
                                                              transmission_power, 
                                                              static_power_consumption, 
                                                              rf_chain_power_consumption,
                                                              power_amplifier_efficiency)
    

    def set_nodes_from_dict(self, nodes: dict) -> None:
        self.__nodes = nodes.copy()

    
    def set_links_from_list(self, links: dict) -> None:
        self.__links = links


    def get_links(self) -> list:
        return self.__links.keys()

    
    def get_link(self, key: str) -> Link:
        return self.__links[key]

    
    def get_routes(self) -> list:
        return self.__routes


    def get_route(self, identifier: int) -> Route:
        if len(self.__id_to_route) == 0:
            for route_idx in range(len(self.__routes)):
                route = self.__routes[route_idx]
                self.__id_to_route[route.identifier] = route_idx
        
        return self.__routes[self.__id_to_route[identifier]]


    def get_node(self, key: str) -> Node:
        return self.__nodes[key]

    
    def get_hardware_keys(self) -> list:
        if self.__hardware_keys is None:
            self.__hardware_keys = [hw for node in self.__nodes.values() for hw in node.get_hardware_keys()]
        return self.__hardware_keys 


    def get_hardware_by_id(self, identifier: int) -> Hardware:
        return self.__hardwares[identifier]


    def get_hardware_by_key(self, key: str) -> Hardware:
        result = re.search('(?:(?!_).)*', key)
        node = self.get_node(result.group())
        hw_id = node.get_hardware_identifier(key)
        return self.__hardwares[hw_id]


    def get_base_station(self, key: int) -> BaseStation:
        return self.__base_stations[key]

    
    def get_node_keys(self) -> list:
        return self.__nodes.keys()


    def get_base_station_keys(self) -> list:
        if self.__base_station_keys is None:
            self.__base_station_keys = [key for node in self.__nodes.values() for key in node.get_base_station_keys()]
        return self.__base_station_keys

    
    def generate_routes(self, origin_node) -> None:
        
        route_gen_start = time.time()
        self.__construct_graph()

        destinations = []
        for key in self.__nodes.keys():
            node = self.__nodes[key]
            if node.has_base_station():
                for bs in node.get_base_station_keys():
                    destinations.append(bs)

        for destination in destinations:
            self.__graph.find_all_paths(origin_node, destination)

        self.__routes = []
        idx = 1
        for path in self.__graph.paths:
            routes_aux = self.__find_crosshaul_routes(path)
            for route in self.__process_crosshaul_routes(routes_aux):
                delay_backhaul = sum([self.__links[str(link)].delay for link in route[0]])
                delay_midhaul   = sum([self.__links[str(link)].delay for link in route[1]])
                delay_fronthaul  = sum([self.__links[str(link)].delay for link in route[2]])
                sequence = [xhaul[-1][-1] if len(xhaul) > 0 else origin_node for xhaul in route]
                self.__routes += [Route(idx, path[0], path[-1], sequence, route[2], route[1], 
                                        route[0], delay_fronthaul, delay_midhaul, delay_backhaul)]
                idx += 1
        
        route_gen_end = time.time()
        logging.info('Routes Generated: {}s'.format(route_gen_end - route_gen_start))


    def print_routes(self) -> None:
        for route in self.__routes:
            print(str(route))


    def export_routes(self, path: str) -> None:
        json_output = '[\n'
        for idx, route in enumerate(self.__routes):
            json_output += json.dumps(route.__dict__, indent=4)
            if idx < len(self.__routes) - 1:
                json_output += ','
        json_output += '\n]'
        
        with open(path, 'w') as route_file:
            route_file.write(json_output)


    def import_routes_from_json(self, path: str) -> None:
        json_input = ''
        with open(path, 'r') as route_file:
            json_input = route_file.read()
        
        routes = json.loads(json_input)
        self.__routes = []
        for route in routes:
            fronthaul = [(link[0],link[1]) for link in route['fronthaul']]
            midhaul = [(link[0],link[1]) for link in route['midhaul']]
            backhaul = [(link[0],link[1]) for link in route['backhaul']]
            self.__routes += [Route(route['identifier'], route['source'], route['target'], 
                                    route['sequence'], fronthaul, midhaul, 
                                    backhaul, route['delay_fronthaul'], 
                                    route['delay_midhaul'], route['delay_backhaul'])]
        

