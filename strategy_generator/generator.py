"""
连带实现策略生成器 v2.0
Strategy Generator v2.0 — L8.3 强化版核心模块

在L8.2基础上增加：
1. 多路径策略对比（A/B/C方案并行生成）
2. 策略风险收益对比矩阵
3. 策略推荐评分（基于机会匹配度）
4. 动态策略调整机制

输入：DeepOpportunity对象
输出：多路径策略对比报告 + 推荐方案
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from evolution_event_bus import EventBus

# 从 unified_enums 导入策略阶段枚举
from unified_enums import StrategyPhase

@dataclass
class StrategyOption:
    """策略选项"""
    option_id: str  # A/B/C
    option_name: str
    description: str
    
    # 策略特征
    investment_level: str  # 高/中/低
    risk_level: str  # 高/中/低
    expected_return: str  # 高/中/低
    time_to_market: str  # 快速/中等/慢速
    
    # 详细策略
    entry_tactics: list[str] = field(default_factory=list)
    growth_tactics: list[str] = field(default_factory=list)
    defense_tactics: list[str] = field(default_factory=list)
    
    # 资源需求
    resources_needed: list[str] = field(default_factory=list)
    budget_estimate: str = ""
    team_requirement: str = ""
    
    # 评估
    fit_score: float = 0.0  # 与机会的匹配度
    feasibility_score: float = 0.0  # 可行性评分
    recommended: bool = False

@dataclass
class SynergyEffect:
    """连带效应"""
    effect_name: str
    effect_type: str
    description: str
    potential_value: str
    realization_difficulty: str

@dataclass
class ResourceLinkage:
    """资源联动"""
    existing_asset: str
    reuse_method: str
    synergy_value: str
    required_investment: str

@dataclass
class CompetitiveAdvantage:
    """竞争优势"""
    advantage_type: str
    build_path: str
    time_to_build: str
    defensibility: str

@dataclass
class PhaseStrategy:
    """阶段性策略"""
    phase: StrategyPhase
    objective: str
    key_actions: list[str]
    success_metrics: list[str]
    timeline: str
    resource_needed: list[str]
    risks: list[str]

@dataclass
class OverallStrategy:
    """完整连带实现策略"""
    opportunity_name: str
    
    # 多路径策略
    strategy_options: list[StrategyOption] = field(default_factory=list)
    recommended_option: StrategyOption = None
    
    # 核心策略摘要
    entry_strategy: str = ""
    penetration_strategy: str = ""
    expansion_strategy: str = ""
    defense_strategy: str = ""
    
    # 连带效应
    synergy_effects: list[SynergyEffect] = field(default_factory=list)
    
    # 资源联动
    resource_linkages: list[ResourceLinkage] = field(default_factory=list)
    
    # 竞争优势
    competitive_advantages: list[CompetitiveAdvantage] = field(default_factory=list)
    
    # 阶段策略
    phase_strategies: list[PhaseStrategy] = field(default_factory=list)
    
    # 关键里程碑
    milestones: list[str] = field(default_factory=list)
    
    # 风险预案
    risk_plans: dict[str, str] = field(default_factory=dict)


class StrategyGenerator:
    """连带实现策略生成器 v2.0"""

    def __init__(self, event_bus: 'EventBus' = None):
        self.strategies: list[OverallStrategy] = []
        self.event_bus = event_bus
    
    def generate_multi_path(self, opportunity_name: str,
                           core_capability: str,
                           existing_assets: list[str],
                           target_users: list[str],
                           revenue_model: str,
                           opportunity_fit: float = 7.5) -> OverallStrategy:
        """生成多路径策略对比"""
        
        strategy = OverallStrategy(opportunity_name=opportunity_name)
        
        # 生成A/B/C三个策略选项
        strategy.strategy_options = self._generate_option_a(
            opportunity_name, core_capability, target_users, revenue_model
        ) + self._generate_option_b(
            opportunity_name, core_capability, target_users, revenue_model
        ) + self._generate_option_c(
            opportunity_name, core_capability, target_users, revenue_model
        )
        
        # 计算每个策略的匹配度和可行性
        self._score_options(strategy.strategy_options, opportunity_fit)
        
        # 选择推荐策略
        self._select_recommended(strategy)
        
        # 生成连带效应和资源联动
        strategy.synergy_effects = self._analyze_synergy(opportunity_name, existing_assets)
        strategy.resource_linkages = self._plan_resource_linkage(existing_assets, opportunity_name)
        strategy.competitive_advantages = self._build_competitive_advantage(core_capability)
        
        # 生成阶段策略（基于推荐方案）
        if strategy.recommended_option:
            strategy.phase_strategies = self._generate_phase_strategies(
                strategy.recommended_option
            )
        
        # 设置里程碑
        strategy.milestones = [
            "Day 3: 最小验证完成",
            "Day 7: 产品化完成",
            "Day 14: 首批付费用户",
            "Day 30: 可持续的获客模式",
            "Day 60: 护城河初步建立"
        ]
        
        # 风险预案
        strategy.risk_plans = {
            "竞品快速复制": "快速迭代 + 差异化功能",
            "用户付费意愿低于预期": "降低定价 + 增加免费额度",
            "技术方案不可行": "准备备选方案/外采"
        }
        
        self.strategies.append(strategy)
        return strategy
    
    def _generate_option_a(self, name: str, capability: str,
                          users: list, revenue: str) -> list[StrategyOption]:
        """方案A：快速验证策略（低成本、快速启动）"""
        return [StrategyOption(
            option_id="A",
            option_name="快速验证策略",
            description="以最低成本快速验证核心假设，专注于产品-市场匹配",
            investment_level="低",
            risk_level="中",
            expected_return="中",
            time_to_market="快速",
            entry_tactics=[
                "单一人工服务模式起步",
                "聚焦单一用户痛点",
                "手动服务流程验证"
            ],
            growth_tactics=[
                "根据反馈快速迭代",
                "口碑获客",
                "逐步工具化"
            ],
            defense_tactics=[
                "积累用户信任",
                "建立品牌认知"
            ],
            resources_needed=["1人", "基础工具"],
            budget_estimate="<1000元",
            team_requirement="1人核心团队"
        )]
    
    def _generate_option_b(self, name: str, capability: str,
                          users: list, revenue: str) -> list[StrategyOption]:
        """方案B：均衡发展策略（中等投入、平衡风险）"""
        return [StrategyOption(
            option_id="B",
            option_name="均衡发展策略",
            description="投入适度资源，建立完整产品线，追求可持续增长",
            investment_level="中",
            risk_level="中",
            expected_return="高",
            time_to_market="中等",
            entry_tactics=[
                "MVP产品开发",
                "多渠道测试",
                "内容营销建立信任"
            ],
            growth_tactics=[
                "产品功能完善",
                "多渠道获客",
                "用户留存体系"
            ],
            defense_tactics=[
                "数据积累",
                "功能迭代领先",
                "用户社区"
            ],
            resources_needed=["2-3人", "完整工具链", "营销预算"],
            budget_estimate="3000-10000元",
            team_requirement="2-3人团队"
        )]
    
    def _generate_option_c(self, name: str, capability: str,
                          users: list, revenue: str) -> list[StrategyOption]:
        """方案C：全力冲刺策略（高投入、高风险高回报）"""
        return [StrategyOption(
            option_id="C",
            option_name="全力冲刺策略",
            description="大投入快速抢占市场，建立领先地位，适合窗口期短的机会",
            investment_level="高",
            risk_level="高",
            expected_return="高",
            time_to_market="快速",
            entry_tactics=[
                "完整产品开发",
                "多渠道同步启动",
                "付费投放获客"
            ],
            growth_tactics=[
                "规模化获客",
                "快速扩张团队",
                "市场独占"
            ],
            defense_tactics=[
                "技术壁垒",
                "数据壁垒",
                "品牌壁垒"
            ],
            resources_needed=["5人+", "充足预算", "完整运营"],
            budget_estimate=">20000元",
            team_requirement="5人+完整团队"
        )]
    
    def _score_options(self, options: list[StrategyOption], opportunity_fit: float):
        """为每个策略评分"""
        for option in options:
            # 匹配度评分（基于投入水平和机会匹配度）
            if option.investment_level == "低":
                option.fit_score = opportunity_fit * 0.9
            elif option.investment_level == "中":
                option.fit_score = opportunity_fit * 1.0
            else:
                option.fit_score = opportunity_fit * 0.85
            
            # 可行性评分（基于风险和投入）
            if option.risk_level == "低":
                option.feasibility_score = 8.5
            elif option.risk_level == "中":
                option.feasibility_score = 7.0
            else:
                option.feasibility_score = 5.5
    
    def _select_recommended(self, strategy: OverallStrategy):
        """选择推荐策略"""
        # 基于匹配度和可行性选择最优
        best = None
        best_score = 0
        for option in strategy.strategy_options:
            score = option.fit_score * 0.6 + option.feasibility_score * 0.4
            if score > best_score:
                best_score = score
                best = option

        if best:
            best.recommended = True
            strategy.recommended_option = best

            # 发布策略选中事件（可选）
            if self.event_bus:
                self.event_bus.publish("strategy.selected", {
                    "opp_name": strategy.opportunity_name,
                    "option_id": best.option_id,
                    "fit_score": best.fit_score,
                    "feasibility": best.feasibility_score
                }, source_module="StrategyGenerator")
    
    def _analyze_synergy(self, name: str, assets: list) -> list[SynergyEffect]:
        effects = []
        for asset in assets:
            effects.append(SynergyEffect(
                effect_name=f"{asset}协同{name}",
                effect_type="资源复用",
                description=f"复用{asset}触达目标用户",
                potential_value="中等",
                realization_difficulty="低"
            ))
        return effects
    
    def _plan_resource_linkage(self, assets: list, name: str) -> list[ResourceLinkage]:
        linkages = []
        for asset in assets:
            linkages.append(ResourceLinkage(
                existing_asset=asset,
                reuse_method=f"作为{name}的获客渠道",
                synergy_value="降低CAC",
                required_investment="低"
            ))
        return linkages
    
    def _build_competitive_advantage(self, capability: str) -> list[CompetitiveAdvantage]:
        return [
            CompetitiveAdvantage(
                advantage_type="数据积累",
                build_path="用户使用过程中积累数据",
                time_to_build="1-2个月",
                defensibility="中"
            )
        ]
    
    def _generate_phase_strategies(self, option: StrategyOption) -> list[PhaseStrategy]:
        base_actions = {
            "A": ["人工验证", "快速迭代", "口碑获客"],
            "B": ["MVP开发", "多渠道测试", "内容营销"],
            "C": ["完整开发", "付费投放", "规模化"]
        }
        
        return [
            PhaseStrategy(
                phase=StrategyPhase.ENTRY,
                objective="完成核心功能和市场验证",
                key_actions=base_actions.get(option.option_id, ["标准流程"]),
                success_metrics=["付费用户≥10" if option.option_id != "A" else "付费用户≥3"],
                timeline="Week 1-2",
                resource_needed=option.resources_needed,
                risks=["功能不符合需求"]
            )
        ]
    
    def generate_comparison_report(self, strategy: OverallStrategy) -> str:
        """生成多路径策略对比报告"""
        lines = [f"# 多路径策略对比报告：{strategy.opportunity_name}\n"]
        lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        
        lines.append(f"\n## 策略对比矩阵\n")
        lines.append(f"| 维度 | A-快速验证 | B-均衡发展 | C-全力冲刺 |\n")
        lines.append(f"|------|-----------|-----------|-----------|\n")
        
        options = {o.option_id: o for o in strategy.strategy_options}
        
        for dim in ["investment_level", "risk_level", "expected_return", "time_to_market"]:
            row = f"| {dim.replace('_', ' ').title()} |"
            for opt_id in ["A", "B", "C"]:
                if opt_id in options:
                    val = getattr(options[opt_id], dim, "")
                    row += f" {val} |"
                else:
                    row += " - |"
            lines.append(row + "\n")
        
        lines.append(f"\n## 评分对比\n")
        lines.append(f"| 策略 | 匹配度 | 可行性 | 综合 | 推荐 |\n")
        lines.append(f"|------|--------|--------|------|------|\n")
        for option in strategy.strategy_options:
            rec = "✅" if option.recommended else ""
            lines.append(f"| {option.option_id}-{option.option_name} | {option.fit_score:.1f} | {option.feasibility_score:.1f} | {option.fit_score*0.6+option.feasibility_score*0.4:.1f} | {rec} |\n")
        
        if strategy.recommended_option:
            reco = strategy.recommended_option
            lines.append(f"\n## 推荐方案：{reco.option_id} - {reco.option_name}\n")
            lines.append(f"**原因：** 综合匹配度{reco.fit_score:.1f} + 可行性{reco.feasibility_score:.1f}\n")
            lines.append(f"**投入：** {reco.budget_estimate}\n")
            lines.append(f"**团队：** {reco.team_requirement}\n")
            lines.append(f"\n**进入策略：**\n")
            for t in reco.entry_tactics:
                lines.append(f"- {t}\n")
        
        return "".join(lines)
    
    def generate_report(self, strategy: OverallStrategy) -> str:
        """生成完整策略报告"""
        lines = [f"# 连带实现策略：{strategy.opportunity_name}\n"]
        lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        
        lines.append(f"\n## 推荐策略摘要\n")
        if strategy.recommended_option:
            reco = strategy.recommended_option
            lines.append(f"**方案：** {reco.option_id} - {reco.option_name}\n")
            lines.append(f"**投入水平：** {reco.investment_level}\n")
            lines.append(f"**风险等级：** {reco.risk_level}\n")
            lines.append(f"**预期收益：** {reco.expected_return}\n")
        
        lines.append(f"\n## 连带效应\n")
        for s in strategy.synergy_effects:
            lines.append(f"- **{s.effect_name}**：{s.description}\n")
        
        lines.append(f"\n## 资源联动\n")
        for r in strategy.resource_linkages:
            lines.append(f"- {r.existing_asset} → {r.reuse_method}\n")
        
        return "".join(lines)


if __name__ == "__main__":
    gen = StrategyGenerator()
    
    strategy = gen.generate_multi_path(
        opportunity_name="知识博主AI助手",
        core_capability="AI辅助写作",
        existing_assets=["小红书账号", "AI提示词库", "闲鱼商品"],
        target_users=["知识博主", "内容创作者"],
        revenue_model="订阅制/月费99",
        opportunity_fit=8.0
    )
    
    print(gen.generate_comparison_report(strategy))
