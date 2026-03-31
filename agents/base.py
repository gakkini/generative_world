"""
Agent基类 - 整合所有认知模块
增强版：集成 ReflectionEngine, RelationshipManager, EventBus, SocialNetwork, BehaviorSpread
"""
import random
from .memory import AssociativeMemory, WorkingMemory
from .planning import PlanGenerator, Action, Plan
from .perception import PerceptionSystem, PerceptionEvent
from .dialogue import DialogueGenerator, Dialogue


class DialogueContext:
    """轻量级对话上下文对象，避免重复创建Agent实例"""
    def __init__(self, id, name, sect, cultivation, current_location):
        self.id = id
        self.name = name
        self.sect = sect
        self.cultivation = cultivation
        self.current_location = current_location


class Agent:
    """
    完整的Agent智能体
    整合：记忆 + 感知 + 规划 + 对话 + 日记 + 反思 + 关系 + 社交网络
    """
    
    def __init__(self, config, world, 
                 social_network=None,
                 relationship_manager=None,
                 event_bus=None,
                 behavior_engine=None):
        # 基本信息
        self.id = config['id']
        self.name = config['name']
        self.sect = config['sect']
        self.age = config['age']
        self.cultivation = config.get('cultivation', '凡人')
        self.personality = config.get('personality', '')
        self.background = config.get('background', '')
        self.role = config.get('role', 'npc')
        
        # 目标与关系
        self.goals = config.get('goals', [])
        self.relationships = {}  # character_id -> {type, level, ...}
        
        # 敌对势力
        self.hostile_sects = config.get('hostile_sects', [])
        
        # 世界引用
        self.world = world
        self.current_location = world.get_character_location(self.id)
        
        # 核心模块
        self.memory = AssociativeMemory(self.id)  # 关联记忆
        self.working_memory = WorkingMemory(self.id)  # 工作记忆
        self.perception = PerceptionSystem()  # 感知系统
        self.planner = PlanGenerator()  # 规划器
        self.dialogue_gen = DialogueGenerator()  # 对话生成器
        
        # ========== 新增模块 ==========
        # 反思引擎
        self.reflection_engine = None
        
        # 关系管理器（可选，由外部注入）
        self.relationship_manager = relationship_manager
        
        # 事件总线（可选）
        self.event_bus = event_bus
        
        # 社交网络（可选）
        self.social_network = social_network
        
        # 行为传播引擎（可选）
        self.behavior_engine = behavior_engine
        
        # 待处理的社交事件
        self.pending_invitations = []
        self.active_social_events = []
        
        # ========== 原有初始化 ==========
        
        # 当前计划
        self.current_plan = None
        self.current_actions = []
        
        # 今日感知
        self.today_perceptions = []
        self.today_dialogues = []
        
        # 初始化
        self._init_relationships()
        self._init_enhanced_modules()
    
    def _init_enhanced_modules(self):
        """初始化增强模块"""
        # 延迟导入避免循环依赖
        try:
            from .reflection import ReflectionEngine
            from .social_network import SocialNetwork
            from .relationship import RelationshipManager
            from .event_bus import EventBus
            from .behavior_spread import EmergentBehaviorEngine
            
            # 初始化反思引擎
            self.reflection_engine = ReflectionEngine(self.id)
            
            # 如果没有提供关系管理器，创建本地版本并同步
            if self.relationship_manager is None:
                self.relationship_manager = RelationshipManager()
            
            # 如果提供了社交网络，注册自己
            if self.social_network:
                self.social_network.add_agent(self.id)
            
            # 如果有事件总线，订阅相关事件
            if self.event_bus:
                self.event_bus.subscribe(self.id, '*', self._handle_event)
            
        except ImportError as e:
            print(f"Warning: Enhanced modules not available: {e}")
    
    def _handle_event(self, event):
        """处理收到的事件"""
        if event.type == 'invitation':
            # 收到邀请
            self.pending_invitations.append({
                'event_id': event.id,
                'content': event.content,
                'from': event.source_id,
                'day': event.day
            })
        elif event.type == 'notification':
            # 收到通知
            self.add_memory_event(
                f"收到通知：{event.content}",
                event_type='notification'
            )
    
    # ==================== 关系系统 ====================
    
    def _init_relationships(self):
        """初始化关系"""
        # 根据宗门设置初始关系
        sect_relations = {
            'canglange': ['qingming'],  # 友好宗门
            'qingming': ['canglange'],
            'zixu': [],  # 中立
            'chiyan': ['canglange', 'qingming'],  # 敌对
        }
        
        friendly = sect_relations.get(self.sect, [])
        for other_config in self.world.config['characters']:
            if other_config['id'] == self.id:
                continue
            other_sect = other_config['sect']
            
            if other_sect in friendly:
                self.relationships[other_config['id']] = {
                    'type': 'friendly',
                    'level': 30,
                    'history': []
                }
            elif other_sect in self.hostile_sects:
                self.relationships[other_config['id']] = {
                    'type': 'hostile',
                    'level': -30,
                    'history': []
                }
            else:
                self.relationships[other_config['id']] = {
                    'type': 'stranger',
                    'level': 0,
                    'history': []
                }
        
        # 同步到 RelationshipManager
        if self.relationship_manager:
            for other_id, rel_data in self.relationships.items():
                rel = self.relationship_manager.initialize_relationship(
                    self.id,
                    other_id,
                    initial_affinity=rel_data.get('level', 0)
                )
    
    def update_relationship(self, other_id: str, delta: float, 
                          interaction_type: str = 'dialogue',
                          sentiment: float = 0.0):
        """
        更新与某人的关系
        
        Args:
            other_id: 对方ID
            delta: 关系变化量
            interaction_type: 交互类型
            sentiment: 情感极性 -1.0 ~ 1.0
        """
        if other_id not in self.relationships:
            self.relationships[other_id] = {
                'type': 'stranger',
                'level': 0,
                'history': []
            }
        
        self.relationships[other_id]['level'] += delta
        self.relationships[other_id]['level'] = max(-100, min(100, 
            self.relationships[other_id]['level']))
        
        # 同步到 RelationshipManager
        if self.relationship_manager:
            self.relationship_manager.record_interaction(
                self.id,
                other_id,
                interaction_type,
                sentiment,
                self.world.time.day,
                self.current_location
            )
    
    def get_relationship_with(self, other_id: str) -> dict:
        """获取与某人的关系详情"""
        if other_id in self.relationships:
            return self.relationships[other_id]
        
        # 尝试从 RelationshipManager 获取
        if self.relationship_manager:
            rel = self.relationship_manager.get_relationship(self.id, other_id)
            if rel:
                return {
                    'type': rel.stage.value,
                    'level': rel.affinity,
                    'trust': rel.trust,
                    'familiarity': rel.familiarity
                }
        
        return {'type': 'unknown', 'level': 0}
    
    # ==================== 感知模块 ====================
    
    def perceive(self):
        """感知环境"""
        # 感知当前环境
        perceptions = self.perception.perceive_environment(self, self.world)
        
        # 过滤感知
        perceptions = self.perception.filter_perceptions(perceptions, self)
        
        # 记录感知
        self.today_perceptions = perceptions
        
        # 将重要感知写入记忆
        for p in perceptions:
            if p.urgency in ['high', 'urgent']:
                self.memory.add_event(
                    content=f"[感知] {p.content}",
                    day=self.world.time.day,
                    location=self.current_location,
                    event_type='observation'
                )
            
            # 如果感知到其他角色，同步到社交网络
            if p.type == 'character' and hasattr(p, 'source'):
                if self.social_network:
                    self.social_network.record_interaction(
                        self.id,
                        p.source,
                        'perceive',
                        self.world.time.day,
                        1.0  # 轻微正面
                    )
        
        return perceptions
    
    def get_perception_narrative(self) -> str:
        """获取感知叙述"""
        return self.perception.generate_perception_narrative(
            self, self.today_perceptions
        )
    
    # ==================== 对话模块 ====================
    
    def check_for_interactions(self, all_agents: dict) -> list:
        """检查是否有可以互动的角色

        Args:
            all_agents: 所有角色的字典 {id: Agent}, 包含protagonists和npcs
        """
        interactions = []

        for other_id, other_loc in self.world.positions.items():
            if other_id == self.id:
                continue

            if other_loc == self.current_location:
                # 在同一位置 - 直接获取实际的Agent实例，避免状态丢失
                other_agent = all_agents.get(other_id)
                if other_agent:
                    if self.dialogue_gen.should_initiate_dialogue(
                        self, other_agent, "同处一地"
                    ):
                        interactions.append(other_agent)

        return interactions
    
    def interact(self, other_agent) -> Dialogue:
        """与另一角色互动"""
        context = {
            'location_name': self.world.get_location(
                self.current_location
            ).get('name', self.current_location),
            'day': self.world.time.day
        }
        
        dialogue = self.dialogue_gen.generate_dialogue(
            self, other_agent, context, max_turns=3
        )
        
        # 记录对话
        self.today_dialogues.append(dialogue)
        
        # 记录到记忆
        for line in dialogue.lines:
            if line.speaker == self.id:
                self.memory.add_event(
                    content=f"[对话] 对{other_agent.name}说：{line.content}",
                    day=self.world.time.day,
                    location=self.current_location,
                    participants=[other_agent.id],
                    event_type='dialogue'
                )
        
        # 更新关系（双向）
        sentiment = 0.5 if '友好' in dialogue.get_summary() else -0.3 if '冲突' in dialogue.get_summary() else 0.0
        self._update_relationship_after_dialogue(other_agent, dialogue, sentiment)
        
        # 记录到社交网络
        if self.social_network:
            self.social_network.record_interaction(
                self.id,
                other_agent.id,
                'dialogue',
                self.world.time.day,
                sentiment * 10  # 转换为 delta
            )
        
        # 通过事件总线发送消息
        if self.event_bus:
            self.event_bus.publish_message(
                self.id,
                other_agent.id,
                dialogue.get_summary(),
                self.world.time.day
            )
        
        return dialogue
    
    def _update_relationship_after_dialogue(self, other_agent, dialogue, sentiment=0.0):
        """对话后更新关系"""
        if other_agent.id not in self.relationships:
            self.relationships[other_agent.id] = {
                'type': 'acquaintance',
                'level': 5,
                'history': []
            }
        
        rel = self.relationships[other_agent.id]
        
        # 简单关系更新
        if '友好' in dialogue.get_summary():
            rel['level'] = min(rel['level'] + 5, 100)
        elif '冲突' in dialogue.get_summary():
            rel['level'] = max(rel['level'] - 10, -100)
        else:
            rel['level'] += random.randint(-2, 3)
        
        rel['history'].append(dialogue.get_summary())
        
        # 同步到 RelationshipManager
        if self.relationship_manager:
            self.relationship_manager.record_interaction(
                self.id,
                other_agent.id,
                'dialogue',
                sentiment,
                self.world.time.day,
                self.current_location
            )
    
    # ==================== 规划模块 ====================
    
    def plan(self) -> list:
        """制定今日计划"""
        world_state = self.world.get_state_summary()
        
        # 检查是否有待处理的邀请
        if self.pending_invitations:
            # 将邀请纳入计划考量
            world_state['pending_invitations'] = self.pending_invitations
        
        # 尝试使用LLM生成计划（如果有配置）
        if hasattr(self.planner, 'llm_client') and self.planner.llm_client:
            self.current_plan = self.planner.generate_plan_with_llm(
                self, world_state
            )
        else:
            # 使用规则生成计划
            self.current_actions = self.planner.generate_daily_plan(
                self, world_state
            )
        
        return self.current_actions
    
    def execute_action(self, action: Action) -> str:
        """执行单个动作"""
        # 根据动作类型执行
        if action.name == 'cultivate':
            result = self._execute_cultivate(action)
        elif action.name == 'explore':
            result = self._execute_explore(action)
        elif action.name == 'train_with_peers':
            result = self._execute_train(action)
        elif action.name in ['visit_master', 'visit_tavern']:
            result = self._execute_social(action)
        elif action.name == 'move':
            result = self._execute_move(action)
        elif action.name == 'respond_invitation':
            result = self._execute_respond_invitation(action)
        else:
            result = f"{self.name}执行了动作：{action.description}"
        
        # 记录到世界事件
        self.world.add_event(
            self.id,
            result,
            'action'
        )
        
        # 记录到记忆
        self.memory.add_event(
            content=result,
            day=self.world.time.day,
            location=self.current_location,
            event_type='action'
        )
        
        return result
    
    def _execute_cultivate(self, action) -> str:
        """执行修炼动作"""
        insights = [
            "运转周天，体内灵力又凝实了几分",
            "感悟天地灵气，若有所悟",
            "观摩功法要义，心境更加通明",
            "今日打坐，灵识有所增长"
        ]
        return f"在{self.current_location}修炼：{random.choice(insights)}"
    
    def _execute_explore(self, action) -> str:
        """执行探索动作"""
        discoveries = [
            "在附近发现了一株灵草",
            "深入探索，周围景致别有洞天",
            "发现前人留下的遗迹，似乎藏有玄机",
            "仔细搜索，未有特殊发现"
        ]
        return f"探索{self.world.get_location(self.current_location).get('name', '')}：{random.choice(discoveries)}"
    
    def _execute_train(self, action) -> str:
        """执行切磋动作"""
        return f"与师兄弟切磋武艺，交流心得"
    
    def _execute_social(self, action) -> str:
        """执行社交动作"""
        return f"{action.description}，有所收获"
    
    def _execute_move(self, action) -> str:
        """执行移动动作"""
        if hasattr(action, 'destination'):
            days = self.world.move_character(self.id, action.destination)
            self.current_location = action.destination
            if days == 0:
                return f"通过传送阵瞬间抵达{action.destination}"
            else:
                return f"御剑前往{action.destination}，历时{days}日"
        return "执行移动"
    
    def _execute_respond_invitation(self, action) -> str:
        """执行回复邀请"""
        event_id = getattr(action, 'event_id', None)
        accept = getattr(action, 'accept', True)
        
        if not event_id or not self.behavior_engine:
            return "无法处理邀请"
        
        # 处理邀请回复
        self.behavior_engine.process_invitation_response(
            event_id,
            self.id,
            accept,
            self.world.time.day,
            {'agent': self}
        )
        
        status = "接受" if accept else "拒绝"
        return f"对邀请({event_id}){status}"
    
    def act(self):
        """执行今日所有动作"""
        results = []
        
        for action in self.current_actions:
            result = self.execute_action(action)
            results.append(result)
        
        return results
    
    # ==================== 反思模块 ====================
    
    def reflect(self):
        """反思：生成高层洞察"""
        current_day = self.world.time.day
        recent_events = self.memory.get_recent_events(current_day, days=7)
        
        if len(recent_events) < 5:
            return  # 记忆太少不反思
        
        # 使用增强版反思引擎
        if self.reflection_engine:
            new_reflections = self.reflection_engine.generate_reflections(
                self, recent_events, current_day
            )
            
            # 将反思添加到记忆中
            for ref in new_reflections:
                self.memory.add_reflection(ref.content, ref.day)
        
        # 原有的简单反思保留作为fallback
        insights = self._generate_insights(recent_events)
        for insight in insights:
            self.memory.add_reflection(insight, current_day)
    
    def _generate_insights(self, recent_events) -> list:
        """生成洞察（简单版本）"""
        insights = []
        
        # 基于事件类型生成洞察
        event_types = {}
        for e in recent_events:
            t = e.type
            event_types[t] = event_types.get(t, 0) + 1
        
        if event_types.get('dialogue', 0) >= 3:
            insights.append("最近与多人交流，社交颇为频繁")
        
        if event_types.get('action', 0) >= 5:
            insights.append("近日活动频繁，修为有所精进")
        
        # 基于关系变化
        for other_id, rel in self.relationships.items():
            if len(rel.get('history', [])) >= 2:
                insights.append(f"与{other_id}的关系有了新的发展")
        
        # 基于位置
        locations = set(e.location for e in recent_events)
        if len(locations) >= 3:
            insights.append("近日游历多处，眼界有所开阔")
        
        return insights if insights else ["今日修行，平平无奇"]
    
    # ==================== 社交行为模块 ====================
    
    def initiate_social_event(self, event_type: str, content: str, 
                             target_location: str = None) -> str:
        """
        发起一个社交事件（派对、聚会等）
        
        Returns:
            event_id
        """
        if not self.behavior_engine:
            return None
        
        from .behavior_spread import SocialBehaviorType
        
        type_map = {
            'party': SocialBehaviorType.PARTY,
            'invitation': SocialBehaviorType.INVITATION,
            'date': SocialBehaviorType.DATE,
            'gathering': SocialBehaviorType.PARTY,
        }
        
        bh_type = type_map.get(event_type, SocialBehaviorType.INVITATION)
        
        event = self.behavior_engine.initiate_behavior(
            bh_type,
            self.id,
            content,
            self.world.time.day,
            target_location
        )
        
        self.active_social_events.append(event.id)
        
        return event.id
    
    def check_pending_invitations(self) -> list:
        """检查待回复的邀请"""
        if not self.behavior_engine:
            return self.pending_invitations
        
        return self.behavior_engine.get_pending_invitations(self.id)
    
    # ==================== 日记模块 ====================
    
    def get_prompt_context(self) -> dict:
        """获取用于生成日记的上下文"""
        ctx = {
            'name': self.name,
            'sect': self.sect,
            'cultivation': self.cultivation,
            'personality': self.personality,
            'goals': self.goals,
            'current_location': self.current_location,
            'location_name': self.world.get_location(
                self.current_location
            ).get('name', self.current_location),
            'world_time': self.world.time.get_full_time_str(),
            'today_perceptions': self.today_perceptions,
            'today_perceptions_desc': self.get_perception_narrative(),
            'today_dialogues': self.today_dialogues,
            'today_dialogue_desc': self._get_dialogue_summary(),
            'memory_summary': self.memory.get_summary(self.world.time.day),
            'recent_events': [
                e.content for e in self.memory.get_recent_events(
                    self.world.time.day, 7
                )
            ]
        }
        
        # 添加关系信息
        if self.relationship_manager:
            ctx['relationship_summary'] = self.relationship_manager.get_relationship_summary(self.id)
        
        # 添加反思信息
        if self.reflection_engine:
            recent_reflections = self.reflection_engine.get_recent_reflections(
                self.world.time.day, days=7
            )
            ctx['recent_reflections'] = [r.content for r in recent_reflections]
        
        # 添加社交事件信息
        if self.behavior_engine:
            pending = self.check_pending_invitations()
            ctx['pending_invitations'] = pending
        
        return ctx
    
    def _get_dialogue_summary(self) -> str:
        """获取今日对话摘要"""
        if not self.today_dialogues:
            return "今日未与人交谈"
        
        summaries = []
        for d in self.today_dialogues:
            summaries.append(d.get_summary())
        return "; ".join(summaries)
    
    def write_diary(self, use_llm=False, llm_client=None) -> str:
        """生成日记"""
        from .diary import DiaryWriter
        
        diary_writer = DiaryWriter(llm_client)
        return diary_writer.generate(self, use_llm=use_llm)
    
    # ==================== 辅助方法 ====================
    
    def clear_daily_data(self):
        """清空每日数据"""
        self.today_perceptions = []
        self.today_dialogues = []
        self.current_actions = []
    
    def add_memory_event(self, content, event_type='action'):
        """直接添加记忆事件"""
        self.memory.add_event(
            content=content,
            day=self.world.time.day,
            location=self.current_location,
            event_type=event_type
        )
    
    def move_to(self, destination):
        """移动到某地"""
        days = self.world.move_character(self.id, destination)
        self.current_location = destination
        
        self.add_memory_event(
            f"从原来地点移动到{destination}，耗时{'瞬间' if days == 0 else f'{days}日'}",
            event_type='movement'
        )
        
        return days


def create_agents(config, world, 
                 social_network=None,
                 relationship_manager=None,
                 event_bus=None,
                 behavior_engine=None) -> dict:
    """
    批量创建角色
    
    Args:
        config: 世界配置
        world: 世界实例
        social_network: 社交网络（可选，共享实例）
        relationship_manager: 关系管理器（可选，共享实例）
        event_bus: 事件总线（可选，共享实例）
        behavior_engine: 行为引擎（可选，共享实例）
    """
    agents = {}
    
    for char_config in config['characters']:
        if char_config.get('role') == 'protagonist':
            agents[char_config['id']] = Agent(
                char_config, 
                world,
                social_network=social_network,
                relationship_manager=relationship_manager,
                event_bus=event_bus,
                behavior_engine=behavior_engine
            )
    
    return agents


def create_shared_systems():
    """
    创建共享系统（供多个Agent使用）
    
    Returns:
        (social_network, relationship_manager, event_bus, behavior_engine)
    """
    from .social_network import SocialNetwork, BehaviorSpreadEngine
    from .relationship import RelationshipManager
    from .event_bus import EventBus
    from .behavior_spread import EmergentBehaviorEngine
    
    social_network = SocialNetwork()
    relationship_manager = RelationshipManager()
    event_bus = EventBus(
        social_network=social_network,
        relationship_manager=relationship_manager
    )
    behavior_engine = EmergentBehaviorEngine(
        social_network=social_network,
        relationship_manager=relationship_manager
    )
    
    return social_network, relationship_manager, event_bus, behavior_engine
