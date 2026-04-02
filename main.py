#!/usr/bin/env python3
"""
Generative World Simulator - 主入口
完整版 - 支持智能主角 + 简单NPC + 增强模块

增强模块：
- ReflectionEngine: 层次化反思
- RelationshipManager: 复杂关系系统
- SocialNetwork: 社交网络与信息传播
- EventBus: 跨Agent事件总线
- BehaviorSpreadEngine: 涌现行为（派对邀请扩散等）
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import World
from agents.base import Agent, create_agents, create_shared_systems
from agents.npc import SimpleNPCAgent, create_npc_agent
from agents.behavior_spread import SocialBehaviorType
from plot import PlotEngine
from llm import create_llm_client


def create_characters(config, world, shared_systems=None, llm_client=None):
    """根据角色类型创建Agent"""
    protagonists = {}
    npcs = {}
    
    # 解包共享系统
    social_network, relationship_manager, event_bus, behavior_engine = shared_systems
    
    for char_config in config['characters']:
        role = char_config.get('role', 'npc')
        
        if role == 'protagonist':
            # 主角：使用完整智能Agent + 共享系统
            agent = Agent(
                char_config, 
                world,
                social_network=social_network,
                relationship_manager=relationship_manager,
                event_bus=event_bus,
                behavior_engine=behavior_engine
            )
            # 如果配置了LLM，给主角装备
            if llm_client:
                agent.planner.llm_client = llm_client
                agent.dialogue_gen.llm_client = llm_client
            protagonists[char_config['id']] = agent
            print(f"   🧠 {agent.name}（主角·智能·增强）")
        else:
            # NPC：使用简单Agent
            npc = create_npc_agent(char_config, world)
            npcs[char_config['id']] = npc
            print(f"   📦 {npc.name}（NPC·简单）")
    
    return protagonists, npcs


def demonstrate_enhanced_features(protagonists, npcs, world, day_num):
    """演示增强功能（仅在特定天数触发）"""
    print("\n" + "="*60)
    print("🔔 增强功能演示")
    print("="*60)
    
    for agent_id, agent in protagonists.items():
        # 1. 关系系统演示
        if agent.relationship_manager:
            rels = agent.relationship_manager.get_all_relationships_for(agent_id)
            if rels:
                print(f"\n📊 {agent.name} 的关系网：")
                for rel in rels[:3]:
                    other = rel['other']
                    r = rel['relationship']
                    print(f"   - {other}: {r.affinity:.1f}（{r.stage.value}）")
        
        # 2. 反思系统演示
        if agent.reflection_engine:
            recent_refs = agent.reflection_engine.get_recent_reflections(world.time.day, days=7)
            if recent_refs:
                print(f"\n💭 {agent.name} 的反思：")
                for ref in recent_refs[-2:]:
                    print(f"   - {ref.content}")
        
        # 3. 待处理邀请演示
        pending = agent.check_pending_invitations()
        if pending:
            print(f"\n📬 {agent.name} 有 {len(pending)} 个待处理邀请：")
            for inv in pending[:2]:
                print(f"   - [{inv[0]}] 从 {inv[1]}: {inv[2][:30]}...")
    
    # 4. 社交事件演示（只在特定天数）
    if day_num == 3:
        print("\n🎉 演示：发起社交事件...")
        if protagonists:
            first_agent = list(protagonists.values())[0]
            event_id = first_agent.initiate_social_event(
                'party',
                f"第{day_num}天修仙交流会",
                target_location=first_agent.current_location
            )
            print(f"   {first_agent.name} 发起事件: {event_id}")


def run_day(world, protagonists, npcs, plot_engine, diary_writer, day_num, shared_systems):
    """运行一天"""
    print(f"\n{'='*60}")
    print(f"📅 第 {day_num} 天 | {world.time.get_full_time_str()}")
    print(f"{'='*60}")
    
    # 解包共享系统用于事件处理
    social_network, relationship_manager, event_bus, behavior_engine = shared_systems
    
    # ===== 事件总线处理 =====
    # 处理待传播的事件
    all_agents = {a.id: a for a in protagonists.values()} | {n.id: n for n in npcs.values()}
    event_bus.process_events(world.time.day, all_agents)
    
    # ===== 行为传播引擎处理 =====
    behavior_engine.simulate_day(world.time.day, all_agents)
    
    # 主角行动
    for agent_id, agent in protagonists.items():
        run_agent_day(agent, world, protagonists, npcs, plot_engine, diary_writer)
    
    # NPC行动（简化）
    for npc_id, npc in npcs.items():
        run_npc_day(npc, world)
    
    # ===== 每日关系衰减 =====
    relationship_manager.apply_daily_decay(world.time.day)
    
    # 时间推进
    world.advance_day()
    
    # 主角反思（每隔一天）
    if world.time.day % 2 == 0:
        for agent in protagonists.values():
            agent.reflect()
    
    # ===== 演示增强功能 =====
    if day_num in [2, 3, 4]:
        demonstrate_enhanced_features(protagonists, npcs, world, day_num)


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
    print("🌍 Generative World Simulator - 增强版")
    print("=" * 60)
    print("\n✨ 新增功能：")
    print("  - ReflectionEngine: 层次化反思")
    print("  - RelationshipManager: 复杂关系建模")
    print("  - SocialNetwork: 社交网络传播")
    print("  - EventBus: 跨Agent事件总线")
    print("  - BehaviorSpreadEngine: 涌现行为")
    
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
    
    # 3. 创建共享系统
    print(f"\n🔧 初始化增强系统...")
    shared_systems = create_shared_systems()
    social_network, relationship_manager, event_bus, behavior_engine = shared_systems
    print("   ✅ SocialNetwork 已初始化")
    print("   ✅ RelationshipManager 已初始化")
    print("   ✅ EventBus 已初始化")
    print("   ✅ BehaviorSpreadEngine 已初始化")
    
    # 4. 创建角色
    print(f"\n👥 创建角色...")
    protagonists, npcs = create_characters(config, world, shared_systems, llm_client)
    print(f"   主角：{len(protagonists)}个")
    print(f"   NPC：{len(npcs)}个")
    
    # 5. 剧本引擎
    plot_engine = PlotEngine(world)
    plot_path = os.path.join(os.path.dirname(__file__), 'config/plot_example.yaml')
    if os.path.exists(plot_path):
        plot_engine.load_plot(plot_path)
        print(f"📜 剧本已加载：{len(plot_engine.nodes)}个节点")
    
    # 6. 日记生成器
    from agents.diary import DiaryWriter
    diary_writer = DiaryWriter(llm_client) if llm_client else DiaryWriter()
    
    # 7. 主循环
    print("\n" + "=" * 60)
    print("开始模拟...")
    print("=" * 60)
    
    days = 3
    for day in range(1, days + 1):
        run_day(world, protagonists, npcs, plot_engine, diary_writer, day, shared_systems)
    
    # 8. 完成
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
    
    print("\n🤝 关系统计：")
    for aid, agent in protagonists.items():
        rels = agent.relationship_manager.get_all_relationships_for(agent.id)
        if rels:
            print(f"   {agent.name}：{len(rels)}段关系")
    
    print("\n🎭 活跃社交事件：")
    active_events = behavior_engine.get_active_events()
    if active_events:
        for evt in active_events[:3]:
            print(f"   - {evt.behavior_type.value}: {evt.content[:40]}...")
            print(f"     邀请了 {len(evt.invitees)} 人，{len(evt.confirmed)} 人确认")
    else:
        print("   暂无活跃事件")


if __name__ == '__main__':
    main()
