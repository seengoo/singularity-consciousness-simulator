"""
规则式行为系统

不是"动机"，而是纯规则 ——
定义奇点如何移动、如何应对世界、如何留下痕迹。

规则类型:
  移动规则  — 决定下一步往哪走
  拾取规则  — 决定是否采集资源
  反应规则  — 遇到边界/灾难/其他奇点时的应对
  记忆规则  — 记住什么信息

每个规则是一个可组合的模块，规则之间通过优先级和条件互斥。
"""
import random
import math


# ================================================================
# 移动规则
# ================================================================

def move_random(perception, state, memory, world=None, self_pos=None):
    """完全随机"""
    dx = random.choice([-1, 0, 1])
    dy = random.choice([-1, 0, 1])
    return (dx, dy)


def move_straight(perception, state, memory, world=None, self_pos=None):
    """直走 — 保持方向，撞了才转"""
    dx, dy = state.get("_last_dir", (0, 1))
    if dx == 0 and dy == 0:
        dx, dy = random.choice([(1,0), (-1,0), (0,1), (0,-1)])
    # 如果撞墙/障碍就换方向
    if state.get("_last_bumped", False):
        dx, dy = random.choice([(1,0), (-1,0), (0,1), (0,-1)])
        state["_last_bumped"] = False
    state["_last_dir"] = (dx, dy)
    return (dx, dy)


def move_spiral(perception, state, memory, world=None, self_pos=None):
    """螺旋 — 始终左转（贴墙走）"""
    dx, dy = state.get("_last_dir", (0, 1))
    if state.get("_last_bumped", False) or random.random() < 0.15:
        # 左转: (dx,dy) -> (-dy, dx)
        dx, dy = -dy, dx
        state["_last_bumped"] = False
    state["_last_dir"] = (dx, dy)
    return (dx, dy)


def move_scan(perception, state, memory, world=None, self_pos=None):
    """扫描 — 逐行扫描，到底换行"""
    direction = state.get("_scan_dir", 1)  # 1=右, -1=左
    dx = direction
    dy = 0
    if state.get("_last_bumped", False):
        dx = 0
        dy = 1  # 换行
        state["_scan_dir"] = -state["_scan_dir"]
        state["_last_bumped"] = False
    state["_last_dir"] = (dx, dy)
    return (dx, dy)


def move_explore(perception, state, memory, world=None, self_pos=None):
    """探索 — 优先去没去过/去得少的方向"""
    if not perception:
        return move_random(perception, state, memory)
    # 找访问次数最少的方向
    best_dir = None
    best_count = 999999
    x, y = self_pos or (0, 0)
    for (dx, dy), info in perception.items():
        vc = info.get("visit_count", 0)
        if vc < best_count:
            best_count = vc
            best_dir = (dx, dy)
    if best_dir and random.random() < 0.7:
        return best_dir
    return move_random(perception, state, memory)


def move_boundary(perception, state, memory, world=None, self_pos=None):
    """边界 — 沿着世界边缘走"""
    # 简单实现：先走到边缘，然后沿着走
    x, y = self_pos or (0, 0)
    size = world.size if world else 60
    # 靠近边缘了吗？
    edge_dist = min(x, y, size-x-1, size-y-1)
    if edge_dist > 3:
        # 没到边缘，往边缘走
        dx = -1 if x > size//2 else 1 if x < size//2 else 0
        dy = -1 if y > size//2 else 1 if y < size//2 else 0
        if dx == 0 and dy == 0:
            dx = 1
        return (dx, dy)
    # 到了边缘，沿着走（顺时针）
    # 上边缘: (1,0), 右边缘: (0,1), 下边缘: (-1,0), 左边缘: (0,-1)
    dirs = [(1,0), (0,1), (-1,0), (0,-1)]
    if state.get("_last_bumped", False):
        state["_edge_idx"] = (state.get("_edge_idx", 0) + 1) % 4
        state["_last_bumped"] = False
    didx = state.get("_edge_idx", 0)
    return dirs[didx % 4]


def move_escape(perception, state, memory, world=None, self_pos=None):
    """逃逸 — 远离一切（资源、其他奇点、足迹密集区）"""
    if not perception:
        return move_random(perception, state, memory)
    # 找周围"最讨厌"的东西的方向，反方向走
    avoid_x, avoid_y = 0, 0
    x, y = self_pos or (0, 0)
    for (dx, dy), info in perception.items():
        weight = 0
        if info["type"] == "singularity":
            weight = 2.0
        elif info.get("visit_count", 0) > 5:
            weight = 1.0
        elif info.get("claimed"):
            weight = 0.5
        if weight > 0:
            # 远离这个方向
            avoid_x -= dx * weight
            avoid_y -= dy * weight

    # 归一化
    length = abs(avoid_x) + abs(avoid_y)
    if length > 0:
        dx = max(-1, min(1, int(round(avoid_x / length))))
        dy = max(-1, min(1, int(round(avoid_y / length))))
        if dx != 0 or dy != 0:
            return (dx, dy)
    return move_random(perception, state, memory)


def move_toward_resources(perception, state, memory, world=None, self_pos=None):
    """资源导向 — 朝资源走"""
    if not perception:
        return move_random(perception, state, memory)
    best = None
    best_dist = 999
    for (dx, dy), info in perception.items():
        if info["type"] == "resource":
            dist = abs(dx) + abs(dy)
            if dist < best_dist:
                best_dist = dist
                best = (dx, dy)
    if best and random.random() < 0.6:
        return best
    return move_random(perception, state, memory)


def move_flee_disasters(perception, state, memory, world=None, self_pos=None):
    """灾难规避 — 远离灾难"""
    if not perception:
        return move_random(perception, state, memory)
    for (dx, dy), info in perception.items():
        if info["type"] == "disaster":
            # 反方向
            return (-dx, -dx) if dx != 0 else (random.choice([-1,1]), 0)
    return move_random(perception, state, memory)


def move_stalk(perception, state, memory, world=None, self_pos=None):
    """跟踪 — 朝其他奇点走"""
    if not perception:
        return move_random(perception, state, memory)
    for (dx, dy), info in perception.items():
        if info["type"] == "singularity":
            return (dx, dy)
    return move_random(perception, state, memory)


# 移动规则注册表
MOVE_RULES = {
    "random":        ("随机移动", move_random, "完全随机方向"),
    "straight":      ("直走", move_straight, "保持方向，撞了才转"),
    "spiral":        ("螺旋", move_spiral, "始终左转贴墙走"),
    "scan":          ("扫描", move_scan, "逐行扫描到底换行"),
    "explore":       ("探索", move_explore, "优先去没去过的地方"),
    "boundary":      ("边界", move_boundary, "沿着世界边缘走"),
    "escape":        ("逃逸", move_escape, "远离一切足迹和奇点"),
    "resource":      ("寻资源", move_toward_resources, "朝资源方向走"),
    "flee":          ("避灾", move_flee_disasters, "远离灾难"),
    "stalk":         ("跟踪", move_stalk, "朝其他奇点走"),
}


# ================================================================
# 拾取规则 — 决定是否采集资源
# ================================================================

def collect_all(state, memory, resource_info=None):
    """全部采集"""
    return True


def collect_left(state, memory, resource_info=None):
    """只在从左边接近时采集"""
    approach_dir = state.get("_approach_dir", (0, 0))
    # 左边 = (-1, 0) 或 (0, -1) 的某种意义
    if approach_dir == (-1, 0):  # 从右边来（相对向左）
        return True
    if random.random() < 0.3:  # 概率性
        return True
    return False


def collect_right(state, memory, resource_info=None):
    """只在从右边接近时采集"""
    approach_dir = state.get("_approach_dir", (0, 0))
    if approach_dir == (1, 0):
        return True
    if random.random() < 0.3:
        return True
    return False


def collect_hungry(state, memory, resource_info=None):
    """只在能量低时采集"""
    energy = state.get("energy", 1.0)
    if energy < 1.0:
        return True
    return False


def collect_hoard(state, memory, resource_info=None):
    """采集并标记领地"""
    return True  # 采集逻辑统一由引擎处理，这个规则只是标记"要占地"


def collect_ignore(state, memory, resource_info=None):
    """不采集"""
    return False


def collect_alternate(state, memory, resource_info=None):
    """隔一个采一个"""
    state["_collect_count"] = state.get("_collect_count", 0) + 1
    return state["_collect_count"] % 2 == 0


PICKUP_RULES = {
    "all":       ("全部采集", collect_all, "踩到就采"),
    "left":      ("左向采集", collect_left, "只采左边的"),
    "right":     ("右向采集", collect_right, "只采右边的"),
    "hungry":    ("饥饿才采", collect_hungry, "能量<1才采"),
    "hoard":     ("占领囤积", collect_hoard, "采集并占地"),
    "ignore":    ("不采集", collect_ignore, "无视资源"),
    "alternate": ("间隔采集", collect_alternate, "隔一个采一个"),
}


# ================================================================
# 反应规则
# ================================================================

def react_bounce(state):
    """撞墙反弹"""
    state["_last_bumped"] = True
    return ("bounce",)


def react_flee(state):
    """遇险逃跑 — 反转方向"""
    state["_last_bumped"] = True
    state["_flee_mode"] = state.get("_flee_mode", 0) + 1
    return ("flee", state["_flee_mode"])


def react_ignore(state):
    """无视"""
    return ("ignore",)


def react_aggress(state):
    """遇险反击 — 往前走（强行）"""
    # 不改变方向，反而继续
    return ("aggress",)


REACTION_RULES = {
    "bounce":  ("反弹", react_bounce, "撞墙就转向"),
    "flee":    ("逃跑", react_flee, "遇险反向逃跑"),
    "ignore":  ("无视", react_ignore, "撞墙/遇险当无事"),
    "aggress": ("强闯", react_aggress, "遇险反而继续冲"),
}


# ================================================================
# 记忆规则
# ================================================================

def mem_none(state, action, result, memory):
    """无记忆 — 每次清零"""
    pass


def mem_positions(state, action, result, memory):
    """记住走过的位置（避免重复）"""
    pos = (state.get("x", -1), state.get("y", -1))
    if "visited" not in memory:
        memory["visited"] = set()
    memory["visited"].add(pos)


def mem_resources(state, action, result, memory):
    """记住资源位置"""
    if result and result.get("type") == "got_resource":
        x, y = state.get("x", -1), state.get("y", -1)
        if "resource_spots" not in memory:
            memory["resource_spots"] = []
        memory["resource_spots"].append((x, y))
        if len(memory["resource_spots"]) > 50:
            memory["resource_spots"] = memory["resource_spots"][-50:]


def mem_dangers(state, action, result, memory):
    """记住危险位置"""
    if result and result.get("type") in ("disaster", "bump_wall"):
        x, y = state.get("x", -1), state.get("y", -1)
        if "danger_zones" not in memory:
            memory["danger_zones"] = set()
        memory["danger_zones"].add((x, y))


MEMORY_RULES = {
    "none":       ("无记忆", mem_none, "不记任何事"),
    "positions":  ("记位置", mem_positions, "记住走过的格子"),
    "resources":  ("记资源", mem_resources, "记住哪里找到过资源"),
    "dangers":    ("记危险", mem_dangers, "记住遇到危险的地方"),
}


# ================================================================
# 规则架构 — 组合所有规则
# ================================================================

class RuleArchitecture:
    """
    规则式架构

    由4条规则组成:
      移动规则×1 + 拾取规则×1 + 反应规则×1 + 记忆规则×1 (+可选辅移动规则)

    奇点的行为完全由这些规则决定。
    """

    def __init__(self, name, move_rule, pickup_rule, reaction_rule, memory_rule,
                 secondary_move=None):
        self.name = name
        self.description = f"移:{move_rule[0]} 采:{pickup_rule[0]} 应:{reaction_rule[0]} 记:{memory_rule[0]}"
        self.move_fn = move_rule[1]
        self.pickup_fn = pickup_rule[1]
        self.react_fn = reaction_rule[1]
        self.mem_fn = memory_rule[1]
        self.secondary_move = secondary_move[1] if secondary_move else None

    def perceive(self, local_area, own_state):
        return local_area

    def process(self, perception, internal_state):
        return internal_state

    def decide(self, internal_state):
        """核心决策 — 由规则驱动"""
        # 决策结果由外部引擎使用 step_on + 规则
        # 这里只返回移动方向
        perception = internal_state.get("_last_perception", {})
        memory = internal_state.get("_memory", {})
        world = internal_state.get("_world")
        pos = (internal_state.get("x", 0), internal_state.get("y", 0))

        # 主移动规则
        dx, dy = self.move_fn(perception, internal_state, memory, world, pos)

        # 如果有辅规则且概率触发
        if self.secondary_move and random.random() < 0.3:
            sdx, sdy = self.secondary_move(perception, internal_state, memory, world, pos)
            if random.random() < 0.5:
                dx, dy = sdx, sdy

        # 记录接近方向（给采集规则用）
        internal_state["_approach_dir"] = (dx, dy)

        internal_state["步数"] = internal_state.get("步数", 0) + 1
        return {"type": "move", "dx": dx, "dy": dy}

    def should_collect(self, internal_state, resource_info=None):
        """是否采集这个资源"""
        return self.pickup_fn(internal_state, internal_state.get("_memory", {}), resource_info)

    def react(self, internal_state):
        """反应事件"""
        return self.react_fn(internal_state)

    def memorize(self, perception, action, result, memory):
        """记忆"""
        state = {}  # 内部状态代理
        state["x"] = state.get("x", 0)
        state["y"] = state.get("y", 0)
        self.mem_fn(state, action, result, memory)

    def init_state(self):
        import copy
        return {
            "步数": 0,
            "energy": 1.5,
            "_last_dir": (0, 1),
            "_last_bumped": False,
            "_scan_dir": 1,
            "_edge_idx": 0,
            "_approach_dir": (0, 0),
            "_collect_count": 0,
            "_memory": {},
            "_last_perception": {},
        }

    def describe_state(self, internal_state):
        return self.description

    def get_state_summary(self, internal_state):
        return [
            ("移动", 0.6, 0.5),
            ("能量", internal_state.get("energy", 1.0) / 3.0, 0.3),
        ]

    def on_touch_resource(self, internal_state, resource_info):
        """由引擎调用 — 是否采集由 should_collect 决定"""
        internal_state["energy"] = min(3.0, internal_state.get("energy", 1.0) +
                                       resource_info.get("energy", 0.4))

    def on_touch_disaster(self, internal_state):
        internal_state["energy"] = max(0, internal_state.get("energy", 1.0) - 0.3)

    def on_bump_wall(self, internal_state):
        self.react(internal_state)


# ================================================================
# 规则组合构建器
# ================================================================

class RuleBuilder:
    """规则选择器 — 从规则库挑选组合"""

    @staticmethod
    def build(name, move_key, pickup_key, reaction_key, memory_key,
              secondary_move_key=None):
        """构建规则架构"""
        return RuleArchitecture(
            name,
            MOVE_RULES[move_key],
            PICKUP_RULES[pickup_key],
            REACTION_RULES[reaction_key],
            MEMORY_RULES[memory_key],
            MOVE_RULES.get(secondary_move_key) if secondary_move_key else None,
        )

    @staticmethod
    def list_rules():
        """列出所有可用的规则"""
        return {
            "move": [(k, v[0], v[2]) for k, v in MOVE_RULES.items()],
            "pickup": [(k, v[0], v[2]) for k, v in PICKUP_RULES.items()],
            "reaction": [(k, v[0], v[2]) for k, v in REACTION_RULES.items()],
            "memory": [(k, v[0], v[2]) for k, v in MEMORY_RULES.items()],
        }

    @staticmethod
    def total_combinations():
        """理论组合数"""
        return len(MOVE_RULES) * len(PICKUP_RULES) * len(REACTION_RULES) * len(MEMORY_RULES) * len(MOVE_RULES)

    @staticmethod
    def get_preset(name):
        """预设架构"""
        presets = {
            "纯随机": ("random", "all", "bounce", "none"),
            "直线征服": ("straight", "all", "aggress", "positions"),
            "螺旋探索": ("spiral", "hungry", "bounce", "positions"),
            "逃逸者": ("escape", "ignore", "flee", "dangers"),
            "领土扫描": ("scan", "hoard", "aggress", "positions"),
            "边界领主": ("boundary", "hoard", "bounce", "resources"),
            "资源猎人": ("resource", "hungry", "bounce", "resources"),
            "壁虎": ("boundary", "all", "flee", "positions", "spiral"),
            "幽灵": ("explore", "ignore", "ignore", "none"),
            "暴君": ("scan", "all", "aggress", "positions", "resource"),
        }
        if name in presets:
            spec = presets[name]
            return RuleBuilder.build(name, *spec)
        return None
