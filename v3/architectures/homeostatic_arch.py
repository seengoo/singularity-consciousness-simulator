"""
内稳态架构 — 平衡维持

内部有多个变量需要维持平衡：活力、稳定、和谐。
不同资源影响不同变量。
系统感知周围，主动寻找能修正偏离变量的资源。
如果找不到目标资源，则随机探索。

关键机制：适度偏离驱动探索，高度偏离驱动觅食。
"""
import random
import math
from architectures.base import Architecture

# 资源类型对内部变量的影响映射
RESOURCE_EFFECTS = {
    0: {"name": "赤焰", "vitality": 0.3, "stability": -0.2, "harmony": -0.1},
    1: {"name": "深水", "vitality": -0.1, "stability": 0.3, "harmony": 0.2},
    2: {"name": "翡翠", "vitality": 0.1, "stability": 0.1, "harmony": 0.3},
    3: {"name": "玄金", "vitality": 0.4, "stability": -0.3, "harmony": -0.2},
    4: {"name": "紫晶", "vitality": -0.2, "stability": -0.1, "harmony": 0.4},
}

DISASTER_EFFECT = {"vitality": -0.3, "stability": -0.4, "harmony": -0.2}

# 每个变量对应的资源ID（正效果）
VAR_TO_RESOURCE = {
    "vitality": [0, 3],   # 赤焰、玄金
    "stability": [1],     # 深水
    "harmony": [2, 4],    # 翡翠、紫晶
}


class HomeostaticArch(Architecture):
    """内稳态 — 平衡驱动探索"""

    def __init__(self):
        super().__init__()
        self.name = "内稳态平衡者"
        self.description = "内部平衡驱动：偏离产生紧张，紧张驱动觅食，平衡状态探索"

    def _find_avoid_dir(self, local_area):
        """仅规避相邻的灾难"""
        adjacent = []
        for (dx, dy), info in local_area.items():
            if info["type"] == "disaster" and abs(dx) <= 1 and abs(dy) <= 1:
                adjacent.append((dx, dy))
        if not adjacent:
            return None
        avg_dx = sum(d[0] for d in adjacent) / len(adjacent)
        avg_dy = sum(d[1] for d in adjacent) / len(adjacent)
        avoid = (-int(round(avg_dx)), -int(round(avg_dy)))
        if avoid == (0, 0):
            avoid = random.choice([(1,0), (-1,0), (0,1), (0,-1)])
        return avoid

    def _find_target_dir(self, local_area, target_rid):
        """在局部区域中找到目标资源的方向"""
        if not local_area or target_rid is None:
            return None
        candidates = []
        for (dx, dy), info in local_area.items():
            if info["type"] == "resource" and info.get("resource_id") == target_rid:
                dist = math.sqrt(dx*dx + dy*dy)
                candidates.append(((dx, dy), dist))
        if candidates:
            candidates.sort(key=lambda x: x[1])
            return candidates[0][0]
        return None

    def perceive(self, local_area, own_state):
        """感知周围，评估偏离方向"""
        vars_state = {
            k: own_state.get(k, 0.5)
            for k in ["vitality", "stability", "harmony"]
        }

        # 计算各变量偏离度
        deviations = {k: abs(v - 0.5) for k, v in vars_state.items()}
        most_dev = max(deviations, key=deviations.get)
        dev_value = deviations[most_dev]
        current_val = vars_state[most_dev]

        # 确定需要什么资源类型（正/负效果）
        need_positive = current_val < 0.5
        target_rids = VAR_TO_RESOURCE.get(most_dev, [])
        # 尝试找能给最偏离变量正效果的资源
        target_rid = None
        for rid in target_rids:
            eff = RESOURCE_EFFECTS[rid].get(most_dev, 0)
            if (need_positive and eff > 0) or (not need_positive and eff < 0):
                target_rid = rid
                break

        # 如果找不到正效果资源，接受任何修正资源
        if target_rid is None and target_rids:
            target_rid = target_rids[0]

        # 寻找方向
        target_dir = self._find_target_dir(local_area, target_rid)
        avoid_dir = self._find_avoid_dir(local_area)

        # 统计周围资源丰富度（用于探索决策）
        n_resources_nearby = sum(
            1 for info in local_area.values() if info["type"] == "resource"
        )

        return {
            "most_deviated": most_dev,
            "deviation": dev_value,
            "vars": vars_state,
            "target_resource_id": target_rid,
            "target_resource_name": RESOURCE_EFFECTS[target_rid]["name"]
                if target_rid is not None else None,
            "target_dir": target_dir,
            "avoid_dir": avoid_dir,
            "tension": dev_value,
            "n_resources_nearby": n_resources_nearby,
        }

    def process(self, perception, internal_state):
        """更新内部状态 — 动态漂移"""
        # 偏离大时漂移快（自我修正加快），偏离小时漂移慢（稳定状态）
        base_drift = 0.002
        tension_boost = perception.get("deviation", 0) * 0.01
        drift = base_drift + tension_boost

        for var in ["vitality", "stability", "harmony"]:
            internal_state[var] += (0.5 - internal_state[var]) * drift
            internal_state[var] = max(0.05, min(0.95, internal_state[var]))

        # 紧张度 = 最大偏离 * 3 (0到~1.35, cap at 1.0)
        tension = min(1.0, perception.get("deviation", 0) * 3)
        internal_state["tension"] = tension

        # 缓存感知
        internal_state["target_resource"] = perception.get("target_resource_name")
        internal_state["most_deviated"] = perception.get("most_deviated")
        internal_state["_cached_target_dir"] = perception.get("target_dir")
        internal_state["_cached_avoid_dir"] = perception.get("avoid_dir")

        # 环境丰富度影响探索欲望
        env_rich = min(1.0, perception.get("n_resources_nearby", 0) / 5)
        internal_state["explore_drive"] = max(0.2, 1.0 - tension - env_rich * 0.3)

        return internal_state

    def decide(self, internal_state):
        """决策：紧张驱动觅食，放松驱动探索"""
        tension = internal_state.get("tension", 0)
        explore_drive = internal_state.get("explore_drive", 0.5)
        target_dir = internal_state.get("_cached_target_dir")
        avoid_dir = internal_state.get("_cached_avoid_dir")

        # 规则：
        # 1. 相邻有灾难 → 回避（任何状态）
        # 2. 高紧张 + 有目标方向 → 觅食
        # 3. 中紧张 → 探索（随机大步）
        # 4. 低紧张 → 悠闲漫步

        if avoid_dir is not None:
            dx, dy = avoid_dir
        elif tension > 0.25 and target_dir is not None:
            dx, dy = target_dir
        elif tension > 0.15:
            # 中紧张 — 探索性移动
            dx = random.choice([-1, 0, 1])
            dy = random.choice([-1, 0, 1])
            if tension > 0.2:
                dx = random.choice([-1, 1])
                dy = random.choice([-1, 1])
        else:
            # 低紧张 — 悠闲探索
            dx = random.choice([-1, 0, 1])
            dy = random.choice([-1, 0, 1])
            # 偶尔停下"休息"
            if random.random() < 0.15:
                dx, dy = 0, 0

        internal_state["步数"] = internal_state.get("步数", 0) + 1
        return {"type": "move", "dx": dx, "dy": dy}

    def init_state(self):
        return {
            "vitality": 0.6,
            "stability": 0.5,
            "harmony": 0.4,
            "tension": 0.0,
            "explore_drive": 0.5,
            "步数": 0,
            "target_resource": None,
            "most_deviated": None,
            "balance_events": 0,
            "_cached_target_dir": None,
            "_cached_avoid_dir": None,
        }

    def describe_state(self, internal_state):
        v = internal_state.get("vitality", 0.5) * 100
        s = internal_state.get("stability", 0.5) * 100
        h = internal_state.get("harmony", 0.5) * 100
        t = internal_state.get("tension", 0) * 100
        target = internal_state.get("target_resource", "无")
        return f"活:{v:.0f} 稳:{s:.0f} 谐:{h:.0f} 张:{t:.0f} 寻:{target}"

    def get_state_summary(self, internal_state):
        return [
            ("活力", internal_state.get("vitality", 0.5), 0.5),
            ("稳定", internal_state.get("stability", 0.5), 0.5),
            ("和谐", internal_state.get("harmony", 0.5), 0.5),
            ("紧张", min(1.0, internal_state.get("tension", 0)), 0.3),
        ]

    def on_touch_resource(self, internal_state, resource_info):
        rid = resource_info.get("resource_id")
        if rid is not None and rid in RESOURCE_EFFECTS:
            effects = RESOURCE_EFFECTS[rid]
            for var, delta in effects.items():
                if var == "name":
                    continue
                internal_state[var] = max(0.0, min(1.0, internal_state[var] + delta))
            internal_state["balance_events"] = internal_state.get("balance_events", 0) + 1
            internal_state["tension"] = max(0, internal_state.get("tension", 0) - 0.12)

    def on_touch_disaster(self, internal_state):
        for var, delta in DISASTER_EFFECT.items():
            internal_state[var] = max(0.0, min(1.0, internal_state[var] + delta))
        internal_state["tension"] = min(1.0, internal_state.get("tension", 0) + 0.25)

    def on_bump_wall(self, internal_state):
        internal_state["tension"] = min(1.0, internal_state.get("tension", 0) + 0.02)
        # 撞墙后增加探索驱动力（换个方向尝试）
        internal_state["explore_drive"] = min(1.0, internal_state.get("explore_drive", 0) + 0.1)
