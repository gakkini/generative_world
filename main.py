#!/usr/bin/env python3
"""
Generative World Simulator - 主入口
完整版 - 支持智能主角 + 简单NPC
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import World
from agents import Agent, DiaryWriter
from agents.npc import SimpleNPCAgent, create_npc_agent
from plot import PlotEngine
from llm import create_llm_client


def create_characters(config, world, llm_client=None):
    """根据角色类型创建Agent"""
    protagonists = {}
    npcs = {}
    
    for char_config in config['characters']:
        role = char_config.get('role', 'npc')
        
        if role == 'protagonist':
            # 主角：使用完整智能Agent
            agent = Agent(char_config, world)
            # 如果配置了LLM，给主角装备
            if llm_client:
                agent.planner.llm_client = llm_client
                agent.dialogue_gen.llm_client = llm_client
            protagonists[char_config['id']] = agent
            print(f"   🧠 {agent.name}（主角·智能）")
        else:
            # NPC：使用简单Agent
            npc = create_npc_agent(char_config, world)
            npcs[char_config['id']] = npc
            print(f"   📦 {npc.name}（NPC·简单）")
    
    return protagonists, npcs


def run_day(world, protagonists, npcs, plot_engine, diary_writer, day_num):
    """运行一天"""
    print(f"\n{'='*60}")
    print(f"📅 第 {day_num} 天 | {world.time.get_full_time_str()}")
    print(f"{'='*60}")
    
    # 主角行动
    for agent_id, agent in protagonists.items():
        run_agent_day(agent, world, protagonists, npcs, plot_engine, diary_writer)
    
    # NPC行动（简化）
    for npc_id, npc in npcs.items():
        run_npc_day(npc, world)
    
    # 时间推进
    world.advance_day()
    
    # 主角反思
    if world.time.day % 2 == 0:
        for agent in protagonists.values():
            agent.reflect()


def run_agent_day(agent, world, protagonists, npcs, plot_engine, diary_writer):
    """运行主角的一天"""
    print(f"\n【{agent.name}】")
    
    # 感知
    perceptions = agent.perceive()
    perception_desc = agent.get_perception_narrative()
    print(f"  👁️ 感知：{perception_desc}")

    # 互动 - 传入完整agents字典，避免状态丢失
    all_agents = {a.id: a for a in protagonists.values()} | {n.id: n for n in npcs.values()}
    interactions = agent.check_for_interactions(all_agents)
    if interactions:
        other = interactions[0]
        dialogue = agent.interact(other)
        print(f"  💬 与{other.name}对话：{dialogue.get_transcript()[:80]}...")
    
    # 规划
    actions = agent.plan()
    print(f"  📋 计划：{' | '.join([a.description for a in actions])}")
    
    # 执行
    agent.act()
    
    # 剧本检查 - 使用dict union避免键冲突
    plot_engine.check_triggers({a.id: a for a in protagonists.values()} | {n.id: n for n in npcs.values()})
    
    # 日记
    use_llm = hasattr(agent.planner, 'llm_client') and agent.planner.llm_client
    print(f"  📖 日记：")
    diary = agent.write_diary(use_llm=use_llm)
    for line in diary.split('\n')[:6]:
        print(f"     {line}")
    
    agent.clear_daily_data()


def run_npc_day(npc, world):
    """运行NPC的一天（简化版）"""
    npc.perceive()
    plans = npc.plan()
    npc.act(plans)


def main():
    print("=" * 60)
    print("🌍 Generative World Simulator - 完整版")
    print("=" * 60)
    
    # 1. 加载配置
    config_path = os.path.join(os.path.dirname(__file__), 'config/world.yaml')
    
    with open(config_path, 'r', encoding='utf-8') as f:
        import yaml
        config = yaml.safe_load(f)
    
    world = World(config_path)
    print(f"\n📍 世界：{world.name}")
    print(f"🗺️  地点数：{len(world.locations)}")
    
    # 2. LLM配置
    llm_config = config.get('llm', {})
    llm_client = None
    
    if llm_config.get('enabled', False):
        client_type = llm_config.get('client_type', 'auto')
        model = llm_config.get('model', 'MiniMax-M2.7')
        api_key = llm_config.get('api_key', '')
        
        llm_client = create_llm_client(
            client_type=client_type,
            config={'model': model, 'api_key': api_key}
        )
        
        if llm_client:
            print(f"✅ LLM已启用：{model}")
        else:
            print("⚠️ LLM未配置或无法连接")
    else:
        print("📝 LLM未启用（使用模板生成）")
    
    # 3. 创建角色
    print(f"\n👥 创建角色...")
    protagonists, npcs = create_characters(config, world, llm_client)
    print(f"   主角：{len(protagonists)}个")
    print(f"   NPC：{len(npcs)}个")
    
    # 4. 剧本引擎
    plot_engine = PlotEngine(world)
    plot_path = os.path.join(os.path.dirname(__file__), 'config/plot_example.yaml')
    if os.path.exists(plot_path):
        plot_engine.load_plot(plot_path)
        print(f"📜 剧本已加载：{len(plot_engine.nodes)}个节点")
    
    # 5. 日记生成器
    diary_writer = DiaryWriter(llm_client) if llm_client else DiaryWriter()
    
    # 6. 主循环
    print("\n" + "=" * 60)
    print("开始模拟...")
    print("=" * 60)
    
    days = 5
    for day in range(1, days + 1):
        run_day(world, protagonists, npcs, plot_engine, diary_writer, day)
    
    # 7. 完成
    print("\n" + "=" * 60)
    print("✅ 模拟完成！")
    print("=" * 60)
    
    # 统计
    if plot_engine.nodes:
        status = plot_engine.get_status()
        print(f"\n📊 剧本状态：已完成 {status['completed']}/{status['total_nodes']} 节点")
    
    print("\n📝 记忆统计：")
    for aid, agent in protagonists.items():
        mem_count = len(agent.memory.events)
        ref_count = len(agent.memory.reflections)
        print(f"   {agent.name}：{mem_count}条记忆，{ref_count}条反思")


if __name__ == '__main__':
    main()
