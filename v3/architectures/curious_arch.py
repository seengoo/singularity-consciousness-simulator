"""
好奇心架构 — 新颖性驱动

真正的好奇：不仅记忆所见，还主动朝向未知。
对新颜色好奇，对熟悉厌倦。探索欲驱动方向。
"""
import random
import math
from architectures.base import Architecture


class CuriousArch(Architecture):
    """好奇心驱动 — 主动探索未知"""

    def __init__(self, memory_size=100, curiosity_rate=0.3, boredom_rate=0.05):
        super().__init__()
        self.name = "好奇心探索者"
        self.description = "记住所见，主动朝向未知，对重复感到厌倦"
        self.params = {
            "memory_size": memory_size,
            "curiosity_rate": curiosity_rate,
            "boredom_rate": boredom_rate,
        }

    def perceive(self, local_area, own_state):
        """感知周围 — 找出最"新"的方向"""
        memory = own_state.get("memory", set())
        novelty_dirs = []
        resource_dirs = []
        disaster_dirs = []

        for (dx, dy), info in local_area.items():
            t = info["type"]
            if t == "resource":
                c = info["color"]
                is_novel = c not in memory
                novelty_dirs.append(((dx, dy), 1.0 if is_novel else 0.2))
                resource_dirs.append((dx, dy))
            elif t == "disaster":
                disaster_dirs.append((dx, dy))

        # 计算各个方向的新颖度
        # 如果周围有新颖资源，向那个方向走
        best_dir = (0, 0)
        best_novelty = 0

        if novelty_dirs:
            novelty_dirs.sort(key=lambda x: -x[1])
            best_dir, best_novelty = novelty_dirs[0]

        return {
            "novelty_dir": best_dir,
            "novelty_score": best_novelty,
            "n_novel": sum(1 for _, s in novelty_dirs if s > 0.5),
            "n_total": len(local_area),
            "has_resource": len(resource_dirs) > 0,
            "has_disaster": len(disaster_dirs) > 0,
            "disaster_nearby": disaster_dirs[:3],
        }

    def process(self, perception, internal_state):
        """处理感知 → 更新内部状态"""
        # 好奇心自然衰减
        internal_state["curiosity"] *= 0.998
        internal_state["curiosity"] = max(0.1, min(1.0, internal_state["curiosity"]))

        # 新发现刺激好奇心
        novelty = perception.get("novelty_score", 0)
        if novelty > 0.5:
            boost = novelty * self.params["curiosity_rate"]
            internal_state["curiosity"] = min(1.0, internal_state["curiosity"] + boost)
            internal_state["boredom"] = max(0, internal_state["boredom"] - 0.1)
        else:
            # 没新东西 → 无聊累积
            internal_state["boredom"] += self.params["boredom_rate"]
        internal_state["boredom"] = min(3.0, max(0, internal_state["boredom"]))

        # 朝向往新颖方向积累
        nd = perception.get("novelty_dir", (0, 0))
        if nd != (0, 0):
            internal_state["direction_bias"] = (
                internal_state.get("direction_bias", 0) * 0.7 +
                (nd[0] * 0.5)  # 轻微的x方向偏移积累
            )

        # 兴奋度
        internal_state["excitement"] = (
            internal_state["curiosity"] * 0.7 +
            (1 - min(1, internal_state["boredom"] / 3)) * 0.3
        )

        return internal_state

    def decide(self, internal_state):
        """基于好奇心和感知方向决策"""
        curiosity = internal_state.get("curiosity", 0.5)
        boredom = internal_state.get("boredom", 0)
        direction_bias = internal_state.get("direction_bias", 0)

        # 无聊高 → 大步转向（探索新模式）
        if boredom > 2.0:
            dx = random.choice([-2, -1, 1, 2])
            dy = random.choice([-2, -1, 1, 2])
            dx = max(-1, min(1, dx))
            dy = max(-1, min(1, dy))
            # 无聊释放
            internal_state["boredom"] = max(0, boredom - 1.0)
        elif direction_bias > 0.3:
            # 有方向偏好 → 顺着走
            dx = 1 if random.random() < 0.7 else -1
            dy = random.choice([-1, 0, 1])
        elif direction_bias < -0.3:
            dx = -1 if random.random() < 0.7 else 1
            dy = random.choice([-1, 0, 1])
        else:
            # 随机探索
            dx = random.choice([-1, 0, 1])
            dy = random.choice([-1, 0, 1])
            # 好奇心高时更可能移动
            if curiosity > 0.8 and dx == 0 and dy == 0:
                dx = random.choice([-1, 1])

        internal_state["步数"] = internal_state.get("步数", 0) + 1
        return {"type": "move", "dx": dx, "dy": dy}

    def init_state(self):
        return {
            "curiosity": 0.8,
            "boredom": 0.0,
            "excitement": 0.7,
            "步数": 0,
            "memory": set(),
            "direction_bias": 0,
            "discoveries": 0,
        }

    def describe_state(self, internal_state):
        c = internal_state.get("curiosity", 0) * 100
        b = internal_state.get("boredom", 0) * 33
        return f"好奇:{c:.0f}% 厌倦:{b:.0f}%"

    def get_state_summary(self, internal_state):
        return [
            ("好奇心", internal_state.get("curiosity", 0.5), 0.6),
            ("厌倦度", min(1.0, internal_state.get("boredom", 0) / 3), 0.3),
            ("兴奋度", internal_state.get("excitement", 0.5), 0.5),
        ]

    def on_touch_resource(self, internal_state, resource_info):
        internal_state["discoveries"] = internal_state.get("discoveries", 0) + 1
        internal_state["curiosity"] = min(1.0, internal_state["curiosity"] + 0.03)
        internal_state["boredom"] = max(0, internal_state["boredom"] - 0.2)

    def on_touch_disaster(self, internal_state):
        internal_state["curiosity"] = max(0.1, internal_state["curiosity"] - 0.08)
        internal_state["boredom"] += 0.2

    def on_bump_wall(self, internal_state):
        internal_state["direction_bias"] = -internal_state.get("direction_bias", 0) * 0.5
