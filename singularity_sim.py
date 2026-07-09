#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
奇点模拟器 v2.0 — 设计世界，观察意识的萌芽
===========================================
理论来源：森谷智创

你可以设计不同的世界结构，观察奇点如何在其中演化。
每个奇点拥有独特的性格，在有限世界中吞并模式、
构建内部模型，最终成长或死亡。

世界类型:
  random  随机散布的模式
  cluster 模式集群（大陆型）
  gradient 平滑渐变
  ring    环形分布

运行:
  python singularity_sim.py                    # 交互模式
  python singularity_sim.py batch [次数]       # 批量模式
  python singularity_sim.py world [类型]       # 指定世界类型

按键 (交互):
  q 退出  Space暂停  s单步  +/-速度  r重置  w切换世界
"""

import random
import time
import os
import sys
import math
from collections import deque

# ============ 配置 ============
W = 36
H = 16
MAX_NODES = 80
INIT_ENERGY = 60.0
MOVE_COST = 0.5
ENTROPY_BASE = 0.08
MAX_CYCLES = 3000

# ============ 符号 ============
EMPTY = chr(183)
PATS = [chr(9617), chr(9618), chr(9619), chr(9672), chr(9670)]
AGENT_SYM = chr(10022)


def val_sym(v):
    if v < 0.2: return PATS[0]
    elif v < 0.4: return PATS[1]
    elif v < 0.6: return PATS[2]
    elif v < 0.8: return PATS[3]
    else: return PATS[4]


def sym_val(s):
    if s == EMPTY: return None
    try:
        idx = PATS.index(s)
        v = idx * 0.25 + 0.125
        v += random.uniform(-0.03, 0.03)
        return max(0, min(1, v))
    except ValueError:
        return None


# ================================================================
# 世界工厂
# ================================================================
class World:
    """有限世界 - 支持多种结构"""

    TYPES = ["random", "cluster", "gradient", "ring"]

    def __init__(self, wtype="random", seed=None):
        if seed is not None:
            random.seed(seed)
        self.w, self.h = W, H
        self.wtype = wtype
        self.grid = [[EMPTY for _ in range(self.w)] for _ in range(self.h)]
        self._generate()

    def _generate(self):
        if self.wtype == "random":
            self._gen_random()
        elif self.wtype == "cluster":
            self._gen_cluster()
        elif self.wtype == "gradient":
            self._gen_gradient()
        elif self.wtype == "ring":
            self._gen_ring()
        else:
            self._gen_random()

    def _gen_random(self):
        """随机散布 - 控制组"""
        n = self.w * self.h // 3
        cells = [(x, y) for x in range(self.w) for y in range(self.h)]
        for x, y in random.sample(cells, min(n, len(cells))):
            self.grid[y][x] = val_sym(random.random())

    def _gen_cluster(self):
        """模式集群 - 模拟"大陆"结构"""
        n_clusters = random.randint(3, 5)
        centers = []
        for _ in range(n_clusters):
            cx = random.randint(3, self.w - 4)
            cy = random.randint(3, self.h - 4)
            val = random.random()
            radius = random.uniform(2.5, 5.5)
            density = random.uniform(0.5, 0.9)
            centers.append((cx, cy, val, radius, density))

        for y in range(self.h):
            for x in range(self.w):
                for cx, cy, val, radius, density in centers:
                    dist = ((x - cx)**2 + (y - cy)**2)**0.5
                    if dist < radius and random.random() < density * (1 - dist/radius):
                        noise = random.uniform(-0.12, 0.12)
                        v = max(0.0, min(1.0, val + noise))
                        self.grid[y][x] = val_sym(v)
                        break

    def _gen_gradient(self):
        """平滑渐变 - 从左上到右下"""
        for y in range(self.h):
            for x in range(self.w):
                if random.random() < 0.35:
                    base = (x / self.w + y / self.h) / 2
                    noise = random.uniform(-0.15, 0.15)
                    v = max(0, min(1, base + noise))
                    self.grid[y][x] = val_sym(v)

    def _gen_ring(self):
        """环形分布 - 中间空心"""
        cx, cy = self.w / 2, self.h / 2
        for y in range(self.h):
            for x in range(self.w):
                dist = ((x - cx)**2 + (y - cy)**2)**0.5
                if 2 < dist < 7 and random.random() < 0.6:
                    angle = math.atan2(y - cy, x - cx)
                    v = (math.sin(angle * 3) + 1) / 2
                    noise = random.uniform(-0.1, 0.1)
                    v = max(0, min(1, v + noise))
                    self.grid[y][x] = val_sym(v)
                elif dist <= 2 and random.random() < 0.3:
                    self.grid[y][x] = val_sym(random.random())

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return sym_val(self.grid[y][x])
        return None

    def consume(self, x, y):
        if not (0 <= x < self.w and 0 <= y < self.h):
            return None
        s = self.grid[y][x]
        if s == EMPTY: return None
        self.grid[y][x] = EMPTY
        return sym_val(s)

    def remaining(self):
        return sum(1 for r in self.grid for c in r if c != EMPTY)

    def regrow(self, chance=0.00002):
        for y in range(self.h):
            for x in range(self.w):
                if self.grid[y][x] == EMPTY and random.random() < chance:
                    self.grid[y][x] = val_sym(random.random())


# ================================================================
# 奇点
# ================================================================
class Singularity:
    """
    奇点 — 从"1"开始，在吞并中构建自我。
    """

    def __init__(self, world):
        # 初始位置
        self.x = world.w // 2 + random.randint(-2, 2)
        self.y = world.h // 2 + random.randint(-2, 2)
        self.x = max(0, min(world.w - 1, self.x))
        self.y = max(0, min(world.h - 1, self.y))

        # 性格
        self.curiosity = random.uniform(0.2, 0.9)
        self.caution = random.uniform(0.2, 0.9)
        self.metabolism = random.uniform(0.6, 1.2)

        base_energy = INIT_ENERGY * (0.8 + self.metabolism * 0.4)
        self.energy = base_energy

        # 内部结构: {nid: {val, strength, age, conn: {nid: weight}}}
        self.nodes = {0: {"val": 0.5, "strength": 1.0, "age": 0, "conn": {}}}
        self.next_id = 1

        # 状态
        self.alive = True
        self.cycle = 0
        self.boredom = 0
        self.last_event = "诞生"

        # 统计
        self.assim_n = 0
        self.grow_n = 0
        self.fail_n = 0

        self.dir = random.choice([(1,0),(-1,0),(0,1),(0,-1)])

    def sense(self, world):
        res = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0: continue
                v = world.get(self.x + dx, self.y + dy)
                if v is not None: res.append(v)
        return res

    def tension(self, percepts):
        if not percepts: return 0.0
        vals = [n["val"] for n in self.nodes.values()]
        if not vals: return 0.5
        return sum(min(abs(p - v) for v in vals) for p in percepts) / len(percepts)

    def swallow(self, val):
        """吞并：同化 / 生长 / 冒险"""
        best = min(self.nodes, key=lambda n: abs(self.nodes[n]["val"] - val))
        diff = abs(self.nodes[best]["val"] - val)
        sim = 1.0 - diff
        novelty = 1.0 - sim

        cap_room = 1.0 - len(self.nodes) / MAX_NODES
        grow_tend = novelty * self.curiosity * (0.3 + cap_room * 0.7)
        grow_tend *= (1.0 + self.boredom / 80)
        grow_tend = min(0.95, grow_tend)

        risk_tend = novelty * (1.0 - self.caution) * (0.1 + self.boredom / 60)
        risk_tend = min(0.7, risk_tend)

        # 同化
        if sim > 0.9:
            old = self.nodes[best]["val"]
            self.nodes[best]["val"] = old * 0.85 + val * 0.15
            self.nodes[best]["strength"] = min(2.0, self.nodes[best].get("strength", 1.0) + 0.03)
            gain = 0.5 + sim * 0.5
            self.energy += gain
            self.assim_n += 1
            self.boredom += 1.5
            self.last_event = f"同#{best}: {old:.2f}->{self.nodes[best]['val']:.2f} +{gain:.1f}E"
            return True

        # 生长
        if random.random() < grow_tend and self.next_id < MAX_NODES:
            nid = self.next_id
            self.next_id += 1
            self.nodes[nid] = {"val": val, "strength": 0.8, "age": 0, "conn": {best: sim}}
            self.nodes[best]["conn"][nid] = sim
            gain = 1.5 + novelty * 4.0 + self.boredom / 20
            self.energy += gain
            self.grow_n += 1
            self.boredom = max(0, self.boredom - 15)
            self.last_event = f"长#{nid}: {val:.2f} +{gain:.1f}E"
            return True

        # 冒险
        if random.random() < risk_tend and self.next_id < MAX_NODES:
            risk_r = 2.0 + novelty * 10.0
            odds = max(0.1, 0.5 - self.caution * 0.3 + self.boredom / 100)
            if random.random() < odds:
                nid = self.next_id
                self.next_id += 1
                self.nodes[nid] = {"val": val, "strength": 1.2, "age": 0, "conn": {}}
                self.energy += risk_r
                self.grow_n += 1
                self.boredom = max(0, self.boredom - 25)
                self.last_event = f"冒险#{nid}: {val:.2f} +{risk_r:.1f}E"
                return True
            else:
                cost = risk_r * 0.7
                self.energy -= cost
                self.fail_n += 1
                self.boredom += 3
                self.last_event = f"败:{val:.2f} -{cost:.1f}E"
                return False

        # 保底
        self.nodes[best]["val"] = self.nodes[best]["val"] * 0.9 + val * 0.1
        gain = 0.2 + sim * 0.3
        self.energy += gain
        self.assim_n += 1
        self.boredom += 2
        self.last_event = f"强同#{best}: +{gain:.1f}E"
        return True

    def move(self, world, dx, dy):
        nx, ny = self.x + dx, self.y + dy
        if 0 <= nx < world.w and 0 <= ny < world.h:
            self.x, self.y = nx, ny
            self.energy -= MOVE_COST * (0.8 + self.metabolism * 0.4)
            return True
        return False

    def step(self, world):
        if not self.alive: return
        self.cycle += 1

        # 节点老化
        for n in self.nodes.values():
            n["age"] += 1

        # 感知
        percepts = self.sense(world)
        t = self.tension(percepts)

        # 决策
        starving = self.energy < 15
        if percepts and (t > 0.02 or starving) and self.energy > 3:
            if starving:
                target = random.choice(percepts)
            elif self.boredom > 50:
                vals = [n["val"] for n in self.nodes.values()]
                target = max(percepts, key=lambda p: min(abs(p - v) for v in vals))
            else:
                target = random.choice(percepts)

            ok = self.swallow(target)
            if ok:
                world.consume(self.x, self.y)
            else:
                self.move(world, *self.dir)
        else:
            self.energy -= 0.1
            if self.cycle % 2 == 0:
                if random.random() < self.curiosity * 0.2:
                    self.dir = random.choice([(1,0),(-1,0),(0,1),(0,-1)])
                self.move(world, *self.dir)

        # 代谢
        self.energy -= ENTROPY_BASE * len(self.nodes) * (0.7 + self.metabolism * 0.6)

        # 无聊衰减
        self.boredom = max(0, self.boredom - 0.3 - self.curiosity * 0.2)

        # 死亡
        if self.energy <= 0:
            self.alive = False
            self.last_event = f"死:{self.cycle}周期 {len(self.nodes)}节点"

    def get_stats(self):
        v = [n["val"] for n in self.nodes.values()]
        if not v:
            return (f"X死{self.cycle}周{len(self.nodes)}节")
        avg = sum(v)/len(v)
        bb = chr(9608) * min(10, max(0, int(self.boredom/6))) + chr(9617) * max(0, 10 - max(0, int(self.boredom/6)))
        return (f"E{self.energy:4.1f}|周{self.cycle:4d}|节{len(self.nodes):2d}|"
                f"好{self.curiosity:.2f}谨{self.caution:.2f}|"
                f"同{self.assim_n}长{self.grow_n}败{self.fail_n}|"
                f"厌[{bb}]")


# ================================================================
# 显示
# ================================================================
def render(agent, world, paused=False, speed=1.0, mode="full"):
    os.system("cls" if os.name == "nt" else "clear")
    status = "暂停" if paused else f"x{speed:.1f}"

    # 标题
    print(f"奇点模拟器 v2.0 | 世界:{world.wtype} | 状态:{status}")
    print("-" * (W + 22))

    # 网格 + 侧边统计
    stats_right = [
        agent.get_stats(),
        f"世界: {world.remaining()} 模式",
        f"活: {'是' if agent.alive else '否'}",
        "",
        f"好奇心: {agent.curiosity:.2f}",
        f"谨慎度: {agent.caution:.2f}",
        f"代谢率: {agent.metabolism:.2f}",
        "",
        f"同化: {agent.assim_n}",
        f"生长: {agent.grow_n}",
        f"失败: {agent.fail_n}",
        f"节点: {len(agent.nodes)}",
    ]

    for y in range(world.h):
        line = "|"
        for x in range(world.w):
            if x == agent.x and y == agent.y:
                line += AGENT_SYM if agent.alive else "x"
            else:
                line += world.grid[y][x]
        line += "|"
        if y < len(stats_right):
            line += " " + stats_right[y]
        print(line)

    print("-" * (W + 22))
    print(f"  {agent.last_event}")

    # 内部结构
    if agent.nodes:
        vals = [n["val"] for n in agent.nodes.values()]
        sr = [n.get("strength", 1.0) for n in agent.nodes.values()]

        # 节点值
        b1 = "".join(chr(9608) if v > 0.8 else chr(9619) if v > 0.6
                      else chr(9618) if v > 0.4 else chr(9617) if v > 0.2 else " "
                     for v in vals[:40])
        print(f"  值: [{b1}]")

        # 节点强度
        b2 = "".join(chr(9608) if s > 1.2 else chr(9619) if s > 0.8
                      else chr(9618) if s > 0.5 else chr(9617) if s > 0.2 else " "
                     for s in sr[:40])
        print(f"  力: [{b2}]")

        # 连接图 (显示最强的几条)
        if len(agent.nodes) <= 12:
            edges = []
            for nid, n in agent.nodes.items():
                for cid, w in n["conn"].items():
                    if cid > nid:
                        edges.append((nid, cid, w))
            if edges:
                edges.sort(key=lambda e: -e[2])
                n = min(3, len(edges))
                conn_str = " | ".join(f"#{e[0]}-#{e[1]}:{e[2]:.2f}" for e in edges[:n])
                print(f"  连接: {conn_str}")

    print("-" * (W + 22))
    print("  [Space]暂停 [s]步进 [+]快 [-]慢 [r]重置 [w]换世界 [q]退出")
    print(f"  使用 seed={getattr(agent, '_seed', '?')} 可复现")


# ================================================================
# 交互运行
# ================================================================
def run_interactive(seed=None, world_type="random"):
    if seed is None:
        seed = random.randint(0, 99999)

    random.seed(seed)
    world = World(world_type, seed=seed) if world_type else World("random", seed=seed)
    agent = Singularity(world)
    agent._seed = seed

    paused = False
    speed = 1.0
    frame = 0

    print("=" * 50)
    print(f"  奇点 #{seed}")
    print(f"  世界: {world.wtype}")
    print(f"  性格: 好奇={agent.curiosity:.2f} 谨慎={agent.caution:.2f}")
    print("=" * 50)
    time.sleep(1)

    import msvcrt as _m
    def getk():
        if _m.kbhit():
            b = _m.getch()
            if b == b'\xe0':  # arrow/function keys
                _m.getch()
                return None
            return b.decode("ascii", errors="ignore").lower()
        return None

    while agent.alive and frame < MAX_CYCLES:
        frame += 1
        key = getk()

        if key == "q": break
        elif key == " ": paused = not paused
        elif key == "s": paused = True  # step once
        elif key in ("+", "="): speed = min(5, speed + 0.5)
        elif key in ("-", "_"): speed = max(0.25, speed - 0.5)
        elif key == "r":
            seed = random.randint(0, 99999)
            random.seed(seed)
            world = World(world_type, seed=seed)
            agent = Singularity(world)
            agent._seed = seed
            frame = 0
            paused = False
        elif key == "w":
            types = World.TYPES
            idx = (types.index(world_type) + 1) % len(types)
            world_type = types[idx]
            seed = random.randint(0, 99999)
            random.seed(seed)
            world = World(world_type, seed=seed)
            agent = Singularity(world)
            agent._seed = seed
            frame = 0
            paused = False
            print(f"  切换到世界: {world_type}")
            time.sleep(0.5)

        if not paused:
            agent.step(world)
            world.regrow()
            if frame % max(1, int(2 / speed)) == 0:
                render(agent, world, paused, speed)
                time.sleep(max(0.03, 0.12 / speed))
        elif key == "s":
            agent.step(world)
            render(agent, world, paused, speed)

    render(agent, world, paused, speed)
    print(f"\n  结束: {agent.last_event}")
    print(f"  同化 {agent.assim_n} | 生长 {agent.grow_n} | 失败 {agent.fail_n}")


# ================================================================
# 批量运行
# ================================================================
def run_batch(n=30, world_type="random"):
    print(f"世界类型: {world_type}")
    print("=" * 50)
    rs = []
    for i in range(n):
        s = random.randint(0, 99999)
        random.seed(s)
        w = World(world_type, seed=s) if world_type else World("random", seed=s)
        a = Singularity(w)
        for _ in range(MAX_CYCLES):
            if not a.alive: break
            a.step(w)
            w.regrow()

        sym = "[L]" if a.alive else "[D]"
        print(f"  {i+1:2d}/{n} s={s:5d} {sym} "
              f"周{a.cycle:4d} 节{len(a.nodes):2d} "
              f"好{a.curiosity:.2f} 谨{a.caution:.2f} "
              f"同{a.assim_n}长{a.grow_n}败{a.fail_n} "
              f"{a.last_event}")
        rs.append((s, a))

    lived = sum(1 for _, a in rs if a.alive)
    died = sum(1 for _, a in rs if not a.alive)
    print(f"\n  总:{n} 存活:{lived} 死亡:{died}")
    if rs:
        avg_n = sum(len(a.nodes) for _, a in rs) / n
        max_n = max(len(a.nodes) for _, a in rs)
        print(f"  均节点:{avg_n:.1f} 最大:{max_n}")
        hc = [(s,a) for s,a in rs if a.curiosity > 0.6]
        lc = [(s,a) for s,a in rs if a.curiosity <= 0.6]
        if hc: print(f"  高好奇(>{0.6}):{len(hc)}只 死亡率{sum(1 for _,a in hc if not a.alive)/len(hc):.0%}")
        if lc: print(f"  低好奇(<={0.6}):{len(lc)}只 死亡率{sum(1 for _,a in lc if not a.alive)/len(lc):.0%}")

    return rs


# ================================================================
# 多世界对比
# ================================================================
def compare_worlds(n=20):
    for wt in World.TYPES:
        print(f"\n{'='*50}")
        print(f"  世界类型: {wt}")
        print('='*50)
        rs = run_batch(n, wt)
        lived = sum(1 for _, a in rs if a.alive)
        avg_n = sum(len(a.nodes) for _, a in rs) / n if rs else 0
        print(f"  -> 存活:{lived}/{n} 均节点:{avg_n:.1f}")


# ================================================================
# 入口
# ================================================================
if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "interactive"

    if mode == "batch":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        wt = sys.argv[3] if len(sys.argv) > 3 else "random"
        run_batch(n, wt)
    elif mode == "compare":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 15
        compare_worlds(n)
    elif mode in ("i", "interactive"):
        wt = sys.argv[2] if len(sys.argv) > 2 else "random"
        s = int(sys.argv[3]) if len(sys.argv) > 3 else None
        run_interactive(s, wt)
    else:
        print(f"用法:")
        print(f"  {sys.argv[0]} interactive [world_type] [seed]")
        print(f"  {sys.argv[0]} batch [次数] [world_type]")
        print(f"  {sys.argv[0]} compare [次数]")
        print(f"  世界类型: {', '.join(World.TYPES)}")
