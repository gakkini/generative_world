"""
社交网络模块 - 角色间关系与社交行为传播
原论文实现：
- Agents form lasting impressions of each other
- Information spreads through the social network
- "Party invitation" spreads autonomously over 2 days
"""
import time
import random
from collections import defaultdict


class SocialEdge:
    """社交边 - 两个角色之间的关系"""
    
    TYPE_FRIEND = 'friend'
    TYPE_ENEMY = 'enemy'
    TYPE_NEUTRAL = 'neutral'
    TYPE_FAMILY = 'family'
    TYPE_ROMANTIC = 'romantic'
    
    def __init__(self, from_agent, to_agent, edge_type=TYPE_NEUTRAL, initial_weight=0.0):
        self.from_agent = from_agent  # 关系发起者
        self.to_agent = to_agent      # 关系接收者
        self.edge_type = edge_type     # 关系类型
        self.weight = initial_weight   # 关系强度 -100 ~ 100
        self.interaction_count = 0     # 交互次数
        self.last_interaction_day = 0  # 上次交互时间
        self.history = []              # 交互历史摘要
        self.created_day = 0
        self.impression = ""           # 印象描述
    
    def update_after_interaction(self, interaction_type: str, day: int, delta: float):
        """交互后更新关系"""
        self.interaction_count += 1
        self.last_interaction_day = day
        self.weight = max(-100, min(100, self.weight + delta))
        
        # 记录历史
        self.history.append({
            'day': day,
            'type': interaction_type,
            'delta': delta,
            'cumulative_weight': self.weight
        })
    
    def get_impression(self) -> str:
        """获取当前印象"""
        if self.weight >= 70:
            return "挚友"
        elif self.weight >= 40:
            return "好友"
        elif self.weight >= 15:
            return "熟人"
        elif self.weight >= -15:
            return "陌生人"
        elif self.weight >= -40:
            return "泛泛之交"
        elif self.weight >= -70:
            return "不太友好"
        else:
            return "仇敌"
    
    def to_dict(self) -> dict:
        return {
            'from': self.from_agent,
            'to': self.to_agent,
            'type': self.edge_type,
            'weight': self.weight,
            'impression': self.get_impression(),
            'interaction_count': self.interaction_count,
            'last_interaction_day': self.last_interaction_day
        }


class SocialNetwork:
    """
    社交网络 - 管理所有角色间的关系
    
    原论文特性：
    - Agents observe each other's actions and update relationships
    - Information propagates through the network
    - Trust builds over repeated interactions
    """
    
    def __init__(self):
        self.edges = {}  # (from_id, to_id) -> SocialEdge
        self.agent_list = set()
        self.message_log = []  # 传播的消息/事件
    
    def add_agent(self, agent_id: str):
        """添加一个角色到网络"""
        self.agent_list.add(agent_id)
    
    def get_edge(self, from_id: str, to_id: str) -> SocialEdge:
        """获取两个角色间的关系边"""
        key = (from_id, to_id)
        return self.edges.get(key)
    
    def get_or_create_edge(self, from_id: str, to_id: str) -> SocialEdge:
        """获取或创建关系边"""
        key = (from_id, to_id)
        if key not in self.edges:
            self.edges[key] = SocialEdge(from_id, to_id)
        return self.edges[key]
    
    def record_interaction(self, from_id: str, to_id: str, 
                          interaction_type: str, day: int, delta: float):
        """
        记录一次交互并更新关系
        
        Args:
            from_id: 交互发起者
            to_id: 交互接收者
            interaction_type: 'dialogue' / 'help' / 'conflict' / 'trade' etc
            day: 当前天数
            delta: 关系变化量
        """
        edge = self.get_or_create_edge(from_id, to_id)
        edge.update_after_interaction(interaction_type, day, delta)
        
        # 如果是重要交互，也创建反向边
        reverse_key = (to_id, from_id)
        if reverse_key not in self.edges:
            reverse_delta = delta * 0.5  # 反向关系影响减半
            self.edges[reverse_key] = SocialEdge(to_id, from_id)
            self.edges[reverse_key].update_after_interaction(
                f"reciprocal_{interaction_type}", day, reverse_delta
            )
    
    def get_relationship_weight(self, agent_a: str, agent_b: str) -> float:
        """获取两个角色的关系权重（平均值）"""
        edge_ab = self.get_edge(agent_a, agent_b)
        edge_ba = self.get_edge(agent_b, agent_a)
        
        weights = []
        if edge_ab:
            weights.append(edge_ab.weight)
        if edge_ba:
            weights.append(edge_ba.weight)
        
        return sum(weights) / len(weights) if weights else 0.0
    
    def get_all_relationships(self, agent_id: str) -> list:
        """获取某角色的所有关系"""
        relationships = []
        for (from_id, to_id), edge in self.edges.items():
            if from_id == agent_id:
                relationships.append({
                    'other': to_id,
                    'edge': edge,
                    'direction': 'outgoing'
                })
            elif to_id == agent_id:
                relationships.append({
                    'other': from_id,
                    'edge': edge,
                    'direction': 'incoming'
                })
        return relationships
    
    def get_friends(self, agent_id: str, min_weight: float = 40) -> list:
        """获取某角色的朋友（关系权重 >= min_weight）"""
        friends = []
        for rel in self.get_all_relationships(agent_id):
            if rel['edge'].weight >= min_weight:
                friends.append(rel)
        return friends
    
    def get_agents_within_reach(self, agent_id: str, depth: int = 2) -> set:
        """
        获取通过N步可达的所有角色
        用于信息传播
        """
        reached = {agent_id}
        current_level = {agent_id}
        
        for _ in range(depth):
            next_level = set()
            for a in current_level:
                for rel in self.get_all_relationships(a):
                    if rel['edge'].weight >= 0:  # 只通过正面关系传播
                        next_level.add(rel['other'])
            reached.update(next_level)
            current_level = next_level - reached
        
        return reached - {agent_id}


class InformationSpreader:
    """
    信息传播器 - 模拟信息在社交网络中的传播
    
    原论文实现派对邀请的机制：
    - Agent A invites B to party
    - B decides whether to attend and whether to re-invite others
    - Information spreads organically
    """
    
    def __init__(self, social_network: SocialNetwork):
        self.social_network = social_network
        self.spread_messages = []  # 传播的消息记录
    
    def spread_invitation(self, from_agent: str, to_agent: str, 
                         content: str, day: int, 
                         urgency: float = 0.5) -> list:
        """
        传播邀请
        
        Args:
            from_agent: 邀请发起者
            to_agent: 邀请接收者
            content: 邀请内容
            day: 当前天数
            urgency: 紧急程度 0-1
        
        Returns:
            list of (from_id, to_id, content) 表示下一步要传播的邀请
        """
        # 记录这次传播
        self.spread_messages.append({
            'from': from_agent,
            'to': to_agent,
            'content': content,
            'day': day,
            'type': 'invitation'
        })
        
        # 获取发送者的社交圈
        friends = self.social_network.get_friends(from_agent, min_weight=20)
        
        # 决定是否接受邀请并继续传播
        next_spread = []
        relationship_weight = self.social_network.get_relationship_weight(
            from_agent, to_agent
        )
        
        # 关系越好，接受并传播的概率越高
        accept_probability = (relationship_weight + 100) / 200  # 0-1
        
        if random.random() < accept_probability:
            # 接受邀请
            # 从好友中选择几个继续传播
            candidates = [f['other'] for f in friends 
                         if f['other'] != from_agent and f['other'] != to_agent]
            
            # 关系够好才传播
            for candidate in candidates[:3]:  # 最多传播给3人
                candidate_rel = self.social_network.get_relationship_weight(
                    to_agent, candidate
                )
                if candidate_rel >= 20:
                    next_spread.append((to_agent, candidate, content))
        
        return next_spread
    
    def spread_information(self, origin_agent: str, information: str, 
                          topic: str, day: int, max_hops: int = 3) -> list:
        """
        通用信息传播
        
        Args:
            origin_agent: 信息源
            information: 信息内容
            topic: 话题标签
            day: 当前天数
            max_hops: 最大传播跳数
        
        Returns:
            所有收到信息的角色列表
        """
        reached = {origin_agent}
        current_reached = {origin_agent}
        
        for hop in range(max_hops):
            next_reached = set()
            
            for agent in current_reached:
                # 获取该角色的好友
                friends = self.social_network.get_friends(agent, min_weight=10)
                
                for friend in friends:
                    target = friend['other']
                    if target not in reached:
                        # 根据关系决定是否传播
                        rel_weight = friend['edge'].weight
                        spread_prob = (rel_weight + 100) / 200
                        
                        if random.random() < spread_prob:
                            next_reached.add(target)
                            reached.add(target)
                            
                            # 记录
                            self.spread_messages.append({
                                'from': agent,
                                'to': target,
                                'content': information,
                                'topic': topic,
                                'day': day,
                                'hop': hop + 1
                            })
            
            current_reached = next_reached
        
        return list(reached - {origin_agent})
    
    def get_spread_path(self, message_id: int) -> list:
        """获取某条消息的传播路径"""
        # 简化实现
        return [m for m in self.spread_messages]


class BehaviorSpreadEngine:
    """
    行为传播引擎 - 触发涌现行为
    
    原论文核心：没有预设"派对脚本"
    Agent自己决定：
    - 是否参加活动
    - 是否邀请其他人
    - 如何协调时间
    """
    
    def __init__(self, social_network: SocialNetwork):
        self.social_network = social_network
        self.spreader = InformationSpreader(social_network)
        self.pending_events = []  # 待处理的行为事件
        self.active_events = {}   # 进行中的事件
    
    def initiate_event(self, event_type: str, initiator: str, 
                      content: str, day: int) -> str:
        """
        发起一个社交事件（派对、聚会、邀约等）
        
        Returns:
            event_id
        """
        event_id = f"event_{event_type}_{day}_{initiator}"
        
        self.active_events[event_id] = {
            'type': event_type,
            'initiator': initiator,
            'content': content,
            'start_day': day,
            'invitees': [initiator],  # 初始参与者
            'confirmed': [initiator],
            'declined': [],
            'status': 'active'
        }
        
        # 获取发起者的好友，开始传播
        friends = self.social_network.get_friends(initiator, min_weight=30)
        for friend in friends[:5]:  # 最多邀请5个
            self.spreader.spread_invitation(
                initiator, 
                friend['other'],
                content,
                day,
                urgency=0.7
            )
        
        return event_id
    
    def respond_to_event(self, event_id: str, responder: str, 
                        accept: bool, day: int) -> list:
        """
        角色响应事件邀请
        
        Returns:
            可能的后续行动
        """
        if event_id not in self.active_events:
            return []
        
        event = self.active_events[event_id]
        
        if accept:
            event['confirmed'].append(responder)
            
            # 决定是否邀请其他人
            my_friends = self.social_network.get_friends(responder, min_weight=40)
            # 排除已经邀请的
            already_invited = set(event['invitees'])
            new_invitees = [
                f['other'] for f in my_friends
                if f['other'] not in already_invited
            ]
            
            # 随机选择1-2个邀请
            import random
            to_invite = random.sample(
                new_invitees, 
                min(len(new_invitees), random.randint(1, 2))
            )
            
            next_actions = []
            for invitee in to_invite:
                event['invitees'].append(invitee)
                next_actions.append(('invite', responder, invitee, event['content']))
            
            return next_actions
        else:
            event['declined'].append(responder)
            return []
    
    def check_event_completion(self, event_id: str, day: int) -> dict:
        """检查事件是否完成"""
        if event_id not in self.active_events:
            return {'status': 'unknown'}
        
        event = self.active_events[event_id]
        
        return {
            'status': event['status'],
            'confirmed_count': len(event['confirmed']),
            'declined_count': len(event['declined']),
            'invitee_count': len(event['invitees']),
            'total_invited': len(set(event['invitees']))
        }
    
    def simulate_day(self, day: int):
        """每日模拟：处理行为传播"""
        # 处理pending事件
        still_pending = []
        
        for pending in self.pending_events:
            # 检查是否触发
            if pending.get('trigger_day') == day:
                # 触发传播
                initiator = pending['initiator']
                content = pending['content']
                
                self.initiate_event(
                    pending['type'],
                    initiator,
                    content,
                    day
                )
            else:
                still_pending.append(pending)
        
        self.pending_events = still_pending
