#!/usr/bin/env python3
"""
Generative World Simulator - 带进度汇报的运行脚本
每7分钟汇报一次进度，完成后写入完整日志
"""
import os
import sys
import time
import json
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

LOG_FILE = "/root/.openclaw/workspace/logs/generative_world_run.log"
LAST_PROGRESS_FILE = "/root/.openclaw/workspace/logs/generative_world_progress.json"
PROGRESS_INTERVAL = 420  # 7分钟 = 420秒


def log(msg):
    """写入日志"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def save_progress(data):
    """保存进度状态"""
    with open(LAST_PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_progress():
    """加载进度状态"""
    if os.path.exists(LAST_PROGRESS_FILE):
        with open(LAST_PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"started": False, "current_day": 0, "phase": "init"}


def run_simulation_with_progress():
    """运行模拟，每7分钟汇报一次进度"""
    from core import World
    from agents.base import create_agents, create_shared_systems
    from agents.npc import create_npc_agent
    from agents.behavior_spread import SocialBehaviorType
    from plot import PlotEngine
    from agents.diary import DiaryWriter
    from llm import create_llm_client
    import yaml

    # 初始化日志
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    log("=" * 60)
    log("🚀 Generative World 模拟任务启动")
    log("=" * 60)

    # 加载配置
    config_path = os.path.join(os.path.dirname(__file__), 'config/world.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    world = World(config_path)

    # LLM配置
    llm_config = config.get('llm', {})
    llm_client = None
    if llm_config.get('enabled', False):
        llm_client = create_llm_client(
            client_type=llm_config.get('client_type', 'auto'),
            config={
                'model': llm_config.get('model', 'MiniMax-M2.7'),
                'api_key': llm_config.get('api_key', '')
            }
        )
        if llm_client:
            log(f"✅ LLM已连接：{llm_config.get('model', 'MiniMax-M2.7')}")
        else:
            log("⚠️ LLM连接失败")
    else:
        log("⚠️ LLM未启用（主角强制需要LLM）")
        save_progress({"error": "LLM not enabled", "phase": "init"})
        return

    if not llm_client:
        save_progress({"error": "No LLM client", "phase": "init"})
        return

    # 创建共享系统
    shared_systems = create_shared_systems()
    social_network, relationship_manager, event_bus, behavior_engine = shared_systems

    # 创建角色
    protagonists, npcs = {}, {}
    for char_config in config['characters']:
        role = char_config.get('role', 'npc')
        if role == 'protagonist':
            from agents.base import Agent
            agent = Agent(
                char_config, world,
                social_network=social_network,
                relationship_manager=relationship_manager,
                event_bus=event_bus,
                behavior_engine=behavior_engine
            )
            agent.planner.llm_client = llm_client
            agent.dialogue_gen.llm_client = llm_client
            protagonists[char_config['id']] = agent
            log(f"   🧠 {agent.name}（主角·LLM）")
        else:
            npc = create_npc_agent(char_config, world)
            npcs[char_config['id']] = npc
            log(f"   📦 {npc.name}（NPC）")

    log(f"✅ 角色创建完成：{len(protagonists)}主角 + {len(npcs)}NPC")

    # 剧本引擎
    plot_engine = PlotEngine(world)
    plot_path = os.path.join(os.path.dirname(__file__), 'config/plot_example.yaml')
    if os.path.exists(plot_path):
        plot_engine.load_plot(plot_path)

    # 日记器
    diary_writer = DiaryWriter(llm_client)

    total_days = config.get('simulation', {}).get('days', 5)
    log(f"📅 开始模拟：共 {total_days} 天")
    log(f"⏰ 进度汇报间隔：{PROGRESS_INTERVAL // 60} 分钟")

    save_progress({
        "started": True,
        "total_days": total_days,
        "current_day": 0,
        "phase": "running",
        "last_report": time.time()
    })

    all_agents = {a.id: a for a in protagonists.values()} | {n.id: n for n in npcs.values()}
    start_time = time.time()

    for day in range(1, total_days + 1):
        phase = f"Day {day}/{total_days}"
        log(f"\n{'=' * 40}")
        log(f"📅 第 {day} 天 | {world.time.get_full_time_str()}")
        log(f"{'=' * 40}")

        phase_start = time.time()

        # 事件总线
        event_bus.process_events(world.time.day, all_agents)
        behavior_engine.simulate_day(world.time.day, all_agents)

        # 主角行动
        for agent_id, agent in protagonists.items():
            try:
                log(f"\n【{agent.name}】")
                t0 = time.time()

                # 感知
                perceptions = agent.perceive()
                perception_desc = agent.get_perception_narrative()
                log(f"  👁️ 感知：{perception_desc[:80]}")

                # 互动
                interactions = agent.check_for_interactions(all_agents)
                if interactions:
                    other = interactions[0]
                    dialogue = agent.interact(other)
                    log(f"  💬 与{other.name}：{dialogue.get_summary()[:60]}")

                # 规划（强制LLM）
                try:
                    actions = agent.plan()
                    action_str = ' | '.join([a.description[:30] for a in actions])
                    log(f"  📋 计划：{action_str}")
                except RuntimeError as e:
                    log(f"  ❌ 规划失败：{e}")
                    raise

                # 执行
                agent.act()

                # 剧本
                plot_engine.check_triggers(all_agents)

                # 日记
                try:
                    diary = agent.write_diary()
                    log(f"  📖 日记已生成（{len(diary)}字）")
                except RuntimeError as e:
                    log(f"  ❌ 日记失败：{e}")

                # 清理
                agent.clear_daily_data()

                elapsed = time.time() - t0
                log(f"  ⏱️ {agent.name}完成（{elapsed:.1f}秒）")

            except Exception as e:
                log(f"  ❌ {agent.name}执行出错：{e}")
                import traceback
                log(f"     {traceback.format_exc()[:200]}")

        # NPC
        for npc_id, npc in npcs.items():
            npc.perceive()
            plans = npc.plan()
            npc.act(plans)

        # 关系衰减
        relationship_manager.apply_daily_decay(world.time.day)

        # 推进时间
        world.advance_day()

        # 反思（每隔一天）
        if world.time.day % 2 == 0:
            for agent in protagonists.values():
                try:
                    agent.reflect()
                except Exception as e:
                    log(f"  ⚠️ {agent.name}反思失败：{e}")

        # 更新进度
        elapsed_total = time.time() - start_time
        progress = {
            "started": True,
            "total_days": total_days,
            "current_day": day,
            "phase": f"已完成 {day}/{total_days} 天",
            "elapsed_seconds": round(elapsed_total),
            "elapsed_minutes": round(elapsed_total / 60, 1),
            "last_report": time.time(),
            "phase": phase
        }
        save_progress(progress)

        log(f"\n📊 进度汇报（{day}/{total_days}天，{elapsed_total/60:.1f}分钟）")

        # 增强功能演示
        if day in [2, 3, 4]:
            _demonstrate_enhanced(protagonists, world, day)

        # 检查是否到了汇报时间
        time_since_report = time.time() - progress["last_report"]
        if time_since_report >= PROGRESS_INTERVAL:
            log(f"\n⏰ 【进度汇报】已完成 {day}/{total_days} 天，"
                f"耗时 {elapsed_total/60:.1f} 分钟")
            save_progress({**progress, "last_report": time.time()})

    # ===== 模拟完成 =====
    total_time = time.time() - start_time
    log(f"\n{'=' * 60}")
    log(f"✅ 模拟完成！总耗时：{total_time/60:.1f} 分钟")
    log(f"{'=' * 60}")

    # 最终统计
    log("\n📝 记忆统计：")
    for aid, agent in protagonists.items():
        mem_count = len(agent.memory.events)
        ref_count = len(agent.memory.reflections)
        log(f"   {agent.name}：{mem_count}条记忆，{ref_count}条反思")

    log("\n🤝 关系统计：")
    for aid, agent in protagonists.items():
        rels = agent.relationship_manager.get_all_relationships_for(agent.id)
        if rels:
            log(f"   {agent.name}：{len(rels)}段关系")

    log("\n🎭 活跃社交事件：")
    active_events = behavior_engine.get_active_events()
    if active_events:
        for evt in active_events[:3]:
            log(f"   - {evt.behavior_type.value}: {evt.content[:40]}...")
            log(f"     邀请了 {len(evt.invitees)} 人，{len(evt.confirmed)} 人确认")
    else:
        log("   暂无活跃事件")

    # 剧本状态
    if plot_engine.nodes:
        status = plot_engine.get_status()
        log(f"\n📜 剧本状态：已完成 {status['completed']}/{status['total_nodes']} 节点")

    # 最终进度
    final_progress = {
        "started": True,
        "total_days": total_days,
        "current_day": total_days,
        "phase": "completed",
        "total_time_minutes": round(total_time / 60, 1),
        "completed_at": time.time()
    }
    save_progress(final_progress)
    log("\n🏁 任务完成！")


def _demonstrate_enhanced(protagonists, world, day_num):
    """演示增强功能"""
    for agent_id, agent in protagonists.items():
        if agent.relationship_manager:
            rels = agent.relationship_manager.get_all_relationships_for(agent_id)
            if rels:
                log(f"\n📊 {agent.name} 的关系网（Top3）：")
                for rel in rels[:3]:
                    r = rel['relationship']
                    log(f"   - {rel['other']}: {r.affinity:.1f}（{r.stage.value}）")

        if agent.reflection_engine:
            recent_refs = agent.reflection_engine.get_recent_reflections(world.time.day, days=7)
            if recent_refs:
                log(f"\n💭 {agent.name} 的反思：")
                for ref in recent_refs[-2:]:
                    log(f"   - {ref.content[:60]}")


if __name__ == '__main__':
    try:
        run_simulation_with_progress()
    except Exception as e:
        import traceback
        log(f"\n❌ 模拟任务崩溃：{e}")
        log(traceback.format_exc())
        save_progress({"error": str(e), "phase": "crashed"})
        sys.exit(1)
