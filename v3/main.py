#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微型文明演化沙盒 — 规则实验版

不是选"动机"，而是设计"行动规则"——
定义奇点怎么走、怎么采、怎么反应、怎么记忆。
放在世界里，观察它是否能征服。

用法:
  python main.py                     # 规则构建器 → GUI
  python main.py batch [次数]        # 批量测试
  python main.py eval                # 评估报告
  python main.py preset [名称]       # 直接跑预设
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

from engine import SimEngine
from architectures.rule_system import RuleBuilder, MOVE_RULES, PICKUP_RULES, REACTION_RULES, MEMORY_RULES
from reports.evaluation import evaluate_architectures, format_evaluation_report

# 注册所有预设
PRESETS = ["纯随机", "直线征服", "螺旋探索", "逃逸者", "领土扫描",
           "边界领主", "资源猎人", "壁虎", "幽灵", "暴君"]
for name in PRESETS:
    arch = RuleBuilder.get_preset(name)
    if arch:
        SimEngine.ARCHITECTURES[name] = lambda a=arch: a

HEADER = """
+=====================================================+
|  微型文明演化沙盒 — 规则实验版                        |
|                                                      |
|  设计奇点的行动规则 → 观察它能否统治世界              |
|                                                      |
|  森谷智创 . SenGu Intelligence                       |
+=====================================================+
"""


def show_rule_builder():
    """规则构建器"""
    print(HEADER)
    print("\n  [1] 使用预设行为")
    print("  [2] 自定义组合规则")
    choice = input("\n  选择 (1/2): ").strip()

    if choice == "1":
        return _select_preset()
    else:
        return _custom_rules()


def _select_preset():
    """选预设"""
    print("\n  可用预设:")
    for i, name in enumerate(PRESETS, 1):
        arch = RuleBuilder.get_preset(name)
        desc = arch.description if arch else ""
        print(f"    [{i}] {name}  — {desc}")
    print(f"\n  理论组合数: {RuleBuilder.total_combinations()} 种")

    while True:
        try:
            c = input(f"\n  选择 (1-{len(PRESETS)}, q退出): ").strip()
            if c.lower() in ("q", "quit"): return None
            idx = int(c) - 1
            if 0 <= idx < len(PRESETS):
                return PRESETS[idx]
        except (ValueError, EOFError, KeyboardInterrupt):
            return PRESETS[0]


def _custom_rules():
    """自定义规则组合"""
    print("\n  [自定义规则] 组合奇点的行动模式")
    print("  ─────────────────────────────────────")

    # 移动规则 (核心)
    print("\n  ◆ 移动规则 — 奇点怎么走？")
    move_keys = list(MOVE_RULES.keys())
    for i, k in enumerate(move_keys, 1):
        print(f"    [{i:2d}] {MOVE_RULES[k][0]:8s} — {MOVE_RULES[k][2]}")

    move_key = _pick_one(move_keys, "移动规则", 0)

    # 辅移动规则 (可选)
    has_sec = input("\n  添加辅移动规则？（偶尔切换，y/n）: ").strip().lower() == "y"
    sec_key = None
    if has_sec:
        sec_key = _pick_one(move_keys, "辅移动规则", None)

    # 拾取规则
    print("\n  ◆ 拾取规则 — 遇到资源怎么办？")
    pickup_keys = list(PICKUP_RULES.keys())
    for i, k in enumerate(pickup_keys, 1):
        print(f"    [{i}] {PICKUP_RULES[k][0]:8s} — {PICKUP_RULES[k][2]}")
    pickup_key = _pick_one(pickup_keys, "拾取规则", 0)

    # 反应规则
    print("\n  ◆ 反应规则 — 撞墙/遇灾怎么反应？")
    react_keys = list(REACTION_RULES.keys())
    for i, k in enumerate(react_keys, 1):
        print(f"    [{i}] {REACTION_RULES[k][0]:8s} — {REACTION_RULES[k][2]}")
    reaction_key = _pick_one(react_keys, "反应规则", 0)

    # 记忆规则
    print("\n  ◆ 记忆规则 — 记住什么？")
    mem_keys = list(MEMORY_RULES.keys())
    for i, k in enumerate(mem_keys, 1):
        print(f"    [{i}] {MEMORY_RULES[k][0]:8s} — {MEMORY_RULES[k][2]}")
    memory_key = _pick_one(mem_keys, "记忆规则", 0)

    # 命名
    name_parts = [
        MOVE_RULES[move_key][0],
        PICKUP_RULES[pickup_key][0],
    ]
    default_name = "-".join(name_parts)
    name = input(f"\n  架构名称 (回车={default_name}): ").strip() or default_name

    # 注册
    arch = RuleBuilder.build(name, move_key, pickup_key, reaction_key, memory_key, sec_key)
    SimEngine.ARCHITECTURES[name] = lambda a=arch: a

    print(f"\n  [完成] {name}")
    print(f"  规则: 走={MOVE_RULES[move_key][0]} | 采={PICKUP_RULES[pickup_key][0]} | "
          f"应={REACTION_RULES[reaction_key][0]} | 记={MEMORY_RULES[memory_key][0]}")
    sec_text = f" + {MOVE_RULES[sec_key][0]}" if sec_key else ""
    print(f"  辅规则:{sec_text}")
    return name


def _pick_one(keys, label, default_idx):
    """从列表选一项"""
    while True:
        try:
            c = input(f"  选择{label} (1-{len(keys)}, 回车=默认): ").strip()
            if not c and default_idx is not None:
                return keys[default_idx]
            if not c:
                return keys[0]
            idx = int(c) - 1
            if 0 <= idx < len(keys):
                return keys[idx]
        except (ValueError, EOFError):
            return keys[default_idx or 0]
        except KeyboardInterrupt:
            sys.exit(0)


# ============ 运作模式 ============
def run_interactive(arch_name=None):
    if arch_name is None:
        arch_name = show_rule_builder()
        if not arch_name:
            return

    print(f"\n  [启动] {arch_name}")
    print(f"  [世界] 60x60 | 每步染色 | 天灾随机")
    print(f"  窗口打开中...")

    engine = SimEngine(world_size=60, max_cycles=10000)
    engine.init_run(arch_name, extra_npcs=3)
    pc = engine.population.pc_singularity

    from ui.main_window import EmergenceUI
    ui = EmergenceUI(engine, world_size=60)
    ui.render_frame()
    ui.log_event(f"[启动] {arch_name}")
    ui.log_event(f"[世界] 60x60, {engine.world.total_resources}初始资源, PC#{pc._npc_id}")
    ui.log_event(f"[机制] 每步染色 → 重复走变深 → 天灾改变足迹")
    ui.run()

    print(f"\n  [结束] 周期:{pc.cycle} | 能量:{pc.energy:.3f}")


def run_batch(n=5, specific=None):
    arch_list = [specific] if specific else SimEngine.get_architecture_names()
    print(f"\n  [批量] {len(arch_list)}个架构 × {n}次")
    print("=" * 55)

    for arch_name in arch_list:
        print(f"\n  [{arch_name}]")
        for i in range(n):
            engine = SimEngine(world_size=60, max_cycles=5000)
            engine.init_run(arch_name, extra_npcs=3)
            while engine.is_running:
                engine.step()
            pc = engine.population.pc_singularity
            claimed = engine.world.get_claimed_count("pc") if engine.world else 0
            total_visits = sum(c.visit_count for row in engine.world.grid
                               for c in row) if engine.world else 0
            print(f"    [{i+1:2d}] 周期:{pc.cycle:4d} | {'存活' if pc.alive else '死亡'} | "
                  f"能:{pc.energy:.2f} | 领:{claimed:3d} | 迹:{total_visits:4d}")
        print()

    print("=" * 55)
    eval_result = evaluate_architectures("data")
    if eval_result:
        print(format_evaluation_report(eval_result))


def show_evaluation():
    print("\n  [加载历史数据...]")
    result = evaluate_architectures("data")
    if not result:
        print("  无数据，先跑: python main.py batch 10")
        return
    print(format_evaluation_report(result))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "interactive"

    if mode in ("batch", "b"):
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        arch = sys.argv[3] if len(sys.argv) > 3 else None
        run_batch(n, arch)

    elif mode in ("eval", "e"):
        show_evaluation()

    elif mode in ("preset", "p"):
        name = sys.argv[2] if len(sys.argv) > 2 else "暴君"
        if name not in SimEngine.get_architecture_names():
            arch = RuleBuilder.get_preset(name)
            if arch:
                SimEngine.ARCHITECTURES[name] = lambda a=arch: a
            else:
                print(f"未知预设: {name}"); sys.exit(1)
        run_interactive(name)

    elif mode in ("interactive", "i"):
        run_interactive()

    else:
        print(__doc__)
