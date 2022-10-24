class Drc:
    def __init__(self, identifier: int, cu_cpu_usage: float, du_cpu_usage: float, ru_cpu_usage: float,
                 fs_cu: list, fs_du: list, fs_ru: list, bs_relief: float, delay_bh: float, 
                 delay_mh: float, delay_fh: float, bandwidth_bh: float, bandwidth_mh: float, 
                 bandwidth_fh: float, qty_cr: int):
        self.identifier = identifier
        self.cu_cpu_usage = cu_cpu_usage
        self.du_cpu_usage = du_cpu_usage
        self.ru_cpu_usage = ru_cpu_usage
        self.fs_cu = fs_cu
        self.fs_du = fs_du
        self.fs_ru = fs_ru
        self.bs_relief = bs_relief
        self.delay_bh = delay_bh
        self.delay_mh = delay_mh
        self.delay_fh = delay_fh
        self.bandwidth_bh = bandwidth_bh
        self.bandwidth_mh = bandwidth_mh
        self.bandwidth_fh = bandwidth_fh
        self.qty_cr = qty_cr

    def __hash__(self):
        return hash(self.identifier)

    def __eq__(self, other):
        return self.identifier == other.identifier

    def num_needed_nodes(self) -> int:
        if len(self.fs_du) == 0:
            return 1
        elif len(self.fs_cu) == 0:
            return 2
        else:
            return 3


def get_drc_list() -> list:
    return [Drc(identifier=1, cu_cpu_usage=0.49, du_cpu_usage=2.058, ru_cpu_usage=2.352,
                fs_cu=['f8'], fs_du=['f7', 'f6', 'f5', 'f4', 'f3', 'f2'], fs_ru=['f1', 'f0'],
                bs_relief=0.078, delay_bh=10.0, delay_mh=10.0, delay_fh=0.25,
                bandwidth_bh=9.9, bandwidth_mh=13.2, bandwidth_fh=42.6, qty_cr=3),
            Drc(identifier=2, cu_cpu_usage=0.98, du_cpu_usage=1.568, ru_cpu_usage=2.352,
                fs_cu=['f8', 'f7'], fs_du=['f6', 'f5', 'f4', 'f3', 'f2'], fs_ru=['f1', 'f0'],
                bs_relief=0.078, delay_bh=10.0, delay_mh=10.0, delay_fh=0.25,
                bandwidth_bh=9.9, bandwidth_mh=13.2, bandwidth_fh=42.6, qty_cr=3),
            Drc(identifier=4, cu_cpu_usage=0.49, du_cpu_usage=1.225, ru_cpu_usage=3.185,
                fs_cu=['f8'], fs_du=['f7', 'f6', 'f5', 'f4', 'f3'], fs_ru=['f2', 'f1', 'f0'],
                bs_relief=0.0525, delay_bh=10.0, delay_mh=10.0, delay_fh=0.25,
                bandwidth_bh=9.9, bandwidth_mh=13.2, bandwidth_fh=13.6, qty_cr=3),
            Drc(identifier=5, cu_cpu_usage=0.98, du_cpu_usage=0.735, ru_cpu_usage=3.185,
                fs_cu=['f8', 'f7'], fs_du=['f6', 'f5', 'f4', 'f3'], fs_ru=['f2', 'f1', 'f0'],
                bs_relief=0.0525, delay_bh=10.0, delay_mh=10.0, delay_fh=0.25,
                bandwidth_bh=9.9, bandwidth_mh=13.2, bandwidth_fh=13.6, qty_cr=3),

            Drc(identifier=6, cu_cpu_usage=0.0, du_cpu_usage=0.49, ru_cpu_usage=4.41,
                fs_cu=[], fs_du=['f8'], fs_ru=['f7', 'f6', 'f5', 'f4', 'f3', 'f2', 'f1', 'f0'],
                bs_relief=0.015, delay_bh=0.0, delay_mh=10.0, delay_fh=10.0, 
                bandwidth_bh=0.0, bandwidth_mh=9.9, bandwidth_fh=13.2, qty_cr=2),
            Drc(identifier=7, cu_cpu_usage=0.0, du_cpu_usage=0.98, ru_cpu_usage=3.92,
                fs_cu=[], fs_du=['f8', 'f7'], fs_ru=['f6', 'f5', 'f4', 'f3', 'f2', 'f1', 'f0'],
                bs_relief=0.03, delay_bh=0.0, delay_mh=10.0, delay_fh=10.0,
                bandwidth_bh=0.0, bandwidth_mh=9.9, bandwidth_fh=13.2, qty_cr=2),
            Drc(identifier=9, cu_cpu_usage=0.0, du_cpu_usage=2.54, ru_cpu_usage=2.354,
                fs_cu=[], fs_du=['f8', 'f7', 'f6', 'f5', 'f4', 'f3', 'f2'], fs_ru=['f1', 'f0'],
                bs_relief=0.078, delay_bh=0.0, delay_mh=10.0, delay_fh=0.25,
                bandwidth_bh=0.0, bandwidth_mh=9.9, bandwidth_fh=42.6, qty_cr=2),
            Drc(identifier=10, cu_cpu_usage=0.0, du_cpu_usage=1.71, ru_cpu_usage=3.185,
                fs_cu=[], fs_du=['f8', 'f7', 'f6', 'f5', 'f4', 'f3'], fs_ru=['f2', 'f1', 'f0'],
                bs_relief=0.0525, delay_bh=0.0, delay_mh=10.0, delay_fh=0.25,
                bandwidth_bh=0.0, bandwidth_mh=3.0, bandwidth_fh=13.6, qty_cr=2),

            Drc(identifier=8, cu_cpu_usage=0.0, du_cpu_usage=0.0, ru_cpu_usage=4.9,
                fs_cu=[], fs_du=[], fs_ru=['f8', 'f7', 'f6', 'f5', 'f4', 'f3', 'f2', 'f1', 'f0'],
                bs_relief=0.0, delay_bh=0.0, delay_mh=0.0, delay_fh=10.0,
                bandwidth_bh=0.0, bandwidth_mh=0.0, bandwidth_fh=9.9, qty_cr=1)]

def get_vnf_dict() -> dict:
    return {'f0': 1.176, 'f1': 1.176, 'f2': 0.833, 'f3': 0.343, 'f4': 0.343,
            'f5': 0.0245, 'f6': 0.0245, 'f7': 0.49, 'f8': 0.49}
