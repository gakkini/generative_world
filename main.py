#!/usr/bin/env python3
"""
Generative World Simulator - 主入口 (Paper Architecture)

按照Stanford Generative Agents论文架构重构：
- Persona Agent 替代原来的 agents.base.Agent
- 保留所有增强模块: RelationshipManager, SocialNetwork, EventBus, BehaviorSpreadEngine
- 剔除可视化部分

核心模块:
- persona/persona.py: Agent主类
- persona/cognitive_modules/: 认知模块
  - perceive.py: 感知
  - retrieve.py: 关联记忆检索 (核心!)
  - plan.py: 规划
  - execute.py: 执行
  - converse.py: 对话
  - reflect.py: 反思
- persona/memory_structures/: 记忆结构
  - associative_memory.py: 记忆流 (核心!)
  - scratch.py: 工作记忆
  - spatial_memory.py: 空间记忆
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import World
from llm import create_llm_client

# 尝试导入新架构
try:
    from persona import Persona
    NEW_ARCHITECTURE = True
except ImportError:
    NEW_ARCHITECTURE = False
    Persona = None

# 保留旧的Agent导入作为fallback
try:
    from agents.base import Agent, create_agents, create_shared_systems
    OLD_ARCHITECTURE = True
except ImportError:
    OLD_ARCHITECTURE = False


def create_characters_new(config, world, shared_systems=None, llm_client=None):
    """
    新架构：创建Persona Agent

    使用新的paper-accurate架构
    """
    protagonists = {}

    social_network, relationship_manager, event_bus, behavior_engine = shared_systems

    for char_config in config['characters']:
        role = char_config.get('role', 'npc')

        if role == 'protagonist':
            agent = Persona(
                config=char_config,
                world=world,
                llm_client=llm_client,
                social_network=social_network,
                relationship_manager=relationship_manager,
                event_bus=event_bus,
                behavior_engine=behavior_engine
            )
            protagonists[char_config['id']] = agent
            print(f"   🧠 {agent.name}（Persona·智能）")

    return protagonists


def create_characters_old(config, world, shared_systems=None, llm_client=None):
    """
    旧架构：创建传统Agent
    """
    protagonists, npcs = {}, {}

    social_network, relationship_manager, event_bus, behavior_engine = shared_systems

    for char_config in config['characters']:
        role = char_config.get('role', 'npc')

        if role == 'protagonist':
            agent = Agent(
                char_config,
                world,
                social_network=social_network,
                relationship_manager=relationship_manager,
                event_bus=event_bus,
                behavior_engine=behavior_engine
            )
            if llm_client:
                agent.planner.llm_client = llm_client
                agent.dialogue_gen.llm_client = llm_client
            protagonists[char_config['id']] = agent
            print(f"   🧠 {agent.name}（Agent·增强）")
        else:
            from agents.npc import create_npc_agent
            npc = create_npc_agent(char_config, world)
            npcs[char_config['id']] = npc
            print(f"   📦 {npc.name}（NPC·简单）")

    return protagonists, npcs


def run_agent_day_new(agent, world, all_agents):
    """新架构：运行主角的一天"""
    print(f"\n【{agent.name}】")

    # 主循环 tick
    result = agent.tick(all_agents)

    # 输出结果
    perception_desc = " | ".join(result['perceptions'][:3]) if result['perceptions'] else "无特殊感知"
    print(f"  👁️ 感知：{perception_desc}")
    print(f"  📋 计划：{result['plan_summary'] or '无计划'}")

    if result['dialogues']:
        print(f"  💬 对话：{result['dialogues'][0]}")

    for action in result['actions']:
        print(f"  🎬 行动：{action}")

    # 生成日记
    print(f"  📖 日记：")
    diary = agent.write_diary()
    for line in diary.split('\n')[:6]:
        print(f"     {line}")

    if result.get('reflection'):
        print(f"  💭 反思：{result['reflection'][:50]}...")


def run_agent_day_old(agent, world, protagonists, npcs, plot_engine):
    """旧架构：运行主角的一天"""
    print(f"\n【{agent.name}】")

    # 感知
    perceptions = agent.perceive()
    perception_desc = agent.get_perception_narrative()
    print(f"  👁️ 感知：{perception_desc}")

    # 互动
    all_agents_dict = {a.id: a for a in protagonists.values()} | {n.id: n for n in npcs.values()}
    interactions = agent.check_for_interactions(all_agents_dict)
    if interactions:
        other = interactions[0]
        dialogue = agent.interact(other)
        print(f"  💬 与{other.name}对话：{dialogue.get_transcript()[:80]}...")

    # 规划
    actions = agent.plan()
    print(f"  📋 计划：{' | '.join([a.description for a in actions])}")

    # 执行
    agent.act()

    # 日记
    use_llm = hasattr(agent.planner, 'llm_client') and agent.planner.llm_client
    print(f"  📖 日记：")
    diary = agent.write_diary(use_llm=use_llm)
    for line in diary.split('\n')[:6]:
        print(f"     {line}")

    agent.clear_daily_data()


def demonstrate_features(protagonists, world, day_num):
    """演示增强功能"""
    print("\n" + "=" * 60)
    print("🔔 增强功能演示")
    print("=" * 60)

    for agent_id, agent in protagonists.items():
        # 关系
        if hasattr(agent, 'relationship_manager') and agent.relationship_manager:
            rels = agent.relationship_manager.get_all_relationships_for(agent_id)
            if rels:
                print(f"\n📊 {agent.name} 的关系网：")
                for rel in rels[:3]:
                    other = rel['other']
                    r = rel['relationship']
                    print(f"   - {other}: {r.affinity:.1f}（{r.stage.value}）")

        # 反思
        if hasattr(agent, 'reflection_engine') and agent.reflection_engine:
            recent_refs = agent.reflection_engine.get_recent_reflections(world.time.day, days=7)
            if recent_refs:
                print(f"\n💭 {agent.name} 的反思：")
                for ref in recent_refs[-2:]:
                    print(f"   - {ref.content}")

        # 记忆检索演示
        if hasattr(agent, 'retriever'):
            print(f"\n🔍 {agent.name} 的关联记忆检索演示：")
            retrieval = agent.retriever.retrieve_for_planning(
                current_day=world.time.day,
                location=agent.spatial.current_location if hasattr(agent, 'spatial') else None,
                nearby_agents=[]
            )
            context_preview = retrieval.get('combined_context', '')[:100]
            print(f"   检索上下文: {context_preview}...")


def run_day_new(world, protagonists, shared_systems, day_num):
    """新架构：运行一天"""
    print(f"\n{'=' * 60}")
    print(f"📅 第 {day_num} 天 | {world.time.get_full_time_str()}")
    print(f"{'=' * 60}")

    social_network, relationship_manager, event_bus, behavior_engine = shared_systems

    # 行为引擎模拟
    all_agents = {a.id: a for a in protagonists.values()}
    behavior_engine.simulate_day(world.time.day, all_agents)

    # 运行每个主角
    for agent_id, agent in protagonists.items():
        all_agents = {a.id: a for a in protagonists.values()}
        run_agent_day_new(agent, world, all_agents)

    # 每日关系衰减
    relationship_manager.apply_daily_decay(world.time.day)

    # 推进时间
    world.advance_day()

    # 演示
    if day_num in [2, 3, 4]:
        demonstrate_features(protagonists, world, day_num)


def run_day_old(world, protagonists, npcs, plot_engine, shared_systems, day_num):
    """旧架构：运行一天"""
    print(f"\n{'=' * 60}")
    print(f"📅 第 {day_num} 天 | {world.time.get_full_time_str()}")
    print(f"{'=' * 60}")

    social_network, relationship_manager, event_bus, behavior_engine = shared_systems

    # 事件处理
    all_agents = {a.id: a for a in protagonists.values()} | {n.id: n for n in npcs.values()}
    event_bus.process_events(world.time.day, all_agents)
    behavior_engine.simulate_day(world.time.day, all_agents)

    # 主角
    for agent_id, agent in protagonists.items():
        run_agent_day_old(agent, world, protagonists, npcs, plot_engine)

    # NPC
    for npc_id, npc in npcs.items():
        npc.perceive()
        plans = npc.plan()
        npc.act(plans)

    # 衰减
    relationship_manager.apply_daily_decay(world.time.day)
    world.advance_day()

    # 反思
    if world.time.day % 2 == 0:
        for agent in protagonists.values():
            agent.reflect()

    # 演示
    if day_num in [2, 3, 4]:
        demonstrate_features(protagonists, world, day_num)


def main():
    print("=" * 60)
    print("🌍 Generative World Simulator - Paper Architecture")
    print("=" * 60)

    if NEW_ARCHITECTURE:
        print("\n✨ 使用Stanford Generative Agents论文架构：")
        print("  - Persona Agent（整合记忆流、感知、规划、执行、反思）")
        print("  - 关联记忆检索（importance × recency × relevance）")
        print("  - 空间记忆（位置导航）")
        print("  - 保留增强模块（RelationshipManager, SocialNetwork, EventBus, BehaviorSpread）")
    else:
        print("\n⚠️ 新架构不可用，使用传统Agent")

    # 加载配置
    config_path = os.path.join(os.path.dirname(__file__), 'config/world.yaml')

    # 优先使用 couple_world.yaml
    couple_config_path = os.path.join(os.path.dirname(__file__), 'config/couple_world.yaml')
    if os.path.exists(couple_config_path):
        config_path = couple_config_path
        print(f"📁 使用配置: couple_world.yaml (MBTI情侣·现代都市)")

    with open(config_path, 'r', encoding='utf-8') as f:
        import yaml
        config = yaml.safe_load(f)

    world = World(config_path)
    print(f"\n📍 世界：{world.name}")
    print(f"🗺️  地点数：{len(world.locations)}")
    print(f"🎭 世界类型：{world.type}")

    # LLM配置
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

    # 创建共享系统
    print(f"\n🔧 初始化增强系统...")
    shared_systems = create_shared_systems()
    social_network, relationship_manager, event_bus, behavior_engine = shared_systems
    print("   ✅ SocialNetwork")
    print("   ✅ RelationshipManager")
    print("   ✅ EventBus")
    print("   ✅ BehaviorSpreadEngine")

    # 创建角色
    print(f"\n👥 创建角色...")

    if NEW_ARCHITECTURE:
        protagonists = create_characters_new(config, world, shared_systems, llm_client)
        npcs = {}
    else:
        protagonists, npcs = create_characters_old(config, world, shared_systems, llm_client)

    print(f"   主角：{len(protagonists)}个")

    # 剧本引擎（仅旧架构使用）
    plot_engine = None
    if OLD_ARCHITECTURE:
        from plot import PlotEngine
        plot_engine = PlotEngine(world)
        plot_path = os.path.join(os.path.dirname(__file__), 'config/plot_example.yaml')
        if os.path.exists(plot_path):
            plot_engine.load_plot(plot_path)
            print(f"📜 剧本已加载")

    # 主循环
    print("\n" + "=" * 60)
    print("开始模拟...")
    print("=" * 60)

    days = 3
    for day in range(1, days + 1):
        if NEW_ARCHITECTURE:
            run_day_new(world, protagonists, shared_systems, day)
        else:
            run_day_old(world, protagonists, npcs, plot_engine, shared_systems, day)

    # 完成
    print("\n" + "=" * 60)
    print("✅ 模拟完成！")
    print("=" * 60)

    # 统计
    print("\n📝 记忆统计：")
    for aid, agent in protagonists.items():
        mem_count = len(agent.memory.events)
        ref_count = len(agent.memory.reflections)
        print(f"   {agent.name}：{mem_count}条记忆，{ref_count}条反思")

    # 关系统计
    if hasattr(list(protagonists.values())[0], 'relationship_manager'):
        print("\n🤝 关系统计：")
        for aid, agent in protagonists.items():
            rels = agent.relationship_manager.get_all_relationships_for(agent.id)
            if rels:
                print(f"   {agent.name}：{len(rels)}段关系")

    # 社交事件统计
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
