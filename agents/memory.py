"""
记忆模块 - 包含关联记忆、工作记忆、反思机制
"""
import time
import math


class MemoryImportance:
    """记忆重要度评估器"""
    
    HIGH_IMPORTANCE_KEYWORDS = [
        '生死', '决斗', '大战', '突破', '渡劫', 
        '背叛', '结交', '秘籍', '功法', '师父',
        '仇人', '救命', '救命之恩', '约定', '誓言',
        '秘境', '遗迹', '宝藏', '发现了'
    ]
    
    MEDIUM_IMPORTANCE_KEYWORDS = [
        '交流', '切磋', '论道', '拜访', '相遇',
        '听说', '传闻', '讨论', '商量', '邀请'
    ]
    
    @classmethod
    def assess(cls, content: str) -> float:
        """评估事件重要程度 (0.0 - 1.0)"""
        score = 0.5  # 默认基础分
        
        for kw in cls.HIGH_IMPORTANCE_KEYWORDS:
            if kw in content:
                score += 0.2
        
        for kw in cls.MEDIUM_IMPORTANCE_KEYWORDS:
            if kw in content:
                score += 0.1
        
        return min(score, 1.0)


class MemoryEvent:
    """单条记忆"""
    
    def __init__(self, content, day, location=None, 
                 participants=None, event_type='action'):
        self.id = f"mem_{int(time.time() * 1000)}"
        self.content = content
        self.day = day
        self.location = location
        self.participants = participants or []
        self.type = event_type  # action, observation, dialogue, reflection
        self.importance = MemoryImportance.assess(content)
        self.created_at = time.time()
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'content': self.content,
            'day': self.day,
            'location': self.location,
            'participants': self.participants,
            'type': self.type,
            'importance': self.importance
        }


class AssociativeMemory:
    """
    关联记忆 - 核心记忆存储与检索系统
    实现论文中的 Memory Stream + 检索机制
    """
    
    # 检索权重
    RECENCY_WEIGHT = 0.3
    IMPORTANCE_WEIGHT = 0.3
    RELEVANCE_WEIGHT = 0.4
    
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.events = []  # 所有事件记忆
        self.reflections = []  # 反思洞察
        self.summary = ""  # 记忆摘要（供LLM使用）
    
    def add_event(self, content, day, location=None, 
                  participants=None, event_type='action'):
        """添加新事件到记忆流"""
        event = MemoryEvent(content, day, location, participants, event_type)
        self.events.append(event)
        return event
    
    def add_reflection(self, reflection_text, day):
        """添加反思洞察"""
        self.reflections.append({
            'id': f"ref_{int(time.time() * 1000)}",
            'content': reflection_text,
            'day': day,
            'created_at': time.time()
        })
    
    def get_recency_score(self, event_day, current_day, decay_rate=0.03) -> float:
        """
        计算新鲜度得分
        使用指数衰减：score = e^(-decay_rate * days_ago)
        """
        days_ago = current_day - event_day
        return math.exp(-decay_rate * days_ago)
    
    def get_relevance_score(self, event, query_embedding) -> float:
        """
        计算相关度得分
        简单版本：基于关键词匹配
        完整版本：使用向量嵌入计算余弦相似度
        """
        if not query_embedding:
            return 0.5
        
        # 简单版本：提取关键词重叠度
        query_words = set(query_embedding.lower().split())
        event_words = set(event.content.lower().split())
        
        if not query_words or not event_words:
            return 0.5
        
        overlap = len(query_words & event_words)
        total = len(query_words | event_words)
        
        return overlap / total if total > 0 else 0.5
    
    def retrieve(self, query: str, current_day: int, 
                 n: int = 5, event_types=None) -> list:
        """
        检索记忆
        
        Args:
            query: 查询文本
            current_day: 当前天数
            n: 返回数量
            event_types: 过滤的事件类型
        
        Returns:
            按得分排序的记忆列表 [(event, score), ...]
        """
        candidates = self.events
        
        # 按类型过滤
        if event_types:
            candidates = [e for e in candidates if e.type in event_types]
        
        scored = []
        for event in candidates:
            recency = self.get_recency_score(event.day, current_day)
            relevance = self.get_relevance_score(event, query)
            
            total_score = (
                self.RECENCY_WEIGHT * recency +
                self.IMPORTANCE_WEIGHT * event.importance +
                self.RELEVANCE_WEIGHT * relevance
            )
            
            scored.append((event, total_score))
        
        # 排序并返回top n
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:n]
    
    def retrieve_by_type(self, event_type: str, current_day: int, n: int = 3) -> list:
        """按类型检索记忆"""
        return self.retrieve("", current_day, n=n, event_types=[event_type])
    
    def get_recent_events(self, current_day, days: int = 7) -> list:
        """获取最近N天的事件"""
        return [
            e for e in self.events
            if current_day - e.day <= days
        ]
    
    def get_events_by_location(self, location: str, current_day: int, n: int = 5) -> list:
        """获取某地点相关的记忆"""
        candidates = [
            e for e in self.events
            if e.location == location
        ]
        # 按新鲜度排序
        candidates.sort(
            key=lambda e: self.get_recency_score(e.day, current_day),
            reverse=True
        )
        return candidates[:n]
    
    def get_events_with_person(self, person_id: str, current_day: int, n: int = 5) -> list:
        """获取与某人有交互的记忆"""
        candidates = [
            e for e in self.events
            if person_id in e.participants
        ]
        candidates.sort(
            key=lambda e: self.get_recency_score(e.day, current_day),
            reverse=True
        )
        return candidates[:n]
    
    def get_summary(self, current_day: int) -> str:
        """生成记忆摘要（供LLM context使用）"""
        recent = self.get_recent_events(current_day, days=7)
        
        lines = ["【近期重要记忆】"]
        for e in recent:
            if e.importance >= 0.6:
                lines.append(f"- 第{e.day}日：{e.content}")
        
        if self.reflections:
            lines.append("\n【反思洞察】")
            for r in self.reflections[-3:]:
                lines.append(f"- {r['content']}")
        
        return "\n".join(lines) if lines else "暂无特殊记忆"
    
    def __len__(self):
        return len(self.events)


class WorkingMemory:
    """
    工作记忆 - 规划时使用的短期记忆
    类似于论文中的 Scratch
    """
    
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.current_plans = []  # 当前计划
        self.current_plan_index = 0
        self. plan_context = {}  # 计划执行上下文
        self.attending_to = None  # 当前关注点
        self.pending_actions = []  # 待执行动作队列
    
    def set_context(self, key, value):
        self.plan_context[key] = value
    
    def get_context(self, key, default=None):
        return self.plan_context.get(key, default)
    
    def push_action(self, action):
        self.pending_actions.append(action)
    
    def pop_action(self):
        return self.pending_actions.pop(0) if self.pending_actions else None
    
    def clear(self):
        self.current_plans = []
        self.current_plan_index = 0
        self.plan_context = {}
        self.pending_actions = []
