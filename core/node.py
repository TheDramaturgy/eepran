class Node:
    def __init__(self, number: int, hardwares: list,  
                 static_percentage: float, base_stations: list) -> None:
        self.number = number
        self.hardwares = hardwares
        self.base_stations = base_stations
        self.static_percentage = static_percentage

        self.hardwares_key_to_id = {}
        for idx, value in enumerate(self.get_hardware_keys()):
            self.hardwares_key_to_id[value] = self.hardwares[idx]
        
        self.base_stations_key_to_id = {}
        for idx, value in enumerate(self.get_base_station_keys()):
            self.base_stations_key_to_id[value] = self.base_stations[idx]
    
    def has_base_station(self) -> bool:
        if len(self.base_stations) > 0:
            return True
        return False
    
    def has_hardware(self) -> bool:
        if len(self.hardwares) > 0:
            return True
        return False

    def get_hardware_keys(self) -> list:
        return ['node{}_hw{}'.format(self.number, idx) for idx in range(1, len(self.hardwares)+1)]
    
    def get_base_station_keys(self) -> list:
        return ['node{}_bs{}'.format(self.number, idx) for idx in range(1, len(self.base_stations)+1)]

    def get_hardware_type_identifiers(self) -> list:
        return self.hardwares

    def get_base_station_identifiers(self) -> int:
        return self.base_stations

    def get_hardware_identifier(self, key: str) -> int:
        return self.hardwares_key_to_id[key]
    
    def get_base_station_identifier(self, key: str) -> int:
        return self.base_stations_key_to_id[key]

class BaseStation:
    def __init__(self, num_rf_chains: int, num_sectors: int, transmission_power: float,
                 static_power_consumption: float, rf_chain_power_consumption: float,
                 power_amplifier_efficiency: float) -> None:
        self.num_rf_chains = num_rf_chains
        self.num_sectors = num_sectors
        self.transmission_power = transmission_power
        self.static_power_consumption = static_power_consumption
        self.rf_chain_power_consumption = rf_chain_power_consumption
        self.power_amplifier_efficiency = power_amplifier_efficiency

class Hardware:
    def __init__(self, cpu: int, power_consumption: float) -> None:
        self.num_cpu_cores = cpu
        self.power_consumption = power_consumption