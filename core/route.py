from core.node import *

class Route:
    def __init__(self, identifier: int, source: str, target: str, sequence: list, fronthaul: list,
                 midhaul: list, backhaul: list, delay_fronthaul: float, delay_midhaul: float, delay_backhaul: float):
        self.identifier = identifier
        self.source = source
        self.target = target
        self.sequence = sequence
        self.fronthaul = fronthaul
        self.midhaul = midhaul
        self.backhaul = backhaul
        self.delay_fronthaul = delay_fronthaul
        self.delay_midhaul = delay_midhaul
        self.delay_backhaul = delay_backhaul


    def __hash__(self) -> int:
        hash_key = [j for i in (self.fronthaul + self.midhaul + self.backhaul + self.sequence) 
                        for j in i]
        return hash(frozenset(hash_key))


    def __str__(self) -> str:
        return ('{}: {} -- {}\n'.format(self.identifier, self.source, self.target) +
                'Sequence: {}\n'.format(self.sequence) +
                'Backhaul: {}\n  - Delay: {}\n'.format(self.backhaul, self.delay_backhaul) +
                'Midhaul: {}\n  - Delay: {}\n'.format(self.midhaul, self.delay_midhaul) +
                'Fronthaul: {}\n  - Delay: {}'.format(self.fronthaul, self.delay_fronthaul))


    def __eq__(self, other) -> bool:
        return (self.backhaul == other.backhaul and 
                self.midhaul == other.midhaul and 
                self.fronthaul == other.fronthaul and 
                self.sequence == other.sequence)


    def get_all_links(self) -> bool:
        return [str(link) for link in self.fronthaul + self.midhaul + self.backhaul]


    def get_fronthaul_links(self) -> list:
        return [str(link) for link in self.fronthaul]


    def get_midhaul_links(self) -> list:
        return [str(link) for link in self.midhaul]


    def get_backhaul_links(self) -> list:
        return [str(link) for link in self.backhaul]


    def get_hardware_keys(self) -> list:
        return [node for node in self.sequence[:2] if node != self.source]


    def get_backhaul_hardware_key(self) -> str:
        if self.has_backhaul():
            return self.backhaul[-1][1]
        return None


    def get_backhaul_node_key(self) -> str:
        if self.has_backhaul():
            return self.backhaul[-1][0]
        return None


    def get_midhaul_hardware_key(self) -> str:
        if self.has_midhaul():
            return self.midhaul[-1][1]
        return None


    def get_midhaul_node_key(self) -> str:
        if self.has_midhaul():
            return self.midhaul[-1][0]
        return None


    def get_fronthaul_hardware_key(self) -> str:
        if self.has_fronthaul():
            return self.fronthaul[-1][1]
        return None


    def get_fronthaul_node_key(self) -> str:
        if self.has_fronthaul():
            return self.fronthaul[-1][0]
        return None

    
    def get_target_base_station(self) -> str:
        return self.target


    def qty_nodes(self) -> int:
        """ :returns: An int representing the amount of CR's available on the route """
        if not self.has_midhaul():
            return 1
        elif not self.has_backhaul():
            return 2
        else:
            return 3


    def contains(self, node_key: str) -> bool:
        """ Check if Hardware hw is part of the route. """
        return node_key in self.sequence


    def is_cu(self, hw: str) -> bool:
        """ Check if Hardware hw is CU in the route. """
        return hw == self.sequence[0]


    def is_du(self, hw: str) -> bool:
        """ Check if Hardware hw is DU in the route. """
        return hw == self.sequence[1]


    def is_ru(self, hw: str) -> bool:
        """ Check if Hardware hw is RU in the route. """
        return hw == self.sequence[2]


    def has_fronthaul(self) -> bool:
        return len(self.fronthaul) > 0


    def has_midhaul(self) -> bool:
        return len(self.midhaul) > 0


    def has_backhaul(self) -> bool:
        return len(self.backhaul) > 0


    def is_fronthaul(self, link: str) -> bool:
        return link in [str(link) for link in self.fronthaul]


    def is_midhaul(self, link: str) -> bool:
        return link in [str(link) for link in self.midhaul]


    def is_backhaul(self, link: str) -> bool:
        return link in [str(link) for link in self.backhaul]


    def is_destination(self, ru: str) -> bool:
        """ Check if Ru ru is the destination of the route. """
        return self.target == ru