#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
奇点 Demo v0.3 - 意识诞生实验
=========================================
理论来源：森谷智创
实现：Claude Code + DeepSeek

核心假说：
  一个白板系统 + 开放性指令 + 吞并操作 = 意识可能涌现

v0.3 改进：
  - 每个奇点有随机"性格"（好奇心/谨慎度/效率）
  - 生存压力加大，死亡成为可能
  - 世界有资源枯竭和恢复机制
  - 路径依赖性更明显

启动指令：
  "你活了，世界很大，去做你想做的事"

用法：
  python singularity_demo.py batch [次数]
  python singularity_demo.py single [seed]
"""

import random
import time
import os
import sys

# ============ 配置 ============
GRID_W = 35
GRID_H = 16
MAX_NODES = 60
INIT_ENERGY = 60.0
MOVE_COST = 0.5
ENTROPY_BASE = 0.08
REFRESH_MS = 0.12
MAX_CYCLES = 3000
PATTERN_COUNT = None  # auto: w * h // 3

# ============ 符号 ============
EMPTY = chr(183)
PATS = [chr(9617), chr(9618), chr(9619), chr(9672), chr(9670)]
AGENT_SYM = chr(10022)
DEAD_SYM = chr(10023)


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
        return idx * 0.25 + 0.125
    except ValueError:
        return None


class World:
    """有限网格世界"""

    def __init__(self):
        self.w, self.h = GRID_W, GRID_H
        self.grid = [[EMPTY for _ in range(self.w)] for _ in range(self.h)]
        n = PATTERN_COUNT if PATTERN_COUNT else self.w * self.h // 3
        cells = [(x, y) for x in range(self.w) for y in range(self.h)]
        for x, y in random.sample(cells, min(n, len(cells))):
            self.grid[y][x] = val_sym(random.random())

    def get_val(self, x, y):
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

    def count_rem(self):
        return sum(1 for r in self.grid for c in r if c != EMPTY)

    # 资源缓慢再生
    def regrow(self, chance=0.00002):
        for y in range(self.h):
            for x in range(self.w):
                if self.grid[y][x] == EMPTY and random.random() < chance:
                    self.grid[y][x] = val_sym(random.random())


class Singularity:
    """奇点 - v0.3 每个个体都有独特性格"""

    def __init__(self, world):
        self.x = world.w // 2 + random.randint(-3, 3)
        self.y = world.h // 2 + random.randint(-3, 3)
        self.x = max(0, min(world.w - 1, self.x))
        self.y = max(0, min(world.h - 1, self.y))

        # === 性格特质（每次启动都不同）===
        self.curiosity = random.uniform(0.2, 0.95)     # 探索欲
        self.caution = random.uniform(0.2, 0.95)       # 谨慎度
        self.metabolism = random.uniform(0.6, 1.2)     # 代谢率

        # 性格决定初始能量
        base_energy = INIT_ENERGY * (0.8 + self.metabolism * 0.4)
        self.energy = base_energy

        # === 内部结构：从"1"开始 ===
        self.nodes = {
            0: {"val": 0.5, "age": 0, "strength": 1.0, "energy_track": [], "conn": {}}
        }
        self.next_id = 1

        # === 生命 ===
        self.alive = True
        self.cycle = 0

        # === 统计 ===
        self.assim_n = 0
        self.grow_n = 0
        self.fail_n = 0
        self.boredom = 0
        self.last_event = "诞生"

        # 方向
        self.dir = random.choice([(1,0),(-1,0),(0,1),(0,-1)])

    def perceive(self, world):
        res = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0: continue
                v = world.get_val(self.x + dx, self.y + dy)
                if v is not None: res.append(v)
        return res

    def tension(self, percepts):
        """张力 = 感知与自我的平均差异"""
        if not percepts: return 0.0
        vals = [n["val"] for n in self.nodes.values()]
        return sum(min(abs(p - v) for v in vals) for p in percepts) / len(percepts)

    def swallow(self, val):
        """吞并操作 v0.3

        行为受性格(好奇/谨慎)状态调节。
        """
        best = min(self.nodes, key=lambda n: abs(self.nodes[n]["val"] - val))
        diff = abs(self.nodes[best]["val"] - val)
        sim = 1.0 - diff

        # 生长倾向 = 新奇性 * 好奇心 * 容量空间 * 无聊因子
        cap_room = 1.0 - len(self.nodes) / MAX_NODES
        novelty = 1.0 - sim
        grow_tend = novelty * self.curiosity * (0.3 + cap_room * 0.7)
        grow_tend = grow_tend * (1.0 + self.boredom / 80)
        grow_tend = min(0.95, grow_tend)

        # 冒险倾向 (失败风险高)
        risk_tend = novelty * (1.0 - self.caution) * (0.1 + self.boredom / 60)
        risk_tend = min(0.7, risk_tend)

        if sim > 0.9 and not (sim > 0.95 and self.boredom > 60 and random.random() < 0.2):
            # === 高度匹配 -> 同化 ===
            old = self.nodes[best]["val"]
            self.nodes[best]["val"] = old * 0.85 + val * 0.15
            self.nodes[best]["strength"] = min(2.0, self.nodes[best].get("strength", 1.0) + 0.03)
            gain = 0.5 + sim * 0.5
            self.energy += gain
            self.assim_n += 1
            self.boredom += 1.5
            self.last_event = f"同#{best}: {old:.2f}->{self.nodes[best]['val']:.2f} +{gain:.1f}E"
            return True

        if random.random() < grow_tend and self.next_id < MAX_NODES:
            # === 生长：创建新节点 ===
            nid = self.next_id
            self.next_id += 1
            self.nodes[nid] = {"val": val, "age": 0, "strength": 0.8, "conn": {best: sim}}
            if best != nid:
                self.nodes[best]["conn"][nid] = sim
            gain = 1.5 + novelty * 4.0 + self.boredom / 20
            self.energy += gain
            self.grow_n += 1
            self.boredom = max(0, self.boredom - 15)
            self.last_event = f"长#{nid}: {val:.2f} +{gain:.1f}E"
            return True

        if random.random() < risk_tend and self.next_id < MAX_NODES:
            # === 冒险：高风险高回报 ===
            risk_r = 2.0 + (1.0 - sim) * 10.0
            odds = max(0.1, 0.5 - self.caution * 0.3 + self.boredom / 100)
            if random.random() < odds:
                nid = self.next_id
                self.next_id += 1
                self.nodes[nid] = {"val": val, "age": 0, "strength": 1.2, "conn": {}}
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

        # === 保底：勉强同化（低收益）===
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
            cost = MOVE_COST * (0.8 + self.metabolism * 0.4)
            self.energy -= cost
            return True
        return False

    def step(self, world):
        if not self.alive:
            return
        self.cycle += 1

        # 1. 节点老化
        for n in self.nodes.values():
            n["age"] += 1

        # 2. 感知
        percepts = self.perceive(world)
        t = self.tension(percepts)

        # 3. 决策
        starving = self.energy < 15
        can_act = percepts and (t > 0.02 or starving) and self.energy > 5

        if can_act:
            # 饥饿时优先找最近模式; 无聊时找最陌生模式
            if starving:
                # 饥不择食
                target = random.choice(percepts)
            elif self.boredom > 40:
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
            # 探索
            if self.cycle % 2 == 0:
                # 好奇心决定探索方向变化频率
                if random.random() < self.curiosity * 0.3 or starving:
                    self.dir = random.choice([(1,0),(-1,0),(0,1),(0,-1)])
                self.move(world, *self.dir)

        # 4. 代谢熵增
        ent_cost = ENTROPY_BASE * len(self.nodes) * (0.7 + self.metabolism * 0.6)
        self.energy -= ent_cost

        # 5. 无聊衰减
        self.boredom = max(0, self.boredom - 0.3 - self.curiosity * 0.2)

        # 6. 能量过低时开始自噬（弱节点被回收）
        if self.energy < 5 and len(self.nodes) > 1:
            weakest = min(self.nodes, key=lambda n: self.nodes[n].get("strength", 0))
            if self.nodes[weakest].get("strength", 1.0) < 0.5:
                salvage = 3.0 + random.random() * 3.0
                self.energy += salvage
                del self.nodes[weakest]
                self.last_event = f"自噬#{weakest} +{salvage:.1f}E"
                self.grow_n -= 1  # 不算增长

        # 7. 死亡检查
        if self.energy <= 0:
            self.alive = False
            self.last_event = f"死:{self.cycle}周期, {len(self.nodes)}节点"

    def status(self):
        if not self.alive:
            return (f"X死|周{self.cycle}|节{len(self.nodes)}|"
                    f"同{self.assim_n}长{self.grow_n}败{self.fail_n}")
        v = [n["val"] for n in self.nodes.values()]
        avg = sum(v)/len(v) if v else 0
        bb = chr(9608) * min(15, int(self.boredom/4)) + chr(9617) * max(0, 15-int(self.boredom/4))
        c = f"C{self.curiosity:.2f}"
        cv = f"V{self.caution:.2f}"
        return (f"E{self.energy:4.1f}|周{self.cycle:4d}|"
                f"节{len(self.nodes):2d}|{c}{cv}|"
                f"同{self.assim_n}长{self.grow_n}败{self.fail_n}|"
                f"厌[{bb}]")


def render(world, agent):
    os.system("cls" if os.name == "nt" else "clear")
    print("+" + "-" * world.w + "+")
    for y in range(world.h):
        line = "|"
        for x in range(world.w):
            if agent.alive and x == agent.x and y == agent.y:
                line += AGENT_SYM
            elif not agent.alive and x == agent.x and y == agent.y:
                line += DEAD_SYM
            else:
                line += world.grid[y][x]
        line += "|"
        print(line)
    print("+" + "-" * world.w + "+")
    print(f"  {agent.status()}")
    print(f"  +-- {agent.last_event}")
    print(f"  剩余:{world.count_rem()}")
    if agent.alive and agent.nodes:
        v = [n["val"] for n in agent.nodes.values()]
        vis = "".join(chr(9608) if x > 0.75 else chr(9619) if x > 0.6 else chr(9618) if x > 0.4 else chr(9617) if x > 0.2 else " " for x in v[:40])
        print(f"  内部:[{vis}]({len(v)}节)")


def run(seed, silent=False):
    random.seed(seed)
    world = World()
    agent = Singularity(world)

    if not silent:
        print("=" * 50)
        print("  你活了，世界很大，去做你想做的事。")
        print(f"  性格: 好奇={agent.curiosity:.2f} 谨慎={agent.caution:.2f} 代谢={agent.metabolism:.2f}")
        print("=" * 50)
        time.sleep(1.5)

    for _ in range(MAX_CYCLES):
        if not agent.alive: break
        agent.step(world)
        # 几乎无资源再生 - 世界是有穷的
        world.regrow(0.00002)
        if not silent and agent.cycle % 2 == 0:
            render(world, agent)
            time.sleep(REFRESH_MS)

    v = [n["val"] for n in agent.nodes.values()]
    if not v:
        return {"seed": seed, "cycles": agent.cycle, "nodes": 0,
                "alive": False, "assim": 0, "grow": 0, "fail": 0,
                "diversity": 0, "curiosity": agent.curiosity,
                "caution": agent.caution, "event": "无结构"}
    uniq = len(set(round(x, 1) for x in v))
    div = uniq / len(v) if v else 0
    return {"seed": seed, "cycles": agent.cycle, "nodes": len(agent.nodes),
            "alive": agent.alive, "assim": agent.assim_n,
            "grow": agent.grow_n, "fail": agent.fail_n,
            "diversity": div, "curiosity": agent.curiosity,
            "caution": agent.caution, "event": agent.last_event}


def batch(n=20):
    print("=" * 50)
    print("  [BATCH] 奇点批量实验")
    print("=" * 50)
    rs = []
    for i in range(n):
        s = random.randint(0, 99999)
        r = run(s, silent=True)
        rs.append(r)
        sym = "[L]" if r["alive"] else "[D]"
        print(f"  {i+1:2d}/{n} s={s:5d} {sym} "
              f"周{r['cycles']:4d} 节{r['nodes']:2d} "
              f"好{r['curiosity']:.2f} 谨{r['caution']:.2f} "
              f"同{r['assim']}长{r['grow']}败{r['fail']} "
              f"{r['event']}")

    print("\n" + "=" * 50)
    print("  [SUMMARY]")
    print("=" * 50)
    lived = sum(1 for r in rs if r["alive"])
    died = sum(1 for r in rs if not r["alive"])
    print(f"  总: {n} | 存活: {lived} | 死亡: {died}")
    if rs:
        print(f"  平均寿命: {sum(r['cycles'] for r in rs)/n:.0f}")
        print(f"  平均节点: {sum(r['nodes'] for r in rs)/n:.1f}")
        print(f"  最大节点: {max(r['nodes'] for r in rs)}")
        print(f"  多样性:   {sum(r['diversity'] for r in rs)/n:.0%}")

    # 按性格分组看趋势
    high_c = [r for r in rs if r["curiosity"] > 0.6]
    low_c = [r for r in rs if r["curiosity"] <= 0.6]
    if high_c and low_c:
        print(f"\n  高好奇(>{0.6}): {len(high_c)}只, "
              f"均节点{sum(r['nodes'] for r in high_c)/len(high_c):.1f}, "
              f"死亡率{sum(1 for r in high_c if not r['alive'])/len(high_c):.0%}")
        print(f"  低好奇(<={0.6}): {len(low_c)}只, "
              f"均节点{sum(r['nodes'] for r in low_c)/len(low_c):.1f}, "
              f"死亡率{sum(1 for r in low_c if not r['alive'])/len(low_c):.0%}")


if __name__ == "__main__":
    m = sys.argv[1] if len(sys.argv) > 1 else "batch"
    if m == "batch":
        c = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        batch(c)
    elif m == "single":
        s = int(sys.argv[2]) if len(sys.argv) > 2 else random.randint(0, 99999)
        print(f"seed={s}")
        run(s, silent=False)
    else:
        print(f"py {sys.argv[0]} [batch|single] [num/seed]")
