"""
世界 — 足迹系统：每个格子记录被谁走过、多少次、被谁占领
"""
import random
import math

RESOURCE_TYPES = {
    0: {"name": "赤焰", "color": (255, 80, 80), "energy": 0.8},
    1: {"name": "深水", "color": (60, 140, 255), "energy": 0.6},
    2: {"name": "翡翠", "color": (70, 220, 100), "energy": 0.7},
    3: {"name": "玄金", "color": (255, 210, 50), "energy": 1.0},
    4: {"name": "紫晶", "color": (190, 70, 230), "energy": 0.5},
}

TERRAIN_NAMES = {0: "荒原", 1: "绿洲", 2: "裂谷", 3: "高地"}
TERRAIN_COLORS = {
    0: (15, 12, 8),  1: (10, 25, 12),  2: (8, 8, 18),  3: (18, 16, 10),
}


class Cell:
    __slots__ = ("type", "color", "value", "resource_id", "terrain", "energy",
                 "visit_count", "last_visitor", "last_visit_cycle", "stain_color")

    def __init__(self, terrain=0):
        self.type = "empty"
        self.color = (0, 0, 0)
        self.value = 0.0
        self.resource_id = None
        self.terrain = terrain
        self.energy = 0.0
        # 足迹
        self.visit_count = 0          # 被走过的次数
        self.last_visitor = None      # "pc" / "npc_1" / None
        self.last_visit_cycle = 0     # 最后一次被踩的周期
        self.stain_color = None       # 留下的颜色 (经过颜色混合)


class World:
    """世界 — 每个格子有记忆"""

    def __init__(self, size=60, seed=None):
        self.size = size
        self.seed = seed or random.randint(0, 999999)
        random.seed(self.seed)
        self.cycle = 0

        self.grid = [[Cell() for _ in range(size)] for _ in range(size)]
        self.resource_counts = {rid: 0 for rid in RESOURCE_TYPES}
        self.total_resources = 0
        self.terrain_counts = {0: size*size, 1: 0, 2: 0, 3: 0}

        # 领地
        self.claimed_by = {}  # (x,y) -> singularity_id

        self._init_terrain()
        self._init_resources(0.12)

    def _init_terrain(self):
        s = self.size
        n_patches = random.randint(6, 10)
        for _ in range(n_patches):
            cx, cy = random.randint(0, s-1), random.randint(0, s-1)
            ttype = random.choice([1, 2, 3])
            radius = random.uniform(3, 10)
            for y in range(max(0, cy-int(radius)), min(s, cy+int(radius)+1)):
                for x in range(max(0, cx-int(radius)), min(s, cx+int(radius)+1)):
                    dist = math.sqrt((x-cx)**2 + (y-cy)**2)
                    if dist < radius and random.random() < 0.6:
                        self.grid[y][x].terrain = ttype
                        self.terrain_counts[ttype] = self.terrain_counts.get(ttype, 0) + 1
                        self.terrain_counts[0] = max(0, self.terrain_counts[0] - 1)

    def _init_resources(self, density):
        n = int(self.size * self.size * density)
        cells = [(x, y) for x in range(self.size) for y in range(self.size)]
        for x, y in random.sample(cells, min(n, len(cells))):
            self._place_resource(x, y)

    def _place_resource(self, x, y):
        if not (0 <= x < self.size and 0 <= y < self.size):
            return False
        if self.grid[y][x].type != "empty":
            return False
        rid = random.choices(
            list(RESOURCE_TYPES.keys()),
            weights=[0.3, 0.2, 0.25, 0.1, 0.15], k=1
        )[0]
        rt = RESOURCE_TYPES[rid]
        c = self.grid[y][x]
        c.type = "resource"
        c.color = rt["color"]
        c.value = random.uniform(0.3, 1.0)
        c.resource_id = rid
        c.energy = rt["energy"]
        self.resource_counts[rid] = self.resource_counts.get(rid, 0) + 1
        self.total_resources += 1
        return True

    def tick(self):
        """世界时间推进"""
        self.cycle += 1
        s = self.size

        # 资源涌现
        spawn_rate = 0.003 + 0.001 * math.sin(self.cycle * 0.015)
        if random.random() < spawn_rate:
            x = random.randint(0, s-1)
            y = random.randint(0, s-1)
            if self.grid[y][x].type == "empty":
                terrain = self.grid[y][x].terrain
                bonus = {0: 1.0, 1: 2.5, 2: 0.5, 3: 1.5}.get(terrain, 1.0)
                if random.random() < bonus * 0.3:
                    self._place_resource(x, y)

        # 资源消失
        if random.random() < 0.0003:
            x, y = random.randint(0, s-1), random.randint(0, s-1)
            c = self.grid[y][x]
            if c.type == "resource":
                self._clear_cell(x, y)

        # 足迹褪色：长时间没人走的格子足迹减淡
        if self.cycle % 100 == 0:
            for y in range(s):
                for x in range(s):
                    c = self.grid[y][x]
                    if c.visit_count > 0 and self.cycle - c.last_visit_cycle > 500:
                        c.visit_count = max(0, c.visit_count - 1)
                        if c.visit_count == 0:
                            c.stain_color = None
                            c.last_visitor = None

    def _clear_cell(self, x, y):
        """清空格子（保留足迹）"""
        c = self.grid[y][x]
        if c.resource_id is not None:
            self.resource_counts[c.resource_id] = max(0, self.resource_counts.get(c.resource_id, 0) - 1)
        self.total_resources = max(0, self.total_resources - 1)
        terrain = c.terrain
        # 保留足迹
        vc, lv, lvc, stain = c.visit_count, c.last_visitor, c.last_visit_cycle, c.stain_color
        new_c = Cell(terrain)
        new_c.visit_count = vc
        new_c.last_visitor = lv
        new_c.last_visit_cycle = lvc
        new_c.stain_color = stain
        self.grid[y][x] = new_c
        self.claimed_by.pop((x, y), None)

    # ─── 足迹系统 ───

    def step_on(self, x, y, visitor_id, visitor_color):
        """奇点踩到一个格子——留下足迹"""
        if not (0 <= x < self.size and 0 <= y < self.size):
            return
        c = self.grid[y][x]
        c.visit_count += 1
        c.last_visitor = visitor_id
        c.last_visit_cycle = self.cycle

        # 足迹颜色混合：奇点颜色 + 已有痕迹
        if c.stain_color is None:
            c.stain_color = visitor_color
        else:
            # 混合颜色（逐渐加深偏向访问者）
            r = int(c.stain_color[0] * 0.7 + visitor_color[0] * 0.3)
            g = int(c.stain_color[1] * 0.7 + visitor_color[1] * 0.3)
            b = int(c.stain_color[2] * 0.7 + visitor_color[2] * 0.3)
            c.stain_color = (min(255, r), min(255, g), min(255, b))

        # 占领标记
        if c.type == "resource":
            self.claimed_by[(x, y)] = visitor_id

    # ─── 资源 ───

    def get_cell(self, x, y):
        if 0 <= x < self.size and 0 <= y < self.size:
            return self.grid[y][x]
        return None

    def consume_resource(self, x, y):
        cell = self.get_cell(x, y)
        if cell and cell.type == "resource":
            info = {
                "color": cell.color,
                "value": cell.value,
                "resource_id": cell.resource_id,
                "name": RESOURCE_TYPES[cell.resource_id]["name"],
                "energy": cell.energy,
            }
            self._clear_cell(x, y)
            return info
        return None

    def can_occupy(self, x, y):
        return self.get_cell(x, y) is not None

    def get_local_area(self, cx, cy, radius):
        local = {}
        for dy in range(-radius, radius+1):
            for dx in range(-radius, radius+1):
                if dx == 0 and dy == 0:
                    continue
                x, y = cx + dx, cy + dy
                cell = self.get_cell(x, y)
                if cell:
                    local[(dx, dy)] = {
                        "type": cell.type,
                        "color": cell.color,
                        "value": cell.value,
                        "resource_id": cell.resource_id,
                        "terrain": cell.terrain,
                        "energy": cell.energy,
                        "visit_count": cell.visit_count,
                        "stain_color": cell.stain_color,
                        "last_visitor": cell.last_visitor,
                        "claimed": self.is_claimed(x, y),
                        "claimed_by_id": self.claimed_by_id(x, y),
                    }
        return local

    # ─── 领地 ───

    def claim_cell(self, x, y, sid):
        if 0 <= x < self.size and 0 <= y < self.size:
            self.claimed_by[(x, y)] = sid
            return True
        return False

    def unclaim_cell(self, x, y):
        self.claimed_by.pop((x, y), None)

    def is_claimed(self, x, y):
        return (x, y) in self.claimed_by

    def claimed_by_id(self, x, y):
        return self.claimed_by.get((x, y))

    def get_claimed_count(self, sid):
        return sum(1 for s in self.claimed_by.values() if s == sid)

    def get_claim_color(self, x, y):
        sid = self.claimed_by.get((x, y))
        if sid is None:
            return None
        if sid == "pc":
            return (180, 180, 255)
        try:
            h = hash(str(sid)) & 0xFFFFFF
            return ((h >> 16) & 0xFF, (h >> 8) & 0xFF, h & 0xFF)
        except:
            return (150, 150, 150)

    # ─── 天灾 ───

    def change_terrain(self, cx, cy, radius, new_terrain):
        """改变地形"""
        for dy in range(-radius, radius+1):
            for dx in range(-radius, radius+1):
                x, y = cx + dx, cy + dy
                cell = self.get_cell(x, y)
                if cell:
                    old = cell.terrain
                    cell.terrain = new_terrain
                    self.terrain_counts[old] = max(0, self.terrain_counts.get(old, 0) - 1)
                    self.terrain_counts[new_terrain] = self.terrain_counts.get(new_terrain, 0) + 1

    def destroy_area(self, cx, cy, radius):
        destroyed = 0
        for dy in range(-radius, radius+1):
            for dx in range(-radius, radius+1):
                x, y = cx + dx, cy + dy
                cell = self.get_cell(x, y)
                if cell and cell.type == "resource":
                    self._clear_cell(x, y)
                    destroyed += 1
                # 天灾改变足迹颜色（红色调）
                if cell and cell.visit_count > 0:
                    r = min(255, cell.stain_color[0] + 60) if cell.stain_color else 200
                    g = max(0, cell.stain_color[1] - 40) if cell.stain_color else 50
                    b = max(0, cell.stain_color[2] - 40) if cell.stain_color else 50
                    cell.stain_color = (r, g, b)
        return destroyed

    def scatter_resources(self, cx, cy, radius, count):
        placed = 0
        for _ in range(count * 3):
            x = cx + random.randint(-radius, radius)
            y = cy + random.randint(-radius, radius)
            if self._place_resource(x, y):
                placed += 1
                if placed >= count:
                    break
        return placed

    def get_stats(self):
        total_visits = sum(c.visit_count for row in self.grid for c in row)
        return {
            "cycle": self.cycle,
            "total_resources": self.total_resources,
            "by_type": dict(self.resource_counts),
            "total_visits": total_visits,
        }
