"""
associative_memory.py - 关联记忆流 (Associative Memory Stream)

原论文核心实现：
- Memory Stream: 持续的经验流，按时间顺序存储
- 每条记忆包含: 文本描述、创建时间、重要性分数
- 记忆分类: observation, action, dialogue, reflection

检索机制 (Retrieval):
- 不是简单获取最近N条
- 加权评分: importance * recency * relevance
- recency: 指数衰减 0.99^(天数差)
- importance: 根据事件类型和关键词评估
- relevance: 与当前情境的语义匹配度
"""
import time
import math
from typing import List, Dict, Any, Optional, Tuple


class MemoryImportance:
    """记忆重要性评估器"""

    HIGH_IMPORTANCE_KEYWORDS = [
        '生死', '决斗', '大战', '突破', '渡劫',
        '背叛', '结交', '秘籍', '功法', '师父',
        '仇人', '救命', '约定', '誓言', '秘境',
        '发现', '秘密', '告白', '求婚', '争吵',
        '分手', '和好', '重要', '关键'
    ]

    MEDIUM_IMPORTANCE_KEYWORDS = [
        '交流', '切磋', '论道', '拜访', '相遇',
        '听说', '传闻', '讨论', '邀请', '约会',
        '吃饭', '散步', '聊天', '工作', '学习'
    ]

    # 事件类型对应的基础重要性
    EVENT_TYPE_BASE_IMPORTANCE = {
        'dialogue': 0.6,     # 对话通常中等重要
        'action': 0.5,       # 动作中等
        'observation': 0.4,  # 观察较不重要
        'reflection': 0.8,   # 反思重要
        'social_event': 0.7, # 社交事件重要
        'notification': 0.3, # 通知较不重要
    }

    @classmethod
    def assess(cls, content: str, event_type: str = 'action') -> float:
        """评估事件重要程度 (0.0 - 1.0)"""
        # 基础分
        score = cls.EVENT_TYPE_BASE_IMPORTANCE.get(event_type, 0.5)

        # 关键词加成
        for kw in cls.HIGH_IMPORTANCE_KEYWORDS:
            if kw in content:
                score += 0.15

        for kw in cls.MEDIUM_IMPORTANCE_KEYWORDS:
            if kw in content:
                score += 0.05

        return min(max(score, 0.0), 1.0)


class MemoryEvent:
    """
    单条记忆

    字段:
    - id: 唯一标识
    - content: 记忆内容文本
    - day: 记忆发生的天数
    - location: 发生地点
    - participants: 参与者ID列表
    - type: 记忆类型 (observation/action/dialogue/reflection)
    - importance: 重要性分数 (0-1)
    - created_at: 创建时间戳
    """

    TYPE_OBSERVATION = 'observation'
    TYPE_ACTION = 'action'
    TYPE_DIALOGUE = 'dialogue'
    TYPE_REFLECTION = 'reflection'
    TYPE_SOCIAL = 'social_event'
    TYPE_NOTIFICATION = 'notification'

    def __init__(self, content: str, day: int, location: Optional[str] = None,
                 participants: Optional[List[str]] = None,
                 event_type: str = 'action'):
        self.id = f"mem_{int(time.time() * 1000)}_{hash(content) % 10000}"
        self.content = content
        self.day = day
        self.location = location
        self.participants = participants or []
        self.type = event_type
        self.importance = MemoryImportance.assess(content, event_type)
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

    def __repr__(self):
        return f"<MemoryEvent [{self.type}] day={self.day}: {self.content[:40]}...>"


class Reflection:
    """反思洞察"""

    def __init__(self, content: str, day: int, related_events: Optional[List[str]] = None):
        self.id = f"ref_{int(time.time() * 1000)}"
        self.content = content
        self.day = day
        self.related_events = related_events or []
        self.created_at = time.time()

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'content': self.content,
            'day': self.day,
            'related_events': self.related_events
        }


class AssociativeMemory:
    """
    关联记忆 - 核心记忆存储与检索系统

    实现论文中的 Memory Stream + 检索机制

    检索权重分配:
    - RECENCY_WEIGHT (0.3): 新鲜度权重
    - IMPORTANCE_WEIGHT (0.3): 重要性权重
    - RELEVANCE_WEIGHT (0.4): 相关性权重

    检索公式:
    score = w_r * recency + w_i * importance + w_rel * relevance

    其中:
    - recency = e^(-decay_rate * days_ago)
    - importance: 0-1 直接使用
    - relevance: 基于关键词重叠度
    """

    # 检索权重
    RECENCY_WEIGHT = 0.3
    IMPORTANCE_WEIGHT = 0.3
    RELEVANCE_WEIGHT = 0.4

    # 衰减参数
    RECENCY_DECAY_RATE = 0.03  # 每天衰减约3%

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.events: List[MemoryEvent] = []  # 记忆流
        self.reflections: List[Reflection] = []  # 反思列表
        self._event_counter = 0

    def add(self, content: str, day: int, location: Optional[str] = None,
            participants: Optional[List[str]] = None,
            event_type: str = 'action') -> MemoryEvent:
        """添加新事件到记忆流"""
        self._event_counter += 1
        event = MemoryEvent(
            content=content,
            day=day,
            location=location,
            participants=participants,
            event_type=event_type
        )
        self.events.append(event)
        return event

    def add_reflection(self, reflection_text: str, day: int,
                       related_events: Optional[List[str]] = None) -> Reflection:
        """添加反思洞察"""
        reflection = Reflection(reflection_text, day, related_events)
        self.reflections.append(reflection)
        return reflection

    # ==================== 检索相关方法 ====================

    def _compute_recency_score(self, event_day: int, current_day: int) -> float:
        """
        计算新鲜度得分
        使用指数衰减: score = e^(-decay_rate * days_ago)
        """
        days_ago = current_day - event_day
        return math.exp(-self.RECENCY_DECAY_RATE * days_ago)

    def _compute_relevance_score(self, event: MemoryEvent, query: str) -> float:
        """
        计算相关度得分
        基于关键词重叠度 + 位置/人物匹配

        Args:
            event: 记忆事件
            query: 查询文本

        Returns:
            0-1 之间的相关度分数
        """
        if not query or not query.strip():
            return 0.5  # 无查询时返回中性

        query_lower = query.lower()
        content_lower = event.content.lower()

        # 提取查询词
        query_words = set(query_lower.split())
        content_words = set(content_lower.split())

        # 过滤停用词
        stopwords = {'的', '了', '在', '是', '我', '你', '他', '她', '它', '这', '那', '和', '与', '或'}
        query_words -= stopwords
        content_words -= stopwords

        if not query_words or not content_words:
            return 0.5

        # 1. 基础关键词重叠度
        overlap = query_words & content_words
        base_score = len(overlap) / len(query_words) if query_words else 0

        # 2. 查询词在内容中的密度
        density = len(overlap) / len(content_words) if content_words else 0

        # 3. 组合得分
        relevance = base_score * 0.6 + density * 0.4

        return min(max(relevance, 0.0), 1.0)

    def retrieve(self, query: str, current_day: int,
                 k: int = 5,
                 event_types: Optional[List[str]] = None) -> List[Tuple[MemoryEvent, float]]:
        """
        从记忆流中检索与当前情境相关的记忆

        核心算法:
        1. 计算每条记忆的"重要性分数" (importance)
        2. 计算"时效衰减" (recency) - 越久远衰减越多
        3. 计算"关联性" (relevance) - 与当前情境的相关程度
        4. 加权得分 = w_r*recency + w_i*importance + w_rel*relevance
        5. 排序取Top k

        Args:
            query: 检索查询（当前情境描述）
            current_day: 当前天数
            k: 返回的记忆数量
            event_types: 可选，过滤特定类型

        Returns:
            [(event, score), ...] 按得分降序排列
        """
        candidates = self.events

        # 按类型过滤
        if event_types:
            candidates = [e for e in candidates if e.type in event_types]

        scored = []
        for event in candidates:
            recency = self._compute_recency_score(event.day, current_day)
            relevance = self._compute_relevance_score(event, query)

            total_score = (
                self.RECENCY_WEIGHT * recency +
                self.IMPORTANCE_WEIGHT * event.importance +
                self.RELEVANCE_WEIGHT * relevance
            )

            scored.append((event, total_score))

        # 排序并返回top k
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    def retrieve_by_type(self, event_type: str, current_day: int, k: int = 5) -> List[Tuple[MemoryEvent, float]]:
        """按类型检索记忆"""
        return self.retrieve("", current_day, k=k, event_types=[event_type])

    def retrieve_dialogues(self, current_day: int, k: int = 3) -> List[Tuple[MemoryEvent, float]]:
        """检索对话记忆"""
        return self.retrieve_by_type(MemoryEvent.TYPE_DIALOGUE, current_day, k=k)

    def retrieve_by_location(self, location: str, current_day: int, k: int = 5) -> List[Tuple[MemoryEvent, float]]:
        """获取某地点相关的记忆"""
        candidates = [e for e in self.events if e.location == location]
        scored = []
        for event in candidates:
            recency = self._compute_recency_score(event.day, current_day)
            score = 0.7 * recency + 0.3 * event.importance
            scored.append((event, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    def retrieve_with_person(self, person_id: str, current_day: int, k: int = 5) -> List[Tuple[MemoryEvent, float]]:
        """获取与某人有交互的记忆"""
        candidates = [e for e in self.events if person_id in e.participants]
        scored = []
        for event in candidates:
            recency = self._compute_recency_score(event.day, current_day)
            score = 0.6 * recency + 0.4 * event.importance
            scored.append((event, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    def get_recent_events(self, current_day: int, days: int = 7) -> List[MemoryEvent]:
        """获取最近N天的所有事件"""
        return [e for e in self.events if current_day - e.day <= days]

    def get_recent_reflections(self, current_day: int, days: int = 7) -> List[Reflection]:
        """获取最近的反思"""
        return [r for r in self.reflections if current_day - r.day <= days]

    def get_summary(self, current_day: int, max_events: int = 10) -> str:
        """生成记忆摘要（供LLM context使用）"""
        # 先检索重要记忆
        important = self.retrieve("", current_day, k=max_events,
                                 event_types=['action', 'dialogue', 'observation'])

        lines = ["【近期记忆】"]
        for event, score in important:
            lines.append(f"- 第{event.day}日({event.type}): {event.content[:50]}")

        if self.reflections:
            lines.append("\n【反思洞察】")
            for r in self.reflections[-3:]:
                lines.append(f"- {r.content}")

        return "\n".join(lines) if len(lines) > 1 else "暂无特殊记忆"

    def __len__(self):
        return len(self.events)
