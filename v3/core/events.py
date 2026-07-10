"""
天灾引擎 — 模拟各种自然现象

事件类型:
  流星雨: 随机撞击，摧毁资源，改变地形
  地震:   改变地形，摧毁资源，创造裂谷
  台风:   移动资源，吹散堆积
  瘟疫:   削弱范围内的奇点
  资源潮: 资源在某个区域爆发涌现
"""
import random
import math
from core.world import Cell


class Event:
    def __init__(self, event_type, world, cycle):
        self.type = event_type
        self.cycle = cycle
        self.duration = 0
        self.phase = 0         # 0=pending, 1=active, 2=fading
        self.description = ""
        self.affected_area = []
        self.resources_destroyed = 0
        self.resources_created = 0

    def to_dict(self):
        return {
            "type": self.type,
            "cycle": self.cycle,
            "description": self.description,
            "resources_destroyed": self.resources_destroyed,
            "resources_created": self.resources_created,
        }


class MeteorShower(Event):
    """流星雨 — 多波次撞击"""
    def __init__(self, world, cycle):
        super().__init__("meteor", world, cycle)
        self.duration = random.randint(3, 8)
        self.n_impacts = random.randint(3, 7)
        self.impact_radius = random.randint(2, 4)
        self.description = f"流星雨 ({self.n_impacts}波)"

    def impact(self, world, cycle, observer=None):
        """执行一波撞击"""
        if self.phase == 0:
            self.phase = 1

        if cycle >= self.cycle + self.duration:
            self.phase = 2
            return

        if random.random() < 0.4:
            cx = random.randint(5, world.size-5)
            cy = random.randint(5, world.size-5)
            r = self.impact_radius
            destroyed = world.destroy_area(cx, cy, r)
            # 撞击点变成"陨石坑"地形(裂谷)
            world.change_terrain(cx, cy, 1, 2)
            self.resources_destroyed += destroyed
            self.affected_area.append((cx, cy, r))

            if observer:
                observer.log_world_event(
                    "天灾", f"流星撞击 ({cx},{cy}) 摧毁{destroyed}资源"
                )


class Earthquake(Event):
    """地震 — 改变地形"""
    def __init__(self, world, cycle):
        super().__init__("quake", world, cycle)
        self.duration = 2
        self.epicenter = (
            random.randint(10, world.size-10),
            random.randint(10, world.size-10)
        )
        self.magnitude = random.uniform(3, 8)
        self.description = f"地震 (震级{self.magnitude:.1f})"

    def execute(self, world, cycle, observer=None):
        if self.phase == 0:
            self.phase = 1

        cx, cy = self.epicenter
        r = int(self.magnitude)

        # 震中摧毁资源
        destroyed = world.destroy_area(cx, cy, 2)

        # 改变地形
        for dy in range(-r, r+1):
            for dx in range(-r, r+1):
                x, y = cx + dx, cy + dy
                dist = math.sqrt(dx*dx + dy*dy)
                if dist <= r:
                    cell = world.get_cell(x, y)
                    if cell:
                        # 随机改变地形
                        if random.random() < 0.3 * (1 - dist/r):
                            new_t = random.choice([2, 3, 0])
                            world.change_terrain(x, y, 0, new_t)

        self.resources_destroyed = destroyed
        self.phase = 2

        if observer:
            observer.log_world_event(
                "天灾", f"地震 ({cx},{cy}) 摧毁{destroyed}资源"
            )


class Typhoon(Event):
    """台风 — 吹散/移动资源"""
    def __init__(self, world, cycle):
        super().__init__("typhoon", world, cycle)
        self.duration = random.randint(5, 10)
        self.path = []
        self._generate_path(world)
        self.description = f"台风 (路径{len(self.path)}步)"

    def _generate_path(self, world):
        s = world.size
        x = random.randint(5, s-5)
        y = random.randint(5, s-5)
        steps = random.randint(4, 8)
        for _ in range(steps):
            self.path.append((x, y))
            x += random.choice([-1, 0, 1]) * random.randint(2, 5)
            y += random.choice([-1, 0, 1]) * random.randint(2, 5)
            x = max(2, min(s-3, x))
            y = max(2, min(s-3, y))

    def execute(self, world, cycle, observer=None):
        if self.phase == 0:
            self.phase = 1

        idx = cycle - self.cycle
        if idx >= len(self.path) or idx < 0:
            if idx >= self.duration:
                self.phase = 2
            return

        cx, cy = self.path[idx]
        r = 3

        # 吹散资源（移除并随机散布到周围）
        scattered = 0
        for dy in range(-r, r+1):
            for dx in range(-r, r+1):
                x, y = cx + dx, cy + dy
                cell = world.get_cell(x, y)
                if cell and cell.type == "resource":
                    rid = cell.resource_id
                    color = cell.color
                    terrain = cell.terrain
                    world.grid[y][x] = Cell(terrain)
                    # 把资源吹到附近随机位置
                    nx = x + random.randint(-r, r)
                    ny = y + random.randint(-r, r)
                    if world.can_occupy(nx, ny) and world.grid[ny][nx].type == "empty":
                        world._place_resource(nx, ny)
                        scattered += 1

        if scattered > 0 and observer:
            self.resources_destroyed += scattered


class Plague(Event):
    """瘟疫 — 削弱奇点"""
    def __init__(self, world, cycle):
        super().__init__("plague", world, cycle)
        self.duration = random.randint(10, 20)
        self.epicenter = (
            random.randint(5, world.size-5),
            random.randint(5, world.size-5)
        )
        self.spread_radius = random.randint(5, 12)
        self.description = f"瘟疫 (半径{self.spread_radius})"

    def affects_position(self, x, y):
        dist = math.sqrt((x-self.epicenter[0])**2 + (y-self.epicenter[1])**2)
        return dist <= self.spread_radius


class ResourceBloom(Event):
    """资源潮 — 资源爆发"""
    def __init__(self, world, cycle):
        super().__init__("bloom", world, cycle)
        self.duration = 1
        self.center = (
            random.randint(5, world.size-5),
            random.randint(5, world.size-5)
        )
        self.radius = random.randint(4, 8)
        self.count = random.randint(5, 15)
        self.description = f"资源潮 ({self.count}个新资源)"

    def execute(self, world, cycle, observer=None):
        cx, cy = self.center
        created = world.scatter_resources(cx, cy, self.radius, self.count)
        self.resources_created = created
        self.phase = 2

        if observer:
            observer.log_world_event(
                "自然", f"资源潮在({cx},{cy})涌现 {created}个新资源"
            )


class EventScheduler:
    """事件调度器"""

    EVENT_TYPES = ["meteor", "quake", "typhoon", "plague", "bloom"]

    def __init__(self, world):
        self.world = world
        self.active_events = []
        self.event_log = []
        self.events_triggered = 0

        # 计时器
        self.next_event_cycle = random.randint(50, 150)

    def tick(self, cycle, observer=None):
        """每周期检查事件"""
        # 执行活跃事件
        for event in self.active_events[:]:
            if event.type == "meteor":
                event.impact(self.world, cycle, observer)
            elif event.type == "quake":
                if event.phase == 0:
                    event.execute(self.world, cycle, observer)
            elif event.type == "typhoon":
                event.execute(self.world, cycle, observer)
            elif event.type == "plague":
                if event.phase == 0:
                    event.phase = 1
                    if observer:
                        x, y = event.epicenter
                        observer.log_world_event(
                            "天灾", f"瘟疫爆发 ({x},{y}) 半径{event.spread_radius}"
                        )
            elif event.type == "bloom":
                if event.phase == 0:
                    event.execute(self.world, cycle, observer)

            # 移除结束的事件
            if event.phase >= 2:
                if event.type == "plague":
                    pass  # 瘟疫需要手动移除
                else:
                    self.active_events.remove(event)
                    self.event_log.append(event.to_dict())

        # 检查是否触发新事件
        if cycle >= self.next_event_cycle:
            self._trigger_event(cycle, observer)

        # 瘟疫特殊处理（持续时间到后移除）
        for event in self.active_events[:]:
            if event.type == "plague" and cycle >= event.cycle + event.duration:
                self.active_events.remove(event)
                self.event_log.append(event.to_dict())

    def _trigger_event(self, cycle, observer=None):
        """触发新事件"""
        event_type = random.choices(
            self.EVENT_TYPES,
            weights=[0.25, 0.15, 0.2, 0.2, 0.2],
            k=1
        )[0]

        event_map = {
            "meteor": MeteorShower,
            "quake": Earthquake,
            "typhoon": Typhoon,
            "plague": Plague,
            "bloom": ResourceBloom,
        }

        event_class = event_map[event_type]
        event = event_class(self.world, cycle)
        self.active_events.append(event)
        self.events_triggered += 1

        # 调度下一个事件
        interval = random.randint(80, 200)
        self.next_event_cycle = cycle + interval

    def is_plague_zone(self, x, y):
        """检查(x,y)是否在瘟疫区"""
        for event in self.active_events:
            if event.type == "plague" and hasattr(event, 'affects_position'):
                if event.affects_position(x, y):
                    return True
        return False

    def get_stats(self):
        return {
            "total_events": self.events_triggered,
            "active": len(self.active_events),
            "next_event": self.next_event_cycle,
            "types": {},
        }
