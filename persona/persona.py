"""
persona.py - 智能Agent (Generative Agent)

按照Stanford Generative Agents论文架构实现的核心Agent类

整合了:
- 记忆系统 (AssociativeMemory)
- 工作记忆 (Scratch/WorkingMemory)
- 空间记忆 (SpatialMemory)
- 认知模块 (Perceive, Retrieve, Plan, Execute, Converse, Reflect)

主循环 tick():
1. perceive() - 感知环境
2. retrieve() - 检索相关记忆
3. plan() - 生成计划
4. execute() - 执行动作
5. converse() - 对话交互
6. reflect() - 反思生成洞察
"""
from typing import Dict, List, Any, Optional

from .memory_structures.associative_memory import AssociativeMemory
from .memory_structures.scratch import Scratch, Plan
from .memory_structures.spatial_memory import SpatialMemory

from .cognitive_modules.retrieve import Retriever
from .cognitive_modules.reflect import ReflectionEngine
from .cognitive_modules.plan import PlanGenerator, Action
from .cognitive_modules.execute import Executor
from .cognitive_modules.perceive import PerceptionSystem, Perception
from .cognitive_modules.converse import DialogueGenerator, Dialogue


class Persona:
    """
    智能Agent - 斯坦福Generative Agents论文实现

    属性:
    - id, name: 基本信息
    - personality, background: 角色设定
    - memory: 关联记忆流
    - scratch: 工作记忆
    - spatial: 空间记忆
    - cognitive_modules: 各认知模块
    - relationships: 关系字典

    方法:
    - tick(): 主循环，一次模拟step
    - perceive(): 感知环境
    - plan(): 生成计划
    - execute(): 执行动作
    - reflect(): 反思
    - interact(): 与其他agent交互
    """

    def __init__(self, config: Dict,
                 world: 'World',
                 llm_client=None,
                 # 增强模块（可选）
                 social_network=None,
                 relationship_manager=None,
                 event_bus=None,
                 behavior_engine=None):
        """
        初始化Agent

        Args:
            config: 角色配置字典
            world: 世界对象
            llm_client: LLM客户端（可选）
            social_network: 社交网络（可选）
            relationship_manager: 关系管理器（可选）
            event_bus: 事件总线（可选）
            behavior_engine: 行为引擎（可选）
        """
        # 基本信息
        self.id = config['id']
        self.name = config['name']
        self.personality = config.get('personality', '')
        self.background = config.get('background', '')
        self.age = config.get('age', 0)
        self.role = config.get('role', 'npc')

        # MBTI/角色设定
        self.mbti = config.get('mbti', '')
        self.occupation = config.get('occupation', '')
        self.system_prompt = config.get('system_prompt', '')

        # 宗门/阵营（修仙世界用）
        self.sect = config.get('sect', 'none')
        self.cultivation = config.get('cultivation', '凡人')

        # 世界类型
        self.world_type = world.config.get('world', {}).get('type', 'default')

        # 世界引用
        self.world = world

        # 关联记忆流
        self.memory = AssociativeMemory(self.id)

        # 工作记忆
        self.scratch = Scratch(self.id)

        # 空间记忆
        current_loc = world.get_character_location(self.id)
        loc_name = world.get_location(current_loc).get('name', current_loc) if current_loc else ''
        self.spatial = SpatialMemory(self.id)
        self.spatial.set_current_location(current_loc, loc_name)

        # 认知模块
        self.retriever = Retriever(self.memory)
        self.reflection_engine = ReflectionEngine(self.memory)
        self.planner = PlanGenerator(llm_client)
        self.executor = Executor()
        self.perception_system = PerceptionSystem()
        self.dialogue_gen = DialogueGenerator(llm_client)

        # 当前计划
        self.current_plan: Optional[Plan] = None

        # 今日数据
        self.current_day = world.time.day
        self.today_perceptions: List[Perception] = []
        self.today_dialogues: List[Dialogue] = []
        self.today_actions: List[Dict] = []

        # 关系
        self.relationships: Dict[str, Dict] = {}

        # 增强模块
        self.social_network = social_network
        self.relationship_manager = relationship_manager
        self.event_bus = event_bus
        self.behavior_engine = behavior_engine

        # 待处理事件
        self.pending_invitations: List[Dict] = []

        # LLM客户端
        self.llm_client = llm_client

        # 初始化关系
        self._init_relationships()

    def _init_relationships(self):
        """初始化关系"""
        for other_config in self.world.config.get('characters', []):
            if other_config['id'] == self.id:
                continue

            other_sect = other_config.get('sect', 'none')
            other_name = other_config.get('name', other_config['id'])

            # 基于宗门设置初始关系
            if other_sect == self.sect:
                initial_level = 30
            elif other_sect in getattr(self, 'hostile_sects', []):
                initial_level = -30
            else:
                initial_level = 0

            self.relationships[other_config['id']] = {
                'name': other_name,
                'type': 'stranger',
                'level': initial_level,
                'history': []
            }

    # ==================== 主循环 ====================

    def tick(self, all_agents: Dict[str, 'Persona']) -> Dict[str, Any]:
        """
        主循环 tick - 一次完整的模拟step

        步骤:
        1. 感知环境
        2. 检索相关记忆
        3. 生成计划
        4. 执行动作
        5. 对话交互
        6. 反思

        Returns:
            当日活动摘要
        """
        self.current_day = self.world.time.day

        # 更新当前位置
        current_loc = self.world.get_character_location(self.id)
        if current_loc and current_loc != self.spatial.current_location:
            loc_name = self.world.get_location(current_loc).get('name', current_loc)
            self.spatial.set_current_location(current_loc, loc_name, self.current_day)

        result = {
            'agent_id': self.id,
            'agent_name': self.name,
            'day': self.current_day,
            'location': self.spatial.current_location,
            'perceptions': [],
            'plan_summary': '',
            'actions': [],
            'dialogues': [],
            'reflection': None
        }

        # 1. 感知
        perceptions = self._do_perceive(all_agents)
        result['perceptions'] = [p.content for p in perceptions]

        # 2. 检查互动
        dialogues = self._do_interact(all_agents)
        result['dialogues'] = [d.get_summary() for d in dialogues]

        # 3. 规划
        plan = self._do_plan()
        if plan:
            result['plan_summary'] = plan.get_summary()

        # 4. 执行
        actions = self._do_execute()
        result['actions'] = [a['description'] for a in actions]

        # 5. 记录到世界事件
        for action in actions:
            self.world.add_event(self.id, action['description'], 'action')

        # 6. 反思（每隔一定天数）
        if self.reflection_engine.should_reflect(self.current_day):
            reflection = self._do_reflect()
            result['reflection'] = reflection

        # 清空每日数据
        self._clear_daily_data()

        return result

    # ==================== 感知 ====================

    def _do_perceive(self, all_agents: Dict[str, 'Persona']) -> List[Perception]:
        """执行感知"""
        perceptions = self.perception_system.perceive_environment(
            self, self.world, all_agents
        )
        self.today_perceptions = perceptions

        # 记录到工作记忆
        for p in perceptions:
            self.scratch.add_perception(p)

        # 将重要感知写入记忆
        for p in perceptions:
            if p.urgency in ['high', 'urgent']:
                self.memory.add(
                    content=f"[感知] {p.content}",
                    day=self.current_day,
                    location=self.spatial.current_location,
                    event_type='observation'
                )

            # 如果感知到其他角色，记录到空间记忆
            if p.type == 'character' and p.source:
                self.spatial.record_person_encountered(p.source)

        return perceptions

    def get_perception_narrative(self) -> str:
        """获取感知叙述"""
        return self.perception_system.generate_perception_narrative(self, self.world_type)

    # ==================== 规划 ====================

    def _do_plan(self) -> Optional[Plan]:
        """执行规划"""
        # 1. 获取环境状态
        env_state = self.world.get_state_summary()

        # 2. 检索相关记忆（关键！基于加权检索）
        retrieval = self.retriever.retrieve_for_planning(
            current_day=self.current_day,
            location=self.spatial.current_location,
            nearby_agents=self._get_nearby_agent_ids(),
            current_activity=self.scratch.get_context('current_goal')
        )

        # 3. 获取反思
        reflection_context = self.reflection_engine.get_insights_for_planning(
            self.current_day
        )

        # 4. 生成计划
        self.current_plan = self.planner.generate_plan(
            agent=self,
            current_day=self.current_day,
            env_state=env_state,
            retrieval_context=retrieval,
            reflection_context=reflection_context
        )

        self.scratch.current_plan = self.current_plan

        return self.current_plan

    def _get_nearby_agent_ids(self) -> List[str]:
        """获取附近的agent ID"""
        nearby = []
        current_loc = self.spatial.current_location
        if not current_loc:
            return nearby

        for other_id, other_loc in self.world.positions.items():
            if other_id != self.id and other_loc == current_loc:
                nearby.append(other_id)

        return nearby

    # ==================== 执行 ====================

    def _do_execute(self) -> List[Dict]:
        """执行计划"""
        if not self.current_plan:
            return []

        results = self.executor.execute_plan(self, self.current_plan, self.world)

        actions = []
        for result in results:
            if result.status == 'success':
                actions.append({
                    'description': result.result_text,
                    'action': result.action.name,
                    'status': 'success'
                })
            else:
                actions.append({
                    'description': result.action.description,
                    'action': result.action.name,
                    'status': f"failed: {result.error}"
                })

        self.today_actions = actions
        return actions

    # ==================== 对话 ====================

    def _do_interact(self, all_agents: Dict[str, 'Persona']) -> List[Dialogue]:
        """执行对话交互"""
        dialogues = []

        # 检查附近的agent
        nearby_agents = []
        current_loc = self.spatial.current_location

        for other_id, other_loc in self.world.positions.items():
            if other_id == self.id:
                continue
            if other_loc == current_loc and other_id in all_agents:
                other_agent = all_agents[other_id]
                if self.dialogue_gen.should_initiate(self, other_agent, "同处一地"):
                    nearby_agents.append(other_agent)

        # 与第一个可互动的agent对话
        if nearby_agents:
            other = nearby_agents[0]
            context = {
                'location_name': self.spatial.current_location_name,
                'day': self.current_day,
                'topic': '日常闲聊'
            }

            dialogue = self.dialogue_gen.generate_dialogue(
                self, other, context, max_turns=3
            )

            # 记录对话
            self.today_dialogues.append(dialogue)
            dialogues.append(dialogue)

            # 记录对话到记忆
            for utterance in dialogue.utterances:
                if utterance.speaker_id == self.id:
                    self.memory.add(
                        content=f"[对话] 对{other.name}说: {utterance.content}",
                        day=self.current_day,
                        location=self.spatial.current_location,
                        participants=[other.id],
                        event_type='dialogue'
                    )

            # 更新关系
            sentiment = dialogue.sentiment_trend
            self._update_relationship_after_dialogue(other, dialogue, sentiment)

            # 记录到社交网络
            if self.social_network:
                self.social_network.record_interaction(
                    self.id, other.id, 'dialogue',
                    self.current_day, sentiment * 10
                )

        return dialogues

    def _update_relationship_after_dialogue(self, other: 'Persona',
                                           dialogue: Dialogue,
                                           sentiment: float):
        """对话后更新关系"""
        if other.id not in self.relationships:
            self.relationships[other.id] = {
                'name': other.name,
                'type': 'acquaintance',
                'level': 0,
                'history': []
            }

        rel = self.relationships[other.id]

        # 简单关系更新
        if dialogue.sentiment_trend > 0.3:
            rel['level'] = min(rel['level'] + 5, 100)
        elif dialogue.sentiment_trend < -0.3:
            rel['level'] = max(rel['level'] - 10, -100)
        else:
            rel['level'] += 0  # 中性不变

        rel['history'].append(dialogue.get_summary())

        # 同步到RelationshipManager
        if self.relationship_manager:
            self.relationship_manager.record_interaction(
                self.id, other.id, 'dialogue',
                sentiment, self.current_day,
                self.spatial.current_location
            )

    # ==================== 反思 ====================

    def _do_reflect(self) -> str:
        """执行反思"""
        # 获取agent上下文
        agent_context = {
            'name': self.name,
            'personality': self.personality,
            'mbti': self.mbti,
            'occupation': self.occupation,
            'world_type': self.world_type
        }

        reflections = self.reflection_engine.generate_reflections(
            self.current_day,
            agent_name=self.name,
            agent_context=agent_context
        )

        if reflections:
            return "\n".join([r.content for r in reflections[-3:]])

        return ""

    # ==================== 辅助方法 ====================

    def _clear_daily_data(self):
        """清空每日数据"""
        self.today_perceptions = []
        self.today_dialogues = []
        self.today_actions = []
        self.scratch.pending_actions = []

    def get_relationship_with(self, other_id: str) -> Dict:
        """获取与某人的关系"""
        return self.relationships.get(other_id, {
            'type': 'unknown',
            'level': 0
        })

    def get_context_for_llm(self) -> Dict[str, Any]:
        """获取供LLM使用的上下文"""
        recent_events = self.memory.get_recent_events(self.current_day, days=7)
        recent_reflections = self.memory.get_recent_reflections(self.current_day, days=7)

        return {
            'name': self.name,
            'personality': self.personality,
            'current_location': self.spatial.current_location,
            'location_name': self.spatial.current_location_name,
            'world_time': self.world.time.get_full_time_str(),
            'today_perceptions': [p.content for p in self.today_perceptions],
            'today_dialogues': [d.get_summary() for d in self.today_dialogues],
            'recent_events': [e.content for e in recent_events[-10:]],
            'recent_reflections': [r.content for r in recent_reflections[-5:]],
            'memory_summary': self.memory.get_summary(self.current_day),
            'relationships': {
                k: {'level': v['level'], 'type': v['type']}
                for k, v in self.relationships.items()
            }
        }

    def write_diary(self) -> str:
        """生成日记"""
        ctx = self.get_context_for_llm()
        world_type = self.world_type

        if world_type == 'modern_urban':
            lines = [
                f"【日记】{ctx['name']} · {ctx['world_time']}",
                f"地点：{ctx['location_name']}",
            ]
        else:
            lines = [
                f"【修仙日志】{ctx['name']} · {ctx['world_time']}",
                f"地点：{ctx['location_name']}",
            ]

        # 今日感知
        if ctx['today_perceptions']:
            lines.append("\n今日感知：")
            for p in ctx['today_perceptions'][:3]:
                lines.append(f"  - {p}")

        # 今日对话
        if ctx['today_dialogues']:
            lines.append("\n今日对话：")
            for d in ctx['today_dialogues']:
                lines.append(f"  - {d}")

        # 今日行动
        if ctx.get('today_actions'):
            lines.append("\n今日行动：")
            for a in ctx['today_actions']:
                lines.append(f"  - {a}")

        # 反思
        if ctx['recent_reflections']:
            lines.append("\n反思：")
            for r in ctx['recent_reflections'][-2:]:
                lines.append(f"  - {r}")

        return "\n".join(lines)

    def add_memory(self, content: str, event_type: str = 'action',
                   participants: List[str] = None):
        """直接添加记忆"""
        self.memory.add(
            content=content,
            day=self.current_day,
            location=self.spatial.current_location,
            participants=participants or [],
            event_type=event_type
        )
