"""
execute.py - 执行模块 (Execution)

原论文描述:
- "Actions have real effects on the world state"
- "Agents execute actions that affect their environment"
- "Executed actions are added to memory stream"

功能:
- 执行规划中的动作
- 动作真正影响世界状态（移动、交互、更新）
- 将执行结果记录到记忆
- 处理异常和回退
"""
from typing import List, Dict, Any, Optional, Tuple
import random

from ..memory_structures.scratch import Plan
from .plan import Action as ActionType


class ExecutionResult:
    """执行结果"""

    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'
    STATUS_BLOCKED = 'blocked'
    STATUS_PARTIAL = 'partial'

    def __init__(self, action,  # Action from plan.py
                 status: str = STATUS_SUCCESS,
                 result_text: str = "",
                 world_state_change: Optional[Dict] = None,
                 error: Optional[str] = None):
        self.action = action
        self.status = status
        self.result_text = result_text
        self.world_state_change = world_state_change or {}
        self.error = error

    def __repr__(self):
        return f"<ExecutionResult {self.status}: {self.result_text[:40]}>"


class Executor:
    """
    执行器

    功能:
    1. 执行单个动作并产生世界影响
    2. 更新空间记忆
    3. 记录执行结果到记忆流
    4. 处理执行失败
    """

    def __init__(self):
        self.last_execution: Optional[ExecutionResult] = None

    def execute_plan(self, agent: 'Persona',
                    plan: Plan,
                    world: 'World') -> List[ExecutionResult]:
        """
        执行完整计划

        Args:
            agent: agent对象
            plan: 计划对象
            world: 世界对象

        Returns:
            执行结果列表
        """
        results = []

        for action_dict in plan.actions:
            # 将dict转为Action对象（如果需要）
            if isinstance(action_dict, dict):
                action = ActionType(
                    name=action_dict.get('type', 'general'),
                    description=action_dict.get('description', ''),
                    action_type=action_dict.get('type', 'action'),
                    target=action_dict.get('target')
                )
            else:
                action = action_dict

            result = self.execute_action(agent, action, world)
            results.append(result)

            # 如果动作失败，可能需要调整后续计划
            if result.status == ExecutionResult.STATUS_FAILED:
                # 简化：继续执行，但不保证效果
                pass

        return results

    def execute_action(self, agent: 'Persona',
                     action,
                     world: 'World') -> ExecutionResult:
        """
        执行单个动作

        Args:
            agent: agent对象
            action: 动作对象
            world: 世界对象

        Returns:
            ExecutionResult
        """
        # 获取当前天数
        current_day = world.time.day if hasattr(world, 'time') else 1

        # 根据动作类型执行
        if action.name == 'move' or action.type == ActionType.TYPE_MOVE:
            result = self._execute_move(agent, action, world, current_day)
        elif action.name == 'social' or action.type == ActionType.TYPE_SOCIAL:
            result = self._execute_social(agent, action, world, current_day)
        elif action.name == 'work' or action.type == ActionType.TYPE_WORK:
            result = self._execute_work(agent, action, world, current_day)
        elif action.name == 'rest' or action.type == ActionType.TYPE_REST:
            result = self._execute_rest(agent, action, world, current_day)
        elif action.name == 'cultivate':
            result = self._execute_cultivate(agent, action, world, current_day)
        else:
            result = self._execute_general(agent, action, world, current_day)

        self.last_execution = result

        # 记录到记忆
        if result.status == ExecutionResult.STATUS_SUCCESS:
            agent.memory.add(
                content=f"[行动] {result.result_text}",
                day=current_day,
                location=agent.spatial.current_location,
                event_type='action'
            )
        else:
            agent.memory.add(
                content=f"[行动失败] {action.description}: {result.error or '未知原因'}",
                day=current_day,
                location=agent.spatial.current_location,
                event_type='action'
            )

        return result

    def _execute_move(self, agent: 'Persona',
                     action,
                     world: 'World',
                     current_day: int) -> ExecutionResult:
        """
        执行移动动作

        影响:
        - agent.spatial.current_location 更新
        - world.positions 更新
        - agent.spatial.navigation_history 添加记录
        """
        target = action.target
        if not target:
            return ExecutionResult(
                action=action,
                status=ExecutionResult.STATUS_FAILED,
                error="移动目标未指定"
            )

        # 获取当前位置
        old_location = agent.spatial.current_location
        old_location_name = agent.spatial.current_location_name
        target_info = world.get_location(target)
        target_name = target_info.get('name', target) if target_info else target

        # 执行移动
        days = world.move_character(agent.id, target)

        # 更新空间记忆
        duration = days if days > 0 else 0.5  # 瞬移也算半个时间块
        agent.spatial.set_current_location(
            target, target_name,
            day=current_day,
            duration=duration
        )

        # 记录活动
        if days == 0:
            result_text = f"从{old_location_name}瞬间转移到{target_name}"
        else:
            result_text = f"从{old_location_name}前往{target_name}，耗时{days}天"

        return ExecutionResult(
            action=action,
            status=ExecutionResult.STATUS_SUCCESS,
            result_text=result_text,
            world_state_change={
                'location_changed': True,
                'from': old_location,
                'to': target,
                'travel_days': days
            }
        )

    def _execute_social(self, agent: 'Persona',
                       action,
                       world: 'World',
                       current_day: int) -> ExecutionResult:
        """
        执行社交动作

        影响:
        - 对话产生
        - 关系可能变化
        - 记忆记录
        """
        target = action.target
        current_loc = agent.spatial.current_location
        current_loc_name = agent.spatial.current_location_name

        if not target:
            return ExecutionResult(
                action=action,
                status=ExecutionResult.STATUS_FAILED,
                error="社交对象未指定"
            )

        # 获取对方信息
        target_name = target
        if hasattr(agent, 'relationships') and target in agent.relationships:
            rel = agent.relationships[target]
            target_name = rel.get('name', target)

        # 记录遇到的人
        agent.spatial.record_person_encountered(target)

        # 生成社交结果
        world_type = getattr(agent, 'world_type', 'default')

        if world_type == 'modern_urban':
            if '共进晚餐' in action.description or '吃饭' in action.description:
                result_text = f"和{target_name}一起吃饭，度过了一段愉快的时光"
            elif '聊天' in action.description:
                result_text = f"和{target_name}聊了聊天，交流了彼此的想法"
            else:
                result_text = f"和{target_name}进行了社交互动"
        else:
            if '论道' in action.description:
                result_text = f"与{target_name}论道交流，颇有收获"
            elif '切磋' in action.description:
                result_text = f"与{target_name}切磋武艺"
            else:
                result_text = f"与{target_name}进行了交流"

        # 记录对话记忆（作为observation）
        agent.memory.add(
            content=f"和{target_name}互动: {result_text}",
            day=current_day,
            location=current_loc,
            participants=[target],
            event_type='dialogue'
        )

        return ExecutionResult(
            action=action,
            status=ExecutionResult.STATUS_SUCCESS,
            result_text=result_text,
            world_state_change={
                'social_interaction': True,
                'with': target
            }
        )

    def _execute_work(self, agent: 'Persona',
                     action,
                     world: 'World',
                     current_day: int) -> ExecutionResult:
        """
        执行工作动作

        影响:
        - 记忆记录
        - 可能影响关系
        """
        current_loc = agent.spatial.current_location
        current_loc_name = agent.spatial.current_location_name
        world_type = getattr(agent, 'world_type', 'default')

        # 记录活动
        agent.spatial.record_activity(action.description)

        if world_type == 'modern_urban':
            if '邮件' in action.description:
                result_text = f"处理了一批工作邮件"
            elif '报告' in action.description:
                result_text = f"撰写和整理了报告"
            elif '会议' in action.description:
                result_text = f"参加了线上会议"
            elif '处理' in action.description:
                result_text = f"处理了一些工作任务"
            else:
                result_text = f"专注完成了手头的工作"
        else:
            insights = [
                "运转周天,体内灵力又凝实了几分",
                "感悟天地灵气,若有所悟",
                "观摩功法要义,心境更加通明",
            ]
            result_text = f"在{current_loc_name}修炼: {random.choice(insights)}"

        return ExecutionResult(
            action=action,
            status=ExecutionResult.STATUS_SUCCESS,
            result_text=result_text,
            world_state_change={}
        )

    def _execute_rest(self, agent: 'Persona',
                     action,
                     world: 'World',
                     current_day: int) -> ExecutionResult:
        """执行休息动作"""
        current_loc = agent.spatial.current_location
        world_type = getattr(agent, 'world_type', 'default')

        agent.spatial.record_activity('休息')

        if world_type == 'modern_urban':
            result_text = f"在{agent.spatial.current_location_name}放松休息了一下"
        else:
            result_text = f"静修调息，心境平和"

        return ExecutionResult(
            action=action,
            status=ExecutionResult.STATUS_SUCCESS,
            result_text=result_text,
            world_state_change={}
        )

    def _execute_cultivate(self, agent: 'Persona',
                          action,
                          world: 'World',
                          current_day: int) -> ExecutionResult:
        """执行修炼动作（修仙世界）"""
        current_loc = agent.spatial.current_location
        agent.spatial.record_activity('修炼')

        insights = [
            "运转周天,体内灵力又凝实了几分",
            "感悟天地灵气,若有所悟",
            "观摩功法要义,心境更加通明",
            "今日打坐,灵识有所增长"
        ]
        result_text = random.choice(insights)

        return ExecutionResult(
            action=action,
            status=ExecutionResult.STATUS_SUCCESS,
            result_text=f"在{agent.spatial.current_location_name}{result_text}",
            world_state_change={}
        )

    def _execute_general(self, agent: 'Persona',
                        action,
                        world: 'World',
                        current_day: int) -> ExecutionResult:
        """执行通用动作"""
        current_loc = agent.spatial.current_location

        agent.memory.add(
            content=f"[行动] {action.description}",
            day=current_day,
            location=current_loc,
            event_type='action'
        )

        return ExecutionResult(
            action=action,
            status=ExecutionResult.STATUS_SUCCESS,
            result_text=action.description,
            world_state_change={}
        )

    def should_adjust_plan(self, failed_result: ExecutionResult) -> bool:
        """
        判断是否需要调整计划

        例如：移动失败后，可能需要重新规划路线
        """
        if failed_result.status != ExecutionResult.STATUS_FAILED:
            return False

        # 移动失败需要调整
        if failed_result.action.name == 'move':
            return True

        return False
