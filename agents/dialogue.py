"""
对话模块 - Agent间的对话生成
"""
import random
import time


class DialogueLine:
    """单句对话"""
    
    def __init__(self, speaker_id, content, emotion=None):
        self.id = f"dlg_{int(time.time() * 1000)}"
        self.speaker = speaker_id
        self.content = content
        self.emotion = emotion  # neutral / happy / angry / fearful / etc.
        self.timestamp = time.time()


class Dialogue:
    """一段对话"""
    
    def __init__(self, participants: list, topic=None):
        self.id = f"dialogue_{int(time.time() * 1000)}"
        self.participants = participants  # [char_id, ...]
        self.topic = topic
        self.lines = []
        self.context = {}  # 对话上下文
        self.status = 'ongoing'  # ongoing / completed
    
    def add_line(self, line: DialogueLine):
        self.lines.append(line)
    
    def get_transcript(self) -> str:
        """获取对话记录"""
        return "\n".join([
            f"{line.speaker}：{line.content}"
            for line in self.lines
        ])
    
    def get_summary(self) -> str:
        """获取对话摘要"""
        if not self.lines:
            return ""
        
        first = self.lines[0]
        last = self.lines[-1]
        
        return f"与{', '.join(self.participants)}讨论{self.topic}，从「{first.content[:20]}」到「{last.content[:20]}」"


class DialogueGenerator:
    """
    对话生成器
    基于记忆、关系、场景生成自然对话
    """
    
    # 对话模板
    GREETING_TEMPLATES = [
        "{speaker}点头示意：「道友有礼。」",
        "{speaker}抱拳道：「幸会幸会，不知阁下如何称呼？」",
        "{speaker}微微一笑：「这位道友面生得很，可是初来此地？」",
    ]
    
    CULTIVATION_TOPICS = [
        "近日修行可有所悟？",
        "道友可知哪里灵气充沛，适合闭关？",
        "听闻最近有秘境开启，不知是真是假？",
        "筑基之道，道友可有心得？",
    ]
    
    SECT_TOPICS = [
        "不知贵派近日可有什么大事？",
        "听闻{other_sect}与{self_sect}近来颇有嫌隙？",
        "道友可知最近各宗门的动向？",
    ]
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    def should_initiate_dialogue(self, agent, other_agent, situation: str) -> bool:
        """
        判断是否应该发起对话
        
        Args:
            agent: 当前角色
            other_agent: 对方
            situation: 当前情境
        
        Returns:
            bool: 是否发起对话
        """
        # 性格因素
        personality = agent.personality
        
        # 沉稳内敛型不爱主动搭话
        if '沉稳' in personality or '内向' in personality:
            return random.random() < 0.3
        
        # 豪迈洒脱型主动
        if '豪迈' in personality or '洒脱' in personality:
            return random.random() < 0.7
        
        # 活泼开朗型爱社交
        if '活泼' in personality or '开朗' in personality:
            return random.random() < 0.8
        
        # 默认50%
        return random.random() < 0.5
    
    def generate_greeting(self, agent, other_agent) -> str:
        """生成问候语"""
        templates = self.GREETING_TEMPLATES
        template = random.choice(templates)
        return template.format(speaker=agent.name)
    
    def select_topic(self, agent, other_agent, context: dict) -> str:
        """选择话题"""
        topics = []
        
        # 修为话题（通用）
        if random.random() < 0.4:
            topics.extend(self.CULTIVATION_TOPICS)
        
        # 宗门话题（不同宗门）
        if agent.sect != other_agent.sect:
            topic = random.choice(self.SECT_TOPICS)
            topic = topic.format(
                other_sect=other_agent.sect,
                self_sect=agent.sect
            )
            topics.append(topic)
        
        # 从记忆中提取话题
        recent_interactions = []
        if hasattr(agent, 'memory') and agent.memory:
            recent_interactions = agent.memory.get_events_with_person(
                other_agent.id,
                agent.world.time.day if hasattr(agent, 'world') else 1,
                n=2
            )
        if recent_interactions:
            topics.append(f"上次与道友谈及{recent_interactions[0].content[:15]}...")
        
        return random.choice(topics) if topics else "今日天气甚好，道友可有兴致论道一番？"
    
    def generate_response(self, agent, other_agent, their_line: str, 
                         context: dict) -> str:
        """生成对其他角色台词的回应"""
        
        if self.llm_client:
            return self._generate_with_llm(
                agent, other_agent, their_line, context
            )
        else:
            return self._fallback_response(agent, other_agent, their_line)
    
    def _fallback_response(self, agent, other_agent, their_line: str) -> str:
        """使用模板生成回应"""
        responses = [
            "道友所言甚是。",
            "嗯，此言有理。",
            "愿闻其详。",
            "确实如此，修仙界波诡云谲。",
            "道友好见识。",
        ]
        return random.choice(responses)
    
    def _generate_with_llm(self, agent, other_agent, their_line: str,
                          context: dict) -> str:
        """使用LLM生成更自然的对话"""
        
        prompt = f"""场景：{context.get('location_name', '某地')}
角色A：{agent.name}（{agent.sect}弟子，修为{agent.cultivation}）
角色B：{other_agent.name}（{other_agent.sect}弟子，修为{other_agent.cultivation}）
性格A：{agent.personality}

角色B刚才说：「{their_line}」

请以角色A的身份，生成角色A的回应。要符合角色性格，自然流畅。
回应应控制在20字以内。

回应："""
        
        response = self.llm_client.generate(prompt, max_tokens=100)
        return response.strip()
    
    def generate_dialogue(self, agent, other_agent, context: dict,
                        max_turns: int = 3) -> Dialogue:
        """
        生成一段完整对话
        
        Args:
            agent: 角色A
            other_agent: 角色B  
            context: 对话上下文（地点、时间等）
            max_turns: 最大轮次
        
        Returns:
            Dialogue对象
        """
        dialogue = Dialogue(
            participants=[agent.id, other_agent.id],
            topic="初次相遇"
        )
        
        # 第一轮：问候
        greeting = self.generate_greeting(agent, other_agent)
        dialogue.add_line(DialogueLine(agent.id, greeting))
        
        # 第二轮：选择话题
        topic = self.select_topic(agent, other_agent, context)
        dialogue.add_line(DialogueLine(agent.id, topic))
        
        # 后续轮次：简单对话
        turns = 0
        current_speaker = other_agent.id
        agent_a = agent
        agent_b = other_agent
        
        while turns < max_turns:
            their_line = dialogue.lines[-1].content if dialogue.lines else ""
            
            if current_speaker == agent.id:
                response = self.generate_response(
                    agent_b, agent_a, their_line, context
                )
                dialogue.add_line(DialogueLine(agent.id, response))
                current_speaker = other_agent.id
            else:
                response = self.generate_response(
                    agent_a, agent_b, their_line, context
                )
                dialogue.add_line(DialogueLine(other_agent.id, response))
                current_speaker = agent.id
            
            turns += 1
        
        dialogue.status = 'completed'
        return dialogue
    
    def generate_dialogue_summary(self, dialogue: Dialogue, 
                                 for_agent_id: str) -> str:
        """
        为特定角色生成对话摘要
        （从该角色视角的对话理解）
        """
        if not dialogue.lines:
            return "无对话"
        
        lines_from_agent = [
            line for line in dialogue.lines
            if line.speaker == for_agent_id
        ]
        
        other_lines = [
            line for line in dialogue.lines
            if line.speaker != for_agent_id
        ]
        
        if not other_lines:
            return "今日未曾与人交谈。"
        
        other_name = dialogue.participants[1] if dialogue.participants[0] == for_agent_id \
                     else dialogue.participants[0]
        
        summary_parts = [f"与{other_name}交谈："]
        
        # 提取关键信息
        key_points = [line.content[:30] for line in other_lines[:2]]
        summary_parts.extend([f"- {p}..." for p in key_points])
        
        return "\n".join(summary_parts)
