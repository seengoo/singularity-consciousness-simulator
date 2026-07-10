"""
意识涌现评估系统

不从哲学上判断奇点"有没有意识"。
而是问一个可测量的问题：

  它的行为轨迹，是否展现出超越规则本身的特征？

评估维度：
  自适应    — 失败后是否改变行为？
  目标持久  — 是否有持续稳定的行为倾向？
  资源策略  — 采集行为的效率和组织程度？
  领地意识  — 是否表现出领域性？
  探索策略  — 探索方式是否呈现模式？
  学习能力  — 是否避免重复犯错？
  行为复杂度 — 行为序列的熵和多样性？
"""
import math
from collections import Counter, defaultdict


class ConsciousnessAssessment:
    """意识涌现评估"""

    def __init__(self, observer, singularity, world, population):
        self.obs = observer
        self.sing = singularity
        self.world = world
        self.pop = population

    def assess(self):
        """全面评估，返回评估报告"""
        dims = {
            "adaptability":     self._adaptability(),
            "goal_persistence": self._goal_persistence(),
            "resource_strategy": self._resource_strategy(),
            "territoriality":   self._territoriality(),
            "exploration":      self._exploration_strategy(),
            "learning":         self._learning(),
            "behavior_complexity": self._complexity(),
        }

        # 加权总分 (每个维度 0-100)
        weights = {
            "adaptability": 0.15,
            "goal_persistence": 0.10,
            "resource_strategy": 0.15,
            "territoriality": 0.15,
            "exploration": 0.15,
            "learning": 0.10,
            "behavior_complexity": 0.20,
        }

        total = sum(dims[k]["score"] * weights[k] for k in dims)
        max_total = sum(100 * w for w in weights.values())

        emergence_index = total / max_total * 100 if max_total > 0 else 0

        # 裁决
        verdict = self._verdict(emergence_index, dims)

        return {
            "dimensions": dims,
            "emergence_index": round(emergence_index, 1),
            "verdict": verdict,
            "raw": {
                "cycles": self.sing.cycle,
                "alive": self.sing.alive,
                "npc_count": len(self.pop.npcs) if self.pop else 0,
            }
        }

    # ─── 维度1: 自适应 ───
    def _adaptability(self):
        """撞墙/遇灾后是否改变行为？"""
        events = self.obs.events
        if len(events) < 20:
            return {"score": 0, "detail": "数据不足"}

        # 统计"撞墙→转向"的延迟
        wall_events = [e for e in events if e.get("result", {}).get("type") == "bump_wall"]
        if not wall_events:
            return {"score": 50, "detail": "无撞墙事件(可能沿墙走)"}

        # 撞墙后下一步的方向是否不同？
        direction_changes = 0
        for i, e in enumerate(events[:-1]):
            if e.get("result", {}).get("type") == "bump_wall":
                next_e = events[i+1] if i+1 < len(events) else None
                if next_e:
                    next_result = next_e.get("result", {}).get("type", "")
                    if next_result in ("got_resource", "move", "wait"):
                        direction_changes += 1

        change_rate = direction_changes / len(wall_events) if wall_events else 0
        # 70-100% 变化率 = 好的自适应
        score = min(100, max(0, change_rate * 100))

        return {
            "score": round(score),
            "detail": f"撞墙{len(wall_events)}次, {direction_changes}次改变方向(率{change_rate:.0%})",
        }

    # ─── 维度2: 目标持久性 ───
    def _goal_persistence(self):
        """行为是否呈现出持续稳定的模式？"""
        events = self.obs.events
        if len(events) < 50:
            return {"score": 0, "detail": "数据不足"}

        # 分析行为序列的"运行长度"
        result_types = [e.get("result", {}).get("type", "none") for e in events]

        # 同一个行为的连续重复长度
        run_lengths = []
        current = 1
        for i in range(1, len(result_types)):
            if result_types[i] == result_types[i-1]:
                current += 1
            else:
                run_lengths.append(current)
                current = 1
        run_lengths.append(current)

        if not run_lengths:
            return {"score": 0, "detail": "无行为数据"}

        avg_run = sum(run_lengths) / len(run_lengths)
        max_run = max(run_lengths)

        # 平均运行长度 2-10 之间 = 健康的持久性
        # < 2 = 太随机, > 20 = 卡住了
        if avg_run < 2:
            score = 20
        elif avg_run < 5:
            score = 60 + avg_run * 8  # 60-92
        elif avg_run < 15:
            score = 80  # 稳定
        else:
            score = max(0, 100 - avg_run * 2)  # 太长 = 卡死

        return {
            "score": round(min(100, score)),
            "detail": f"行为平均持续{avg_run:.1f}步, 最长{max_run}步",
        }

    # ─── 维度3: 资源策略 ───
    def _resource_strategy(self):
        """采集行为是否有效率？"""
        events = self.obs.events
        if not events:
            return {"score": 0, "detail": "无数据"}

        total_steps = len(events)
        resources = self.obs.action_counts.get("got_resource", 0)

        if total_steps == 0:
            return {"score": 0, "detail": "无活动"}

        # 资源获取率（每步获取资源的效率）
        rate = resources / total_steps

        # 资源偏好多样性
        pref_diversity = len(self.obs.resource_encounters)

        # 最优策略：每20-50步获取一个资源 = 可持续
        # rate = 0.02-0.05 = 理想
        if rate == 0:
            score = 5
        elif rate < 0.01:
            score = 20  # 太少
        elif rate < 0.03:
            score = 60 + rate * 1000  # ~60-90
        elif rate < 0.1:
            score = 90  # 良好
        else:
            score = 80  # 太多 = 可能是运气

        # 多样性加分
        diversity_bonus = min(20, pref_diversity * 5)

        return {
            "score": round(min(100, score + diversity_bonus)),
            "detail": f"采集率{rate:.2%}({resources}/{total_steps}), 偏好{pref_diversity}种资源",
        }

    # ─── 维度4: 领地意识 ───
    def _territoriality(self):
        """是否表现出领域性行为？"""
        if not self.world:
            return {"score": 0, "detail": "无世界数据"}

        pc_claimed = self.world.get_claimed_count("pc")
        all_claimed = len(self.world.claimed_by)

        if all_claimed == 0:
            return {"score": 0, "detail": "无领地行为"}

        # 领地占有率
        market_share = pc_claimed / max(1, all_claimed) * 100

        # 领地密度：是否聚集还是分散？
        if pc_claimed > 0:
            # 如果有领地且占有率>50% = 领地意识强
            if market_share > 80:
                score = 95
            elif market_share > 50:
                score = 80
            elif market_share > 20:
                score = 60
            else:
                score = 40
        else:
            score = 10

        return {
            "score": round(score),
            "detail": f"领地{pc_claimed}格/共{all_claimed}格(占有率{market_share:.0f}%)",
        }

    # ─── 维度5: 探索策略 ───
    def _exploration_strategy(self):
        """探索方式是否系统化？"""
        if not self.obs:
            return {"score": 0, "detail": "无观察数据"}

        explored = len(self.obs.explored_positions)
        total = self.world.size * self.world.size if self.world else 3600
        coverage = explored / total * 100 if total > 0 else 0

        # 探索覆盖率和效率
        events = len(self.obs.events)
        if events == 0:
            return {"score": 0, "detail": "无活动"}

        # 每步探索新格子的效率
        explore_efficiency = explored / events if events > 0 else 0
        # 理想：每步0.3-0.6新格子 = 高效探索
        # 如果 <0.1 = 在重复绕圈
        # 如果 >0.8 = 随机乱走

        if coverage < 1:
            score = 10  # 几乎没探索
        elif explore_efficiency > 0.4:
            score = 90  # 高效
        elif explore_efficiency > 0.2:
            score = 70  # 中等
        elif explore_efficiency > 0.1:
            score = 50  # 低效
        else:
            score = 30  # 重复绕圈

        # 覆盖率加分
        if coverage > 60:
            score += 10
        elif coverage > 30:
            score += 5

        return {
            "score": round(min(100, score)),
            "detail": f"探索{explored}/{total}({coverage:.1f}%), 效率{explore_efficiency:.2f}/步",
        }

    # ─── 维度6: 学习能力 ───
    def _learning(self):
        """是否学会避免重复犯错？"""
        events = self.obs.events
        if len(events) < 50:
            return {"score": 0, "detail": "数据不足"}

        # 按时间分前后两半，比较"错误率"
        half = len(events) // 2
        first_half = events[:half]
        second_half = events[half:]

        def error_rate(evts):
            bad = sum(1 for e in evts
                      if e.get("result", {}).get("type") in ("bump_wall", "disaster"))
            return bad / len(evts) if evts else 0

        first_err = error_rate(first_half)
        second_err = error_rate(second_half)

        # 如果后半段错误减少 = 有学习
        improvement = first_err - second_err

        if first_err == 0:
            score = 50  # 没错可学
        elif improvement > 0.2:
            score = 95
        elif improvement > 0.1:
            score = 80
        elif improvement > 0.05:
            score = 65
        elif improvement > 0:
            score = 55
        elif improvement == 0:
            score = 40
        else:
            score = 20  # 越来越差

        return {
            "score": round(score),
            "detail": f"错误率 前半{first_err:.1%}→后半{second_err:.1%}" +
                     (f" (改善{improvement:.1%})" if improvement > 0 else
                      f" (恶化{-improvement:.1%})" if improvement < 0 else " (无变化)"),
        }

    # ─── 维度7: 行为复杂度 ───
    def _complexity(self):
        """行为序列的多样性和信息熵"""
        events = self.obs.events
        if len(events) < 20:
            return {"score": 0, "detail": "数据不足"}

        # 行为类型分布
        types = [e.get("result", {}).get("type", "none") for e in events]
        counter = Counter(types)

        # 熵：多样性越高熵越大
        total = len(types)
        entropy = 0
        for count in counter.values():
            p = count / total
            entropy -= p * math.log2(p) if p > 0 else 0

        # 最大可能熵（全不同行为）
        n_types = len(counter)
        max_entropy = math.log2(n_types) if n_types > 0 else 1

        # 相对熵
        relative_entropy = entropy / max_entropy if max_entropy > 0 else 0
        # 0.7-1.0 = 行为多样 = 好
        # < 0.3 = 行为单一

        if relative_entropy > 0.8:
            score = 90
        elif relative_entropy > 0.6:
            score = 75
        elif relative_entropy > 0.4:
            score = 55
        elif relative_entropy > 0.2:
            score = 35
        else:
            score = 15

        return {
            "score": round(score),
            "detail": f"行为种类{n_types}种, 熵{entropy:.2f}/{max_entropy:.2f}(相对{relative_entropy:.0%})",
        }

    # ─── 裁决 ───
    def _verdict(self, index, dims):
        """综合裁决"""
        if index >= 80:
            level = "极高"
            summary = "行为展现出显著的超越简单规则的迹象"
        elif index >= 65:
            level = "高"
            summary = "行为模式中出现了规则之外的自组织特征"
        elif index >= 50:
            level = "中"
            summary = "部分行为指标显示超越纯随机的模式"
        elif index >= 30:
            level = "低"
            summary = "行为主要由规则驱动，偶见异常模式"
        else:
            level = "极低"
            summary = "行为完全由预设规则驱动"

        # 找出最强和最弱维度
        sorted_dims = sorted(dims.items(), key=lambda x: -x[1]["score"])
        strengths = [d for d, v in sorted_dims[:3] if v["score"] >= 50]
        weaknesses = [d for d, v in sorted_dims[-3:] if v["score"] < 50]

        dim_names = {
            "adaptability": "自适应",
            "goal_persistence": "目标持久性",
            "resource_strategy": "资源策略",
            "territoriality": "领地意识",
            "exploration": "探索策略",
            "learning": "学习能力",
            "behavior_complexity": "行为复杂度",
        }

        verdict = (
            f"[意识涌现指数: {index:.1f}/100] {level}\n"
            f"{summary}\n"
        )
        if strengths:
            verdict += f"  优势: {'/'.join(dim_names.get(d, d) for d in strengths)}\n"
        if weaknesses:
            verdict += f"  短板: {'/'.join(dim_names.get(d, d) for d in weaknesses)}\n"

        return verdict


def format_assessment_report(assessment):
    """格式化评估报告"""
    dim_names = {
        "adaptability": "自适应",
        "goal_persistence": "目标持久性",
        "resource_strategy": "资源策略",
        "territoriality": "领地意识",
        "exploration": "探索策略",
        "learning": "学习能力",
        "behavior_complexity": "行为复杂度",
    }

    lines = []
    lines.append("=" * 55)
    lines.append("  [评估] 意识涌现分析报告")
    lines.append("  问: 这个奇点的行为是否展现出'思考'的迹象？")
    lines.append("=" * 55)
    lines.append("")

    # 综合指数
    ei = assessment["emergence_index"]
    bar = "█" * int(ei / 10) + "░" * (10 - int(ei / 10))
    lines.append(f"  意识涌现指数: {ei:.1f}/100")
    lines.append(f"  [{bar}]")
    lines.append(f"  裁决: {assessment['verdict']}")
    lines.append("")

    # 各维度
    lines.append("  维度分析:")
    lines.append(f"  {'维度':12s} {'分数':>5s} {'说明'}")
    lines.append("  " + "-" * 50)
    for key, data in assessment["dimensions"].items():
        name = dim_names.get(key, key)
        score = data["score"]
        detail = data["detail"]
        bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
        lines.append(f"  {name:10s} [{bar}] {score:3d}  {detail}")
    lines.append("  " + "-" * 50)

    lines.append("")
    if ei >= 65:
        lines.append("  > 这个奇点的行为已经超越了纯规则驱动的范畴。")
        lines.append("  > 它的行为模式中出现了自组织、自适应、策略性规划的特征。")
    elif ei >= 40:
        lines.append("  > 这个奇点展现了一些有趣的模式，但尚未明显超越规则范畴。")
        lines.append("  > 可以尝试调整规则(特别是增加探索策略和领地意识)后重新实验。")
    else:
        lines.append("  > 这个奇点的行为基本由预设规则完全决定。")
        lines.append("  > 建议选择更复杂的规则组合(如加入辅移动规则或长记忆)。")
    lines.append("")

    lines.append("=" * 55)
    return "\n".join(lines)
