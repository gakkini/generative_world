"""
规划模块 - Agent的规划大脑
根据记忆、目标、当前状态生成行为计划
"""
import random
import time


class Action:
    """原子动作"""
    
    def __init__(self, name, description, duration=1, 
                 location=None, target=None, cost=None):
        self.id = f"action_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        self.name = name  # 动作名称
        self.description = description  # 动作描述
        self.duration = duration  # 持续时间（天）
        self.location = location  # 动作发生地点
        self.target = target  # 动作目标（角色ID）
        self.cost = cost  # 消耗（资源/灵力等）
        self.status = 'pending'  # pending / executing / completed / failed
        self.result = None  # 执行结果
    
    def execute(self, agent) -> str:
        """执行动作"""
        self.status = 'executing'
        # 实际执行逻辑在agent中
        self.status = 'completed'
        return f"{agent.name}执行了动作：{self.name}"


class Plan:
    """计划"""
    
    def __init__(self, goal, agent_id):
        self.id = f"plan_{int(time.time() * 1000)}"
        self.goal = goal  # 计划目标
        self.agent_id = agent_id
        self.actions = []  # 动作序列
        self.status = 'active'  # active / completed / abandoned
        self.created_day = 0
        self.completed_day = None
    
    def add_action(self, action):
        self.actions.append(action)
    
    def get_next_action(self):
        for a in self.actions:
            if a.status == 'pending':
                return a
        return None
    
    def is_complete(self) -> bool:
        return all(a.status == 'completed' for a in self.actions)


class PlanGenerator:
    """
    计划生成器 - 核心规划大脑
    """
    
    # 地点行为模板
    LOCATION_ACTIVITIES = {
        'sect': [
            ('cultivate', '在宗门内修炼', 1, 'cultivation'),
            ('visit_master', '拜访师父请益', 1, 'social'),
            ('train_with_peers', '与师兄弟切磋', 1, 'social'),
            ('attend_lecture', '参加宗门讲座', 1, 'learning'),
            ('collect_resources', '采集灵草灵石', 2, 'resource'),
        ],
        'neutral': [
            ('explore', '探索此区域', 1, 'adventure'),
            ('trade', '与当地人交易', 1, 'resource'),
            ('gather_info', '打探消息', 1, 'information'),
            ('rest', '在客栈休息', 1, 'recovery'),
        ],
        'hostile': [
            ('investigate', '调查危险区域', 1, 'adventure'),
            ('fight', '与敌人战斗', 1, 'combat'),
            ('sneak', '潜行探索', 1, 'stealth'),
            ('retreat', '伺机撤退', 1, 'survival'),
        ]
    }
    
    # 角色类型行为偏好
    PERSONALITY_ACTIVITIES = {
        '沉稳内敛': ['cultivate', 'visit_master', 'investigate'],
        '外冷内热': ['train_with_peers', 'explore', 'fight'],
        '豪迈洒脱': ['train_with_peers', 'visit_tavern', 'gather_info'],
        '温婉聪慧': ['visit_master', 'trade', 'collect_resources'],
        '阴狠果决': ['investigate', 'fight', 'sneak'],
        '活泼开朗': ['train_with_peers', 'attend_lecture', 'explore'],
    }
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    def generate_daily_plan(self, agent, world_state: dict) -> list:
        """
        生成今日计划
        
        Returns:
            list of Action
        """
        current_location = agent.current_location
        location_type = world_state.get('locations', {}).get(
            current_location, {}
        ).get('type', 'neutral')
        
        # 获取可用的行为模板
        available_activities = self.LOCATION_ACTIVITIES.get(
            location_type, 
            self.LOCATION_ACTIVITIES['neutral']
        )
        
        # 根据角色性格调整
        personality = agent.personality
        preferred = self.PERSONALITY_ACTIVITIES.get(
            personality,
            [a[0] for a in available_activities]
        )
        
        # 选择1-3个动作
        num_actions = random.choices(
            [1, 2, 3],
            weights=[0.4, 0.4, 0.2]
        )[0]
        
        actions = []
        used_types = set()
        
        for _ in range(num_actions):
            # 优先选择性格匹配的行为
            candidates = [
                a for a in available_activities
                if a[0] in preferred and a[0] not in used_types
            ]
            if not candidates:
                candidates = [
                    a for a in available_activities
                    if a[0] not in used_types
                ]
            
            if not candidates:
                continue
            
            # 根据性格权重选择
            activity = random.choice(candidates)
            used_types.add(activity[0])
            
            action = Action(
                name=activity[0],
                description=activity[1],
                duration=activity[2],
                location=current_location
            )
            actions.append(action)
        
        # 如果是角色有目标，添加目标相关动作
        if hasattr(agent, 'goals') and agent.goals:
            goal_action = self._generate_goal_action(agent)
            if goal_action:
                actions.insert(0, goal_action)
        
        return actions
    
    def _generate_goal_action(self, agent) -> Action:
        """根据角色目标生成动作"""
        if not agent.goals:
            return None
        
        primary_goal = agent.goals[0]
        
        # 目标驱动的动作映射
        goal_actions = {
            '修炼成仙': ('deep_cultivation', '闭关于山顶感悟天道', 1),
            '保护亲友': ('guard_around', '守护在意之人', 1),
            '寻找真相': ('investigate_secret', '追查线索', 1),
            '证明自己': ('compete', '参加宗门大比', 2),
            '拯救苍生': ('patrol', '巡视世间', 1),
            '寻找真爱': ('socialize', '广交好友', 1),
        }
        
        action_spec = goal_actions.get(primary_goal)
        if action_spec:
            return Action(
                name=action_spec[0],
                description=action_spec[1],
                duration=action_spec[2],
                location=agent.current_location
            )
        
        return None
    
    def revise_plan(self, agent, plan: Plan, world_state: dict) -> Plan:
        """
        动态调整计划
        当发生意外事件时，调整原有计划
        """
        # 检查是否有紧急事件
        recent_events = agent.memory.get_recent_events(
            world_state.get('day', 1), 
            days=1
        )
        
        urgent_keywords = ['危险', '敌人', '求救', '紧急', '发现', '秘境']
        
        for event in recent_events:
            if any(kw in event.content for kw in urgent_keywords):
                # 插入紧急行动
                urgent_action = Action(
                    name='respond_urgent',
                    description=f'应对紧急事件：{event.content}',
                    duration=1,
                    location=event.location
                )
                plan.add_action(urgent_action)
        
        return plan
    
    def generate_plan_with_llm(self, agent, world_state: dict) -> Plan:
        """使用LLM生成更智能的计划"""
        if not self.llm_client:
            return Plan(self._fallback_goal(agent), agent.id)
        
        prompt = f"""你是{agent.name}（{agent.sect}弟子，修为{agent.cultivation}）。

当前情况：
- 时间：{world_state.get('time_str', '第1日')}
- 位置：{world_state.get('locations', {}).get(agent.current_location, {}).get('name', agent.current_location)}
- 最近经历：{agent.memory.get_recent_events(world_state.get('day', 1), days=3)}

性格特点：{agent.personality}
个人目标：{', '.join(agent.goals) if hasattr(agent, 'goals') and agent.goals else '无'}
当前关系：{self._get_relationship_summary(agent)}

请制定今日计划，考虑：
1. 符合角色性格和目标
2. 符合当前处境
3. 适当推进剧情

输出格式：
计划目标：<一句话>
执行动作：
1. <动作1> - <描述>
2. <动作2> - <描述>
"""
        
        response = self.llm_client.generate(prompt)
        return self._parse_llm_plan(response, agent)
    
    def _fallback_goal(self, agent) -> str:
        """备用目标"""
        return f"在{agent.current_location}修炼"
    
    def _get_relationship_summary(self, agent) -> str:
        """获取关系摘要"""
        if not hasattr(agent, 'relationships'):
            return "暂无深厚交情"
        
        recent = [
            (rid, r) for rid, r in agent.relationships.items()
            if r.get('level', 0) > 50
        ]
        
        if not recent:
            return "暂无深厚交情"
        
        return ", ".join([f"{rid}({r.get('type', '相识')})" for rid, r in recent])
    
    def _parse_llm_plan(self, response: str, agent) -> Plan:
        """解析LLM生成的计划"""
        plan = Plan(f"LLM生成计划", agent.id)
        
        # 简单的文本解析
        # TODO: 更 robust 的解析
        lines = response.split('\n')
        current_action = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('1.') or line.startswith('-'):
                desc = line.lstrip('123456789.- ')
                action = Action(
                    name='llm_action',
                    description=desc,
                    duration=1,
                    location=agent.current_location
                )
                plan.add_action(action)
        
        if not plan.actions:
            # Fallback
            plan.add_action(Action(
                name='cultivate',
                description='按计划修炼',
                duration=1
            ))
        
        return plan
