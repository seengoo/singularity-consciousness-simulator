"""
模拟引擎 v2 — 多奇点版本

管理：世界 + 天灾 + 种群(PC+NPCs) + 观察者
"""
import random
import os

from core.world import World
from core.singularity import Singularity
from core.observer import Observer
from core.events import EventScheduler
from core.population import Population
from reports.run_report import generate_run_report, save_run_report


class SimEngine:
    """模拟引擎"""

    ARCHITECTURES = {}

    @classmethod
    def register_architecture(cls, name, arch_class):
        cls.ARCHITECTURES[name] = arch_class

    @classmethod
    def get_architecture_names(cls):
        return list(cls.ARCHITECTURES.keys())

    @classmethod
    def create_composed_architecture(cls, name, module_specs):
        """
        从模块规格创建组合架构
        module_specs: [(module_id, weight), ...]
        例: [("curiosity", 0.8), ("territory", 0.9), ("aggressive", 0.5)]
        """
        from architectures.component_system import (
            ALL_DRIVES, ALL_ACTIONS, ALL_MEMORIES,
            ComposedArchitecture
        )
        arch = ComposedArchitecture(name)
        for module_id, weight in module_specs:
            module_class = (
                ALL_DRIVES.get(module_id) or
                ALL_ACTIONS.get(module_id) or
                ALL_MEMORIES.get(module_id)
            )
            if module_class:
                arch.add_module(module_class(weight))
        # 注册到引擎
        cls.ARCHITECTURES[name] = lambda: arch
        return name

    def __init__(self, world_size=60, max_cycles=8000):
        self.world_size = world_size
        self.max_cycles = max_cycles

        self.world = None
        self.observer = None
        self.events = None
        self.population = None
        self.pc_arch = None

        self.is_running = False
        self.run_completed = False
        self.last_report = ""
        self._seed = 0

    def init_run(self, arch_name, seed=None, extra_npcs=1):
        """初始化运行（PC + NPCs）"""
        self._seed = seed or random.randint(0, 999999)
        random.seed(self._seed)

        # 世界
        self.world = World(self.world_size, seed=self._seed)

        # 观察者
        self.observer = Observer()
        self.observer.log_world_event = self._log_world_event

        # 天灾引擎
        self.events = EventScheduler(self.world)
        self.world.active_events = self.events.active_events

        # 创建PC
        arch_class = self.ARCHITECTURES.get(arch_name)
        if not arch_class:
            raise ValueError(f"未知架构: {arch_name}")
        self.pc_arch = arch_class()
        pc = Singularity(self.world, self.pc_arch)
        pc.set_observer(self.observer)

        # 种群系统
        self.population = Population(self.world, self.observer)
        self.population.set_pc(pc, self.pc_arch)

        # 生成初始NPC
        for _ in range(extra_npcs):
            from architectures.random_arch import RandomArch
            self.population.spawn_npc(0, RandomArch)

        self.is_running = True
        self.run_completed = False
        self.last_report = ""

        self.observer.record_state_snapshot(pc)

    @property
    def singularity(self):
        """兼容旧接口：返回PC奇点"""
        return self.population.pc_singularity if self.population else None

    def step(self):
        """执行一个模拟步骤"""
        if not self.is_running:
            return

        # 世界更新
        self.world.tick()

        # 天灾引擎
        self.events.tick(self.world.cycle, self.observer)

        # 种群更新（NPC生成等）
        self.population.tick(self.world.cycle)

        # 所有活跃奇点各自走一步
        for singular in self.population.get_all_singularities():
            if singular.alive and singular.cycle < self.max_cycles:
                singular.step(self.world)

        # 检查结束条件
        self._check_end_condition()

    def _check_end_condition(self):
        """检查是否需要结束"""
        pc = self.population.pc_singularity

        # PC死亡 → 结束
        if not pc.alive:
            self._finish_run()
            return

        # PC达到最大周期 → 结束
        if pc.cycle >= self.max_cycles:
            self._finish_run()
            return

        # 所有奇点都死亡 → 结束
        all_dead = all(not s.alive for s in self.population.get_all_singularities())
        if all_dead:
            self._finish_run()

    def _finish_run(self):
        """结束并生成报告"""
        self.is_running = False
        self.run_completed = True

        pc = self.population.pc_singularity

        report_data, report_text = generate_run_report(
            self.observer, pc, self.world,
            run_id=f"{pc.arch.name}_{self._seed}"
        )

        # ★ 意识涌现评估
        from reports.consciousness_assessment import ConsciousnessAssessment, format_assessment_report
        assessor = ConsciousnessAssessment(self.observer, pc, self.world, self.population)
        assessment = assessor.assess()
        report_data["consciousness_assessment"] = assessment
        report_text += "\n" + format_assessment_report(assessment)

        # 添加种群信息到报告
        report_data["population"] = {
            "npc_births": self.population.stats["npc_births"],
            "total_npcs": len(self.population.npcs),
            "npc_archetypes": [
                {"name": a.name, "spawn_cycle": a.spawn_cycle,
                 "alive": a.singularity.alive}
                for a in self.population.npcs
            ],
        }

        os.makedirs("data", exist_ok=True)
        save_run_report(report_data, "data")

        # 简短控制台输出
        status = "存活" if pc.alive else "死亡"
        npc_info = f"NPCs:{len(self.population.npcs)}"

        print(f"  [结束] {pc.arch.name} | 周期:{pc.cycle} | "
              f"状态:{status} | 能量:{pc.energy:.2f} | {npc_info}")

        self.last_report = report_text + "\n" + self._population_summary()

    def _population_summary(self):
        """种群摘要"""
        lines = ["", "  [种群] NPC统计:"]
        for a in self.population.npcs:
            s = a.singularity
            status = "存活" if s.alive else "死亡"
            lines.append(f"    {a.name} [{a.archetype}] 周期:{s.cycle} 状态:{status}")
        return "\n".join(lines)

    def _log_world_event(self, category, description):
        """记录世界事件到观察者"""
        if self.observer:
            self.observer._mark_interesting(self.world.cycle, f"[{category}] {description}")

    def reset(self):
        self.is_running = False
        self.run_completed = False
        self.last_report = ""
        self.world = None
        self.observer = None
        self.events = None
        self.population = None

    def stop(self):
        self.is_running = False
