"""交通系统"""


class TransportSystem:
    """地点间移动系统"""
    
    def __init__(self, locations, connections):
        self.locations = {loc['id']: loc for loc in locations}
        self.connections = {}  # (from, to) -> days
        
        for conn in connections:
            key = (conn['from'], conn['to'])
            self.connections[key] = conn.get('days', 1)
    
    def get_travel_days(self, from_loc, to_loc) -> int:
        """获取两地移动天数，0表示瞬移/传送阵"""
        return self.connections.get((from_loc, to_loc), 1)
    
    def can_travel(self, from_loc, to_loc) -> bool:
        """检查两地是否连通"""
        return (from_loc, to_loc) in self.connections
    
    def get_reachable(self, from_loc) -> list:
        """从某地可到达的所有地点"""
        reachable = []
        for (f, t), days in self.connections.items():
            if f == from_loc:
                reachable.append({'to': t, 'days': days})
        return reachable
