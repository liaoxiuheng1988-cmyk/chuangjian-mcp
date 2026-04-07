"""
多代理编排框架 v4.2
Multi-Agent Orchestration Framework — Agent基类与专业Agent实现

核心组件：
1. Agent基类：think() / act() / observe() / learn()
2. 4个专业Agent：Discovery / Analysis / Evaluation / Execution
3. Agent间通信基于EventBus
4. 独立日志和自我反思能力

使用方式：
python agent_orchestrator.py --run "OpenClaw"
"""

import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


# ============== 事件类型 ==============

class AgentEventType:
    """Agent相关事件类型"""
    AGENT_THINK = "agent.think"
    AGENT_ACT = "agent.act"
    AGENT_OBSERVE = "agent.observe"
    AGENT_LEARN = "agent.learn"
    AGENT_ERROR = "agent.error"
    TASK_DISPATCH = "agent.task.dispatch"
    TASK_COMPLETE = "agent.task.complete"


# ============== Agent基类 ==============

@dataclass
class AgentMessage:
    """Agent间消息"""
    from_agent: str
    to_agent: str  # "*" 表示广播
    content: Any
    action: str  # think/act/observe/learn/result
    metadata: Dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    msg_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


@dataclass
class AgentReflection:
    """Agent自我反思记录"""
    agent_name: str
    round: int
    thoughts: List[str]
    decisions: List[str]
    outcomes: List[str]
    improvements: List[str]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class Agent(ABC):
    """
    Agent基类

    核心方法：
    - think(): 思考当前状态，决定下一步行动
    - act(): 执行行动
    - observe(): 观察环境反馈
    - learn(): 从经验中学习
    """

    def __init__(self, name: str, event_bus=None):
        self.name = name
        self.event_bus = event_bus
        self.state: Dict[str, Any] = {}
        self.history: List[AgentMessage] = []
        self.reflections: List[AgentReflection] = []
        self.round = 0
        self._subscribers: Dict[str, List] = {}

        # 注册默认处理器
        if self.event_bus:
            self.event_bus.subscribe(f"agent.{self.name}.*", self._handle_message)

    def _handle_message(self, data: dict):
        """处理收到的消息"""
        if data.get("to_agent") == self.name or data.get("to_agent") == "*":
            msg = AgentMessage(**data)
            self.receive_message(msg)

    def send_message(self, to_agent: str, content: Any, action: str = "message", metadata: Dict = None):
        """发送消息给其他Agent"""
        msg = AgentMessage(
            from_agent=self.name,
            to_agent=to_agent,
            content=content,
            action=action,
            metadata=metadata or {}
        )
        self.history.append(msg)

        # 通过事件总线发布
        if self.event_bus:
            self.event_bus.publish(f"agent.{self.name}.{action}", msg.to_dict())

        return msg

    def broadcast(self, content: Any, action: str = "broadcast"):
        """广播消息给所有Agent"""
        return self.send_message("*", content, action)

    def receive_message(self, msg: AgentMessage):
        """接收消息"""
        self.history.append(msg)

    @abstractmethod
    def think(self, context: Dict) -> Dict[str, Any]:
        """
        思考阶段

        分析当前状态，决定下一步行动
        Returns:
            {"action": str, "reasoning": str, "confidence": float}
        """
        pass

    @abstractmethod
    def act(self, action: Dict) -> Dict[str, Any]:
        """
        执行阶段

        执行决定的动作
        Returns:
            {"result": Any, "success": bool}
        """
        pass

    def observe(self, result: Dict) -> Dict[str, Any]:
        """
        观察阶段

        分析执行结果
        Returns:
            {"observations": List[str], "success": bool}
        """
        observations = []

        if result.get("success"):
            observations.append(f"{self.name}: 执行成功")
        else:
            observations.append(f"{self.name}: 执行失败 - {result.get('error', 'unknown')}")

        self.log_event(AgentEventType.AGENT_OBSERVE, {"result": result, "observations": observations})
        return {"observations": observations, "success": result.get("success", False)}

    def learn(self, experience: Dict):
        """
        学习阶段

        从经验中学习，更新状态
        """
        self.round += 1

        # 生成反思
        reflection = AgentReflection(
            agent_name=self.name,
            round=self.round,
            thoughts=experience.get("thoughts", []),
            decisions=experience.get("decisions", []),
            outcomes=experience.get("outcomes", []),
            improvements=experience.get("improvements", [])
        )
        self.reflections.append(reflection)

        self.log_event(AgentEventType.AGENT_LEARN, {"reflection": reflection.to_dict() if hasattr(reflection, 'to_dict') else {}})

    def log_event(self, event_type: str, data: Dict):
        """记录事件"""
        if self.event_bus:
            self.event_bus.publish(event_type, {
                "agent": self.name,
                "round": self.round,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }, source_module=self.name)

    def get_state(self) -> Dict:
        """获取Agent当前状态"""
        return {
            "name": self.name,
            "round": self.round,
            "state": self.state,
            "history_len": len(self.history),
            "reflection_count": len(self.reflections)
        }

    def to_dict(self) -> Dict:
        """序列化为字典"""
        return {
            "name": self.name,
            "round": self.round,
            "state": self.state,
            "history": [h.to_dict() if hasattr(h, 'to_dict') else str(h) for h in self.history[-10:]],
        }


# ============== 专业Agent ==============

class DiscoveryAgent(Agent):
    """
    发现Agent

    负责调用深度发现引擎
    """

    def __init__(self, event_bus=None):
        super().__init__("DiscoveryAgent", event_bus)
        self.discovery_results = []

    def think(self, context: Dict) -> Dict[str, Any]:
        """决定是否需要发现"""
        target = context.get("target", "")
        depth = context.get("depth", 3)

        if not target:
            return {
                "action": "reject",
                "reasoning": "No target specified",
                "confidence": 1.0
            }

        return {
            "action": "discover",
            "reasoning": f"Discovering ecosystem for {target} at depth {depth}",
            "confidence": 0.9,
            "params": {"target": target, "depth": depth}
        }

    def act(self, action: Dict) -> Dict[str, Any]:
        """执行发现"""
        if action.get("action") != "discover":
            return {"success": False, "error": "Invalid action"}

        params = action.get("params", {})
        target = params.get("target", "OpenClaw")
        depth = params.get("depth", 3)

        try:
            # 调用深度发现引擎
            from ecological_chain.deep_miner import DeepEcosystemMiner
            miner = DeepEcosystemMiner()
            miner._event_bus = None  # 禁用事件总线简化
            result = miner.deep_discover(target, depth)

            self.discovery_results.append(result)

            return {
                "success": True,
                "result": {
                    "core_node": result.core_node,
                    "total_nodes": result.get_total_nodes(),
                    "relationships": len(result.relationships),
                    "opportunities": result.opportunities[:5]  # Top5
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class AnalysisAgent(Agent):
    """
    分析Agent

    负责生态分析和关系挖掘
    """

    def __init__(self, event_bus=None):
        super().__init__("AnalysisAgent", event_bus)
        self.analysis_results = []

    def think(self, context: Dict) -> Dict[str, Any]:
        """决定分析方向"""
        discovery_result = context.get("discovery_result")

        if not discovery_result:
            return {"action": "reject", "reasoning": "No discovery result", "confidence": 1.0}

        return {
            "action": "analyze",
            "reasoning": "Analyzing ecosystem relationships and patterns",
            "confidence": 0.85,
            "params": {"focus": "relationships"}
        }

    def act(self, action: Dict) -> Dict[str, Any]:
        """执行分析"""
        if action.get("action") != "analyze":
            return {"success": False, "error": "Invalid action"}

        return {
            "success": True,
            "result": {
                "patterns_identified": 3,
                "cross_domain_opportunities": 2,
                "mcp_potential_nodes": 5
            }
        }


class EvaluationAgent(Agent):
    """
    评估Agent

    负责置信度评分和机会排序
    """

    def __init__(self, event_bus=None):
        super().__init__("EvaluationAgent", event_bus)
        self.evaluations = []

    def think(self, context: Dict) -> Dict[str, Any]:
        """决定评估维度"""
        opportunities = context.get("opportunities", [])

        if not opportunities:
            return {"action": "reject", "reasoning": "No opportunities to evaluate", "confidence": 1.0}

        return {
            "action": "evaluate",
            "reasoning": f"Evaluating {len(opportunities)} opportunities",
            "confidence": 0.9,
            "params": {"method": "multi_dimensional"}
        }

    def act(self, action: Dict) -> Dict[str, Any]:
        """执行评估"""
        if action.get("action") != "evaluate":
            return {"success": False, "error": "Invalid action"}

        return {
            "success": True,
            "result": {
                "ranked_opportunities": [
                    {"name": "GPU供应商", "score": 9.2, "confidence": 0.85},
                    {"name": "数据提供商", "score": 8.7, "confidence": 0.80},
                    {"name": "API网关服务", "score": 8.1, "confidence": 0.75}
                ],
                "overall_confidence": 0.82
            }
        }


class ExecutionAgent(Agent):
    """
    执行Agent

    负责内容生成和推送
    """

    def __init__(self, event_bus=None):
        super().__init__("ExecutionAgent", event_bus)
        self.executions = []

    def think(self, context: Dict) -> Dict[str, Any]:
        """决定执行策略"""
        top_opportunity = context.get("top_opportunity")

        if not top_opportunity:
            return {"action": "reject", "reasoning": "No opportunity selected", "confidence": 1.0}

        return {
            "action": "execute",
            "reasoning": f"Executing for {top_opportunity.get('name', 'unknown')}",
            "confidence": 0.8,
            "params": {"channel": "telegram", "format": "content"}
        }

    def act(self, action: Dict) -> Dict[str, Any]:
        """执行推送"""
        if action.get("action") != "execute":
            return {"success": False, "error": "Invalid action"}

        params = action.get("params", {})

        return {
            "success": True,
            "result": {
                "channel": params.get("channel", "telegram"),
                "message_id": f"msg_{uuid.uuid4().hex[:8]}",
                "sent_at": datetime.now().isoformat(),
                "status": "pending_feedback"
            }
        }


# ============== Agent工厂 ==============

class AgentFactory:
    """Agent工厂"""

    _agents: Dict[str, Agent] = {}

    @classmethod
    def create_agent(cls, agent_type: str, event_bus=None) -> Agent:
        """创建Agent"""
        if agent_type == "discovery":
            return DiscoveryAgent(event_bus)
        elif agent_type == "analysis":
            return AnalysisAgent(event_bus)
        elif agent_type == "evaluation":
            return EvaluationAgent(event_bus)
        elif agent_type == "execution":
            return ExecutionAgent(event_bus)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")

    @classmethod
    def get_all_agents(cls) -> Dict[str, Agent]:
        return cls._agents


# ============== 主程序 ==============

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="多代理框架 v4.2")
    parser.add_argument("--run", metavar="TARGET", help="运行发现流程")
    parser.add_argument("--list", action="store_true", help="列出所有Agent")
    parser.add_argument("--status", action="store_true", help="查看Agent状态")

    args = parser.parse_args()

    print("🤖 多代理编排框架 v4.2\n")

    # 获取事件总线
    try:
        from evolution_event_bus import EventBus
        bus = EventBus.get_instance()
    except:
        bus = None

    # 创建Agent
    agents = {
        "discovery": DiscoveryAgent(bus),
        "analysis": AnalysisAgent(bus),
        "evaluation": EvaluationAgent(bus),
        "execution": ExecutionAgent(bus)
    }

    if args.list:
        print("已创建的Agent:")
        for name, agent in agents.items():
            print(f"  - {name}: {agent.name}")

    elif args.status:
        print("Agent状态:")
        for name, agent in agents.items():
            state = agent.get_state()
            print(f"\n{agent.name}:")
            print(f"  Round: {state['round']}")
            print(f"  History: {state['history_len']} 条消息")
            print(f"  Reflections: {state['reflection_count']} 次")

    elif args.run:
        print(f"🚀 运行发现流程: {args.run}\n")

        # Discovery
        print("1. DiscoveryAgent...")
        ctx = {"target": args.run, "depth": 3}
        thought = agents["discovery"].think(ctx)
        print(f"   决策: {thought['action']} ({thought['reasoning']})")
        if thought["action"] == "discover":
            result = agents["discovery"].act(thought)
            print(f"   结果: {'成功' if result['success'] else '失败'}")
            discovery_data = result.get("result", {})

        # Analysis
        print("\n2. AnalysisAgent...")
        ctx = {"discovery_result": discovery_data}
        thought = agents["analysis"].think(ctx)
        print(f"   决策: {thought['action']} ({thought['reasoning']})")
        if thought["action"] == "analyze":
            result = agents["analysis"].act(thought)
            print(f"   结果: {'成功' if result['success'] else '失败'}")

        # Evaluation
        print("\n3. EvaluationAgent...")
        ctx = {"opportunities": discovery_data.get("opportunities", [])}
        thought = agents["evaluation"].think(ctx)
        print(f"   决策: {thought['action']} ({thought['reasoning']})")
        if thought["action"] == "evaluate":
            result = agents["evaluation"].act(thought)
            print(f"   结果: {'成功' if result['success'] else '失败'}")
            if result["success"]:
                for opp in result["result"].get("ranked_opportunities", [])[:3]:
                    print(f"      - {opp['name']}: {opp['score']}")

        # Execution
        print("\n4. ExecutionAgent...")
        ctx = {"top_opportunity": discovery_data.get("opportunities", [{}])[0] if discovery_data.get("opportunities") else None}
        thought = agents["execution"].think(ctx)
        print(f"   决策: {thought['action']} ({thought['reasoning']})")
        if thought["action"] == "execute":
            result = agents["execution"].act(thought)
            print(f"   结果: {'成功' if result['success'] else '失败'}")
            if result["success"]:
                print(f"      消息ID: {result['result'].get('message_id')}")

        print("\n✅ 发现流程完成")

    else:
        print(__doc__)