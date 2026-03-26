#!/usr/bin/env python3
"""
Generative World Simulator - 主入口
完整版 - 集成所有模块
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import World
from agents import (
    Agent, create_agents, DiaryWriter, 
    PerceptionSystem, PlanGenerator, DialogueGenerator
)
from plot import PlotEngine


def main():
    print("=" * 60)
    print("🌍 Generative World Simulator - 完整版")
    print("=" * 60)
    
    # 1. 加载世界配置
    config_path = os.path.join(
        os.path.dirname(__file__),
        'config/world.yaml'
    )
    world = World(config_path)
    print(f"\n📍 世界：{world.name}")
    print(f"🗺️  地点数：{len(world.locations)}")
    
    # 2. 创建角色
    with open(config_path, 'r', encoding='utf-8') as f:
        import yaml
        config = yaml.safe_load(f)
    
    agents = create_agents(config, world)
    print(f"👥 主角数：{len(agents)}")
    
    for aid, agent in agents.items():
        print(f"   - {agent.name}（{agent.sect}·{agent.cultivation}）")
    
    # 3. 初始化日记生成器
    diary_writer = DiaryWriter()
    
    # 4. 初始化剧本引擎
    plot_engine = PlotEngine(world)
    plot_path = os.path.join(
        os.path.dirname(__file__),
        'config/plot_example.yaml'
    )
    if os.path.exists(plot_path):
        plot_engine.load_plot(plot_path)
        print(f"📜 剧本已加载：{len(plot_engine.nodes)}个节点")
    
    print("\n" + "=" * 60)
    print("开始模拟...")
    print("=" * 60)
    
    # 5. 主循环：模拟5天
    for day in range(1, 6):
        print(f"\n{'='*60}")
        print(f"📅 第 {day} 天 | {world.time.get_full_time_str()}")
        print(f"{'='*60}")
        
        # 每个角色执行行为
        for agent_id, agent in agents.items():
            print(f"\n【{agent.name}】")
            
            # === 感知阶段 ===
            perceptions = agent.perceive()
            perception_desc = agent.get_perception_narrative()
            print(f"  👁️ 感知：{perception_desc}")
            
            # === 互动阶段 ===
            interactions = agent.check_for_interactions()
            if interactions:
                print(f"  💬 遇到同处一地的角色：{[a.name for a in interactions]}")
                for other in interactions[:1]:  # 最多互动1个
                    dialogue = agent.interact(other)
                    print(f"     对话记录：{dialogue.get_transcript()[:100]}...")
            
            # === 规划阶段 ===
            actions = agent.plan()
            print(f"  📋 计划：{' | '.join([a.description for a in actions])}")
            
            # === 执行阶段 ===
            results = agent.act()
            for result in results:
                print(f"     → {result}")
            
            # === 剧本检查 ===
            plot_engine.check_triggers(agents)
            
            # === 写日记 ===
            print(f"  📖 日记：")
            diary = diary_writer.generate(agent, use_llm=False)
            for line in diary.split('\n')[:8]:  # 限制输出行数
                print(f"     {line}")
            
            # === 清空每日数据 ===
            agent.clear_daily_data()
        
        # === 时间推进 ===
        world.advance_day()
        
        # === 角色反思 ===
        for agent in agents.values():
            if world.time.day % 2 == 0:
                agent.reflect()
    
    print("\n" + "=" * 60)
    print("✅ 模拟完成！")
    print("=" * 60)
    
    # 打印剧本状态
    if plot_engine.nodes:
        status = plot_engine.get_status()
        print(f"\n📊 剧本状态：已完成 {status['completed']}/{status['total_nodes']} 节点")
    
    # 打印记忆统计
    print("\n📝 记忆统计：")
    for aid, agent in agents.items():
        print(f"   {agent.name}：{len(agent.memory.events)}条记忆，{len(agent.memory.reflections)}条反思")


if __name__ == '__main__':
    main()
