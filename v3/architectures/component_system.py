"""
模块化架构系统 — 搭积木式组合奇点的行为

每个模块是一个"驱动力"，产生一个方向偏好向量。
奇点的行为 = 所有模块加权后的综合决策。

模块类型：
  - 感知类:   如何看世界
  - 驱动力类: 想要什么（核心）
  - 行动类:   如何行动
  - 记忆类:   如何学习
"""
import random
import math
from abc import ABC, abstractmethod


# ============================================================
# 模块基类
# ============================================================
class BehaviorModule(ABC):
    """行为模块基类"""

    def __init__(self, name, weight=0.5):
        self.name = name
        self.weight = max(0.0, min(1.0, weight))
        self.category = "base"

    def desire(self, perception, state, memory):
        """
        返回方向偏好: {(dx,dy): strength, ...}
        strength 范围 0.0 ~ 1.0
        也可以返回特殊动作: {"type": "wait", "strength": 0.5}
        记忆/行动类模块可以覆写这个方法，也可以只覆写 on_result
        """
        return {}

    def on_result(self, state, result, memory):
        """对行动结果的反馈（可选覆写）"""
        pass

    def get_state_display(self, state):
        """返回状态显示文本"""
        return ""


# ============================================================
# 驱动力模块 — 核心
# ============================================================
class CuriosityDrive(BehaviorModule):
    """好奇心 — 向往未知"""
    def __init__(self, weight=0.5):
        super().__init__("好奇心", weight)
        self.category = "drive"

    def desire(self, perception, state, memory):
        desire_map = {}
        for (dx, dy), info in perception.items():
            if info["type"] == "resource":
                # 见过这个颜色吗？
                col = info["color"]
                seen = col in state.get("seen_colors", set())
                novelty = 0.3 if seen else 1.0
                desire_map[(dx, dy)] = novelty * self.weight * 1.5
        return desire_map

    def on_result(self, state, result, memory):
        if "seen_colors" not in state:
            state["seen_colors"] = set()
        if result.get("type") == "got_resource":
            r = result.get("encountered", {})
            if r and "color" in r:
                state["seen_colors"].add(r["color"])


class HungerDrive(BehaviorModule):
    """饥饿 — 寻找能量"""
    def __init__(self, weight=0.5):
        super().__init__("饥饿", weight)
        self.category = "drive"

    def desire(self, perception, state, memory):
        desire_map = {}
        energy = state.get("energy", 1.0)
        urgency = max(0, 1.0 - energy / 1.5)  # 能量越低越迫切
        for (dx, dy), info in perception.items():
            if info["type"] == "resource":
                desire_map[(dx, dy)] = urgency * self.weight * 2.0
        return desire_map


class TerritoryDrive(BehaviorModule):
    """领地 — 占领和守护格子"""
    def __init__(self, weight=0.5):
        super().__init__("领地欲", weight)
        self.category = "drive"

    def desire(self, perception, state, memory):
        desire_map = {}
        claimed_by_self = state.get("claimed_cells", set())
        for (dx, dy), info in perception.items():
            # 如果格子上有资源且未被自己占领 → 想去占领
            if info["type"] == "resource":
                world_pos = (state.get("x", 0) + dx, state.get("y", 0) + dy)
                if world_pos not in claimed_by_self:
                    desire_map[(dx, dy)] = 0.8 * self.weight
        return desire_map


class AggressionDrive(BehaviorModule):
    """侵略 — 抢夺他人领地"""
    def __init__(self, weight=0.5):
        super().__init__("侵略性", weight)
        self.category = "drive"

    def desire(self, perception, state, memory):
        desire_map = {}
        for (dx, dy), info in perception.items():
            if info.get("claimed_by") and info["claimed_by"] != "self":
                desire_map[(dx, dy)] = 1.0 * self.weight
            elif info["type"] == "resource":
                desire_map[(dx, dy)] = 0.3 * self.weight
        return desire_map


class SocialDrive(BehaviorModule):
    """社交 — 靠近/远离其他奇点"""
    def __init__(self, weight=0.5, prefer_approach=True):
        super().__init__("社交", weight)
        self.category = "drive"
        self.approach = prefer_approach

    def desire(self, perception, state, memory):
        desire_map = {}
        for (dx, dy), info in perception.items():
            if info["type"] == "singularity":
                strength = 0.8 * self.weight
                if self.approach:
                    desire_map[(dx, dy)] = strength
                else:
                    desire_map[(-dx, -dy)] = strength
        return desire_map


class ExplorationDrive(BehaviorModule):
    """探索 — 去没去过的地方"""
    def __init__(self, weight=0.5):
        super().__init__("探索欲", weight)
        self.category = "drive"

    def desire(self, perception, state, memory):
        visited = state.get("visited", set())
        desire_map = {}
        for (dx, dy) in perception:
            world_pos = (state.get("x", 0) + dx, state.get("y", 0) + dy)
            if world_pos not in visited:
                desire_map[(dx, dy)] = 0.6 * self.weight
        return desire_map


class OrderDrive(BehaviorModule):
    """秩序 — 沿着固定模式走（系统化）"""
    def __init__(self, weight=0.5):
        super().__init__("秩序感", weight)
        self.category = "drive"
        self._pattern_idx = 0
        self._pattern = [(1,0), (0,1), (-1,0), (0,-1)]

    def desire(self, perception, state, memory):
        desire_map = {}
        idx = state.get("_order_idx", 0)
        p = self._pattern[idx % len(self._pattern)]
        desire_map[p] = 0.5 * self.weight
        state["_order_idx"] = idx + 1
        return desire_map


# 所有可用驱动力
ALL_DRIVES = {
    "curiosity": CuriosityDrive,
    "hunger": HungerDrive,
    "territory": TerritoryDrive,
    "aggression": AggressionDrive,
    "social": SocialDrive,
    "exploration": ExplorationDrive,
    "order": OrderDrive,
}


# ============================================================
# 行动模块
# ============================================================
class AggressiveAction(BehaviorModule):
    """激进行动 — 直接冲目标"""
    def __init__(self, weight=0.5):
        super().__init__("激进行动", weight)
        self.category = "action"

    def desire(self, perception, state, memory):
        # 不产生方向偏好，但放大其他模块的偏好
        return {}


class CautiousAction(BehaviorModule):
    """谨慎行动 — 避免风险"""
    def __init__(self, weight=0.5):
        super().__init__("谨慎行动", weight)
        self.category = "action"

    def desire(self, perception, state, memory):
        avoid = {}
        for (dx, dy), info in perception.items():
            if info["type"] == "resource" and info.get("value", 0) < 0.3:
                avoid[(-dx, -dy)] = 0.5 * self.weight
        return avoid


class ErraticAction(BehaviorModule):
    """随性行动 — 加入随机扰动"""
    def __init__(self, weight=0.5):
        super().__init__("随性行动", weight)
        self.category = "action"

    def desire(self, perception, state, memory):
        noise = random.uniform(-0.3, 0.3) * self.weight
        rd = random.choice([(1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)])
        return {rd: max(0, noise)}


ALL_ACTIONS = {
    "aggressive": AggressiveAction,
    "cautious": CautiousAction,
    "erratic": ErraticAction,
}


# ============================================================
# 记忆模块
# ============================================================
class ShortMemory(BehaviorModule):
    """短时记忆"""
    def __init__(self, weight=0.5):
        super().__init__("短时记忆", weight)
        self.category = "memory"

    def on_result(self, state, result, memory):
        # 只保留最近的记忆
        if len(memory.get("encounters", [])) > 5:
            memory["encounters"] = memory["encounters"][-5:]


class LongMemory(BehaviorModule):
    """长时记忆"""
    def __init__(self, weight=0.5):
        super().__init__("长时记忆", weight)
        self.category = "memory"

    def on_result(self, state, result, memory):
        # 保留所有记忆
        pass


ALL_MEMORIES = {
    "short": ShortMemory,
    "long": LongMemory,
}


# ============================================================
# 架构组装器
# ============================================================
class ComposedArchitecture:
    """
    由多个模块组合而成的架构

    工作方式：
      1. 所有驱动力模块各自产生"欲望方向"
      2. 按权重合并
      3. 选择最强偏好方向作为行动
    """

    def __init__(self, name="自定义架构"):
        self.name = name
        self.description = "由行为模块组合而成"
        self.drives = []       # 驱动力模块
        self.actions = []      # 行动模块
        self.memories = []     # 记忆模块
        self._components = []

    def add_module(self, module):
        """添加一个模块"""
        self._components.append(module)
        if module.category == "drive":
            self.drives.append(module)
        elif module.category == "action":
            self.actions.append(module)
        elif module.category == "memory":
            self.memories.append(module)
        return self

    def perceive(self, local_area, own_state):
        """感知 — 原样返回供模块使用"""
        return local_area

    def process(self, perception, internal_state):
        """处理 — 不改变感知"""
        return internal_state

    def decide(self, internal_state):
        """
        决策 — 合并所有模块的偏好
        1. 每个驱动力模块投票
        2. 按权重合并
        3. 加入行动模块的修正
        4. 加随机扰动
        5. 选出方向
        """
        # 收集所有偏好
        desire_sum = {}
        perception = internal_state.get("_last_perception", {})

        for drive in self.drives:
            d = drive.desire(perception, internal_state, {})
            for key, strength in d.items():
                desire_sum[key] = desire_sum.get(key, 0) + strength

        for action in self.actions:
            d = action.desire(perception, internal_state, {})
            for key, strength in d.items():
                desire_sum[key] = desire_sum.get(key, 0) + strength

        # 选最高偏好方向
        if desire_sum:
            best_dir = max(desire_sum, key=lambda k: desire_sum.get(k, 0) if isinstance(k, tuple) else 0)
            if isinstance(best_dir, tuple):
                internal_state["步数"] = internal_state.get("步数", 0) + 1
                return {"type": "move", "dx": best_dir[0], "dy": best_dir[1]}

        # 保底：随机
        dx = random.choice([-1, 0, 1])
        dy = random.choice([-1, 0, 1])
        internal_state["步数"] = internal_state.get("步数", 0) + 1
        return {"type": "move", "dx": dx, "dy": dy}

    def memorize(self, perception, action, result, memory):
        """记忆更新"""
        for m in self.memories:
            m.on_result({}, result, memory)

    def init_state(self):
        return {
            "步数": 0,
            "seen_colors": set(),
            "visited": set(),
            "claimed_cells": set(),
            "energy": 1.5,
        }

    def describe_state(self, internal_state):
        parts = []
        for drive in self.drives[:3]:
            parts.append(drive.name)
        return "+".join(parts) if parts else "原始"

    def get_state_summary(self, internal_state):
        bars = []
        for drive in self.drives[:4]:
            bars.append((drive.name, drive.weight, 0.5))
        return bars

    def on_touch_resource(self, internal_state, resource_info):
        for m in self._components:
            m.on_result(internal_state, {"type": "got_resource", "encountered": resource_info}, {})

    def on_touch_disaster(self, internal_state):
        pass

    def on_bump_wall(self, internal_state):
        pass


# ============================================================
# 构建器
# ============================================================
class ArchitectureBuilder:
    """架构构建器 — 生成组合架构"""

    @staticmethod
    def create_preset(name):
        """从预设创建"""
        presets = {
            "好奇探索者": [
                ("curiosity", 0.8),
                ("exploration", 0.7),
                ("hunger", 0.3),
                ("erratic", 0.2),
                ("long", 0.5),
            ],
            "领地霸主": [
                ("territory", 0.9),
                ("aggression", 0.8),
                ("hunger", 0.6),
                ("aggressive", 0.7),
                ("long", 0.5),
            ],
            "和平采集者": [
                ("hunger", 0.8),
                ("exploration", 0.5),
                ("cautious", 0.5),
                ("order", 0.3),
                ("short", 0.5),
            ],
            "社交达人": [
                ("social", 0.8),
                ("curiosity", 0.5),
                ("exploration", 0.5),
                ("erratic", 0.3),
                ("long", 0.5),
            ],
            "独裁者": [
                ("territory", 1.0),
                ("aggression", 1.0),
                ("hunger", 0.8),
                ("aggressive", 1.0),
                ("order", 0.5),
                ("long", 0.5),
            ],
            "随机原始": [
                ("curiosity", 0.3),
                ("hunger", 0.3),
                ("exploration", 0.3),
                ("erratic", 0.5),
                ("short", 0.5),
            ],
        }

        if name in presets:
            arch = ComposedArchitecture(name)
            for module_id, weight in presets[name]:
                module_class = ALL_DRIVES.get(module_id) or \
                              ALL_ACTIONS.get(module_id) or \
                              ALL_MEMORIES.get(module_id)
                if module_class:
                    arch.add_module(module_class(weight))
            return arch

        # 自定义自由组合
        return ComposedArchitecture(name)

    @staticmethod
    def get_preset_names():
        return ["好奇探索者", "领地霸主", "和平采集者", "社交达人", "独裁者", "随机原始"]

    @staticmethod
    def get_total_combinations():
        """理论组合数"""
        n_drives = len(ALL_DRIVES)
        n_actions = len(ALL_ACTIONS)
        n_memories = len(ALL_MEMORIES)
        # 选任意数量的驱动力 + 0-1个行动 + 1个记忆 + 每种有权重变化(假设3档)
        import math
        drive_combs = 2**n_drives - 1  # 至少选1个
        action_combs = n_actions + 1  # 0个或1个
        memory_combs = n_memories    # 必须选1个
        weight_levels = 3**(n_drives + 1)  # 粗略估计
        total = drive_combs * action_combs * memory_combs * weight_levels
        return total
