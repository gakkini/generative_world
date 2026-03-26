"""日记生成器"""
import random


class DiaryWriter:
    """日记生成器（简单版本，可扩展为LLM调用）"""
    
    # 模板片段库
    MORNING_PHRASES = [
        "晨钟暮鼓，修仙无岁。",
        "东方既白，又是新的一日。",
        "天际初明，我于山巅吐纳灵气。",
        "露水未干，已闻远处钟声。",
    ]
    
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
    
    def __init__(self, llm_client=None):
        """
        llm_client: LLM客户端，如果为None则使用模板生成
        """
        self.llm_client = llm_client
    
    def generate(self, agent, use_llm=False) -> str:
        """
        生成日记
        
        Args:
            agent: Agent实例
            use_llm: 是否使用LLM生成（需要配置LLM客户端）
        
        Returns:
            str: 日记内容
        """
        if use_llm and self.llm_client:
            return self._generate_with_llm(agent)
        else:
            return self._generate_with_template(agent)
    
    def _generate_with_template(self, agent) -> str:
        """使用模板生成日记（离线可用）"""
        ctx = agent.get_prompt_context()
        
        # 标题
        title = f"【修仙日志】{ctx['name']} · {ctx['world_time']}"
        
        # 地点
        location_note = f"地点：{ctx['location_name']}（{ctx['sect']}）"
        
        # 感知描述
        perception_note = ctx.get('today_perceptions_desc', '今日无事')
        
        # 对话摘要
        dialogue_note = ctx.get('today_dialogue_desc', '')
        
        # 今日行为
        events = agent.today_dialogues if hasattr(agent, 'today_dialogues') else []
        
        # 组合日记
        parts = [
            title,
            location_note,
            f"\n感知：{perception_note}",
        ]
        
        if dialogue_note:
            parts.append(f"\n与人交流：{dialogue_note}")
        
        parts.extend([
            f"\n修行心得：{random.choice(self.CULTIVATION_PHRASES)}",
            f"\n今日感悟：{random.choice(self.REFLECTION_PHRASES)}",
        ])
        
        # 添加记忆摘要
        memory_summary = ctx.get('memory_summary', '')
        if memory_summary:
            parts.append(f"\n杂记：{memory_summary[:100]}")
        
        return "\n".join(parts)
    
    def _generate_with_llm(self, agent) -> str:
        """使用LLM生成更丰富的日记"""
        ctx = agent.get_prompt_context()
        
        prompt = f"""你是{ctx['name']}，{ctx['sect']}弟子，修为{ctx['cultivation']}，性格{ctx['personality']}。

当前时间：{ctx['world_time']}
当前位置：{ctx['location_name']}

今日经历：
{chr(10).join(['- ' + e for e in ctx['today_events']]) if ctx['today_events'] else '今日在静室中闭关修炼'}

请以第一人称写一篇修仙日记，要求：
1. 融入修仙世界观（灵识、筑基、丹劫等术语）
2. 体现角色性格
3. 可埋下伏笔
4. 字数200-400字
5. 文笔要有古风韵味

日记内容："""
        
        # 调用LLM
        response = self.llm_client.generate(prompt)
        return response


class LLMClient:
    """简单的LLM客户端封装"""
    
    def __init__(self, api_key=None, model="gpt-4"):
        self.api_key = api_key
        self.model = model
    
    def generate(self, prompt, max_tokens=1000) -> str:
        """
        调用LLM生成文本
        TODO: 接入实际的LLM API
        """
        # 这里暂时返回提示信息，后续接入实际API
        return f"[LLM调用占位] 请配置LLM API以生成真实日记\n\n参考Prompt:\n{prompt[:500]}..."
