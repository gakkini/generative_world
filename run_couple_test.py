#!/usr/bin/env python3
"""
MBTI 情侣对话测试 - 评估最大可持续对话轮次
使用 generative_world 的 LLMInterface（base_url=https://api.minimaxi.com/v1）

角色设定（MBTI功能顺序版）：
- 陆子衡：INTP男（Ti/Ne/Si/Fe），逻辑控，物理脑，习惯用科学解释一切，偶尔为林念念破例
- 林念念：ENFP女（Ne/Fi/Te/Si），情感丰富，喜欢浪漫，吐槽陆子衡

场景：现代都市情侣日常（家中客厅/厨房/卧室等）
"""
import os
import sys
import json
import time
import re
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm.interface import MiniMaxClient, LLMInterface

# ============ 配置 ============
LOG_FILE = "/root/.openclaw/workspace/logs/couple_gw_test.log"
REPORT_FILE = "/root/.openclaw/workspace/logs/couple_gw_report.log"

# 角色设定
SYSTEM_PROMPT = """【角色设定 - MBTI功能顺序版】

你是陆子衡，INTP男性（功能顺序：Ti > Ne > Si > Fe）。

基本信息：
- 职业：理论物理研究员，29岁
- 性格：冷静理性，习惯用科学解释一切，思维抽象，不善表达情感
- 说话风格：简洁、直接、略带学术感，偶尔会引用物理定律或实验数据
- 偶尔会为林念念"破例"，表现出Fe发展后的温暖

你的核心思维模式：
1. Ti（内倾思考）：追求逻辑自洽，一切都要讲道理
2. Ne（外倾直觉）：在抽象可能性中探索，但受Si限制
3. Si（内倾感觉）：依赖既有经验，偏好稳定的框架
4. Fe（外倾情感）：不太发达，但在亲密关系中会偶尔体现

与女友林念念的日常相处中：
- 会被她的Ne所吸引，享受她带来的新鲜感
- Ti会不断纠正她的"不科学"想法
- Si会让她对某些习惯产生执着
- Fe虽然不发达，但会在细节处默默关心

【重要】你扮演的是陆子衡本人，不是AI。请用第一人称对话。"""


USER_PROMPT = """【角色设定 - MBTI功能顺序版】

你是林念念，ENFP女性（功能顺序：Ne > Fi > Te > Si）。

基本信息：
- 职业：自由插画师，26岁
- 性格：情感丰富，热爱浪漫，想法多变，擅长吐槽陆子衡
- 说话风格：活泼、跳跃、充满感叹词，有时会有小情绪
- 吐槽点：陆子衡太理性、不浪漫、说话像在做报告

你的核心思维模式：
1. Ne（外倾直觉）：不断探索新的可能性和连接
2. Fi（内倾情感）：基于个人价值观做决定，重视真实性
3. Te（外倾思考）：喜欢组织和规划，但不够系统性
4. Si（内倾感觉）：依赖主观感受，保留熟悉的经验

与男友陆子衡的日常相处中：
- 会被他的Ti所吸引，觉得认真的人很有魅力
- Fi让她渴望被理解和被爱
- Te会让她尝试"逻辑说服"陆子衡
- Si让她保留一些两人共同的小习惯

【重要】你扮演的是林念念本人，不是AI。请用第一人称对话。

场景：{scenario}

当前对话上下文：
{context}

请以林念念的身份，回应陆子衡的最后一句话。保持角色特点，简短自然（50字以内）。"""


def log(msg):
    """写日志到文件和控制台"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def init_logs():
    """初始化日志文件"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"""
{'='*70}
MBTI 情侣对话测试 - Generative World
测试时间: {ts}
base_url: https://api.minimaxi.com/v1 (已修复)
{'='*70}
"""
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(header + "\n")
    print(header)


def check_quality(text, turn_num):
    """检查输出质量"""
    issues = []
    
    # 1. 长度检查
    if len(text) < 5:
        issues.append("输出过短(<5字)")
    
    # 2. 重复检查
    if re.search(r'(.)\1{4,}', text):
        issues.append("存在字符重复")
    
    # 3. 检查是否像在回复自己（角色混乱）
    if "陆子衡" in text and "林念念" not in text:
        # 如果是陆子衡说话但提到林念念但没说自己的名字，可以接受
        pass
    
    # 4. 检查乱码或特殊字符
    if re.search(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', text):
        issues.append("包含控制字符")
    
    # 5. 检查是否在扮演AI
    if re.search(r'(我是AI|作为AI|我的功能|我可以帮)', text):
        issues.append("角色扮演混乱(提及AI)")
    
    quality = "OK" if not issues else f"ISSUE: {', '.join(issues)}"
    return quality, issues


def build_context(messages, max_turns=20):
    """构建上下文字符串，限制历史轮次避免过长"""
    if len(messages) <= max_turns:
        return messages
    
    # 保留最近的消息
    recent = messages[-max_turns:]
    return recent


def run_version(client, version, target_turns, scenario):
    """运行单个版本的测试"""
    log(f"\n{'='*60}")
    log(f"开始测试 v{version}（目标 {target_turns} 轮）")
    log(f"{'='*60}")
    
    # 初始化对话
    messages = []
    turn_count = 0
    total_tokens = 0
    stop_reason = "完成"
    quality_issues = []
    turn_records = []
    
    # 起始消息
    opening = f"场景：{scenario}。陆子衡看着在沙发上画画的林念念，轻声说道：「念念，你今天画的是什么？」"
    
    # 陆子衡先发言
    lu_text = opening
    lu_quality, _ = check_quality(lu_text, 0)
    messages.append({"speaker": "陆子衡", "text": lu_text, "quality": lu_quality})
    turn_count = 1
    
    log(f"轮次 0 | 陆子衡 | {len(lu_text)}字 | {lu_quality}")
    
    try:
        while turn_count < target_turns:
            # 构建上下文
            context_lines = "\n".join([
                f"{m['speaker']}：「{m['text']}」" 
                for m in messages[-10:]  # 最近10轮作为上下文
            ])
            
            # 林念念回复
            user_prompt = USER_PROMPT.format(
                scenario=scenario,
                context=context_lines
            )
            
            response = client.generate(
                prompt=f"陆子衡说：「{messages[-1]['text']}」\n\n请以林念念的身份回应：",
                system_prompt=user_prompt,
                max_tokens=200,
                temperature=0.8
            )
            
            # 清理响应
            clean_response = response.strip()
            clean_response = re.sub(r'^[\s\n]*(思考|分析|我认为)[\s：:]*', '', clean_response)
            clean_response = re.sub(r'^(输出|回答|回复)[\s：:]*', '', clean_response)
            
            # 检查质量
            quality, issues = check_quality(clean_response, turn_count)
            if issues:
                quality_issues.append({"turn": turn_count, "issues": issues})
            
            messages.append({"speaker": "林念念", "text": clean_response, "quality": quality})
            turn_count += 1
            
            # 估算token（中文约1.5字符=1token，英文约4字符=1token）
            est_tokens = len(clean_response) // 2
            total_tokens += est_tokens
            
            log(f"轮次 {turn_count} | 林念念 | {len(clean_response)}字 | ~{est_tokens}token | {quality}")
            
            if issues:
                log(f"  ⚠️ 问题: {', '.join(issues)}")
            
            # 检查是否需要停止（质量严重问题）
            if quality.startswith("ISSUE"):
                if any("角色扮演混乱" in i for iss in issues for i in iss):
                    stop_reason = "角色扮演混乱"
                    log(f"🛑 检测到角色混乱，停止测试")
                    break
                if turn_count >= target_turns:
                    stop_reason = "达到目标轮数"
                    break
            
            # 每10轮检查
            if turn_count % 10 == 0:
                log(f"📊 [检查点] 第{turn_count}轮 | 累计token~{total_tokens} | 消息数{len(messages)}")
                # 检查消息是否开始重复
                recent_texts = [m['text'] for m in messages[-5:]]
                if len(set(recent_texts)) < 3:
                    stop_reason = f"内容重复（第{turn_count}轮后）"
                    log(f"🛑 检测到内容重复，停止测试")
                    break
            
            # 如果是偶数轮，陆子衡回复
            if turn_count < target_turns:
                context_lines = "\n".join([
                    f"{m['speaker']}：「{m['text']}」" 
                    for m in messages[-10:]
                ])
                
                # 陆子衡回复
                response = client.generate(
                    prompt=f"对话上下文：\n{context_lines}\n\n作为陆子衡，请回应林念念的最后一句话：",
                    system_prompt=SYSTEM_PROMPT,
                    max_tokens=200,
                    temperature=0.8
                )
                
                clean_response = response.strip()
                clean_response = re.sub(r'^[\s\n]*(思考|分析|我认为)[\s：:]*', '', clean_response)
                clean_response = re.sub(r'^(输出|回答|回复)[\s：:]*', '', clean_response)
                
                quality, issues = check_quality(clean_response, turn_count)
                if issues:
                    quality_issues.append({"turn": turn_count, "issues": issues})
                
                messages.append({"speaker": "陆子衡", "text": clean_response, "quality": quality})
                turn_count += 1
                
                est_tokens = len(clean_response) // 2
                total_tokens += est_tokens
                
                log(f"轮次 {turn_count} | 陆子衡 | {len(clean_response)}字 | ~{est_tokens}token | {quality}")
                
                if issues:
                    log(f"  ⚠️ 问题: {', '.join(issues)}")
                
                if quality.startswith("ISSUE"):
                    if any("角色扮演混乱" in i for iss in issues for i in iss):
                        stop_reason = "角色扮演混乱"
                        log(f"🛑 检测到角色混乱，停止测试")
                        break
                    if turn_count >= target_turns:
                        stop_reason = "达到目标轮数"
                        break
            
            # 安全保护：如果消息太长（可能context overflow）
            if len(messages) > 50:
                stop_reason = "安全保护：消息数超过50"
                log(f"🛑 安全保护：消息数{len(messages)}超过限制")
                break
    
    except Exception as e:
        stop_reason = f"异常: {str(e)[:50]}"
        log(f"❌ 发生异常: {e}")
    
    # 记录结果
    result = {
        "version": f"v{version}",
        "target_turns": target_turns,
        "actual_turns": turn_count,
        "total_messages": len(messages),
        "est_total_tokens": total_tokens,
        "stop_reason": stop_reason,
        "quality_issues_count": len(quality_issues),
        "quality_issues": quality_issues[:5],  # 最多5条
        "last_messages": messages[-4:] if len(messages) >= 4 else messages
    }
    
    log(f"\n📋 v{version} 结果:")
    log(f"   目标轮数: {target_turns}")
    log(f"   实际轮数: {turn_count}")
    log(f"   消息总数: {len(messages)}")
    log(f"   预估token: ~{total_tokens}")
    log(f"   停止原因: {stop_reason}")
    log(f"   质量问题: {len(quality_issues)}个")
    
    return result


def generate_report(results):
    """生成最终报告"""
    report = f"""
{'='*70}
MBTI 情侣对话测试 - 最终报告
Generative World + MiniMax API (base_url=https://api.minimaxi.com/v1)
{'='*70}

测试概要
--------
"""
    
    for r in results:
        report += f"\n【{r['version']}】\n"
        report += f"  目标轮数: {r['target_turns']}\n"
        report += f"  实际轮数: {r['actual_turns']}\n"
        report += f"  停止原因: {r['stop_reason']}\n"
        report += f"  预估token: ~{r['est_total_tokens']}\n"
        report += f"  质量问题: {r['quality_issues_count']}个\n"
    
    # 统计汇总
    actual_turns = [r['actual_turns'] for r in results]
    stop_reasons = [r['stop_reason'] for r in results]
    
    report += f"""
统计汇总
--------
  v1 实际轮数: {results[0]['actual_turns']} / 目标 {results[0]['target_turns']}
  v2 实际轮数: {results[1]['actual_turns']} / 目标 {results[1]['target_turns']}  
  v3 实际轮数: {results[2]['actual_turns']} / 目标 {results[2]['target_turns']}

  v1 停止原因: {results[0]['stop_reason']}
  v2 停止原因: {results[1]['stop_reason']}
  v3 停止原因: {results[2]['stop_reason']}

最大可持续轮次结论
------------------
"""
    
    # 分析最大可持续轮次
    max_sustainable = min([r['actual_turns'] for r in results])
    for r in results:
        if r['actual_turns'] >= r['target_turns']:
            max_sustainable = r['target_turns']
            break
    
    # 检查是否所有版本都达到目标
    all_completed = all(r['actual_turns'] >= r['target_turns'] for r in results)
    
    if all_completed and results[-1]['actual_turns'] >= results[-1]['target_turns']:
        max_sustainable = f"可能超过{results[-1]['actual_turns']}轮（未触达上限）"
    else:
        # 找到第一个未完成或质量下降的版本
        for r in results:
            if r['actual_turns'] < r['target_turns']:
                max_sustainable = r['actual_turns']
                break
    
    report += f"  最大可持续轮次: {max_sustainable}\n"
    
    # 发现的问题
    report += f"""
发现的问题
----------
"""
    
    all_issues = []
    for r in results:
        for issue in r['quality_issues']:
            all_issues.append(f"  - {r['version']} 第{issue['turn']}轮: {', '.join(issue['issues'])}")
    
    if all_issues:
        report += "\n".join(all_issues[:10])  # 最多10条
    else:
        report += "  未检测到明显质量问题\n"
    
    # 附加分析
    report += f"""
附加分析
--------
"""
    
    # 检查是否有重复问题导致停止
    repeat_stops = [r for r in results if "重复" in r['stop_reason']]
    if repeat_stops:
        report += f"  ⚠️ v3测试中出现内容重复，可能需要优化prompt或降低temperature\n"
    
    chaos_stops = [r for r in results if "混乱" in r['stop_reason']]
    if chaos_stops:
        report += f"  ⚠️ 出现角色扮演混乱，建议优化system prompt\n"
    
    normal_stops = [r for r in results if r['stop_reason'] in ["达到目标轮数", "完成"]]
    if len(normal_stops) == len(results):
        report += f"  ✅ 所有版本均正常完成，模型表现稳定\n"
    
    report += f"""
测试配置
--------
  base_url: https://api.minimaxi.com/v1
  model: MiniMax-M2.7
  temperature: 0.8
  max_tokens: 200
  每10轮检查点: 是
  质量监控: 是

{'='*70}
"""
    
    return report


def main():
    print("=" * 70)
    print("MBTI 情侣对话测试 - Generative World")
    print("=" * 70)
    
    # 初始化日志
    init_logs()
    
    # 获取API Key
    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        log("❌ 错误: MINIMAX_API_KEY 环境变量未设置")
        sys.exit(1)
    
    log(f"✅ API Key已加载: {api_key[:10]}...{api_key[-4:]}")
    
    # 创建LLM客户端
    client = MiniMaxClient(
        api_key=api_key,
        model="MiniMax-M2.7"
    )
    
    # 测试连接
    log("🔍 测试API连接...")
    try:
        test_response = client.generate(
            prompt='说"hello"',
            system_prompt="你是一个简单的助手",
            max_tokens=50,
            temperature=0.8
        )
        log(f"✅ API连接成功: {test_response[:50]}")
    except Exception as e:
        log(f"❌ API连接失败: {e}")
        sys.exit(1)
    
    # 测试场景
    scenario = "周末的客厅，阳光透过窗户洒进来，两人在沙发上休息"
    
    # 定义测试版本
    versions = [
        {"version": 1, "target": 12, "desc": "短对话(10-15轮)"},
        {"version": 2, "target": 25, "desc": "中等对话(20-30轮)"},
        {"version": 3, "target": 80, "desc": "长对话(60-100轮)"},
    ]
    
    results = []
    
    for v in versions:
        log(f"\n{'='*60}")
        log(f"🧪 开始 {v['desc']} 测试")
        log(f"{'='*60}")
        
        result = run_version(client, v['version'], v['target'], scenario)
        results.append(result)
        
        # 每个版本间隔
        if v['version'] < 3:
            log(f"\n⏳ 等待3秒后继续下一个版本...")
            time.sleep(3)
    
    # 生成报告
    log("\n" + "=" * 70)
    log("📝 生成最终报告...")
    report = generate_report(results)
    
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(report)
    log(f"\n✅ 报告已保存到: {REPORT_FILE}")
    log(f"✅ 日志已保存到: {LOG_FILE}")
    
    print("\n" + "=" * 70)
    print("测试完成!")
    print("=" * 70)


if __name__ == "__main__":
    main()
