"""
scratch.py - 暂存器 / 工作记忆 (Working Memory / Scratch)

原论文描述:
- Scratch: 规划时使用的短期记忆
- "The agent's working memory includes their mental state and plan"

功能:
- 当前计划的上下文
- 正在执行的子任务
- 当前的关注点
- 近期感知缓冲
- 对话上下文栈
"""
from typing import List, Dict, Any, Optional


class Scratch:
    """
    工作记忆/暂存器

    类似于计算机的RAM，用于规划期间的临时存储
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id

        # 计划相关
        self.current_plan: Optional['Plan'] = None  # 当前执行计划
        self.plan_index: int = 0  # 当前计划执行到哪一步
        self.plan_context: Dict[str, Any] = {}  # 计划执行上下文

        # 注意力相关
        self.attending_to: Optional[str] = None  # 当前关注点
        self.attention_depth: int = 0  # 注意力深度

        # 感知缓冲
        self.perception_buffer: List[Any] = []  # 最近感知
        self.last_perception_summary: str = ""  # 最后感知描述

        # 对话栈
        self.conversation_stack: List[Dict] = []  # 对话上下文栈
        self.current_dialogue_topic: Optional[str] = None

        # 情绪/状态
        self.mood: str = "neutral"  # neutral/happy/frustrated/excited/etc
        self.energy: float = 0.8  # 精力水平 0-1

        # 待处理动作队列
        self.pending_actions: List[Dict] = []

        # 反思缓存
        self.last_reflection_day: int = 0
        self.reflection_needed: bool = False

    def set_context(self, key: str, value: Any):
        """设置上下文"""
        self.plan_context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """获取上下文"""
        return self.plan_context.get(key, default)

    def clear_context(self):
        """清空上下文"""
        self.plan_context = {}

    def push_action(self, action: Dict):
        """添加待执行动作"""
        self.pending_actions.append(action)

    def pop_action(self) -> Optional[Dict]:
        """取出下一个待执行动作"""
        if self.pending_actions:
            return self.pending_actions.pop(0)
        return None

    def add_perception(self, perception: Any):
        """添加感知到缓冲"""
        self.perception_buffer.append(perception)
        # 保持缓冲在合理大小
        if len(self.perception_buffer) > 20:
            self.perception_buffer = self.perception_buffer[-20:]

    def start_dialogue(self, partner_id: str, topic: str = None):
        """开始一段对话"""
        ctx = {
            'partner_id': partner_id,
            'topic': topic,
            'turns': 0
        }
        self.conversation_stack.append(ctx)
        self.current_dialogue_topic = topic

    def end_dialogue(self):
        """结束当前对话"""
        if self.conversation_stack:
            self.conversation_stack.pop()
        if self.conversation_stack:
            self.current_dialogue_topic = self.conversation_stack[-1].get('topic')
        else:
            self.current_dialogue_topic = None

    def get_current_dialogue(self) -> Optional[Dict]:
        """获取当前对话上下文"""
        if self.conversation_stack:
            return self.conversation_stack[-1]
        return None

    def set_mood(self, mood: str):
        """设置情绪"""
        self.mood = mood

    def adjust_energy(self, delta: float):
        """调整精力"""
        self.energy = max(0.0, min(1.0, self.energy + delta))

    def clear(self):
        """清空工作记忆"""
        self.current_plan = None
        self.plan_index = 0
        self.plan_context = {}
        self.attending_to = None
        self.attention_depth = 0
        self.perception_buffer = []
        self.last_perception_summary = ""
        self.conversation_stack = []
        self.current_dialogue_topic = None
        self.pending_actions = []


class Plan:
    """
    计划对象

    原论文描述:
    - "The agent generates a long-term plan at the beginning of each day"
    - "The plan contains a rough schedule for the morning, afternoon, and evening"
    - "The agent also generates a reactive plan for unexpected events"
    """

    TIME_MORNING = 'morning'
    TIME_AFTERNOON = 'afternoon'
    TIME_EVENING = 'evening'

    def __init__(self, agent_id: str, current_day: int):
        self.agent_id = agent_id
        self.day = current_day

        # 时间段计划
        self.morning: List[str] = []  # 早上计划动作描述
        self.afternoon: List[str] = []  # 下午计划
        self.evening: List[str] = []  # 晚上计划

        # 具体动作序列
        self.actions: List[Dict] = []  # [{'type': 'action', 'description': '...'}, ...]

        # 预期结果
        self.expected_outcomes: List[str] = []

        # 元数据
        self.created_at = None  # 将在generate时设置
        self.status: str = 'created'  # created/in_progress/completed/aborted

    def set_morning_actions(self, actions: List[str]):
        self.morning = actions

    def set_afternoon_actions(self, actions: List[str]):
        self.afternoon = actions

    def set_evening_actions(self, actions: List[str]):
        self.evening = actions

    def add_action(self, action_type: str, description: str, **kwargs):
        """添加动作"""
        action = {
            'type': action_type,
            'description': description,
            **kwargs
        }
        self.actions.append(action)

    def get_next_action(self) -> Optional[Dict]:
        """获取下一个待执行动作"""
        if self.actions:
            return self.actions[0]
        return None

    def advance(self):
        """推进到下一个动作"""
        if self.actions:
            self.actions.pop(0)

    def get_summary(self) -> str:
        """获取计划摘要"""
        parts = []
        if self.morning:
            parts.append(f"上午: {', '.join(self.morning)}")
        if self.afternoon:
            parts.append(f"下午: {', '.join(self.afternoon)}")
        if self.evening:
            parts.append(f"晚上: {', '.join(self.evening)}")
        return " | ".join(parts)

    def to_dict(self) -> dict:
        return {
            'agent_id': self.agent_id,
            'day': self.day,
            'morning': self.morning,
            'afternoon': self.afternoon,
            'evening': self.evening,
            'actions': self.actions,
            'expected_outcomes': self.expected_outcomes,
            'status': self.status
        }
