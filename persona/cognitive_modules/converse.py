"""
converse.py - 对话模块 (Conversation)

原论文描述:
- "Agents converse with each other based on their relationships and context"
- "Dialogue is generated based on persona, relationship, and recent events"

功能:
- 基于位置和关系的对话
- 对话内容生成（模板 + LLM）
- 对话记忆记录
- 对话情感分析
"""
from typing import List, Dict, Any, Optional, Tuple
import random
import re


class Utterance:
    """单句对话"""

    def __init__(self, speaker_id: str, content: str, sentiment: float = 0.0):
        self.speaker_id = speaker_id
        self.content = content
        self.sentiment = sentiment  # -1.0 (负面) ~ 1.0 (正面)

    def __repr__(self):
        return f"<Utterance {self.speaker_id}: {self.content[:30]}>"


class Dialogue:
    """完整对话"""

    def __init__(self, participants: List[str] = None, topic: str = "闲聊"):
        self.participants = participants or []
        self.topic = topic
        self.utterances: List[Utterance] = []
        self.status: str = 'active'  # active / completed
        self.sentiment_trend: float = 0.0  # 整体情感趋势
        self.summary: str = ""

    def add_utterance(self, utterance: Utterance):
        self.utterances.append(utterance)
        # 更新情感趋势（简化）
        if self.utterances:
            sentiments = [u.sentiment for u in self.utterances]
            self.sentiment_trend = sum(sentiments) / len(sentiments)

    def get_transcript(self) -> str:
        """获取对话记录"""
        if not self.utterances:
            return ""
        return "\n".join([f"{u.speaker_id}：{u.content}" for u in self.utterances])

    def get_summary(self) -> str:
        """获取对话摘要"""
        if not self.utterances:
            return "无对话"

        # 基于情感趋势判断
        if self.sentiment_trend > 0.3:
            tone = "友好"
        elif self.sentiment_trend < -0.3:
            tone = "紧张"
        else:
            tone = "中性"

        last = self.utterances[-1].content
        return f"[{tone}] {last[:50]}"

    def complete(self):
        self.status = 'completed'


class DialogueGenerator:
    """
    对话生成器

    功能:
    1. 判断是否应该发起对话
    2. 生成对话内容（模板 + LLM）
    3. 管理对话流程
    """

    # 现代都市问候语
    MODERN_GREETINGS = [
        "嗨，你也在家呀？",
        "嘿，今天怎么样？",
        "哈喽！",
        "哇，你在这呢！",
    ]

    MODERN_TOPICS = [
        "今天想聊点什么？",
        "工作还顺利吗？",
        "最近有什么新鲜事吗？",
        "要不要一起做点什么？",
    ]

    # 修仙世界问候语
    CULTIVATION_GREETINGS = [
        "在下{name}，幸会幸会。",
        "道友有礼了。",
        "原来是道友，当真有缘。",
    ]

    CULTIVATION_TOPICS = [
        "今日天气甚好，道友可有兴致论道一番？",
        "不知道友对近日修仙界的局势有何看法？",
        "修行路上，道友可有困惑？",
    ]

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def should_initiate(self, agent: 'Persona',
                       other: 'Persona',
                       context: str = "同处一地") -> bool:
        """
        判断是否应该发起对话

        基于:
        - 关系亲密度
        - 当前情境
        - 随机因素
        """
        if not hasattr(agent, 'relationships'):
            return random.random() < 0.3

        rel = agent.relationships.get(other.id, {})
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

    def generate_dialogue(self, agent: 'Persona',
                         other: 'Persona',
                         context: Dict[str, Any],
                         max_turns: int = 3) -> Dialogue:
        """
        生成完整对话

        Args:
            agent: 当前agent
            other: 对方agent
            context: 对话上下文
            max_turns: 最大轮数

        Returns:
            Dialogue对象
        """
        world_type = getattr(agent, 'world_type', 'default')

        dialogue = Dialogue(
            participants=[agent.id, other.id],
            topic=context.get('topic', '闲聊')
        )

        # 第一轮：问候
        greeting = self._generate_greeting(agent, other, world_type)
        dialogue.add_utterance(Utterance(agent.id, greeting, sentiment=0.2))

        # 第二轮：选择话题
        topic_line = self._generate_topic(agent, other, world_type)
        dialogue.add_utterance(Utterance(agent.id, topic_line, sentiment=0.1))

        # 后续轮次：LLM驱动或模板
        turns = 0
        current_speaker = other.id
        speaker_a = agent
        speaker_b = other

        while turns < max_turns:
            last_content = dialogue.utterances[-1].content

            if current_speaker == agent.id:
                response = self._generate_response(
                    speaker_b, speaker_a, last_content, world_type
                )
                dialogue.add_utterance(Utterance(agent.id, response))
                current_speaker = other.id
            else:
                response = self._generate_response(
                    speaker_a, speaker_b, last_content, world_type
                )
                dialogue.add_utterance(Utterance(other.id, response))
                current_speaker = agent.id

            turns += 1

        dialogue.complete()
        return dialogue

    def _generate_greeting(self, agent: 'Persona',
                         other: 'Persona',
                         world_type: str) -> str:
        """生成问候语"""
        if world_type == 'modern_urban':
            greetings = self.MODERN_GREETINGS
            return random.choice(greetings).format(name=other.name)
        else:
            greetings = self.CULTIVATION_GREETINGS
            return random.choice(greetings).format(name=agent.name)

    def _generate_topic(self, agent: 'Persona',
                      other: 'Persona',
                      world_type: str) -> str:
        """生成话题"""
        if world_type == 'modern_urban':
            topics = self.MODERN_TOPICS
        else:
            topics = self.CULTIVATION_TOPICS
        return random.choice(topics)

    def _generate_response(self, speaker: 'Persona',
                         listener: 'Persona',
                         last_line: str,
                         world_type: str) -> str:
        """
        生成对对方上一句话的回应

        Args:
            speaker: 当前说话者
            listener: 听话者
            last_line: 对方最后说的话
            world_type: 世界类型
        """
        # 优先使用LLM
        if self.llm_client:
            return self._generate_llm_response(
                speaker, listener, last_line, world_type
            )

        # Fallback: 模板
        return self._generate_template_response(speaker, world_type)

    def _generate_llm_response(self, speaker: 'Persona',
                              listener: 'Persona',
                              last_line: str,
                              world_type: str) -> str:
        """使用LLM生成回应"""
        # 构建prompt
        if world_type == 'modern_urban':
            prompt = f"""{speaker.name}（{getattr(speaker, 'occupation', '未知')}，性格{getattr(speaker, 'personality', '正常')}）
对方（{listener.name}）说：「{last_line}」

以{speaker.name}的身份，用一句简短的现代风格的话回应（20字以内）。
直接输出对话内容，不要有角色标签，不要有思考过程。"""
        else:
            prompt = f"""{speaker.name}（{getattr(speaker, 'sect', '宗门')}弟子，修为{getattr(speaker, 'cultivation', '未知')}）
对方（{listener.name}）说：「{last_line}」

以{speaker.name}的身份，用一句简短的修仙风格的话回应（20字以内）。
直接输出对话内容，不要有角色标签，不要有思考过程。"""

        system_prompt = getattr(speaker, 'system_prompt', '') or self._get_default_system_prompt(speaker)

        try:
            response = self.llm_client.generate(
                prompt,
                system_prompt=system_prompt,
                max_tokens=200,
                temperature=0.85
            )

            # 清洗响应
            response = self._clean_response(response)

            if response and len(response) >= 2:
                return response

        except Exception:
            pass

        return self._generate_template_response(speaker, world_type)

    def _clean_response(self, raw: str) -> str:
        """清洗LLM响应"""
        if not raw:
            return ""

        # 移除think标记
        raw = re.sub(r'<[^>]*think[^>]*>[\s\S]*?</[^>]*think[^>]*>', '', raw, flags=re.IGNORECASE)
        raw = re.sub(r'<[^>]*think[^>]*>[\s\S]*?</[^>]*think[^>]*>', '', raw, flags=re.IGNORECASE)
        raw = re.sub(r'<think>[\s\S]*?\[/INST]', '', raw, flags=re.IGNORECASE)
        # 移除前缀标签
        raw = re.sub(r'^(p\d+|n\d+|角色|输出|回答|回复)[\s：:]*', '', raw, flags=re.IGNORECASE)

        return raw.strip()

    def _get_default_system_prompt(self, speaker: 'Persona') -> str:
        """获取默认system prompt"""
        world_type = getattr(speaker, 'world_type', 'default')

        if world_type == 'modern_urban':
            return f"你是{speaker.name}，职业是{getattr(speaker, 'occupation', '未知')}，性格{speaker.personality}。你正在与他人对话。请用一句简短自然的话回应。"
        else:
            return f"你是{speaker.name}，{speaker.sect}弟子，修为{speaker.cultivation}，性格{speaker.personality}。你正在与他人对话。请用一句简短的修仙风格的话回应。"

    def _generate_template_response(self, speaker: 'Persona',
                                   world_type: str) -> str:
        """模板生成回应（无法使用LLM时的fallback）"""
        personality = getattr(speaker, 'personality', '')

        if world_type == 'modern_urban':
            if 'INTP' in personality or '理性' in personality:
                return random.choice(["嗯嗯，知道了。", "好的，继续。", "这个嘛...让我想想。"])
            elif 'ENFP' in personality or '活泼' in personality:
                return random.choice(["哇，太有意思了！", "真的吗！", "哇哦！"])
            else:
                return random.choice(["嗯，是这样吗？", "有道理！", "好的。"])
        else:
            if '沉稳' in personality or '内敛' in personality:
                return random.choice(["点头不语。", "道友请讲。", "善。"])
            elif '豪迈' in personality or '洒脱' in personality:
                return random.choice(["哈哈哈！", "道友爽快！", "好说好说！"])
            else:
                return random.choice(["道友所言甚是。", "愿闻其详。", "承蒙指点。"])


class ConversationManager:
    """
    对话管理器

    功能:
    - 管理对话上下文
    - 协调对话流程
    - 记录对话历史
    """

    def __init__(self):
        self.active_conversations: Dict[str, Dialogue] = {}  # conversation_id -> Dialogue
        self.conversation_history: List[Dialogue] = []

    def start_conversation(self, agent_a: str, agent_b: str,
                          context: Dict[str, Any] = None) -> str:
        """开始新对话"""
        conv_id = f"conv_{agent_a}_{agent_b}_{len(self.conversation_history)}"
        dialogue = Dialogue(
            participants=[agent_a, agent_b],
            topic=context.get('topic', '闲聊') if context else '闲聊'
        )
        self.active_conversations[conv_id] = dialogue
        return conv_id

    def add_to_conversation(self, conv_id: str, utterance: Utterance):
        """添加对话"""
        if conv_id in self.active_conversations:
            self.active_conversations[conv_id].add_utterance(utterance)

    def end_conversation(self, conv_id: str):
        """结束对话"""
        if conv_id in self.active_conversations:
            dialogue = self.active_conversations[conv_id]
            dialogue.complete()
            self.conversation_history.append(dialogue)
            del self.active_conversations[conv_id]

    def get_conversation_summary(self, conv_id: str) -> str:
        """获取对话摘要"""
        if conv_id in self.active_conversations:
            return self.active_conversations[conv_id].get_summary()
        return "对话不存在"
