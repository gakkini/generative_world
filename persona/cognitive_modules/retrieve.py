"""
retrieve.py - 关联记忆检索 (Associative Retrieval)

原论文核心算法：

这是Stanford Generative Agents论文最关键的机制之一！

检索不是简单的"取最近N条"，而是加权评分：

    score(event) = importance(event) × recency(event) × relevance(event, query)

其中:
- importance: 记忆来源于重要事件则高（对话>行动>感知）
- recency: 指数衰减, 0.99^(天数差)
- relevance: 与当前情境(query)的语义匹配度

最终选取得分最高的k条记忆用于规划上下文。
"""
from typing import List, Tuple, Dict, Any, Optional

from ..memory_structures.associative_memory import (
    MemoryEvent, AssociativeMemory
)


class Retriever:
    """
    关联检索器

    核心功能：从记忆流中检索与当前情境最相关的记忆
    """

    # 加权系数（可调）
    RECENCY_COEFFICIENT = 0.3
    IMPORTANCE_COEFFICIENT = 0.3
    RELEVANCE_COEFFICIENT = 0.4

    # 衰减参数
    RECENCY_DECAY = 0.03  # 每天衰减约3%

    def __init__(self, memory: AssociativeMemory):
        self.memory = memory

    def retrieve(self, query: str, current_day: int, k: int = 5,
                 event_types: Optional[List[str]] = None) -> List[Tuple[MemoryEvent, float]]:
        """
        从记忆流中检索与当前情境相关的记忆

        核心算法:
        1. 遍历所有记忆
        2. 计算 recency_score = e^(-decay * days_ago)
        3. 计算 importance_score = memory_event.importance
        4. 计算 relevance_score = keyword_overlap(query, content)
        5. 加权得分 = w_r*recency + w_i*importance + w_rel*relevance
        6. 排序取Top k

        Args:
            query: 当前情境描述（用于计算相关性）
            current_day: 当前天数
            k: 返回数量
            event_types: 可选的事件类型过滤

        Returns:
            [(MemoryEvent, score), ...] 按得分降序
        """
        candidates = self.memory.events

        # 按类型过滤
        if event_types:
            candidates = [e for e in candidates if e.type in event_types]

        scored = []
        for event in candidates:
            recency = self._calc_recency(event.day, current_day)
            relevance = self._calc_relevance(event, query)

            total = (
                self.RECENCY_COEFFICIENT * recency +
                self.IMPORTANCE_COEFFICIENT * event.importance +
                self.RELEVANCE_COEFFICIENT * relevance
            )

            scored.append((event, total))

        # 排序
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    def _calc_recency(self, event_day: int, current_day: int) -> float:
        """
        计算新鲜度得分

        使用指数衰减: e^(-decay * days_ago)
        - 1天前: e^0 ≈ 1.0
        - 7天前: e^-0.21 ≈ 0.81
        - 30天前: e^-0.9 ≈ 0.41
        """
        days_ago = current_day - event_day
        return pow(2.71828, -self.RECENCY_DECAY * days_ago)

    def _calc_relevance(self, event: MemoryEvent, query: str) -> float:
        """
        计算相关度得分

        基于:
        1. 关键词重叠（60%权重）
        2. 查询词密度（40%权重）
        """
        if not query or not query.strip():
            return 0.5

        query_words = set(query.lower().split())
        content_words = set(event.content.lower().split())

        # 停用词
        stopwords = {'的', '了', '在', '是', '我', '你', '他', '她', '它',
                     '这', '那', '和', '与', '或', '了', '着', '过', '有',
                     '个', '一', '上', '下', '中', '来', '去', '到', '把'}
        query_words -= stopwords
        content_words -= stopwords

        if not query_words:
            return 0.5

        # 重叠度
        overlap = query_words & content_words
        if not overlap:
            return 0.1  # 最低分

        # 精确匹配得分
        match_ratio = len(overlap) / len(query_words)

        # 密度得分（重叠词占内容的比例）
        density = len(overlap) / len(content_words) if content_words else 0

        return min(match_ratio * 0.6 + density * 0.4, 1.0)

    def retrieve_for_planning(self, current_day: int,
                             location: str = None,
                             nearby_agents: List[str] = None,
                             current_activity: str = None) -> Dict[str, Any]:
        """
        为规划检索相关记忆

        综合考虑:
        - 当前位置相关的记忆
        - 附近人物相关的记忆
        - 当前活动相关的记忆

        Returns:
            {
                'location_memories': [...],
                'person_memories': {...},
                'general_memories': [...],
                'reflections': [...],
                'combined_context': "..."
            }
        """
        result = {}

        # 1. 位置相关记忆
        if location:
            location_scores = []
            for event in self.memory.events:
                if event.location == location:
                    recency = self._calc_recency(event.day, current_day)
                    score = recency * 0.7 + event.importance * 0.3
                    location_scores.append((event, score))
            location_scores.sort(key=lambda x: x[1], reverse=True)
            result['location_memories'] = location_scores[:5]
        else:
            result['location_memories'] = []

        # 2. 人物相关记忆（按人物分组）
        if nearby_agents:
            person_memories = {}
            for agent_id in nearby_agents:
                agent_scores = []
                for event in self.memory.events:
                    if agent_id in event.participants:
                        recency = self._calc_recency(event.day, current_day)
                        score = recency * 0.6 + event.importance * 0.4
                        agent_scores.append((event, score))
                agent_scores.sort(key=lambda x: x[1], reverse=True)
                person_memories[agent_id] = agent_scores[:3]
            result['person_memories'] = person_memories
        else:
            result['person_memories'] = {}

        # 3. 当前活动相关记忆
        if current_activity:
            activity_query = current_activity
            result['general_memories'] = self.retrieve(activity_query, current_day, k=5)
        else:
            result['general_memories'] = self.retrieve("", current_day, k=5)

        # 4. 近期反思
        reflections = self.memory.get_recent_reflections(current_day, days=7)
        result['reflections'] = reflections

        # 5. 组合上下文（供LLM使用）
        result['combined_context'] = self._build_planning_context(result, current_day)

        return result

    def _build_planning_context(self, retrieval_result: Dict, current_day: int) -> str:
        """构建供LLM使用的检索上下文"""
        lines = []

        # 位置记忆
        loc_mems = retrieval_result.get('location_memories', [])
        if loc_mems:
            lines.append("【相关地点记忆】")
            for event, score in loc_mems:
                lines.append(f"- 第{event.day}日: {event.content[:60]}")

        # 人物记忆
        person_mems = retrieval_result.get('person_memories', {})
        if person_mems:
            lines.append("\n【与相关人物的过往】")
            for agent_id, memories in person_mems.items():
                lines.append(f"与{agent_id}的互动:")
                for event, score in memories:
                    lines.append(f"  - 第{event.day}日: {event.content[:50]}")

        # 一般记忆
        gen_mems = retrieval_result.get('general_memories', [])
        if gen_mems:
            lines.append("\n【相关经历】")
            for event, score in gen_mems[:3]:
                lines.append(f"- 第{event.day}日: {event.content[:60]}")

        # 反思
        reflections = retrieval_result.get('reflections', [])
        if reflections:
            lines.append("\n【反思洞察】")
            for r in reflections[-3:]:
                lines.append(f"- {r.content}")

        return "\n".join(lines) if lines else "暂无相关记忆"

    def retrieve_dialogues(self, current_day: int, k: int = 5) -> List[Tuple[MemoryEvent, float]]:
        """检索对话相关记忆"""
        return self.retrieve("", current_day, k=k,
                           event_types=[MemoryEvent.TYPE_DIALOGUE])

    def retrieve_with_keywords(self, keywords: List[str], current_day: int,
                              k: int = 5) -> List[Tuple[MemoryEvent, float]]:
        """
        基于关键词检索记忆

        用于精确的关键词匹配检索
        """
        query = " ".join(keywords)
        return self.retrieve(query, current_day, k=k)

    def get_memories_as_context(self, current_day: int, k: int = 5) -> str:
        """
        获取记忆作为文本上下文（供LLM直接使用）

        Returns:
            格式化的记忆文本
        """
        memories = self.retrieve("", current_day, k=k)

        if not memories:
            return "暂无相关记忆"

        lines = []
        for event, score in memories:
            lines.append(f"[{event.type}, day{event.day}, imp={event.importance:.2f}] {event.content}")

        return "\n".join(lines)
