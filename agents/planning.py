"""
规划模块 - Agent的规划大脑
根据记忆、目标、当前状态生成行为计划
仅支持LLM版本，模板版本已移除
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
    仅支持LLM版本，强制要求llm_client配置
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    def generate_daily_plan(self, agent, world_state: dict) -> list:
        """
        生成今日计划（仅LLM版本）
        如果未配置LLM客户端，抛出异常
        """
        if not self.llm_client:
            raise RuntimeError(
                f"[PlanGenerator] {agent.name} 未配置LLM客户端，无法生成计划。"
                " 请在初始化时配置 llm_client。（主角强制使用LLM版本）"
            )
        
        return self._generate_plan_via_llm(agent, world_state)
    
    def _generate_plan_via_llm(self, agent, world_state: dict) -> list:
        """通过LLM生成计划"""
        prompt = self._build_plan_prompt(agent, world_state)
        
        # 优先使用角色配置中的 system_prompt，否则使用默认
        if hasattr(agent, 'system_prompt') and agent.system_prompt:
            system_prompt = agent.system_prompt + "\n\n你是一个行为规划专家。请严格按照输出格式生成计划。"
        else:
            system_prompt = "你是一个修仙世界的行为规划专家。请严格按照输出格式生成计划。"
        
        response = self.llm_client.generate(
            prompt,
            system_prompt=system_prompt,
            max_tokens=1500,
            temperature=0.8
        )
        
        actions = self._parse_plan_response(response, agent)
        return actions
    
    def _build_plan_prompt(self, agent, world_state: dict) -> str:
        """构建计划生成Prompt"""
        current_location = agent.current_location
        location_info = world_state.get('locations', {}).get(current_location, {})
        location_name = location_info.get('name', current_location)
        location_type = location_info.get('type', 'neutral')
        
        recent_events = agent.memory.get_recent_events(
            world_state.get('day', 1), days=3
        ) if hasattr(agent, 'memory') else []
        recent_str = "\n".join([f"- {e.content}" for e in recent_events[-5:]]) or "暂无"
        
        relationships = self._get_relationship_summary(agent)
        
        # 根据世界类型选择动作模板
        world_type = world_state.get('world_type', 'cultivation')
        occupation = getattr(agent, 'occupation', '')
        
        if world_type == 'modern_urban':
            # 现代都市动作模板
            action_templates = f"""现代都市家中：阅读研究、工作学习、使用电子设备、休息放松、与家人/伴侣互动、做家务、观看窗外风景、听音乐、喝咖啡
现代都市户外：外出散步、购物、健身、与朋友聚会、餐厅用餐、观看电影"""
            world_style_hint = "现代都市日常生活特色"
            role_intro = f"你是{agent.name}，职业是{occupation}（现代都市）。"
        else:
            # 修仙世界动作模板
            action_templates = """宗门内：修炼、拜访师父、与师兄弟切磋、参加讲座、采集灵草
中立区：探索、与当地人交易、打探消息、客栈休息
危险区：调查危险区域、与敌人战斗、潜行探索"""
            world_style_hint = "修仙世界特色"
            role_intro = f"你是{agent.name}（{agent.sect} {agent.cultivation}）。"
        
        return f"""{role_intro}

【角色基本信息】
- 性格：{agent.personality}
- 目标：{', '.join(agent.goals) if agent.goals else '无'}
- 当前位置：{location_name}（{location_type}）

【当前时间】
{world_state.get('time_str', f'第{world_state.get("day", 1)}日')}

【近三日经历】
{recent_str}

【当前人际关系】
{relationships}

【可选动作类型】（根据位置和性格选择1-3个）
{action_templates}

请制定今日计划，严格按以下JSON格式输出（不要有其他内容）：
{{
  "goal": "计划目标一句话描述",
  "actions": [
    {{"name": "动作名", "description": "动作详细描述", "duration": 1}},
    ...
  ]
}}

要求：
1. 动作数量1-3个
2. 必须符合角色性格和当前位置
3. 动作描述要有{world_style_hint}
4. JSON外不要有多余文字（只需输出JSON）
        """
        
    def _get_relationship_summary(self, agent) -> str:
        """获取关系摘要"""
        if not hasattr(agent, 'relationships') or not agent.relationships:
            return "暂无深厚交情"
        
        recent = [
            (rid, r) for rid, r in agent.relationships.items()
            if r.get('level', 0) > 30
        ]
        
        if not recent:
            return "暂无深厚交情"
        
        return ", ".join([
            f"{rid}(关系{r.get('level', 0)}, {r.get('type', '相识')})" 
            for rid, r in recent[:5]
        ])
    
    def _parse_plan_response(self, response: str, agent) -> list:
        """解析LLM返回的计划JSON"""
        import json
        import re
        
        # 去除 markdown 代码块包裹
        clean_response = response.strip()
        if clean_response.startswith('```'):
            # 去掉 ```json 或 ``` 和结尾的 ```
            clean_response = re.sub(r'^```(?:json)?\s*', '', clean_response, flags=re.IGNORECASE)
            clean_response = re.sub(r'\s*```$', '', clean_response)
        
        # 尝试提取JSON块
        json_match = re.search(r'\{[\s\S]*\}', clean_response)
        if not json_match:
            # Fallback: 尝试直接解析
            try:
                data = json.loads(clean_response.strip())
            except Exception:
                # 最后一次尝试：提取所有"动作"相关行
                return self._fallback_parse(response, agent)
        else:
            try:
                data = json.loads(json_match.group())
            except Exception:
                return self._fallback_parse(response, agent)
        
        actions = []
        goal = data.get('goal', f'{agent.name}的今日计划')
        
        for a in data.get('actions', []):
            action = Action(
                name=a.get('name', 'unknown'),
                description=a.get('description', ''),
                duration=a.get('duration', 1),
                location=agent.current_location
            )
            actions.append(action)
        
        # 如果没有解析出动作，fallback
        if not actions:
            return self._fallback_parse(response, agent)
        
        return actions
    
    def _fallback_parse(self, response: str, agent) -> list:
        """Fallback: 当JSON解析失败时"""
        actions = []
        
        # 提取所有"-"或"1."开头的动作行
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('-') or (len(line) > 2 and line[1] == '.'):
                desc = line.lstrip('123456789.-、 ')
                if desc:
                    actions.append(Action(
                        name='cultivate',
                        description=desc,
                        duration=1,
                        location=agent.current_location
                    ))
        
        # 最基础的fallback
        if not actions:
            actions.append(Action(
                name='cultivate',
                description='按计划修炼',
                duration=1,
                location=agent.current_location
            ))
        
        return actions
    
    def revise_plan(self, agent, plan: Plan, world_state: dict) -> Plan:
        """
        动态调整计划
        当发生意外事件时，调整原有计划
        """
        if not self.llm_client:
            # 无LLM时用简单规则处理紧急事件
            return self._revise_plan_simple(agent, plan, world_state)
        
        prompt = f"""你是{agent.name}的计划调整专家。

原计划：{[a.description for a in plan.actions]}
当前事件：{world_state.get('recent_events', [])}
今日突发事件：{world_state.get('urgent_events', [])}

如果存在紧急事件，在原计划前插入应对动作。
输出JSON格式：
{{
  "revised": true/false,
  "reason": "调整原因",
  "actions": [
    {{"name": "动作名", "description": "描述", "duration": 1, "urgent": true/false}}
  ]
}}
        """
        response = self.llm_client.generate(prompt, max_tokens=800, temperature=0.7)
        
        try:
            import json, re
            m = re.search(r'\{[\s\S]*\}', response)
            if m:
                data = json.loads(m.group())
                if data.get('revised'):
                    # 清空原计划，替换为新计划
                    plan.actions = []
                    for a in data.get('actions', []):
                        action = Action(
                            name=a.get('name', 'unknown'),
                            description=a.get('description', ''),
                            duration=a.get('duration', 1),
                            location=agent.current_location
                        )
                        plan.add_action(action)
        except Exception:
            pass
        
        return plan
    
    def _revise_plan_simple(self, agent, plan: Plan, world_state: dict) -> Plan:
        """简单规则调整计划（无LLM时）"""
        recent_events = []
        if hasattr(agent, 'memory'):
            recent_events = agent.memory.get_recent_events(
                world_state.get('day', 1), days=1
            )
        
        urgent_keywords = ['危险', '敌人', '求救', '紧急', '发现', '秘境', '异象']
        
        for event in recent_events:
            if any(kw in event.content for kw in urgent_keywords):
                urgent_action = Action(
                    name='respond_urgent',
                    description=f'应对紧急事件：{event.content}',
                    duration=1,
                    location=event.location
                )
                plan.actions.insert(0, urgent_action)
        
        return plan
