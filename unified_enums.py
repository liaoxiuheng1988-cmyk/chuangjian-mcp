"""
统一枚举定义 v1.0
Unified Enums — 解决各模块间枚举命名冲突

所有发现系统模块应导入此文件的枚举，不再各自定义

使用方式：
from unified_enums import Dimension, SignalStrength, WindowPhase, ...
"""

from enum import Enum


# ============== 维度枚举 ==============

class Dimension(Enum):
    """信号/机会维度"""
    TECHNOLOGY = "技术"
    BUSINESS_MODEL = "商业模式"
    USER_PAIN = "用户痛点"
    POLICY = "政策"
    CROSS_INDUSTRY = "跨界"
    TIME_WINDOW = "时间窗口"
    RESOURCE = "资源"
    MARKET = "市场"


# ============== 信号强度枚举 ==============

class SignalStrength(Enum):
    """信号强度"""
    HIGH = "🔴"
    MEDIUM = "🟡"
    LOW = "🟢"

    @classmethod
    def from_str(cls, s: str):
        """从字符串转换"""
        mapping = {
            "高": cls.HIGH,
            "中": cls.MEDIUM,
            "低": cls.LOW,
            "high": cls.HIGH,
            "medium": cls.MEDIUM,
            "low": cls.LOW,
        }
        return mapping.get(s, cls.MEDIUM)


# ============== 窗口阶段枚举 ==============

class WindowPhase(Enum):
    """机会窗口阶段"""
    PREMATURE = "窗口未到"
    OPTIMAL = "最佳进入期"
    GROWING = "成长期窗口"
    MATURE = "成熟期窗口"
    CLOSING = "窗口关闭"


# ============== 机会阶段枚举 ==============

class OpportunityStage(Enum):
    """机会所处阶段"""
    EMBRYONIC = "萌芽期"
    GROWING = "成长期"
    MATURING = "成熟期"
    SATURATED = "饱和期"


# ============== 机会类型枚举 ==============

class OpportunityType(Enum):
    """机会类型"""
    DIRECT = "直接机会"
    INFRASTRUCTURE = "基础设施机会"
    SERVICE = "服务机会"
    DOWNSTREAM = "下游机会"
    DERIVATIVE = "衍生机会"
    CASCADE = "连锁机会"
    INVERSE = "逆向机会"


# ============== 项目类型枚举 ==============

class ProjectType(Enum):
    """项目类型判断"""
    DIRECT = "值得做"
    SHOVEL = "卖铲子"
    HYBRID = "混合型"


# ============== 优先级枚举 ==============

class PriorityLevel(Enum):
    """优先级"""
    P1 = 1
    P2 = 2
    P3 = 3


# ============== 验证结果枚举 ==============

class ValidationResult(Enum):
    """验证结果"""
    PASS = "通过"
    FAIL = "否决"
    INCONCLUSIVE = "不确定"
    NEED_MORE_DATA = "需更多数据"


# ============== 执行状态枚举 ==============

class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = "待执行"
    RUNNING = "执行中"
    COMPLETED = "已完成"
    FAILED = "失败"
    ABANDONED = "已放弃"
    SKIPPED = "已跳过"


# ============== 生态节点类型枚举 ==============

class EcosystemNodeType(Enum):
    """生态系统节点类型"""
    # 按层级分
    CORE = "核心层"
    INFRASTRUCTURE = "基础设施层"
    SERVICE = "服务层"
    USER = "用户层"
    DERIVATIVE = "衍生层"
    COMPETITOR = "竞品层"
    UPSTREAM = "上游层"
    DOWNSTREAM = "下游层"
    # 按价值链分
    PROVIDER = "供应方"
    INTEGRATOR = "整合方"
    FACILITATOR = "撮合方"
    ENABLER = "赋能方"


# ============== 自进化状态枚举 ==============

class EvolutionState(Enum):
    """自进化系统状态"""
    LEARNING = "学习中"
    STABLE = "稳定"
    ADAPTING = "适应中"
    CALIBRATING = "校准中"


# ============== 任务状态枚举 ==============

class TaskStatus(Enum):
    """任务执行状态"""
    PENDING = "⬜"
    IN_PROGRESS = "🔄"
    DONE = "✅"
    BLOCKED = "🚫"
    CANCELLED = "❌"


# ============== 任务优先级枚举 ==============

class TaskPriority(Enum):
    """任务优先级"""
    P0 = "P0-紧急"
    P1 = "P1-重要"
    P2 = "P2-一般"
    P3 = "P3-低"


# ============== 告警级别枚举 ==============

class AlertLevel(Enum):
    """告警级别"""
    INFO = "信息"
    WARNING = "警告"
    CRITICAL = "严重"


# ============== 策略阶段枚举 ==============

class StrategyPhase(Enum):
    """策略阶段"""
    ENTRY = "进入期"
    PENETRATION = "渗透期"
    EXPANSION = "扩展期"
    DEFENSE = "防御期"


# ============== 验证阶段枚举 ==============

class ValidationPhase(Enum):
    """验证阶段"""
    ASSUMPTION = "假设构建"
    LIGHT = "轻量级验证(72h)"
    DEEP = "深度验证(7-30d)"
    DECISION = "决策点"


# ============== 检查点决策枚举 ==============

class CheckpointDecision(Enum):
    """检查点决策"""
    PROCEED = "PROCEED"
    PIVOT = "PIVOT"
    ABORT = "ABORT"
    EXPAND = "EXPAND"


# ============== 辅助函数 ==============

import json
from pathlib import Path


def dimension_from_str(s: str) -> Dimension:
    """从字符串获取Dimension枚举"""
    mapping = {
        "技术": Dimension.TECHNOLOGY,
        " TECHNOLOGY": Dimension.TECHNOLOGY,
        "商业模式": Dimension.BUSINESS_MODEL,
        " BUSINESS_MODEL": Dimension.BUSINESS_MODEL,
        "用户痛点": Dimension.USER_PAIN,
        " USER_PAIN": Dimension.USER_PAIN,
        "政策": Dimension.POLICY,
        " POLICY": Dimension.POLICY,
        "跨界": Dimension.CROSS_INDUSTRY,
        " CROSS_INDUSTRY": Dimension.CROSS_INDUSTRY,
        "时间窗口": Dimension.TIME_WINDOW,
        " TIME_WINDOW": Dimension.TIME_WINDOW,
    }
    return mapping.get(s, Dimension.TECHNOLOGY)
