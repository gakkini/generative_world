"""
日记生成模块 - 仅支持LLM版本
主角强制使用LLM生成日记
"""
import random


class DiaryWriter:
    """
    日记生成器 - 仅LLM版本
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def generate(self, agent, use_llm=None) -> str:
        """
        生成日记

        Args:
            agent: Agent实例
            use_llm: 是否使用LLM（默认True，如果客户端可用）
                     主角强制使用LLM，忽略此参数

        Returns:
            str: 日记内容
        """
        is_protagonist = getattr(agent, 'role', 'npc') == 'protagonist'

        if is_protagonist:
            if not self.llm_client:
                raise RuntimeError(
                    f"[DiaryWriter] {agent.name} 是主角，必须使用LLM生成日记。"
                    " 请在初始化时配置 llm_client。"
                )
            return self._generate_with_llm(agent)

        # NPC 可选择使用模板
        effective_use_llm = use_llm if use_llm is not None else False
        if effective_use_llm and self.llm_client:
            return self._generate_with_llm(agent)
        else:
            return self._generate_with_template(agent)

    def _generate_with_template(self, agent) -> str:
        """使用模板生成日记（仅NPC可用）"""
        ctx = agent.get_prompt_context()

        title = f"【修仙日志】{ctx['name']} · {ctx['world_time']}"
        location_note = f"地点：{ctx['location_name']}（{ctx['sect']}）"
        perception_note = ctx.get('today_perceptions_desc', '今日无事')

        CULTIVATION_PHRASES = [
            "今日打坐，对于「道」之一途似有所悟。",
            "运转周天，体内灵力又凝实了几分。",
            "观摩师父所传功法，心有所感。",
            "修行之道，在于日积月累，不可懈怠。",
        ]

        REFLECTION_PHRASES = [
            "近日宗门内多有暗流涌动，需小心行事。",
            "想起师父昔日教诲，不敢或忘。",
            "修真界波诡云谲，实力才是立身之本。",
            "天下无不散之筵席，唯有道心永恒。",
        ]

        parts = [
            title,
            location_note,
            f"\n感知：{perception_note}",
        ]

        dialogue_note = ctx.get('today_dialogue_desc', '')
        if dialogue_note:
            parts.append(f"\n与人交流：{dialogue_note}")

        parts.extend([
            f"\n修行心得：{random.choice(CULTIVATION_PHRASES)}",
            f"\n今日感悟：{random.choice(REFLECTION_PHRASES)}",
        ])

        memory_summary = ctx.get('memory_summary', '')
        if memory_summary:
            parts.append(f"\n杂记：{memory_summary[:100]}")

        return "\n".join(parts)

    def _generate_with_llm(self, agent) -> str:
        """使用LLM生成高质量日记"""
        ctx = agent.get_prompt_context()

        # 感知描述
        perceptions = ctx.get('today_perceptions', [])
        perception_desc = "\n".join([f"- {p.content if hasattr(p, 'content') else str(p)}"
                                     for p in perceptions[:5]]) if perceptions else '今日无特殊感知'

        # 对话摘要
        dialogues = ctx.get('today_dialogues', [])
        dialogue_desc = "\n".join([f"- 与{d.participants}交流：{d.get_summary()}"
                                   for d in dialogues[:3]]) if dialogues else '今日未与人交谈'

        # 反思
        reflections = ctx.get('recent_reflections', [])
        reflection_desc = "\n".join([f"- {r}" for r in reflections[:3]]) if reflections else ''

        prompt = f"""你是{ctx['name']}，{ctx['sect']}弟子，修为{ctx['cultivation']}，性格{ctx['personality']}。

【当前时间】
{ctx['world_time']}

【当前位置】
{ctx['location_name']}（{ctx['sect']}）

【今日感知】
{perception_desc}

【今日与人交流】
{dialogue_desc}

【近七日反思】
{reflection_desc if reflection_desc else '暂无反思'}

请以第一人称写一篇修仙日记，要求：
1. 融入修仙世界观（灵识、筑基、周天、丹田中灵力等术语）
2. 体现角色性格特点
3. 200-300字，有古风韵味
4. 可以埋下一些剧情伏笔
5. 不要写标题，直接写正文

日记内容："""

        response = self.llm_client.generate(
            prompt,
            system_prompt=f"你是{ctx['name']}，一个修仙世界中的角色。写日记时要有角色代入感，文笔流畅，古风盎然。",
            max_tokens=1200,
            temperature=0.8
        )

        # 清洗响应
        import re
        response = re.sub(r'<[^>]*think[^>]*>[\s\S]*?</[^>]*think[^>]*>', '', response, flags=re.IGNORECASE)
        response = re.sub(r'<think>[\s\S]*?</think>', '', response, flags=re.IGNORECASE)
        response = response.strip()

        if not response or len(response) < 20:
            # Fallback to template if LLM fails
            return self._generate_with_template(agent)

        # 组装完整日记
        title = f"【修仙日志】{ctx['name']} · {ctx['world_time']}"
        location = f"地点：{ctx['location_name']}（{ctx['sect']}）"

        return f"""{title}
{location}

{response}"""

    def _generate_with_llm_simple(self, agent) -> str:
        """
        简单版LLM日记生成（流式场景使用）
        不传入完整上下文，直接用角色信息
        """
        ctx = agent.get_prompt_context()

        prompt = f"""你是{ctx['name']}，{ctx['sect']}弟子，修为{ctx['cultivation']}。
当前位置：{ctx['location_name']}
时间：{ctx['world_time']}

以角色身份写一段今日感想/日记，50字以内，古风，简短。
直接输出内容："""

        response = self.llm_client.generate(
            prompt,
            max_tokens=300,
            temperature=0.8
        )

        import re
        response = re.sub(r'<think>[\s\S]*?</think>', '', response, flags=re.IGNORECASE)
        response = response.strip()

        if not response or len(response) < 5:
            return f"【{ctx['name']}】今日无事，闭关修炼。"

        return response
