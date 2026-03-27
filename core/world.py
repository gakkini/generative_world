"""世界状态管理"""
import yaml
from .time_system import TimeSystem
from .transport import TransportSystem


class World:
    """世界状态：管理所有角色、地点、事件"""
    
    def __init__(self, config_path=None, config=None):
        if config_path:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        
        self.config = config
        self.name = config['world']['name']
        self.type = config['world']['type']
        
        # 时间系统
        self.time = TimeSystem(config.get('world', {}))
        
        # 交通系统
        self.transport = TransportSystem(
            config['locations'],
            config['connections']
        )
        
        # 地点配置
        self.locations = {loc['id']: loc for loc in config['locations']}
        
        # 角色状态
        self.characters = {}
        self.positions = {}  # character_id -> location_id
        
        # 事件日志
        self.event_log = []
        
        # 初始化角色位置
        initial = config.get('initial_state', {})
        self.time.day = initial.get('day', 1)
        for char_id, loc_id in initial.get('positions', {}).items():
            self.positions[char_id] = loc_id
    
    def get_location(self, loc_id) -> dict:
        """获取地点信息"""
        return self.locations.get(loc_id, {})
    
    def get_character_location(self, char_id) -> str:
        """获取角色当前位置"""
        return self.positions.get(char_id, 'unknown')
    
    def move_character(self, char_id, to_loc) -> int:
        """移动角色，返回移动天数（0表示瞬移）"""
        from_loc = self.positions.get(char_id, 'unknown')
        days = self.transport.get_travel_days(from_loc, to_loc)
        
        self.positions[char_id] = to_loc
        
        if days == 0:
            event = f"{char_id}从{from_loc}通过传送阵抵达{to_loc}"
        else:
            event = f"{char_id}从{from_loc}御剑前往{to_loc}，历时{days}日"
        
        self.add_event(char_id, event)
        return days
    
    def add_event(self, char_id, content, event_type='action'):
        """记录事件"""
        self.event_log.append({
            'day': self.time.day,
            'character': char_id,
            'type': event_type,
            'content': content,
            'location': self.positions.get(char_id),
            'location_name': self.locations.get(self.positions.get(char_id), {}).get('name', '未知')
        })
    
    def get_events_for_character(self, char_id) -> list:
        """获取某角色相关的所有事件"""
        return [
            e for e in self.event_log 
            if e['character'] == char_id
        ]
    
    def get_recent_events(self, char_id, days=7) -> list:
        """获取某角色最近几天的事件"""
        current_day = self.time.day
        return [
            e for e in self.get_events_for_character(char_id)
            if current_day - e['day'] < days
        ]
    
    def advance_day(self, days=1):
        """推进一天"""
        self.time.advance(days)
    
    def get_state_summary(self) -> dict:
        """获取世界状态摘要（供剧本引擎使用）"""
        return {
            'day': self.time.day,
            'time_str': self.time.get_full_time_str(),
            'positions': self.positions.copy(),
            'locations': self.locations
        }
