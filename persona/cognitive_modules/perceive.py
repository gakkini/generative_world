"""
perceive.py - 感知模块 (Perception)

原论文描述:
- "The agent perceives their environment through their daily observations"
- "They notice other agents and events in their vicinity"
- "Perception is filtered through the agent's current plan and interests"

功能:
- 感知当前环境（地点、其他agent、物品）
- 检测附近的其他agent
- 感知环境变化
- 过滤感知（与当前计划相关的保留）
- 生成感知叙述
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import random


@dataclass
class Perception:
    """感知事件"""
    type: str  # character, event, object, location_change, danger, opportunity
    content: str
    source: Optional[str] = None  # 来源（如对方agent的id）
    urgency: str = 'normal'  # low, normal, high, urgent
    location: Optional[str] = None

    # 感知属性
    is_actionable: bool = False  # 是否可据此行动
    is_memory_trigger: bool = False  # 是否触发记忆
    trigger_memory_id: Optional[str] = None  # 触发的记忆ID

    def __repr__(self):
        return f"<Perception [{self.type}] {self.content[:40]}>"


class PerceptionSystem:
    """
    感知系统

    功能:
    1. 感知环境中的各种元素
    2. 过滤无关感知
    3. 识别可操作的感知
    4. 生成感知叙述
    """

    TYPE_CHARACTER = 'character'
    TYPE_EVENT = 'event'
    TYPE_OBJECT = 'object'
    TYPE_LOCATION_CHANGE = 'location_change'
    TYPE_DANGER = 'danger'
    TYPE_OPPORTUNITY = 'opportunity'
    TYPE_MEMORY_TRIGGER = 'memory_trigger'

    URGENCY_LOW = 'low'
    URGENCY_NORMAL = 'normal'
    URGENCY_HIGH = 'high'
    URGENCY_URGENT = 'urgent'

    # 危险关键词
    DANGER_KEYWORDS = ['危险', '敌人', '攻击', '受伤', '紧急', '危机']

    # 机会关键词
    OPPORTUNITY_KEYWORDS = ['机会', '发现', '惊喜', '难得', '恰好', '刚好']

    def __init__(self):
        self.last_perceptions: List[Perception] = []

    def perceive_environment(self, agent: 'Persona',
                           world: 'World',
                           all_agents: Dict[str, 'Persona']) -> List[Perception]:
        """
        感知当前环境

        Args:
            agent: 当前agent
            world: 世界对象
            all_agents: 所有agent字典

        Returns:
            感知列表
        """
        perceptions = []

        current_loc = agent.spatial.current_location

        if not current_loc:
            return perceptions

        # 1. 感知当前地点
        location_info = world.get_location(current_loc)
        loc_perception = self._perceive_location(agent, location_info)
        if loc_perception:
            perceptions.append(loc_perception)

        # 2. 感知附近的agent
        nearby_agents = self._perceive_nearby_agents(agent, world, all_agents)
        perceptions.extend(nearby_agents)

        # 3. 感知环境中的事件
        event_perceptions = self._perceive_events(agent, world)
        perceptions.extend(event_perceptions)

        # 4. 感知世界事件（通知等）
        notification_perceptions = self._perceive_notifications(agent, world)
        perceptions.extend(notification_perceptions)

        # 5. 检查是否有记忆触发
        memory_trigger_perceptions = self._check_memory_triggers(
            agent, perceptions
        )
        perceptions.extend(memory_trigger_perceptions)

        # 过滤
        perceptions = self.filter_perceptions(perceptions, agent)

        self.last_perceptions = perceptions
        return perceptions

    def _perceive_location(self, agent: 'Persona',
                           location_info: Dict) -> Optional[Perception]:
        """感知当前地点"""
        if not location_info:
            return None

        name = location_info.get('name', '')
        description = location_info.get('description', '')

        # 描述地点特征
        if description:
            return Perception(
                type=self.TYPE_LOCATION_CHANGE,
                content=f"当前位置{name}：{description}",
                location=name,
                urgency=self.URGENCY_NORMAL
            )

        return None

    def _perceive_nearby_agents(self, agent: 'Persona',
                                world: 'World',
                                all_agents: Dict[str, 'Persona']) -> List[Perception]:
        """
        感知附近的agent

        关键: 检测同地点的其他agent
        """
        perceptions = []
        current_loc = agent.spatial.current_location

        # 获取同地点的其他agent
        for other_id, other_loc in world.positions.items():
            if other_id == agent.id:
                continue

            if other_loc == current_loc:
                # 同地点！检查是否是已知agent
                if other_id in all_agents:
                    other_agent = all_agents[other_id]
                    other_name = getattr(other_agent, 'name', other_id)

                    # 获取关系
                    relationship = self._get_relationship_description(
                        agent, other_id
                    )

                    perception = Perception(
                        type=self.TYPE_CHARACTER,
                        content=f"{other_name}也在{world.get_location(current_loc).get('name', '')}，{relationship}",
                        source=other_id,
                        urgency=self.URGENCY_NORMAL,
                        location=current_loc,
                        is_actionable=True
                    )
                    perceptions.append(perception)

        return perceptions

    def _perceive_events(self, agent: 'Persona',
                         world: 'World') -> List[Perception]:
        """
        感知世界事件

        例如: 公告、天气变化、突发事件
        """
        perceptions = []
        current_day = world.time.day

        # 检查世界事件日志中与该agent相关的
        for event in world.event_log[-20:]:  # 最近20条
            if event.get('character') == agent.id:
                continue  # 跳过自己的事件

            if event.get('day') != current_day:
                continue  # 只关注今天的事件

            event_content = event.get('content', '')
            event_type = event.get('type', 'action')

            # 检查危险/机会关键词
            urgency = self.URGENCY_NORMAL

            if any(kw in event_content for kw in self.DANGER_KEYWORDS):
                urgency = self.URGENCY_HIGH

            if any(kw in event_content for kw in self.OPPORTUNITY_KEYWORDS):
                urgency = self.URGENCY_NORMAL
                is_opportunity = True

            perception = Perception(
                type=self.TYPE_EVENT,
                content=f"[世界事件] {event_content}",
                urgency=urgency,
                location=event.get('location')
            )
            perceptions.append(perception)

        return perceptions

    def _perceive_notifications(self, agent: 'Persona',
                               world: 'World') -> List[Perception]:
        """感知通知和邀请"""
        perceptions = []

        # 检查待处理的邀请
        if hasattr(agent, 'pending_invitations'):
            for inv in agent.pending_invitations[-5:]:  # 最近5条
                perception = Perception(
                    type=self.TYPE_EVENT,
                    content=f"收到来自{inv.get('from', '?')}的邀请：{inv.get('content', '')[:50]}",
                    urgency=self.URGENCY_NORMAL,
                    is_actionable=True
                )
                perceptions.append(perception)

        return perceptions

    def _check_memory_triggers(self, agent: 'Persona',
                              current_perceptions: List[Perception]) -> List[Perception]:
        """
        检查是否有感知触发相关记忆

        例如: 在某个地点触发之前在该地点的记忆
        """
        triggered = []

        # 获取agent的记忆系统
        if not hasattr(agent, 'memory'):
            return triggered

        current_loc = agent.spatial.current_location
        if not current_loc:
            return triggered

        # 检查是否有同地点的近期记忆
        recent_at_location = agent.memory.get_recent_events(
            agent.current_day if hasattr(agent, 'current_day') else 1,
            days=7
        )

        for event in recent_at_location:
            if event.location == current_loc and event.type == 'action':
                # 触发记忆
                perception = Perception(
                    type=self.TYPE_MEMORY_TRIGGER,
                    content=f"想起上次在这里：{event.content[:50]}",
                    urgency=self.URGENCY_LOW,
                    is_memory_trigger=True,
                    trigger_memory_id=event.id
                )
                triggered.append(perception)
                break  # 每感知最多触发一条记忆

        return triggered

    def _get_relationship_description(self, agent: 'Persona',
                                     other_id: str) -> str:
        """获取与某人的关系描述"""
        if not hasattr(agent, 'relationships'):
            return "关系未知"

        rel = agent.relationships.get(other_id, {})
        level = rel.get('level', 0)

        if level >= 70:
            return "关系亲密"
        elif level >= 40:
            return "关系友好"
        elif level >= 15:
            return "普通朋友"
        elif level >= -15:
            return "不太熟悉"
        else:
            return "关系紧张"

    def filter_perceptions(self, perceptions: List[Perception],
                          agent: 'Persona') -> List[Perception]:
        """
        过滤感知

        过滤规则:
        1. 与当前计划无关的感知降级
        2. 重复感知去重
        3. 低优先级感知可被忽略
        """
        if not hasattr(agent, 'scratch'):
            return perceptions

        current_plan = agent.scratch.get_context('current_goal', '')

        filtered = []
        seen_content = set()

        for p in perceptions:
            # 去重
            content_hash = hash(p.content[:30])
            if content_hash in seen_content:
                continue
            seen_content.add(content_hash)

            # 如果有当前目标，相关性高的优先
            if current_plan:
                if any(kw in p.content for kw in [current_plan, agent.spatial.current_location or '']):
                    p.urgency = self.URGENCY_HIGH if p.urgency == self.URGENCY_NORMAL else p.urgency

            # 低优先级过滤
            if p.urgency == self.URGENCY_LOW and random.random() < 0.3:
                continue

            filtered.append(p)

        return filtered

    def generate_perception_narrative(self, agent: 'Persona',
                                     world_type: str = 'default') -> str:
        """
        生成感知叙述文本

        用于日记和规划上下文
        """
        if not self.last_perceptions:
            return "未感知到特殊情况"

        lines = []
        world_type = getattr(agent, 'world_type', world_type)

        for p in self.last_perceptions:
            if p.type == self.TYPE_CHARACTER:
                lines.append(f"看到{p.source}在这里，{p.content}")
            elif p.type == self.TYPE_MEMORY_TRIGGER:
                lines.append(f"💭 {p.content}")
            elif p.type == self.TYPE_EVENT:
                lines.append(f"[事件] {p.content}")
            elif p.type == self.TYPE_OPPORTUNITY:
                lines.append(f"✨ {p.content}")
            elif p.type == self.TYPE_DANGER:
                lines.append(f"⚠️ {p.content}")
            else:
                lines.append(p.content)

        if world_type == 'modern_urban':
            # 现代都市风格的感知描述
            return " | ".join(lines) if lines else "周围一切平静"
        else:
            return "；".join(lines) if lines else "四周寂静无声"

    def get_actionable_perceptions(self) -> List[Perception]:
        """获取可操作的感知"""
        return [p for p in self.last_perceptions if p.is_actionable]
