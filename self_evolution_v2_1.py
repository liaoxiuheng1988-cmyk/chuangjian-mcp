"""
自进化管理器 v2.1
SelfEvolutionManager Enhanced — 规则质量、跨域挖掘、反馈闭环优化

v2.1优化内容：
1. 规则质量评估与智能衰减机制
2. 增强跨域模式挖掘（显式领域映射）
3. 负面反馈优先 + mini-evolve机制
4. 自进化仪表盘简报

使用方式：
from self_evolution_v2_1 import SelfEvolutionManagerV21
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


# ============== 辅助类 ==============

class RuleQuality(Enum):
    """规则质量等级"""
    HIGH = "high"      # ≥0.8
    MEDIUM = "medium"  # 0.5-0.8
    LOW = "low"        # 0.3-0.5
    DECAYED = "decayed"  # <0.3


class FeedbackPriority(Enum):
    """反馈优先级"""
    CRITICAL = 3   # 负面反馈且严重影响质量
    HIGH = 2       # 负面反馈
    NORMAL = 1     # 普通反馈
    LOW = 0        # 轻微正面反馈


# ============== 规则质量追踪器 ==============

@dataclass
class RuleQualityTracker:
    """规则质量追踪器 v2.1"""
    rule_id: str
    rule_type: str  # description | scoring | action
    trigger: str
    pattern: str
    source: str

    # 质量指标
    effectiveness: float = 0.8
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0

    # 时间追踪
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    last_used_at: str = ""
    last_feedback_at: str = ""

    # 质量衰减
    decay_count: int = 0
    quality_history: List[float] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """计算成功率"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.5  # 默认50%
        return self.success_count / total

    @property
    def quality(self) -> RuleQuality:
        """评估规则质量等级"""
        if self.effectiveness >= 0.8:
            return RuleQuality.HIGH
        elif self.effectiveness >= 0.5:
            return RuleQuality.MEDIUM
        elif self.effectiveness >= 0.3:
            return RuleQuality.LOW
        else:
            return RuleQuality.DECAYED

    def record_usage(self, success: bool):
        """记录规则使用结果"""
        self.usage_count += 1
        self.last_used_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1

        # 基于成功率动态调整effectiveness
        self._update_effectiveness()

    def record_feedback(self, is_positive: bool):
        """记录反馈对规则的影响"""
        self.last_feedback_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if is_positive:
            self.effectiveness = min(1.0, self.effectiveness * 1.1)
        else:
            self.effectiveness *= 0.85

        self.quality_history.append(self.effectiveness)

    def _update_effectiveness(self):
        """基于使用成功率更新effectiveness"""
        success_rate = self.success_rate
        # 加权更新：70%基于成功率，30%保持历史
        self.effectiveness = self.effectiveness * 0.3 + success_rate * 0.7

    def should_decay(self) -> bool:
        """判断是否应该被衰减"""
        return (
            self.effectiveness < 0.4 or
            (self.usage_count > 10 and self.success_rate < 0.4) or
            (self.decay_count > 3)
        )

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "rule_type": self.rule_type,
            "trigger": self.trigger,
            "pattern": self.pattern,
            "effectiveness": round(self.effectiveness, 3),
            "quality": self.quality.value,
            "usage_count": self.usage_count,
            "success_rate": round(self.success_rate, 3),
            "created_at": self.created_at,
            "last_used_at": self.last_used_at,
        }


# ============== 跨域模式挖掘器 ==============

@dataclass
class CrossDomainPattern:
    """跨域模式 v2.1"""
    pattern_id: str
    source_domain: str
    target_domain: str
    trigger_condition: str  # 触发条件
    migration_rule: str      # 迁移规则描述
    score: float
    confidence: float        # 置信度
    evidence_count: int = 0
    last_triggered: str = ""

    def to_dict(self) -> dict:
        return {
            "pattern_id": self.pattern_id,
            "source_domain": self.source_domain,
            "target_domain": self.target_domain,
            "trigger_condition": self.trigger_condition,
            "migration_rule": self.migration_rule,
            "score": round(self.score, 3),
            "confidence": round(self.confidence, 3),
            "evidence_count": self.evidence_count,
        }


class CrossDomainMiner:
    """
    跨域模式挖掘器 v2.1

    显式领域映射 + 模式迁移
    """

    # 预定义领域映射
    DOMAIN_MAPPING = {
        "电商": {
            "pain_points": ["转化率低", "获客成本高", "复购率低", "库存积压"],
            "success_patterns": ["爆款逻辑", "私域运营", "用户分层"],
            "target_domains": ["内容创作", "知识付费", "SaaS工具"],
        },
        "内容创作": {
            "pain_points": ["产能低", "变现难", "粉丝粘性低"],
            "success_patterns": ["矩阵运营", "IP孵化", "内容迭代"],
            "target_domains": ["电商", "教育", "知识付费"],
        },
        "SaaS工具": {
            "pain_points": ["获客难", "留存难", "功能同质化"],
            "success_patterns": ["PLG增长", "集成生态", "垂直深耕"],
            "target_domains": ["电商", "内容创作", "企业服务"],
        },
        "AI": {
            "pain_points": ["算力成本高", "效果不稳定", "用户门槛高"],
            "success_patterns": ["API封装", "垂直优化", "用户体验简化"],
            "target_domains": ["所有行业"],
        },
    }

    def __init__(self):
        self.patterns: List[CrossDomainPattern] = []
        self.domain_effectiveness: Dict[str, Dict[str, float]] = {}

    def mine_cross_domain_patterns(
        self,
        history: List[dict],
        recent_rounds: int = 5
    ) -> List[CrossDomainPattern]:
        """
        从历史数据中挖掘跨域模式

        Args:
            history: 进化历史
            recent_rounds: 考虑的最近轮次

        Returns:
            发现的新跨域模式列表
        """
        if len(history) < recent_rounds:
            return []

        recent = history[-recent_rounds:]
        new_patterns = []

        # 1. 挖掘高评分模式的跨域迁移
        high_score_rounds = [
            r for r in recent
            if r.get("multi_dim_score", {}).get("overall", 0) > 0.65
        ]

        if len(high_score_rounds) >= 2:
            # 分析高评分轮的共同特征
            avg_depth = sum(r.get("multi_dim_score", {}).get("depth", 0) for r in high_score_rounds) / len(high_score_rounds)
            avg_novelty = sum(r.get("multi_dim_score", {}).get("novelty", 0) for r in high_score_rounds) / len(high_score_rounds)
            avg_action = sum(r.get("multi_dim_score", {}).get("action", 0) for r in high_score_rounds) / len(high_score_rounds)

            # 深度+新颖度都高 → 可能是跨域成功
            if avg_depth > 0.6 and avg_novelty > 0.6:
                # 推断可能的跨域迁移
                for source, info in self.DOMAIN_MAPPING.items():
                    # 检查源领域的痛点是否被解决
                    if avg_action > 0.7:
                        for target in info["target_domains"]:
                            pattern = self._create_cross_domain_pattern(
                                source_domain=source,
                                target_domain=target,
                                score=(avg_depth + avg_novelty + avg_action) / 3,
                                evidence_count=len(high_score_rounds),
                            )
                            if pattern and pattern not in self.patterns:
                                new_patterns.append(pattern)

        # 2. 跨域痛点映射
        pain_point_mappings = self._mine_pain_point_mappings(recent)
        for mapping in pain_point_mappings:
            if mapping not in self.patterns:
                new_patterns.append(mapping)

        # 3. 添加新模式并更新置信度
        for pattern in new_patterns:
            self.patterns.append(pattern)
            self._update_domain_effectiveness(pattern)

        return new_patterns

    def _create_cross_domain_pattern(
        self,
        source_domain: str,
        target_domain: str,
        score: float,
        evidence_count: int
    ) -> Optional[CrossDomainPattern]:
        """创建跨域模式"""
        source_info = self.DOMAIN_MAPPING.get(source_domain, {})
        target_info = self.DOMAIN_MAPPING.get(target_domain, {})

        if not source_info or not target_info:
            return None

        # 生成迁移规则
        migration_rule = f"从{source_domain}的{source_info['success_patterns'][0] if source_info['success_patterns'] else '模式'}迁移到{target_domain}"

        return CrossDomainPattern(
            pattern_id=f"xdomain_{source_domain}_{target_domain}_{datetime.now().strftime('%H%M%S')}",
            source_domain=source_domain,
            target_domain=target_domain,
            trigger_condition=f"depth>{0.6} AND novelty>{0.6} AND action>{0.7}",
            migration_rule=migration_rule,
            score=score,
            confidence=min(0.9, 0.5 + evidence_count * 0.1),
            evidence_count=evidence_count,
            last_triggered=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def _mine_pain_point_mappings(self, recent: List[dict]) -> List[CrossDomainPattern]:
        """挖掘痛点映射模式"""
        patterns = []

        # 电商 → 内容创作痛点映射
        ecommerce_low = [r for r in recent if r.get("multi_dim_score", {}).get("action", 0) < 0.5]
        if len(ecommerce_low) >= 1:
            patterns.append(CrossDomainPattern(
                pattern_id=f"xdomain_pain_ecommerce_content_{datetime.now().strftime('%H%M%S')}",
                source_domain="电商",
                target_domain="内容创作",
                trigger_condition="action<0.5",
                migration_rule="电商的[获客成本高]痛点可通过内容创作的低成本获客模式解决",
                score=0.65,
                confidence=0.6,
            ))

        return patterns

    def _update_domain_effectiveness(self, pattern: CrossDomainPattern):
        """更新领域间效果追踪"""
        key = f"{pattern.source_domain}_to_{pattern.target_domain}"
        if key not in self.domain_effectiveness:
            self.domain_effectiveness[key] = {"total_score": 0, "count": 0}

        self.domain_effectiveness[key]["total_score"] += pattern.score
        self.domain_effectiveness[key]["count"] += 1

    def get_transferable_patterns(self, target_domain: str) -> List[CrossDomainPattern]:
        """获取可迁移到目标领域的模式"""
        return [
            p for p in self.patterns
            if p.target_domain == target_domain or p.target_domain == "所有行业"
        ]


# ============== 反馈优先级处理器 ==============

class FeedbackPriorityProcessor:
    """
    反馈优先级处理器 v2.1

    负面反馈优先处理 + mini-evolve机制
    """

    def __init__(self):
        self.pending_negative: List[dict] = []  # 待处理的负面反馈
        self.mini_evolve_threshold = 2  # 积累2条负面反馈触发mini-evolve
        self.last_mini_evolve_round = 0

    def process_feedback(self, feedback: dict, current_round: int) -> tuple[str, dict]:
        """
        处理反馈并返回优先级和处理建议

        Returns:
            (priority_level, mini_evolve_suggestion)
        """
        is_positive = feedback.get("adopted", False)
        severity = feedback.get("severity", "normal")  # critical | high | normal | low

        # 判断优先级
        if not is_positive and severity == "critical":
            priority = FeedbackPriority.CRITICAL
            suggestion = self._handle_critical_negative(feedback)
        elif not is_positive and severity in ("high", "normal"):
            priority = FeedbackPriority.HIGH
            suggestion = self._handle_negative(feedback)
            self.pending_negative.append(feedback)
        elif not is_positive:
            priority = FeedbackPriority.NORMAL
            suggestion = {}
        else:
            priority = FeedbackPriority.LOW
            suggestion = {}

        # 检查是否触发mini-evolve
        mini_evolve = None
        if len(self.pending_negative) >= self.mini_evolve_threshold:
            if current_round - self.last_mini_evolve_round >= 3:
                mini_evolve = self._trigger_mini_evolve()
                self.last_mini_evolve_round = current_round

        return priority.value, {
            "suggestion": suggestion,
            "mini_evolve": mini_evolve,
            "pending_negative_count": len(self.pending_negative),
        }

    def _handle_critical_negative(self, feedback: dict) -> dict:
        """处理严重负面反馈 - 立即响应"""
        return {
            "action": "immediate_weight_adjust",
            "target": feedback.get("dimension", "all"),
            "adjustment": -0.15,  # 立即降低权重
            "reason": "critical_negative_feedback",
        }

    def _handle_negative(self, feedback: dict) -> dict:
        """处理一般负面反馈"""
        return {
            "action": "queue_for_mini_evolve",
            "target": feedback.get("dimension", "unknown"),
            "pending": True,
        }

    def _trigger_mini_evolve(self) -> dict:
        """触发mini-evolve - 轻量级快速调整"""
        mini_evolve_result = {
            "triggered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "negative_count": len(self.pending_negative),
            "adjustments": [],
        }

        # 统计负面反馈的维度分布
        dimension_issues = {}
        for fb in self.pending_negative:
            dim = fb.get("dimension", "unknown")
            dimension_issues[dim] = dimension_issues.get(dim, 0) + 1

        # 对高频出问题的维度进行小幅调整
        for dim, count in dimension_issues.items():
            if count >= 2:
                mini_evolve_result["adjustments"].append({
                    "dimension": dim,
                    "adjustment": -0.05 * count,  # 每条反馈降低5%
                    "reason": f"accumulated_negative_feedback({count})",
                })

        # 清空待处理队列
        self.pending_negative.clear()

        return mini_evolve_result

    def clear_pending(self):
        """清空待处理反馈"""
        self.pending_negative.clear()


# ============== 自进化管理器 v2.1 ==============

class SelfEvolutionManagerV21:
    """
    自进化管理器 v2.1 — 规则质量优化版

    v2.1核心优化：
    1. 规则质量评估与智能衰减
    2. 增强跨域模式挖掘
    3. 负面反馈优先 + mini-evolve
    4. 自进化仪表盘
    """

    def __init__(self):
        self.evolution_round = 0
        self.evolution_history = []

        # v2.0: 多维度评分权重
        self.multi_dim_weights = {
            "depth_score": 0.25,
            "novelty_score": 0.25,
            "action_score": 0.30,
            "feedback_score": 0.20,
        }

        # v2.1: 规则质量追踪器（替代原有规则库）
        self.rule_tracker: Dict[str, RuleQualityTracker] = {}
        self._rule_id_counter = 0

        # v2.0: 规则模板库（可进化）
        self.description_templates = {
            "上游供应": [
                "{b}解决{a}的算力成本痛点，两者联合可将推理延迟从3s降至0.8s",
            ],
            "服务依赖": [
                "{a}开发者通过{b}降低学习曲线，联合解决[入门难]痛点",
            ],
            "衍生关联": [
                "{b}内容创作者依赖{a}工具，联合解决[产能低]痛点",
            ],
        }

        # v2.0: 评分权重
        self.scoring_weights = {
            "strength": 0.25,
            "conflict_low": 0.15,
            "mcp_high": 0.20,
            "layer3_bonus": 0.15,
            "supply_chain": 0.10,
            "type_complement": 0.15,
        }

        # v2.0: 行动建议模板
        self.action_templates = {
            "基础设施": [
                "①在GitHub创建openclaw-{name}-sdk仓库 → ②编写SDK核心代码 → ③在掘金发帖附链接",
            ],
            "服务": [
                "①在Notion搭建{name}落地SOP → ②整理企业案例 → ③知乎专栏发布教程",
            ],
        }

        # Self-Reflection记录
        self.reflection_journal = []

        # v2.0: 用户反馈历史
        self.feedback_history = []

        # v2.1: 发现的模式（增强）
        self.discovered_patterns = []

        # v2.1: 跨域模式挖掘器
        self.cross_domain_miner = CrossDomainMiner()

        # v2.1: 反馈优先级处理器
        self.feedback_processor = FeedbackPriorityProcessor()

        # v2.1: 进化日志
        self.evolution_log: Dict[str, Any] = {}
        self.mini_evolve_log: List[dict] = []

    def _generate_rule_id(self) -> str:
        """生成唯一规则ID"""
        self._rule_id_counter += 1
        return f"rule_{self.evolution_round}_{self._rule_id_counter}"

    # ============== 核心方法 ==============

    def record_round(self, analysis_result: dict, feedback: dict = None) -> dict:
        """v2.1: 记录一轮分析"""
        self.evolution_round += 1

        # 多维度评分
        multi_dim = self._evaluate_multi_dimensional(analysis_result)

        # v2.1: 处理反馈优先级
        feedback_priority_info = {}
        if feedback:
            priority, feedback_priority_info = self.feedback_processor.process_feedback(
                feedback, self.evolution_round
            )
            feedback["priority"] = priority
            feedback["priority_info"] = feedback_priority_info

        record = {
            "round": self.evolution_round,
            "multi_dim_score": multi_dim,
            "feedback": feedback,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "analysis_summary": analysis_result,
        }
        self.evolution_history.append(record)

        # 记录反馈
        if feedback:
            self._learn_from_feedback(feedback, analysis_result)

        # 模式挖掘（每3轮）
        if self.evolution_round % 3 == 0:
            self._mine_patterns()

        # 检查是否触发进化
        unprocessed_feedback = len([f for f in self.feedback_history if not f.get("incorporated")])

        # v2.1: 负面反馈优先触发
        has_critical_negative = any(
            f.get("priority") == "critical"
            for f in self.feedback_history[-3:]
        )

        if has_critical_negative:
            self._mini_evolve()
        elif self.should_evolve(self.evolution_round, unprocessed_feedback):
            self._auto_evolve(multi_dim)

        return multi_dim

    def _evaluate_multi_dimensional(self, analysis_result: dict) -> dict:
        """v2.1: 多维度评估（带规则质量加权）"""
        # 基础评分计算
        node_count = analysis_result.get("node_count", 0)
        rel_count = analysis_result.get("rel_count", 0)
        depth_score = min((node_count / 50 + rel_count / 1000) / 2, 1.0)

        mcp_high = analysis_result.get("mcp_high_count", 0)
        novelty_score = min(mcp_high / 50, 1.0)

        top_score = analysis_result.get("top_score", 0)
        action_score = top_score / 10.0

        # v2.1: 基于规则质量的反馈评分调整
        feedback_score = self._calculate_feedback_score_with_quality()

        # 综合评分
        overall = (
            depth_score * self.multi_dim_weights["depth_score"] +
            novelty_score * self.multi_dim_weights["novelty_score"] +
            action_score * self.multi_dim_weights["action_score"] +
            feedback_score * self.multi_dim_weights["feedback_score"]
        )

        return {
            "depth": depth_score,
            "novelty": novelty_score,
            "action": action_score,
            "feedback": feedback_score,
            "overall": overall,
        }

    def _calculate_feedback_score_with_quality(self) -> float:
        """v2.1: 基于规则质量计算反馈评分"""
        recent_feedback = self.feedback_history[-5:]
        if not recent_feedback:
            return 0.5

        # 考虑规则质量的影响
        weighted_score = 0.0
        for fb in recent_feedback:
            base = 1.0 if fb.get("adopted") else 0.0
            # 规则质量乘数
            rule_id = fb.get("rule_id")
            if rule_id and rule_id in self.rule_tracker:
                quality_mult = self.rule_tracker[rule_id].effectiveness
            else:
                quality_mult = 0.8
            weighted_score += base * quality_mult

        return min(1.0, weighted_score / len(recent_feedback))

    def _learn_from_feedback(self, feedback: dict, analysis_result: dict):
        """v2.1: 从反馈学习（带质量追踪）"""
        self.feedback_history.append({
            "round": self.evolution_round,
            "feedback": feedback,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        # 如果反馈被采纳，生成规则
        if feedback.get("adopted", False):
            self._generate_rule_from_feedback(feedback, analysis_result)

            # v2.1: 更新相关规则的质量
            if feedback.get("rule_id") in self.rule_tracker:
                self.rule_tracker[feedback["rule_id"]].record_feedback(True)
        else:
            # v2.1: 负面反馈也更新质量
            if feedback.get("rule_id") in self.rule_tracker:
                self.rule_tracker[feedback["rule_id"]].record_feedback(False)

    def _generate_rule_from_feedback(self, feedback: dict, analysis_result: dict):
        """v2.1: 从反馈生成带质量追踪的规则"""
        rule_type = feedback.get("type", "description")
        content = feedback.get("content", "")

        rule_id = self._generate_rule_id()
        trigger = analysis_result.get("relation_type", "通用")

        rule = RuleQualityTracker(
            rule_id=rule_id,
            rule_type=rule_type,
            trigger=trigger,
            pattern=content,
            source=f"feedback_round_{self.evolution_round}",
        )

        self.rule_tracker[rule_id] = rule

        # 关联反馈与规则
        feedback["rule_id"] = rule_id

    def _mine_patterns(self):
        """v2.1: 模式挖掘（增强跨域挖掘）"""
        if len(self.evolution_history) < 3:
            return

        recent = self.evolution_history[-3:]

        # 基础模式挖掘
        high_scores = [r for r in recent if r["multi_dim_score"]["overall"] > 0.6]
        if len(high_scores) >= 2:
            pattern = {
                "type": "high_score_pattern",
                "trigger": "mcp_high_count >= 30 AND top_score >= 8",
                "score": sum(r["multi_dim_score"]["overall"] for r in high_scores) / len(high_scores),
                "source": f"mined_round_{self.evolution_round}",
            }
            if pattern not in self.discovered_patterns:
                self.discovered_patterns.append(pattern)

        # v2.1: 跨域模式挖掘
        new_cross_domain = self.cross_domain_miner.mine_cross_domain_patterns(
            self.evolution_history,
            recent_rounds=5
        )
        for pattern in new_cross_domain:
            self.discovered_patterns.append(pattern.to_dict())

    def _auto_evolve(self, multi_dim: dict = None):
        """v2.1: 全量进化"""
        recent = self.evolution_history[-5:]
        avg_overall = sum(r["multi_dim_score"]["overall"] for r in recent) / len(recent) if recent else 0.5

        # v2.1: 基于规则质量调整权重
        self._adjust_weights_by_rule_quality()

        # 规则自生成
        self._generate_rules_from_patterns()

        # 动态调整多维度权重
        if multi_dim:
            if multi_dim["novelty"] < 0.4:
                self.multi_dim_weights["novelty_score"] += 0.05
                self.multi_dim_weights["depth_score"] -= 0.02
            if multi_dim["action"] < 0.5:
                self.multi_dim_weights["action_score"] += 0.03

        # 标准化权重
        total = sum(self.multi_dim_weights.values())
        self.multi_dim_weights = {k: v/total for k, v in self.multi_dim_weights.items()}

        # 进化模板
        self._evolve_description_templates(avg_overall)
        self._evolve_scoring_weights(avg_overall)
        self._evolve_action_templates(avg_overall)

        # 标记反馈已处理
        for f in self.feedback_history:
            if not f.get("incorporated"):
                f["incorporated"] = True

        # v2.1: 智能规则衰减
        self._smart_decay_rules()

        # 进化日志
        self.evolution_log = {
            "evolved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "avg_overall": avg_overall,
            "new_multi_dim_weights": dict(self.multi_dim_weights),
            "rules_current": len(self.rule_tracker),
            "patterns_discovered": len(self.discovered_patterns),
        }

    def _mini_evolve(self):
        """v2.1: 轻量级快速进化（负面反馈触发）"""
        mini_evolve = {
            "triggered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "trigger": "critical_negative_feedback",
            "adjustments": [],
        }

        # 快速调整：降低反馈权重，提高其他维度
        self.multi_dim_weights["feedback_score"] = max(0.1, self.multi_dim_weights["feedback_score"] - 0.1)
        self.multi_dim_weights["depth_score"] = min(0.35, self.multi_dim_weights["depth_score"] + 0.05)
        self.multi_dim_weights["novelty_score"] = min(0.35, self.multi_dim_weights["novelty_score"] + 0.05)

        # 标准化
        total = sum(self.multi_dim_weights.values())
        self.multi_dim_weights = {k: v/total for k, v in self.multi_dim_weights.items()}

        mini_evolve["new_weights"] = dict(self.multi_dim_weights)
        self.mini_evolve_log.append(mini_evolve)

    def _generate_rules_from_patterns(self):
        """v2.1: 从发现模式生成规则"""
        for pattern in self.discovered_patterns[-3:]:
            if isinstance(pattern, dict) and pattern.get("type") == "high_score_pattern":
                # 基于高评分模式生成描述规则
                rule_id = self._generate_rule_id()
                rule = RuleQualityTracker(
                    rule_id=rule_id,
                    rule_type="description",
                    trigger="mcp_high",
                    pattern=f"高MCP潜力节点组合的完播率比普通组合高{pattern['score']*100:.0f}%",
                    source=f"pattern_round_{self.evolution_round}",
                    effectiveness=pattern.get("score", 0.7),
                )
                self.rule_tracker[rule_id] = rule

    def _evolve_description_templates(self, avg_overall: float):
        """扩展描述模板库（基于综合评分调整方向）"""
        if avg_overall < 0.5:
            new_templates = [
                "{b}与{a}形成互补，联合解决[效率低]痛点",
                "{a}+{b}组合使开发迭代速度提升40%",
            ]
        else:
            new_templates = [
                "{b}为{a}用户提供差异化能力，组合后ROI提升60%",
                "{a}开发者使用{b}后月活留存率提升25%",
            ]

        for template in new_templates:
            for rel_type in ["上游供应", "服务依赖", "衍生关联"]:
                if template not in self.description_templates.get(rel_type, []):
                    if rel_type not in self.description_templates:
                        self.description_templates[rel_type] = []
                    self.description_templates[rel_type].append(template)

    def _evolve_scoring_weights(self, avg_overall: float):
        """基于综合评分调整评分权重"""
        if avg_overall > 0.7:
            self.scoring_weights["strength"] = min(0.35, self.scoring_weights["strength"] + 0.02)
            self.scoring_weights["conflict_low"] = max(0.10, self.scoring_weights["conflict_low"] - 0.01)
        elif avg_overall < 0.4:
            self.scoring_weights["mcp_high"] = min(0.30, self.scoring_weights["mcp_high"] + 0.03)
            self.scoring_weights["layer3_bonus"] = min(0.25, self.scoring_weights["layer3_bonus"] + 0.02)

    def _evolve_action_templates(self, avg_overall: float):
        """扩展行动建议模板"""
        new_actions = {
            "基础设施": [
                "①注册{name}开发者账号 → ②申请API测试额度 → ③编写OpenClaw集成demo → ④提交GitHub PR",
            ],
            "服务": [
                "①联系3家使用{name}的企业 → ②访谈痛点 → ③输出需求文档 → ④基于反馈优化SOP",
            ],
        }
        for category, templates in new_actions.items():
            if category not in self.action_templates:
                self.action_templates[category] = []
            for template in templates:
                if template not in self.action_templates[category]:
                    self.action_templates[category].append(template)

    def _adjust_weights_by_rule_quality(self):
        """v2.1: 基于规则质量调整评分权重"""
        if not self.rule_tracker:
            return

        # 计算高质量规则比例
        high_quality = sum(1 for r in self.rule_tracker.values() if r.quality == RuleQuality.HIGH)
        total_rules = len(self.rule_tracker)
        high_ratio = high_quality / total_rules if total_rules > 0 else 0

        # 高质量规则多 → 提高action权重（规则更可靠）
        if high_ratio > 0.6:
            self.multi_dim_weights["action_score"] = min(0.4, self.multi_dim_weights["action_score"] + 0.05)
        # 低质量规则多 → 提高feedback权重（需要更多反馈校准）
        elif high_ratio < 0.3:
            self.multi_dim_weights["feedback_score"] = min(0.3, self.multi_dim_weights["feedback_score"] + 0.05)

    def _smart_decay_rules(self):
        """v2.1: 智能规则衰减"""
        decay_candidates = []
        for rule_id, tracker in self.rule_tracker.items():
            if tracker.should_decay():
                decay_candidates.append(rule_id)

        # 标记为decayed但不立即删除（保留用于分析）
        for rule_id in decay_candidates:
            self.rule_tracker[rule_id].quality = RuleQuality.DECAYED
            self.rule_tracker[rule_id].decay_count += 1

    # ============== 仪表盘 ==============

    def get_dashboard_brief(self) -> dict:
        """
        v2.1: 自进化仪表盘简报

        Returns:
            包含关键指标的简报
        """
        # 规则质量分布
        rule_quality_dist = {
            "high": 0,
            "medium": 0,
            "low": 0,
            "decayed": 0,
        }
        for tracker in self.rule_tracker.values():
            rule_quality_dist[tracker.quality.value] += 1

        # 跨域模式统计
        cross_domain_patterns = [
            p for p in self.discovered_patterns
            if isinstance(p, dict) and "cross_domain" in p.get("type", "")
        ]

        # 最近进化趋势
        recent_trends = []
        for record in self.evolution_history[-5:]:
            recent_trends.append({
                "round": record["round"],
                "overall": record["multi_dim_score"]["overall"],
                "timestamp": record["timestamp"],
            })

        # mini-evolve统计
        mini_evolve_count = len(self.mini_evolve_log)
        last_mini_evolve = self.mini_evolve_log[-1] if self.mini_evolve_log else None

        return {
            "evolution_round": self.evolution_round,
            "system_health": self._assess_system_health(rule_quality_dist),
            "rule_quality": {
                "distribution": rule_quality_dist,
                "total_active": len([r for r in self.rule_tracker.values() if r.quality != RuleQuality.DECAYED]),
                "total_rules": len(self.rule_tracker),
            },
            "cross_domain": {
                "patterns_count": len(cross_domain_patterns),
                "transferable_domains": list(set(
                    p.get("target_domain", "")
                    for p in cross_domain_patterns
                )),
            },
            "feedback_loop": {
                "total_feedback": len(self.feedback_history),
                "pending_negative": len(self.feedback_processor.pending_negative),
                "mini_evolve_count": mini_evolve_count,
                "last_mini_evolve": last_mini_evolve,
            },
            "recent_trends": recent_trends,
            "multi_dim_weights": self.multi_dim_weights,
        }

    def _assess_system_health(self, rule_quality_dist: dict) -> str:
        """评估系统健康度"""
        total = sum(rule_quality_dist.values())
        if total == 0:
            return "🟡 初始化中"

        decayed_ratio = rule_quality_dist.get("decayed", 0) / total
        high_ratio = rule_quality_dist.get("high", 0) / total

        if decayed_ratio > 0.5:
            return "🔴 需要清理"
        elif high_ratio > 0.6:
            return "🟢 健康"
        elif rule_quality_dist.get("low", 0) + rule_quality_dist.get("decayed", 0) > total * 0.4:
            return "🟠 需要优化"
        else:
            return "🟡 正常"

    # ============== 原有兼容方法 ==============

    @staticmethod
    def should_evolve(evolution_round: int, feedback_count: int, threshold: int = 5) -> bool:
        """纯函数触发判断"""
        return (evolution_round > 0 and evolution_round % threshold == 0) or feedback_count >= 3

    def self_reflect(self, analysis_result: dict) -> str:
        """Self-Reflection循环"""
        multi_dim = self._evaluate_multi_dimensional(analysis_result)

        suggestions = []
        if multi_dim["depth"] < 0.5:
            suggestions.append("建议扩展跨层类型发现以提升深度")
        if multi_dim["novelty"] < 0.4:
            suggestions.append("建议增加服务-基础设施MCP机会识别")
        if multi_dim["action"] < 0.5:
            suggestions.append("建议强化Layer3机会的具体行动路径")

        # 考虑跨域模式
        transferable = self.cross_domain_miner.get_transferable_patterns("AI")
        if transferable:
            suggestions.append(f"可迁移{len(transferable)}条跨域模式")

        return " | ".join(suggestions) if suggestions else "多维度评分均衡，暂无需强制改进"

    def get_evolution_report(self) -> dict:
        """获取自进化报告"""
        recent = self.evolution_history[-1]["multi_dim_score"] if self.evolution_history else None
        return {
            "total_rounds": self.evolution_round,
            "current_multi_dim": recent,
            "multi_dim_weights": self.multi_dim_weights,
            "generated_rules_count": len(self.rule_tracker),
            "discovered_patterns": len(self.discovered_patterns),
            "feedback_received": len(self.feedback_history),
            "description_template_count": sum(len(v) for v in self.description_templates.values()),
            "recent_patterns": self.discovered_patterns[-3:] if self.discovered_patterns else [],
            "evolution_log": self.evolution_log,
            "dashboard": self.get_dashboard_brief(),
        }


# ============== 演示 ==============

if __name__ == "__main__":
    print("🔄 SelfEvolutionManager v2.1 演示\n")

    manager = SelfEvolutionManagerV21()

    # 模拟几轮分析
    for i in range(8):
        analysis = {
            "node_count": 20 + i * 5,
            "rel_count": 100 + i * 20,
            "mcp_high_count": 5 + i,
            "top_score": 7 + (i % 3),
        }

        # 模拟反馈
        feedback = None
        if i > 0:
            feedback = {
                "adopted": i % 2 == 0,
                "type": "description" if i % 2 == 0 else "action",
                "content": f"测试反馈 {i}",
                "severity": "critical" if i == 3 else "normal",
            }

        result = manager.record_round(analysis, feedback)
        print(f"Round {i+1}: overall={result['overall']:.3f}")

    # 输出仪表盘
    print("\n" + "=" * 50)
    print("📊 自进化仪表盘 v2.1")
    print("=" * 50)
    dashboard = manager.get_dashboard_brief()
    print(f"系统健康: {dashboard['system_health']}")
    print(f"总轮次: {dashboard['evolution_round']}")
    print(f"活跃规则: {dashboard['rule_quality']['total_active']}/{dashboard['rule_quality']['total_rules']}")
    print(f"跨域模式: {dashboard['cross_domain']['patterns_count']}")
    print(f"mini-evolve次数: {dashboard['feedback_loop']['mini_evolve_count']}")
    print(f"\n规则质量分布: {dashboard['rule_quality']['distribution']}")