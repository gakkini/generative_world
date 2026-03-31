"""
关系建模模块 - 角色间复杂关系系统
支持关系阶段推进、情感计算、行为影响关系
"""
import time
import random
from enum import Enum
from collections import defaultdict


class RelationshipType(Enum):
    """关系类型"""
    STRANGER = 'stranger'
    ACQUAINTANCE = 'acquaintance'
    FRIEND = 'friend'
    CLOSE_FRIEND = 'close_friend'
    ROMANTIC = 'romantic'
    RIVAL = 'rival'
    ENEMY = 'enemy'
    MENTOR = 'mentor'
    DISCIPLE = 'disciple'


class RelationshipStage(Enum):
    """关系发展阶段"""
    INITIAL = 'initial'           # 初始状态
    AWARENESS = 'awareness'        # 注意到对方
    SURFACE = 'surface'            # 表面交流
    MULTIPLE = 'multiple'           # 多次互动
    ESTABLISHED = 'established'    # 稳定关系
    CLOSE = 'close'               # 亲密关系


class Relationship:
    """
    关系对象 - 跟踪两个角色间的关系
    """
    
    # 关系阶段阈值
    STAGE_THRESHOLDS = {
        RelationshipStage.INITIAL: -50,
        RelationshipStage.AWARENESS: -20,
        RelationshipStage.SURFACE: 0,
        RelationshipStage.MULTIPLE: 30,
        RelationshipStage.ESTABLISHED: 60,
        RelationshipStage.CLOSE: 80,
    }
    
    def __init__(self, from_id: str, to_id: str):
        self.from_id = from_id
        self.to_id = to_id
        
        # 基础属性
        self.affinity = 0.0      # 亲密度 -100 ~ 100
        self.trust = 0.5         # 信任度 0 ~ 1
        self.familiarity = 0.0   # 熟悉度 0 ~ 1 (基于交互次数)
        self.affection = 0.0     # 好感度 -100 ~ 100
        
        # 关系阶段
        self.stage = RelationshipStage.INITIAL
        
        # 历史追踪
        self.interaction_count = 0
        self.positive_interactions = 0
        self.negative_interactions = 0
        self.last_interaction_day = 0
        self.first_met_day = None
        self.meeting_history = []  # 相遇地点记录
        
        # 情感记忆
        self.key_moments = []  # 重要时刻
        self.shared_experiences = []  # 共同经历
        
        # 元数据
        self.created_day = 0
        self.updated_day = 0
    
    def update_after_interaction(self, interaction_type: str, 
                                 sentiment: float, day: int,
                                 location: str = None):
        """
        交互后更新关系
        
        Args:
            interaction_type: 'dialogue'/'help'/'conflict'/'gift'/'training' etc
            sentiment: 情感极性 -1.0 ~ 1.0
            day: 当前天数
            location: 相遇地点
        """
        self.interaction_count += 1
        self.last_interaction_day = day
        
        if self.first_met_day is None:
            self.first_met_day = day
        
        # 更新熟悉度（交互次数越多越熟悉）
        self.familiarity = min(1.0, self.interaction_count / 10)
        
        # 根据情感更新亲和度
        affinity_delta = sentiment * 15
        self.affinity = max(-100, min(100, self.affinity + affinity_delta))
        
        # 根据交互类型调整信任
        if interaction_type in ['help', 'gift', 'save', 'share_secret']:
            self.trust = min(1.0, self.trust + 0.1)
        elif interaction_type in ['conflict', 'betray', 'lie']:
            self.trust = max(0.0, self.trust - 0.2)
        
        # 记录情感
        if sentiment > 0.3:
            self.positive_interactions += 1
        elif sentiment < -0.3:
            self.negative_interactions += 1
        
        # 更新好感
        self.affection += sentiment * 10
        
        # 记录相遇
        if location:
            self.meeting_history.append({
                'day': day,
                'location': location,
                'type': interaction_type
            })
        
        # 更新关系阶段
        self._update_stage()
        
        self.updated_day = day
    
    def _update_stage(self):
        """根据亲和度更新关系阶段"""
        affinity = self.affinity
        
        if affinity < self.STAGE_THRESHOLDS[RelationshipStage.AWARENESS]:
            new_stage = RelationshipStage.INITIAL
        elif affinity < self.STAGE_THRESHOLDS[RelationshipStage.SURFACE]:
            new_stage = RelationshipStage.AWARENESS
        elif affinity < self.STAGE_THRESHOLDS[RelationshipStage.MULTIPLE]:
            new_stage = RelationshipStage.SURFACE
        elif affinity < self.STAGE_THRESHOLDS[RelationshipStage.ESTABLISHED]:
            new_stage = RelationshipStage.MULTIPLE
        elif affinity < self.STAGE_THRESHOLDS[RelationshipStage.CLOSE]:
            new_stage = RelationshipStage.ESTABLISHED
        else:
            new_stage = RelationshipStage.CLOSE
        
        self.stage = new_stage
    
    def add_key_moment(self, moment_type: str, description: str, day: int):
        """添加重要时刻"""
        self.key_moments.append({
            'type': moment_type,
            'description': description,
            'day': day
        })
    
    def add_shared_experience(self, experience: str, day: int):
        """添加共同经历"""
        self.shared_experiences.append({
            'experience': experience,
            'day': day
        })
    
    def get_sentiment_trend(self) -> str:
        """获取情感趋势"""
        total = self.positive_interactions + self.negative_interactions
        if total == 0:
            return "neutral"
        
        positive_ratio = self.positive_interactions / total
        
        if positive_ratio >= 0.7:
            return "increasing"  # 越来越友好
        elif positive_ratio <= 0.3:
            return "decreasing"  # 越来越冷淡
        else:
            return "stable"
    
    def should_initiate_contact(self, current_day: int, base_probability: float = 0.3) -> bool:
        """
        决定是否主动联系对方
        
        基于：熟悉度、最后交互时间、当前关系
        """
        if self.interaction_count == 0:
            return random.random() < 0.1
        
        days_since_contact = current_day - self.last_interaction_day
        
        # 很久没联系，增加联系概率
        recency_factor = min(1.0, days_since_contact / 7)
        
        # 关系越好越可能联系
        relationship_factor = (self.affinity + 100) / 200
        
        # 熟悉度影响
        familiarity_factor = self.familiarity
        
        probability = (
            base_probability * 0.3 +
            recency_factor * 0.3 +
            relationship_factor * 0.3 +
            familiarity_factor * 0.1
        )
        
        return random.random() < probability
    
    def get_interaction_probability(self, other_id: str, context: dict) -> float:
        """
        计算在特定情境下与对方互动的概率
        
        Args:
            context: 情境信息 {'location': 'sect', 'event': 'festival', etc}
        """
        base = 0.3
        
        # 关系加成
        base += (self.affinity + 50) / 150 * 0.3
        
        # 地点加成（同一宗门更容易互动）
        if context.get('location_type') == 'sect':
            base += 0.1
        
        # 特殊事件加成
        if context.get('event') == 'festival':
            base += 0.2
        
        return min(0.9, max(0.05, base))
    
    def to_dict(self) -> dict:
        return {
            'from': self.from_id,
            'to': self.to_id,
            'affinity': self.affinity,
            'trust': self.trust,
            'familiarity': self.familiarity,
            'affection': self.affection,
            'stage': self.stage.value,
            'interaction_count': self.interaction_count,
            'sentiment_trend': self.get_sentiment_trend(),
            'last_interaction_day': self.last_interaction_day
        }
    
    def __repr__(self):
        return f"Relationship({self.from_id}->{self.to_id}, affinity={self.affinity:.1f}, stage={self.stage.value})"


class RelationshipManager:
    """
    关系管理器 - 管理所有角色的关系
    
    功能：
    - 创建/更新关系
    - 查询关系
    - 关系衰减
    - 关系驱动的行为决策
    """
    
    # 每日自然衰减量
    DAILY_DECAY = 0.5
    
    def __init__(self):
        self.relationships = {}  # (from_id, to_id) -> Relationship
        self.initialized_agents = set()
    
    def initialize_relationship(self, from_id: str, to_id: str, 
                               initial_affinity: float = 0.0,
                               initial_stage: RelationshipStage = None) -> Relationship:
        """初始化一段关系"""
        key = (from_id, to_id)
        
        if key in self.relationships:
            return self.relationships[key]
        
        rel = Relationship(from_id, to_id)
        rel.affinity = initial_affinity
        
        if initial_stage:
            rel.stage = initial_stage
        
        self.relationships[key] = rel
        return rel
    
    def get_relationship(self, from_id: str, to_id: str) -> Relationship:
        """获取关系"""
        key = (from_id, to_id)
        return self.relationships.get(key)
    
    def get_or_create(self, from_id: str, to_id: str) -> Relationship:
        """获取或创建关系"""
        key = (from_id, to_id)
        if key not in self.relationships:
            self.relationships[key] = Relationship(from_id, to_id)
        return self.relationships[key]
    
    def record_interaction(self, from_id: str, to_id: str,
                          interaction_type: str, sentiment: float,
                          day: int, location: str = None):
        """记录一次交互"""
        rel = self.get_or_create(from_id, to_id)
        rel.update_after_interaction(interaction_type, sentiment, day, location)
        
        # 同时更新反向关系（但影响减半）
        reverse_key = (to_id, from_id)
        if reverse_key not in self.relationships:
            self.relationships[reverse_key] = Relationship(to_id, from_id)
        
        reverse_rel = self.relationships[reverse_key]
        reverse_rel.update_after_interaction(
            f"reciprocal_{interaction_type}",
            sentiment * 0.5,  # 反向影响减半
            day,
            location
        )
    
    def apply_daily_decay(self, current_day: int):
        """
        每日衰减 - 长时间不互动关系会慢慢变淡
        """
        to_remove = []
        
        for (from_id, to_id), rel in self.relationships.items():
            if rel.last_interaction_day == current_day:
                continue  # 今天有互动的不衰减
            
            days_idle = current_day - rel.last_interaction_day
            if days_idle > 7:  # 超过7天开始衰减
                decay = self.DAILY_DECAY * (days_idle - 7) / 7
                rel.affinity = max(-100, rel.affinity - decay)
                
                # 衰减到一定程度考虑清理
                if rel.affinity < -80 and rel.interaction_count < 3:
                    to_remove.append((from_id, to_id))
        
        # 清理负面关系
        for key in to_remove:
            if key in self.relationships:
                del self.relationships[key]
    
    def get_all_relationships_for(self, agent_id: str) -> list:
        """获取某角色的所有关系"""
        result = []
        for (from_id, to_id), rel in self.relationships.items():
            if from_id == agent_id:
                result.append({
                    'other': to_id,
                    'relationship': rel,
                    'direction': 'outgoing'
                })
            elif to_id == agent_id:
                result.append({
                    'other': from_id,
                    'relationship': rel,
                    'direction': 'incoming'
                })
        
        # 按亲和度排序
        result.sort(key=lambda x: x['relationship'].affinity, reverse=True)
        return result
    
    def get_friends(self, agent_id: str, min_affinity: float = 40) -> list:
        """获取好友列表"""
        all_rels = self.get_all_relationships_for(agent_id)
        return [
            r for r in all_rels
            if r['relationship'].affinity >= min_affinity
        ]
    
    def get_best_friend(self, agent_id: str) -> str:
        """获取最亲密的朋友"""
        friends = self.get_all_relationships_for(agent_id)
        if not friends:
            return None
        return friends[0]['other']
    
    def get_relationship_summary(self, agent_id: str) -> str:
        """生成关系摘要"""
        rels = self.get_all_relationships_for(agent_id)
        
        if not rels:
            return "暂无深厚交情"
        
        lines = []
        for r in rels[:5]:  # 最多5个
            other = r['other']
            rel = r['relationship']
            stage = rel.stage.value
            affinity = rel.affinity
            
            if affinity >= 70:
                level = "挚友"
            elif affinity >= 40:
                level = "好友"
            elif affinity >= 15:
                level = "熟人"
            elif affinity >= -15:
                level = "陌生"
            else:
                level = "不友好"
            
            lines.append(f"{other}({level})")
        
        return ", ".join(lines)
    
    def calculate_compatibility(self, agent_a: str, agent_b: str) -> float:
        """
        计算两个角色的相性
        
        返回 0.0 ~ 1.0
        """
        rel = self.get_relationship(agent_a, agent_b)
        if not rel:
            return 0.5  # 默认中性
        
        # 综合考虑：亲密度、信任、熟悉度
        affinity_score = (rel.affinity + 100) / 200  # 0-1
        trust_score = rel.trust
        familiarity_score = rel.familiarity
        
        return (affinity_score * 0.5 + trust_score * 0.3 + familiarity_score * 0.2)
