"""
感知模块 - Agent感知环境的能力
检测附近角色、事件、危险、机遇等
"""
import random


class PerceptionEvent:
    """感知事件"""
    
    def __init__(self, perception_type, content, source=None, urgency='normal'):
        self.type = perception_type
        self.content = content
        self.source = source  # 来源（角色/地点等）
        self.urgency = urgency  # urgent / normal / low
        self.acknowledged = False
    
    def __str__(self):
        return f"[{self.type}] {self.content}"


class PerceptionSystem:
    """
    感知系统
    决定Agent能感知到什么
    """
    
    # 感知类型
    TYPE_CHARACTER = 'character'  # 感知到其他角色
    TYPE_EVENT = 'event'  # 感知到事件发生
    TYPE_LOCATION = 'location'  # 感知到地点变化
    TYPE_DANGER = 'danger'  # 感知到危险
    TYPE_OPPORTUNITY = 'opportunity'  # 感知到机遇
    TYPE_MEMORY_TRIGGER = 'memory_trigger'  # 触发记忆
    
    def __init__(self):
        self.visible_range = 100  # 可见范围（地图单位）
        self.alert_level = 'normal'  # normal / cautious / alert
    
    def perceive_environment(self, agent, world) -> list:
        """
        感知当前环境
        返回：list of PerceptionEvent
        """
        perceptions = []
        current_day = world.time.day
        current_loc = agent.current_location
        
        # 1. 感知附近是否有其他角色
        nearby_characters = self._detect_nearby_characters(
            agent, world, current_day
        )
        perceptions.extend(nearby_characters)
        
        # 2. 感知周围发生的事件
        location_events = self._detect_location_events(
            agent, world, current_day
        )
        perceptions.extend(location_events)
        
        # 3. 感知危险
        dangers = self._detect_dangers(agent, world)
        perceptions.extend(dangers)
        
        # 4. 感知机遇
        opportunities = self._detect_opportunities(agent, world)
        perceptions.extend(opportunities)
        
        # 5. 记忆触发（某些事件唤醒记忆）
        memory_triggers = self._trigger_memories(
            agent, world, current_day
        )
        perceptions.extend(memory_triggers)
        
        return perceptions
    
    def _detect_nearby_characters(self, agent, world, current_day) -> list:
        """检测附近角色"""
        perceptions = []
        
        # 获取其他角色的位置
        for other_id, other_loc in world.positions.items():
            if other_id == agent.id:
                continue
            
            # 检查是否在同一位置
            if other_loc == agent.current_location:
                # 找到同地点的角色
                other_config = world.config['characters']
                other_info = next(
                    (c for c in other_config if c['id'] == other_id),
                    None
                )
                
                if other_info:
                    event = PerceptionEvent(
                        perception_type=self.TYPE_CHARACTER,
                        content=f"看到{other_info['name']}（{other_info.get('sect', 'unknown')}）也在此",
                        source=other_id,
                        urgency='normal'
                    )
                    perceptions.append(event)
        
        return perceptions
    
    def _detect_location_events(self, agent, world, current_day) -> list:
        """检测地点相关的事件"""
        perceptions = []
        
        # 获取最近一天在该地点发生的事件
        recent = [
            e for e in world.event_log
            if e.get('location') == agent.current_location
            and current_day - e.get('day', 0) <= 1
        ]
        
        for event in recent[-3:]:  # 最多3个
            if event.get('character') != agent.id:
                percevent = PerceptionEvent(
                    perception_type=self.TYPE_EVENT,
                    content=f"听闻：{event.get('content', '')}",
                    source=event.get('location'),
                    urgency='normal'
                )
                perceptions.append(percevent)
        
        return perceptions
    
    def _detect_dangers(self, agent, world) -> list:
        """检测危险"""
        perceptions = []
        
        # 危险地点判断
        location = world.get_location(agent.current_location)
        loc_type = location.get('type', 'neutral')
        
        if loc_type == 'hostile':
            danger = PerceptionEvent(
                perception_type=self.TYPE_DANGER,
                content=f"此区域({location.get('name', '')})危险重重，需小心行事",
                source=agent.current_location,
                urgency='high'
            )
            perceptions.append(danger)
        
        # 敌对宗门成员感知
        if hasattr(agent, 'hostile_sects'):
            current_sect = agent.sect
            for other_id, other_loc in world.positions.items():
                if other_loc == agent.current_location:
                    other_config = world.config['characters']
                    other_info = next(
                        (c for c in other_config if c['id'] == other_id),
                        None
                    )
                    if other_info:
                        other_sect = other_info.get('sect')
                        if other_sect in agent.hostile_sects:
                            danger = PerceptionEvent(
                                perception_type=self.TYPE_DANGER,
                                content=f"发现敌对宗门{other_sect}的{other_info['name']}",
                                source=other_id,
                                urgency='high'
                            )
                            perceptions.append(danger)
        
        return perceptions
    
    def _detect_opportunities(self, agent, world) -> list:
        """检测机遇"""
        perceptions = []
        
        # 特殊地点可能有机遇
        location = world.get_location(agent.current_location)
        loc_name = location.get('name', '')
        
        opportunity_keywords = ['秘境', '遗迹', '宝地', '机缘']
        
        for kw in opportunity_keywords:
            if kw in loc_name:
                opp = PerceptionEvent(
                    perception_type=self.TYPE_OPPORTUNITY,
                    content=f"此处可能藏有{kw}，值得探索",
                    source=agent.current_location,
                    urgency='normal'
                )
                perceptions.append(opp)
                break
        
        return perceptions
    
    def _trigger_memories(self, agent, world, current_day) -> list:
        """触发记忆相关的事件"""
        perceptions = []
        
        # 获取最近的记忆
        recent_events = agent.memory.get_recent_events(current_day, days=7)
        
        # 检查是否有人的出现触发记忆
        current_others = [
            other_id for other_id in world.positions
            if world.positions[other_id] == agent.current_location
            and other_id != agent.id
        ]
        
        for other_id in current_others:
            # 检查是否与该角色有过重要交互
            past_events = agent.memory.get_events_with_person(
                other_id, current_day, n=3
            )
            
            if past_events:
                other_config = world.config['characters']
                other_info = next(
                    (c for c in other_config if c['id'] == other_id),
                    None
                )
                if other_info:
                    last_event = past_events[0]
                    trigger = PerceptionEvent(
                        perception_type=self.TYPE_MEMORY_TRIGGER,
                        content=f"想起与{other_info['name']}的过往：{last_event.content}",
                        source=other_id,
                        urgency='low'
                    )
                    perceptions.append(trigger)
        
        return perceptions
    
    def filter_perceptions(self, perceptions: list, agent) -> list:
        """
        过滤感知
        根据角色性格决定关注什么
        """
        # 性格影响感知权重
        personality = getattr(agent, 'personality', '')
        
        # 沉稳型更关注危险
        if '沉稳' in personality:
            perceptions.sort(
                key=lambda p: (
                    0 if p.type == self.TYPE_DANGER else 1,
                    0 if p.urgency == 'high' else 1
                )
            )
        
        # 冲动型更容易忽略警告
        elif '冲动' in personality or '鲁莽' in personality:
            perceptions = [
                p for p in perceptions
                if not (p.type == self.TYPE_DANGER and p.urgency == 'high')
            ]
        
        # 限制感知数量（认知负荷）
        return perceptions[:5]
    
    def generate_perception_narrative(self, agent, perceptions: list, llm_client=None) -> str:
        """生成感知叙述 - 使用LLM根据角色设定生成个性化描述"""
        
        if not perceptions:
            return "今日似乎无事发生"
        
        # 构建感知列表
        perception_items = []
        for p in perceptions:
            if p.type == self.TYPE_CHARACTER:
                perception_items.append(f"- 看到其他角色：{p.source}")
            elif p.type == self.TYPE_EVENT:
                perception_items.append(f"- {p.content}")
            elif p.type == self.TYPE_DANGER:
                perception_items.append(f"- ⚠️ {p.content}")
            elif p.type == self.TYPE_OPPORTUNITY:
                perception_items.append(f"- ✨ {p.content}")
            elif p.type == self.TYPE_MEMORY_TRIGGER:
                perception_items.append(f"- 💭 {p.content}")
        
        perception_str = "\n".join(perception_items)
        
        # 如果有LLM客户端，使用LLM生成个性化描述
        if llm_client:
            world_type = getattr(agent, 'world_type', 'cultivation')
            
            if world_type == 'modern_urban':
                system_prompt = f"""你是{agent.name}，职业是{getattr(agent, 'occupation', '未知')}，性格{getattr(agent, 'personality', '')}。
你是一个观察记录专家。请根据以下感知内容，用符合角色职业和性格的方式，描述今天观察到了什么。
要求：自然流畅，符合现代都市生活，字数50字以内。"""
                user_prompt = f"""感知内容：
{perception_str}

请描述你今天观察/感知到的事物："""
            else:
                system_prompt = f"""你是{agent.name}，{getattr(agent, 'sect', '某')}弟子，性格{getattr(agent, 'personality', '')}。
你是一个修仙世界观察记录专家。请根据以下感知内容，用符合修仙世界的方式描述今天观察到了什么。
要求：融入修仙元素，自然流畅，50字以内。"""
                user_prompt = f"""感知内容：
{perception_str}

请描述你今日所察："""
            
            try:
                result = llm_client.generate(
                    user_prompt,
                    system_prompt=system_prompt,
                    max_tokens=200,
                    temperature=0.8
                )
                import re
                result = re.sub(r'<think>[\s\S]*?</think>', '', result, flags=re.IGNORECASE).strip()
                if result and len(result) > 10:
                    return f"今日所见所闻：\n{result}"
            except Exception:
                pass  # fallback to template
        
        # Fallback: 使用模板生成
        world_type = getattr(agent, 'world_type', 'cultivation')
        
        if world_type == 'modern_urban':
            lines = ["今日所见所闻："]
            for i, p in enumerate(perceptions, 1):
                if p.type == self.TYPE_CHARACTER:
                    lines.append(f"  {i}. 看到有人在附近")
                elif p.type == self.TYPE_EVENT:
                    lines.append(f"  {i}. {p.content}")
                elif p.type == self.TYPE_DANGER:
                    lines.append(f"  {i}. ⚠️ {p.content}")
                elif p.type == self.TYPE_OPPORTUNITY:
                    lines.append(f"  {i}. ✨ {p.content}")
                elif p.type == self.TYPE_MEMORY_TRIGGER:
                    lines.append(f"  {i}. 💭 {p.content}")
        else:
            lines = ["今日所见所闻："]
            for i, p in enumerate(perceptions, 1):
                if p.type == self.TYPE_CHARACTER:
                    lines.append(f"  {i}. 偶遇{p.source}")
                elif p.type == self.TYPE_EVENT:
                    lines.append(f"  {i}. {p.content}")
                elif p.type == self.TYPE_DANGER:
                    lines.append(f"  {i}. ⚠️ {p.content}")
                elif p.type == self.TYPE_OPPORTUNITY:
                    lines.append(f"  {i}. ✨ {p.content}")
                elif p.type == self.TYPE_MEMORY_TRIGGER:
                    lines.append(f"  {i}. 💭 {p.content}")
        
        return "\n".join(lines)
