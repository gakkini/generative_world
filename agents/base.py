"""
Agent基类 - 整合所有认知模块
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
    整合：记忆 + 感知 + 规划 + 对话 + 日记
    """
    
    def __init__(self, config, world):
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
        
        # 当前计划
        self.current_plan = None
        self.current_actions = []
        
        # 今日感知
        self.today_perceptions = []
        self.today_dialogues = []
        
        # 初始化
        self._init_relationships()
    
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
        
        return perceptions
    
    def get_perception_narrative(self) -> str:
        """获取感知叙述"""
        return self.perception.generate_perception_narrative(
            self, self.today_perceptions
        )
    
    # ==================== 对话模块 ====================
    
    def check_for_interactions(self) -> list:
        """检查是否有可以互动的角色"""
        interactions = []
        
        for other_id, other_loc in self.world.positions.items():
            if other_id == self.id:
                continue
            
            if other_loc == self.current_location:
                # 在同一位置 - 获取其他角色的基本信息
                other_config = next(
                    (c for c in self.world.config['characters'] 
                     if c['id'] == other_id),
                    None
                )
                
                if other_config:
                    # 创建轻量级对话上下文对象，不创建完整Agent实例
                    other_context = DialogueContext(
                        id=other_config['id'],
                        name=other_config['name'],
                        sect=other_config['sect'],
                        cultivation=other_config.get('cultivation', '凡人'),
                        current_location=other_loc
                    )
                    
                    if self.dialogue_gen.should_initiate_dialogue(
                        self, other_context, "同处一地"
                    ):
                        interactions.append(other_context)
        
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
        
        # 更新关系
        self._update_relationship_after_dialogue(other_agent, dialogue)
        
        return dialogue
    
    def _update_relationship_after_dialogue(self, other_agent, dialogue):
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
    
    # ==================== 规划模块 ====================
    
    def plan(self) -> list:
        """制定今日计划"""
        world_state = self.world.get_state_summary()
        
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
        
        # 生成反思
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
    
    # ==================== 日记模块 ====================
    
    def get_prompt_context(self) -> dict:
        """获取用于生成日记的上下文"""
        return {
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


def create_agents(config, world) -> dict:
    """批量创建角色"""
    agents = {}
    for char_config in config['characters']:
        if char_config.get('role') == 'protagonist':
            agents[char_config['id']] = Agent(char_config, world)
    return agents
