"""
跨架构评估 — 多次运行后，对比不同架构的多维分析报告

评估维度：
  1. 探索力 — 覆盖了多少区域
  2. 生存力 — 平均生命周期
  3. 资源获取效率
  4. 行为复杂度 — 行为模式多样性
  5. 灾难应对能力
  6. 涌现特征 — "有趣"事件的数量和质量
"""
import json
import os
from collections import defaultdict
from statistics import mean, stdev


def evaluate_architectures(run_data_dir="data"):
    """
    评估所有已保存的运行报告
    Returns: dict of architecture_name -> evaluation
    """
    if not os.path.exists(run_data_dir):
        return None

    # 加载所有报告
    reports = []
    for fname in os.listdir(run_data_dir):
        if fname.endswith(".json"):
            with open(os.path.join(run_data_dir, fname), "r", encoding="utf-8") as f:
                reports.append(json.load(f))

    if not reports:
        return None

    # 按架构分组
    groups = defaultdict(list)
    for r in reports:
        groups[r["architecture"]].append(r)

    # 评估每个架构
    evaluations = {}
    for arch_name, group in groups.items():
        ev = _evaluate_group(group, arch_name)
        evaluations[arch_name] = ev

    # 对比总分
    rankings = _rank_architectures(evaluations)

    return {
        "evaluations": evaluations,
        "rankings": rankings,
        "total_runs": len(reports),
    }


def _evaluate_group(reports, arch_name):
    """评估一组相同架构的运行"""
    n = len(reports)

    # 基础指标
    cycles = [r["cycles"] for r in reports]
    survivals = [r["survived"] for r in reports]
    resources = [r["actions"]["resources_acquired"] for r in reports]
    disasters = [r["actions"]["disasters_encountered"] for r in reports]
    explored_pcts = [
        float(r["exploration"]["coverage_pct"].rstrip("%"))
        for r in reports
    ]
    interesting_counts = [r["interesting_events"] for r in reports]

    # 行为稳定性
    resource_consistency = 1.0 - (stdev(resources) / max(mean(resources), 1)) if n > 1 else 0.5

    # 综合评分 (每个维度 0-100)
    survival_score = mean(survivals) * 100
    exploration_score = min(100, mean(explored_pcts) * 2)
    resource_score = min(100, mean(resources) * 10)
    disaster_response = max(0, 100 - mean(disasters) * 20)
    complexity_score = min(100, mean(interesting_counts) * 20 + resource_consistency * 50)

    total_score = (
        survival_score * 0.2 +
        exploration_score * 0.25 +
        resource_score * 0.2 +
        disaster_response * 0.15 +
        complexity_score * 0.2
    )

    return {
        "n_runs": n,
        "avg_cycles": f"{mean(cycles):.1f}",
        "survival_rate": f"{mean(survivals)*100:.0f}%",
        "avg_resources": f"{mean(resources):.1f}",
        "avg_disasters": f"{mean(disasters):.1f}",
        "avg_explored_pct": f"{mean(explored_pcts):.1f}%",
        "avg_interesting_events": f"{mean(interesting_counts):.1f}",
        "scores": {
            "生存力": f"{survival_score:.0f}/100",
            "探索力": f"{exploration_score:.0f}/100",
            "资源效率": f"{resource_score:.0f}/100",
            "灾难应对": f"{disaster_response:.0f}/100",
            "行为复杂度": f"{complexity_score:.0f}/100",
        },
        "total_score": f"{total_score:.1f}",
    }


def _rank_architectures(evaluations):
    """按总分排序架构"""
    ranked = []
    for name, ev in evaluations.items():
        ranked.append((name, float(ev["total_score"])))
    ranked.sort(key=lambda x: -x[1])
    return [{"rank": i+1, "name": name, "score": score} for i, (name, score) in enumerate(ranked)]


def format_evaluation_report(eval_result):
    """格式化评估报告为可读文本"""
    if not eval_result:
        return "暂无运行数据，请先运行模拟。\n"

    lines = []
    lines.append("=" * 55)
    lines.append("  [冠军] 跨架构评估报告 — 意识涌现对比")
    lines.append(f"  总运行次数: {eval_result['total_runs']}")
    lines.append("=" * 55)
    lines.append("")

    # 排名
    lines.append("  [排名] 综合排名")
    for r in eval_result["rankings"]:
        medal = {1: "[1st]", 2: "[2nd]", 3: "[3rd]"}.get(r["rank"], f"  #{r['rank']}")
        lines.append(f"    {medal} {r['name']} -- 总分 {r['score']:.1f}")
    lines.append("")

    # 各架构详细
    for name, ev in eval_result["evaluations"].items():
        lines.append(f"  --- {name} ---")
        lines.append(f"    运行次数: {ev['n_runs']}")
        lines.append(f"    平均周期: {ev['avg_cycles']}")
        lines.append(f"    存活率:   {ev['survival_rate']}")
        lines.append(f"    平均资源: {ev['avg_resources']}")
        lines.append(f"    平均灾难: {ev['avg_disasters']}")
        lines.append(f"    探索区域: {ev['avg_explored_pct']}")
        lines.append(f"    有趣事件: {ev['avg_interesting_events']}")
        lines.append("    维度评分:")
        for dim, score in ev["scores"].items():
            lines.append(f"      {dim}: {score}")
        lines.append("")

    lines.append("=" * 55)
    return "\n".join(lines)
