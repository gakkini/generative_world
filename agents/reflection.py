"""
反思模块 - Generative Agents 核心机制
将低层经验合成高层洞察，更新角色认知

原论文实现：
- Reflection: periodically reflects on past experiences to generate higher-level insights
- These insights reshape the agent's memory and future behavior
"""
import time
import random
from collections import defaultdict


class Reflection:
    """单条反思"""
    
    def __init__(self, content, agent_id, day, related_events=None):
        self.id = f"ref_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        self.content = content
        self.agent_id = agent_id
        self.day = day
        self.related_events = related_events or []  # 相关的记忆事件IDs
        self.importance = 0.5
        self.created_at = time.time()


class CognitiveLabel:
    """
    认知标签 - 角色对他人的认知
    例如："XXX是一个好朋友"、"YYY最近对我很冷淡"
    """
    
    def __init__(self, target_id, label_type, content, confidence=0.5, day=1):
        self.id = f"label_{int(time.time() * 1000)}"
        self.target_id = target_id  # 标签指向的角色
        self.label_type = label_type  # friend/enemy/romantic/trustworthy/etc
        self.content = content  # 标签描述
        self.confidence = confidence  # 置信度 0-1
        self.day = day  # 生成日期
        self.last_updated = day
    
    def update(self, new_content, confidence_delta, day):
        """更新标签"""
        self.content = new_content
        self.confidence = max(0.0, min(1.0, self.confidence + confidence_delta))
        self.last_updated = day


class ReflectionEngine:
    """
    反思引擎 - 核心算法
    
    原论文步骤：
    1. 观察最近的重要事件
    2. 生成"问题"（what does X mean for my future plans?）
    3. 用LLM基于记忆回答问题，生成反思
    4. 将反思存储，并更新认知标签
    """
    
    # 高重要性关键词（触发反思）
    HIGH_IMPORTANCE_KEYWORDS = [
        '生死', '决斗', '大战', '突破', '渡劫',
        '背叛', '结交', '秘籍', '功法', '师父',
        '救命之恩', '约定', '誓言', '深谈',
        '秘境', '遗迹', '宝藏', '冲突', '和解'
    ]
    
    # 反思主题模板
    REFLECTION_THEMES = [
        "这段经历对我追求修仙之道有何启示？",
        "我与他人的关系有何变化？",
        "这次遭遇对我的目标有何影响？",
        "我应该对他人的行为有何判断？",
    ]
    
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.reflections = []  # 所有反思
        self.cognitive_labels = {}  # target_id -> list of CognitiveLabel
    
    def generate_reflections(self, agent, recent_events: list, current_day: int) -> list:
        """
        生成反思
        
        Args:
            agent: Agent实例
            recent_events: 最近的事件列表
            current_day: 当前天数
        
        Returns:
            list of Reflection
        """
        if len(recent_events) < 3:
            return []
        
        # 1. 找出重要事件
        important_events = self._identify_important_events(recent_events)
        
        if not important_events:
            return []
        
        # 2. 按主题/人物分组
        grouped = self._group_events_by_theme(important_events)
        
        # 3. 为每组生成反思
        new_reflections = []
        for theme, events in grouped.items():
            reflection = self._synthesize_reflection(
                agent, theme, events, current_day
            )
            if reflection:
                new_reflections.append(reflection)
                self.reflections.append(reflection)
        
        # 4. 从反思中提取认知标签
        self._extract_cognitive_labels(agent, new_reflections, current_day)
        
        return new_reflections
    
    def _identify_important_events(self, events: list) -> list:
        """识别重要事件"""
        important = []
        for e in events:
            # 检查关键词
            content = e.content if hasattr(e, 'content') else str(e)
            for kw in self.HIGH_IMPORTANCE_KEYWORDS:
                if kw in content:
                    e.importance = getattr(e, 'importance', 0.5) + 0.3
                    break
            if getattr(e, 'importance', 0.5) >= 0.5:
                important.append(e)
        return important
    
    def _group_events_by_theme(self, events: list) -> dict:
        """按主题分组事件"""
        groups = defaultdict(list)
        
        for e in events:
            content = e.content if hasattr(e, 'content') else str(e)
            
            # 关系相关
            if any(kw in content for kw in ['对话', '交流', '遇到', '切磋']):
                groups['relationship'].append(e)
            # 修炼相关
            elif any(kw in content for kw in ['修炼', '修炼', '功法', '突破']):
                groups['cultivation'].append(e)
            # 危险相关
            elif any(kw in content for kw in ['危险', '敌人', '战斗']):
                groups['danger'].append(e)
            # 机遇相关
            elif any(kw in content for kw in ['发现', '秘境', '遗迹', '宝藏']):
                groups['opportunity'].append(e)
            # 默认
            else:
                groups['general'].append(e)
        
        return dict(groups)
    
    def _synthesize_reflection(self, agent, theme: str, events: list, day: int) -> Reflection:
        """
        综合事件生成反思
        简单版本使用模板，完整版本用LLM
        """
        if not events:
            return None
        
        # 生成反思内容（基于模板）
        if theme == 'relationship':
            content = self._synthesize_relationship_reflection(agent, events, day)
        elif theme == 'cultivation':
            content = self._synthesize_cultivation_reflection(agent, events, day)
        elif theme == 'danger':
            content = self._synthesize_danger_reflection(agent, events, day)
        elif theme == 'opportunity':
            content = self._synthesize_opportunity_reflection(agent, events, day)
        else:
            content = self._synthesize_general_reflection(agent, events, day)
        
        related_ids = [e.id if hasattr(e, 'id') else str(i) for i, e in enumerate(events)]
        
        return Reflection(
            content=content,
            agent_id=self.agent_id,
            day=day,
            related_events=related_ids
        )
    
    def _synthesize_relationship_reflection(self, agent, events, day) -> str:
        """生成关系反思"""
        # 统计与各角色的交互
        person_interactions = defaultdict(list)
        for e in events:
            if hasattr(e, 'participants'):
                for p in e.participants:
                    person_interactions[p].append(e)
        
        if len(person_interactions) == 1:
            person_id = list(person_interactions.keys())[0]
            person_name = person_id  # 简化，实际应查配置
            count = len(person_interactions[person_id])
            
            if count >= 3:
                return f"我与{person_name}近期交流频繁，这段关系值得我重视"
            else:
                return f"我与{person_name}有过一次愉快的交流"
        
        return "近期我与他人的交流让我对人情世故有了更多理解"
    
    def _synthesize_cultivation_reflection(self, agent, events, day) -> str:
        """生成修炼反思"""
        return "近日修炼有所精进，对功法有了更深的理解"
    
    def _synthesize_danger_reflection(self, agent, events, day) -> str:
        """生成危险反思"""
        return "修真界危机四伏，必须时刻保持警惕"
    
    def _synthesize_opportunity_reflection(self, agent, events, day) -> str:
        """生成机遇反思"""
        return "机缘可遇不可求，应当善于把握"
    
    def _synthesize_general_reflection(self, agent, events, day) -> str:
        """生成一般反思"""
        templates = [
            "回顾近日经历，让我对修行之路有了新的思考",
            "世事多变，唯有道心永恒",
            "修仙路上，每一步都是成长",
        ]
        return random.choice(templates)
    
    def _extract_cognitive_labels(self, agent, reflections: list, day: int):
        """从反思中提取认知标签"""
        for ref in reflections:
            content = ref.content
            
            # 从内容中提取对他人态度
            if '交流' in content or '关系' in content:
                # 检查是否有具体人物
                for other_id, rel in agent.relationships.items():
                    if other_id in content:
                        # 更新或创建标签
                        if other_id not in self.cognitive_labels:
                            self.cognitive_labels[other_id] = []
                        
                        # 检查是否已有相关标签
                        existing = [
                            l for l in self.cognitive_labels[other_id]
                            if l.label_type == 'trust'
                        ]
                        
                        if existing:
                            # 更新
                            existing[0].update(
                                f"认为对方是可信之人（{day}日更新）",
                                0.1,
                                day
                            )
                        else:
                            # 新建
                            label = CognitiveLabel(
                                target_id=other_id,
                                label_type='trust',
                                content=f"此人曾与我频繁交流，值得信任",
                                confidence=0.5,
                                day=day
                            )
                            self.cognitive_labels[other_id].append(label)
    
    def get_recent_reflections(self, current_day: int, days: int = 7) -> list:
        """获取最近N天的反思"""
        return [
            r for r in self.reflections
            if current_day - r.day <= days
        ]
    
    def get_cognitive_labels_for(self, target_id: str) -> list:
        """获取对某人的所有认知标签"""
        return self.cognitive_labels.get(target_id, [])
    
    def get_trust_level_for(self, target_id: str) -> float:
        """获取对某人的信任度"""
        labels = self.get_cognitive_labels_for(target_id)
        trust_labels = [l for l in labels if l.label_type == 'trust']
        if not trust_labels:
            return 0.5  # 默认中性
        return max(l.confidence for l in trust_labels)
