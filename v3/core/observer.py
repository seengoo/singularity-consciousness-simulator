"""
观察系统 — 记录奇点的每一个行为、状态变化、有趣事件

提供：
  1. 实时追踪（当前周期的状态）
  2. 事件日志（何时发生了什么）
  3. 状态快照历史（用于分析趋势）
  4. 行为模式识别
  5. 报告数据聚合
"""
import time
import json
import math
from collections import defaultdict, Counter


class Observer:
    """全知的观察者 — 记录一切但不干涉"""

    def __init__(self):
        self.reset()

    def reset(self):
        """重置所有记录"""
        self.start_time = time.time()

        # 事件流
        self.events = []          # [(cycle, type, data), ...]
        self.event_counters = Counter()

        # 状态快照 (用于时间序列分析)
        self.state_snapshots = []  # [{cycle, x, y, internal_state, ...}]

        # 行为统计
        self.action_counts = Counter()
        self.resource_encounters = Counter()
        self.disaster_count = 0
        self.wall_bumps = 0
        self.wait_count = 0

        # 有趣事件标记
        self.interesting_events = []
        self.interesting_keywords = [
            "首次", "发现", "循环", "模式", "规律",
            "反复", "边界", "探索", "回避", "偏好",
        ]

        # 探索统计
        self.explored_positions = set()
        self.position_history = []  # 位置时间序列

        # 行为模式
        self.recent_actions = []  # 滑窗用于模式检测
        self.pattern_window = 15

        # 特征提取
        self.behavior_signature = {}

    def record_event(self, singularity, action_type, action_detail, result):
        """记录一个事件"""
        cycle = singularity.cycle
        state_snapshot = dict(singularity.internal_state) if singularity.internal_state else {}

        event = {
            "cycle": cycle,
            "action_type": action_type,
            "action": self._sanitize(action_detail),
            "result": self._sanitize(result),
            "pos": (singularity.x, singularity.y),
            "state": self._sanitize(state_snapshot),
        }

        self.events.append(event)
        self.event_counters[action_type] += 1
        self.recent_actions.append(action_type)
        if len(self.recent_actions) > self.pattern_window:
            self.recent_actions.pop(0)

        # 分类统计 — 按结果类型追踪
        result_type = result.get("type", "none") if result else "none"
        self.action_counts[result_type] += 1
        if result_type == "got_resource":
            r = result.get("encountered", {})
            if r:
                self.resource_encounters[r.get("name", "unknown")] += 1
        elif result_type == "disaster":
            self.disaster_count += 1
        elif result_type == "bump_wall":
            self.wall_bumps += 1
        elif result_type == "wait":
            self.wait_count += 1

        # 位置跟踪
        self.position_history.append((cycle, singularity.x, singularity.y))
        self.explored_positions.add((singularity.x, singularity.y))

        # 检测"有趣"事件
        self._detect_interesting(singularity, action_type, result)

    def record_state_snapshot(self, singularity):
        """记录内部状态快照"""
        snapshot = {
            "cycle": singularity.cycle,
            "x": singularity.x,
            "y": singularity.y,
            "alive": singularity.alive,
            "state": dict(singularity.internal_state) if singularity.internal_state else {},
            "n_visited": len(self.explored_positions),
            "n_encounters": len(singularity.memory["encounters"]),
        }
        self.state_snapshots.append(snapshot)

    def _detect_interesting(self, singularity, action_type, result):
        """检测行为是否'有趣'"""
        result_type = result.get("type", "none") if result else "none"
        cycle = singularity.cycle

        # 标记的冷却机制 — 防止同一事件连续刷屏
        last_marked = getattr(self, "_last_marked_cycle", 0)
        if cycle - last_marked < 100:  # 至少间隔100周期
            return

        # 1. 首次发现每种资源
        if result_type == "got_resource":
            r = result.get("encountered", {})
            if r:
                resource_name = r.get("name")
                if resource_name and self.resource_encounters.get(resource_name) == 1:
                    self._mark_interesting(cycle, f"首次发现 {resource_name}！")
                    self._last_marked_cycle = cycle

        # 2. 边界探索行为
        if result_type == "bump_wall":
            # 只在边界行为频繁时标记一次
            if not getattr(self, "_wall_noted", False):
                wall_rate = self.wall_bumps / max(1, cycle)
                if wall_rate > 0.2 and self.wall_bumps >= 20:
                    self._mark_interesting(cycle,
                        f"边界探索行为 ({self.wall_bumps}次撞墙)")
                    self._last_marked_cycle = cycle
                    self._wall_noted = True

        # 3. 灾难遭遇
        if result_type == "disaster":
            if not getattr(self, "_disaster_noted", False) and self.disaster_count >= 10:
                self._mark_interesting(cycle,
                    f"多次遭遇灾难 ({self.disaster_count}次)")
                self._last_marked_cycle = cycle
                self._disaster_noted = True

        # 4. 探索里程碑
        if cycle > 0 and cycle % 1000 == 0:
            explored = len(self.explored_positions)
            self._mark_interesting(cycle,
                f"探索里程碑: 到达 {explored} 个不同位置")
            self._last_marked_cycle = cycle

    def _mark_interesting(self, cycle, description):
        self.interesting_events.append({
            "cycle": cycle,
            "description": description,
        })

    def _recent_events(self, event_type, n):
        """返回最近n个周期中某种事件的数量"""
        recent = [e for e in self.events if e["cycle"] > max(0, (e["cycle"] if e["cycle"] else 0) - n)]
        return [e for e in recent if e.get("action_type") == event_type]

    def _sanitize(self, obj):
        """确保对象可序列化"""
        if isinstance(obj, dict):
            return {k: self._sanitize(v) for k, v in obj.items()
                    if not k.startswith("_") and not callable(v)}
        elif isinstance(obj, set):
            return list(obj)[:20]
        elif isinstance(obj, (list, tuple)):
            return [self._sanitize(x) for x in obj[:50]]
        return obj

    def get_current_stats(self):
        """获取当前统计数据"""
        return {
            "events_total": len(self.events),
            "actions": dict(self.action_counts),
            "resources": dict(self.resource_encounters),
            "disasters": self.disaster_count,
            "wall_bumps": self.wall_bumps,
            "area_explored": len(self.explored_positions),
            "interesting_count": len(self.interesting_events),
        }

    def get_behavior_summary(self):
        """行为摘要"""
        total = sum(self.action_counts.values()) or 1
        return {
            "explore_ratio": self.action_counts.get("got_resource", 0) / total,
            "disaster_ratio": self.disaster_count / total,
            "wall_bump_ratio": self.wall_bumps / total,
            "wait_ratio": self.wait_count / total,
            "area_percent": len(self.explored_positions) / (50*50) * 100,
        }

    def export_json(self, filepath):
        """导出观察数据为JSON"""
        data = {
            "duration_sec": time.time() - self.start_time,
            "events": self.events,
            "interesting": self.interesting_events,
            "action_counts": dict(self.action_counts),
            "resource_encounters": dict(self.resource_encounters),
            "behavior": self.get_behavior_summary(),
            "explored_positions": list(self.explored_positions),
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
