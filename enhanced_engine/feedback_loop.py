"""
执行反馈闭环 v4.2
Execution Feedback Loop — RL反馈 + 信号回收

核心功能：
1. 收集执行结果（TG推送后的互动数据）
2. 将反馈写入signal_history表
3. RL Agent读取反馈更新Q表
4. 影响下次评分

使用方式：
python feedback_loop.py --record "msg_123" --likes 50 --comments 10 --shares 5
python feedback_loop.py --process "msg_123"
python feedback_loop.py --pending
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path


# ============== 反馈数据结构 ==============

@dataclass
class ExecutionFeedback:
    """执行反馈"""
    message_id: str
    opportunity_name: str
    action: str  # template/tool/content/service
    channel: str  # telegram/wechat/etc

    # 互动数据
    likes: int = 0
    comments: int = 0
    shares: int = 0
    views: int = 0  # 阅读量

    # 计算得出的指标
    engagement_rate: float = 0.0
    total_engagement: int = 0

    # 元数据
    sent_at: str = ""
    feedback_at: str = ""
    state_snapshot: Dict = field(default_factory=dict)

    def calculate_engagement(self):
        """计算互动指标"""
        self.total_engagement = self.likes + self.comments * 2 + self.shares * 3
        self.engagement_rate = self.total_engagement / max(self.views, 1)
        return self

    def to_dict(self) -> Dict:
        return {
            "message_id": self.message_id,
            "opportunity_name": self.opportunity_name,
            "action": self.action,
            "channel": self.channel,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "views": self.views,
            "engagement_rate": self.engagement_rate,
            "total_engagement": self.total_engagement,
            "sent_at": self.sent_at,
            "feedback_at": self.feedback_at or datetime.now().isoformat(),
            "state_snapshot": self.state_snapshot,
        }


@dataclass
class PendingExecution:
    """待反馈的执行"""
    message_id: str
    opportunity_name: str
    action: str
    state: Dict  # 执行时的状态快照
    path: List[Dict] = field(default_factory=list)  # 执行的路径（边列表）
    sent_at: str = field(default_factory=lambda: datetime.now().isoformat())
    expected_feedback_hours: int = 24  # 期望24小时内反馈


# ============== 反馈循环管理器 ==============

class FeedbackLoopManager:
    """
    执行反馈循环管理器 v4.2

    1. 记录待反馈的执行
    2. 收集反馈数据
    3. 更新RL系统
    4. 影响下次评分
    """

    def __init__(self, db=None, rl_scorer=None):
        self.db = db
        self.rl_scorer = rl_scorer

        # 待反馈队列
        self.pending_file = Path("/home/admin1/aiagent/代理知识库/我的/opportunity_discovery/pending_feedback.json")
        self.pending_executions: List[PendingExecution] = []
        self.load_pending()

        # 历史反馈
        self.feedback_history: List[ExecutionFeedback] = []

    def load_pending(self):
        """加载待反馈队列"""
        if self.pending_file.exists():
            try:
                with open(self.pending_file, 'r') as f:
                    data = json.load(f)
                    self.pending_executions = [
                        PendingExecution(**item) for item in data
                    ]
            except Exception as e:
                print(f"待反馈加载失败: {e}")

    def save_pending(self):
        """保存待反馈队列"""
        try:
            with open(self.pending_file, 'w') as f:
                json.dump([
                    pe.__dict__ for pe in self.pending_executions
                ], f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"待反馈保存失败: {e}")

    def record_execution(self, message_id: str, opportunity_name: str,
                        action: str, state: Dict, path: List[Dict] = None) -> bool:
        """
        记录待反馈的执行

        Args:
            message_id: 消息ID
            opportunity_name: 机会名称
            action: 执行的动作
            state: 执行时的状态快照
            path: 执行的路径（边列表），如 [{"from_node": "A", "to_node": "B", "relation_type": "触发"}]

        Returns:
            是否成功
        """
        execution = PendingExecution(
            message_id=message_id,
            opportunity_name=opportunity_name,
            action=action,
            state=state,
            path=path or []
        )
        self.pending_executions.append(execution)
        self.save_pending()

        # 写入数据库
        if self.db:
            self._save_execution_to_db(execution)

        return True

    def _save_execution_to_db(self, execution: PendingExecution):
        """保存执行到数据库"""
        if self.db is None:
            return

        sql = """
            INSERT INTO signal_history
            (platform, entity, metric, value, timestamp, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        try:
            self.db.execute(sql, (
                "execution",
                execution.opportunity_name,
                "execution_pending",
                1.0,
                datetime.now().isoformat(),
                json.dumps({
                    "message_id": execution.message_id,
                    "action": execution.action,
                    "state": execution.state
                })
            ))
        except Exception as e:
            pass

    def receive_feedback(self, message_id: str, likes: int = 0,
                        comments: int = 0, shares: int = 0,
                        views: int = 0) -> Optional[ExecutionFeedback]:
        """
        接收反馈

        Args:
            message_id: 消息ID
            likes: 点赞数
            comments: 评论数
            shares: 转发数
            views: 阅读量

        Returns:
            ExecutionFeedback或None
        """
        # 查找对应的执行
        execution = None
        for pe in self.pending_executions:
            if pe.message_id == message_id:
                execution = pe
                break

        if execution is None:
            print(f"⚠️ 未找到message_id: {message_id}")
            # 创建一个模拟的执行记录
            execution = PendingExecution(
                message_id=message_id,
                opportunity_name="unknown",
                action="unknown",
                state={}
            )

        # 创建反馈
        feedback = ExecutionFeedback(
            message_id=message_id,
            opportunity_name=execution.opportunity_name,
            action=execution.action,
            channel="telegram",
            likes=likes,
            comments=comments,
            shares=shares,
            views=views,
            sent_at=execution.sent_at,
            state_snapshot=execution.state
        )
        feedback.calculate_engagement()
        feedback.feedback_at = datetime.now().isoformat()

        # 从待反馈队列移除
        self.pending_executions = [
            pe for pe in self.pending_executions
            if pe.message_id != message_id
        ]
        self.save_pending()

        # 保存到历史
        self.feedback_history.append(feedback)

        # 写入数据库
        if self.db:
            self._save_feedback_to_db(feedback)

        # 更新RL系统
        if self.rl_scorer and execution.state:
            self._update_rl(feedback, execution)

        # ===== 新增：写回 kg_edges.strength =====
        if execution.path:
            self._update_kg_edge_strengths(feedback, execution)

        return feedback

    def _update_kg_edge_strengths(self, feedback: ExecutionFeedback,
                                  execution: PendingExecution):
        """
        更新知识图谱边的权重

        使用指数移动平均：new_strength = old_strength + α * (reward - old_strength)
        """
        try:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from knowledge_graph import KnowledgeGraphManager
            kg = KnowledgeGraphManager(self.db)

            # 计算奖励（与RL奖励一致）
            engagement = feedback.total_engagement
            if engagement >= 100:
                reward = 1.0
            elif engagement >= 50:
                reward = 0.5
            elif engagement >= 10:
                reward = 0.1
            else:
                reward = -0.5

            # 更新衰减系数
            alpha = 0.1

            # 对路径上的每条边更新权重
            for edge in execution.path:
                old_strength = kg.get_edge_strength(
                    edge["from_node"], edge["to_node"], edge.get("relation_type", "关联")
                )

                # 如果边不存在，使用默认值0.5
                if old_strength is None:
                    old_strength = 0.5

                # 指数移动平均更新
                new_strength = old_strength + alpha * (reward - old_strength)
                new_strength = max(0.0, min(1.0, new_strength))

                kg.update_edge_strength(
                    edge["from_node"],
                    edge["to_node"],
                    edge.get("relation_type", "关联"),
                    new_strength
                )

        except Exception as e:
            print(f"⚠️ 知识图谱边权重更新失败: {e}")

    def _save_feedback_to_db(self, feedback: ExecutionFeedback):
        """保存反馈到数据库"""
        if self.db is None:
            return

        sql = """
            INSERT INTO signal_history
            (platform, entity, metric, value, timestamp, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        try:
            self.db.execute(sql, (
                "feedback",
                feedback.opportunity_name,
                "engagement",
                float(feedback.total_engagement),
                datetime.now().isoformat(),
                json.dumps({
                    "message_id": feedback.message_id,
                    "action": feedback.action,
                    "likes": feedback.likes,
                    "comments": feedback.comments,
                    "shares": feedback.shares,
                    "views": feedback.views,
                    "engagement_rate": feedback.engagement_rate
                })
            ))
        except Exception as e:
            pass

    def _update_rl(self, feedback: ExecutionFeedback, execution: PendingExecution):
        """更新RL系统"""
        if self.rl_scorer is None:
            return

        # 重建状态
        state_dict = execution.state
        # 延迟导入避免循环依赖
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from enhanced_engine.rl_scorer import StateSpace
        state = StateSpace(
            signal_strength=state_dict.get("signal_strength", 0.5),
            velocity=state_dict.get("velocity", 0.5),
            cross_platform=state_dict.get("cross_platform", 0.5),
            market_timing=state_dict.get("market_timing", 0.5)
        )

        # 处理奖励
        result = self.rl_scorer.process_reward(
            message_id=feedback.message_id,
            engagement=feedback.total_engagement,
            state=state,
            action=feedback.action
        )

        return result

    def get_pending(self) -> List[PendingExecution]:
        """获取待反馈列表"""
        # 检查超时
        now = datetime.now()
        timeout_hours = 48

        active = []
        for pe in self.pending_executions:
            sent_time = datetime.fromisoformat(pe.sent_at)
            if (now - sent_time).total_seconds() > timeout_hours * 3600:
                # 超过48小时未反馈，标记为超时
                continue
            active.append(pe)

        return active

    def get_feedback_summary(self, days: int = 7) -> Dict:
        """获取反馈摘要"""
        now = datetime.now()
        cutoff = now - timedelta(days=days)

        recent = [
            f for f in self.feedback_history
            if datetime.fromisoformat(f.feedback_at) > cutoff
        ]

        if not recent:
            return {
                "total_feedbacks": 0,
                "avg_engagement": 0,
                "top_action": None,
                "action_stats": {}
            }

        # 统计
        total = len(recent)
        avg_engagement = sum(f.total_engagement for f in recent) / total

        action_stats = {}
        for f in recent:
            if f.action not in action_stats:
                action_stats[f.action] = {"count": 0, "total_engagement": 0}
            action_stats[f.action]["count"] += 1
            action_stats[f.action]["total_engagement"] += f.total_engagement

        # 找出最佳动作
        top_action = max(action_stats, key=lambda x: action_stats[x]["total_engagement"])

        return {
            "total_feedbacks": total,
            "avg_engagement": round(avg_engagement, 2),
            "top_action": top_action,
            "action_stats": action_stats,
            "pending_count": len(self.get_pending())
        }

    def export_feedback_history(self, output_path: str = None) -> List[Dict]:
        """导出反馈历史"""
        data = [f.to_dict() for f in self.feedback_history]

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        return data


# ============== 主程序 ==============

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="执行反馈闭环 v4.2")
    parser.add_argument("--record", nargs='+',
                       help="记录执行: msg_id opportunity action state_json [path_json]")
    parser.add_argument("--feedback", nargs=5, metavar=("MSG_ID", "LIKES", "COMMENTS", "SHARES", "VIEWS"),
                       help="接收反馈: msg_id likes comments shares views")
    parser.add_argument("--pending", action="store_true", help="查看待反馈")
    parser.add_argument("--summary", action="store_true", help="反馈摘要")
    parser.add_argument("--demo", action="store_true", help="演示模式")

    args = parser.parse_args()

    print("🔄 执行反馈闭环 v4.2\n")

    # 初始化组件
    db = None
    rl = None
    try:
        from knowledge_graph import DBConnection
        from enhanced_engine.rl_scorer import RLScorerManager
        db = DBConnection.get_instance()
        db.connect()
        rl = RLScorerManager(db)
    except Exception as e:
        print(f"⚠️ 组件初始化: {e}")

    manager = FeedbackLoopManager(db, rl)

    if args.record:
        msg_id, opp, action, state_json = args.record[:4]
        state = json.loads(state_json)
        path = None
        if len(args.record) > 4:
            path = json.loads(args.record[4])
        success = manager.record_execution(msg_id, opp, action, state, path)
        print(f"{'✓' if success else '✗'} 已记录执行: {msg_id}")
        print(f"  机会: {opp}")
        print(f"  动作: {action}")
        if path:
            print(f"  路径: {len(path)} 条边")

    elif args.feedback:
        msg_id, likes, comments, shares, views = args.feedback
        feedback = manager.receive_feedback(
            msg_id, int(likes), int(comments), int(shares), int(views)
        )
        if feedback:
            print(f"✓ 反馈已接收: {msg_id}")
            print(f"  总互动: {feedback.total_engagement}")
            print(f"  互动率: {feedback.engagement_rate:.4%}")
        else:
            print(f"⚠️ 反馈处理失败")

        # 如果RL可用，显示学习结果
        if feedback and rl:
            state = feedback.state_snapshot
            print(f"\n🧠 RL学习:")
            print(f"  奖励: 基于{feedback.total_engagement}互动量")
            print(f"  建议: 查看RL统计获取详情")

    elif args.pending:
        pending = manager.get_pending()
        print(f"📋 待反馈 ({len(pending)}条):\n")
        for pe in pending[:10]:
            print(f"  {pe.message_id}: {pe.opportunity_name} ({pe.action})")
            print(f"    发送于: {pe.sent_at}")

    elif args.summary:
        summary = manager.get_feedback_summary()
        print("📊 反馈摘要 (最近7天):\n")
        print(f"  总反馈数: {summary['total_feedbacks']}")
        print(f"  平均互动: {summary['avg_engagement']}")
        print(f"  最佳动作: {summary['top_action']}")
        print(f"  待反馈: {summary['pending_count']}")
        if summary['action_stats']:
            print(f"\n  动作统计:")
            for action, stats in summary['action_stats'].items():
                avg = stats['total_engagement'] / max(stats['count'], 1)
                print(f"    {action}: {stats['count']}次, 总互动{stats['total_engagement']}, 均值{avg:.1f}")

    elif args.demo:
        print("🎯 反馈闭环演示\n")

        # 记录执行
        state = {"signal_strength": 0.8, "velocity": 0.6, "cross_platform": 0.5, "market_timing": 0.7}
        msg_id = f"msg_{uuid.uuid4().hex[:8]}"
        manager.record_execution(msg_id, "OpenClaw GPU供应商", "tool", state)
        print(f"1. 记录执行: {msg_id}")

        # 模拟反馈
        print(f"\n2. 模拟反馈...")
        feedback = manager.receive_feedback(msg_id, likes=85, comments=12, shares=5, views=500)
        if feedback:
            print(f"   总互动: {feedback.total_engagement}")
            print(f"   互动率: {feedback.engagement_rate:.4%}")

        # 显示摘要
        print(f"\n3. 反馈摘要:")
        summary = manager.get_feedback_summary()
        print(f"   总反馈: {summary['total_feedbacks']}")
        print(f"   最佳动作: {summary['top_action']}")

        print("\n✅ 演示完成")

    else:
        print(__doc__)