"""
行为传播模块 - 实现原论文的涌现行为机制
核心：没有预设"派对脚本"，行为自然涌现

原论文描述：
- "starting with only a single user-specified notion that one agent 
   wants to throw a Valentine's Day party"
- "agents autonomously spread invitations to the party over the next two days"
- "make new acquaintances, ask each other out on dates to the party"
- "coordinate to show up for the party together at the right time"
"""
import time
import random
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict


class SocialBehaviorType(Enum):
    """社交行为类型"""
    INVITATION = 'invitation'           # 邀请
    PARTY = 'party'                   # 派对/聚会
    DATE = 'date'                     # 约会
    TRADE = 'trade'                   # 交易
    COOPERATION = 'cooperation'        # 合作
    COMPETITION = 'competition'        # 竞争
    GREETING = 'greeting'             # 问候
    GIFT = 'gift'                     # 礼物
    HELP = 'help'                     # 帮助
    CONFLICT = 'conflict'             # 冲突


class SocialEvent:
    """
    社交事件 - 一次涌现的社会行为
    """
    
    STATUS_PLANNED = 'planned'        # 计划中
    STATUS_SPREADING = 'spreading'    # 传播中
    STATUS_ONGOING = 'ongoing'        # 进行中
    STATUS_COMPLETED = 'completed'    # 已完成
    STATUS_CANCELLED = 'cancelled'    # 已取消
    
    def __init__(self, behavior_type: SocialBehaviorType, 
                 initiator: str, content: str, day: int,
                 target_location: str = None):
        self.id = f"soc_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        self.behavior_type = behavior_type
        self.initiator = initiator  # 发起者
        self.content = content      # 事件内容
        self.day = day              # 发起日期
        self.target_location = target_location  # 目标地点
        
        self.invitees = set([initiator])  # 已邀请的人
        self.confirmed = set([initiator])  # 确认参加的人
        self.declined = set()       # 拒绝的人
        self.pending_responses = {}  # 待回复的邀请
        
        self.status = SocialEvent.STATUS_PLANNED
        self.spreading_depth = 0     # 当前传播深度
        
        # 传播历史
        self.spread_history = []  # [(from, to, day), ...]
        
        # 时间协调
        self.planned_day = day + random.randint(1, 3)  # 计划举行的日期
        self.coordination_log = []  # 协调记录
    
    def add_invitee(self, from_id: str, to_id: str, day: int) -> bool:
        """
        添加被邀请者
        
        Returns:
            True if newly added, False if already invited
        """
        if to_id in self.invitees:
            return False
        
        self.invitees.add(to_id)
        self.pending_responses[to_id] = 'pending'
        self.spread_history.append((from_id, to_id, day))
        return True
    
    def respond_invitation(self, agent_id: str, accept: bool, day: int):
        """回复邀请"""
        if agent_id not in self.pending_responses:
            return
        
        self.pending_responses[agent_id] = 'accepted' if accept else 'declined'
        
        if accept:
            self.confirmed.add(agent_id)
        else:
            self.declined.add(agent_id)
    
    def is_confirmed(self, agent_id: str) -> bool:
        return agent_id in self.confirmed
    
    def get_attendance_prediction(self) -> Tuple[int, int]:
        """预测出席人数 (min, max)"""
        # 乐观：所有人都来
        optimistic = len(self.invitees)
        # 保守：只有确认的来
        conservative = len(self.confirmed)
        return (conservative, optimistic)
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'type': self.behavior_type.value,
            'initiator': self.initiator,
            'content': self.content,
            'day': self.day,
            'planned_day': self.planned_day,
            'status': self.status,
            'invitees': list(self.invitees),
            'confirmed': list(self.confirmed),
            'declined': list(self.declined),
            'attendance_prediction': self.get_attendance_prediction()
        }


class EmergentBehaviorEngine:
    """
    行为传播引擎 - 核心涌现行为机制
    
    关键机制：
    1. Event Trigger - 事件触发（节日、生日、意外相遇）
    2. Invitation Propagation - 邀请传播
    3. Response & Re-invitation - 回复与再邀请
    4. Coordination - 协调（时间、地点）
    5. Attendance - 出席决策
    """
    
    def __init__(self, social_network=None, relationship_manager=None):
        self.social_network = social_network
        self.relationship_manager = relationship_manager
        
        # 活跃的社交事件
        self.active_events = {}  # event_id -> SocialEvent
        
        # 已完成的事件
        self.completed_events = []
        
        # 待处理的行为队列
        self.pending_actions = []
        
        # 全局行为规则
        self.behavior_rules = {
            SocialBehaviorType.PARTY: self._party_behavior_rule,
            SocialBehaviorType.INVITATION: self._invitation_behavior_rule,
            SocialBehaviorType.DATE: self._date_behavior_rule,
        }
    
    # ==================== 行为规则（桩方法）====================
    
    def _party_behavior_rule(self, event, agent, day):
        """派对行为规则"""
        return []
    
    def _invitation_behavior_rule(self, event, agent, day):
        """邀请行为规则"""
        return []
    
    def _date_behavior_rule(self, event, agent, day):
        """约会行为规则"""
        return []
    
    # ==================== 事件发起 ====================
    
    def initiate_behavior(self, behavior_type: SocialBehaviorType,
                         initiator: str, content: str, day: int,
                         target_location: str = None) -> SocialEvent:
        """
        发起一个社交行为
        
        Args:
            behavior_type: 行为类型
            initiator: 发起者ID
            content: 行为内容（如"情人节派对"）
            day: 当前天数
            target_location: 目标地点
        
        Returns:
            SocialEvent对象
        """
        event = SocialEvent(behavior_type, initiator, content, day, target_location)
        
        # 特殊处理派对类型
        if behavior_type == SocialBehaviorType.PARTY:
            # 派对的传播更激进
            event = self._setup_party_event(event)
        
        self.active_events[event.id] = event
        
        # 初始传播
        self._initial_spread(event, day)
        
        return event
    
    def _setup_party_event(self, event: SocialEvent) -> SocialEvent:
        """设置派对事件的特殊参数"""
        # 派对给更多时间传播
        event.planned_day = event.day + random.randint(2, 4)
        return event
    
    def _initial_spread(self, event: SocialEvent, day: int):
        """初始传播 - 发起者邀请自己的好友"""
        if not self.relationship_manager:
            return
        
        friends = self.relationship_manager.get_friends(
            event.initiator, min_affinity=30
        )
        
        # 选择最亲密的几个
        top_friends = friends[:min(5, len(friends))]
        
        for friend in top_friends:
            target_id = friend['other']
            event.add_invitee(event.initiator, target_id, day)
            
            # 模拟发送给邀请（通过relationship_manager通知）
            # 实际通知由外部处理
    
    # ==================== 邀请传播 ====================
    
    def process_invitation_response(self, event_id: str, 
                                    agent_id: str, 
                                    accept: bool,
                                    day: int,
                                    agent_context: Dict) -> List[Tuple]:
        """
        处理邀请回复
        
        Args:
            event_id: 事件ID
            agent_id: 响应的Agent ID
            accept: 是否接受
            day: 当前天数
            agent_context: Agent的上下文信息
        
        Returns:
            后续行动列表 [(action_type, from_id, to_id, content), ...]
        """
        if event_id not in self.active_events:
            return []
        
        event = self.active_events[event_id]
        event.respond_invitation(agent_id, accept, day)
        
        后续_actions = []

        if not accept:
            return []
        
        # 如果接受，決定是否邀请其他人
        if event.status == SocialEvent.STATUS_SPREADING:
            # 只有在传播阶段才继续邀请
            reinvites = self._decide_reinvitation(event, agent_id, day, agent_context)
            后续_actions.extend(reinvites)
        
        # 如果是日期类型，设置协调
        if event.behavior_type == SocialBehaviorType.DATE:
            coordination = self._coordinate_date(event, agent_id, day)
            后续_actions.extend(coordination)
        
        return 后续_actions
    
    def _decide_reinvitation(self, event: SocialEvent, 
                            reinviter_id: str, 
                            day: int,
                            agent_context: Dict) -> List[Tuple]:
        """
        决定是否再邀请其他人
        
        基于：
        - 与被邀请者的关系
        - 被邀请者与其他候选人的关系
        - 事件剩余传播时间
        """
        if not self.relationship_manager:
            return []
        
        后续_actions = []
        
        # 获取该Agent的好友
        my_friends = self.relationship_manager.get_friends(
            reinviter_id, min_affinity=40
        )
        
        # 排除已经邀请的
        candidates = [
            f['other'] for f in my_friends
            if f['other'] not in event.invitees and f['other'] != event.initiator
        ]
        
        if not candidates:
            return []
        
        # 基于关系强度决定邀请数量
        # 关系越好，邀请概率越高
        max_invites = 3 if event.behavior_type == SocialBehaviorType.PARTY else 1
        
        for candidate in candidates[:max_invites]:
            rel = self.relationship_manager.get_relationship(reinviter_id, candidate)
            
            # 计算邀请概率
            invite_prob = 0.5
            if rel:
                # 亲密度高 -> 邀请概率高
                invite_prob = (rel.affinity + 100) / 200
                # 熟悉度高 -> 邀请概率高
                invite_prob = invite_prob * 0.7 + rel.familiarity * 0.3
            
            # 检查是否已通过其他途径邀请
            if candidate in event.pending_responses:
                continue
            
            if random.random() < invite_prob:
                event.add_invitee(reinviter_id, candidate, day)
                后续_actions.append((
                    'invite',
                    reinviter_id,
                    candidate,
                    event.content
                ))
        
        return 后续_actions
    
    # ==================== 协调机制 ====================
    
    def _coordinate_date(self, event: SocialEvent, 
                        agent_id: str, day: int) -> List[Tuple]:
        """约会协调 - 双方协商时间地点"""
        # 简化为确认回复
        return []
    
    def initiate_coordination(self, event_id: str, 
                             from_id: str, to_id: str,
                             day: int) -> List[Tuple]:
        """发起协调请求"""
        if event_id not in self.active_events:
            return []
        
        event = self.active_events[event_id]
        
        return [('coordinate', from_id, to_id, event.content)]
    
    # ==================== 每日模拟 ====================
    
    def simulate_day(self, day: int, agents: Dict):
        """
        每日模拟 - 处理行为传播
        
        步骤：
        1. 检查事件是否该触发
        2. 处理传播
        3. 更新事件状态
        4. 收集待执行的动作
        """
        self.pending_actions = []
        
        for event_id, event in list(self.active_events.items()):
            # 检查事件是否该开始
            if event.status == SocialEvent.STATUS_PLANNED and day >= event.day:
                self._activate_event(event, day)
            
            # 处理传播
            if event.status == SocialEvent.STATUS_SPREADING:
                self._process_spreading(event, day, agents)
            
            # 检查是否该结束
            if event.status == SocialEvent.STATUS_ONGOING:
                if day >= event.planned_day + 1:
                    self._complete_event(event, day)
        
        return self.pending_actions
    
    def _activate_event(self, event: SocialEvent, day: int):
        """激活事件，开始传播"""
        event.status = SocialEvent.STATUS_SPREADING
        event.spreading_depth = 0
    
    def _process_spreading(self, event: SocialEvent, day: int, agents: Dict):
        """处理传播逻辑"""
        # 检查是否达到最大传播深度
        max_depth = 3 if event.behavior_type == SocialBehaviorType.PARTY else 2
        
        if event.spreading_depth >= max_depth:
            # 转为进行中
            event.status = SocialEvent.STATUS_ONGOING
            return
        
        # 传播衰减：随着时间推移，传播概率降低
        days_since_start = day - event.day
        spread_decay = max(0.3, 1.0 - days_since_start * 0.15)
        
        # 处理待回复的邀请
        for invitee in list(event.pending_responses.keys()):
            if event.pending_responses[invitee] != 'pending':
                continue
            
            # 模拟回复决策
            if invitee in agents:
                decision = self._simulate_invitation_response(
                    event, invitee, day, agents[invitee]
                )
                
                if decision is not None:
                    accept = decision
                    self.process_invitation_response(
                        event.id, invitee, accept, day,
                        {'agent': agents[invitee]}
                    )
        
        event.spreading_depth += 1
    
    def _simulate_invitation_response(self, event: SocialEvent,
                                      agent_id: str,
                                      day: int,
                                      agent) -> Optional[bool]:
        """
        模拟Agent对邀请的回复决策
        
        基于：
        - 与邀请者的关系
        - 与其他已确认者的关系
        - 事件的吸引力
        """
        if not self.relationship_manager:
            return random.random() < 0.5
        
        # 获取谁邀请了我
        inviter = None
        for from_id, to_id, d in event.spread_history:
            if to_id == agent_id:
                inviter = from_id
                break
        
        if not inviter:
            return None
        
        # 获取关系
        rel = self.relationship_manager.get_relationship(inviter, agent_id)
        if not rel:
            rel = self.relationship_manager.get_or_create(inviter, agent_id)
        
        # 计算接受概率
        accept_prob = 0.5
        
        # 关系影响
        accept_prob = accept_prob * 0.4 + (rel.affinity + 100) / 200 * 0.6
        
        # 熟悉度影响
        accept_prob = accept_prob * 0.7 + rel.familiarity * 0.3
        
        # 特殊行为类型调整
        if event.behavior_type == SocialBehaviorType.PARTY:
            # 派对更看关系
            if rel.affinity < 20:
                accept_prob *= 0.5
        
        elif event.behavior_type == SocialBehaviorType.DATE:
            # 约会更谨慎
            if rel.affinity < 50:
                accept_prob *= 0.3
        
        # 检查是否有共同朋友已确认
        confirmed_friends = [
            c for c in event.confirmed
            if c != inviter and c != agent_id
        ]
        
        if confirmed_friends:
            # 有共同朋友，增加概率
            mutual_count = 0
            for friend in confirmed_friends:
                friend_rel = self.relationship_manager.get_relationship(
                    agent_id, friend
                )
                if friend_rel and friend_rel.affinity > 30:
                    mutual_count += 1
            accept_prob += mutual_count * 0.05
        
        accept_prob = max(0.1, min(0.9, accept_prob))
        
        return random.random() < accept_prob
    
    def _complete_event(self, event: SocialEvent, day: int):
        """完成事件"""
        event.status = SocialEvent.STATUS_COMPLETED
        self.completed_events.append(event)
        del self.active_events[event.id]
    
    # ==================== 查询接口 ====================
    
    def get_active_events(self) -> List[SocialEvent]:
        return list(self.active_events.values())
    
    def get_event_by_id(self, event_id: str) -> SocialEvent:
        return self.active_events.get(event_id)
    
    def get_events_for_agent(self, agent_id: str) -> List[SocialEvent]:
        """获取某Agent参与的所有事件"""
        result = []
        
        for event in self.active_events.values():
            if agent_id in event.invitees:
                result.append(event)
        
        for event in self.completed_events:
            if agent_id in event.invitees:
                result.append(event)
        
        return result
    
    def get_pending_invitations(self, agent_id: str) -> List[Tuple]:
        """获取某Agent的待回复邀请 [(event_id, from_id, content), ...]"""
        result = []
        
        for event in self.active_events.values():
            if agent_id in event.pending_responses:
                if event.pending_responses[agent_id] == 'pending':
                    # 找到是谁邀请的
                    inviter = None
                    for from_id, to_id, d in event.spread_history:
                        if to_id == agent_id:
                            inviter = from_id
                            break
                    result.append((event.id, inviter, event.content))
        
        return result
    
    def get_agent_attendance(self, event_id: str) -> Dict[str, Any]:
        """获取事件的出席情况"""
        if event_id not in self.active_events:
            return {}
        
        event = self.active_events[event_id]
        return {
            'confirmed': list(event.confirmed),
            'declined': list(event.declined),
            'pending': [k for k, v in event.pending_responses.items() 
                       if v == 'pending'],
            'prediction': event.get_attendance_prediction()
        }
