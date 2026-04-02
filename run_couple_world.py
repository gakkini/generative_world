#!/usr/bin/env python3
"""
MBTI情侣世界 - Generative World核心模块运行
使用 World/Agent/Brain 模拟器运行陆子衡(INTP)与林念念(ENFP)的情侣对话

通过项目的 core 模块（World, Agent, DialogueGenerator）驱动，而非独立脚本。
"""
import os
import sys
import json
import re
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import World
from agents.base import Agent, create_agents, create_shared_systems
from agents.dialogue import DialogueGenerator, Dialogue, DialogueLine
from llm.interface import MiniMaxClient

# ============ 日志配置 ============
LOG_FILE = "/root/.openclaw/workspace/logs/couple_world_dialogue.log"
REPORT_FILE = "/root/.openclaw/workspace/logs/couple_world_report.log"


def log_msg(fp, msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    fp.write(line + "\n")
    fp.flush()


def init_logs():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"""
{'='*70}
MBTI 情侣对话模拟 - Generative World 核心模块
测试时间: {ts}
World/Agent 模拟器 + MiniMax API
base_url: https://api.minimaxi.com/v1
{'='*70}
"""
    print(header)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(header + "\n")
    return ts


def generate_report(ts, dialogue_log, turns, stop_reason):
    """生成运行报告"""
    # 分析对话质量
    lu_lines = [m for m in dialogue_log if m['speaker'] == '陆子衡']
    niannian_lines = [m for m in dialogue_log if m['speaker'] == '林念念']
    
    avg_lu_len = sum(len(m['text']) for m in lu_lines) / max(len(lu_lines), 1)
    avg_nn_len = sum(len(m['text']) for m in niannian_lines) / max(len(niannian_lines), 1)
    
    # 检查MBTI特征
    ti_count = sum(1 for m in lu_lines if any(kw in m['text'] for kw in ['逻辑', '科学', '根据', '其实', '研究', '定律', '数据']))
    ne_count = sum(1 for m in niannian_lines if any(kw in m['text'] for kw in ['觉得', '好像', '突然', '好想', '好啦', '哈哈', '诶']))
    
    report = f"""
{'='*70}
MBTI 情侣对话模拟 - 运行报告
Generative World Core Modules
测试时间: {ts}
{'='*70}

运行概要
--------
  角色: 陆子衡(INTP) × 林念念(ENFP)
  场景: 现代都市同居 - 温馨小家
  运行模块: World + Agent + DialogueGenerator
  API: MiniMax-M2.7 (base_url=https://api.minimaxi.com/v1)

对话统计
--------
  总轮次: {turns}
  陆子衡发言: {len(lu_lines)} 次
  林念念发言: {len(niannian_lines)} 次
  平均陆子衡发言长度: {avg_lu_len:.1f} 字
  平均林念念发言长度: {avg_nn_len:.1f} 字
  停止原因: {stop_reason}

MBTI特征检测
------------
  陆子衡(INTP) Ti特征词出现: {ti_count} 次
  林念念(ENFP) Ne/Fi特征词出现: {ne_count} 次

对话内容
--------
"""
    for i, m in enumerate(dialogue_log):
        report += f"  [{i+1}] {m['speaker']}: {m['text'][:100]}"
        if len(m['text']) > 100:
            report += "..."
        report += "\n"

    report += f"""
{'='*70}
报告生成完毕
{'='*70}
"""
    
    print(report)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report)


class MBTIDialogueRunner:
    """MBTI情侣对话运行器 - 使用项目核心模块"""
    
    def __init__(self, config_path, llm_client):
        self.llm_client = llm_client
        self.dialogue_log = []
        self.turn_count = 0
        
        # 加载世界配置
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 替换环境变量
        api_key = os.environ.get('MINIMAX_API_KEY', '')
        if config.get('llm', {}).get('api_key') == '${MINIMAX_API_KEY}':
            config['llm']['api_key'] = api_key
        
        self.config = config
        
        # 创建世界
        self.world = World(config_path=config_path)
        
        # 创建共享系统
        self.social_network, self.relationship_manager, self.event_bus, self.behavior_engine = \
            create_shared_systems()
        
        # 创建Agent
        self.agents = {}
        for char_cfg in config['characters']:
            if char_cfg.get('role') == 'protagonist':
                agent = Agent(
                    char_cfg,
                    self.world,
                    social_network=self.social_network,
                    relationship_manager=self.relationship_manager,
                    event_bus=self.event_bus,
                    behavior_engine=self.behavior_engine
                )
                # 装备LLM客户端
                agent.planner.llm_client = llm_client
                agent.dialogue_gen = DialogueGenerator(llm_client)
                agent.dialogue_gen.llm_gen.llm_client = llm_client
                
                # 保存system_prompt用于直接LLM调用
                agent.system_prompt = char_cfg.get('system_prompt', '')
                agent.mbti = char_cfg.get('mbti', 'N/A')
                
                self.agents[char_cfg['id']] = agent
                print(f"  🧠 {agent.name} ({agent.mbti}) - 初始化完成")
        
        # 获取两个主角引用
        self.lu = self.agents.get('lu_ziheng')
        self.nn = self.agents.get('lin_niannian')
        
        # 设置初始关系（情侣）
        if self.lu and self.nn:
            self.lu.relationships[self.nn.id] = {
                'type': '恋人',
                'level': 80,
                'history': []
            }
            self.nn.relationships[self.lu.id] = {
                'type': '恋人',
                'level': 80,
                'history': []
            }
    
    def run_dialogue_turn(self, max_tokens=200, temperature=0.8):
        """
        执行一轮对话 - 使用MiniMaxClient直接调用
        这是核心方法，使用项目的LLMInterface而非dialogue.py的模板
        """
        # 构建对话上下文
        context_lines = []
        for m in self.dialogue_log[-12:]:  # 最近12条消息
            speaker = m['speaker']
            text = m['text']
            context_lines.append(f"{speaker}：「{text}」")
        
        context_str = "\n".join(context_lines) if context_lines else "（对话刚开始）"
        
        turn_num = self.turn_count + 1
        
        # ===== 陆子衡发言 =====
        # 构建prompt - 让LLM扮演陆子衡回应林念念的最后一句话
        if self.dialogue_log:
            last_msg = self.dialogue_log[-1]['text']
            last_speaker = self.dialogue_log[-1]['speaker']
            prompt_text = f"对话上下文：\n{context_str}\n\n林念念刚刚说：「{last_msg}」\n\n作为陆子衡，请用简洁自然的方式回应林念念。注意：你是一个真实的INTP男友，不要说自己是AI或语言模型。保持30-80字。中文回答。"
        else:
            prompt_text = f"""场景：周六下午，客厅。陆子衡坐在沙发上看着书，林念念窝在旁边画画。

{context_str}

作为陆子衡，用一句话开启这段对话。简洁自然，体现INTP的性格特点。30字以内。中文。"""
        
        response_lu = self.llm_client.generate(
            prompt=prompt_text,
            system_prompt=self.lu.system_prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        # 清理响应
        lu_text = self._clean_response(response_lu)
        self.dialogue_log.append({'speaker': '陆子衡', 'text': lu_text, 'turn': turn_num})
        print(f"  💬 陆子衡: {lu_text[:60]}")
        self.turn_count += 1
        
        # ===== 林念念发言 =====
        context_lines_now = "\n".join([f"{m['speaker']}：「{m['text']}」" for m in self.dialogue_log[-12:]])
        
        if self.dialogue_log:
            last_msg_lu = self.dialogue_log[-1]['text']
            prompt_nn = f"对话上下文：\n{context_lines_now}\n\n陆子衡说：「{last_msg_lu}」\n\n作为林念念，请用活泼自然的方式回应。注意：你是一个真实的ENFP女友，不要说自己是AI或语言模型。保持30-80字。中文回答。"
        else:
            prompt_nn = f"""场景：周六下午，客厅。陆子衡坐在沙发上看着书，林念念窝在旁边画画。

{context_str}

作为林念念，请主动和陆子衡说话。活泼自然，体现ENFP的性格特点。30字以内。中文。"""
        
        response_nn = self.llm_client.generate(
            prompt=prompt_nn,
            system_prompt=self.nn.system_prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        nn_text = self._clean_response(response_nn)
        self.dialogue_log.append({'speaker': '林念念', 'text': nn_text, 'turn': turn_num})
        print(f"  💬 林念念: {nn_text[:60]}")
        self.turn_count += 1
        
        return lu_text, nn_text
    
    def _clean_response(self, response: str) -> str:
        """清理LLM响应"""
        raw = response.strip()
        
        # 移除think标签
        raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL)
        raw = re.sub(r'\[think\][\s\S]*?\[/think\]', '', raw, flags=re.IGNORECASE)
        
        # 移除角色前缀标签
        raw = re.sub(r'^(陆子衡|林念念)[\s：:]*', '', raw)
        
        # 移除"输出："、"回答："等前缀
        raw = re.sub(r'^(输出|回答|回复|Response)[\s：:]*', '', raw, flags=re.IGNORECASE)
        
        # 移除开头的思考说明
        raw = re.sub(r'^[\s\n]*(思考|分析|理解|我认为)[\s：:]*', '', raw)
        
        # 移除引号包裹
        raw = raw.strip('"\'「」''""')
        
        return raw.strip()
    
    def check_quality(self, text: str, speaker: str) -> tuple:
        """检查输出质量"""
        issues = []
        
        if len(text) < 2:
            issues.append("输出过短")
        
        if re.search(r'(.)\1{4,}', text):
            issues.append("字符重复")
        
        if re.search(r'(我是AI|作为AI|我的功能|我可以帮)', text):
            issues.append("角色混乱(AI)")
        
        if re.search(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', text):
            issues.append("控制字符")
        
        return ("OK" if not issues else f"ISSUE: {', '.join(issues)}"), issues
    
    def run(self, target_turns=25, max_tokens=200, temperature=0.8):
        """
        运行完整模拟
        target_turns: 目标对话轮数（每轮包含两人各一次发言）
        """
        log_fp = open(LOG_FILE, "a", encoding="utf-8")
        
        print(f"\n{'='*60}")
        print(f"开始MBTI情侣对话模拟")
        print(f"目标: {target_turns} 轮")
        print(f"{'='*60}\n")
        
        log_msg(log_fp, f"开始模拟，目标 {target_turns} 轮")
        
        # 设置场景
        scene_msg = "场景：周六下午，阳光从落地窗洒进温馨的客厅。陆子衡窝在沙发一角看书，林念念趴在茶几旁画画，一切都很安静美好。"
        self.dialogue_log.append({'speaker': '系统', 'text': scene_msg, 'turn': 0})
        print(f"  🎬 {scene_msg}")
        log_msg(log_fp, f"系统: {scene_msg}")
        
        stop_reason = "完成"
        
        try:
            while self.turn_count < target_turns:
                current_round = (self.turn_count // 2) + 1
                print(f"\n--- 第 {current_round} 轮对话 ---")
                log_msg(log_fp, f"\n--- 第 {current_round} 轮对话 ---")
                
                lu_text, nn_text = self.run_dialogue_turn(max_tokens, temperature)
                
                # 质量检查
                lu_quality, lu_issues = self.check_quality(lu_text, '陆子衡')
                nn_quality, nn_issues = self.check_quality(nn_text, '林念念')
                
                if lu_issues:
                    log_msg(log_fp, f"  ⚠️ 陆子衡质量问题: {', '.join(lu_issues)}")
                if nn_issues:
                    log_msg(log_fp, f"  ⚠️ 林念念质量问题: {', '.join(nn_issues)}")
                
                # 检查是否出现重复（连续3条消息相似）
                if len(self.dialogue_log) >= 6:
                    recent = [m['text'] for m in self.dialogue_log[-6:] if m['speaker'] != '系统']
                    if len(set(recent[-3:])) == 1:
                        stop_reason = f"内容重复（第{current_round}轮后）"
                        log_msg(log_fp, f"🛑 检测到内容重复，停止测试")
                        break
                
                # 安全检查：turn_count是单个发言计数，25轮=50次发言
                if self.turn_count > target_turns + 10:
                    stop_reason = "安全限制"
                    break
                
                log_msg(log_fp, f"轮次 {current_round} | 陆子衡({len(lu_text)}字) | 林念念({len(nn_text)}字)")
        
        except Exception as e:
            stop_reason = f"异常: {str(e)[:80]}"
            log_msg(log_fp, f"❌ 发生异常: {e}")
            import traceback
            log_msg(log_fp, traceback.format_exc())
        
        finally:
            log_fp.close()
        
        # 计算实际轮数（每次循环=1轮，turn_count是2x）
        actual_rounds = self.turn_count // 2
        
        print(f"\n{'='*60}")
        print(f"模拟完成")
        print(f"实际轮数: {actual_rounds} / 目标 {target_turns//2} (按发言计: {target_turns})")
        print(f"停止原因: {stop_reason}")
        print(f"{'='*60}")
        
        return actual_rounds, stop_reason


def main():
    ts = init_logs()
    
    print("\n" + "="*60)
    print("🌍 Generative World - MBTI情侣对话模拟")
    print("="*60)
    
    # 1. 配置路径
    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'config/couple_world.yaml'
    )
    print(f"\n📋 加载世界配置: {config_path}")
    
    # 2. 获取API Key
    import yaml
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    api_key = os.environ.get('MINIMAX_API_KEY', '')
    if not api_key:
        api_key = cfg.get('llm', {}).get('api_key', '')
    if not api_key:
        print("❌ 错误: MINIMAX_API_KEY 未设置且配置文件中也未找到")
        sys.exit(1)
    
    # 3. 初始化MiniMax客户端
    print(f"\n🔧 初始化 MiniMax Client...")
    print(f"   base_url: https://api.minimaxi.com/v1")
    print(f"   model: MiniMax-M2.7")
    
    llm_client = MiniMaxClient(api_key=api_key, model="MiniMax-M2.7")
    print("   ✅ LLM客户端初始化成功")
    
    # 4. 创建运行器
    print(f"\n🤖 初始化MBTI Agent...")
    runner = MBTIDialogueRunner(config_path, llm_client)
    
    print(f"\n   角色列表:")
    for aid, agent in runner.agents.items():
        mbti = getattr(agent, 'mbti', 'N/A')
        print(f"   - {agent.name} ({mbti})")
    
    # 5. 运行模拟
    print(f"\n{'='*60}")
    print("开始模拟...")
    print("="*60)
    
    actual_rounds, stop_reason = runner.run(
        target_turns=50,  # 25 rounds × 2 turns/round = 50 individual turns → exactly 25 complete rounds
        max_tokens=200,
        temperature=0.8
    )
    
    # 6. 生成报告
    print(f"\n📊 生成运行报告...")
    generate_report(ts, runner.dialogue_log, actual_rounds, stop_reason)
    
    print(f"\n✅ 完成!")
    print(f"   对话记录: {LOG_FILE}")
    print(f"   运行报告: {REPORT_FILE}")


if __name__ == '__main__':
    main()
