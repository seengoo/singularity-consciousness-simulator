"""
基线架构 — 纯随机

最简单的"思考"：什么都不存储，随机选择方向移动。
没有好奇心，没有记忆，没有偏好。
作为对照组，其他架构的表现与之对比。
"""
import random
from architectures.base import Architecture


class RandomArch(Architecture):
    """纯随机 — 意识基线"""

    def __init__(self):
        super().__init__()
        self.name = "随机游荡"
        self.description = "完全随机行动，无记忆无偏好 — 对照组"

    def perceive(self, local_area, own_state):
        """随机架构不关心感知"""
        return {"nothing": True}

    def process(self, perception, internal_state):
        """什么都不做"""
        return internal_state

    def decide(self, internal_state):
        """随机选方向"""
        dx = random.choice([-1, 0, 1])
        dy = random.choice([-1, 0, 1])
        return {"type": "move", "dx": dx, "dy": dy}

    def memorize(self, perception, action, result, memory):
        pass

    def init_state(self):
        return {"步数": 0}

    def describe_state(self, internal_state):
        return f"随机游荡中... (已走 {internal_state.get('步数', 0)} 步)"

    def get_state_summary(self, internal_state):
        return [("活动量", internal_state.get("步数", 0) % 100 / 100, 0.5)]

    def on_touch_resource(self, internal_state, resource_info):
        internal_state["步数"] = internal_state.get("步数", 0) + 1
        # 随机架构碰到资源也不会在意

    def on_touch_disaster(self, internal_state):
        internal_state["步数"] = internal_state.get("步数", 0) + 1
