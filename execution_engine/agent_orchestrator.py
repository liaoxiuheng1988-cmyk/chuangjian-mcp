"""
Agent编排器 v4.2
Agent Orchestrator — 多Agent协调 + RL评分 + 反馈闭环

整合所有组件：
1. 多Agent框架 (Discovery/Analysis/Evaluation/Execution)
2. RL评分系统 (Q-Learning)
3. 执行反馈闭环

使用方式：
python agent_orchestrator.py --run "OpenClaw"
python agent_orchestrator.py --feedback "msg_123" --likes 50 --comments 10
"""

import json
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============== 编排器 ==============

class AgentOrchestrator:
    """
    Agent编排器 v4.2

    协调多Agent、RL评分和反馈闭环
    """

    def __init__(self, event_bus=None, db=None):
        self.event_bus = event_bus
        self.db = db

        # Agent
        from execution_engine.agent_base import (
            DiscoveryAgent, AnalysisAgent, EvaluationAgent, ExecutionAgent
        )
        self.agents = {
            "discovery": DiscoveryAgent(event_bus),
            "analysis": AnalysisAgent(event_bus),
            "evaluation": EvaluationAgent(event_bus),
            "execution": ExecutionAgent(event_bus)
        }

        # RL评分器
        try:
            from enhanced_engine.rl_scorer import RLScorerManager, StateSpace
            self.rl_scorer = RLScorerManager(db)
            self.StateSpace = StateSpace
        except Exception as e:
            print(f"RL评分器初始化失败: {e}")
            self.rl_scorer = None
            self.StateSpace = None

        # 反馈管理器
        try:
            from enhanced_engine.feedback_loop import FeedbackLoopManager
            self.feedback_manager = FeedbackLoopManager(db, self.rl_scorer)
        except Exception as e:
            print(f"反馈管理器初始化失败: {e}")
            self.feedback_manager = None

        # 执行上下文
        self.context: Dict[str, Any] = {}
        self.execution_history: List[Dict] = []

    def run_full_pipeline(self, target: str, depth: int = 3) -> Dict:
        """
        运行完整Pipeline

        Args:
            target: 目标节点
            depth: 发现深度

        Returns:
            执行结果
        """
        print(f"\n🚀 开始完整Pipeline: {target}\n")
        print("=" * 60)

        result = {
            "target": target,
            "start_time": datetime.now().isoformat(),
            "stages": {}
        }

        # Stage 1: Discovery
        print("\n[Stage 1/4] DiscoveryAgent")
        print("-" * 40)
        discovery_result = self._run_discovery(target, depth)
        result["stages"]["discovery"] = discovery_result

        # Stage 2: Analysis
        print("\n[Stage 2/4] AnalysisAgent")
        print("-" * 40)
        analysis_result = self._run_analysis(discovery_result)
        result["stages"]["analysis"] = analysis_result

        # Stage 3: Evaluation + RL Scoring
        print("\n[Stage 3/4] EvaluationAgent + RL Scoring")
        print("-" * 40)
        eval_result = self._run_evaluation(discovery_result, analysis_result)
        result["stages"]["evaluation"] = eval_result

        # Stage 4: Execution
        print("\n[Stage 4/4] ExecutionAgent")
        print("-" * 40)
        exec_result = self._run_execution(eval_result)
        result["stages"]["execution"] = exec_result

        # 完成
        result["end_time"] = datetime.now().isoformat()
        result["success"] = True

        self.execution_history.append(result)
        self._save_history()

        print("\n" + "=" * 60)
        print("✅ Pipeline完成")
        print("=" * 60)

        return result

    def _run_discovery(self, target: str, depth: int) -> Dict:
        """运行发现阶段"""
        agent = self.agents["discovery"]

        ctx = {"target": target, "depth": depth}
        thought = agent.think(ctx)

        print(f"  思考: {thought['reasoning']}")
        print(f"  置信度: {thought['confidence']:.0%}")

        if thought["action"] == "reject":
            return {"success": False, "reason": thought.get("reasoning")}

        action_result = agent.act(thought)

        if action_result["success"]:
            data = action_result["result"]
            print(f"  ✓ 发现完成")
            print(f"    节点数: {data.get('total_nodes', 0)}")
            print(f"    关系数: {data.get('relationships', 0)}")

            # 保存到上下文
            self.context["discovery_result"] = data
            self.context["opportunities"] = data.get("opportunities", [])

            # 观察
            agent.observe(action_result)
        else:
            print(f"  ✗ 发现失败: {action_result.get('error')}")

        return action_result

    def _run_analysis(self, discovery_result: Dict) -> Dict:
        """运行分析阶段"""
        agent = self.agents["analysis"]

        ctx = {"discovery_result": discovery_result.get("result", {})}
        thought = agent.think(ctx)

        print(f"  思考: {thought['reasoning']}")

        if thought["action"] == "reject":
            return {"success": False, "reason": thought.get("reasoning")}

        action_result = agent.act(thought)

        if action_result["success"]:
            data = action_result["result"]
            print(f"  ✓ 分析完成")
            print(f"    识别模式: {data.get('patterns_identified', 0)}")
            print(f"    跨域机会: {data.get('cross_domain_opportunities', 0)}")

            self.context["analysis_result"] = data
            agent.observe(action_result)
        else:
            print(f"  ✗ 分析失败")

        return action_result

    def _run_evaluation(self, discovery_result: Dict, analysis_result: Dict) -> Dict:
        """运行评估阶段 + RL评分"""
        agent = self.agents["evaluation"]

        opportunities = self.context.get("opportunities", [])
        ctx = {"opportunities": opportunities}
        thought = agent.think(ctx)

        print(f"  思考: {thought['reasoning']}")

        if thought["action"] == "reject":
            return {"success": False, "reason": thought.get("reasoning")}

        action_result = agent.act(thought)

        if action_result["success"]:
            data = action_result["result"]
            ranked = data.get("ranked_opportunities", [])
            print(f"  ✓ 评估完成")
            print(f"    评估机会: {len(ranked)}")

            # RL评分
            if self.rl_scorer and ranked:
                print(f"\n  🧠 RL评分:")
                # 使用Top1机会的状态进行RL评分
                top_opp = ranked[0]
                state = self.StateSpace(
                    signal_strength=0.7,  # 从机会数据中提取
                    velocity=0.6,
                    cross_platform=0.5,
                    market_timing=0.7
                )
                rl_result = self.rl_scorer.score_opportunity(state)

                print(f"    推荐动作: {rl_result['recommended_action']}")
                print(f"    动作描述: {rl_result['action_description']}")
                print(f"    置信度: {rl_result['confidence']:.0%}")

                data["rl_recommendation"] = rl_result
                self.context["rl_recommendation"] = rl_result

            # 保存到上下文
            self.context["evaluation_result"] = data
            agent.observe(action_result)
        else:
            print(f"  ✗ 评估失败")

        return action_result

    def _run_execution(self, eval_result: Dict) -> Dict:
        """运行执行阶段"""
        agent = self.agents["execution"]

        ranked = eval_result.get("result", {}).get("ranked_opportunities", [])
        top_opp = ranked[0] if ranked else None

        ctx = {"top_opportunity": top_opp}
        thought = agent.think(ctx)

        print(f"  思考: {thought['reasoning']}")

        if thought["action"] == "reject":
            return {"success": False, "reason": thought.get("reasoning")}

        action_result = agent.act(thought)

        if action_result["success"]:
            data = action_result["result"]
            print(f"  ✓ 执行完成")
            print(f"    渠道: {data.get('channel')}")
            print(f"    消息ID: {data.get('message_id')}")

            # 记录待反馈执行
            if self.feedback_manager and top_opp:
                rl_rec = self.context.get("rl_recommendation", {})
                state = {
                    "signal_strength": 0.7,
                    "velocity": 0.6,
                    "cross_platform": 0.5,
                    "market_timing": 0.7,
                    "opportunity_score": top_opp.get("score", 0)
                }
                self.feedback_manager.record_execution(
                    message_id=data.get("message_id"),
                    opportunity_name=top_opp.get("name"),
                    action=rl_rec.get("recommended_action", "content"),
                    state=state
                )
                print(f"    ✓ 已记录待反馈")

            self.context["execution_result"] = data
            agent.observe(action_result)
        else:
            print(f"  ✗ 执行失败")

        return action_result

    def process_feedback(self, message_id: str, likes: int = 0,
                       comments: int = 0, shares: int = 0,
                       views: int = 0) -> Dict:
        """处理反馈"""
        if not self.feedback_manager:
            return {"success": False, "error": "Feedback manager not available"}

        feedback = self.feedback_manager.receive_feedback(
            message_id, likes, comments, shares, views
        )

        if feedback:
            print(f"\n📥 反馈已处理:")
            print(f"  消息ID: {feedback.message_id}")
            print(f"  总互动: {feedback.total_engagement}")
            print(f"  互动率: {feedback.engagement_rate:.4%}")

            return {"success": True, "feedback": feedback.to_dict()}
        else:
            return {"success": False, "error": "Feedback processing failed"}

    def get_status(self) -> Dict:
        """获取系统状态"""
        status = {
            "agents": {},
            "rl_available": self.rl_scorer is not None,
            "feedback_available": self.feedback_manager is not None,
            "pending_feedbacks": 0
        }

        for name, agent in self.agents.items():
            state = agent.get_state()
            status["agents"][name] = {
                "round": state["round"],
                "history_len": state["history_len"],
                "reflections": state["reflection_count"]
            }

        if self.feedback_manager:
            status["pending_feedbacks"] = len(self.feedback_manager.get_pending())

        if self.rl_scorer:
            rl_stats = self.rl_scorer.get_stats()
            status["rl_stats"] = rl_stats

        return status

    def _save_history(self):
        """保存执行历史"""
        history_file = Path("/home/admin1/aiagent/代理知识库/我的/opportunity_discovery/pipeline_history.json")
        try:
            with open(history_file, 'w') as f:
                json.dump(self.execution_history[-100:], f, indent=2, default=str)
        except Exception as e:
            print(f"历史保存失败: {e}")


# ============== 主程序 ==============

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Agent编排器 v4.2")
    parser.add_argument("--run", metavar="TARGET", help="运行完整Pipeline")
    parser.add_argument("--depth", type=int, default=3, help="发现深度")
    parser.add_argument("--feedback", nargs=5, metavar=("MSG_ID", "LIKES", "COMMENTS", "SHARES", "VIEWS"),
                       help="处理反馈")
    parser.add_argument("--status", action="store_true", help="查看状态")
    parser.add_argument("--demo", action="store_true", help="演示模式")

    args = parser.parse_args()

    print("""
╔══════════════════════════════════════════════════════════════╗
║              Agent编排器 v4.2                              ║
║        多Agent + RL评分 + 执行反馈闭环                      ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # 初始化
    event_bus = None
    db = None
    try:
        from evolution_event_bus import EventBus
        event_bus = EventBus.get_instance()
    except:
        pass

    try:
        from knowledge_graph import DBConnection
        db = DBConnection.get_instance()
        db.connect()
    except:
        pass

    orchestrator = AgentOrchestrator(event_bus, db)

    if args.run:
        result = orchestrator.run_full_pipeline(args.run, args.depth)
        print(f"\n📊 Pipeline结果:")
        print(f"  目标: {result['target']}")
        print(f"  成功: {result.get('success', False)}")
        print(f"  耗时: {result.get('end_time', '')}")

    elif args.feedback:
        msg_id, likes, comments, shares, views = args.feedback
        result = orchestrator.process_feedback(
            msg_id, int(likes), int(comments), int(shares), int(views)
        )
        print(f"\n{'✓' if result['success'] else '✗'} 反馈处理{'成功' if result['success'] else '失败'}")

    elif args.status:
        print("\n📊 系统状态:\n")
        status = orchestrator.get_status()

        print("Agent状态:")
        for name, agent_status in status["agents"].items():
            print(f"  {name}:")
            print(f"    Round: {agent_status['round']}")
            print(f"    History: {agent_status['history_len']} 条")
            print(f"    Reflections: {agent_status['reflections']} 次")

        print(f"\nRL评分: {'✓ 可用' if status['rl_available'] else '✗ 不可用'}")
        if status.get("rl_stats"):
            stats = status["rl_stats"]
            print(f"  状态数: {stats['total_states']}")
            print(f"  Q值更新: {stats['total_q_updates']}")

        print(f"\n反馈闭环: {'✓ 可用' if status['feedback_available'] else '✗ 不可用'}")
        print(f"  待反馈: {status['pending_feedbacks']}")

    elif args.demo:
        print("🎯 演示模式\n")

        # 演示Pipeline
        result = orchestrator.run_full_pipeline("OpenClaw", depth=2)

        # 演示反馈
        print("\n\n🔄 模拟反馈处理")
        exec_result = result.get("stages", {}).get("execution", {}).get("result", {})
        msg_id = exec_result.get("message_id")
        if msg_id:
            orchestrator.process_feedback(msg_id, likes=75, comments=8, shares=3, views=300)

        print("\n✅ 演示完成")

    else:
        parser.print_help()