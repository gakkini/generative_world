"""
reflect.py - 反思模块 (Reflection)

原论文描述:
- "The agent reflects on its observations to generate higher-level insights"
- "Reflection enables agents to generalize and reason about their experiences"
- 不是生成"总结"，而是生成"洞察"

输入: 最近发生的事件（记忆流）
过程:
1. 聚类相似事件
2. 从事件中归纳模式
3. 生成高层洞察

示例输出:
- "每当讨论工作时，Klaus会变得沉默"
- "人们通常在感到压力时会寻求社交支持"
- "林念念在阳台画画时心情最好"
"""
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

from ..memory_structures.associative_memory import (
    MemoryEvent, Reflection, AssociativeMemory
)


class ReflectionEngine:
    """
    反思引擎

    核心功能:
    1. 分析近期记忆，识别模式和趋势
    2. 生成高层洞察（不是简单总结）
    3. 将洞察存储到记忆流中
    """

    # 反思阈值
    MIN_EVENTS_FOR_REFLECTION = 5  # 至少需要5条事件才反思
    REFLECTION_INTERVAL_DAYS = 3  # 每3天至少反思一次

    # 分析参数
    PATTERN_THRESHOLD = 3  # 同一类型事件出现N次视为模式
    TOPIC_CLUSTER_THRESHOLD = 2  # 关键词重叠 >= 2 视为同一主题

    def __init__(self, memory: AssociativeMemory):
        self.memory = memory
        self.last_reflection_day = 0

    def should_reflect(self, current_day: int) -> bool:
        """
        判断是否应该进行反思

        条件:
        1. 距离上次反思 >= REFLECTION_INTERVAL_DAYS
        2. 有足够的近期记忆
        """
        if current_day - self.last_reflection_day < self.REFLECTION_INTERVAL_DAYS:
            return False

        recent_events = self.memory.get_recent_events(current_day, days=7)
        if len(recent_events) < self.MIN_EVENTS_FOR_REFLECTION:
            return False

        return True

    def generate_reflections(self, current_day: int,
                            agent_name: str = "Agent",
                            agent_context: Optional[Dict] = None) -> List[Reflection]:
        """
        生成反思

        步骤:
        1. 获取近期记忆
        2. 按主题聚类
        3. 按人物聚类
        4. 识别行为模式
        5. 生成洞察

        Args:
            current_day: 当前天数
            agent_name: agent名字（用于生成个性化洞察）
            agent_context: agent上下文（性格、MBTI等）

        Returns:
            生成的反思列表
        """
        recent_events = self.memory.get_recent_events(current_day, days=7)

        if len(recent_events) < self.MIN_EVENTS_FOR_REFLECTION:
            return []

        # 聚类分析
        topic_clusters = self._cluster_by_topic(recent_events)
        person_clusters = self._cluster_by_person(recent_events)
        type_clusters = self._cluster_by_type(recent_events)

        # 生成洞察
        insights = []

        # 1. 基于主题聚类的洞察
        for topic, events in topic_clusters.items():
            if len(events) >= 2:
                insight = self._generate_topic_insight(topic, events, agent_name)
                if insight:
                    insights.append(insight)

        # 2. 基于人物的洞察
        for person_id, events in person_clusters.items():
            if len(events) >= 2:
                insight = self._generate_person_insight(person_id, events, agent_name)
                if insight:
                    insights.append(insight)

        # 3. 基于行为类型的洞察
        for event_type, events in type_clusters.items():
            if len(events) >= self.PATTERN_THRESHOLD:
                insight = self._generate_behavior_insight(event_type, events, agent_name)
                if insight:
                    insights.append(insight)

        # 4. 基于agent上下文的个性化洞察
        if agent_context:
            context_insights = self._generate_context_insights(
                recent_events, agent_context, agent_name
            )
            insights.extend(context_insights)

        # 存储反思到记忆
        reflections = []
        for insight_text in insights:
            ref = self.memory.add_reflection(
                insight_text,
                current_day,
                related_events=[e.id for e in recent_events]
            )
            reflections.append(ref)

        if reflections:
            self.last_reflection_day = current_day

        return reflections

    def _cluster_by_topic(self, events: List[MemoryEvent]) -> Dict[str, List[MemoryEvent]]:
        """
        按主题聚类事件

        使用关键词重叠判断主题相似性
        """
        clusters = defaultdict(list)

        for event in events:
            # 提取关键词
            keywords = self._extract_keywords(event.content)
            if not keywords:
                clusters['其他'].append(event)
                continue

            # 尝试合并到已有簇
            merged = False
            for existing_topic in list(clusters.keys()):
                if existing_topic == '其他':
                    continue
                if self._topics_overlap(keywords, self._extract_keywords(existing_topic)):
                    clusters[existing_topic].append(event)
                    merged = True
                    break

            if not merged:
                # 创建新簇，以最常见的关键词作为主题名
                primary_topic = max(keywords, key=lambda w: len(w))
                clusters[primary_topic].append(event)

        # 过滤掉太小的簇
        return {k: v for k, v in clusters.items() if len(v) >= 2}

    def _cluster_by_person(self, events: List[MemoryEvent]) -> Dict[str, List[MemoryEvent]]:
        """按参与者聚类"""
        clusters = defaultdict(list)

        for event in events:
            if event.participants:
                for person_id in event.participants:
                    clusters[person_id].append(event)

        return {k: v for k, v in clusters.items() if len(v) >= 2}

    def _cluster_by_type(self, events: List[MemoryEvent]) -> Dict[str, List[MemoryEvent]]:
        """按事件类型聚类"""
        clusters = defaultdict(list)

        for event in events:
            clusters[event.type].append(event)

        return dict(clusters)

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单实现：过滤停用词
        stopwords = {
            '的', '了', '在', '是', '我', '你', '他', '她', '它',
            '这', '那', '和', '与', '或', '了', '着', '过', '有',
            '个', '一', '上', '下', '中', '来', '去', '到', '把',
            '说', '道', '曰', '云', '一个', '什么', '怎么', '如何'
        }

        words = text.lower().split()
        keywords = [w for w in words if len(w) >= 2 and w not in stopwords]
        return keywords

    def _topics_overlap(self, keywords1: List[str], keywords2: List[str]) -> bool:
        """判断两个主题是否重叠"""
        set1 = set(keywords1)
        set2 = set(keywords2)
        overlap = len(set1 & set2)
        return overlap >= self.TOPIC_CLUSTER_THRESHOLD

    def _generate_topic_insight(self, topic: str,
                                events: List[MemoryEvent],
                                agent_name: str) -> Optional[str]:
        """
        基于主题聚类生成洞察

        例如:
        - "最近频繁讨论'工作'话题"
        - "关于'约会'的活动明显增多"
        """
        if len(events) < 2:
            return None

        event_contents = [e.content for e in events]

        # 分析趋势
        days = [e.day for e in events]
        day_range = max(days) - min(days) if len(days) > 1 else 1
        frequency = len(events) / max(day_range, 1)

        # 生成洞察
        if frequency > 1.0:
            freq_desc = "持续关注"
        elif len(events) >= 4:
            freq_desc = "经常思考"
        else:
            freq_desc = "偶尔涉及"

        # 提取主题相关的内容描述
        avg_importance = sum(e.importance for e in events) / len(events)

        if avg_importance > 0.7:
            importance_desc = "很重要的话题"
        elif avg_importance > 0.5:
            importance_desc = "值得关注的话题"
        else:
            importance_desc = "日常话题"

        return f"{freq_desc}'{topic}'，这是{importance_desc}。"

    def _generate_person_insight(self, person_id: str,
                                 events: List[MemoryEvent],
                                 agent_name: str) -> Optional[str]:
        """
        基于人物聚类生成洞察

        例如:
        - "与{lin_niannian}的对话增加，我们的关系似乎更亲密了"
        - "{person}在对话中经常提到'工作'相关话题"
        """
        if len(events) < 2:
            return None

        # 分析对话类型分布
        dialogue_count = sum(1 for e in events if e.type == 'dialogue')
        action_count = sum(1 for e in events if e.type == 'action')

        # 分析情感趋势（简化版：基于重要性）
        avg_importance = sum(e.importance for e in events) / len(events)

        # 生成洞察
        if dialogue_count > action_count:
            interaction_desc = "主要是聊天交流"
        else:
            interaction_desc = "共同活动较多"

        if avg_importance > 0.65:
            relationship_desc = "与对方的互动很重要"
        else:
            relationship_desc = "普通相处"

        days = sorted(set(e.day for e in events))
        if len(days) >= 2 and days[-1] - days[0] <= 3:
            recency_desc = "最近互动频繁"
        elif len(events) >= 3:
            recency_desc = "持续保持联系"
        else:
            recency_desc = "偶尔有所交流"

        return f"{recency_desc}与{person_id}，{relationship_desc}，{interaction_desc}。"

    def _generate_behavior_insight(self, event_type: str,
                                   events: List[MemoryEvent],
                                   agent_name: str) -> Optional[str]:
        """
        基于行为类型生成洞察

        例如:
        - "最近社交活动明显增多"
        - "独处时间减少，社交需求增加"
        """
        if len(events) < self.PATTERN_THRESHOLD:
            return None

        type_labels = {
            'dialogue': '对话交流',
            'action': '实际行动',
            'observation': '观察体验',
            'reflection': '反思思考',
            'social_event': '社交活动'
        }

        type_label = type_labels.get(event_type, event_type)

        # 分析频率变化（简化）
        days = [e.day for e in events]
        if len(days) >= 2:
            day_span = max(days) - min(days)
            if day_span > 0:
                frequency = len(events) / day_span
                if frequency > 1.5:
                    freq_desc = "显著增加"
                elif frequency < 0.5:
                    freq_desc = "明显减少"
                else:
                    freq_desc = "保持稳定"
            else:
                freq_desc = "集中在短时间内"
        else:
            freq_desc = "偶尔出现"

        return f"{agent_name}近期的{type_label}{freq_desc}。"

    def _generate_context_insights(self, events: List[MemoryEvent],
                                   agent_context: Dict,
                                   agent_name: str) -> List[str]:
        """
        基于agent上下文生成个性化洞察

        Args:
            agent_context: 包含性格、MBTI、角色设定等信息
        """
        insights = []

        # 获取MBTI或性格信息
        mbti = agent_context.get('mbti', '')
        personality = agent_context.get('personality', '')
        occupation = agent_context.get('occupation', '')

        # 分析行为与性格的匹配度
        dialogue_events = [e for e in events if e.type == 'dialogue']

        if mbti:
            # E/I 维度
            if 'E' in mbti and len(dialogue_events) >= 4:
                insights.append(
                    f"{agent_name}是{mbti}外向型，与人交流是能量来源，近期的社交活动让人精力充沛。"
                )
            elif 'I' in mbti and len(dialogue_events) <= 2:
                insights.append(
                    f"{agent_name}是{mbti}内向型，独处时光很重要，需要平衡社交和个人时间。"
                )

        # 基于职业的洞察
        if occupation and len(dialogue_events) >= 3:
            work_related = [
                e for e in dialogue_events
                if any(kw in e.content.lower() for kw in ['工作', '项目', '任务', '开会', '客户'])
            ]
            if len(work_related) >= 2:
                insights.append(
                    f"作为{occupation}，{agent_name}最近经常讨论工作话题。"
                )

        return insights

    def generate_insight_about_environment(self, current_day: int,
                                          world_type: str = 'default') -> str:
        """
        生成关于环境的洞察

        分析近期记忆中地点和活动的分布
        """
        recent_events = self.memory.get_recent_events(current_day, days=7)

        # 地点分布
        location_counts = defaultdict(int)
        for e in recent_events:
            if e.location:
                location_counts[e.location] += 1

        if location_counts:
            most_visited = max(location_counts.items(), key=lambda x: x[1])
            return f"最近主要活动在{most_visited[0]}，共{most_visited[1]}次。"

        return ""

    def get_recent_reflections(self, current_day: int, days: int = 7) -> list:
        """获取近期的反思列表（兼容接口）"""
        return self.memory.get_recent_reflections(current_day, days=days)

    def get_insights_for_planning(self, current_day: int, k: int = 3) -> str:
        """
        获取用于规划的洞察文本

        Returns:
            格式化的洞察字符串
        """
        reflections = self.memory.get_recent_reflections(current_day, days=7)

        if not reflections:
            return "暂无反思洞察"

        lines = []
        for r in reflections[-k:]:
            lines.append(f"- {r.content}")

        return "\n".join(lines)
