"""
事件总线 - Agent间事件传播机制
支持跨Agent的信息扩散、状态同步、行为触发
"""
import time
import random
from collections import defaultdict
from typing import Callable, Dict, List, Any, Optional


class Event:
    """事件对象"""
    
    TYPE_MESSAGE = 'message'           # 消息传递
    TYPE_NOTIFICATION = 'notification'  # 通知
    TYPE_BROADCAST = 'broadcast'        # 广播
    TYPE_PRIVATE = 'private'            # 私信
    TYPE_RUMOR = 'rumor'               # 谣言传播
    TYPE_GOSSIP = 'gossip'             # 八卦/闲聊传播
    
    def __init__(self, event_type: str, source_id: str, 
                 content: str, day: int, target_id: str = None):
        self.id = f"evt_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        self.type = event_type
        self.source_id = source_id
        self.target_id = target_id  # None表示广播
        self.content = content
        self.day = day
        self.timestamp = time.time()
        self.metadata = {}
        self.hops = 0  # 传播跳数
        self.recipients = []  # 已接收的接收者
    
    def is_broadcast(self) -> bool:
        return self.target_id is None
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'type': self.type,
            'source': self.source_id,
            'target': self.target_id,
            'content': self.content,
            'day': self.day,
            'hops': self.hops
        }


class EventBus:
    """
    事件总线 - 中心事件调度器
    
    功能：
    - 事件发布/订阅
    - 事件传播（支持多跳）
    - 事件过滤与路由
    - 基于事件的触发器
    """
    
    def __init__(self, social_network=None, relationship_manager=None):
        self.events = []  # 所有事件记录
        
        # 订阅者：agent_id -> list of (event_type, callback)
        self.subscribers = defaultdict(list)
        
        # 事件队列：待处理事件
        self.event_queue = []
        
        # 社交网络引用
        self.social_network = social_network
        self.relationship_manager = relationship_manager
        
        # 传播规则
        self.spread_rules = {
            Event.TYPE_MESSAGE: self._spread_to_targets,
            Event.TYPE_NOTIFICATION: self._broadcast_to_aware,
            Event.TYPE_BROADCAST: self._broadcast_all,
            Event.TYPE_GOSSIP: self._spread_gossip,
            Event.TYPE_RUMOR: self._spread_rumor,
        }
        
        # 事件主题过滤器
        self.topic_filters = defaultdict(list)
    
    def subscribe(self, agent_id: str, event_type: str, callback: Callable):
        """订阅事件"""
        self.subscribers[agent_id].append((event_type, callback))
    
    def unsubscribe(self, agent_id: str, event_type: str):
        """取消订阅"""
        if agent_id in self.subscribers:
            self.subscribers[agent_id] = [
                (t, cb) for t, cb in self.subscribers[agent_id]
                if t != event_type
            ]
    
    def publish(self, event: Event):
        """发布事件"""
        self.events.append(event)
        self.event_queue.append(event)
    
    def publish_message(self, source_id: str, target_id: str, 
                       content: str, day: int):
        """发送私信"""
        event = Event(
            Event.TYPE_MESSAGE,
            source_id,
            content,
            day,
            target_id=target_id
        )
        self.publish(event)
    
    def publish_broadcast(self, source_id: str, content: str, 
                        day: int, topic: str = None):
        """发布广播"""
        event = Event(
            Event.TYPE_BROADCAST,
            source_id,
            content,
            day
        )
        if topic:
            event.metadata['topic'] = topic
        self.publish(event)
    
    def publish_gossip(self, source_id: str, content: str, day: int):
        """发布八卦（会自动扩散）"""
        event = Event(
            Event.TYPE_GOSSIP,
            source_id,
            content,
            day
        )
        self.publish(event)
    
    def process_events(self, current_day: int, agents: Dict) -> List[Event]:
        """
        处理事件队列
        
        Args:
            current_day: 当前天数
            agents: 所有Agent的字典
        
        Returns:
            处理过程中产生的新事件
        """
        new_events = []
        still_pending = []
        
        for event in self.event_queue:
            # 根据类型决定传播方式
            spread_func = self.spread_rules.get(event.type, self._broadcast_all)
            
            next_events = spread_func(event, agents, current_day)
            
            if next_events:
                new_events.extend(next_events)
                for e in next_events:
                    self.events.append(e)
                    still_pending.append(e)
            elif event.hops >= 3:  # 超过3跳不再传播
                pass
            else:
                still_pending.append(event)
        
        self.event_queue = still_pending
        return new_events
    
    def _spread_to_targets(self, event: Event, agents: Dict, day: int) -> List[Event]:
        """向指定目标传播"""
        if event.target_id and event.target_id in agents:
            event.recipients.append(event.target_id)
            # 触发订阅者回调
            self._notify_subscriber(event.target_id, event)
        return []
    
    def _broadcast_to_aware(self, event: Event, agents: Dict, day: int) -> List[Event]:
        """向所有知晓该事件的Agent广播（基于社交网络）"""
        if not self.social_network:
            return []
        
        # 获取与事件源有关系的Agent
        reachable = self.social_network.get_agents_within_reach(
            event.source_id, depth=event.hops + 1
        )
        
        new_events = []
        for target_id in reachable:
            if target_id not in event.recipients and target_id in agents:
                event.recipients.append(target_id)
                self._notify_subscriber(target_id, event)
        
        return new_events
    
    def _broadcast_all(self, event: Event, agents: Dict, day: int) -> List[Event]:
        """向所有Agent广播"""
        new_events = []
        
        for agent_id in agents:
            if agent_id != event.source_id and agent_id not in event.recipients:
                new_event = Event(
                    event.type,
                    event.source_id,
                    event.content,
                    day,
                    target_id=agent_id
                )
                new_event.hops = event.hops + 1
                new_event.metadata = event.metadata.copy()
                new_events.append(new_event)
                event.recipients.append(agent_id)
        
        return new_events
    
    def _spread_gossip(self, event: Event, agents: Dict, day: int) -> List[Event]:
        """
        八卦传播 - 基于社交关系的概率传播
        原论文：消息在社交网络中以一定概率传播
        """
        if not self.relationship_manager:
            return self._broadcast_all(event, agents, day)
        
        new_events = []
        
        # 获取与事件源有直接关系的Agent
        if event.hops >= 2:  # 八卦最多传2跳
            return []
        
        source_rels = self.relationship_manager.get_all_relationships_for(event.source_id)
        
        for rel_info in source_rels:
            target_id = rel_info['other']
            
            if target_id in event.recipients:
                continue
            
            rel = rel_info['relationship']
            
            # 基于关系决定是否传播
            # 关系越好、越熟悉越可能传播
            spread_prob = (
                (rel.affinity + 100) / 200 * 0.5 +
                rel.familiarity * 0.3 +
                0.2
            )
            
            # 负面关系不太会传播正面八卦
            if rel.affinity < -20:
                spread_prob *= 0.3
            
            if random.random() < spread_prob:
                new_event = Event(
                    Event.TYPE_GOSSIP,
                    event.source_id,
                    f"听说：{event.content}",
                    day,
                    target_id=target_id
                )
                new_event.hops = event.hops + 1
                new_event.metadata = event.metadata.copy()
                new_event.metadata['original_source'] = event.source_id
                new_events.append(new_event)
                event.recipients.append(target_id)
        
        return new_events
    
    def _spread_rumor(self, event: Event, agents: Dict, day: int) -> List[Event]:
        """谣言传播 - 比八卦更激进，可能变异"""
        if event.hops >= 3:
            return []
        
        if not self.relationship_manager:
            return self._broadcast_all(event, agents, day)
        
        new_events = []
        source_rels = self.relationship_manager.get_all_relationships_for(event.source_id)
        
        for rel_info in source_rels:
            target_id = rel_info['other']
            
            if target_id in event.recipients:
                continue
            
            rel = rel_info['relationship']
            spread_prob = 0.4  # 谣言传播概率
            
            # 负面关系更可能传播谣言
            if rel.affinity < -30:
                spread_prob = 0.6
            
            if random.random() < spread_prob:
                # 谣言可能变形
                content = event.content
                if event.hops > 0 and random.random() < 0.3:
                    # 30%概率变形
                    content = self._mutate_rumor(content)
                
                new_event = Event(
                    Event.TYPE_RUMOR,
                    event.source_id,
                    content,
                    day,
                    target_id=target_id
                )
                new_event.hops = event.hops + 1
                new_event.metadata = event.metadata.copy()
                new_events.append(new_event)
                event.recipients.append(target_id)
        
        return new_events
    
    def _mutate_rumor(self, content: str) -> str:
        """谣言变形"""
        mutations = [
            "据说",
            "传闻",
            "有人说",
            "我听说",
            "最新消息",
        ]
        
        prefix = random.choice(mutations)
        return f"{prefix}，{content}"
    
    def _notify_subscriber(self, agent_id: str, event: Event):
        """通知订阅者"""
        if agent_id not in self.subscribers:
            return
        
        for event_type, callback in self.subscribers[agent_id]:
            if event_type == event.type or event_type == '*':
                callback(event)
    
    def get_events_for_agent(self, agent_id: str, 
                            event_type: str = None,
                            since_day: int = None) -> List[Event]:
        """获取某Agent的事件历史"""
        result = []
        
        for e in self.events:
            # 私信事件
            if e.target_id == agent_id:
                result.append(e)
            # 广播事件
            elif e.is_broadcast() and e.source_id != agent_id:
                result.append(e)
            # 自己发出的
            elif e.source_id == agent_id:
                result.append(e)
        
        # 过滤
        if event_type:
            result = [e for e in result if e.type == event_type]
        
        if since_day:
            result = [e for e in result if e.day >= since_day]
        
        return result
    
    def get_recent_broadcasts(self, days: int = 3) -> List[Event]:
        """获取最近的广播"""
        return [
            e for e in self.events
            if e.is_broadcast() and e.type == Event.TYPE_BROADCAST
        ][:days * 10]  # 限制数量
    
    def get_gossip_about(self, agent_id: str) -> List[Event]:
        """获取关于某Agent的八卦"""
        return [
            e for e in self.events
            if (e.type == Event.TYPE_GOSSIP or e.type == Event.TYPE_RUMOR)
            and agent_id in e.content
        ]
    
    def subscribe_to_topic(self, agent_id: str, topic: str, callback: Callable):
        """订阅特定主题"""
        self.topic_filters[topic].append((agent_id, callback))
    
    def get_agent_awareness(self, agent_id: str) -> Dict[str, Any]:
        """获取Agent的认知状态（知道哪些事件/消息源）"""
        events = self.get_events_for_agent(agent_id, since_day=-1)
        
        sources = set()
        topics = set()
        for e in events:
            sources.add(e.source_id)
            if 'topic' in e.metadata:
                topics.add(e.metadata['topic'])
        
        return {
            'known_sources': list(sources),
            'known_topics': list(topics),
            'message_count': len(events)
        }


class EventDrivenBehavior:
    """
    事件驱动的行为触发器
    
    监听事件总线，决定是否触发特定行为
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.behavior_triggers = []  # (condition, action) pairs
    
    def register_trigger(self, condition: Callable[[Event, Dict], bool],
                        action: Callable[[Event, Dict], Any]):
        """
        注册行为触发器
        
        Args:
            condition: 条件函数，接受(event, agents)返回bool
            action: 行为函数
        """
        self.behavior_triggers.append((condition, action))
    
    def check_and_trigger(self, event: Event, agents: Dict) -> List[Any]:
        """检查条件并触发行为"""
        results = []
        
        for condition, action in self.behavior_triggers:
            try:
                if condition(event, agents):
                    result = action(event, agents)
                    results.append(result)
            except Exception as e:
                print(f"Trigger error: {e}")
        
        return results
    
    def process_event_batch(self, events: List[Event], agents: Dict) -> List[Any]:
        """批量处理事件"""
        all_results = []
        
        for event in events:
            results = self.check_and_trigger(event, agents)
            all_results.extend(results)
        
        return all_results
