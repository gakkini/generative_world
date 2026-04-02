"""
日记生成模块 - LLM版本
根据世界类型和角色设定动态生成日记
"""
import random


def _get_diary_system_prompt(agent) -> str:
    """
    根据角色 system_prompt 和世界类型获取日记生成用的 system prompt
    
    优先级：
    1. agent.system_prompt（完整的角色设定）
    2. 基于 world_type 的默认 prompt
    """
    # 优先使用 agent 的 system_prompt
    if hasattr(agent, 'system_prompt') and agent.system_prompt:
        return agent.system_prompt + "\n\n【日记写作】你是一个日记写作专家。请用第一人称，根据上述角色设定，写一篇符合角色性格和世界观的日记。"
    
    # Fallback: 根据 world_type 生成
    world_type = getattr(agent, 'world_type', 'cultivation')
    
    if world_type == 'modern_urban':
        # 现代都市
        occupation = getattr(agent, 'occupation', '')
        name = agent.name
        personality = getattr(agent, 'personality', '')
        return f"""你是{name}，职业是{occupation}，性格{personality}。

你是一个日记写作专家。请用第一人称，写一篇符合现代都市人角色的日记，要求：
1. 融入现代都市生活场景（工作、家庭、休闲、电子设备等）
2. 体现角色职业和性格特点
3. 200-300字，自然流畅
4. 可以包含内心独白和情感表达
5. 不要写标题，直接写正文"""
    
    else:
        # 修仙世界（默认）
        sect = getattr(agent, 'sect', '未知宗门')
        cultivation = getattr(agent, 'cultivation', '凡人')
        personality = getattr(agent, 'personality', '')
        name = agent.name
        return f"""你是{name}，{sect}弟子，修为{cultivation}，性格{personality}。

你是一个修仙日记写作专家。请用第一人称，写一篇修仙风格的日记，要求：
1. 融入修仙世界观（灵识、筑基、周天、丹田、灵力等术语）
2. 体现角色性格特点
3. 200-300字，有古风韵味
4. 可以埋下一些剧情伏笔
5. 不要写标题，直接写正文"""


class DiaryWriter:
    """日记生成器"""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    def generate(self, agent, use_llm=None) -> str:
        """生成日记"""
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
        world_type = getattr(agent, 'world_type', 'cultivation')
        
        if world_type == 'modern_urban':
            title = f"【日记】{ctx['name']} · {ctx['world_time']}"
            phrases = [
                "今天又是充实的一天。",
                "工作之余，也不忘享受生活。",
                "和朋友的聊天让我心情愉悦。",
            ]
        else:
            title = f"【修仙日志】{ctx['name']} · {ctx['world_time']}"
            phrases = [
                "今日打坐，对于「道」之一途似有所悟。",
                "运转周天，体内灵力又凝实了几分。",
                "修行之道，在于日积月累。",
            ]
        
        parts = [
            title,
            f"地点：{ctx['location_name']}（{ctx['sect']}）",
            f"\n感知：{ctx.get('today_perceptions_desc', '今日无事')}",
            f"\n{random.choice(phrases)}",
        ]
        
        dialogue_note = ctx.get('today_dialogue_desc', '')
        if dialogue_note:
            parts.append(f"\n与人交流：{dialogue_note}")
        
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
        dialogue_desc = "\n".join([f"- 与{d.get('participants', '某人')}交流：{d.get('summary', '')[:50]}"
                                   for d in dialogues[:3]]) if dialogues else '今日未与人交谈'
        
        # 反思
        reflections = ctx.get('recent_reflections', [])
        reflection_desc = "\n".join([f"- {r}" for r in reflections[:3]]) if reflections else ''
        
        world_type = getattr(agent, 'world_type', 'cultivation')
        
        # 构建上下文感知的 prompt
        if world_type == 'modern_urban':
            context_block = f"""【当前时间】
{ctx['world_time']}

【当前位置】
{ctx['location_name']}

【职业】
{getattr(agent, 'occupation', '未知')}

【今日感知】
{perception_desc}

【今日与人交流】
{dialogue_desc}

【近七日反思】
{reflection_desc if reflection_desc else '暂无反思'}"""
        else:
            context_block = f"""【当前时间】
{ctx['world_time']}

【当前位置】
{ctx['location_name']}（{ctx['sect']}）

【修为】
{ctx['cultivation']}

【今日感知】
{perception_desc}

【今日与人交流】
{dialogue_desc}

【近七日反思】
{reflection_desc if reflection_desc else '暂无反思'}"""
        
        # 优先使用 agent.system_prompt，其次基于world_type生成
        if hasattr(agent, 'system_prompt') and agent.system_prompt:
            system_prompt = agent.system_prompt
        else:
            system_prompt = _get_diary_system_prompt(agent)
        
        prompt = f"""{context_block}

请根据上述信息，写一篇日记。"""

        response = self.llm_client.generate(
            prompt,
            system_prompt=system_prompt,
            max_tokens=500,
            temperature=0.8
        )
        
        # 清理思考标签
        import re
        response = re.sub(r'<think>[\s\S]*?</think>', '', response, flags=re.IGNORECASE)
        response = response.strip()
        
        if not response or len(response) < 20:
            # Fallback to template if LLM fails
            return self._generate_with_template(agent)
        
        # 组装完整日记
        if world_type == 'modern_urban':
            title = f"【日记】{ctx['name']} · {ctx['world_time']}"
        else:
            title = f"【修仙日志】{ctx['name']} · {ctx['world_time']}"
        
        location = f"地点：{ctx['location_name']}"
        
        return f"""{title}
{location}

{response}"""
    
    def _generate_with_llm_simple(self, agent) -> str:
        """简单版LLM日记生成"""
        ctx = agent.get_prompt_context()
        world_type = getattr(agent, 'world_type', 'cultivation')
        
        if world_type == 'modern_urban':
            prompt = f"""你是{ctx['name']}，职业是{getattr(agent, 'occupation', '未知')}。
当前位置：{ctx['location_name']}
时间：{ctx['world_time']}

以角色身份写一段今日感想/日记，50字以内，现代风格，简短自然。
直接输出内容："""
        else:
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
            if world_type == 'modern_urban':
                return f"【{ctx['name']}】今日无事，享受生活。"
            else:
                return f"【{ctx['name']}】今日无事，闭关修炼。"
        
        return response
