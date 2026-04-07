"""
深度生态挖掘引擎 v3.0
Deep Ecosystem Miner — 多层递归生态发现与关系分析

核心能力：
1. 多层递归发现（默认3层，可配置至5层）
2. 节点间关系图数据库式查询
3. 跨层关系分析
4. 关系强度计算

层级定义：
- 第1层：核心爆发点（OpenClaw）
- 第2层：直接生态节点（LLM API/教程/插件）
- 第3层：间接生态节点（GPU供应商/视频平台/开发工具）

使用方式：
from deep_miner import DeepEcosystemMiner

miner = DeepEcosystemMiner()
result = miner.deep_discover("OpenClaw", depth=3)
rel = miner.find_node_relations(node_a_id, node_b_id)
"""

from dataclasses import dataclass, field
from typing import Optional, Any, TYPE_CHECKING
from datetime import datetime
from collections import deque
import re

if TYPE_CHECKING:
    from self_evolution import SelfEvolutionManager

# 从 unified_enums 导入枚举
from unified_enums import EcosystemNodeType, OpportunityType

# v4.0: 事件总线集成
try:
    from evolution_event_bus import EventBus, EvolutionEventType
    _EVENT_BUS_AVAILABLE = True
except ImportError:
    _EVENT_BUS_AVAILABLE = False
    EvolutionEventType = None


# ============== 配置 ==============

@dataclass
class DeepMiningConfig:
    """深度挖掘配置"""
    max_depth: int = 3           # 最大深度（3-5层可配置）
    cross_layer_analysis: bool = True  # 是否启用跨层关系分析
    similarity_threshold: float = 0.6  # 节点相似度阈值


# ============== 关系数据结构 ==============

@dataclass
class NodeRelationship:
    """节点间关系（含增强属性分析）"""
    node_a: str                   # 节点A ID
    node_b: str                   # 节点B ID
    relation_type: str            # "供应链"/"服务依赖"/"替代"/"互补"/"竞争"
    strength: float = 0.0         # 关系强度 0-1

    # ========== v1.1 增强属性 ==========
    conflict_level: str = "低"     # 利益冲突程度：高/中/低
    resource_direction: str = ""  # 资源依赖方向：上游/下游/竞争/合作
    mcp_potential: str = "低"      # MCP集成潜力：低/中/高

    # ========== v1.2 新增 ==========
    shovel_score: int = 1         # 卖铲子机会评分 1-10
    specific_description: str = "" # 项目特异性描述（1句）
    mcp_suggestion: str = ""      # MCP具体集成建议

    path: list = field(default_factory=list)  # 关联路径

    def exists(self) -> bool:
        """判断关系是否存在"""
        return self.strength > 0

    def get_shovel_label(self) -> str:
        """获取卖铲子机会标签"""
        if self.shovel_score >= 8:
            return "⭐⭐⭐ 强烈推荐"
        elif self.shovel_score >= 6:
            return "⭐⭐ 建议关注"
        elif self.shovel_score >= 4:
            return "⭐ 观察"
        else:
            return "暂不推荐"


@dataclass
class DiscoveredNode:
    """带深度信息的节点"""
    node_id: str
    name: str
    node_type: EcosystemNodeType
    parent_id: str = ""
    depth: int = 0                # 所在层深
    description: str = ""
    children: list = field(default_factory=list)  # 子节点ID列表


@dataclass
class DiscoveryResult:
    """深度发现结果"""
    core_node: str                        # 核心节点名称
    depth_reached: int                    # 实际到达深度
    all_nodes: dict[str, DiscoveredNode]  # 所有节点 {node_id: node}
    relationships: list[NodeRelationship]  # 发现的关系
    layer_summary: dict[int, int]         # 每层节点数 {depth: count}
    opportunities: list = field(default_factory=list)  # 生成的机会
    execution_time: str = ""              # 执行时间
    self_reflection: str = ""             # v1.5 Self-Reflection改进建议

    def get_nodes_at_depth(self, depth: int) -> list[DiscoveredNode]:
        """获取指定深度的所有节点"""
        return [n for n in self.all_nodes.values() if n.depth == depth]

    def get_total_nodes(self) -> int:
        return len(self.all_nodes)


# ============== 自进化管理器 v2.0 ==============

class SelfEvolutionManager:
    """
    自进化管理器 v3.0 — 规则生成型

    v3.0升级：
    - 异常安全：进化失败不影响主流程
    - 纯函数触发：should_evolve()不依赖side effect
    - 统一评分源：_evaluate_multi_dimensional()为单一数据源
    """

    def __init__(self):
        self.evolution_round = 0
        self.evolution_history = []

        # v2.0: 多维度评分权重
        self.multi_dim_weights = {
            "depth_score": 0.25,      # 深度评分
            "novelty_score": 0.25,    # 新颖度评分
            "action_score": 0.30,     # 可执行性评分
            "feedback_score": 0.20,   # 反馈采纳率
        }

        # v2.0: 自生成规则库（从历史数据挖掘）
        self.generated_rules = {
            "description_rules": [],   # 自生成的描述规则
            "scoring_rules": [],       # 自生成的评分规则
            "action_rules": [],        # 自生成的行动规则
        }

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

        # v2.0: 发现的模式
        self.discovered_patterns = []

    @staticmethod
    def should_evolve(evolution_round: int, feedback_count: int, threshold: int = 5) -> bool:
        """v3.0: 纯函数触发判断（不依赖side effect）"""
        return (evolution_round > 0 and evolution_round % threshold == 0) or feedback_count >= 3

    def record_round(self, analysis_result: dict, feedback: dict = None) -> dict:
        """v3.0: 记录一轮分析（含多维度评分，异常安全）"""
        self.evolution_round += 1

        # v3.0: 多维度评分（单一数据源）
        multi_dim = self._evaluate_multi_dimensional(analysis_result)

        record = {
            "round": self.evolution_round,
            "multi_dim_score": multi_dim,
            "feedback": feedback,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "analysis_summary": analysis_result,
        }
        self.evolution_history.append(record)

        # v3.0: 记录用户反馈
        if feedback:
            self._learn_from_feedback(feedback, analysis_result)

        # v3.0: 模式挖掘（每3轮）
        if self.evolution_round % 3 == 0:
            self._mine_patterns()

        # v3.0: 解耦触发判断（纯函数）
        unprocessed_feedback = len([f for f in self.feedback_history if not f.get("incorporated")])
        if self.should_evolve(self.evolution_round, unprocessed_feedback):
            try:
                self._auto_evolve(multi_dim)
            except Exception as e:
                # v3.0: 异常安全 - 进化失败不影响主流程
                self.evolution_error = str(e)

        return multi_dim

    def _evaluate_multi_dimensional(self, analysis_result: dict) -> dict:
        """v2.0: 多维度评估"""
        # 深度评分：基于节点数和关系数
        node_count = analysis_result.get("node_count", 0)
        rel_count = analysis_result.get("rel_count", 0)
        depth_score = min((node_count / 50 + rel_count / 1000) / 2, 1.0)

        # 新颖度评分：基于MCP高潜力数量
        mcp_high = analysis_result.get("mcp_high_count", 0)
        novelty_score = min(mcp_high / 50, 1.0)

        # 可执行性评分：基于Top1机会评分
        top_score = analysis_result.get("top_score", 0)
        action_score = top_score / 10.0

        # 反馈采纳率
        recent_feedback = [r for r in self.feedback_history[-5:] if r.get("adopted")]
        feedback_score = len(recent_feedback) / 5 if recent_feedback else 0.5

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

    def _learn_from_feedback(self, feedback: dict, analysis_result: dict):
        """v2.0: 从用户反馈学习"""
        self.feedback_history.append({
            "round": self.evolution_round,
            "feedback": feedback,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        # 如果反馈被采纳，生成规则
        if feedback.get("adopted", False):
            self._generate_rule_from_feedback(feedback, analysis_result)

    def _generate_rule_from_feedback(self, feedback: dict, analysis_result: dict):
        """v2.0: 从反馈生成新规则"""
        rule_type = feedback.get("type", "description")
        content = feedback.get("content", "")

        if rule_type == "description" and content:
            # 生成描述规则
            rule = {
                "trigger": analysis_result.get("relation_type", "通用"),
                "pattern": content,
                "source": f"feedback_round_{self.evolution_round}",
                "effectiveness": 0.8,
            }
            self.generated_rules["description_rules"].append(rule)

        elif rule_type == "action" and content:
            # 生成行动规则
            rule = {
                "trigger": analysis_result.get("node_type", "通用"),
                "pattern": content,
                "source": f"feedback_round_{self.evolution_round}",
                "effectiveness": 0.8,
            }
            self.generated_rules["action_rules"].append(rule)

    def _mine_patterns(self):
        """v2.1: 从历史数据挖掘新模式（含跨域模式）"""
        if len(self.evolution_history) < 3:
            return

        recent = self.evolution_history[-3:]
        high_scores = [r for r in recent if r["multi_dim_score"]["overall"] > 0.6]

        # v2.1: 基础模式挖掘
        if len(high_scores) >= 2:
            pattern = {
                "type": "high_score_pattern",
                "trigger": "mcp_high_count >= 30 AND top_score >= 8",
                "score": sum(r["multi_dim_score"]["overall"] for r in high_scores) / len(high_scores),
                "source": f"mined_round_{self.evolution_round}",
            }
            if pattern not in self.discovered_patterns:
                self.discovered_patterns.append(pattern)

        # v2.1: 跨域模式发现（电商痛点→内容创作痛点迁移）
        if len(self.evolution_history) >= 5:
            recent5 = self.evolution_history[-5:]
            # 检测深度+新颖度都高的轮次（跨域成功标志）
            cross_domain_success = [r for r in recent5
                                    if r["multi_dim_score"]["depth"] > 0.7
                                    and r["multi_dim_score"]["novelty"] > 0.7]
            if len(cross_domain_success) >= 2:
                cross_pattern = {
                    "type": "cross_domain_pattern",
                    "trigger": "内容创作痛点可借鉴电商的高转化链路模式",
                    "source_domain": "电商",
                    "target_domain": "内容创作",
                    "score": sum(r["multi_dim_score"]["overall"] for r in cross_domain_success) / len(cross_domain_success),
                    "source": f"cross_domain_round_{self.evolution_round}",
                }
                if cross_pattern not in self.discovered_patterns:
                    self.discovered_patterns.append(cross_pattern)

        # v2.1: 行动模式挖掘（高效行动路径识别）
        action_high = [r for r in recent if r["multi_dim_score"]["action"] > 0.8]
        if action_high:
            action_pattern = {
                "type": "action_pattern",
                "trigger": "GitHub+掘金渠道组合在基础设施类机会中效果最佳",
                "score": sum(r["multi_dim_score"]["action"] for r in action_high) / len(action_high),
                "source": f"action_pattern_round_{self.evolution_round}",
            }
            if action_pattern not in self.discovered_patterns:
                self.discovered_patterns.append(action_pattern)

    def _auto_evolve(self, multi_dim: dict = None):
        """v2.0: 自进化"""
        recent = self.evolution_history[-5:]
        avg_overall = sum(r["multi_dim_score"]["overall"] for r in recent) / len(recent) if recent else 0.5

        # v2.0: 规则自生成（基于模式挖掘）
        self._generate_rules_from_patterns()

        # v2.0: 动态调整多维度权重
        if multi_dim:
            if multi_dim["novelty"] < 0.4:
                self.multi_dim_weights["novelty_score"] += 0.05
                self.multi_dim_weights["depth_score"] -= 0.02
            if multi_dim["action"] < 0.5:
                self.multi_dim_weights["action_score"] += 0.03

        # 标准化权重
        total = sum(self.multi_dim_weights.values())
        self.multi_dim_weights = {k: v/total for k, v in self.multi_dim_weights.items()}

        # 进化描述模板
        self._evolve_description_templates(avg_overall)

        # 进化评分权重
        self._evolve_scoring_weights(avg_overall)

        # 进化行动模板
        self._evolve_action_templates(avg_overall)

        # v2.1: 标记反馈已处理
        for f in self.feedback_history:
            if not f.get("incorporated"):
                f["incorporated"] = True

        # v2.1: 规则质量衰减机制（每10轮）
        if self.evolution_round % 10 == 0:
            self._decay_low_quality_rules()

        # v2.1: 确保每轮至少生成1条行动规则
        self._ensure_action_rule_generation(multi_dim)

        self.evolution_log = {
            "evolved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "avg_overall": avg_overall,
            "new_multi_dim_weights": dict(self.multi_dim_weights),
            "rules_generated": len(self.generated_rules["description_rules"]),
            "patterns_discovered": len(self.discovered_patterns),
            "action_rules_current": len(self.generated_rules["action_rules"]),
        }

    def _generate_rules_from_patterns(self):
        """v2.0: 从发现模式生成规则"""
        for pattern in self.discovered_patterns[-3:]:
            if pattern["type"] == "high_score_pattern":
                # 基于高评分模式生成描述规则
                rule = {
                    "trigger": "mcp_high",
                    "pattern": f"高MCP潜力节点组合的完播率比普通组合高{pattern['score']*100:.0f}%",
                    "source": f"pattern_round_{self.evolution_round}",
                    "effectiveness": pattern["score"],
                }
                if rule not in self.generated_rules["description_rules"]:
                    self.generated_rules["description_rules"].append(rule)

    def _evolve_description_templates(self, avg_overall: float):
        """扩展描述模板库（基于综合评分调整方向）"""
        if avg_overall < 0.5:
            # 低评分时增加痛点导向模板
            new_templates = [
                "{b}与{a}形成互补，联合解决[效率低]痛点",
                "{a}+{b}组合使开发迭代速度提升40%",
            ]
        else:
            # 高评分时增加价值导向模板
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
            self.scoring_weights["strength"] = min(self.scoring_weights["strength"] + 0.02, 0.35)
            self.scoring_weights["conflict_low"] = max(self.scoring_weights["conflict_low"] - 0.01, 0.10)
        elif avg_overall < 0.4:
            self.scoring_weights["mcp_high"] = min(self.scoring_weights["mcp_high"] + 0.03, 0.30)
            self.scoring_weights["layer3_bonus"] = min(self.scoring_weights["layer3_bonus"] + 0.02, 0.25)

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

    def _decay_low_quality_rules(self):
        """v2.1: 规则质量衰减机制 - 淘汰低效规则"""
        decay_threshold = 0.4
        decay_rate = 0.9

        rules_decayed = 0
        for rule_type in ["description_rules", "scoring_rules", "action_rules"]:
            remaining = []
            for rule in self.generated_rules.get(rule_type, []):
                # 每次检查将effectiveness衰减
                rule["effectiveness"] *= decay_rate
                if rule["effectiveness"] >= decay_threshold:
                    remaining.append(rule)
                else:
                    rules_decayed += 1
            self.generated_rules[rule_type] = remaining

        # 记录衰减日志
        if not hasattr(self, 'decay_log'):
            self.decay_log = []
        self.decay_log.append({
            "round": self.evolution_round,
            "rules_decayed": rules_decayed,
            "remaining": sum(len(v) for v in self.generated_rules.values()),
        })

    def _ensure_action_rule_generation(self, multi_dim: dict = None):
        """v2.1: 确保每轮至少生成1条行动规则"""
        current_action_rules = len(self.generated_rules.get("action_rules", []))

        if current_action_rules == 0:
            # 首条行动规则：基于多维度评分生成
            action_rule = {
                "trigger": "auto_generated",
                "pattern": "GitHub+掘金组合适合开发者用户，知乎+B站适合企业用户",
                "source": f"auto_round_{self.evolution_round}",
                "effectiveness": 0.6,
            }
            self.generated_rules.setdefault("action_rules", []).append(action_rule)
        elif multi_dim and multi_dim["action"] < 0.6:
            # 行动评分低时，生成补救规则
            remedial_rule = {
                "trigger": f"action_low_round_{self.evolution_round}",
                "pattern": "增加具体数字目标（如：3篇笔记/周）提升可执行性",
                "source": "remedial_generation",
                "effectiveness": 0.5,
            }
            self.generated_rules.setdefault("action_rules", []).append(remedial_rule)

    def self_reflect(self, analysis_result: dict) -> str:
        """v2.0: Self-Reflection循环"""
        multi_dim = self._evaluate_multi_dimensional(analysis_result)

        questions = [
            f"深度足够？{analysis_result.get('node_count', 0)}节点/{analysis_result.get('rel_count', 0)}关系 (评分:{multi_dim['depth']:.2f})",
            f"足够新颖？{analysis_result.get('mcp_high_count', 0)}个MCP高潜力点 (评分:{multi_dim['novelty']:.2f})",
            f"可执行性强？Top1评分{analysis_result.get('top_score', 0)}/10 (评分:{multi_dim['action']:.2f})",
            f"用户反馈好？最近{len([f for f in self.feedback_history[-5:]])}条反馈",
        ]

        reflection = {
            "round": self.evolution_round,
            "questions": questions,
            "multi_dim": multi_dim,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.reflection_journal.append(reflection)

        suggestions = []
        if multi_dim["depth"] < 0.5:
            suggestions.append("建议扩展跨层类型发现以提升深度")
        if multi_dim["novelty"] < 0.4:
            suggestions.append("建议增加服务-基础设施MCP机会识别")
        if multi_dim["action"] < 0.5:
            suggestions.append("建议强化Layer3机会的具体行动路径")

        # v2.0: 考虑已发现的模式
        for pattern in self.discovered_patterns[-2:]:
            if pattern["score"] > 0.7:
                suggestions.append(f"模式复用: {pattern['trigger']}")

        return " | ".join(suggestions) if suggestions else "多维度评分均衡，暂无需强制改进"

    def get_evolution_report(self) -> dict:
        """v2.0: 获取自进化报告"""
        recent = self.evolution_history[-1]["multi_dim_score"] if self.evolution_history else None
        return {
            "total_rounds": self.evolution_round,
            "current_multi_dim": recent,
            "multi_dim_weights": self.multi_dim_weights,
            "generated_rules_count": sum(len(v) for v in self.generated_rules.values()),
            "discovered_patterns": len(self.discovered_patterns),
            "feedback_received": len(self.feedback_history),
            "description_template_count": sum(len(v) for v in self.description_templates.values()),
            "recent_patterns": self.discovered_patterns[-3:] if self.discovered_patterns else [],
            "evolution_log": getattr(self, 'evolution_log', None),
        }


# ============== 深度生态挖掘引擎 ==============

class DeepEcosystemMiner:
    """
    深度生态挖掘引擎 v3.0

    实现多层递归生态发现和节点关系分析

    v3.0升级：
    - 异常安全：进化失败不影响主流程
    - 纯函数触发：should_evolve()不依赖side effect
    - 增量关系分析：O(n²) → 增量计算+缓存
    """

    def __init__(self, config: DeepMiningConfig = None, evolution_manager: 'SelfEvolutionManager' = None,
                 event_bus=None):
        self.config = config or DeepMiningConfig()
        self.evolution_manager = evolution_manager

        # v4.0: 事件总线（可选，用于模块间解耦）
        self._event_bus = event_bus
        if self._event_bus is None and _EVENT_BUS_AVAILABLE:
            self._event_bus = EventBus.get_instance()

        # 节点存储
        self.nodes: dict[str, DiscoveredNode] = {}
        self.relationships: list[NodeRelationship] = []
        self.node_counter = 0
        self.result = None  # 当前结果引用

        # v1.1 新增字段
        self.layer3_opportunities: list = []  # Layer3隐藏机会
        self.accuracy_history: list = []     # 准确率历史
        self.coverage_history: list = []    # 覆盖率历史

        # v3.0: 关系分析缓存
        self._rel_cache: dict[str, float] = {}  # (node_a_id, node_b_id) -> strength
        self._last_node_count: int = 0

        # 关系图（用于路径查找）
        self.graph: dict[str, list[str]] = {}  # node_id -> [connected_node_ids]
        self.type_keywords: dict[EcosystemNodeType, list[str]] = self._init_type_keywords()

    def _publish_event(self, event_type: str, data: dict):
        """v4.0: 发布事件到事件总线"""
        if self._event_bus:
            self._event_bus.publish(event_type, data, source_module="DeepEcosystemMiner")

    def _init_type_keywords(self) -> dict:
        """初始化每层类型对应的关键词"""
        return {
            EcosystemNodeType.INFRASTRUCTURE: [
                "LLM API", "GPU", "云服务器", "数据库", "支付", "短信",
                "数据提供商", "API网关", "CDN", "存储服务"
            ],
            EcosystemNodeType.SERVICE: [
                "教程", "课程", "咨询", "定制开发", "插件开发", "主题模板",
                "视频平台", "博客平台", "知识付费", "培训"
            ],
            EcosystemNodeType.DERIVATIVE: [
                "社区", "媒体", "导航站", "评测", "聚合器",
                "社群工具", "活动平台", "UGC平台", "内容平台"
            ],
            EcosystemNodeType.USER: [
                "普通用户", "企业用户", "开发者", "小型团队"
            ],
            EcosystemNodeType.COMPETITOR: [
                "竞品", "替代品", "同类产品"
            ]
        }

    # ============== 主入口 ==============

    def deep_discover(self, core_name: str, depth: int = 3) -> DiscoveryResult:
        """
        深度递归发现

        Args:
            core_name: 核心节点名称
            depth: 发现深度（默认3层，最大5层）

        Returns:
            DiscoveryResult: 包含所有节点、关系、机会的结果
        """
        # 限制深度范围
        depth = min(max(depth, 1), self.config.max_depth)

        start_time = datetime.now()

        # v4.0: 发布发现开始事件
        self._publish_event("analysis.discovery.started", {
            "core_node": core_name,
            "requested_depth": depth,
            "start_time": start_time.isoformat(),
        })

        # 初始化
        self.nodes.clear()
        self.relationships.clear()
        self.graph.clear()
        self.node_counter = 0

        # 创建核心节点（第1层）
        core_node = self._create_node(
            name=core_name,
            node_type=EcosystemNodeType.CORE,
            depth=0
        )
        self._add_node(core_node)

        # 递归发现各层
        self._recursive_discover(core_node.node_id, 1, depth)

        # 跨层关系分析
        if self.config.cross_layer_analysis:
            self._analyze_cross_layer_relations()

        # 构建层统计
        layer_summary = {}
        for node in self.nodes.values():
            layer_summary[node.depth] = layer_summary.get(node.depth, 0) + 1

        # 构建结果对象
        result = DiscoveryResult(
            core_node=core_name,
            depth_reached=depth,
            all_nodes=self.nodes,
            relationships=self.relationships,
            layer_summary=layer_summary,
            opportunities=[],
            execution_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        # v1.1 设置结果引用后再生成机会和自适应
        self.result = result
        self._generate_deep_opportunities()
        self._record_accuracy()
        self._record_coverage()
        self._adjust_keyword_weights()

        # 更新结果中的机会列表
        result.opportunities = self.layer3_opportunities

        # v4.0: 发布发现完成事件（早于自进化集成）
        self._publish_event("analysis.discovery.completed", {
            "core_node": core_name,
            "depth_reached": depth,
            "total_nodes": len(self.nodes),
            "total_relationships": len(self.relationships),
            "opportunity_count": len(self.layer3_opportunities),
            "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
        })

        # v3.0 自进化集成：记录本轮 + Self-Reflection（异常安全）
        if self.evolution_manager:
            # 构建分析摘要（统一数据源）
            analysis_summary = {
                "node_count": len(self.nodes),
                "rel_count": len(self.relationships),
                "max_strength": max((r.strength for r in self.relationships), default=0),
                "mcp_high_count": len([r for r in self.relationships if r.mcp_potential == "高"]),
                "top_score": max((o["opportunity_score"] for o in self.layer3_opportunities), default=0) if self.layer3_opportunities else 0,
            }
            # v3.0: record_round内部已包含异常保护
            evolution_result = self.evolution_manager.record_round(analysis_summary)
            result.self_reflection = self.evolution_manager.self_reflect(analysis_summary)

            # v4.0: 发布自进化事件
            self._publish_event("evolution.round.recorded", {
                "evolution_round": self.evolution_manager.evolution_round,
                "reflection": result.self_reflection,
                "multi_dim_scores": evolution_result if isinstance(evolution_result, dict) else {},
            })

        return result

    def _recursive_discover(self, parent_id: str, current_depth: int, max_depth: int):
        """
        递归向下发现

        对第N层节点，发现第N+1层节点
        """
        if current_depth > max_depth:
            return

        parent = self.nodes.get(parent_id)
        if not parent:
            return

        # 根据父节点类型决定子节点发现模式
        child_patterns = self._get_child_patterns(parent, current_depth)

        for pattern_type, pattern_name in child_patterns:
            # 检查同名节点是否已存在（按名称去重）
            existing = self._find_node_by_name(pattern_name, current_depth)
            if existing:
                # 已存在，只建立边关系
                self._add_edge(parent_id, existing.node_id)
            else:
                # 创建新节点
                child = self._create_node(
                    name=pattern_name,
                    node_type=pattern_type,
                    parent_id=parent_id,
                    depth=current_depth
                )
                self._add_node(child)
                self._add_edge(parent_id, child.node_id)

                # 递归继续发现
                self._recursive_discover(child.node_id, current_depth + 1, max_depth)

    def _find_node_by_name(self, name: str, depth: int = None) -> Optional[DiscoveredNode]:
        """按名称查找已存在的节点"""
        for node in self.nodes.values():
            if node.name == name:
                if depth is None or node.depth == depth:
                    return node
        return None

    def _get_child_patterns(self, parent: DiscoveredNode, depth: int) -> list:
        """
        根据父节点获取子节点发现模式

        Returns:
            [(EcosystemNodeType, name), ...]
        """
        patterns = []

        if parent.node_type == EcosystemNodeType.CORE:
            # 核心节点 → 发现基础设施、服务、衍生、竞品、用户
            patterns = [
                (EcosystemNodeType.INFRASTRUCTURE, "LLM API"),
                (EcosystemNodeType.INFRASTRUCTURE, "云服务器"),
                (EcosystemNodeType.INFRASTRUCTURE, "数据库"),
                (EcosystemNodeType.INFRASTRUCTURE, "支付通道"),
                (EcosystemNodeType.SERVICE, "教程/培训"),
                (EcosystemNodeType.SERVICE, "咨询/方案"),
                (EcosystemNodeType.SERVICE, "定制开发"),
                (EcosystemNodeType.SERVICE, "插件/扩展"),
                (EcosystemNodeType.DERIVATIVE, "社区"),
                (EcosystemNodeType.DERIVATIVE, "媒体"),
                (EcosystemNodeType.COMPETITOR, "竞品"),
                (EcosystemNodeType.USER, "企业用户"),
            ]

        elif parent.node_type == EcosystemNodeType.INFRASTRUCTURE:
            # 基础设施 → 发现其供应链
            if "LLM" in parent.name or "API" in parent.name:
                patterns = [
                    (EcosystemNodeType.INFRASTRUCTURE, "GPU供应商"),
                    (EcosystemNodeType.INFRASTRUCTURE, "数据提供商"),
                    (EcosystemNodeType.INFRASTRUCTURE, "API网关服务"),
                    (EcosystemNodeType.INFRASTRUCTURE, "模型托管服务"),
                ]
            elif "云服务器" in parent.name or "服务器" in parent.name:
                patterns = [
                    (EcosystemNodeType.INFRASTRUCTURE, "IDC机房"),
                    (EcosystemNodeType.INFRASTRUCTURE, "CDN服务商"),
                    (EcosystemNodeType.INFRASTRUCTURE, "容器平台"),
                ]
            elif "数据库" in parent.name or "DB" in parent.name:
                patterns = [
                    (EcosystemNodeType.INFRASTRUCTURE, "数据存储"),
                    (EcosystemNodeType.INFRASTRUCTURE, "缓存服务"),
                    (EcosystemNodeType.INFRASTRUCTURE, "数据备份"),
                ]

        elif parent.node_type == EcosystemNodeType.SERVICE:
            # 服务 → 发现服务层衍生
            if "教程" in parent.name or "培训" in parent.name:
                patterns = [
                    (EcosystemNodeType.DERIVATIVE, "视频平台"),
                    (EcosystemNodeType.DERIVATIVE, "博客平台"),
                    (EcosystemNodeType.SERVICE, "知识付费平台"),
                    (EcosystemNodeType.SERVICE, "在线教育平台"),
                ]
            elif "咨询" in parent.name:
                patterns = [
                    (EcosystemNodeType.SERVICE, "行业报告"),
                    (EcosystemNodeType.SERVICE, "数据分析服务"),
                ]
            elif "定制开发" in parent.name or "插件" in parent.name:
                patterns = [
                    (EcosystemNodeType.DERIVATIVE, "开发者社区"),
                    (EcosystemNodeType.SERVICE, "开发工具"),
                    (EcosystemNodeType.SERVICE, "API文档服务"),
                ]

        elif parent.node_type == EcosystemNodeType.DERIVATIVE:
            # 衍生层 → 发现衍生生态
            if "社区" in parent.name:
                patterns = [
                    (EcosystemNodeType.SERVICE, "社群工具"),
                    (EcosystemNodeType.SERVICE, "活动平台"),
                    (EcosystemNodeType.DERIVATIVE, "UGC平台"),
                ]
            elif "媒体" in parent.name:
                patterns = [
                    (EcosystemNodeType.DERIVATIVE, "内容聚合"),
                    (EcosystemNodeType.SERVICE, "内容创作工具"),
                ]

        elif parent.node_type == EcosystemNodeType.COMPETITOR:
            # 竞品 → 发现竞品生态
            patterns = [
                (EcosystemNodeType.SERVICE, "跨平台教程"),
                (EcosystemNodeType.SERVICE, "多工具插件"),
                (EcosystemNodeType.DERIVATIVE, "对比评测"),
            ]

        return patterns

    def _create_node(self, name: str, node_type: EcosystemNodeType,
                     parent_id: str = "", depth: int = 0) -> DiscoveredNode:
        """创建新节点"""
        self.node_counter += 1
        return DiscoveredNode(
            node_id=f"DEEP_{self.node_counter:03d}",
            name=name,
            node_type=node_type,
            parent_id=parent_id,
            depth=depth
        )

    def _add_node(self, node: DiscoveredNode):
        """添加节点"""
        self.nodes[node.node_id] = node

    def _add_edge(self, from_id: str, to_id: str):
        """添加关系边"""
        if from_id not in self.graph:
            self.graph[from_id] = []
        if to_id not in self.graph:
            self.graph[to_id] = []
        if to_id not in self.graph[from_id]:
            self.graph[from_id].append(to_id)
        if from_id not in self.graph[to_id]:
            self.graph[to_id].append(from_id)

    # ============== v3.0 跨层关系分析（增量计算+缓存） ==============

    def _analyze_cross_layer_relations(self):
        """v3.0: 分析所有节点间的跨层关系（增量计算）"""
        nodes_list = list(self.nodes.values())
        current_count = len(nodes_list)

        # v3.0: 增量计算 - 如果节点数量变化不大，只分析新增节点对
        if current_count > self._last_node_count and self._last_node_count > 0:
            # 增量模式：只分析新增节点与现有节点的关系
            existing_nodes = nodes_list[:- (current_count - self._last_node_count)] if current_count - self._last_node_count < current_count else []
            new_nodes = nodes_list[self._last_node_count:]

            for node_a in new_nodes:
                for node_b in existing_nodes + new_nodes:
                    if node_a.node_id != node_b.node_id:
                        cache_key = self._get_cache_key(node_a.node_id, node_b.node_id)
                        if cache_key not in self._rel_cache:
                            relation = self._find_relation_between(node_a, node_b)
                            if relation.exists():
                                self.relationships.append(relation)
                                self._rel_cache[cache_key] = relation.strength
        else:
            # 全量模式：首次分析或节点大幅变化
            for i, node_a in enumerate(nodes_list):
                for node_b in nodes_list[i + 1:]:
                    cache_key = self._get_cache_key(node_a.node_id, node_b.node_id)
                    if cache_key in self._rel_cache:
                        # 从缓存恢复
                        strength = self._rel_cache[cache_key]
                        if strength > 0:
                            self.relationships.append(NodeRelationship(
                                node_a.node_id, node_b.node_id, "缓存恢复",
                                strength, path=[]
                            ))
                    else:
                        relation = self._find_relation_between(node_a, node_b)
                        if relation.exists():
                            self.relationships.append(relation)
                            self._rel_cache[cache_key] = relation.strength

        self._last_node_count = current_count

    def _get_cache_key(self, node_a_id: str, node_b_id: str) -> str:
        """v3.0: 生成缓存键（保证有序）"""
        return tuple(sorted([node_a_id, node_b_id])).__repr__()

    def _find_relation_between(self, node_a: DiscoveredNode, node_b: DiscoveredNode) -> NodeRelationship:
        """
        查找两个节点间的关系

        使用BFS找最短路径
        """
        if node_a.node_id == node_b.node_id:
            return NodeRelationship(node_a.node_id, node_b.node_id, "自身", 0.0)

        # BFS找路径
        path = self._bfs_path(node_a.node_id, node_b.node_id)

        if not path:
            # 无路径，检查是否有隐含关系
            return self._check_implicit_relation(node_a, node_b)

        # 计算关系强度
        path_length = len(path) - 1  # 边数
        strength = self._calculate_strength(path_length, node_a, node_b)

        # 判断关系类型
        relation_type = self._classify_relation(node_a, node_b, path)

        # 构建基础关系
        base_rel = NodeRelationship(
            node_a=node_a.node_id,
            node_b=node_b.node_id,
            relation_type=relation_type,
            strength=strength,
            path=path
        )

        # v1.1 增强属性分析
        return self._analyze_enhanced_attributes(node_a, node_b, base_rel, path)

    def _bfs_path(self, start_id: str, end_id: str) -> list:
        """
        BFS查找最短路径

        Returns:
            [node_id, ...] 路径列表
        """
        if start_id == end_id:
            return [start_id]

        queue = deque([(start_id, [start_id])])
        visited = {start_id}

        while queue:
            current, path = queue.popleft()

            for neighbor in self.graph.get(current, []):
                if neighbor == end_id:
                    return path + [neighbor]

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return []  # 无路径

    def _calculate_strength(self, path_length: int, node_a: DiscoveredNode, node_b: DiscoveredNode) -> float:
        """
        计算关系强度（支持自适应动态调整）

        直接关系 = 1.0
        1层间接 = 0.8
        2层间接 = 0.5
        3层间接 = 0.3
        """
        # 基础强度
        if path_length == 1:
            strength = 1.0
        elif path_length == 2:
            strength = 0.8
        elif path_length == 3:
            strength = 0.5
        else:
            strength = 0.3

        # 同层加成
        if node_a.depth == node_b.depth and node_a.depth > 0:
            strength += 0.1

        # 类型关联加成
        if self._are_complementary_types(node_a.node_type, node_b.node_type):
            strength += 0.1

        # v1.2: 应用自适应强度调整因子
        adjusted = self.get_dynamic_strength(strength)
        return adjusted

    def _are_complementary_types(self, type_a: EcosystemNodeType, type_b: EcosystemNodeType) -> bool:
        """判断两个类型是否互补"""
        complementary_pairs = [
            (EcosystemNodeType.INFRASTRUCTURE, EcosystemNodeType.SERVICE),
            (EcosystemNodeType.SERVICE, EcosystemNodeType.DERIVATIVE),
            (EcosystemNodeType.CORE, EcosystemNodeType.USER),
        ]
        return (type_a, type_b) in complementary_pairs or (type_b, type_a) in complementary_pairs

    def _classify_relation(self, node_a: DiscoveredNode, node_b: DiscoveredNode, path: list) -> str:
        """分类关系类型"""
        # 同层同父节点
        if node_a.parent_id == node_b.parent_id and node_a.parent_id != "":
            return "同源竞争"

        # 上下游关系
        if node_a.node_type == EcosystemNodeType.INFRASTRUCTURE and node_b.node_type == EcosystemNodeType.CORE:
            return "上游供应"
        if node_b.node_type == EcosystemNodeType.INFRASTRUCTURE and node_a.node_type == EcosystemNodeType.CORE:
            return "上游供应"

        # 服务依赖
        if node_a.node_type == EcosystemNodeType.SERVICE or node_b.node_type == EcosystemNodeType.SERVICE:
            return "服务依赖"

        # 衍生关系
        if node_a.node_type == EcosystemNodeType.DERIVATIVE or node_b.node_type == EcosystemNodeType.DERIVATIVE:
            return "衍生关联"

        # 竞争关系
        if node_a.node_type == EcosystemNodeType.COMPETITOR or node_b.node_type == EcosystemNodeType.COMPETITOR:
            return "替代竞争"

        return "一般关联"

    def _check_implicit_relation(self, node_a: DiscoveredNode, node_b: DiscoveredNode) -> NodeRelationship:
        """检查隐含关系（无直接路径但可能存在关联）"""
        # 检查类型相似度
        similarity = self.calculate_similarity(node_a, node_b)

        if similarity >= self.config.similarity_threshold:
            base_rel = NodeRelationship(
                node_a=node_a.node_id,
                node_b=node_b.node_id,
                relation_type="隐含关联",
                strength=similarity * 0.5,  # 隐含关系强度打折
                path=[]
            )
            # v1.1 增强属性分析
            return self._analyze_enhanced_attributes(node_a, node_b, base_rel, [])

        return NodeRelationship(node_a.node_id, node_b.node_id, "无关系", 0.0)

    # ============== v1.1 增强属性分析 ==============

    def _analyze_enhanced_attributes(self, node_a: DiscoveredNode, node_b: DiscoveredNode,
                                     base_rel: NodeRelationship, path: list) -> NodeRelationship:
        """
        分析节点对的增强属性

        包括：利益冲突程度、资源依赖方向、MCP集成潜力、卖铲子机会评分
        """
        # 1. 利益冲突程度分析
        conflict = self._analyze_conflict(node_a, node_b, base_rel)

        # 2. 资源依赖方向
        direction = self._analyze_resource_direction(node_a, node_b, path)

        # 3. MCP集成潜力（返回级别和建议）
        mcp_level, mcp_suggestion = self._analyze_mcp_potential(node_a, node_b)

        # 4. 项目特异性描述
        specific_desc = self._generate_specific_description(node_a, node_b, base_rel)

        # 5. 卖铲子机会评分
        shovel_score = self._calculate_shovel_score(node_a, node_b, base_rel, conflict, mcp_level)

        return NodeRelationship(
            node_a=base_rel.node_a,
            node_b=base_rel.node_b,
            relation_type=base_rel.relation_type,
            strength=base_rel.strength,
            conflict_level=conflict,
            resource_direction=direction,
            mcp_potential=mcp_level,
            shovel_score=shovel_score,
            specific_description=specific_desc,
            mcp_suggestion=mcp_suggestion,
            path=path
        )

    def _generate_specific_description(self, node_a: DiscoveredNode, node_b: DiscoveredNode,
                                       base_rel: NodeRelationship) -> str:
        """生成项目特异性描述（1句）- v1.4新增跨节点关联洞察（共同解决痛点）"""
        a_type = node_a.node_type.value
        b_type = node_b.node_type.value
        a_depth = node_a.depth
        b_depth = node_b.depth

        # v1.4: 每条描述必须包含"跨节点关联洞察"——两个节点如何共同解决痛点
        if base_rel.relation_type == "上游供应":
            return f"{node_b.name}解决{node_a.name}的算力成本痛点，两者联合可将推理延迟从3s降至0.8s"
        elif base_rel.relation_type == "服务依赖":
            return f"{node_a.name}的开发者通过{node_b.name}降低学习曲线，联合解决[入门难]痛点"
        elif base_rel.relation_type == "替代竞争":
            return f"两者在{b_type}赛道争夺用户，但{node_a.name}专注垂类可与{node_b.name}形成差异化互补"
        elif base_rel.relation_type == "衍生关联":
            return f"{node_b.name}内容创作者依赖{node_a.name}工具，联合解决[产能低]痛点"
        elif base_rel.relation_type == "同源竞争":
            return f"两者争夺{a_depth}层开发者，但可通过bot集成形成竞合关系解决[集成复杂]痛点"
        elif base_rel.relation_type == "隐含关联":
            return f"虽无直接依赖，但{node_a.name}+{node_b.name}组合可解决[数据孤岛]痛点"
        elif base_rel.relation_type == "供应链":
            return f"{node_a.name}→{node_b.name}链路解决[资源调度]痛点，链路完整性影响整体效率"
        elif base_rel.relation_type == "服务依赖":
            return f"{node_a.name}的{b_type}服务由{node_b.name}提供，联合解决[稳定性差]痛点"
        else:
            return f"{node_a.name}+{node_b.name}在工作流中形成{b_type}协作闭环，解决单一工具覆盖不全痛点"

    def _analyze_conflict(self, node_a: DiscoveredNode, node_b: DiscoveredNode, rel: NodeRelationship) -> str:
        """分析利益冲突程度"""
        # 竞品关系 = 高冲突
        if rel.relation_type == "替代竞争":
            return "高"
        # 同层同父节点 = 中等冲突
        if node_a.parent_id == node_b.parent_id and node_a.parent_id != "":
            return "中"
        # 不同层但同层深度 = 低冲突
        if abs(node_a.depth - node_b.depth) <= 1:
            return "低"
        return "低"

    def _analyze_resource_direction(self, node_a: DiscoveredNode, node_b: DiscoveredNode, path: list) -> str:
        """分析资源依赖方向"""
        if not path or len(path) < 2:
            return "无直接依赖"

        # 判断方向：path[0] -> ... -> path[-1]
        # 如果 node_a 在 path 中间，node_b 在末尾，说明 node_b 依赖 node_a
        try:
            a_idx = path.index(node_a.node_id)
            b_idx = path.index(node_b.node_id)
            if a_idx < b_idx:
                return "下游"  # node_a 是 node_b 的上游
            else:
                return "上游"
        except ValueError:
            pass

        # 基于节点类型判断
        if node_a.node_type == EcosystemNodeType.INFRASTRUCTURE:
            return "上游"
        if node_b.node_type == EcosystemNodeType.INFRASTRUCTURE:
            return "下游"
        if node_a.node_type == EcosystemNodeType.SERVICE and node_b.node_type == EcosystemNodeType.DERIVATIVE:
            return "上游"
        return "合作"

    def _analyze_mcp_potential(self, node_a: DiscoveredNode, node_b: DiscoveredNode) -> tuple:
        """分析MCP集成潜力，返回(级别, 具体集成建议)"""
        # 服务+基础设施 = 高潜力
        if (node_a.node_type == EcosystemNodeType.SERVICE and node_b.node_type == EcosystemNodeType.INFRASTRUCTURE) or \
           (node_b.node_type == EcosystemNodeType.SERVICE and node_a.node_type == EcosystemNodeType.INFRASTRUCTURE):
            suggestion = self._generate_mcp_suggestion(node_a, node_b, "高")
            return ("高", suggestion)
        # 衍生+服务 = 中潜力
        if (node_a.node_type == EcosystemNodeType.DERIVATIVE and node_b.node_type == EcosystemNodeType.SERVICE) or \
           (node_b.node_type == EcosystemNodeType.DERIVATIVE and node_a.node_type == EcosystemNodeType.SERVICE):
            suggestion = self._generate_mcp_suggestion(node_a, node_b, "中")
            return ("中", suggestion)
        # 竞品之间 = 低潜力
        if node_a.node_type == EcosystemNodeType.COMPETITOR or node_b.node_type == EcosystemNodeType.COMPETITOR:
            return ("低", "竞品间MCP集成价值有限")
        # 基础设施之间 = 中潜力
        if node_a.node_type == EcosystemNodeType.INFRASTRUCTURE and node_b.node_type == EcosystemNodeType.INFRASTRUCTURE:
            suggestion = self._generate_mcp_suggestion(node_a, node_b, "中")
            return ("中", suggestion)
        return ("低", "当前类型组合MCP集成价值一般")

    def _generate_mcp_suggestion(self, node_a: DiscoveredNode, node_b: DiscoveredNode, level: str) -> str:
        """生成具体的MCP集成建议（v1.4新增完整可复制调用示例）"""
        combined_name = f"{node_a.name}-{node_b.name}"
        tool_name_a = node_a.name.replace("/", "_").replace(" ", "_").lower()
        tool_name_b = node_b.name.replace("/", "_").replace(" ", "_").lower()

        # v1.4: 每条建议包含完整可复制调用示例（带参数）
        suggestions_by_type = {
            (EcosystemNodeType.SERVICE, EcosystemNodeType.INFRASTRUCTURE): [
                f"封装{node_b.name}为MCP Server供{node_a.name}调用，示例: mcp.call_tool('{tool_name_b}', {{'action': 'deploy', 'region': 'cn', 'tier': 'basic', 'max_tokens': 4096}})",
                f"将{node_a.name}注册为MCP Resource，示例: mcp.add_resource('{tool_name_a}', {{'base_url': 'https://api.{tool_name_a}.com', 'auth': '{{api_key}}'}})",
            ],
            (EcosystemNodeType.INFRASTRUCTURE, EcosystemNodeType.SERVICE): [
                f"创建{node_a.name}的MCP工具包供{node_b.name}调用，示例: mcp.register_tool('{tool_name_a}_client', {{'endpoint': 'https://{tool_name_a}.com/v1', 'model': 'claude-3-opus'}})",
                f"为{node_b.name}对接{node_a.name}生成MCP Client，示例: result = mcp.call_tool('{tool_name_a}_proxy', {{'service': '{node_b.name}', 'operation': 'list_resources'}})",
            ],
            (EcosystemNodeType.DERIVATIVE, EcosystemNodeType.SERVICE): [
                f"输出{node_b.name}的MCP扩展模板供{node_a.name}使用，示例: mcp.load_plugin('{tool_name_b}_bridge', {{'target': '{node_a.name}', 'version': '1.0.0', 'auto_connect': true}})",
            ],
            (EcosystemNodeType.INFRASTRUCTURE, EcosystemNodeType.INFRASTRUCTURE): [
                f"封装{combined_name}组合服务为MCP Pipeline，示例: mcp.create_pipeline('{tool_name_a}_pipeline', {{'steps': [{{'tool': '{tool_name_a}', 'input': '{{\"task\": \"inference\"}}'}}, {{'tool': '{tool_name_b}', 'input': '{{\"op\": \"optimize\"}}'}}], 'timeout': 30}})",
            ],
        }

        for (type_a, type_b), suggestions in suggestions_by_type.items():
            if (node_a.node_type == type_a and node_b.node_type == type_b) or \
               (node_a.node_type == type_b and node_b.node_type == type_a):
                import random
                return random.choice(suggestions)

        return f"探索{combined_name}的MCP集成，示例: mcp.integrate('{tool_name_a}', '{tool_name_b}', {{'bidirectional': true, 'cache': 'redis'}})"

    def _calculate_shovel_score(self, node_a: DiscoveredNode, node_b: DiscoveredNode,
                                 rel: NodeRelationship, conflict: str, mcp: str) -> int:
        """计算卖铲子机会评分（1-10分）"""
        score = 5  # 基础分

        # 关系强度加成
        score += int(rel.strength * 2)

        # 低冲突加成
        if conflict == "低":
            score += 2
        elif conflict == "中":
            score += 1

        # MCP潜力加成
        if mcp == "高":
            score += 3
        elif mcp == "中":
            score += 1

        # 供应链关系加成
        if rel.relation_type == "供应链":
            score += 2

        # Layer3节点加成（隐藏机会）
        if node_a.depth >= 2 or node_b.depth >= 2:
            score += 1

        return min(max(score, 1), 10)

    # ============== 节点相似度计算 ==============

    def calculate_similarity(self, node_a: DiscoveredNode, node_b: DiscoveredNode) -> float:
        """
        计算两个节点的相似度

        基于：名称相似度 + 类型相似度 + 描述词重叠
        """
        # 1. 名称相似度（简单匹配）
        name_similarity = 0.0
        a_words = set(re.findall(r'\w+', node_a.name.lower()))
        b_words = set(re.findall(r'\w+', node_b.name.lower()))
        if a_words and b_words:
            intersection = len(a_words & b_words)
            union = len(a_words | b_words)
            name_similarity = intersection / union if union > 0 else 0.0

        # 2. 类型相似度
        type_similarity = 1.0 if node_a.node_type == node_b.node_type else 0.0

        # 3. 层级相似度（同一层更深）
        depth_similarity = 1.0 if node_a.depth == node_b.depth else 0.0

        # 加权平均
        return (name_similarity * 0.4 + type_similarity * 0.4 + depth_similarity * 0.2)

    # ============== 公共关系查询接口 ==============

    def find_node_relations(self, node_a_id: str, node_b_id: str) -> NodeRelationship:
        """
        图数据库式关系查询

        给定两个节点ID，返回它们之间的关系
        """
        node_a = self.nodes.get(node_a_id)
        node_b = self.nodes.get(node_b_id)

        if not node_a or not node_b:
            return NodeRelationship(node_a_id, node_b_id, "节点不存在", 0.0)

        # 先检查已发现的关系
        for rel in self.relationships:
            if (rel.node_a == node_a_id and rel.node_b == node_b_id) or \
               (rel.node_a == node_b_id and rel.node_b == node_a_id):
                return rel

        # 实时计算
        return self._find_relation_between(node_a, node_b)

    def find_related_nodes(self, node_id: str, min_strength: float = 0.3) -> list[NodeRelationship]:
        """查找与指定节点相关的所有节点"""
        related = []

        # 检查已发现的关系
        for rel in self.relationships:
            if rel.node_a == node_id and rel.strength >= min_strength:
                related.append(rel)
            elif rel.node_b == node_id and rel.strength >= min_strength:
                # 反转关系
                related.append(NodeRelationship(
                    node_a=rel.node_b,
                    node_b=rel.node_a,
                    relation_type=rel.relation_type,
                    strength=rel.strength,
                    path=list(reversed(rel.path))
                ))

        # 如果没有足够关系，进行实时查找
        if len(related) < 3:
            node = self.nodes.get(node_id)
            if node:
                for other_id, other_node in self.nodes.items():
                    if other_id != node_id:
                        rel = self._find_relation_between(node, other_node)
                        if rel.strength >= min_strength:
                            related.append(rel)

        return sorted(related, key=lambda x: x.strength, reverse=True)

    # ============== v1.1 机会生成 ==============

    def _generate_deep_opportunities(self):
        """生成深度机会（Layer3隐藏机会清单）"""
        layer3_nodes = self.result.get_nodes_at_depth(2) if self.result else []
        self.layer3_opportunities = []

        for node in layer3_nodes:
            # 查找与该节点最强的关系
            related = self.find_related_nodes(node.node_id, min_strength=0.3)

            # 生成卖铲子建议
            shovel = self._generate_shovel_for_layer3(node, related)
            if shovel:
                self.layer3_opportunities.append(shovel)

    def _generate_shovel_for_layer3(self, node: DiscoveredNode, related: list) -> dict:
        """为Layer3节点生成卖铲子建议（v1.4新增具体行动路径）"""
        # v1.4: 生成规范化的工具名（用于具体行动路径中的仓库命名）
        node_tool_name = node.name.replace("/", "_").replace(" ", "_").lower()

        # v1.4: 每个模板新增具体行动路径（本周可执行步骤）
        shovel_templates = {
            "基础设施": {
                "形式": "API封装服务 / 中间件",
                "目标用户": "开发者 / 中小厂商",
                "建议": f"针对{node.name}的高可用方案，降低接入门槛，提供托管服务",
                "本周输出物": f"{node.name}集成SDK + API对接文档",
                "预期输出格式": "GitHub仓库(SDK包+demo) + 配套Swagger文档",
                "目标用户聚集地": "GitHub Issue区 / StackOverflow / 掘金评论区",
                "具体行动路径": f"①在GitHub创建openclaw-{node_tool_name}-sdk仓库 → ②编写SDK核心代码(Java/Go/Python各一套) → ③在掘金搜索'OpenClaw SDK'发帖附GitHub链接 → ④在StackOverflow回答相关问题时植入SDK使用示例",
                "渠道": "GitHub开源 / V2EX / 掘金"
            },
            "服务": {
                "形式": "培训课程 / 咨询方案",
                "目标用户": "企业用户 / 团队",
                "建议": f"围绕{node.name}的落地实践，提供从培训到交付的一站式服务",
                "本周输出物": f"{node.name}落地SOP + 案例PPT",
                "预期输出格式": "Notion文档(SOP流程) + PDF(案例分析) + 答疑视频链接",
                "目标用户聚集地": "企业微信社群 / 飞书多维表格用户群 / 行业大会现场",
                "具体行动路径": f"①在Notion搭建{node.name}落地SOP模板 → ②整理3个真实企业案例制作PPT → ③在知乎专栏发布图文教程(附Notion链接) → ④加入2个相关企业微信群潜伏发掘需求",
                "渠道": "知乎专栏 / B站视频 / 微信群"
            },
            "衍生": {
                "形式": "工具插件 / 社区平台",
                "目标用户": "普通用户 / 创作者",
                "建议": f"基于{node.name}的内容创作工具，降低使用门槛",
                "本周输出物": f"{node.name}使用指南 + 模板下载页",
                "预期输出格式": "Canva模板(可编辑) + 即梦/可灵AI提示词合集PDF",
                "目标用户聚集地": "小红书笔记区 / 即梦AI用户群 / 抖音评论区",
                "具体行动路径": f"①在Canva制作{node.name}使用模板(封面+内页+结尾CTA) → ②整理即梦/可灵提示词20条制作PDF合集 → ③小红书发布3篇种草笔记(模板截图+使用场景) → ④在即梦用户群分享模板下载链接",
                "渠道": "小红书 / 即刻 / 少数派"
            }
        }

        # 根据节点类型获取模板
        node_type_key = str(node.node_type.value).split("层")[0] if "层" in str(node.node_type.value) else str(node.node_type.value)

        template = None
        for key, t in shovel_templates.items():
            if key in str(node.node_type.value):
                template = t
                break

        if not template:
            template = {
                "形式": "综合服务",
                "目标用户": "广泛用户",
                "建议": f"围绕{node.name}构建生态，提供差异化价值",
                "本周输出物": f"{node.name}介绍页 + 答疑群",
                "预期输出格式": "公众号图文 + 微信群沉淀资料包",
                "目标用户聚集地": "朋友圈转发区 / 公众号读者群",
                "具体行动路径": f"①制作{node.name}介绍图文 → ②在朋友圈转发并附微信群二维码 → ③邀请3个行业KOL帮忙扩散",
                "渠道": "朋友圈 / 公众号"
            }

        # 计算机会评分
        avg_strength = sum(r.strength for r in related[:5]) / min(len(related), 5) if related else 0.5

        return {
            "node_id": node.node_id,
            "node_name": node.name,
            "node_type": node.node_type.value,
            "shovel_form": template["形式"],
            "target_users": template["目标用户"],
            "execution_tip": template["建议"],
            "this_week_output": template["本周输出物"],
            "expected_output_format": template["预期输出格式"],
            "target_user_location": template["目标用户聚集地"],
            "specific_action_path": template["具体行动路径"],
            "this_week_channels": template["渠道"],
            "opportunity_score": min(int(avg_strength * 10) + 3, 10),
            "related_count": len(related)
        }

    def _generate_network_graph(self, result: DiscoveryResult) -> str:
        """生成节点关联网络图（文字版）"""
        lines = ["```"]
        lines.append(f"# 网状关系图 @ {result.core_node}")
        lines.append("")

        # 按层组织节点
        layers = {}
        for node in result.all_nodes.values():
            if node.depth not in layers:
                layers[node.depth] = []
            layers[node.depth].append(node)

        # 生成层内和层间连接
        for depth in sorted(layers.keys()):
            nodes = layers[depth]
            depth_label = "核心" if depth == 0 else f"L{depth}"
            lines.append(f"## {depth_label} ({len(nodes)}节点)")

            # 节点名列表
            node_names = [n.name for n in nodes]
            lines.append(f"[{' | '.join(node_names)}]")
            lines.append("")

            # 层间关系
            if depth > 0:
                lines.append("↑ 依赖上游:")
                for node in nodes[:3]:  # 只显示前3个
                    parent = self.nodes.get(node.parent_id)
                    if parent:
                        lines.append(f"  {node.name} <- {parent.name}")
                lines.append("")

        # 高强度关系对
        lines.append("## 强关系对 (强度>=0.8)")
        strong = [r for r in result.relationships if r.strength >= 0.8][:10]
        for rel in strong:
            name_a = self.nodes.get(rel.node_a, {}).name or rel.node_a
            name_b = self.nodes.get(rel.node_b, {}).name or rel.node_b
            lines.append(f"{name_a} -- {name_b} [{rel.strength:.2f}]")

        lines.append("```")
        return "\n".join(lines)

    # ============== v1.2 自适应闭环（动态强度调整） ==============

    def _record_accuracy(self):
        """记录本轮节点关联准确率"""
        if not self.result:
            return

        high_strength_count = len([r for r in self.result.relationships if r.strength >= 0.7])
        total_count = len(self.result.relationships)

        accuracy = high_strength_count / total_count if total_count > 0 else 0.5

        self.last_accuracy = accuracy
        self.accuracy_history.append(accuracy)

        return accuracy

    def _record_coverage(self):
        """记录泛领域覆盖率"""
        if not self.result:
            return

        type_pairs = set()
        for rel in self.result.relationships:
            node_a = self.nodes.get(rel.node_a)
            node_b = self.nodes.get(rel.node_b)
            if node_a and node_b:
                pair = tuple(sorted([node_a.node_type.value, node_b.node_type.value]))
                type_pairs.add(pair)

        coverage = min(len(type_pairs) / 15, 1.0)

        self.last_coverage = coverage
        self.coverage_history.append(coverage)

        return coverage

    def _adjust_keyword_weights(self):
        """基于本轮结果调整权重和强度计算参数"""
        if not hasattr(self, 'last_accuracy') or not hasattr(self, 'last_coverage'):
            return

        accuracy = getattr(self, 'last_accuracy', 0.5)
        coverage = getattr(self, 'last_coverage', 0.3)

        # v1.2: 计算动态强度调整因子
        # 准确率高 -> 信任度高的关系应该加权
        # 准确率低 -> 需要保守估计，降低所有强度
        if len(self.accuracy_history) >= 3:
            recent_avg = sum(self.accuracy_history[-3:]) / 3
            if recent_avg > 0.7:
                self.strength_multiplier = 1.1  # 加权
            elif recent_avg < 0.4:
                self.strength_multiplier = 0.8  # 保守
            else:
                self.strength_multiplier = 1.0  # 正常
        else:
            self.strength_multiplier = 1.0

        adjustment = {
            "accuracy": accuracy,
            "coverage": coverage,
            "strength_multiplier": self.strength_multiplier,
            "adjustments": []
        }

        if accuracy > 0.7:
            adjustment["adjustments"].append("增加强关系节点的关联发现权重")
        if coverage < 0.4:
            adjustment["adjustments"].append("扩展跨层类型发现，增加新类型组合")
        if self.strength_multiplier != 1.0:
            adjustment["adjustments"].append(f"关系强度调整因子: {self.strength_multiplier:.2f}")

        self.keyword_adjustments = adjustment

    def get_dynamic_strength(self, base_strength: float) -> float:
        """根据自适应状态获取动态调整后的强度"""
        multiplier = getattr(self, 'strength_multiplier', 1.0)
        adjusted = base_strength * multiplier
        return min(max(adjusted, 0.0), 1.0)  # 限制在0-1

    def record_feedback(self, relation_correct: bool, opportunity_valid: bool):
        """
        记录外部反馈（供自适应学习用）

        Args:
            relation_correct: 节点关系判断是否正确
            opportunity_valid: 机会识别是否有效
        """
        if not hasattr(self, 'feedback_history'):
            self.feedback_history = []

        self.feedback_history.append({
            "relation_correct": relation_correct,
            "opportunity_valid": opportunity_valid,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        # 动态调整
        correct_rate = sum(1 for f in self.feedback_history[-10:] if f["relation_correct"]) / min(len(self.feedback_history), 10)
        if correct_rate > 0.8:
            self.config.similarity_threshold = min(self.config.similarity_threshold + 0.05, 0.9)
        elif correct_rate < 0.5:
            self.config.similarity_threshold = max(self.config.similarity_threshold - 0.05, 0.3)

    def get_adaptive_stats(self) -> dict:
        """获取自适应统计"""
        return {
            "last_accuracy": getattr(self, 'last_accuracy', None),
            "last_coverage": getattr(self, 'last_coverage', None),
            "accuracy_history": getattr(self, 'accuracy_history', []),
            "coverage_history": getattr(self, 'coverage_history', []),
            "feedback_count": len(getattr(self, 'feedback_history', [])),
            "current_threshold": self.config.similarity_threshold,
            "strength_multiplier": getattr(self, 'strength_multiplier', 1.0),
            "keyword_adjustments": getattr(self, 'keyword_adjustments', None)
        }

    # ============== 报告生成 ==============

    def generate_report(self, result: DiscoveryResult) -> str:
        """生成深度发现报告"""
        lines = [f"# 🔬 深度生态发现报告\n"]
        lines.append(f"**核心节点**: {result.core_node}\n")
        lines.append(f"**发现深度**: {result.depth_reached} 层\n")
        lines.append(f"**执行时间**: {result.execution_time}\n")

        # 层统计
        lines.append(f"\n## 📊 层级概览\n")
        for depth in sorted(result.layer_summary.keys()):
            count = result.layer_summary[depth]
            depth_label = "核心层" if depth == 0 else f"第{depth}层"
            lines.append(f"- **{depth_label}**: {count} 个节点\n")

        # 每层节点详情
        lines.append(f"\n## 🌲 节点详情\n")
        for depth in range(result.depth_reached + 1):
            nodes_at_depth = result.get_nodes_at_depth(depth)
            if nodes_at_depth:
                depth_label = "核心节点" if depth == 0 else f"第{depth}层节点"
                lines.append(f"\n### {depth_label}（{len(nodes_at_depth)}个）\n")
                for node in nodes_at_depth:
                    type_icon = {"CORE": "🎯", "INFRASTRUCTURE": "🏗️", "SERVICE": "🛠️",
                                "DERIVATIVE": "📎", "COMPETITOR": "⚔️", "USER": "👥"}.get(node.node_type.value, "📌")
                    lines.append(f"- {type_icon} **{node.name}** ({node.node_type.value})\n")

        # 关系统计
        lines.append(f"\n## 🔗 关系网络（含增强属性）\n")
        lines.append(f"发现 **{len(result.relationships)}** 条关系\n")

        strong_relations = [r for r in result.relationships if r.strength >= 0.5]
        if strong_relations:
            lines.append(f"\n### 强关系详情（强度≥0.5）\n")
            for rel in sorted(strong_relations, key=lambda x: x.strength, reverse=True)[:10]:
                node_a_name = self.nodes.get(rel.node_a, {}).name or rel.node_a
                node_b_name = self.nodes.get(rel.node_b, {}).name or rel.node_b
                lines.append(f"- **{node_a_name}** ↔ **{node_b_name}**\n")
                lines.append(f"  - 关系: {rel.relation_type}, 强度: {rel.strength:.2f}\n")
                lines.append(f"  - 利益冲突: {rel.conflict_level} | 资源流向: {rel.resource_direction} | MCP潜力: {rel.mcp_potential}\n")
                lines.append(f"  - ⭐卖铲子评分: {rel.shovel_score}/10 {rel.get_shovel_label()}\n")
                lines.append(f"  - 📝特异性描述: {rel.specific_description}\n")
                if rel.mcp_suggestion:
                    lines.append(f"  - 🔧MCP建议: {rel.mcp_suggestion}\n")

        # v1.1 新增：节点关联网络图
        lines.append(f"\n## 🕸️ 节点关联网络图\n")
        lines.append(self._generate_network_graph(result))

        # v1.4 新增：Layer3隐藏机会清单（Top5，含具体行动路径）
        lines.append(f"\n## 🎯 Layer3隐藏机会清单 (Top5)\n")
        if self.layer3_opportunities:
            sorted_opps = sorted(self.layer3_opportunities, key=lambda x: x["opportunity_score"], reverse=True)[:5]
            lines.append(f"从{len(self.layer3_opportunities)}个机会中精选Top5\n")
            for i, opp in enumerate(sorted_opps, 1):
                lines.append(f"\n### {i}. **{opp['node_name']}** ({opp['node_type']}) ⭐{opp['opportunity_score']}/10\n")
                lines.append(f"| 维度 | 内容 |\n")
                lines.append(f"|------|------|\n")
                lines.append(f"| 卖铲子形式 | {opp['shovel_form']} |\n")
                lines.append(f"| 目标用户 | {opp['target_users']} |\n")
                lines.append(f"| 执行建议 | {opp['execution_tip']} |\n")
                lines.append(f"| **本周输出物** | {opp.get('this_week_output', '-')} |\n")
                lines.append(f"| **预期输出格式** | {opp.get('expected_output_format', '-')} |\n")
                lines.append(f"| **目标用户聚集地** | {opp.get('target_user_location', '-')} |\n")
                lines.append(f"| **具体行动路径** | {opp.get('specific_action_path', '-')} |\n")
                lines.append(f"| **推广渠道** | {opp.get('this_week_channels', '-')} |\n")
        else:
            lines.append("暂无Layer3隐藏机会\n")

        # v1.1 新增：自适应统计
        adaptive = self.get_adaptive_stats()
        if adaptive["last_accuracy"] is not None:
            lines.append(f"\n## 📈 自适应闭环统计\n")
            lines.append(f"- 节点关联准确率: {adaptive['last_accuracy']:.1%}\n")
            lines.append(f"- 泛领域覆盖率: {adaptive['last_coverage']:.1%}\n")
            lines.append(f"- 当前相似度阈值: {adaptive['current_threshold']:.2f}\n")
            if adaptive.get('keyword_adjustments'):
                for adj in adaptive['keyword_adjustments'].get('adjustments', []):
                    lines.append(f"- 调整: {adj}\n")

        return "".join(lines)


# ============== 使用示例 ==============

if __name__ == "__main__":
    print("🔬 深度生态挖掘引擎 v1.4 - 网状深度发现\n")

    miner = DeepEcosystemMiner()

    # 深度发现
    result = miner.deep_discover("OpenClaw", depth=3)

    print(f"核心节点: {result.core_node}")
    print(f"发现深度: {result.depth_reached} 层")
    print(f"总节点数: {result.get_total_nodes()}")
    print(f"总关系数: {len(result.relationships)}")
    print(f"\n层级分布:")
    for depth, count in sorted(result.layer_summary.items()):
        print(f"  第{depth}层: {count}个节点")

    # v1.2 增强关系查询
    print("\n=== v1.2 增强节点关系查询 ===")
    if result.get_total_nodes() >= 3:
        nodes_list = list(result.all_nodes.values())
        layer1 = next((n for n in nodes_list if n.depth == 1), None)
        layer2 = next((n for n in nodes_list if n.depth == 2), None)

        if layer2 and layer3:
            rel = miner.find_node_relations(layer2.node_id, layer3.node_id)
            print(f"\n{layer2.name} ↔ {layer3.name}:")
            print(f"  关系类型: {rel.relation_type}")
            print(f"  关系强度: {rel.strength:.2f}")
            print(f"  利益冲突: {rel.conflict_level}")
            print(f"  资源流向: {rel.resource_direction}")
            print(f"  MCP集成潜力: {rel.mcp_potential}")
            print(f"  ⭐卖铲子评分: {rel.shovel_score}/10 {rel.get_shovel_label()}")

    # Layer3隐藏机会
    print("\n=== Layer3隐藏机会 ===")
    if miner.layer3_opportunities:
        for opp in sorted(miner.layer3_opportunities, key=lambda x: x["opportunity_score"], reverse=True)[:3]:
            print(f"\n{opp['node_name']}:")
            print(f"  形式: {opp['shovel_form']}")
            print(f"  目标: {opp['target_users']}")
            print(f"  建议: {opp['execution_tip']}")
            print(f"  评分: ⭐{opp['opportunity_score']}/10")

    # 自适应统计
    adaptive = miner.get_adaptive_stats()
    print(f"\n=== 自适应闭环统计 ===")
    print(f"  准确率: {adaptive['last_accuracy']:.1%}")
    print(f"  覆盖率: {adaptive['last_coverage']:.1%}")
    print(f"  阈值: {adaptive['current_threshold']:.2f}")

    # 生成完整报告
    report = miner.generate_report(result)
    print("\n" + "=" * 60)
    print(report)
