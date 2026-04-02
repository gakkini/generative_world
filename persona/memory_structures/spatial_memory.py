"""
spatial_memory.py - 空间记忆 (Spatial Memory)

原论文描述:
- "The agent's spatial memory includes their current location"
- "Agents navigate the sandbox world using their spatial memory"
- "They know which locations are relevant to their current plan"

功能:
- 记录agent当前位置
- 记录已访问的地点
- 记录地点的重要性（基于活动频率）
- 记录地点的特征（有什么、适合做什么）
- 支持空间导航决策
"""
from typing import Dict, List, Optional, Set
from collections import defaultdict


class VisitedLocation:
    """访问过的地点记录"""

    def __init__(self, location_id: str, name: str):
        self.location_id = location_id
        self.name = name
        self.visit_count: int = 0
        self.last_visit_day: int = 0
        self.total_duration: float = 0.0  # 总停留时长（估算）
        self.first_visit_day: Optional[int] = None
        self.activities: List[str] = []  # 在此地点进行的活动
        self.people_encountered: Set[str] = set()  # 遇到的人

    def record_visit(self, day: int, duration: float = 1.0, activity: str = None):
        """记录一次访问"""
        self.visit_count += 1
        self.last_visit_day = day
        self.total_duration += duration

        if self.first_visit_day is None:
            self.first_visit_day = day

        if activity:
            self.activities.append(activity)

    def add_person_encountered(self, person_id: str):
        """记录遇到的人"""
        self.people_encountered.add(person_id)

    def get_importance(self) -> float:
        """
        计算地点重要性
        基于访问频率、最近访问、停留时长
        """
        # 访问频率得分
        frequency_score = min(self.visit_count / 10, 1.0)  # 最多10次封顶

        # 停留时长得分
        duration_score = min(self.total_duration / 20, 1.0)  # 最多20天封顶

        # 最近访问得分
        return frequency_score * 0.4 + duration_score * 0.6

    def get_typical_activities(self) -> List[str]:
        """获取典型活动"""
        if not self.activities:
            return []
        # 返回最常见的活动
        from collections import Counter
        counter = Counter(self.activities)
        return [act for act, _ in counter.most_common(3)]


class SpatialMemory:
    """
    空间记忆

    管理agent对物理世界的认知
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id

        # 当前位置
        self.current_location: Optional[str] = None
        self.current_location_name: str = ""

        # 已访问地点
        self.visited_locations: Dict[str, VisitedLocation] = {}

        # 地点重要性缓存
        self.location_importance: Dict[str, float] = {}

        # 导航历史
        self.navigation_history: List[Dict] = []  # [{'from': ..., 'to': ..., 'day': ...}, ...]

        # 当前位置的已知特征
        self.current_location_features: Dict[str, any] = {}

    def set_current_location(self, location_id: str, location_name: str = "",
                             day: int = 1, duration: float = 1.0):
        """
        设置当前位置

        Args:
            location_id: 地点ID
            location_name: 地点名称
            day: 当前天数
            duration: 停留时长
        """
        old_location = self.current_location

        if self.current_location and old_location != location_id:
            # 移动事件：离开旧地点
            self.navigation_history.append({
                'from': old_location,
                'to': location_id,
                'day': day
            })

        self.current_location = location_id
        self.current_location_name = location_name

        # 记录访问
        if location_id not in self.visited_locations:
            self.visited_locations[location_id] = VisitedLocation(location_id, location_name)
        self.visited_locations[location_id].record_visit(day, duration)

    def record_activity(self, activity: str):
        """记录在当前位置进行的活动"""
        if self.current_location and self.current_location in self.visited_locations:
            self.visited_locations[self.current_location].activities.append(activity)

    def record_person_encountered(self, person_id: str):
        """记录在当前位置遇到的人"""
        if self.current_location and self.current_location in self.visited_locations:
            self.visited_locations[self.current_location].add_person_encountered(person_id)

    def get_visited_count(self) -> int:
        """获取已访问地点数量"""
        return len(self.visited_locations)

    def get_most_visited_locations(self, k: int = 5) -> List[VisitedLocation]:
        """获取最常访问的地点"""
        sorted_locs = sorted(
            self.visited_locations.values(),
            key=lambda x: x.visit_count,
            reverse=True
        )
        return sorted_locs[:k]

    def get_location_importance(self, location_id: str) -> float:
        """获取某地点的重要性"""
        if location_id in self.visited_locations:
            return self.visited_locations[location_id].get_importance()
        return 0.0

    def get_people_at_location(self, location_id: str) -> Set[str]:
        """获取在某地点遇到过的人"""
        if location_id in self.visited_locations:
            return self.visited_locations[location_id].people_encountered
        return set()

    def get_recent_navigation(self, n: int = 5) -> List[Dict]:
        """获取最近的导航记录"""
        return self.navigation_history[-n:]

    def get_location_features(self, location_id: str) -> Optional[Dict]:
        """获取地点特征"""
        return self.current_location_features.get(location_id)

    def set_location_features(self, location_id: str, features: Dict):
        """设置地点特征"""
        self.current_location_features[location_id] = features

    def get_navigatable_locations(self, world_connections: Dict) -> List[str]:
        """
        获取可导航的相邻地点

        Args:
            world_connections: 世界连接配置 {location_id: [connected_ids]}

        Returns:
            可直接前往的地点列表
        """
        if not self.current_location:
            return []

        # 从世界配置获取连接
        connections = world_connections.get(self.current_location, [])
        return connections

    def update_location_importance_cache(self):
        """更新地点重要性缓存"""
        for loc_id, visited in self.visited_locations.items():
            self.location_importance[loc_id] = visited.get_importance()

    def get_known_locations_summary(self) -> str:
        """生成已知地点摘要"""
        if not self.visited_locations:
            return "尚未探索任何地点"

        lines = []
        for loc_id, visited in self.visited_locations.items():
            importance = visited.get_importance()
            importance_label = "重要" if importance > 0.5 else "一般"
            lines.append(
                f"- {visited.name}: 访问{visited.visit_count}次(最近第{visited.last_visit_day}天)"
            )

        return "\n".join(lines[:10])  # 最多10条
