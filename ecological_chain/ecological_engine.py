"""
生态连锁挖掘引擎 v1.0
Ecological Chain Mining Engine — L8.5 生态挖掘核心模块

核心思维：
当一个项目/产品火了，不只是看它本身，而是挖掘：
1. 它的生态位（谁在它的生态里）
2. 它的供应链（它依赖什么）
3. 它的客户链（谁在用它的客户）
4. 连锁反应（它的火爆会引发什么）

供应关系挖掘逻辑：
核心项目 → 依赖层 → 依赖层的依赖层 → ... → 机会

例如：OpenClaw火了
→ OpenClaw需要AI模型API → AI API服务商机会
→ OpenClaw用户需要教程 → 教程/培训机会
→ OpenClaw火了让竞品出现 → 竞品的配套机会
→ OpenClaw火了让行业火了 → 行业周边机会
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any, TYPE_CHECKING
from datetime import datetime
import json

# 统一枚举从unified_enums导入
from unified_enums import EcosystemNodeType as UnifiedEcosystemNodeType, OpportunityType as UnifiedOpportunityType

if TYPE_CHECKING:
    from self_evolution import SelfEvolutionManager

# 保持向后兼容的类型别名
EcosystemNodeType = UnifiedEcosystemNodeType
OpportunityType = UnifiedOpportunityType


@dataclass
class EcosystemNode:
    """生态节点"""
    node_id: str
    name: str
    node_type: EcosystemNodeType
    parent_id: str = ""            # 父节点ID（它在谁的生态里）
    description: str = ""
    scale: str = ""               # 规模：巨头/中厂/小厂/个人
    maturity: str = ""             # 成熟度：早期/成长期/成熟/饱和
    verified: bool = False         # 是否已验证存在

    # 关系
    dependencies: list[str] = field(default_factory=list)  # 它依赖什么
    dependents: list[str] = field(default_factory=list)   # 什么依赖它
    supply_to: list[str] = field(default_factory=list)     # 它供应给谁
    demand_from: list[str] = field(default_factory=list)    # 它从谁那采购


@dataclass
class SupplyChainLink:
    """供应链关系"""
    link_id: str
    from_node: str                 # 供应方
    to_node: str                   # 需求方
    link_type: str                 # 关系类型：技术依赖/服务/资金/数据/流量
    value_flow: str                 # 价值流向
    pain_point: str = ""           # 痛点（机会所在）
    opportunity: str = ""          # 潜在机会描述
    confidence: float = 0.5        # 置信度


@dataclass
class EcologicalOpportunity:
    """生态连锁机会"""
    opportunity_id: str
    trigger_node: str              # 触发这个机会的核心节点
    opportunity_type: OpportunityType
    description: str
    position_in_chain: str         # 在链上的位置
    confidence: float
    estimated_scale: str           # 预估规模
    time_window: str               # 时间窗口
    required_capability: list[str] = field(default_factory=list)  # 所需能力
    entry_barrier: str = "中"      # 进入门槛
    related_opportunities: list[str] = field(default_factory=list)  # 相关机会


# ============== 生态挖掘引擎 ==============

class EcosystemMiner:
    """
    生态连锁挖掘引擎

    从一个核心节点出发，挖掘整个生态的机会网络
    """

    def __init__(self, evolution_manager: 'SelfEvolutionManager' = None):
        self.ecosystem_nodes: dict[str, EcosystemNode] = {}
        self.supply_chain_links: list[SupplyChainLink] = []
        self.opportunities: list[EcologicalOpportunity] = []
        self.node_counter = 0
        self.link_counter = 0
        self.opp_counter = 0
        self.evolution_manager = evolution_manager

        # 初始化已知模式
        self.chain_patterns = self._init_chain_patterns()

    def _init_chain_patterns(self) -> dict:
        """初始化连锁模式库"""
        return {
            # 核心项目 → 基础设施机会
            "infrastructure_pattern": {
                "trigger": "核心项目依赖某技术/服务",
                "chain": "核心 → 依赖技术/服务 → 供应商业机会",
                "example": "OpenClaw用LLM API → LLM API服务商机会"
            },
            # 竞品出现 → 配套机会
            "competitor_pattern": {
                "trigger": "某类项目出现竞品",
                "chain": "竞品 → 竞品配套（教程/插件/主题）→ 机会",
                "example": "Notion火了 → Notion模板/插件机会"
            },
            # 用户涌入 → 用户服务机会
            "user_influx_pattern": {
                "trigger": "项目用户量快速增长",
                "chain": "用户增长 → 用户需求（教程/咨询/定制）→ 机会",
                "example": "ChatGPT用户爆发 → AI提示词工程师需求"
            },
            # 行业火爆 → 周边机会
            "industry_pattern": {
                "trigger": "整个行业被带火",
                "chain": "行业火爆 → 培训/猎头/媒体 → 机会",
                "example": "区块链火了 → 区块链培训/媒体机会"
            },
            # 平台迁移 → 迁移服务商机会
            "migration_pattern": {
                "trigger": "用户从A平台迁移到B平台",
                "chain": "平台迁移 → 迁移工具/服务 → 机会",
                "example": "从WordPress迁移到新平台 → 迁移服务商"
            },
            # 标准化 → 标准服务商机会
            "standardization_pattern": {
                "trigger": "某类需求变得标准化",
                "chain": "需求标准化 → 标准件供应商 → 机会",
                "example": "API调用标准化 → API网关/监控服务商"
            }
        }

    def add_core_node(self, name: str, description: str = "",
                     maturity: str = "成长期") -> EcosystemNode:
        """添加核心节点"""
        self.node_counter += 1
        node = EcosystemNode(
            node_id=f"NODE_{self.node_counter:03d}",
            name=name,
            node_type=EcosystemNodeType.CORE,
            description=description,
            maturity=maturity
        )
        self.ecosystem_nodes[node.node_id] = node
        return node

    def add_ecosphere_node(self, name: str, node_type: EcosystemNodeType,
                          parent_id: str = "", description: str = "") -> EcosystemNode:
        """添加生态节点"""
        self.node_counter += 1
        node = EcosystemNode(
            node_id=f"NODE_{self.node_counter:03d}",
            name=name,
            node_type=node_type,
            parent_id=parent_id,
            description=description
        )
        self.ecosystem_nodes[node.node_id] = node

        # 建立父子关系
        if parent_id and parent_id in self.ecosystem_nodes:
            parent = self.ecosystem_nodes[parent_id]
            if node_type in [EcosystemNodeType.INFRASTRUCTURE, EcosystemNodeType.SERVICE]:
                parent.dependencies.append(node.node_id)
                node.supply_to.append(parent_id)
            elif node_type in [EcosystemNodeType.USER, EcosystemNodeType.DOWNSTREAM]:
                parent.dependents.append(node.node_id)
                node.demand_from.append(parent_id)

        return node

    def discover_ecosphere(self, core_node_id: str) -> list[EcosystemNode]:
        """
        发现核心节点的整个生态系统

        策略：
        1. 技术依赖链：它用什么技术做的？
        2. 服务链：什么服务围绕它？
        3. 用户链：谁在用它？
        4. 竞品链：谁在复制它？
        5. 衍生链：什么基于它开发的？
        """
        if core_node_id not in self.ecosystem_nodes:
            return []

        discovered = []
        core = self.ecosystem_nodes[core_node_id]

        # 1. 发现基础设施层（它依赖什么）
        infra_nodes = self._discover_infrastructure(core)
        discovered.extend(infra_nodes)

        # 2. 发现服务层（围绕它的服务商）
        service_nodes = self._discover_services(core)
        discovered.extend(service_nodes)

        # 3. 发现衍生层（基于它的衍生品）
        derivative_nodes = self._discover_derivatives(core)
        discovered.extend(derivative_nodes)

        # 4. 发现竞品层（它的竞品）
        competitor_nodes = self._discover_competitors(core)
        discovered.extend(competitor_nodes)

        # 5. 发现用户层（谁在用它）
        user_nodes = self._discover_users(core)
        discovered.extend(user_nodes)

        return discovered

    def _discover_infrastructure(self, core: EcosystemNode) -> list[EcosystemNode]:
        """发现基础设施层"""
        nodes = []

        # 常见基础设施模式
        infra_patterns = [
            (EcosystemNodeType.INFRASTRUCTURE, "LLM API", "AI大模型服务"),
            (EcosystemNodeType.INFRASTRUCTURE, "云服务器", "基础设施服务商"),
            (EcosystemNodeType.INFRASTRUCTURE, "数据库", "数据库服务商"),
            (EcosystemNodeType.INFRASTRUCTURE, "支付通道", "支付服务商"),
            (EcosystemNodeType.INFRASTRUCTURE, "短信服务", "短信服务商"),
        ]

        for ntype, name, desc in infra_patterns:
            node = self.add_ecosphere_node(
                name=name,
                node_type=ntype,
                parent_id=core.node_id,
                description=f"{core.name}依赖的{desc}"
            )
            nodes.append(node)

            # 建立供应链关系
            self._add_supply_link(
                from_node=node.node_id,
                to_node=core.node_id,
                link_type="技术依赖",
                value_flow=f"{name} → {core.name}",
                pain_point=f"{name}可能成为{core.name}的瓶颈",
                opportunity=f"提供更稳定/更便宜的{name}"
            )

        return nodes

    def _discover_services(self, core: EcosystemNode) -> list[EcosystemNode]:
        """发现服务层"""
        nodes = []

        # 常见服务模式
        service_patterns = [
            (EcosystemNodeType.SERVICE, f"{core.name}教程", f"{core.name}学习资料"),
            (EcosystemNodeType.SERVICE, f"{core.name}咨询", f"{core.name}实施咨询"),
            (EcosystemNodeType.SERVICE, f"{core.name}定制开发", f"{core.name}二次开发"),
            (EcosystemNodeType.SERVICE, f"{core.name}插件开发", f"{core.name}插件/扩展"),
            (EcosystemNodeType.SERVICE, f"{core.name}主题/模板", f"{core.name} UI资源"),
        ]

        for ntype, name, desc in service_patterns:
            node = self.add_ecosphere_node(
                name=name,
                node_type=ntype,
                parent_id=core.node_id,
                description=desc
            )
            nodes.append(node)

        return nodes

    def _discover_derivatives(self, core: EcosystemNode) -> list[EcosystemNode]:
        """发现衍生层"""
        nodes = []

        # 衍生品模式
        derivative_patterns = [
            (EcosystemNodeType.DERIVATIVE, f"{core.name}社区", f"{core.name}用户社区"),
            (EcosystemNodeType.DERIVATIVE, f"{core.name}媒体", f"{core.name}内容账号"),
            (EcosystemNodeType.DERIVATIVE, f"{core.name}导航站", f"{core.name}资源聚合"),
            (EcosystemNodeType.DERIVATIVE, f"{core.name}评测", f"{core.name}评测对比"),
        ]

        for ntype, name, desc in derivative_patterns:
            node = self.add_ecosphere_node(
                name=name,
                node_type=ntype,
                parent_id=core.node_id,
                description=desc
            )
            nodes.append(node)

        return nodes

    def _discover_competitors(self, core: EcosystemNode) -> list[EcosystemNode]:
        """发现竞品层"""
        # 竞品层不是core的子节点，而是独立节点
        competitor_node = self.add_ecosphere_node(
            name=f"竞品：{core.name}的替代品",
            node_type=EcosystemNodeType.COMPETITOR,
            parent_id=core.node_id,
            description=f"{core.name}的竞争对手"
        )

        # 竞品也会带来机会
        self._add_supply_link(
            from_node=core.node_id,
            to_node=competitor_node.node_id,
            link_type="替代竞争",
            value_flow="用户争夺",
            pain_point="用户可能流失到竞品",
            opportunity="竞品的配套市场（教程、插件往往跨平台）"
        )

        return [competitor_node]

    def _discover_users(self, core: EcosystemNode) -> list[EcosystemNode]:
        """发现用户层"""
        nodes = []

        user_patterns = [
            (EcosystemNodeType.USER, "普通用户", "使用核心功能的用户"),
            (EcosystemNodeType.USER, "企业用户", "有定制需求的企业"),
            (EcosystemNodeType.DOWNSTREAM, "用户的后续需求", "用户用了之后还需要什么"),
        ]

        for ntype, name, desc in user_patterns:
            node = self.add_ecosphere_node(
                name=name,
                node_type=ntype,
                parent_id=core.node_id,
                description=desc
            )
            nodes.append(node)

        return nodes

    def _add_supply_link(self, from_node: str, to_node: str,
                         link_type: str, value_flow: str,
                         pain_point: str = "", opportunity: str = ""):
        """添加供应链关系"""
        self.link_counter += 1
        link = SupplyChainLink(
            link_id=f"LINK_{self.link_counter:03d}",
            from_node=from_node,
            to_node=to_node,
            link_type=link_type,
            value_flow=value_flow,
            pain_point=pain_point,
            opportunity=opportunity,
            confidence=0.7
        )
        self.supply_chain_links.append(link)

    def mine_supply_chain_opportunities(self, core_node_id: str) -> list[EcologicalOpportunity]:
        """
        挖掘供应链上的机会

        核心问题：
        1. core依赖什么？→ 基础设施机会
        2. core的用户需要什么？→ 下游服务机会
        3. core火了会引发什么？→ 连锁反应机会
        4. 竞品出现会带来什么？→ 配套机会
        """
        if core_node_id not in self.ecosystem_nodes:
            return []

        opportunities = []
        core = self.ecosystem_nodes[core_node_id]

        # 1. 基础设施机会：core依赖的基础设施层节点
        for dep_id in core.dependencies:
            dep = self.ecosystem_nodes.get(dep_id)
            if dep and dep.node_type == EcosystemNodeType.INFRASTRUCTURE:
                opp = self._generate_infrastructure_opportunity(core, dep)
                opportunities.append(opp)

        # 2. 服务机会：围绕core的服务层节点
        service_nodes = [n for n in self.ecosystem_nodes.values()
                        if n.parent_id == core.node_id and n.node_type == EcosystemNodeType.SERVICE]
        for svc in service_nodes:
            opp = self._generate_service_opportunity(core, svc)
            opportunities.append(opp)

        # 3. 连锁反应机会：core火爆带来的机会
        opp = self._generate_cascade_opportunity(core)
        opportunities.append(opp)

        # 4. 下游机会：用户买了之后还需要什么
        downstream_opp = self._generate_downstream_opportunity(core)
        opportunities.append(downstream_opp)

        # 5. 逆向机会：竞品火了也给机会
        competitor_opp = self._generate_inverse_opportunity(core)
        opportunities.append(competitor_opp)

        self.opportunities.extend(opportunities)
        return opportunities

    def _generate_infrastructure_opportunity(self, core: EcosystemNode,
                                           infra: EcosystemNode) -> EcologicalOpportunity:
        """生成基础设施机会（使用动态模式置信度）"""
        self.opp_counter += 1

        # 获取动态置信度
        base_confidence = 0.75
        if self.evolution_manager:
            pattern_conf = self.evolution_manager.get_pattern_confidence("infrastructure")
            # 取平均值作为置信度
            confidence = (base_confidence + pattern_conf) / 2
        else:
            confidence = base_confidence

        return EcologicalOpportunity(
            opportunity_id=f"ECO_{self.opp_counter:03d}",
            trigger_node=core.node_id,
            opportunity_type=OpportunityType.INFRASTRUCTURE,
            description=f"{core.name}依赖{infra.name}，存在供应链瓶颈风险",
            position_in_chain=f"{infra.name} → {core.name}",
            confidence=confidence,
            estimated_scale="中等",
            time_window="持续机会",
            required_capability=[f"{infra.name}相关技术"],
            entry_barrier="高" if infra.maturity == "成熟" else "中",
            related_opportunities=[]
        )

    def _generate_service_opportunity(self, core: EcosystemNode,
                                      service: EcosystemNode) -> EcologicalOpportunity:
        """生成服务机会（使用动态模式置信度）"""
        self.opp_counter += 1

        # 获取动态置信度
        base_confidence = 0.80
        if self.evolution_manager:
            pattern_conf = self.evolution_manager.get_pattern_confidence("service")
            confidence = (base_confidence + pattern_conf) / 2
        else:
            confidence = base_confidence

        return EcologicalOpportunity(
            opportunity_id=f"ECO_{self.opp_counter:03d}",
            trigger_node=core.node_id,
            opportunity_type=OpportunityType.SERVICE,
            description=f"围绕{core.name}的{service.name}服务",
            position_in_chain=f"{core.name}用户 → {service.name}",
            confidence=confidence,
            estimated_scale="小而美",
            time_window=f"在{core.name}成长期内持续",
            required_capability=["内容创作", "技术支持"],
            entry_barrier="低",
            related_opportunities=[]
        )

    def _generate_cascade_opportunity(self, core: EcosystemNode) -> EcologicalOpportunity:
        """生成连锁反应机会（使用动态模式置信度）"""
        self.opp_counter += 1

        # 获取动态置信度
        base_confidence = 0.70
        if self.evolution_manager:
            pattern_conf = self.evolution_manager.get_pattern_confidence("cascade")
            confidence = (base_confidence + pattern_conf) / 2
        else:
            confidence = base_confidence

        return EcologicalOpportunity(
            opportunity_id=f"ECO_{self.opp_counter:03d}",
            trigger_node=core.node_id,
            opportunity_type=OpportunityType.CASCADE,
            description=f"{core.name}火爆带动整个行业，周边机会爆发",
            position_in_chain=f"{core.name} → 行业生态",
            confidence=confidence,
            estimated_scale="大",
            time_window="窗口期3-6个月",
            required_capability=["行业知识", "资源整合"],
            entry_barrier="中",
            related_opportunities=[]
        )

    def _generate_downstream_opportunity(self, core: EcosystemNode) -> EcologicalOpportunity:
        """生成下游机会（使用动态模式置信度）"""
        self.opp_counter += 1

        # 获取动态置信度
        base_confidence = 0.85
        if self.evolution_manager:
            pattern_conf = self.evolution_manager.get_pattern_confidence("downstream")
            confidence = (base_confidence + pattern_conf) / 2
        else:
            confidence = base_confidence

        return EcologicalOpportunity(
            opportunity_id=f"ECO_{self.opp_counter:03d}",
            trigger_node=core.node_id,
            opportunity_type=OpportunityType.DOWNSTREAM,
            description=f"用户使用{core.name}后，还需要后续服务（培训、咨询、定制）",
            position_in_chain=f"{core.name}用户 → 后续需求",
            confidence=confidence,
            estimated_scale="中等",
            time_window="持续需求",
            required_capability=["服务能力", "客户关系"],
            entry_barrier="低",
            related_opportunities=[]
        )

    def _generate_inverse_opportunity(self, core: EcosystemNode) -> EcologicalOpportunity:
        """生成逆向机会（竞品带来的机会，使用动态模式置信度）"""
        self.opp_counter += 1

        # 获取动态置信度
        base_confidence = 0.65
        if self.evolution_manager:
            pattern_conf = self.evolution_manager.get_pattern_confidence("inverse")
            confidence = (base_confidence + pattern_conf) / 2
        else:
            confidence = base_confidence

        return EcologicalOpportunity(
            opportunity_id=f"ECO_{self.opp_counter:03d}",
            trigger_node=core.node_id,
            opportunity_type=OpportunityType.INVERSE,
            description=f"{core.name}的竞品出现，相关配套（教程/插件）可跨平台复用",
            position_in_chain=f"竞品生态 → 跨平台机会",
            confidence=confidence,
            estimated_scale="视竞品而定",
            time_window="竞品成长期",
            required_capability=["跨平台适配能力"],
            entry_barrier="中",
            related_opportunities=[]
        )

    def analyze_opportunity_chain(self, opportunity_id: str) -> dict:
        """
        分析机会的完整链条

        例如：
        OpenClaw插件开发机会
        → OpenClaw需要插件 → 插件开发者需要工具 → 工具机会
        → OpenClaw插件多了 → 插件市场机会
        → 插件市场火了 → 插件导航/评测机会
        """
        if opportunity_id not in [o.opportunity_id for o in self.opportunities]:
            return {}

        opp = next((o for o in self.opportunities if o.opportunity_id == opportunity_id), None)
        if not opp:
            return {}

        trigger = self.ecosystem_nodes.get(opp.trigger_node)

        chain_analysis = {
            "opportunity": opp,
            "first_order": self._get_first_order_opportunities(opp),
            "second_order": self._get_second_order_opportunities(opp),
            "risk_chain": self._get_risk_chain(opp)
        }

        return chain_analysis

    def _get_first_order_opportunities(self, opp: EcologicalOpportunity) -> list[str]:
        """获取一级连锁机会"""
        # 直接围绕这个机会的相关机会
        related = []
        for o in self.opportunities:
            if o.opportunity_id != opp.opportunity_id:
                # 同一触发节点的机会
                if o.trigger_node == opp.trigger_node:
                    related.append(o.description)
        return related

    def _get_second_order_opportunities(self, opp: EcologicalOpportunity) -> list[str]:
        """获取二级连锁机会"""
        # 假设opp成功后，会引发什么
        second_order = []

        if opp.opportunity_type == OpportunityType.SERVICE:
            second_order.append(f"{opp.description}做大了 → 可能出现平台机会")
            second_order.append(f"{opp.description}做大了 → 可能出现竞争")

        if opp.opportunity_type == OpportunityType.CASCADE:
            second_order.append(f"行业火了 → 监管可能介入 → 合规服务机会")
            second_order.append(f"行业火了 → 人才争夺 → 培训加速机会")

        return second_order

    def _get_risk_chain(self, opp: EcologicalOpportunity) -> list[str]:
        """获取风险链"""
        risks = []

        if opp.opportunity_type == OpportunityType.INFRASTRUCTURE:
            risks.append("核心项目可能换技术栈，依赖关系消失")
            risks.append("基础设施可能自己切入市场")

        if opp.opportunity_type == OpportunityType.CASCADE:
            risks.append("热度消退快，窗口期短")
            risks.append("竞争激烈，先发优势不明显")

        return risks

    def generate_ecological_report(self, core_node_id: str) -> str:
        """生成生态分析报告"""
        if core_node_id not in self.ecosystem_nodes:
            return "核心节点不存在"

        core = self.ecosystem_nodes[core_node_id]

        lines = [f"# 🌍 生态连锁分析报告\n"]
        lines.append(f"**核心节点：** {core.name}\n")
        lines.append(f"**分析时间：** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

        # 生态系统概览
        lines.append(f"\n## 📊 生态系统概览\n")
        nodes_by_type = {}
        for node in self.ecosystem_nodes.values():
            if node.parent_id == core.node_id:
                t = node.node_type.value
                if t not in nodes_by_type:
                    nodes_by_type[t] = []
                nodes_by_type[t].append(node.name)

        for ntype, names in nodes_by_type.items():
            lines.append(f"- **{ntype}**：{', '.join(names)}\n")

        # 供应链关系
        lines.append(f"\n## 🔗 供应链关系\n")
        core_links = [l for l in self.supply_chain_links
                     if core.node_id in [l.from_node, l.to_node]]
        for link in core_links:
            from_name = self.ecosystem_nodes.get(link.from_node, {}).name or link.from_node
            to_name = self.ecosystem_nodes.get(link.to_node, {}).name or link.to_node
            lines.append(f"- {from_name} → {to_name}\n")
            lines.append(f"  - 关系：{link.link_type}\n")
            if link.opportunity:
                lines.append(f"  - 机会：{link.opportunity}\n")

        # 机会挖掘
        opportunities = self.mine_supply_chain_opportunities(core_node_id)

        lines.append(f"\n## 💰 生态连锁机会（{len(opportunities)}个）\n")

        for i, opp in enumerate(opportunities, 1):
            type_icon = {
                OpportunityType.INFRASTRUCTURE: "🏗️",
                OpportunityType.SERVICE: "🛠️",
                OpportunityType.CASCADE: "🔥",
                OpportunityType.DOWNSTREAM: "📦",
                OpportunityType.INVERSE: "↩️",
                OpportunityType.DERIVATIVE: "📎",
            }.get(opp.opportunity_type, "📌")

            lines.append(f"\n### {i}. {type_icon} {opp.description}\n")
            lines.append(f"- **类型**：{opp.opportunity_type.value}\n")
            lines.append(f"- **置信度**：{opp.confidence:.0%}\n")
            lines.append(f"- **预估规模**：{opp.estimated_scale}\n")
            lines.append(f"- **时间窗口**：{opp.time_window}\n")
            lines.append(f"- **进入门槛**：{opp.entry_barrier}\n")
            lines.append(f"- **所需能力**：{', '.join(opp.required_capability)}\n")

        # 连锁分析
        if opportunities:
            lines.append(f"\n## 🔮 深度连锁分析\n")
            chain = self.analyze_opportunity_chain(opportunities[0].opportunity_id)
            if chain.get("second_order"):
                lines.append(f"**二级连锁机会**：\n")
                for so in chain["second_order"]:
                    lines.append(f"- {so}\n")
            if chain.get("risk_chain"):
                lines.append(f"**风险提示**：\n")
                for risk in chain["risk_chain"]:
                    lines.append(f"- ⚠️ {risk}\n")

        return "".join(lines)

    def auto_scan_hot_projects(self) -> list[EcosystemNode]:
        """
        自动扫描最近热门项目

        无需手动 add_core_node，自动从以下来源发现热门项目：
        1. GitHub Trending
        2. Brave Search 热门话题
        3. 新闻/RSS订阅

        Returns:
            新添加的核心节点列表
        """
        import requests
        import os
        from pathlib import Path

        discovered_nodes = []

        # 1. 从 GitHub Trending 获取热门项目
        github_trending = self._fetch_github_trending()
        for project in github_trending:
            node = self.add_core_node(
                name=project["name"],
                description=project.get("description", ""),
                maturity="成长期"
            )
            discovered_nodes.append(node)

        # 2. 从 Brave Search 获取 AI 相关热门话题
        brave_hot_topics = self._fetch_brave_hot_topics()
        for topic in brave_hot_topics:
            node = self.add_core_node(
                name=topic["name"],
                description=topic.get("description", ""),
                maturity="成长期"
            )
            discovered_nodes.append(node)

        # 3. 读取本地缓存的热门项目列表
        local_hot_projects = self._load_local_hot_projects()
        for project in local_hot_projects:
            node = self.add_core_node(
                name=project["name"],
                description=project.get("description", ""),
                maturity=project.get("maturity", "成长期")
            )
            discovered_nodes.append(node)

        return discovered_nodes

    def _fetch_github_trending(self) -> list[dict]:
        """获取 GitHub Trending 项目"""
        try:
            resp = requests.get(
                "https://api.github.com/search/repositories",
                params={
                    "q": "AI OR GPT OR agent created:>2026-01-01",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 5
                },
                headers={"Accept": "application/vnd.github.v3+json"},
                timeout=15
            )

            if resp.status_code == 200:
                data = resp.json()
                return [
                    {
                        "name": item["name"],
                        "description": item.get("description", ""),
                        "stars": item.get("stargazers_count", 0)
                    }
                    for item in data.get("items", [])[:5]
                ]
        except Exception:
            pass

        return []

    def _fetch_brave_hot_topics(self) -> list[dict]:
        """从 Brave Search 获取热门话题"""
        import os

        brave_api_key = os.environ.get("BRAVE_SEARCH_API_KEY", "")
        if not brave_api_key:
            return []

        try:
            resp = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": brave_api_key
                },
                params={
                    "q": "AI tools trending 2026",
                    "count": 5
                },
                timeout=10
            )

            if resp.status_code == 200:
                data = resp.json()
                results = data.get("web", {}).get("results", [])
                return [
                    {
                        "name": r.get("title", "")[:50],
                        "description": r.get("description", "")
                    }
                    for r in results[:5]
                ]
        except Exception:
            pass

        return []

    def _load_local_hot_projects(self) -> list[dict]:
        """
        加载本地缓存的热门项目

        读取路径：opportunity_discovery/hot_projects.json
        格式：[{"name": "...", "description": "...", "maturity": "..."}]
        """
        from pathlib import Path

        hot_file = Path("/home/admin1/aiagent/代理知识库/我的/opportunity_discovery/hot_projects.json")

        if not hot_file.exists():
            return []

        try:
            import json
            with open(hot_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def export_to_json(self, filepath: str = None) -> str:
        """导出生态数据为 JSON 格式"""
        if filepath is None:
            from pathlib import Path
            output_dir = Path("/home/admin1/aiagent/代理知识库/我的/opportunity_discovery/discovered_projects")
            output_dir.mkdir(parents=True, exist_ok=True)
            filepath = str(output_dir / f"ecological_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

        export_data = {
            "export_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "core_nodes": [],
            "supply_links": [],
            "opportunities": []
        }

        # 导出核心节点
        for node in self.ecosystem_nodes.values():
            if node.node_type == EcosystemNodeType.CORE:
                export_data["core_nodes"].append({
                    "node_id": node.node_id,
                    "name": node.name,
                    "description": node.description,
                    "maturity": node.maturity
                })

        # 导出供应链关系
        for link in self.supply_chain_links:
            export_data["supply_links"].append({
                "link_id": link.link_id,
                "from": link.from_node,
                "to": link.to_node,
                "type": link.link_type,
                "opportunity": link.opportunity
            })

        # 导出机会
        for opp in self.opportunities:
            export_data["opportunities"].append({
                "id": opp.opportunity_id,
                "type": opp.opportunity_type.value,
                "description": opp.description,
                "confidence": opp.confidence,
                "position": opp.position_in_chain
            })

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        return filepath


# ============== 使用示例 ==============

if __name__ == "__main__":
    miner = EcosystemMiner()

    # 添加OpenClaw作为核心节点
    openclaw = miner.add_core_node(
        name="OpenClaw",
        description="AI Agent框架",
        maturity="成长期"
    )

    # 发现生态系统
    print(f"核心节点: {openclaw.name} (ID: {openclaw.node_id})")

    # 挖掘生态系统
    ecosphere = miner.discover_ecosphere(openclaw.node_id)
    print(f"\n发现 {len(ecosphere)} 个生态节点")

    # 生成报告
    report = miner.generate_ecological_report(openclaw.node_id)
    print("\n" + report)