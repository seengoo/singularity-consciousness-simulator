"""
种群系统 — 管理多奇点共存

PC = 用户的实验对象（1个）
NPC = 随机出现的其他奇点（多个）

每个奇点由自己的架构驱动，PC的架构用户可以修改。
"""
import random
import math

from core.singularity import Singularity


# NPC 预设架构
NPC_ARCHETYPES = {
    "explorer": {
        "name": "探索者",
        "color": (100, 200, 255),
        "desc": "好奇心强，喜欢探索未知区域",
        "params": {"curiosity": 0.9, "boldness": 0.7},
    },
    "gatherer": {
        "name": "采集者",
        "color": (100, 255, 100),
        "desc": "专注收集资源，围绕资源区活动",
        "params": {"resource_focus": 0.9},
    },
    "warrior": {
        "name": "战士",
        "color": (255, 80, 80),
        "desc": "攻击性强，会驱赶竞争者",
        "params": {"aggression": 0.9},
    },
    "hermit": {
        "name": "隐士",
        "color": (180, 180, 180),
        "desc": "独来独往，不求人也不理人",
        "params": {"solitude": 0.9},
    },
    "trader": {
        "name": "贸易者",
        "color": (255, 200, 80),
        "desc": "主动寻找其他奇点，交换资源",
        "params": {"social": 0.9},
    },
    "builder": {
        "name": "建造者",
        "color": (200, 150, 255),
        "desc": "喜欢群体生活，分享资源",
        "params": {"cooperation": 0.9},
    },
}


class NPCAgent:
    """NPC 奇点代理"""

    def __init__(self, singularity, archetype):
        self.singularity = singularity
        self.archetype = archetype
        self.data = NPC_ARCHETYPES[archetype]
        self.spawn_cycle = singularity.cycle

    @property
    def name(self):
        return self.data["name"]

    @property
    def color(self):
        return self.data["color"]


class Population:
    """种群管理器"""

    def __init__(self, world, observer=None):
        self.world = world
        self.observer = observer

        # PC = 用户的实验对象
        self.pc_singularity = None      # Singularity instance
        self.pc_arch = None             # Architecture instance

        # NPCs
        self.npcs = []                  # [NPCAgent, ...]

        # NPC 生成控制
        self.max_npcs = 5
        self.next_npc_cycle = 100
        self.npc_spawn_interval = 200

        # 关系网络
        self.relations = {}             # (id1, id2) -> {"type": ..., "strength": ...}

        # 统计数据
        self.stats = {
            "pc_resources": 0,
            "npc_births": 0,
            "npc_deaths": 0,
            "interactions": 0,
        }

        self._next_id = 1

    def set_pc(self, singularity, architecture):
        """设置PC奇点"""
        self.pc_singularity = singularity
        self.pc_arch = architecture
        singularity._is_pc = True
        singularity._population = self

    def spawn_npc(self, cycle, arch_class=None):
        """生成一个NPC"""
        if len(self.npcs) >= self.max_npcs:
            return None

        archetype = random.choice(list(NPC_ARCHETYPES.keys()))
        if arch_class is None:
            from architectures.random_arch import RandomArch
            arch_class = RandomArch
        npc_arch = arch_class()

        # 随机出生
        s = self.world.size
        for _ in range(50):
            x = random.randint(1, s-2)
            y = random.randint(1, s-2)
            if self.world.can_occupy(x, y):
                break

        npc_singularity = Singularity.static_create(x, y, npc_arch)
        npc_singularity.cycle = cycle
        npc_singularity._is_pc = False
        npc_singularity._npc_id = self._next_id
        npc_singularity._population = self
        self._next_id += 1

        npc_singularity._note("诞生", f"NPC#{npc_singularity._npc_id}: {archetype}")

        agent = NPCAgent(npc_singularity, archetype)
        self.npcs.append(agent)
        self.stats["npc_births"] += 1

        if self.observer:
            self.observer.log_world_event(
                "种群",
                f"NPC#{npc_singularity._npc_id} [{archetype}] 诞生于({x},{y})"
            )

        return agent

    def get_all_singularities(self):
        """返回所有活跃奇点列表"""
        result = []
        if self.pc_singularity and self.pc_singularity.alive:
            result.append(self.pc_singularity)
        for agent in self.npcs:
            if agent.singularity.alive:
                result.append(agent.singularity)
        return result

    def tick(self, cycle):
        """每周期更新"""
        # 自然生成NPC
        if cycle >= self.next_npc_cycle and len(self.npcs) < self.max_npcs:
            self.spawn_npc(cycle)
            interval = self.npc_spawn_interval + random.randint(-50, 50)
            self.next_npc_cycle = cycle + interval

        # NPC移除（死亡的）
        self.npcs = [a for a in self.npcs if a.singularity.alive]

    def get_npc_archetype(self, singularity):
        """获取奇点的NPC原型"""
        for agent in self.npcs:
            if agent.singularity is singularity:
                return agent.archetype
        return None

    def get_stats(self):
        return {
            "pc_alive": self.pc_singularity.alive if self.pc_singularity else False,
            "npc_count": len(self.npcs),
            "npc_max": self.max_npcs,
            "npc_births": self.stats["npc_births"],
            "npc_deaths": self.stats["npc_deaths"],
            "total_singularities": len(self.get_all_singularities()),
        }
