"""
落地方案实行引擎 v2.0
Execution Engine v2.0 — L8.3 强化版核心模块

在L8.2基础上增加：
1. 自动任务分解（从策略自动生成任务列表）
2. 进度预警机制（基于临界值的自动预警）
3. 偏差自动纠正机制（检测偏差并提出纠正方案）
4. 动态调整能力（根据执行状态调整后续计划）

输入：OverallStrategy对象
输出：自动生成的可执行任务系统 + 实时监控 + 偏差纠正建议
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timedelta
import json

if TYPE_CHECKING:
    from evolution_event_bus import EventBus

# 从 unified_enums 导入枚举
from unified_enums import TaskStatus, TaskPriority as Priority, AlertLevel

# 保持向后兼容的类型别名
# (旧代码可能使用 Priority，但统一后应使用 TaskPriority)

@dataclass
class Task:
    """可执行任务"""
    task_id: str
    title: str
    description: str
    phase: str  # 72h / 7d / 30d
    priority: Priority
    status: TaskStatus = TaskStatus.PENDING
    assignee: str = ""
    estimated_hours: float = 0.0
    actual_hours: float = 0.0
    depends_on: list[str] = field(default_factory=list)
    created_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    start_date: str = ""
    due_date: str = ""
    completed_date: str = ""
    blockers: list[str] = field(default_factory=list)
    notes: str = ""
    
    # 偏差追踪
    progress: float = 0.0  # 0-100%
    deviation: float = 0.0  # 与计划的偏差%
    deviation_reason: str = ""

@dataclass
class Alert:
    """预警信息"""
    alert_id: str
    level: AlertLevel
    title: str
    description: str
    trigger_condition: str
    generated_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    acknowledged: bool = False
    resolved: bool = False

@dataclass
class Correction:
    """偏差纠正方案"""
    correction_id: str
    task_id: str
    original_plan: str
    deviation_detected: str
    correction_action: str
    expected_outcome: str
    approved: bool = False

@dataclass
class RiskControl:
    """风险控制点"""
    risk_id: str
    description: str
    probability: str
    impact: str
    mitigation: str
    contingency: str
    trigger_condition: str
    status: str = "monitoring"
    monitoring_metrics: list[str] = field(default_factory=list)

@dataclass
class ExecutionPhase:
    """执行阶段"""
    phase_name: str
    start_date: str
    end_date: str
    objectives: list[str]
    tasks: list[Task] = field(default_factory=list)
    deliverables: list[str] = field(default_factory=list)
    status: str = "pending"
    
    # 进度预警阈值
    warning_threshold: float = 0.7  # 完成<70%触发警告
    critical_threshold: float = 0.5  # 完成<50%触发严重警告
    
    # 阶段健康度
    health_score: float = 100.0  # 0-100

@dataclass
class ProgressTracker:
    """进度追踪器"""
    phase: str
    total_tasks: int = 0
    completed_tasks: int = 0
    blocked_tasks: int = 0
    overall_progress: float = 0.0
    kpis: dict[str, float] = field(default_factory=dict)
    risks_triggered: list[str] = field(default_factory=list)
    
    # 预警状态
    alerts: list[Alert] = field(default_factory=list)
    corrections: list[Correction] = field(default_factory=list)
    
    def calculate_progress(self):
        if self.total_tasks == 0:
            self.overall_progress = 0.0
        else:
            self.overall_progress = (self.completed_tasks / self.total_tasks) * 100
        return self

@dataclass
class ExecutionPlan:
    """完整执行计划"""
    opportunity_name: str
    strategy_summary: str
    recommended_strategy_id: str = ""  # A/B/C
    
    phases: list[ExecutionPhase] = field(default_factory=list)
    all_tasks: list[Task] = field(default_factory=list)
    risk_controls: list[RiskControl] = field(default_factory=list)
    progress: dict[str, ProgressTracker] = field(default_factory=dict)
    
    start_date: str = ""
    target_end_date: str = ""
    
    # 决策机制
    checkpoint_decisions: list[str] = field(default_factory=list)
    escalation_rules: dict[str, str] = field(default_factory=dict)
    
    # 预警配置
    auto_task_decomposition: bool = True
    deviation_threshold: float = 0.2  # 偏差>20%触发纠正
    alert_cooldown_hours: int = 24  # 预警冷却时间

class ExecutionEngine:
    """落地方案实行引擎 v2.1"""

    def __init__(self, event_bus: 'EventBus' = None, persistence=None):
        self.plans: list[ExecutionPlan] = []
        self.task_counter = 0
        self.alert_counter = 0
        self.correction_counter = 0
        self.event_bus = event_bus
        self.persistence = persistence  # ExecutionPlanPersistence 实例
    
    def create_plan(self, opportunity_name: str, strategy_summary: str,
                   strategy_id: str = "B") -> ExecutionPlan:
        """创建执行计划"""
        plan = ExecutionPlan(
            opportunity_name=opportunity_name,
            strategy_summary=strategy_summary,
            recommended_strategy_id=strategy_id,
            start_date=datetime.now().strftime("%Y-%m-%d"),
            target_end_date=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        )
        self.plans.append(plan)
        return plan
    
    def auto_decompose_tasks(self, plan: ExecutionPlan, 
                            phase: ExecutionPhase,
                            strategy_actions: list[str]):
        """从策略动作自动分解任务"""
        action_task_map = {
            "人工验证": [("准备验证方案", 2.0, Priority.P1), ("执行验证", 4.0, Priority.P0), ("分析结果", 1.0, Priority.P1)],
            "快速迭代": [("收集反馈", 2.0, Priority.P1), ("优先级排序", 1.0, Priority.P1), ("实施改进", 3.0, Priority.P0)],
            "口碑获客": [("识别种子用户", 1.0, Priority.P2), ("服务种子用户", 4.0, Priority.P1), ("收集证言", 1.0, Priority.P2)],
            "MVP开发": [("需求文档", 2.0, Priority.P1), ("核心功能开发", 8.0, Priority.P0), ("测试上线", 2.0, Priority.P1)],
            "多渠道测试": [("渠道调研", 2.0, Priority.P2), ("准备测试物料", 3.0, Priority.P1), ("执行测试", 4.0, Priority.P1)],
            "内容营销": [("内容规划", 2.0, Priority.P1), ("创作内容", 4.0, Priority.P1), ("发布+监测", 2.0, Priority.P2)],
            "完整开发": [("技术架构", 4.0, Priority.P1), ("功能开发", 16.0, Priority.P0), ("测试验收", 4.0, Priority.P1)],
            "付费投放": [("渠道选择", 2.0, Priority.P1), ("物料准备", 4.0, Priority.P1), ("投放执行", 8.0, Priority.P0)],
            "规模化": [("流程标准化", 4.0, Priority.P1), ("团队扩张", 8.0, Priority.P1), ("SOP建立", 4.0, Priority.P2)]
        }
        
        for action in strategy_actions:
            tasks = action_task_map.get(action, [(action, 4.0, Priority.P2)])
            for title, hours, priority in tasks:
                self.create_task(plan, title, f"执行{title}", 
                              phase.phase_name, priority, hours)
        
        # 更新phase
        for p in plan.phases:
            if p.phase_name == phase.phase_name:
                p.tasks = [t for t in plan.all_tasks if t.phase == phase.phase_name]
                break
    
    def create_task(self, plan: ExecutionPlan, title: str, description: str,
                    phase: str, priority: Priority, estimated_hours: float,
                    assignee: str = "战略爪", depends_on: list[str] = None) -> Task:
        """创建任务"""
        self.task_counter += 1
        task = Task(
            task_id=f"T{self.task_counter:03d}",
            title=title,
            description=description,
            phase=phase,
            priority=priority,
            assignee=assignee,
            estimated_hours=estimated_hours,
            depends_on=depends_on or [],
            due_date=self._calculate_due_date(phase)
        )
        plan.all_tasks.append(task)
        
        # 添加到对应phase
        for p in plan.phases:
            if p.phase_name == phase:
                p.tasks.append(task)
                break
        
        return task
    
    def add_phase(self, plan: ExecutionPlan, phase: ExecutionPhase):
        """添加执行阶段"""
        plan.phases.append(phase)
    
    def add_risk_control(self, plan: ExecutionPlan, risk: RiskControl):
        """添加风险控制点"""
        plan.risk_controls.append(risk)
    
    def create_risk_control(self, plan: ExecutionPlan, description: str,
                           probability: str, impact: str,
                           mitigation: str, contingency: str,
                           trigger_condition: str) -> RiskControl:
        """创建风险控制"""
        risk_id = f"R{len(plan.risk_controls)+1:02d}"
        return RiskControl(
            risk_id=risk_id,
            description=description,
            probability=probability,
            impact=impact,
            mitigation=mitigation,
            contingency=contingency,
            trigger_condition=trigger_condition
        )
    
    def update_task_progress(self, plan: ExecutionPlan, task_id: str, 
                            progress: float, notes: str = ""):
        """更新任务进度"""
        for task in plan.all_tasks:
            if task.task_id == task_id:
                old_progress = task.progress
                task.progress = min(progress, 100.0)
                
                # 计算偏差
                if task.status == TaskStatus.DONE:
                    task.deviation = 0.0
                else:
                    expected = self._get_expected_progress(task)
                    task.deviation = (task.progress - expected) / max(expected, 1) if expected > 0 else 0
                
                # 检测偏差是否需要纠正
                if abs(task.deviation) > plan.deviation_threshold and task.status != TaskStatus.DONE:
                    correction = self._generate_correction(plan, task, old_progress)
                    self._add_correction(plan, correction)
                
                # 触发进度检查
                self._check_progress_alerts(plan, task)
                
                if notes:
                    task.notes = notes
                break
        self._update_progress(plan)
        self._save_progress(plan)

    def update_task_status(self, plan: ExecutionPlan, task_id: str,
                          status: TaskStatus, notes: str = ""):
        """更新任务状态"""
        task = self._find_task(plan, task_id)
        if not task:
            return

        # 检查依赖是否满足
        if status == TaskStatus.IN_PROGRESS:
            if not self._check_dependencies(plan, task):
                # 依赖未完成，阻塞任务
                task.status = TaskStatus.BLOCKED
                task.blockers = [f"等待依赖: {dep}" for dep in task.depends_on]
                self._save_progress(plan)
                return

        task.status = status
        if status == TaskStatus.IN_PROGRESS and not task.start_date:
            task.start_date = datetime.now().strftime("%Y-%m-%d")
        elif status == TaskStatus.DONE:
            task.completed_date = datetime.now().strftime("%Y-%m-%d")
            task.progress = 100.0
            task.deviation = 0.0
            # 释放被该任务阻塞的下游任务
            self._unblock_dependent_tasks(plan, task_id)

        if notes:
            task.notes = notes

        self._update_progress(plan)
        self._save_progress(plan)

        # 发布任务完成事件
        if status == TaskStatus.DONE and self.event_bus:
            self.event_bus.publish("task.completed", {
                "task_id": task_id,
                "plan_name": plan.opportunity_name,
                "phase": task.phase,
                "deviation": task.deviation,
                "actual_hours": task.actual_hours
            }, source_module="ExecutionEngine")

    def _find_task(self, plan: ExecutionPlan, task_id: str):
        """查找任务"""
        for task in plan.all_tasks:
            if task.task_id == task_id:
                return task
        return None

    def _check_dependencies(self, plan: ExecutionPlan, task: Task) -> bool:
        """检查依赖是否全部完成"""
        if not task.depends_on:
            return True

        for dep_id in task.depends_on:
            dep_task = self._find_task(plan, dep_id)
            if dep_task and dep_task.status != TaskStatus.DONE:
                return False
        return True

    def _unblock_dependent_tasks(self, plan: ExecutionPlan, completed_task_id: str):
        """释放被任务阻塞的下游任务"""
        for task in plan.all_tasks:
            if completed_task_id in task.depends_on:
                if task.status == TaskStatus.BLOCKED:
                    # 检查是否所有依赖都已完成
                    if self._check_dependencies(plan, task):
                        task.status = TaskStatus.PENDING
                        task.blockers = []

    def _save_progress(self, plan: ExecutionPlan):
        """自动保存进度到持久化层"""
        if not self.persistence:
            return

        try:
            from execution_persistence import serialize_dataclass
            # 保存进度
            progress_data = {}
            for phase_name, tracker in plan.progress.items():
                progress_data[phase_name] = {
                    "overall_progress": getattr(tracker, 'overall_progress', 0.0),
                    "completed_tasks": getattr(tracker, 'completed_tasks', 0),
                    "total_tasks": getattr(tracker, 'total_tasks', 0),
                    "blocked_tasks": getattr(tracker, 'blocked_tasks', 0)
                }

            # 同时保存任务状态
            tasks_data = []
            for task in plan.all_tasks:
                tasks_data.append({
                    "task_id": task.task_id,
                    "status": task.status.value,
                    "progress": task.progress,
                    "deviation": task.deviation,
                    "completed_date": task.completed_date
                })

            self.persistence.save_progress(plan.opportunity_name, {
                "progress": progress_data,
                "tasks": tasks_data
            })
        except Exception:
            pass  # 静默失败，不影响主流程
    
    def _get_expected_progress(self, task: Task) -> float:
        """计算任务的预期进度（基于时间）"""
        if not task.due_date or not task.start_date:
            return 0.0
        
        try:
            due = datetime.strptime(task.due_date, "%Y-%m-%d")
            start = datetime.strptime(task.start_date, "%Y-%m-%d")
            now = datetime.now()
            
            total_days = (due - start).days
            elapsed_days = (now - start).days
            
            if total_days <= 0:
                return task.progress
            
            return min(100.0, (elapsed_days / total_days) * 100)
        except:
            return task.progress
    
    def _generate_correction(self, plan: ExecutionPlan, task: Task, 
                           old_progress: float) -> Correction:
        """生成偏差纠正方案"""
        self.correction_counter += 1
        
        deviation_pct = abs(task.deviation) * 100
        action = ""
        expected = ""
        
        if task.deviation < 0:
            # 落后于计划
            if task.priority == Priority.P0:
                action = "增加资源/拆解任务，争取快速赶上"
                expected = "2天内进度提升至正常"
            elif task.priority == Priority.P1:
                action = "分析阻塞原因，调配资源"
                expected = "3天内赶上计划"
            else:
                action = "重新评估任务必要性，考虑缩小范围"
                expected = "4天内完成或调整"
        else:
            # 领先于计划
            action = "进度正常，保持当前节奏"
            expected = "继续执行"
        
        return Correction(
            correction_id=f"C{self.correction_counter:03d}",
            task_id=task.task_id,
            original_plan=f"原计划{self._get_expected_progress(task):.0f}%",
            deviation_detected=f"当前{task.progress:.0f}%，偏差{deviation_pct:.0f}%",
            correction_action=action,
            expected_outcome=expected
        )
    
    def _add_correction(self, plan: ExecutionPlan, correction: Correction):
        """添加纠正方案"""
        # 找到任务所属的phase，添加到对应的tracker
        for p in plan.phases:
            if any(t.task_id == correction.task_id for t in p.tasks):
                tracker = plan.progress.get(p.phase_name)
                if tracker and correction not in tracker.corrections:
                    tracker.corrections.append(correction)
                break
    
    def _check_progress_alerts(self, plan: ExecutionPlan, task: Task):
        """检查是否需要进度预警"""
        for phase in plan.phases:
            if task.phase != phase.phase_name:
                continue
            
            tracker = plan.progress.get(phase.phase_name)
            if not tracker:
                continue

            # 检查是否满足预警冷却 (tracker可能是dict或ProgressTracker)
            alerts = getattr(tracker, 'alerts', []) if isinstance(tracker, object) else tracker.get('alerts', [])
            recent_alerts = [a for a in alerts
                          if getattr(a, 'acknowledged', True) is False
                          and (datetime.now() - datetime.strptime(getattr(a, 'generated_at', '2000-01-01 00:00'), "%Y-%m-%d %H:%M")).seconds < plan.alert_cooldown_hours * 3600]
            if recent_alerts:
                return

            # 生成预警
            if task.deviation < -0.3:
                self.alert_counter += 1
                alert = Alert(
                    alert_id=f"A{self.alert_counter:03d}",
                    level=AlertLevel.CRITICAL,
                    title=f"任务严重落后：{task.title}",
                    description=f"偏差{abs(task.deviation)*100:.0f}%，需要立即关注",
                    trigger_condition=f"deviation<{-0.3}"
                )
                if hasattr(tracker, 'alerts'):
                    tracker.alerts.append(alert)
    
    def check_all_alerts(self, plan: ExecutionPlan) -> list[Alert]:
        """检查所有预警"""
        all_alerts = []
        for tracker in plan.progress.values():
            all_alerts.extend([a for a in tracker.alerts if not a.acknowledged])
        return sorted(all_alerts, key=lambda x: x.level.value)
    
    def check_all_corrections(self, plan: ExecutionPlan) -> list[Correction]:
        """检查所有待处理纠正方案"""
        all_corrections = []
        for tracker in plan.progress.values():
            all_corrections.extend([c for c in tracker.corrections if not c.approved])
        return all_corrections
    
    def approve_correction(self, plan: ExecutionPlan, correction_id: str):
        """批准纠正方案"""
        for tracker in plan.progress.values():
            for c in tracker.corrections:
                if c.correction_id == correction_id:
                    c.approved = True
                    # 更新任务
                    for task in plan.all_tasks:
                        if task.task_id == c.task_id:
                            task.notes += f"\n[纠正已批准] {c.correction_action}"
                    break
    
    def generate_execution_checklist(self, plan: ExecutionPlan) -> str:
        """生成执行Checklist"""
        lines = [f"# 执行Checklist：{plan.opportunity_name}\n"]
        lines.append(f"策略方案：{plan.recommended_strategy_id}\n")
        lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        
        for phase in plan.phases:
            tracker = plan.progress.get(phase.phase_name)
            health = tracker.overall_progress if tracker else 0
            
            lines.append(f"\n## {phase.phase_name}阶段\n")
            lines.append(f"**进度：** {health:.0f}%")
            lines.append(f"**状态：** {phase.status}\n")
            lines.append(f"**目标：** {', '.join(phase.objectives)}\n")
            
            for task in phase.tasks:
                status_icon = task.status.value
                priority_icon = "🔴" if task.priority == Priority.P0 else "🟡" if task.priority == Priority.P1 else "⚪"
                dev_info = f" (偏差{task.deviation*100:+.0f}%)" if task.deviation != 0 and task.status != TaskStatus.DONE else ""
                lines.append(f"{status_icon}{priority_icon} [{task.task_id}] {task.title}{dev_info}\n")
                lines.append(f"   - 进度：{task.progress:.0f}% | 预计：{task.estimated_hours}h\n")
        
        # 预警
        alerts = self.check_all_alerts(plan)
        if alerts:
            lines.append(f"\n## 🚨 待处理预警\n")
            for alert in alerts:
                lines.append(f"{alert.level.value} **{alert.title}**：{alert.description}\n")
        
        # 纠正方案
        corrections = self.check_all_corrections(plan)
        if corrections:
            lines.append(f"\n## 📋 待批准纠正方案\n")
            for c in corrections:
                lines.append(f"[ ] **{c.correction_id}** - {c.task_id}：{c.correction_action}\n")
        
        return "".join(lines)
    
    def generate_progress_report(self, plan: ExecutionPlan) -> str:
        """生成进度报告"""
        self._update_progress(plan)
        
        lines = [f"# 进度报告：{plan.opportunity_name}\n"]
        lines.append(f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        
        for phase_name, tracker in plan.progress.items():
            tracker.calculate_progress()
            lines.append(f"\n## {phase_name}\n")
            lines.append(f"**总体进度：** {tracker.overall_progress:.1f}%\n")
            lines.append(f"- 总任务：{tracker.total_tasks}\n")
            lines.append(f"- 已完成：{tracker.completed_tasks} ✅\n")
            lines.append(f"- 进行中：{tracker.total_tasks - tracker.completed_tasks - tracker.blocked_tasks} 🔄\n")
            lines.append(f"- 阻塞中：{tracker.blocked_tasks} 🚫\n")
            
            if tracker.kpis:
                lines.append(f"\n**KPIs：**\n")
                for kpi, value in tracker.kpis.items():
                    lines.append(f"- {kpi}：{value}\n")
            
            if tracker.alerts:
                unack = [a for a in tracker.alerts if not a.acknowledged]
                if unack:
                    lines.append(f"\n⚠️ **待处理预警：**\n")
                    for a in unack:
                        lines.append(f"- {a.level.value} {a.title}\n")
        
        return "".join(lines)
    
    def _calculate_due_date(self, phase: str) -> str:
        """计算截止日期"""
        days_map = {"72h": 3, "7d": 7, "30d": 30}
        days = days_map.get(phase, 14)
        return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    
    def _update_progress(self, plan: ExecutionPlan):
        """更新进度"""
        for phase in plan.phases:
            tracker = ProgressTracker(phase=phase.phase_name)
            tracker.total_tasks = len(phase.tasks)
            tracker.completed_tasks = sum(1 for t in phase.tasks if t.status == TaskStatus.DONE)
            tracker.blocked_tasks = sum(1 for t in phase.tasks if t.status == TaskStatus.BLOCKED)
            tracker.calculate_progress()
            plan.progress[phase.phase_name] = tracker


if __name__ == "__main__":
    engine = ExecutionEngine()
    
    plan = engine.create_plan(
        "知识博主AI助手",
        "帮知识博主用AI提升创作效率，采用订阅制变现",
        strategy_id="B"
    )
    
    # 72h阶段
    phase_72h = ExecutionPhase(
        phase_name="72h",
        start_date=datetime.now().strftime("%Y-%m-%d"),
        end_date=(datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"),
        objectives=["完成核心功能验证", "获取首批用户反馈"]
    )
    engine.add_phase(plan, phase_72h)
    
    # 自动分解任务
    engine.auto_decompose_tasks(plan, phase_72h, ["MVP开发", "多渠道测试"])
    
    # 模拟更新任务进度
    if plan.all_tasks:
        engine.update_task_progress(plan, plan.all_tasks[0].task_id, 50.0)
    
    print(engine.generate_execution_checklist(plan))
