import collections

class Graph:
    def __init__(self):
        self.vertices = []
        self.graph = collections.defaultdict(list)
        self.cost = {}
        self.paths = []
        self.actual_paths_counter = 0
    
    @staticmethod
    def __is_cycle(path: list) -> bool:
        return len(path) > 4 and 1 in path and 2 in path

    def get_paths(self) -> list:
        return self.paths

    def __find_all_paths(self, source: int, destination: int, has_been_visited: list, 
                        actual_path: list, k: int):
        has_been_visited[source] = True
        actual_path.append(source)

        if source == destination:
            if not self.__is_cycle(actual_path):
                self.actual_paths_counter += 1
                if self.actual_paths_counter < k:
                    self.paths.append(actual_path.copy())
        else:
            for node in self.graph[source]:
                if has_been_visited[node]:
                    continue
                self.__find_all_paths(node, destination, has_been_visited, actual_path, k)

        actual_path.pop()
        has_been_visited[source] = False

    def add_edge(self, source: int, destination: int, delay: float = 0):
        if source not in self.vertices:
            self.vertices.append(source)
        if destination not in self.vertices:
            self.vertices.append(destination)
        self.graph[source].append(destination)
        self.cost[(source, destination, 'delay')] = delay

    def find_all_paths(self, source: int, destination: int, k: int = 4):
        has_been_visited = {key: False for key in self.vertices}
        path = []
        self.actual_paths_counter = 0
        self.__find_all_paths(source, destination, has_been_visited, path, k)