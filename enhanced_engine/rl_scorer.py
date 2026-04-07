"""
强化学习评分系统 v4.2
Reinforcement Learning Scorer — Q-Learning实现

核心功能：
1. Q-Learning简单版本
2. 状态空间：signal_strength / velocity / cross_platform / market_timing
3. 动作空间：变现路径推荐
4. 奖励函数：执行结果反馈
5. Q表存储在PostgreSQL

使用方式：
python rl_scorer.py --score "OpenClaw" --state 0.8,0.6,0.5,0.7
python rl_scorer.py --reward "msg_123" --engagement 150
python rl_scorer.py --stats
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path

# ============== 状态空间定义 ==============

@dataclass
class StateSpace:
    """
    状态空间

    四维状态：
    - signal_strength: 信号强度 (0-1)
    - velocity: 变化速度 (0-1)
    - cross_platform: 跨平台程度 (0-1)
    - market_timing: 市场时机 (0-1)
    """
    signal_strength: float = 0.5
    velocity: float = 0.5
    cross_platform: float = 0.5
    market_timing: float = 0.5

    def to_tuple(self) -> Tuple[float, float, float, float]:
        return (self.signal_strength, self.velocity, self.cross_platform, self.market_timing)

    def to_discrete(self, bins: int = 5) -> str:
        """离散化为字符串键"""
        def discretize(value: float) -> int:
            return min(int(value * bins), bins - 1)
        return f"{discretize(self.signal_strength)}-{discretize(self.velocity)}-{discretize(self.cross_platform)}-{discretize(self.market_timing)}"

    def to_dict(self) -> Dict:
        return {
            "signal_strength": self.signal_strength,
            "velocity": self.velocity,
            "cross_platform": self.cross_platform,
            "market_timing": self.market_timing,
        }


# ============== 动作空间定义 ==============

class ActionSpace:
    """动作空间 - 变现路径"""
    TEMPLATE = "template"      # 卖模板
    TOOL = "tool"              # 做工具
    CONTENT = "content"        # 做内容
    SERVICE = "service"         # 做服务

    ALL_ACTIONS = [TEMPLATE, TOOL, CONTENT, SERVICE]

    @classmethod
    def get_action_index(cls, action: str) -> int:
        return cls.ALL_ACTIONS.index(action)

    @classmethod
    def get_action_name(cls, index: int) -> str:
        return cls.ALL_ACTIONS[index]

    @classmethod
    def get_description(cls, action: str) -> str:
        descriptions = {
            cls.TEMPLATE: "卖模板（Notion/Canva等）",
            cls.TOOL: "做工具（API/SDK/插件）",
            cls.CONTENT: "做内容（教程/视频/文章）",
            cls.SERVICE: "做服务（咨询/培训/代运营）"
        }
        return descriptions.get(action, action)


# ============== Q-Learning核心 ==============

@dataclass
class QTable:
    """Q表"""
    states: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def get_q(self, state_key: str, action: str) -> float:
        """获取Q值"""
        if state_key not in self.states:
            self.states[state_key] = {a: 0.0 for a in ActionSpace.ALL_ACTIONS}
        return self.states[state_key].get(action, 0.0)

    def set_q(self, state_key: str, action: str, value: float):
        """设置Q值"""
        if state_key not in self.states:
            self.states[state_key] = {a: 0.0 for a in ActionSpace.ALL_ACTIONS}
        self.states[state_key][action] = value

    def get_best_action(self, state_key: str, exploration: float = 0.1) -> str:
        """
        获取最佳动作（ε-greedy）

        Args:
            state_key: 状态键
            exploration: 探索概率

        Returns:
            最佳动作
        """
        import random
        if random.random() < exploration:
            # 探索：随机选择
            return random.choice(ActionSpace.ALL_ACTIONS)

        # 利用：选择Q值最大的动作
        if state_key not in self.states:
            return ActionSpace.TOOL  # 默认返回工具

        q_values = self.states[state_key]
        return max(q_values, key=q_values.get)


@dataclass
class LearningRecord:
    """学习记录"""
    record_id: str
    state: StateSpace
    action: str
    reward: float
    next_state: StateSpace
    q_value_before: float
    q_value_after: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class QLearningAgent:
    """
    Q-Learning Agent

    实现简单的Q-Learning算法
    """

    def __init__(self, learning_rate: float = 0.1, discount_factor: float = 0.9):
        self.learning_rate = learning_rate  # α
        self.discount_factor = discount_factor  # γ
        self.q_table = QTable()
        self.learning_history: List[LearningRecord] = []

        # 探索参数
        self.exploration_rate = 0.2
        self.min_exploration = 0.05
        self.exploration_decay = 0.99

    def choose_action(self, state: StateSpace, exploration: float = None) -> str:
        """选择动作"""
        exploration = exploration or self.exploration_rate
        state_key = state.to_discrete()
        return self.q_table.get_best_action(state_key, exploration)

    def learn(self, state: StateSpace, action: str, reward: float,
              next_state: StateSpace) -> float:
        """
        学习（Q-Learning更新）

        Q(s,a) = Q(s,a) + α * (r + γ * max_a' Q(s',a') - Q(s,a))

        Returns:
            Q值变化量
        """
        state_key = state.to_discrete()
        next_state_key = next_state.to_discrete()

        # 当前Q值
        current_q = self.q_table.get_q(state_key, action)

        # 下一个状态的最大Q值
        next_max_q = max(
            self.q_table.get_q(next_state_key, a)
            for a in ActionSpace.ALL_ACTIONS
        )

        # Q-Learning更新
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * next_max_q - current_q
        )

        # 更新Q表
        self.q_table.set_q(state_key, action, new_q)

        # 记录学习
        record = LearningRecord(
            record_id=str(uuid.uuid4())[:8],
            state=state,
            action=action,
            reward=reward,
            next_state=next_state,
            q_value_before=current_q,
            q_value_after=new_q
        )
        self.learning_history.append(record)

        # 衰减探索率
        self.exploration_rate = max(
            self.min_exploration,
            self.exploration_rate * self.exploration_decay
        )

        return new_q - current_q

    def get_action_recommendation(self, state: StateSpace) -> Dict:
        """获取动作推荐"""
        state_key = state.to_discrete()

        # 获取所有动作的Q值
        q_values = {
            action: self.q_table.get_q(state_key, action)
            for action in ActionSpace.ALL_ACTIONS
        }

        # 最佳动作
        best_action = max(q_values, key=q_values.get)

        # 置信度（基于Q值差异）
        q_vals = list(q_values.values())
        max_q = max(q_vals)
        second_max = sorted(q_vals)[-2] if len(q_vals) > 1 else max_q
        confidence = 1.0 - (max_q - second_max) if max_q > 0 else 0.5

        return {
            "state": state.to_dict(),
            "q_values": q_values,
            "recommended_action": best_action,
            "action_description": ActionSpace.get_description(best_action),
            "confidence": round(confidence, 3),
            "exploration_rate": round(self.exploration_rate, 3)
        }


# ============== RL评分管理器 ==============

class RLScorerManager:
    """
    RL评分管理器 v4.2

    整合Q-Learning与PostgreSQL存储
    """

    def __init__(self, db=None):
        self.db = db
        self.agent = QLearningAgent()
        self.q_table_path = Path("/home/admin1/aiagent/代理知识库/我的/opportunity_discovery/rl_q_table.json")
        self.load_q_table()

    def load_q_table(self):
        """从文件加载Q表"""
        if self.q_table_path.exists():
            try:
                with open(self.q_table_path, 'r') as f:
                    data = json.load(f)
                self.agent.q_table.states = data.get("states", {})
                self.agent.exploration_rate = data.get("exploration_rate", 0.2)
                print(f"✓ Q表已加载: {len(self.agent.q_table.states)} 个状态")
            except Exception as e:
                print(f"Q表加载失败: {e}")

    def save_q_table(self):
        """保存Q表到文件"""
        try:
            with open(self.q_table_path, 'w') as f:
                json.dump({
                    "states": self.agent.q_table.states,
                    "exploration_rate": self.agent.exploration_rate,
                    "updated_at": datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            print(f"Q表保存失败: {e}")

    def score_opportunity(self, state: StateSpace) -> Dict:
        """评估机会并返回推荐"""
        recommendation = self.agent.get_action_recommendation(state)

        # 同时写入数据库
        if self.db:
            self._save_score_to_db(state, recommendation)

        return recommendation

    def _save_score_to_db(self, state: StateSpace, recommendation: Dict):
        """保存评分到数据库"""
        if self.db is None:
            return

        # 写入信号历史（作为RL评分信号）
        sql = """
            INSERT INTO signal_history
            (platform, entity, metric, value, timestamp, metadata)
            VALUES (%s, %s, %s, %s, NOW(), %s)
        """
        try:
            self.db.execute(sql, (
                "rl_scorer",
                recommendation.get("recommended_action", "unknown"),
                "q_value",
                recommendation.get("q_values", {}).get(recommendation.get("recommended_action"), 0),
                json.dumps({
                    "state": state.to_dict(),
                    "confidence": recommendation.get("confidence"),
                    "action": recommendation.get("recommended_action")
                })
            ))
        except Exception as e:
            pass  # 数据库不可用时静默失败

    def process_reward(self, message_id: str, engagement: int,
                      state: StateSpace, action: str) -> Dict:
        """
        处理奖励反馈

        Args:
            message_id: 消息ID
            engagement: 互动量（点赞/评论/转发等）
            state: 执行时的状态
            action: 执行的动作

        Returns:
            学习结果
        """
        # 计算奖励
        # 基础奖励：基于互动量
        if engagement >= 100:
            reward = 1.0  # 高互动
        elif engagement >= 50:
            reward = 0.5  # 中等互动
        elif engagement >= 10:
            reward = 0.1  # 低互动
        else:
            reward = -0.5  # 无互动

        # 更新状态（假设互动后状态有变化）
        next_state = state  # 简化版：状态不变

        # 学习
        q_delta = self.agent.learn(state, action, reward, next_state)

        # 保存到数据库
        if self.db:
            self._save_reward_to_db(message_id, engagement, reward, q_delta)

        # 保存Q表
        self.save_q_table()

        return {
            "message_id": message_id,
            "engagement": engagement,
            "reward": reward,
            "q_delta": q_delta,
            "new_exploration_rate": round(self.agent.exploration_rate, 3)
        }

    def _save_reward_to_db(self, message_id: str, engagement: int,
                          reward: float, q_delta: float):
        """保存奖励到数据库"""
        if self.db is None:
            return

        sql = """
            INSERT INTO signal_history
            (platform, entity, metric, value, timestamp, metadata)
            VALUES (%s, %s, %s, %s, NOW(), %s)
        """
        try:
            self.db.execute(sql, (
                "rl_feedback",
                message_id,
                "engagement",
                float(engagement),
                json.dumps({"reward": reward, "q_delta": q_delta})
            ))
        except Exception as e:
            pass

    def get_stats(self) -> Dict:
        """获取RL统计"""
        states_count = len(self.agent.q_table.states)
        actions_count = sum(
            sum(1 for v in s.values() if v != 0.0)
            for s in self.agent.q_table.states.values()
        )

        return {
            "total_states": states_count,
            "total_q_updates": len(self.agent.learning_history),
            "exploration_rate": round(self.agent.exploration_rate, 3),
            "recent_learning": [
                {
                    "action": r.action,
                    "reward": r.reward,
                    "q_delta": r.q_value_after - r.q_value_before
                }
                for r in self.agent.learning_history[-5:]
            ]
        }


# ============== 主程序 ==============

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RL评分系统 v4.2")
    parser.add_argument("--score", metavar=("TARGET", "STATE"),
                       nargs=2, help="评估机会: target state(0-1,0-1,0-1,0-1)")
    parser.add_argument("--reward", nargs=2, metavar=("MSG_ID", "ENGAGEMENT"),
                       help="反馈奖励: message_id engagement")
    parser.add_argument("--stats", action="store_true", help="显示统计")
    parser.add_argument("--demo", action="store_true", help="演示模式")

    args = parser.parse_args()

    print("🧠 强化学习评分系统 v4.2\n")

    # 初始化数据库
    db = None
    try:
        from knowledge_graph import DBConnection
        db = DBConnection.get_instance()
        db.connect()
    except:
        print("⚠️ 数据库不可用，使用文件存储")

    # 创建管理器
    manager = RLScorerManager(db)

    if args.score:
        target, state_str = args.score
        state_vals = [float(x) for x in state_str.split(",")]

        state = StateSpace(
            signal_strength=state_vals[0],
            velocity=state_vals[1],
            cross_platform=state_vals[2],
            market_timing=state_vals[3]
        )

        print(f"📊 评估 {target}:")
        print(f"   状态: {state.to_dict()}")

        result = manager.score_opportunity(state)

        print(f"\n   推荐动作: {result['recommended_action']}")
        print(f"   动作描述: {result['action_description']}")
        print(f"   置信度: {result['confidence']:.2%}")
        print(f"   探索率: {result['exploration_rate']:.2%}")

        print(f"\n   Q值:")
        for action, q in result['q_values'].items():
            print(f"     {action}: {q:.4f}")

    elif args.reward:
        msg_id, engagement = args.reward
        print(f"💰 处理奖励反馈:")
        print(f"   消息ID: {msg_id}")
        print(f"   互动量: {engagement}")

        # 模拟状态和动作
        state = StateSpace(0.7, 0.6, 0.5, 0.7)
        action = ActionSpace.CONTENT

        result = manager.process_reward(msg_id, int(engagement), state, action)

        print(f"   奖励: {result['reward']}")
        print(f"   Q值变化: {result['q_delta']:.4f}")
        print(f"   新探索率: {result['new_exploration_rate']}")

    elif args.stats:
        stats = manager.get_stats()
        print("📈 RL统计:")
        print(f"   状态数: {stats['total_states']}")
        print(f"   Q值更新数: {stats['total_q_updates']}")
        print(f"   当前探索率: {stats['exploration_rate']}")

        if stats['recent_learning']:
            print("\n   最近学习:")
            for r in stats['recent_learning']:
                print(f"     {r['action']}: reward={r['reward']}, delta={r['q_delta']:.4f}")

    elif args.demo:
        print("🎯 RL评分演示\n")

        # 模拟评分流程
        test_states = [
            StateSpace(0.9, 0.8, 0.7, 0.6),  # 高质量信号
            StateSpace(0.5, 0.5, 0.5, 0.5),  # 中等信号
            StateSpace(0.3, 0.2, 0.4, 0.8),  # 时机好但信号弱
        ]

        for i, state in enumerate(test_states, 1):
            print(f"\n测试 {i}:")
            result = manager.score_opportunity(state)
            print(f"  状态: 信号={state.signal_strength}, 速度={state.velocity}")
            print(f"  推荐: {result['recommended_action']} ({result['action_description']})")
            print(f"  置信度: {result['confidence']:.2%}")

        print("\n✅ 演示完成")

    else:
        print(__doc__)