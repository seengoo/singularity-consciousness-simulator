"""
奇点 — 没有预设目标，只有内部架构驱动的循环

生命周期循环：
  感知世界 → 处理感知 → 决策行动 → 执行 → 记忆 → 下一周期
"""
import random
import math
from core.world import RESOURCE_TYPES


class Singularity:
    """
    奇点 — 从出现在世界中的那一刻开始，
    它的架构决定了它如何与世界互动。
    """

    def __init__(self, world, architecture):
        # 随机出生在世界中
        self.x = random.randint(0, world.size - 1)
        self.y = random.randint(0, world.size - 1)
        # 确保出生在可占据位置
        for _ in range(100):
            if world.can_occupy(self.x, self.y):
                break
            self.x = random.randint(0, world.size - 1)
            self.y = random.randint(0, world.size - 1)

        self._common_init(architecture, world)

    @classmethod
    def static_create(cls, x, y, architecture):
        """创建一个在指定位置的奇点（用于NPC）"""
        self = cls.__new__(cls)
        self.x = x
        self.y = y
        self._common_init(architecture, None)
        return self

    def _common_init(self, architecture, world):
        """共享初始化"""
        self.arch = architecture
        self.internal_state = architecture.init_state()

        # 能量系统
        self.energy = 2.0
        self.max_energy = 5.0
        self.energy_decay = 0.0008

        # 记忆
        self.memory = {
            "encounters": [],
            "visited_positions": set(),
            "timeline": [],
        }

        # 状态
        self.alive = True
        self.cycle = 0

        # 引用
        self.observer = None
        self._population = None
        self._is_pc = False
        self._npc_id = 0

        # 空闲计数器
        self._idle_counter = 0

        # 上次互动周期
        self._last_interaction_cycle = 0

        self._note("诞生", f"出现在 ({self.x},{self.y}) 架构:{architecture.name}")

    def set_observer(self, observer):
        self.observer = observer
        if observer:
            observer.record_state_snapshot(self)

    def step(self, world):
        """一个生命周期"""
        if not self.alive:
            return

        self.cycle += 1

        # 1️⃣ 感知
        local_area = world.get_local_area(self.x, self.y, radius=2)
        perception = self.arch.perceive(local_area, self.internal_state)

        # 2️⃣ 处理
        self.internal_state = self.arch.process(perception, self.internal_state)

        # 3️⃣ 决策
        action = self.arch.decide(self.internal_state)

        # 4️⃣ 执行
        result = self._execute_action(action, world)

        # 5️⃣ 记忆
        self.arch.memorize(perception, action, result, self.memory)

        # 记录访问位置
        self.memory["visited_positions"].add((self.x, self.y))

        # 6️⃣ 能量系统 — 消耗/饥饿/死亡
        self._update_energy(result, world)

        # 7️⃣ 停滞检测
        self._stagnation_check(result, world)

        # 8️⃣ 瘟疫检测（外部事件影响）
        if world.active_events:
            from core.events import Plague
            for event in world.active_events:
                if isinstance(event, Plague) and event.affects_position(self.x, self.y):
                    self.energy -= 0.02
                    if self.cycle - getattr(self, '_plague_warned', 0) > 50:
                        self._note("瘟疫", "身处瘟疫区，能量流失")
                        self._plague_warned = self.cycle

        # 通知观察者
        if self.observer:
            self.observer.record_event(self, "action", action, result)
            if self.cycle % 5 == 0:  # 每5周期记录一次状态快照
                self.observer.record_state_snapshot(self)

    def _stagnation_check(self, result, world):
        """检测停滞 — 无有效互动太久则死亡"""
        # 初始化计数器
        if not hasattr(self, '_idle_counter'):
            self._idle_counter = 0

        # 什么是有意义互动？
        meaningful = result.get("type") in ("got_resource", "disaster")
        if meaningful:
            self._idle_counter = 0
        else:
            self._idle_counter += 1

        # 连续2000周期无有效互动 → 停滞
        if self._idle_counter >= 2000 and self.cycle > 100:
            self.alive = False
            self.last_event = f"停滞:{self.cycle}周期无有效互动"
            self._note("停滞", self.last_event)

    def _update_energy(self, result, world):
        """能量系统 — 基础消耗 + 资源补充"""
        # 基础代谢
        self.energy -= self.energy_decay

        # 获取资源补充能量
        if result.get("type") == "got_resource":
            resource = result.get("encountered", {})
            if resource:
                gain = resource.get("energy", 0.4) * random.uniform(0.8, 1.2)
                self.energy = min(self.max_energy, self.energy + gain)

        # 能量耗尽 → 死亡
        if self.energy <= 0:
            self.alive = False
            self.last_event = f"能量耗尽:死在第{self.cycle}周期"
            self._note("死亡", self.last_event)

    def _execute_action(self, action, world):
        """执行决策结果"""
        result = {"type": "none", "encountered": None}

        if action["type"] == "move":
            dx, dy = action.get("dx", 0), action.get("dy", 0)
            # 归一化到 -1, 0, 1
            dx = max(-1, min(1, dx))
            dy = max(-1, min(1, dy))

            if dx == 0 and dy == 0:
                # 原地等待
                result["type"] = "wait"
                return result

            nx, ny = self.x + dx, self.y + dy

            # 边界检查
            if not (0 <= nx < world.size and 0 <= ny < world.size):
                self.arch.on_bump_wall(self.internal_state)
                result["type"] = "bump_wall"
                return result

            # 移动
            self.x, self.y = nx, ny

            # ★ 足迹：每走一步都染色
            sid = "pc" if self._is_pc else f"npc_{self._npc_id}"
            visitor_color = (255, 255, 255) if self._is_pc else (150, 150, 200)
            world.step_on(nx, ny, sid, visitor_color)

            # 检查脚下是什么
            cell = world.get_cell(nx, ny)
            if cell and cell.type == "resource":
                # ★ 规则系统：是否采集由规则决定
                should_take = True
                from architectures.rule_system import RuleArchitecture
                if isinstance(self.arch, RuleArchitecture):
                    should_take = self.arch.should_collect(self.internal_state, {
                        "color": cell.color, "value": cell.value,
                        "energy": cell.energy, "resource_id": cell.resource_id,
                    })

                if should_take:
                    resource = world.consume_resource(nx, ny)
                    if resource:
                        self.arch.on_touch_resource(self.internal_state, resource)
                        self.memory["encounters"].append({
                            "cycle": self.cycle, "type": "resource",
                            "name": resource["name"], "value": resource["value"]
                        })
                        self._note("获取", resource["name"])
                        result["type"] = "got_resource"
                        result["encountered"] = resource
                        # 占领
                        world.claim_cell(nx, ny, sid)
                        if "claimed_cells" in self.internal_state:
                            self.internal_state["claimed_cells"].add((nx, ny))

            elif cell and cell.type == "disaster":
                # 碰到灾难，后退一步
                self.x, self.y = self.x - dx, self.y - dy
                self.arch.on_touch_disaster(self.internal_state)
                self._note("灾难", f"遭遇灾难，退回 ({self.x},{self.y})")
                result["type"] = "disaster"
                result["encountered"] = {"type": "disaster"}

        elif action["type"] == "wait":
            result["type"] = "wait"

        return result

    def get_info(self):
        """返回奇点的基本信息"""
        return {
            "x": self.x,
            "y": self.y,
            "cycle": self.cycle,
            "alive": self.alive,
            "arch_name": self.arch.name,
            "n_encounters": len(self.memory["encounters"]),
            "n_visited": len(self.memory["visited_positions"]),
            "area_explored": len(self.memory["visited_positions"]),
        }

    def _note(self, event_type, detail=""):
        """记录内部时间线"""
        self.memory["timeline"].append({
            "cycle": self.cycle,
            "type": event_type,
            "detail": detail,
        })
        # 保留最近100条
        if len(self.memory["timeline"]) > 100:
            self.memory["timeline"] = self.memory["timeline"][-100:]
