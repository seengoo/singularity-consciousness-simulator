"""
架构基类 — 定义奇点的"思考回路"

每个架构是一个可插拔的认知处理管道：
  perceive → process → decide → memorize

我们不告诉奇点"该做什么"，只定义"它如何思考"。
行为从架构与世界的交互中涌现。
"""
from abc import ABC, abstractmethod
import random


class Architecture(ABC):
    """架构基类 — 奇点的内部处理机制"""

    def __init__(self):
        self.name = "未命名架构"
        self.description = ""
        self.version = "1.0"
        # 架构特有的参数
        self.params = {}

    @abstractmethod
    def perceive(self, local_area, own_state):
        """
        感知阶段：将原始世界数据转为感知输入
        Args:
            local_area: dict {(dx,dy): {type, color, value, resource_id}}
            own_state: dict 当前内部状态
        Returns:
            perception: 任何格式的感知数据
        """
        pass

    @abstractmethod
    def process(self, perception, internal_state):
        """
        处理阶段：感知 → 更新内部状态
        Args:
            perception: perceive()的输出
            internal_state: dict 可修改的内部状态
        Returns:
            updated_state: dict
        """
        pass

    @abstractmethod
    def decide(self, internal_state):
        """
        决策阶段：根据内部状态选择行动
        Returns:
            action: {"type": "move"|"wait"|"interact", "dx": int, "dy": int}
        """
        pass

    def memorize(self, perception, action, result, memory):
        """
        记忆阶段：更新长期记忆（可选覆写）
        """
        pass

    def init_state(self):
        """
        初始化内部状态（可选覆写）
        Returns: dict
        """
        return {}

    def describe_state(self, internal_state):
        """
        返回当前状态的可读描述（可选覆写）
        Returns: str
        """
        return ""

    def get_state_summary(self, internal_state):
        """
        返回状态摘要，用于观察面板显示
        Returns: list of (key, value, ratio) for bar display
        """
        return []

    def on_touch_resource(self, internal_state, resource_info):
        """
        碰到资源时的回调（可选覆写）
        """
        pass

    def on_touch_disaster(self, internal_state):
        """
        碰到灾难时的回调（可选覆写）
        """
        pass

    def on_bump_wall(self, internal_state):
        """
        撞墙时的回调（可选覆写）
        """
        pass
