"""
因果发现引擎 v4.3
Causal Discovery Engine — PC Algorithm简化版

核心功能：
1. PC Algorithm简化版本
2. 从时序数据中发现因果关系
3. 因果关系过滤伪信号
4. 预测推理（S曲线阶段）

使用方式：
python causal_engine.py --discover
python causal_engine.py --filter "GPU供应商"
python causal_engine.py --predict "OpenClaw"
"""

import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict


# ============== 因果关系数据结构 ==============

@dataclass
class CausalEdge:
    """因果边"""
    from_node: str
    to_node: str
    cause_type: str  # direct / indirect / conditional
    confidence: float  # 0-1
    lag: int  # 时间滞后（天）
    evidence_count: int = 0
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "from_node": self.from_node,
            "to_node": self.to_node,
            "cause_type": self.cause_type,
            "confidence": round(self.confidence, 3),
            "lag": self.lag,
            "evidence_count": self.evidence_count,
            "metadata": self.metadata
        }


@dataclass
class CausalGraph:
    """因果图"""
    edges: List[CausalEdge] = field(default_factory=list)
    nodes: Set[str] = field(default_factory=set)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_edge(self, edge: CausalEdge):
        self.edges.append(edge)
        self.nodes.add(edge.from_node)
        self.nodes.add(edge.to_node)

    def get_parents(self, node: str) -> List[str]:
        return [e.from_node for e in self.edges if e.to_node == node]

    def get_children(self, node: str) -> List[str]:
        return [e.to_node for e in self.edges if e.from_node == node]

    def get_causes(self, node: str) -> List[CausalEdge]:
        return [e for e in self.edges if e.to_node == node]

    def get_effects(self, node: str) -> List[CausalEdge]:
        return [e for e in self.edges if e.from_node == node]

    def is_ancestor(self, node_a: str, node_b: str) -> bool:
        """检查node_a是否是node_b的祖先"""
        visited = set()
        queue = [node_a]
        while queue:
            current = queue.pop(0)
            if current == node_b:
                return True
            if current in visited:
                continue
            visited.add(current)
            queue.extend(self.get_children(current))
        return False


# ============== PC Algorithm简化版 ==============

class PCAlgorithm:
    """
    PC Algorithm 简化版

    用于从观测数据中发现因果关系
    核心思想：条件独立性测试
    """

    def __init__(self, significance_level: float = 0.3):
        # 放宽阈值以发现更多因果关系（相关性高于0.3认为有边）
        self.significance_level = significance_level
        self.conditional_tests = 0

    def discover_causal_structure(self, data: Dict[str, List[float]]) -> CausalGraph:
        """
        发现因果结构

        Args:
            data: {node_name: [values...]}

        Returns:
            CausalGraph
        """
        nodes = list(data.keys())
        n = len(nodes)

        # 1. 骨架发现（Skeleton Discovery）
        # 从完全图开始，通过条件独立性测试删除边
        skeleton = self._build_skeleton(nodes, data)

        # 2. 方向发现（Orientation）
        # 使用V-结构和其他规则给边定向
        graph = self._orient_edges(skeleton, nodes, data)

        return graph

    def _build_skeleton(self, nodes: List[str], data: Dict) -> Dict[Tuple[str, str], bool]:
        """
        构建骨架（无方向的因果图）

        Returns:
            {(node_a, node_b): is_adjacent}
        """
        n = len(nodes)
        # 初始化：所有节点对都相邻
        adjacents: Dict[Tuple[str, str], bool] = {}
        for i in range(n):
            for j in range(i + 1, n):
                adjacents[(nodes[i], nodes[j])] = True

        # 逐层测试条件独立性
        max_depth = 2  # 最大条件集大小

        for depth in range(max_depth + 1):
            for (a, b) in list(adjacents.keys()):
                if not adjacents.get((a, b), False):
                    continue

                # 获取a和b的邻居（排除a和b自身）
                neighbors_a = set(self._get_neighbors(a, nodes, adjacents))
                neighbors_b = set(self._get_neighbors(b, nodes, adjacents))

                # 使用并集，排除a和b自身
                candidates = list((neighbors_a | neighbors_b) - {a, b})

                if len(candidates) < depth:
                    continue

                # 测试所有大小为depth的条件集
                for cond_set in self._generate_conditional_sets(candidates, depth):
                    self.conditional_tests += 1

                    # 条件独立性测试（偏相关）
                    if self._test_conditional_independence(a, b, list(cond_set), data):
                        # a和b条件独立，删除边
                        adjacents[(a, b)] = False
                        adjacents[(b, a)] = False
                        break

        return adjacents

    def _get_neighbors(self, node: str, all_nodes: List[str],
                     adjacents: Dict[Tuple[str, str], bool]) -> List[str]:
        """获取节点的邻居（排除自身）"""
        neighbors = []
        for other in all_nodes:
            if other == node:
                continue
            if adjacents.get((node, other), False) or adjacents.get((other, node), False):
                neighbors.append(other)
        return neighbors

    def _generate_conditional_sets(self, nodes: List[str], size: int):
        """生成所有大小为size的条件集组合"""
        if size == 0:
            yield set()
            return

        if size > len(nodes):
            return

        for i in range(len(nodes)):
            remaining = nodes[i + 1:]
            for remainder in self._generate_conditional_sets(remaining, size - 1):
                yield {nodes[i]} | remainder

    def _test_conditional_independence(self, a: str, b: str,
                                       cond_set: List[str], data: Dict) -> bool:
        """
        测试a和b在给定条件集下是否条件独立

        使用偏相关作为独立性测试

        Returns:
            True表示条件独立（应该删除边）
        """
        if not cond_set:
            # 简单相关
            corr = self._pearson_correlation(data.get(a, []), data.get(b, []))
            return abs(corr) < self.significance_level

        # 偏相关（简化版）
        # 如果条件集为空，使用简单相关
        corr = self._partial_correlation(data, a, b, cond_set)
        return abs(corr) < self.significance_level

    def _pearson_correlation(self, x: List[float], y: List[float]) -> float:
        """计算皮尔逊相关系数"""
        if len(x) != len(y) or len(x) < 2:
            return 0.0

        n = len(x)
        mean_x = sum(x) / n
        mean_y = sum(y) / n

        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        denom_x = math.sqrt(sum((x[i] - mean_x) ** 2 for i in range(n)))
        denom_y = math.sqrt(sum((y[i] - mean_y) ** 2 for i in range(n)))

        if denom_x == 0 or denom_y == 0:
            return 0.0

        return numerator / (denom_x * denom_y)

    def _partial_correlation(self, data: Dict, a: str, b: str,
                            cond_set: List[str]) -> float:
        """
        计算偏相关系数（简化版）

        简化实现：使用残差相关
        """
        # 简化：如果条件集太大，直接返回0
        if len(cond_set) > 3:
            return 0.0

        # 获取数据
        x = data.get(a, [])
        y = data.get(b, [])

        if len(x) != len(y) or len(x) < 10:
            return 0.0

        # 简化处理：只考虑条件集中最重要的一个变量
        if cond_set:
            z = data.get(list(cond_set)[0], [])
            if len(z) == len(x):
                # 计算简单偏相关
                corr_xy = self._pearson_correlation(x, y)
                corr_xz = self._pearson_correlation(x, z)
                corr_yz = self._pearson_correlation(y, z)

                # 偏相关公式（简化）
                denom = math.sqrt((1 - corr_xz**2) * (1 - corr_yz**2))
                if denom == 0:
                    return 0.0

                return (corr_xy - corr_xz * corr_yz) / denom

        return self._pearson_correlation(x, y)

    def _orient_edges(self, skeleton: Dict[Tuple[str, str], bool],
                     nodes: List[str], data: Dict) -> CausalGraph:
        """
        给边定向

        使用V-结构规则和传播规则
        """
        graph = CausalGraph()

        # 首先添加所有相邻的边（无方向）
        for (a, b), is_adj in skeleton.items():
            if is_adj:
                edge = CausalEdge(
                    from_node=a,
                    to_node=b,
                    cause_type="unknown",
                    confidence=0.5,
                    lag=0
                )
                graph.add_edge(edge)

        # 使用时序信息辅助定向
        # 如果A的变化早于B，且A和B正相关，则A→B
        self._orient_by_temporal(data, graph)

        # 简化：直接假设相关性为正相关的从因到果
        # 实际应用中应使用更复杂的定向算法
        return graph

    def _orient_by_temporal(self, data: Dict, graph: CausalGraph):
        """使用时序信息辅助定向"""
        # 对于每条边，检查时间顺序
        for edge in graph.edges:
            series_a = data.get(edge.from_node, [])
            series_b = data.get(edge.to_node, [])

            if len(series_a) < 2 or len(series_b) < 2:
                continue

            # 检查哪条序列变化更早
            # 通过检查导数的符号
            diff_a = sum(1 for i in range(1, len(series_a))
                        if series_a[i] > series_a[i-1])
            diff_b = sum(1 for i in range(1, len(series_b))
                        if series_b[i] > series_b[i-1])

            # 如果A的变化领先于B，可能A是因
            if diff_a > diff_b:
                edge.confidence = min(0.9, edge.confidence + 0.2)


# ============== 因果过滤器 ==============

class CausalFilter:
    """
    因果过滤器

    使用因果关系过滤伪信号
    """

    def __init__(self, causal_graph: CausalGraph = None):
        self.causal_graph = causal_graph

    def is_true_signal(self, signal_a: str, signal_b: str,
                       correlation: float) -> Tuple[bool, str, float]:
        """
        判断信号是否为真信号

        Args:
            signal_a: 原因信号
            signal_b: 结果信号（机会）
            correlation: 相关性

        Returns:
            (is_true, reason, confidence)
        """
        if self.causal_graph is None:
            # 无因果图，降级为纯相关判断
            return self._fallback_check(signal_a, signal_b, correlation)

        # 检查是否存在因果关系
        direct_causes = self.causal_graph.get_parents(signal_b)

        # 精确匹配
        if signal_a in direct_causes:
            edge = self._get_edge(signal_a, signal_b)
            return True, "直接因果", edge.confidence if edge else 0.8

        # 检查传递因果
        if self.causal_graph.is_ancestor(signal_a, signal_b):
            return True, "传递因果", 0.7

        # 同一祖先的兄弟节点
        for cause in direct_causes:
            if self.causal_graph.is_ancestor(signal_a, cause):
                return True, "共同祖先因果", 0.6

        # 无因果关系
        return False, "伪相关（非因果）", abs(correlation)

    def _fallback_check(self, signal_a: str, signal_b: str,
                        correlation: float) -> Tuple[bool, str, float]:
        """无因果图时的降级判断"""
        if abs(correlation) > 0.7:
            return True, "强相关（无因果验证）", abs(correlation) * 0.5
        elif abs(correlation) > 0.4:
            return True, "中等相关（待观察）", abs(correlation) * 0.3
        else:
            return False, "弱相关", abs(correlation) * 0.2

    def _get_edge(self, from_node: str, to_node: str) -> Optional[CausalEdge]:
        """获取因果边"""
        if self.causal_graph is None:
            return None
        for edge in self.causal_graph.edges:
            if edge.from_node == from_node and edge.to_node == to_node:
                return edge
        return None

    def filter_opportunities(self, opportunities: List[Dict],
                            signals: List[str]) -> List[Dict]:
        """
        过滤机会列表

        Returns:
            带过滤标记的机会列表
        """
        filtered = []

        for opp in opportunities:
            opp_name = opp.get("name", "")

            # 检查每个机会的因果真实性
            is_true_list = []
            reasons = []

            for signal in signals:
                is_true, reason, conf = self.is_true_signal(signal, opp_name, 0.5)
                if is_true:
                    is_true_list.append(True)
                    reasons.append(reason)

            # 判断机会的因果真实性
            true_ratio = sum(is_true_list) / max(len(signals), 1)

            if true_ratio > 0.5:
                verdict = "真信号" if true_ratio > 0.7 else "待观察"
                priority = "P0" if true_ratio > 0.8 else "P1" if true_ratio > 0.5 else "P2"
            else:
                verdict = "伪信号"
                priority = "P3"

            filtered.append({
                **opp,
                "causal_verdict": verdict,
                "causal_confidence": true_ratio,
                "priority": priority,
                "causal_reasons": reasons
            })

        return filtered


# ============== S曲线预测 ==============

class SCurvePredictor:
    """
    S曲线预测器

    基于时序数据预测机会的S曲线阶段
    """

    STAGES = ["引入期", "加速期", "成熟期", "衰退期"]

    def predict_stage(self, values: List[float], timestamps: List[str] = None) -> Dict:
        """
        预测S曲线阶段

        Args:
            values: 时序值（如stars、mentions等）
            timestamps: 对应时间戳

        Returns:
            {stage, confidence, next_stage, days_to_next}
        """
        if len(values) < 5:
            return self._default_prediction()

        # 计算特征 - 使用前半和后半比较
        mid = len(values) // 2
        early_values = values[:mid] if mid >= 2 else values[:2]
        recent_values = values[mid:] if mid >= 2 else values[-3:]

        # 1. 平均值变化
        early_avg = sum(early_values) / len(early_values)
        recent_avg = sum(recent_values) / len(recent_values)

        if early_avg == 0:
            growth_rate = 0
        else:
            growth_rate = (recent_avg - early_avg) / early_avg

        # 2. 加速/减速判断（二阶导数）
        accelerations = []
        for i in range(2, len(values)):
            acc = (values[i] - 2*values[i-1] + values[i-2])
            accelerations.append(acc)
        avg_acceleration = sum(accelerations) / len(accelerations) if accelerations else 0

        # 3. 阶段判断（按优先级排序）
        # 衰退期: 负增长或持续下降
        if growth_rate < -0.05 or (recent_avg < early_avg and avg_acceleration < 0):
            stage = "衰退期"
            confidence = 0.75
        # 成熟期: 低增长(5%-30%)且加速度平稳
        elif 0.05 <= growth_rate <= 0.35 and abs(avg_acceleration) < 0.15:
            stage = "成熟期"
            confidence = 0.8
        # 加速期: 中高增长(>35%)且正加速度
        elif growth_rate > 0.35 and avg_acceleration > 0:
            stage = "加速期"
            confidence = 0.85
        # 引入期: 极低增长(<5%)或尚未突破
        elif growth_rate < 0.05:
            stage = "引入期"
            confidence = 0.7
        # 快速增长但不稳定
        elif growth_rate > 0.35:
            stage = "加速期"
            confidence = 0.7
        else:
            stage = "成熟期"
            confidence = 0.6

        # 预测下一阶段
        next_stage, days_to_next = self._predict_next_stage(stage, growth_rate, avg_acceleration)

        return {
            "stage": stage,
            "confidence": round(confidence, 2),
            "growth_rate": round(growth_rate, 3),
            "acceleration": round(avg_acceleration, 3),
            "next_stage": next_stage,
            "days_to_next": days_to_next,
            "window_months": self._estimate_window_months(stage)
        }

    def _default_prediction(self) -> Dict:
        """默认预测（数据不足时）"""
        return {
            "stage": "引入期",
            "confidence": 0.5,
            "growth_rate": 0.0,
            "acceleration": 0.0,
            "next_stage": "加速期",
            "days_to_next": 30,
            "window_months": 6
        }

    def _predict_next_stage(self, current_stage: str,
                           growth_rate: float,
                           acceleration: float) -> Tuple[str, int]:
        """预测下一阶段"""
        stage_idx = self.STAGES.index(current_stage) if current_stage in self.STAGES else 0

        if current_stage == "引入期":
            if growth_rate > 0.3:
                return "加速期", 30
            else:
                return "加速期", 60

        elif current_stage == "加速期":
            if acceleration < -0.1:
                return "成熟期", 30
            else:
                return "成熟期", 60

        elif current_stage == "成熟期":
            if growth_rate < -0.1:
                return "衰退期", 90
            else:
                return "成熟期", 90

        return "成熟期", 180

    def _estimate_window_months(self, stage: str) -> int:
        """估算窗口期月数"""
        if stage == "引入期":
            return 12
        elif stage == "加速期":
            return 6
        elif stage == "成熟期":
            return 3
        else:
            return 0


# ============== 主程序 ==============

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="因果发现引擎 v4.3")
    parser.add_argument("--discover", action="store_true", help="从数据发现因果关系")
    parser.add_argument("--filter", metavar="NAME", help="过滤机会")
    parser.add_argument("--predict", metavar="NAME", help="预测S曲线阶段")
    parser.add_argument("--demo", action="store_true", help="演示模式")

    args = parser.parse_args()

    print("🔮 因果发现引擎 v4.3\n")

    if args.demo:
        print("🎯 演示模式\n")

        # 1. 模拟因果发现
        print("1. 因果发现演示:")
        sample_data = {
            "github_stars": [100, 150, 220, 350, 500, 720, 1000],
            "twitter_mentions": [10, 25, 50, 90, 140, 200, 280],
            "reddit_posts": [5, 8, 12, 18, 22, 28, 35],
            "jobs_postings": [2, 3, 5, 8, 12, 18, 25],
        }

        pc = PCAlgorithm()
        graph = pc.discover_causal_structure(sample_data)

        print(f"   发现 {len(graph.edges)} 条因果边:")
        for edge in graph.edges:
            print(f"   - {edge.from_node} → {edge.to_node} (置信度: {edge.confidence:.2f})")

        # 2. 因果过滤演示
        print("\n2. 因果过滤演示:")
        cf = CausalFilter(graph)

        opportunities = [
            {"name": "GPU云服务", "score": 8},
            {"name": "AI开发工具", "score": 7},
            {"name": "机器学习平台", "score": 6},
        ]
        signals = ["github_stars", "twitter_mentions"]

        filtered = cf.filter_opportunities(opportunities, signals)
        for f in filtered:
            print(f"   - {f['name']}: {f['causal_verdict']} ({f['priority']})")

        # 3. S曲线预测
        print("\n3. S曲线阶段预测:")
        predictor = SCurvePredictor()

        stages = [
            ([10, 12, 15, 18, 22], "快速成长期"),
            ([100, 105, 108, 110, 112], "成熟稳定期"),
            ([50, 48, 45, 42, 40], "衰退期"),
        ]

        for values, desc in stages:
            result = predictor.predict_stage(values)
            print(f"   {desc}: {result['stage']} (置信度: {result['confidence']:.0%})")
            print(f"     增长: {result['growth_rate']:.1%}, 窗口期: {result['window_months']}月")

    elif args.discover:
        print("📊 从数据发现因果关系...")
        # 实际使用时从数据库读取数据
        print("⚠️ 需要提供signal_history数据")

    elif args.filter:
        print(f"🔍 过滤机会: {args.filter}")

    elif args.predict:
        print(f"📈 预测S曲线: {args.predict}")
        predictor = SCurvePredictor()
        # 模拟数据
        result = predictor.predict_stage([10, 25, 50, 100, 180, 280, 400])
        print(f"\n预测结果: {result['stage']}")
        print(f"置信度: {result['confidence']:.0%}")
        print(f"增长趋势: {result['growth_rate']:.1%}")
        print(f"窗口期: {result['window_months']}月")

    else:
        print(__doc__)