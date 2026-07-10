"""
单次运行报告 — 一个奇点从开始到结束的完整报告

包含：基本统计、行为分析、有趣事件、探索模式
"""
import json
import os
from datetime import datetime
from collections import Counter


def generate_run_report(observer, singularity, world, run_id=None):
    """
    生成单次运行报告
    Args:
        observer: Observer instance
        singularity: Singularity instance
        world: World instance
        run_id: optional identifier
    Returns:
        dict with all report data, and formatted string
    """
    arch_name = singularity.arch.name
    run_id = run_id or f"{arch_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # 基础统计
    stats = observer.get_current_stats()
    behavior = observer.get_behavior_summary()

    # 资源偏好分析
    resource_prefs = dict(sorted(
        observer.resource_encounters.items(),
        key=lambda x: -x[1]
    ))

    # 时间线摘要
    timeline_highlights = []
    for event in observer.interesting_events[:15]:
        timeline_highlights.append(f"  [{event['cycle']:5d}] {event['description']}")

    # 探索热区
    explored = len(observer.explored_positions)
    total_area = world.size * world.size
    explored_pct = explored / total_area * 100

    # 行动分布
    total_actions = sum(observer.action_counts.values()) or 1
    action_dist = {k: f"{v/total_actions*100:.1f}%" for k, v in
                   sorted(observer.action_counts.items(), key=lambda x: -x[1])}

    # 行为倾向评分
    explore_score = min(100, behavior["explore_ratio"] * 500)
    disaster_avoid = max(0, 100 - behavior["disaster_ratio"] * 2000)
    boundary_tendency = min(100, behavior["wall_bump_ratio"] * 1000)
    area_coverage = behavior["area_percent"]

    report = {
        "run_id": run_id,
        "architecture": arch_name,
        "cycles": singularity.cycle,
        "survived": singularity.alive,
        "final_pos": (singularity.x, singularity.y),

        "actions": {
            "total": total_actions,
            "distribution": action_dist,
            "resources_acquired": observer.action_counts.get("got_resource", 0),
            "disasters_encountered": observer.disaster_count,
            "wall_bumps": observer.wall_bumps,
            "waits": observer.wait_count,
        },

        "exploration": {
            "unique_positions": explored,
            "total_area": total_area,
            "coverage_pct": f"{explored_pct:.1f}%",
            "position_count": explored,
        },

        "resource_preferences": resource_prefs,

        "behavior_scores": {
            "探索欲": f"{explore_score:.0f}/100",
            "灾难回避": f"{disaster_avoid:.0f}/100",
            "边界倾向": f"{boundary_tendency:.0f}/100",
            "区域覆盖": f"{area_coverage:.1f}%",
        },

        "interesting_events": len(observer.interesting_events),
        "timeline": observer.interesting_events[:20],

        "raw_stats": stats,
    }

    # === 格式化文本报告 ===
    lines = []
    lines.append("=" * 50)
    lines.append(f"  意识涌现报告 — {arch_name}")
    lines.append(f"  运行ID: {run_id}")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"  [数据] 基础数据")
    lines.append(f"    运行周期: {singularity.cycle}")
    lines.append(f"    最终状态: {'存活' if singularity.alive else '死亡/停滞'}")
    lines.append(f"    最终位置: ({singularity.x}, {singularity.y})")
    lines.append("")
    lines.append(f"  [行动] 行动分析")
    for k, v in action_dist.items():
        sym = {
            "got_resource": "[R]", "disaster": "[D]", "bump_wall": "[W]",
            "wait": "[_]","bump_obstacle": "[O]", "none": " . ",
        }.get(k, " ? ")
        lines.append(f"    {sym} {k}: {v}")
    lines.append(f"    [R] 获取资源: {observer.action_counts.get('got_resource', 0)}次")
    lines.append(f"    [D] 遭遇灾难: {observer.disaster_count}次")
    lines.append(f"    [W] 撞墙: {observer.wall_bumps}次")
    lines.append("")
    lines.append(f"  [探索] 探索")
    lines.append(f"    访问位置: {explored}/{total_area} ({explored_pct:.1f}%)")
    lines.append("")
    lines.append(f"  [偏好] 资源偏好")
    if resource_prefs:
        for name, count in resource_prefs.items():
            lines.append(f"    {name}: {count}次")
    else:
        lines.append("    (未获取任何资源)")
    lines.append("")
    lines.append(f"  [行为] 行为评分")
    lines.append(f"    探索欲: {explore_score:.0f}/100 -- {'高' if explore_score > 60 else '中' if explore_score > 30 else '低'}")
    lines.append(f"    灾难回避: {disaster_avoid:.0f}/100 -- {'好' if disaster_avoid > 60 else '中' if disaster_avoid > 30 else '差'}")
    lines.append(f"    边界倾向: {boundary_tendency:.0f}/100 -- {'强' if boundary_tendency > 60 else '中' if boundary_tendency > 30 else '弱'}")
    lines.append(f"    区域覆盖: {area_coverage:.1f}%")
    lines.append("")
    lines.append(f"  [事件] 有趣事件 ({len(observer.interesting_events)}件)")
    for line in timeline_highlights:
        lines.append(line)
    lines.append("")
    lines.append("=" * 50)

    return report, "\n".join(lines)


def save_run_report(report_data, directory="data"):
    """保存报告到文件"""
    os.makedirs(directory, exist_ok=True)
    filepath = os.path.join(directory, f"{report_data['run_id']}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    return filepath


def load_run_report(filepath):
    """加载报告"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
