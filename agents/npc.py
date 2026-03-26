"""
简单NPC Agent - 用于次要角色
比主角更简单的实现，减少LLM调用
"""
import random


class SimpleNPCAgent:
    """
    简单NPC角色
    - 不使用LLM生成
    - 使用模板和规则生成行为
    - 减少计算开销
    """
    
    # 简单行为模板
    ACTIVITIES = [
        "在宗门内修炼",
        "与同道切磋",
        "采集灵草",
        "打坐冥想",
        "浏览典籍",
    ]
    
    DIALOGUE_TEMPLATES = [
        "道友有礼。",
        "今日天气甚好。",
        "修真之道，贵在坚持。",
        "听闻最近有秘境开启。",
        "我辈修士，当以天下苍生为己任。",
    ]
    
    def __init__(self, config, world):
        self.id = config['id']
        self.name = config['name']
        self.sect = config['sect']
        self.cultivation = config.get('cultivation', '炼气期')
        self.personality = config.get('personality', '普通')
        
        self.world = world
        self.current_location = world.get_character_location(self.id)
        
        # 记忆（简化版）
        self.events = []
        self.relationships = {}
        
        # 当前位置
        self.current_location = self.world.get_character_location(self.id)
    
    def perceive(self):
        """简单感知：只记录位置"""
        self.events.append({
            'day': self.world.time.day,
            'type': 'location',
            'content': f"在{self.current_location}"
        })
    
    def plan(self) -> list:
        """简单规划：随机选择活动"""
        activities = random.sample(self.ACTIVITIES, min(2, len(self.ACTIVITIES)))
        return activities
    
    def act(self, plans: list) -> list:
        """执行动作"""
        results = []
        for plan in plans:
            result = f"{self.name}：{plan}"
            self.events.append({
                'day': self.world.time.day,
                'type': 'action',
                'content': result
            })
            self.world.add_event(self.id, result, 'action')
            results.append(result)
        return results
    
    def interact(self, other) -> str:
        """简单对话"""
        dialogue = random.choice(self.DIALOGUE_TEMPLATES)
        self.events.append({
            'day': self.world.time.day,
            'type': 'dialogue',
            'content': f"对{other.name}说：{dialogue}"
        })
        return f"{self.name}：{dialogue}"
    
    def write_diary(self) -> str:
        """简单日记"""
        events_today = [e for e in self.events if e['day'] == self.world.time.day]
        
        lines = [
            f"【{self.name}日记】{self.world.time.get_full_time_str()}",
            f"地点：{self.current_location}",
        ]
        
        if events_today:
            for e in events_today:
                lines.append(f"- {e['content']}")
        else:
            lines.append("- 今日无事，于静室中闭关修炼。")
        
        return "\n".join(lines)
    
    def clear_daily_data(self):
        """清空每日数据"""
        pass
    
    def reflect(self):
        """简化反思"""
        pass


class SmartAgent:
    """
    智能Agent - 用于主角
    使用完整的LLM能力
    """
    pass  # 实际使用 Agent 类


def create_npc_agent(config, world) -> SimpleNPCAgent:
    """创建简单NPC"""
    return SimpleNPCAgent(config, world)
