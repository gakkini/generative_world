"""
plan.py - 规划模块 (Planning)

原论文描述:
- "The agent generates a long-term plan at the beginning of each day"
- "Plans are generated based on: current environment state + relevant memories + reflections + persona"
- "Output: Today's plan (morning/afternoon/evening) + action sequences + expected outcomes"

规划输入:
1. 当前环境状态 (current environment state)
2. 相关记忆 (relevant memories from retrieve)
3. 近期反思 (recent reflections)
4. 角色设定 (persona/role)

规划输出:
- 今日计划（早上/下午/晚上）
- 动作序列
- 预期结果
"""
from typing import List, Dict, Any, Optional, Tuple
import random

from ..memory_structures.scratch import Plan, Scratch
from .retrieve import Retriever


class Action:
    """
    单个动作

    属性:
    - name: 动作名称 (move, interact, work, rest, etc)
    - description: 动作描述
    - target: 动作目标（如地点ID、agent ID等）
    - duration: 持续时间（时间块数）
    - expected_outcome: 预期结果
    """

    TYPE_MOVE = 'move'
    TYPE_INTERACT = 'interact'
    TYPE_WORK = 'work'
    TYPE_REST = 'rest'
    TYPE_EXPLORE = 'explore'
    TYPE_SOCIAL = 'social'
    TYPE_PERSONAL = 'personal'

    def __init__(self, name: str, description: str,
                 action_type: str = 'action',
                 target: Optional[str] = None,
                 duration: int = 1,
                 expected_outcome: str = "",
                 **kwargs):
        self.name = name
        self.description = description
        self.type = action_type
        self.target = target
        self.duration = duration  # 占据的时间块数
        self.expected_outcome = expected_outcome
        self.kwargs = kwargs  # 其他参数

    def __repr__(self):
        return f"<Action {self.name}: {self.description[:30]}>"

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'description': self.description,
            'type': self.type,
            'target': self.target,
            'duration': self.duration,
            'expected_outcome': self.expected_outcome
        }


class PlanGenerator:
    """
    规划生成器

    功能:
    1. 基于 retrieve 的相关记忆生成计划
    2. 将计划分解为动作序列
    3. 考虑角色设定和当前环境
    4. 支持 LLM 增强的规划（可选）
    """

    # 时间块定义
    TIME_BLOCKS = ['morning', 'afternoon', 'evening']

    # 现代都市的动作模板
    MODERN_ACTIONS = {
        'work': ['处理工作邮件', '撰写报告', '参加线上会议', '整理文件', '回复消息'],
        'personal': ['看书学习', '刷手机放松', '做运动', '听音乐', '画画'],
        'social': ['和室友聊天', '视频通话', '和伴侣共进晚餐', '邀请朋友来家里'],
        'rest': ['午休小憩', '躺在沙发上休息', '发呆放空', '整理房间'],
        'explore': ['在家四处转转', '去阳台吹风', '去厨房做点吃的'],
        'move': ['从{from_loc}移动到{to_loc}', '前往{to_loc}'],
    }

    # 修仙世界的动作模板
    CULTIVATION_ACTIONS = {
        'work': ['修炼功法', '打坐调息', '研读典籍', '炼制丹药'],
        'personal': ['感悟天地', '冥想修行', '练习法术'],
        'social': ['与同道论道', '拜访师父', '与师兄弟切磋', '参加宗门活动'],
        'rest': ['闭关静修', '闲庭信步', '品茶论道'],
        'explore': ['探索秘境', '寻访灵草', '观摩遗迹'],
        'move': ['御剑前往{to_loc}', '通过传送阵前往{to_loc}'],
    }

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.last_plan: Optional[Plan] = None

    def generate_plan(self, agent: 'Persona',
                     current_day: int,
                     env_state: Dict[str, Any],
                     retrieval_context: Dict[str, Any],
                     reflection_context: str = "") -> Plan:
        """
        生成今日计划

        核心算法:
        1. 分析当前情境（地点、时间、关系）
        2. 结合相关记忆和反思
        3. 生成时间段计划
        4. 分解为具体动作

        Args:
            agent: agent对象
            current_day: 当前天数
            env_state: 环境状态（来自world.get_state_summary）
            retrieval_context: retrieve模块返回的上下文
            reflection_context: 反思洞察文本

        Returns:
            Plan对象
        """
        plan = Plan(agent_id=agent.id, current_day=current_day)

        # 获取世界类型
        world_type = env_state.get('world_type', 'default')
        agent_name = getattr(agent, 'name', 'Agent')

        # 选择动作模板
        if world_type == 'modern_urban':
            action_templates = self.MODERN_ACTIONS
            plan_theme = self._generate_modern_plan_theme(
                agent, env_state, retrieval_context, reflection_context
            )
        else:
            action_templates = self.CULTIVATION_ACTIONS
            plan_theme = self._generate_cultivation_plan_theme(
                agent, env_state, retrieval_context, reflection_context
            )

        # 生成各时间段计划
        morning_actions = self._generate_time_block_actions(
            'morning', agent, action_templates, env_state, retrieval_context
        )
        afternoon_actions = self._generate_time_block_actions(
            'afternoon', agent, action_templates, env_state, retrieval_context
        )
        evening_actions = self._generate_time_block_actions(
            'evening', agent, action_templates, env_state, retrieval_context
        )

        plan.set_morning_actions(morning_actions)
        plan.set_afternoon_actions(afternoon_actions)
        plan.set_evening_actions(evening_actions)

        # 生成动作序列
        all_actions = morning_actions + afternoon_actions + evening_actions
        for action_desc in all_actions:
            action = self._parse_action_description(
                action_desc, agent, env_state, world_type
            )
            if action:
                plan.add_action(
                    action.name,
                    action.description,
                    target=action.target,
                    duration=action.duration,
                    expected_outcome=action.expected_outcome
                )

        # 生成预期结果
        plan.expected_outcomes = self._generate_expected_outcomes(
            plan, agent, world_type
        )

        self.last_plan = plan
        return plan

    def _generate_modern_plan_theme(self, agent: 'Persona',
                                   env_state: Dict,
                                   retrieval: Dict,
                                   reflection: str) -> Dict:
        """生成现代都市风格计划主题"""
        # 当前位置
        current_loc = getattr(agent.spatial, 'current_location', None) or env_state.get('positions', {}).get(agent.id, 'unknown')
        current_loc_name = env_state.get('locations', {}).get(current_loc, {}).get('name', current_loc)

        # 附近的人
        nearby = []
        positions = env_state.get('positions', {})
        for aid, loc in positions.items():
            if aid != agent.id and loc == current_loc:
                nearby.append(aid)

        # 从检索上下文获取相关信息
        recent_person_memories = retrieval.get('person_memories', {})
        recent_gen_memories = retrieval.get('general_memories', [])[:3]

        return {
            'current_location': current_loc,
            'current_location_name': current_loc_name,
            'nearby_agents': nearby,
            'person_memories': recent_person_memories,
            'recent_experiences': [m.content for m, _ in recent_gen_memories],
            'reflection': reflection
        }

    def _generate_cultivation_plan_theme(self, agent: 'Persona',
                                        env_state: Dict,
                                        retrieval: Dict,
                                        reflection: str) -> Dict:
        """生成修仙世界风格计划主题"""
        current_loc = getattr(agent.spatial, 'current_location', None) or env_state.get('positions', {}).get(agent.id, 'unknown')
        current_loc_name = env_state.get('locations', {}).get(current_loc, {}).get('name', current_loc)

        nearby = []
        positions = env_state.get('positions', {})
        for aid, loc in positions.items():
            if aid != agent.id and loc == current_loc:
                nearby.append(aid)

        cultivation = getattr(agent, 'cultivation', '炼气期')
        sect = getattr(agent, 'sect', '无名')

        return {
            'current_location': current_loc,
            'current_location_name': current_loc_name,
            'nearby_agents': nearby,
            'cultivation': cultivation,
            'sect': sect,
            'reflection': reflection
        }

    def _generate_time_block_actions(self, time_block: str,
                                   agent: 'Persona',
                                   templates: Dict,
                                   env_state: Dict,
                                   retrieval: Dict) -> List[str]:
        """
        为特定时间段生成动作描述

        Args:
            time_block: 'morning' | 'afternoon' | 'evening'
        """
        actions = []
        world_type = env_state.get('world_type', 'default')

        # 现代都市风格
        if world_type == 'modern_urban':
            if time_block == 'morning':
                # 早上：工作或准备
                occupation = getattr(agent, 'occupation', '工作')
                if '研究' in occupation or '员' in occupation:
                    actions.append(random.choice([
                        '处理工作邮件和消息',
                        '开始一天的工作计划',
                        '参加早会'
                    ]))
                else:
                    actions.append(random.choice([
                        '起床整理',
                        '在家处理一些事情',
                        '看看手机'
                    ]))
                # 可能加入社交
                nearby = self._get_nearby_agents(agent, env_state)
                if nearby and random.random() < 0.5:
                    actions.append(f"和{nearby[0]}打个招呼")
                actions.append('做一些个人事务')

            elif time_block == 'afternoon':
                # 下午：工作或社交
                if random.random() < 0.6:
                    actions.append(random.choice([
                        '处理工作',
                        '专注完成一些任务',
                        '做自己的事情'
                    ]))
                else:
                    nearby = self._get_nearby_agents(agent, env_state)
                    if nearby:
                        actions.append(f"和{nearby[0]}聊聊天")
                    else:
                        actions.append('放松休息一下')
                actions.append('继续手头的事情')

            elif time_block == 'evening':
                # 晚上：休息或社交
                nearby = self._get_nearby_agents(agent, env_state)
                if nearby:
                    if random.random() < 0.7:
                        actions.append(f"和{nearby[0]}共进晚餐")
                    else:
                        actions.append(random.choice([
                            '在客厅休息',
                            '看会电视',
                            '整理一下房间'
                        ]))
                else:
                    actions.append('一个人安静地休息')
                    actions.append('做点自己喜欢的事')

        # 修仙风格
        else:
            if time_block == 'morning':
                actions.append(random.choice(['打坐修炼', '研读功法', '练习法术']))
                actions.append('处理日常事务')
            elif time_block == 'afternoon':
                if random.random() < 0.5:
                    actions.append('继续修炼或探索')
                else:
                    actions.append('与同道交流')
            elif time_block == 'evening':
                actions.append('静修调息')
                actions.append('回顾一日所得')

        return actions

    def _get_nearby_agents(self, agent: 'Persona', env_state: Dict) -> List[str]:
        """获取附近的agent"""
        current_loc = getattr(agent.spatial, 'current_location', None)
        if not current_loc:
            current_loc = env_state.get('positions', {}).get(agent.id)

        if not current_loc:
            return []

        nearby = []
        positions = env_state.get('positions', {})
        for aid, loc in positions.items():
            if aid != agent.id and loc == current_loc:
                nearby.append(aid)
        return nearby

    def _parse_action_description(self, description: str,
                                  agent: 'Persona',
                                  env_state: Dict,
                                  world_type: str) -> Optional[Action]:
        """
        将动作描述解析为Action对象

        Args:
            description: 动作描述文本
            agent: agent对象
            env_state: 环境状态
            world_type: 世界类型

        Returns:
            Action对象
        """
        # 根据描述关键词判断动作类型
        desc_lower = description.lower()

        if '移动' in description or '前往' in description or '去' in description:
            # 移动动作
            target = self._extract_location(description, env_state)
            return Action(
                name='move',
                description=description,
                action_type=Action.TYPE_MOVE,
                target=target,
                duration=1,
                expected_outcome=f"到达{target}"
            )

        elif '聊天' in description or '对话' in description or '共进' in description:
            # 社交动作
            target = self._extract_person(description)
            return Action(
                name='social',
                description=description,
                action_type=Action.TYPE_SOCIAL,
                target=target,
                duration=1,
                expected_outcome="增进关系"
            )

        elif '工作' in description or '处理' in description or '任务' in description:
            return Action(
                name='work',
                description=description,
                action_type=Action.TYPE_WORK,
                duration=1,
                expected_outcome="完成任务"
            )

        elif '休息' in description or '放松' in description or '睡觉' in description:
            return Action(
                name='rest',
                description=description,
                action_type=Action.TYPE_REST,
                duration=1,
                expected_outcome="恢复精力"
            )

        elif '修炼' in description or '打坐' in description:
            return Action(
                name='cultivate',
                description=description,
                action_type=Action.TYPE_WORK,
                duration=1,
                expected_outcome="修为提升"
            )

        else:
            return Action(
                name='general',
                description=description,
                action_type=Action.TYPE_PERSONAL,
                duration=1
            )

    def _extract_location(self, description: str, env_state: Dict) -> Optional[str]:
        """从描述中提取地点"""
        # 简化实现：查找描述中的地点
        locations = env_state.get('locations', {})

        for loc_id, loc_info in locations.items():
            loc_name = loc_info.get('name', '')
            if loc_name in description:
                return loc_id

        return None

    def _extract_person(self, description: str) -> Optional[str]:
        """从描述中提取人物"""
        # 简化实现：查找"和XXX"模式
        if '和' in description:
            parts = description.split('和')
            if len(parts) > 1:
                person = parts[1].split()[0]
                return person
        return None

    def _generate_expected_outcomes(self, plan: Plan,
                                   agent: 'Persona',
                                   world_type: str) -> List[str]:
        """生成预期结果"""
        outcomes = []

        if plan.morning:
            outcomes.append("上午有所收获")
        if plan.afternoon:
            outcomes.append("下午完成任务")
        if plan.evening:
            outcomes.append("晚上心情平静")

        return outcomes

    def generate_llm_plan(self, agent: 'Persona',
                         current_day: int,
                         env_state: Dict,
                         retrieval_context: Dict,
                         reflection_context: str) -> Plan:
        """
        使用LLM增强的规划生成

        调用LLM根据角色设定和相关记忆生成更智能的计划
        """
        if not self.llm_client:
            return self.generate_plan(
                agent, current_day, env_state, retrieval_context, reflection_context
            )

        # 构建prompt
        prompt = self._build_llm_plan_prompt(
            agent, current_day, env_state, retrieval_context, reflection_context
        )

        system_prompt = getattr(agent, 'system_prompt', '') or self._get_default_system_prompt(agent)

        try:
            response = self.llm_client.generate(
                prompt,
                system_prompt=system_prompt,
                max_tokens=500,
                temperature=0.7
            )

            # 解析LLM响应（简化版：直接用模板fallback）
            # 实际项目中应解析LLM返回的结构化计划
            return self.generate_plan(
                agent, current_day, env_state, retrieval_context, reflection_context
            )

        except Exception:
            # Fallback to template-based planning
            return self.generate_plan(
                agent, current_day, env_state, retrieval_context, reflection_context
            )

    def _build_llm_plan_prompt(self, agent: 'Persona',
                              current_day: int,
                              env_state: Dict,
                              retrieval_context: Dict,
                              reflection_context: str) -> str:
        """构建LLM规划prompt"""
        agent_name = getattr(agent, 'name', 'Agent')
        world_type = env_state.get('world_type', 'default')

        prompt = f"""作为{agent_name}，请根据以下信息规划今天的活动。

【当前情境】
- 当前天数: 第{current_day}天
- 世界类型: {world_type}
- 当前位置: {env_state.get('positions', {}).get(agent.id, 'unknown')}
- 时间: {env_state.get('time_str', '早晨')}

【相关记忆】
{retrieval_context}

【反思洞察】
{reflection_context}

请为{agent_name}规划今天的上午、下午和晚上的活动。
用简洁的语言描述每个时间段的主要活动。
直接输出活动计划，不要其他内容。"""

        return prompt

    def _get_default_system_prompt(self, agent: 'Persona') -> str:
        """获取默认system prompt"""
        world_type = getattr(agent, 'world_type', 'default')

        if world_type == 'modern_urban':
            return f"你是{getattr(agent, 'name', 'Agent')}，性格{getattr(agent, 'personality', '正常')}。请用简洁现代的语言规划一天的活动。"
        else:
            return f"你是{getattr(agent, 'name', 'Agent')}，{getattr(agent, 'sect', '宗门')}弟子。请用古风的语言规划一天的活动。"
