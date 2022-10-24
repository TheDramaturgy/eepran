class Link:
    def __init__(self, port_capacity: int, max_ports: int, delay: float, 
                 node1, is_node1_switch: bool, node2, is_node2_switch: bool,
                 pluggable_transceiver_power_consumption: float,
                 switch_port_power_consumption: float):
        self.port_capacity = port_capacity
        self.max_ports = max_ports
        self.delay = delay
        self.node1 = node1
        self.is_node1_switch = is_node1_switch
        self.node2 = node2
        self.is_node2_switch = is_node2_switch
        self.pluggable_transceiver_power_consumption = pluggable_transceiver_power_consumption
        self.switch_port_power_consumption = switch_port_power_consumption
    

    def __str__(self, long: bool = False) -> str:
        return '({}, {}) - port: {}, {}GB, {}ms, {}+{}w'.format(
                self.node1, self.node2, self.max_ports, self.port_capacity,
                self.delay, self.pluggable_transceiver_power_consumption,
                self.switch_port_power_consumption)
        # return '({}, {})'.format(self.node1, self.node2)
    
    def get_power_consumption(self) -> float:
        """
        Calculate the power consumption of a single link

        Important
        ---------

        Check if capacity has not been exceeded!
        """

        power_consumption = 2 * self.pluggable_transceiver_power_consumption
        if self.is_node1_switch:
            power_consumption += self.switch_port_power_consumption
        if self.is_node2_switch:
            power_consumption += self.switch_port_power_consumption
        
        return power_consumption