"""
自进化核心模块 v1.0
Self Evolution Core — L8.5 发现系统自进化核心模块

核心职责：
1. 统一管理所有学习回路
2. 维度权重动态调整
3. 关键词库自动扩展
4. KillChain 阈值自适应
5. 窗口预测回溯校准
6. 连锁模式置信度学习

使用方式：
python3 self_evolution.py --status    # 查看自进化状态
python3 self_evolution.py --learn    # 模拟一次学习
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import sys

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))
from unified_enums import Dimension, SignalStrength


# ============== 自进化状态枚举 ==============

from unified_enums import EvolutionState


# ============== 数据模型 ==============

@dataclass
class DimensionWeight:
    """维度权重"""
    dimension: str
    base_weight: float = 1.0
    current_weight: float = 1.0
    accuracy_history: list = field(default_factory=list)
    adjustment_count: int = 0

    def update_weight(self, new_accuracy: float):
        """根据准确率更新权重"""
        if not self.accuracy_history:
            self.accuracy_history.append(new_accuracy)
            return

        # 简单移动平均
        avg_accuracy = sum(self.accuracy_history[-5:]) / min(len(self.accuracy_history), 5)

        if avg_accuracy >= 0.7:
            # 高准确率 → 提高权重
            self.current_weight = min(2.0, self.current_weight * 1.05)
        elif avg_accuracy <= 0.4:
            # 低准确率 → 降低权重
            self.current_weight = max(0.5, self.current_weight * 0.95)

        self.accuracy_history.append(new_accuracy)
        self.adjustment_count += 1

    def get_weight(self) -> float:
        return self.current_weight


@dataclass
class KillChainThreshold:
    """KillChain 动态阈值"""
    check_name: str
    base_threshold: float
    current_threshold: float
    success_cases: int = 0
    failure_cases: int = 0

    def adjust(self, was_correct_abandon: bool):
        """
        根据放弃判断的正确性调整阈值

        was_correct_abandon: True = 正确放弃了（后来确实失败了）
                            False = 错误放弃了（后来竟然成功了）
        """
        if was_correct_abandon:
            self.failure_cases += 1
            # 保持阈值或稍微提高（更保守）
            self.current_threshold = min(self.base_threshold * 1.2, self.current_threshold + 0.05)
        else:
            self.success_cases += 1
            # 错误放弃 → 应该提高放弃门槛
            self.current_threshold = max(self.base_threshold * 0.7, self.current_threshold - 0.2)


@dataclass
class WindowPredictionRecord:
    """窗口预测记录"""
    opportunity_name: str
    predicted_days: int
    actual_days: int = 0
    phase: str = ""
    recorded_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    closed: bool = False

    @property
    def error_rate(self) -> float:
        if self.actual_days == 0:
            return 0.0
        return abs(self.predicted_days - self.actual_days) / self.predicted_days


@dataclass
class PatternConfidence:
    """连锁模式置信度"""
    pattern_type: str
    base_confidence: float
    current_confidence: float
    success_count: int = 0
    failure_count: int = 0

    def learn(self, success: bool):
        """从执行结果学习"""
        if success:
            self.success_count += 1
            self.current_confidence = min(0.95, self.current_confidence + 0.05)
        else:
            self.failure_count += 1
            self.current_confidence = max(0.3, self.current_confidence - 0.1)


# ============== 动态关键词库 ==============

class DynamicKeywordLibrary:
    """
    动态关键词库

    支持从新发现中提取趋势词并追加到对应维度
    """

    DEFAULT_LIBRARY: Dict[str, List[str]] = {
        "技术": ["LLM", "API", "模型", "开源", "AI", "GPT", "Agent", "RAG", "向量", "Embedding", "微调", "推理", "训练", "部署", "云服务", "GPU", "算力"],
        "商业模式": ["订阅", "付费", "免费", "增值", "SaaS", "API调用", "token", "按量计费", "年费", "代理", "分销", "渠道", "获客", "转化", "留存"],
        "用户痛点": ["效率", "成本", "门槛", "学习曲线", "集成", "迁移", "稳定性", "可靠性", "安全性", "隐私", "合规", "定制", "自动化", "批量", "批处理"],
        "政策": ["监管", "合规", "牌照", "数据安全", "隐私保护", "AI监管", "算法备案", "行业标准", "扶持", "补贴", "税收优惠", "试点", "开放"],
        "跨界": ["组合", "融合", "嫁接", "复制", "迁移", "适配", "集成", "整合", "生态", "平台化", "标准化"],
        "时间窗口": ["窗口期", "先发", "早期", "红利期", "窗口关闭", "最佳进入期", "成长期", "成熟期", "饱和"],
        "资源": ["人脉", "资金", "技术", "数据", "渠道", "团队", "经验", "资源整合", "杠杆", "BD"],
        "市场": ["蓝海", "红海", "细分", "垂直", "下沉", "出海", "全球化", "本地化", "细分市场", " niche", "赛道", "风口"]
    }

    MAX_KEYWORDS_PER_DIMENSION = 100

    def __init__(self):
        self.library: Dict[str, List[str]] = {k: list(v) for k, v in self.DEFAULT_LIBRARY.items()}
        self.trending_tracker: Dict[str, int] = {}  # 追踪新词出现频率

    def add_keywords(self, dimension: str, keywords: List[str]):
        """追加新关键词到指定维度"""
        if dimension not in self.library:
            self.library[dimension] = []

        for kw in keywords:
            kw_clean = kw.strip()
            if kw_clean and kw_clean not in self.library[dimension]:
                self.library[dimension].append(kw_clean)
                # 追踪趋势
                self.trending_tracker[kw_clean] = self.trending_tracker.get(kw_clean, 0) + 1

        # 控制膨胀：淘汰低频词
        self._prune_if_needed(dimension)

    def _prune_if_needed(self, dimension: str):
        """如果关键词过多，淘汰低频词"""
        if len(self.library[dimension]) <= self.MAX_KEYWORDS_PER_DIMENSION:
            return

        # 按出现频率排序，保留高频词
        sorted_words = sorted(
            self.library[dimension],
            key=lambda w: self.trending_tracker.get(w, 0),
            reverse=True
        )
        self.library[dimension] = sorted_words[:self.MAX_KEYWORDS_PER_DIMENSION]

    def extract_from_signals(self, signals: List[Dict]) -> Dict[str, List[str]]:
        """从信号列表中提取趋势关键词"""
        result: Dict[str, List[str]] = {}

        for sig in signals:
            # 从标题和证据中提词
            text = f"{sig.get('title', '')} {sig.get('evidence', '')}"

            for dim, keywords in self.library.items():
                matched = [kw for kw in keywords if kw in text]
                if matched:
                    if dim not in result:
                        result[dim] = []
                    result[dim].extend(matched)

        return result

    def get_keywords(self, dimension: str, n: int = 20) -> List[str]:
        """获取指定维度的关键词"""
        if dimension not in self.library:
            return []
        # 返回按趋势频率排序的词
        return sorted(
            self.library[dimension],
            key=lambda w: self.trending_tracker.get(w, 0),
            reverse=True
        )[:n]

    def to_dict(self) -> dict:
        return {
            "library": self.library,
            "trending": self.trending_tracker
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'DynamicKeywordLibrary':
        lib = cls()
        lib.library = data.get("library", cls.DEFAULT_LIBRARY)
        lib.trending_tracker = data.get("trending", {})
        return lib


# ============== 自进化核心管理器 ==============

class SelfEvolutionManager:
    """
    自进化核心管理器

    统一管理所有学习回路，协调各模块的自进化
    """

    def __init__(self, storage_path: str = None):
        if storage_path is None:
            storage_dir = Path("/home/admin1/aiagent/代理知识库/我的/opportunity_discovery")
            storage_dir.mkdir(parents=True, exist_ok=True)
            storage_path = str(storage_dir / "self_evolution_state.json")

        self.storage_path = storage_path

        # 维度权重
        self.dimension_weights: Dict[str, DimensionWeight] = {
            dim.value: DimensionWeight(dimension=dim.value, base_weight=1.0, current_weight=1.0)
            for dim in Dimension
        }

        # KillChain 动态阈值
        self.killchain_thresholds: Dict[str, KillChainThreshold] = {
            "score_min": KillChainThreshold("score_min", base_threshold=4.5, current_threshold=4.5),
            "window_min": KillChainThreshold("window_min", base_threshold=7, current_threshold=7),
            "validation_failures": KillChainThreshold("validation_failures", base_threshold=3, current_threshold=3),
        }

        # 窗口预测记录
        self.window_predictions: List[WindowPredictionRecord] = []

        # 连锁模式置信度
        self.pattern_confidence: Dict[str, PatternConfidence] = {
            "infrastructure": PatternConfidence("infrastructure", 0.7, 0.7),
            "service": PatternConfidence("service", 0.8, 0.8),
            "cascade": PatternConfidence("cascade", 0.7, 0.7),
            "downstream": PatternConfidence("downstream", 0.85, 0.85),
            "inverse": PatternConfidence("inverse", 0.65, 0.65),
        }

        # 关键词库
        self.keyword_library = DynamicKeywordLibrary()

        # 系统状态
        self.state = EvolutionState.STABLE
        self.last_learning_at = ""

        # 加载已有状态
        self.load_state()

    # ============== 核心学习接口 ==============

    def learn_from_execution(
        self,
        opportunity_name: str,
        outcome: str,
        deviation: str,
        lesson: str,
        dimension_hints: List[str] = None,
        pattern_type: str = None
    ):
        """
        从执行结果中学习

        这是主要的入口方法，被 execution_feedback.py 调用
        """
        self.last_learning_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.state = EvolutionState.LEARNING

        is_success = "成功" in outcome

        # 1. 学习维度准确率
        if dimension_hints:
            for dim in dimension_hints:
                self._learn_dimension_accuracy(dim, is_success)

        # 2. 学习连锁模式置信度
        if pattern_type and pattern_type in self.pattern_confidence:
            self.pattern_confidence[pattern_type].learn(is_success)

        # 3. 学习 KillChain 阈值
        # 如果是失败且有教训，说明之前不该放弃
        if not is_success and lesson:
            self._adjust_killchain_from_lesson(lesson)

        self.state = EvolutionState.STABLE

        # 记录权重历史快照（用于趋势图）
        self.record_weights_history()

        self.save_state()

    def _learn_dimension_accuracy(self, dimension: str, success: bool):
        """学习某个维度的预测准确率"""
        if dimension not in self.dimension_weights:
            return

        # 简单：正确=1.0，错误=0.0
        accuracy = 1.0 if success else 0.0
        self.dimension_weights[dimension].update_weight(accuracy)

    def _adjust_killchain_from_lesson(self, lesson: str):
        """根据教训调整 KillChain 阈值"""
        # 如果教训提到"评分过高被放弃"之类的，说明阈值可能设高了
        if any(kw in lesson for kw in ["评分", "分数", "score", "threshold"]):
            # 降低 score_min 阈值
            self.killchain_thresholds["score_min"].current_threshold = max(
                self.killchain_thresholds["score_min"].base_threshold * 0.7,
                self.killchain_thresholds["score_min"].current_threshold - 0.2
            )

    def record_window_actual(self, opportunity_name: str, predicted_days: int, actual_days: int = None, closed: bool = False):
        """
        记录机会窗口的实际结果，用于校准预测

        如果窗口关闭了但还没到预测天数，说明预测偏乐观
        如果窗口关闭时实际比预测长，说明预测偏保守
        """
        record = WindowPredictionRecord(
            opportunity_name=opportunity_name,
            predicted_days=predicted_days,
            actual_days=actual_days or 0,
            closed=closed,
            recorded_at=datetime.now().strftime("%Y-%m-%d")
        )

        # 如果已关闭，计算误差
        if closed and actual_days:
            error_rate = record.error_rate
            if error_rate > 0.3:
                self.state = EvolutionState.CALIBRATING
                # 误差过大，触发调整
                self._calibrate_window_weights(error_rate)

        self.window_predictions.append(record)
        # 保留最近100条记录
        self.window_predictions = self.window_predictions[-100:]
        self.save_state()

    def _calibrate_window_weights(self, error_rate: float):
        """
        根据窗口预测误差校准市场指标权重

        这是一个简化实现，实际应该回溯分析哪个指标出了问题
        """
        # 简单策略：如果预测普遍偏乐观，适当减少窗口期估计
        if error_rate > 0.3:
            self.state = EvolutionState.CALIBRATING
            # 下次预测时多减几天作为保守估计
            self._conservative_adjustment = getattr(self, '_conservative_adjustment', 0) + 2

        self.state = EvolutionState.STABLE

    # ============== 查询接口 ==============

    def get_dimension_weights(self) -> Dict[str, float]:
        """获取当前维度权重"""
        return {k: v.get_weight() for k, v in self.dimension_weights.items()}

    def get_weight_for_dimension(self, dimension: Dimension) -> float:
        """获取特定维度的权重"""
        dim_weight = self.dimension_weights.get(dimension.value)
        if dim_weight:
            return dim_weight.get_weight()
        return 1.0

    def get_killchain_threshold(self, check_name: str) -> float:
        """获取 KillChain 检查的动态阈值"""
        if check_name in self.killchain_thresholds:
            return self.killchain_thresholds[check_name].current_threshold
        return 0.0

    def get_pattern_confidence(self, pattern_type: str) -> float:
        """获取连锁模式置信度"""
        if pattern_type in self.pattern_confidence:
            return self.pattern_confidence[pattern_type].current_confidence
        return 0.7

    def get_conservative_adjustment(self) -> int:
        """获取窗口预测保守调整值"""
        return getattr(self, '_conservative_adjustment', 0)

    # ============== 关键词库接口 ==============

    def add_keywords(self, dimension: str, keywords: List[str]):
        """追加关键词"""
        self.keyword_library.add_keywords(dimension, keywords)
        self.save_state()

    def extract_and_add_keywords(self, signals: List[Dict]):
        """从信号中提取并追加关键词"""
        extracted = self.keyword_library.extract_from_signals(signals)
        for dim, kws in extracted.items():
            self.keyword_library.add_keywords(dim, kws)
        self.save_state()

    def get_keywords(self, dimension: str, n: int = 20) -> List[str]:
        """获取关键词"""
        return self.keyword_library.get_keywords(dimension, n)

    # ============== 权重历史记录 ==============

    def record_weights_history(self):
        """记录当前权重快照到历史（用于趋势图）"""
        from pathlib import Path

        history_file = Path("/home/admin1/aiagent/代理知识库/我的/opportunity_discovery/weights_history.json")

        # 读取现有历史
        history = []
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except:
                history = []

        # 创建快照
        snapshot = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "weights": {
                k: v.get_weight()
                for k, v in self.dimension_weights.items()
            }
        }

        history.append(snapshot)

        # 只保留最近100条
        if len(history) > 100:
            history = history[-100:]

        # 保存
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    # ============== 状态持久化 ==============

    def save_state(self):
        """保存状态到磁盘"""
        state = {
            "dimension_weights": {
                k: {
                    "dimension": v.dimension,
                    "base_weight": v.base_weight,
                    "current_weight": v.current_weight,
                    "accuracy_history": v.accuracy_history[-10:],  # 只保留最近10条
                    "adjustment_count": v.adjustment_count
                }
                for k, v in self.dimension_weights.items()
            },
            "killchain_thresholds": {
                k: {
                    "check_name": v.check_name,
                    "base_threshold": v.base_threshold,
                    "current_threshold": v.current_threshold,
                    "success_cases": v.success_cases,
                    "failure_cases": v.failure_cases
                }
                for k, v in self.killchain_thresholds.items()
            },
            "pattern_confidence": {
                k: {
                    "pattern_type": v.pattern_type,
                    "base_confidence": v.base_confidence,
                    "current_confidence": v.current_confidence,
                    "success_count": v.success_count,
                    "failure_count": v.failure_count
                }
                for k, v in self.pattern_confidence.items()
            },
            "keyword_library": self.keyword_library.to_dict(),
            "state": self.state,
            "last_learning_at": self.last_learning_at,
            "_conservative_adjustment": getattr(self, '_conservative_adjustment', 0)
        }

        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def load_state(self):
        """从磁盘加载状态"""
        if not Path(self.storage_path).exists():
            return

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                state = json.load(f)

            # 恢复维度权重
            if "dimension_weights" in state:
                for k, v in state["dimension_weights"].items():
                    self.dimension_weights[k] = DimensionWeight(
                        dimension=v["dimension"],
                        base_weight=v["base_weight"],
                        current_weight=v["current_weight"],
                        accuracy_history=v.get("accuracy_history", []),
                        adjustment_count=v.get("adjustment_count", 0)
                    )

            # 恢复 KillChain 阈值
            if "killchain_thresholds" in state:
                for k, v in state["killchain_thresholds"].items():
                    self.killchain_thresholds[k] = KillChainThreshold(
                        check_name=v["check_name"],
                        base_threshold=v["base_threshold"],
                        current_threshold=v["current_threshold"],
                        success_cases=v.get("success_cases", 0),
                        failure_cases=v.get("failure_cases", 0)
                    )

            # 恢复连锁模式置信度
            if "pattern_confidence" in state:
                for k, v in state["pattern_confidence"].items():
                    self.pattern_confidence[k] = PatternConfidence(
                        pattern_type=v["pattern_type"],
                        base_confidence=v["base_confidence"],
                        current_confidence=v["current_confidence"],
                        success_count=v.get("success_count", 0),
                        failure_count=v.get("failure_count", 0)
                    )

            # 恢复关键词库
            if "keyword_library" in state:
                self.keyword_library = DynamicKeywordLibrary.from_dict(state["keyword_library"])

            # 恢复状态
            self.state = state.get("state", EvolutionState.STABLE)
            self.last_learning_at = state.get("last_learning_at", "")
            self._conservative_adjustment = state.get("_conservative_adjustment", 0)

        except Exception as e:
            print(f"加载自进化状态失败: {e}")

    # ============== 状态报告 ==============

    def get_status_summary(self) -> dict:
        """获取自进化状态摘要"""
        return {
            "state": self.state,
            "last_learning_at": self.last_learning_at,
            "dimension_weights": {
                k: round(v.current_weight, 3)
                for k, v in self.dimension_weights.items()
            },
            "killchain_thresholds": {
                k: round(v.current_threshold, 2)
                for k, v in self.killchain_thresholds.items()
            },
            "pattern_confidence": {
                k: round(v.current_confidence, 2)
                for k, v in self.pattern_confidence.items()
            },
            "keyword_counts": {
                dim: len(kws)
                for dim, kws in self.keyword_library.library.items()
            },
            "total_learning_count": sum(
                v.adjustment_count
                for v in self.dimension_weights.values()
            )
        }


# ============== 主程序 ==============

def main():
    import argparse

    parser = argparse.ArgumentParser(description="自进化核心模块")
    parser.add_argument("--status", action="store_true", help="查看自进化状态")
    parser.add_argument("--learn", action="store_true", help="模拟一次学习")
    parser.add_argument("--keywords", action="store_true", help="查看关键词库")

    args = parser.parse_args()

    manager = SelfEvolutionManager()

    if args.status:
        print("\n📊 自进化系统状态：")
        summary = manager.get_status_summary()
        print(f"   状态：{summary['state']}")
        print(f"   上次学习：{summary['last_learning_at'] or '从未学习'}")
        print(f"   总学习次数：{summary['total_learning_count']}")

        print("\n📐 维度权重：")
        for dim, weight in summary['dimension_weights'].items():
            bar = "█" * int(weight * 10)
            print(f"   {dim}: {weight:.3f} {bar}")

        print("\n⚖️ KillChain 阈值：")
        for check, threshold in summary['killchain_thresholds'].items():
            print(f"   {check}: {threshold}")

        print("\n🔮 模式置信度：")
        for pattern, conf in summary['pattern_confidence'].items():
            print(f"   {pattern}: {conf:.0%}")

        print("\n📚 关键词库：")
        for dim, count in summary['keyword_counts'].items():
            print(f"   {dim}: {count} 个关键词")

    elif args.learn:
        print("\n🔄 模拟一次学习...")
        manager.learn_from_execution(
            opportunity_name="测试机会",
            outcome="部分成功",
            deviation="比预期慢",
            lesson="技术维度评分过高",
            dimension_hints=["技术", "商业模式"],
            pattern_type="service"
        )
        print("✅ 学习完成")
        print(f"   新权重：{manager.get_dimension_weights()}")
        print(f"   新模式置信度：service={manager.get_pattern_confidence('service'):.0%}")

    elif args.keywords:
        print("\n📚 关键词库：")
        for dim in ["技术", "商业模式", "用户痛点"]:
            kws = manager.get_keywords(dim, 10)
            print(f"\n   {dim}：")
            print(f"   {', '.join(kws)}")

    else:
        print(__doc__)


if __name__ == "__main__":
    main()
