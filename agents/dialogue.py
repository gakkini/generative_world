"""
对话生成模块 - 支持LLM增强版对话
修复：处理LLM返回截断、think标记、retry机制
"""
import random
import re


class DialogueLine:
    """对话行"""
    
    def __init__(self, speaker_id: str, content: str):
        self.speaker_id = speaker_id
        self.content = content
        self.sentiment = 0.0  # 情感极性


class Dialogue:
    """完整对话"""
    
    def __init__(self, participants=None, topic="闲聊"):
        self.participants = participants or []  # [id_a, id_b]
        self.topic = topic
        self.lines = []
        self.status = 'active'  # active / completed
        self.sentiment = 0.0
    
    def add_line(self, line: DialogueLine):
        self.lines.append(line)
    
    def get_summary(self) -> str:
        if not self.lines:
            return "无对话"
        
        total = len(self.lines)
        last_line = self.lines[-1].content if self.lines else ""
        return last_line

    def get_transcript(self) -> str:
        """获取完整对话记录"""
        if not self.lines:
            return ""
        return "\n".join([f"{line.speaker_id}：{line.content}" for line in self.lines])


# ============ LLM对话生成 ============

class LLMDialogueGenerator:
    """
    基于LLM的对话生成器
    解决：think标记截断、回复为空、格式错误
    """
    
    TEMPLATE_RESPONSES = [
        "道友所言甚是。",
        "嗯，此言有理。",
        "愿闻其详。",
        "确实如此，修仙界波诡云谲。",
        "道友好见识。",
        "善。",
        "承蒙道友指点。",
    ]
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    def generate_response(self, speaker, listener, context: str,
                          max_retries: int = 2) -> str:
        """
        生成角色对话回复
        自动处理LLM返回的各种异常情况
        """
        if not self.llm_client:
            return self._template_fallback(speaker)
        
        prompt = self._build_dialogue_prompt(speaker, listener, context)
        
        # 优先使用角色配置中的 system_prompt，否则使用默认修仙风格
        if hasattr(speaker, 'system_prompt') and speaker.system_prompt:
            system_prompt = speaker.system_prompt
        else:
            system_prompt = f"你是{speaker.name}，{speaker.sect}弟子，修为{speaker.cultivation}，性格{speaker.personality}。你正在与他人对话。请用一句简短的{getattr(speaker, 'sect', '修仙')}风格的话回应。"
        
        for attempt in range(max_retries + 1):
            raw = self.llm_client.generate(
                prompt,
                system_prompt=system_prompt,
                max_tokens=300,
                temperature=0.85
            )
            
            cleaned = self._clean_response(raw)
            
            # 检查是否有效
            if self._is_valid_response(cleaned):
                return cleaned
            
            if attempt < max_retries:
                # 换一个prompt变体重试
                prompt = self._build_dialogue_prompt_variant(
                    speaker, listener, context, attempt
                )
                continue
        
        # 所有重试都失败，使用模板fallback
        return self._template_fallback(speaker)
    
    def _build_dialogue_prompt(self, speaker, listener, context: str) -> str:
        """构建标准对话Prompt"""
        return f"""{speaker.name}（{speaker.sect} {speaker.cultivation}，性格{speaker.personality}）
当前情境：{context}

上面对话中{speaker.name}刚说了一句话，对方回应后，现在需要{speaker.name}继续说。

请用修仙世界的语气，以{speaker.name}的身份，说一句简短的回应（20字以内）。
直接输出对话内容，不要有角色标签，不要有思考过程，不要有任何其他文字。"""
    
    def _build_dialogue_prompt_variant(self, speaker, listener, context: str, attempt: int) -> str:
        """构建变体Prompt（重试时使用）"""
        variants = [
            f"道友「{context}」，作为{speaker.name}，简短回应一句（20字内）。直接输出台词。",
            f"修仙对话情境：{speaker.name}性格{speaker.personality}，情境「{context}」。一句话回应。直接说出台词，不要其他内容。",
            f"{speaker.name}在修仙世界与道友对话，对方说「{context}」。以角色语气简短回应。直接输出：",
        ]
        return variants[attempt % len(variants)]
    
    def _clean_response(self, raw: str) -> str:
        """清洗LLM原始输出"""
        if not raw:
            return ""
        
        # 移除think标记和其内容
        raw = re.sub(r'<[^>]*think[^>]*>[\s\S]*?</[^>]*think[^>]*>', '', raw, flags=re.IGNORECASE)
        raw = re.sub(r'<think>[\s\S]*?</think>', '', raw, flags=re.IGNORECASE)
        raw = re.sub(r'\[think\][\s\S]*?\[/think\]', '', raw, flags=re.IGNORECASE)
        
        # 移除可能的思考标记残留
        raw = re.sub(r'^[\s\n]*(思考|分析|理解|我认为)[\s：:]*', '', raw)
        
        # 移除角色前缀标签
        raw = re.sub(r'^(p\d+|n\d+|角色)[\s：:]*', '', raw, flags=re.IGNORECASE)
        
        # 移除"输出："、"回答："等前缀
        raw = re.sub(r'^(输出|回答|回复|Response)[\s：:]*', '', raw, flags=re.IGNORECASE)
        
        return raw.strip()
    
    def _is_valid_response(self, response: str) -> bool:
        """判断回复是否有效"""
        if not response or len(response.strip()) < 2:
            return False
        
        # 太长也不行（可能是包含了prompt）
        if len(response) > 200:
            return False
        
        # 不能是纯特殊字符
        stripped = response.strip('。！？、，：；「」（）《》【】"\'')
        if not stripped or len(stripped) < 2:
            return False
        
        # 不能是JSON
        if response.strip().startswith('{') and response.strip().endswith('}'):
            return False
        
        return True
    
    def _template_fallback(self, speaker) -> str:
        """模板fallback（完全无法使用LLM时）"""
        # 根据性格选择不同风格的回复
        personality = getattr(speaker, 'personality', '')
        
        if '沉稳' in personality or '内敛' in personality:
            fallbacks = ["点头不语。", "道友请讲。", "嗯。", "善。"]
        elif '豪迈' in personality or '洒脱' in personality:
            fallbacks = ["哈哈哈！", "道友爽快！", "正合我意！", "好说好说！"]
        elif '温婉' in personality or '聪慧' in personality:
            fallbacks = ["道友所言极是。", "愿闻其详。", "承蒙指点。", "是极是极。"]
        elif '阴狠' in personality or '果决' in personality:
            fallbacks = ["哼。", "知道了。", "不必多言。", "动手便是。"]
        else:
            fallbacks = self.TEMPLATE_RESPONSES
        
        return random.choice(fallbacks)


# ============ 对话管理器 ============

class DialogueGenerator:
    """对话管理器（整合模板 + LLM）"""
    
    GREETING_TEMPLATES = [
        "在下{name}，幸会幸会。",
        "道友有礼了。",
        "原来是道友，当真有缘。",
        "今日得见道友，实乃幸事。",
    ]
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.llm_gen = LLMDialogueGenerator(llm_client)
    
    def should_initiate_dialogue(self, agent, other, context: str) -> bool:
        """判断是否应该发起对话"""
        import random
        
        # 基于关系决定是否互动
        rel = agent.get_relationship_with(other.id)
        level = rel.get('level', 0)
        
        # 关系太差不主动
        if level < -20:
            return False
        
        # 关系好大概率互动
        if level > 50:
            return random.random() < 0.8
        
        # 陌生人小概率互动
        if level == 0:
            return random.random() < 0.2
        
        return random.random() < 0.4
    
    def generate_greeting(self, agent, other) -> str:
        """生成问候语"""
        template = random.choice(self.GREETING_TEMPLATES)
        return template.format(name=agent.name)
    
    def select_topic(self, agent, other, context: dict) -> str:
        """选择话题"""
        topics = [
            "今日天气甚好，道友可有兴致论道一番？",
            "不知道友对近日修仙界的局势有何看法？",
            "修行路上，道友可有困惑？",
            "听闻附近有秘境现世，不知是真是假？",
            "你我同在一宗，当多多走动才是。",
        ]
        return random.choice(topics)
    
    def generate_response(self, speaker, listener, last_line: str,
                          context: dict, max_retries: int = 2) -> str:
        """生成角色对对话中对方上一句话的回应"""
        # 构建上下文描述
        context_str = f"{listener.name}说：「{last_line}」"
        
        return self.llm_gen.generate_response(
            speaker, listener, context_str, max_retries=max_retries
        )
    
    def generate_dialogue(self, agent, other_agent, context: dict,
                          max_turns: int = 3) -> Dialogue:
        """生成一段完整对话"""
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
        
        # 后续轮次：LLM驱动对话
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
        """为特定角色生成对话摘要"""
        if not dialogue.lines:
            return "无对话"
        
        other_lines = [
            line for line in dialogue.lines
            if line.speaker_id != for_agent_id
        ]
        
        if not other_lines:
            return "今日未曾与人交谈。"
        
        key_points = [line.content[:30] for line in other_lines[:2]]
        return "与道友交谈：" + "；".join(key_points)
