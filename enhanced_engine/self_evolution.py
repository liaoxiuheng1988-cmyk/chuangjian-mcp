"""
自进化引擎 v4.3
Self-Evolution Engine — 知识压缩 + 遗忘机制

核心功能：
1. 知识压缩 - 将所有学习结果定期压缩
2. 遗忘机制 - 长期无反馈的规则自动降权
3. 知识压缩包存储 - 定期生成知识快照

使用方式：
python self_evolution.py --compress
python self_evolution.py --forget
python self_evolution.py --status
"""

import json
import zlib
import base64
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict


# ============== 知识项定义 ==============

@dataclass
class KnowledgeItem:
    """知识项"""
    knowledge_id: str
    knowledge_type: str  # rule/q_value/causal/pattern
    content: Dict
    confidence: float  # 置信度 0-1
    last_feedback_at: str = ""
    feedback_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    access_count: int = 0
    compressed: bool = False

    def to_dict(self) -> Dict:
        return {
            "knowledge_id": self.knowledge_id,
            "knowledge_type": self.knowledge_type,
            "content": self.content,
            "confidence": self.confidence,
            "last_feedback_at": self.last_feedback_at,
            "feedback_count": self.feedback_count,
            "created_at": self.created_at,
            "access_count": self.access_count,
            "compressed": self.compressed
        }


@dataclass
class CompressedKnowledge:
    """压缩后的知识包"""
    bundle_id: str
    created_at: str
    expires_at: str
    items_count: int
    compressed_data: str  # base64 encoded + zlib compressed
    original_size: int
    compressed_size: int
    compression_ratio: float
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "bundle_id": self.bundle_id,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "items_count": self.items_count,
            "compressed_data": self.compressed_data[:50] + "...",  # 截断显示
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
            "compression_ratio": round(self.compression_ratio, 2),
            "metadata": self.metadata
        }


# ============== 遗忘机制 ==============

class ForgettingMechanism:
    """
    遗忘机制

    核心思想：
    1. 知识有蜜月期 - 新知识有保护期
    2. 长青知识更稳定 - 多次反馈的知识更难遗忘
    3. 冷知识逐渐衰减 - 长时间无反馈的知识自动降权
    4. 压缩包唤醒 - 可以从压缩包恢复知识
    """

    # 遗忘参数
    HONEY_PERIOD_DAYS = 7       # 蜜月期（7天内不降权）
    HALF_LIFE_DAYS = 90         # 半衰期（90天无反馈减半）
    DECAY_RATE = 0.95           # 月衰减率
    MIN_CONFIDENCE = 0.1        # 最低置信度阈值
    RECOVERY_BONUS = 0.2        # 恢复时的加成

    def __init__(self):
        self.knowledge_weights: Dict[str, float] = {}  # knowledge_id -> weight

    def calculate_decay(self, last_feedback: str, current_confidence: float,
                       feedback_count: int) -> Tuple[float, str]:
        """
        计算衰减后的置信度

        Args:
            last_feedback: 上次反馈时间 (ISO格式)
            current_confidence: 当前置信度
            feedback_count: 反馈次数

        Returns:
            (new_confidence, reason)
        """
        if not last_feedback:
            # 从未有过反馈，只衰减不惩罚
            return current_confidence * self.DECAY_RATE, "首次衰减"

        try:
            last_time = datetime.fromisoformat(last_feedback)
            days_since = (datetime.now() - last_time).days
        except:
            return current_confidence * self.DECAY_RATE, "时间解析错误"

        # 蜜月期保护
        if days_since <= self.HONEY_PERIOD_DAYS:
            return current_confidence, "蜜月期保护"

        # 计算衰减
        if feedback_count >= 5:
            # 长青知识：更慢衰减
            decay_factor = 0.98 ** (days_since / 30)
        elif feedback_count >= 3:
            # 稳定知识：正常衰减
            decay_factor = 0.95 ** (days_since / 30)
        else:
            # 新知识：快速衰减
            decay_factor = 0.90 ** (days_since / 30)

        new_confidence = current_confidence * decay_factor

        # 检查半衰期
        if days_since > self.HALF_LIFE_DAYS and feedback_count < 3:
            new_confidence *= 0.5  # 额外减半

        # 确保不低于最低阈值
        if new_confidence < self.MIN_CONFIDENCE:
            new_confidence = 0.0  # 完全遗忘

        reason = f"衰减{1-decay_factor:.1%}" if decay_factor < 1 else "稳定"

        return max(new_confidence, 0.0), reason

    def should_compress(self, item: KnowledgeItem) -> bool:
        """判断知识项是否应该被压缩"""
        if item.compressed:
            return False

        # 置信度低于阈值或长期无反馈
        if item.confidence < self.MIN_CONFIDENCE:
            return True

        if not item.last_feedback_at:
            try:
                created = datetime.fromisoformat(item.created_at)
                days_old = (datetime.now() - created).days
                if days_old > self.HALF_LIFE_DAYS and item.feedback_count == 0:
                    return True
            except:
                pass

        return False

    def get_retention_priority(self, item: KnowledgeItem) -> float:
        """获取知识保留优先级（用于决定保留哪些知识）"""
        priority = 0.0

        # 基于反馈次数（最重要）
        priority += min(item.feedback_count * 0.2, 0.6)

        # 基于最近反馈
        if item.last_feedback_at:
            try:
                last_time = datetime.fromisoformat(item.last_feedback_at)
                days_since = (datetime.now() - last_time).days
                recency_score = max(0, 1 - days_since / self.HALF_LIFE_DAYS)
                priority += recency_score * 0.3
            except:
                pass

        # 基于当前置信度
        priority += item.confidence * 0.1

        return priority


# ============== 知识压缩器 ==============

class KnowledgeCompressor:
    """
    知识压缩器

    将多个知识项压缩成单个压缩包
    """

    def compress(self, items: List[KnowledgeItem]) -> CompressedKnowledge:
        """
        压缩知识项

        Args:
            items: 知识项列表

        Returns:
            CompressedKnowledge
        """
        bundle_id = str(uuid.uuid4())[:8]

        # 序列化
        raw_data = json.dumps([item.to_dict() for item in items], ensure_ascii=False)
        original_size = len(raw_data)

        # 压缩
        compressed = zlib.compress(raw_data.encode('utf-8'), level=9)
        compressed_size = len(compressed)
        compressed_b64 = base64.b64encode(compressed).decode('ascii')

        # 压缩率
        ratio = (original_size - compressed_size) / original_size if original_size > 0 else 0

        now = datetime.now()
        expires = now + timedelta(days=180)  # 180天后过期

        return CompressedKnowledge(
            bundle_id=bundle_id,
            created_at=now.isoformat(),
            expires_at=expires.isoformat(),
            items_count=len(items),
            compressed_data=compressed_b64,
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=ratio,
            metadata={
                "avg_confidence": sum(i.confidence for i in items) / len(items) if items else 0,
                "types": list(set(i.knowledge_type for i in items))
            }
        )

    def decompress(self, bundle: CompressedKnowledge) -> List[KnowledgeItem]:
        """
        解压知识包

        Args:
            bundle: 压缩包

        Returns:
            知识项列表
        """
        try:
            # 解码
            compressed = base64.b64decode(bundle.compressed_data.encode('ascii'))
            # 解压
            raw_data = zlib.decompress(compressed).decode('utf-8')
            # 反序列化
            data_list = json.loads(raw_data)

            items = []
            for data in data_list:
                items.append(KnowledgeItem(
                    knowledge_id=data["knowledge_id"],
                    knowledge_type=data["knowledge_type"],
                    content=data["content"],
                    confidence=data["confidence"],
                    last_feedback_at=data.get("last_feedback_at", ""),
                    feedback_count=data.get("feedback_count", 0),
                    created_at=data.get("created_at", ""),
                    access_count=data.get("access_count", 0),
                    compressed=True
                ))

            return items
        except Exception as e:
            print(f"解压失败: {e}")
            return []


# ============== 自进化管理器 ==============

class SelfEvolutionManager:
    """
    自进化管理器 v4.3

    整合知识压缩与遗忘机制
    """

    def __init__(self, db=None):
        self.db = db

        # 知识存储
        self.knowledge_base: Dict[str, KnowledgeItem] = {}
        self.compressed_bundles: List[CompressedKnowledge] = []

        # 子模块
        self.forgetting = ForgettingMechanism()
        self.compressor = KnowledgeCompressor()

        # 配置
        self.knowledge_file = Path("/home/admin1/aiagent/代理知识库/我的/opportunity_discovery/self_evolution_knowledge.json")
        self.bundles_file = Path("/home/admin1/aiagent/代理知识库/我的/opportunity_discovery/compressed_bundles.json")

        # 加载已有知识
        self.load_knowledge()
        self.load_bundles()

    # ============== 基础操作 ==============

    def add_knowledge(self, knowledge_type: str, content: Dict,
                     initial_confidence: float = 0.5) -> str:
        """添加新知识"""
        knowledge_id = f"kn_{knowledge_type}_{uuid.uuid4().hex[:8]}"

        item = KnowledgeItem(
            knowledge_id=knowledge_id,
            knowledge_type=knowledge_type,
            content=content,
            confidence=initial_confidence
        )

        self.knowledge_base[knowledge_id] = item
        self.save_knowledge()

        return knowledge_id

    def update_feedback(self, knowledge_id: str, is_positive: bool,
                       engagement: int = 0) -> bool:
        """更新知识反馈"""
        if knowledge_id not in self.knowledge_base:
            return False

        item = self.knowledge_base[knowledge_id]
        item.last_feedback_at = datetime.now().isoformat()
        item.feedback_count += 1

        # 正反馈增加置信度
        if is_positive:
            bonus = min(0.1, engagement / 1000)  # 最多+0.1
            item.confidence = min(1.0, item.confidence + bonus)
        else:
            # 负反馈降低置信度
            penalty = 0.05
            item.confidence = max(0.0, item.confidence - penalty)

        self.save_knowledge()
        return True

    def query_knowledge(self, knowledge_type: str = None,
                       min_confidence: float = 0.0) -> List[KnowledgeItem]:
        """查询知识"""
        results = []

        for item in self.knowledge_base.values():
            if knowledge_type and item.knowledge_type != knowledge_type:
                continue
            if item.confidence >= min_confidence:
                item.access_count += 1
                results.append(item)

        return sorted(results, key=lambda x: x.confidence, reverse=True)

    # ============== 压缩操作 ==============

    def compress_knowledge(self) -> Dict:
        """
        执行知识压缩

        Returns:
            压缩结果统计
        """
        # 1. 确定需要压缩的知识
        to_compress = []
        to_keep = []

        for item in self.knowledge_base.values():
            if self.forgetting.should_compress(item):
                to_compress.append(item)
            else:
                to_keep.append(item)

        if not to_compress:
            return {
                "success": True,
                "compressed_count": 0,
                "kept_count": len(to_keep),
                "message": "无需压缩的知识"
            }

        # 2. 执行压缩
        bundle = self.compressor.compress(to_compress)
        self.compressed_bundles.append(bundle)

        # 3. 从活跃知识中移除已压缩的
        for item in to_compress:
            del self.knowledge_base[item.knowledge_id]

        # 4. 保存
        self.save_knowledge()
        self.save_bundles()

        return {
            "success": True,
            "compressed_count": len(to_compress),
            "bundle_id": bundle.bundle_id,
            "compression_ratio": bundle.compression_ratio,
            "kept_count": len(to_keep)
        }

    def recover_from_bundle(self, bundle_id: str) -> List[KnowledgeItem]:
        """从压缩包恢复知识"""
        bundle = None
        for b in self.compressed_bundles:
            if b.bundle_id == bundle_id:
                bundle = b
                break

        if not bundle:
            return []

        # 检查是否过期
        try:
            expires = datetime.fromisoformat(bundle.expires_at)
            if datetime.now() > expires:
                return []  # 已过期
        except:
            pass

        # 解压
        items = self.compressor.decompress(bundle)

        # 恢复时给予恢复加成
        for item in items:
            item.confidence = min(1.0, item.confidence + self.forgetting.RECOVERY_BONUS)
            item.compressed = False

        return items

    # ============== 遗忘操作 ==============

    def apply_forgetting(self) -> Dict:
        """
        应用遗忘机制

        Returns:
            遗忘结果统计
        """
        decayed = []
        forgotten = []

        for item in list(self.knowledge_base.values()):
            new_confidence, reason = self.forgetting.calculate_decay(
                item.last_feedback_at,
                item.confidence,
                item.feedback_count
            )

            if new_confidence == 0:
                forgotten.append(item.knowledge_id)
            elif new_confidence < item.confidence:
                item.confidence = new_confidence
                decayed.append({
                    "knowledge_id": item.knowledge_id,
                    "old_confidence": item.confidence,
                    "new_confidence": new_confidence,
                    "reason": reason
                })

        # 移除完全遗忘的知识
        for kid in forgotten:
            del self.knowledge_base[kid]

        self.save_knowledge()

        return {
            "decayed_count": len(decayed),
            "forgotten_count": len(forgotten),
            "active_count": len(self.knowledge_base),
            "decayed_items": decayed[-5:]  # 最近5条
        }

    def get_forgetting_report(self) -> Dict:
        """获取遗忘报告"""
        items = list(self.knowledge_base.values())

        if not items:
            return {"status": "empty"}

        # 按类型统计
        by_type = defaultdict(list)
        for item in items:
            by_type[item.knowledge_type].append(item)

        # 按阶段统计
        stages = {
            "蜜月期": 0,       # 7天内
            "成长期": 0,       # 7-30天
            "稳定期": 0,       # 30-90天
            "衰减期": 0,       # 90天以上
            "待压缩": 0        # 置信度低于阈值
        }

        now = datetime.now()
        for item in items:
            if self.forgetting.should_compress(item):
                stages["待压缩"] += 1
                continue

            if not item.last_feedback_at:
                try:
                    created = datetime.fromisoformat(item.created_at)
                    days = (now - created).days
                    if days <= 7:
                        stages["蜜月期"] += 1
                    elif days <= 30:
                        stages["成长期"] += 1
                    elif days <= 90:
                        stages["稳定期"] += 1
                    else:
                        stages["衰减期"] += 1
                except:
                    stages["蜜月期"] += 1
            else:
                try:
                    last = datetime.fromisoformat(item.last_feedback_at)
                    days = (now - last).days
                    if days <= 7:
                        stages["蜜月期"] += 1
                    elif days <= 30:
                        stages["成长期"] += 1
                    elif days <= 90:
                        stages["稳定期"] += 1
                    else:
                        stages["衰减期"] += 1
                except:
                    stages["蜜月期"] += 1

        return {
            "total_knowledge": len(items),
            "compressed_bundles": len(self.compressed_bundles),
            "by_type": dict(by_type),
            "by_stage": stages
        }

    # ============== Q表集成 ==============

    def integrate_q_table(self, q_table_states: Dict) -> int:
        """
        将Q表知识添加到自进化系统

        Args:
            q_table_states: QLearningAgent.q_table.states

        Returns:
            添加的知识项数量
        """
        count = 0
        for state_key, actions in q_table_states.items():
            for action, q_value in actions.items():
                if q_value != 0:  # 只记录非零Q值
                    knowledge_id = self.add_knowledge(
                        knowledge_type="q_value",
                        content={
                            "state": state_key,
                            "action": action,
                            "q_value": q_value
                        },
                        initial_confidence=min(1.0, abs(q_value) / 10)
                    )
                    count += 1

        return count

    def integrate_causal_relations(self, causal_edges: List[Dict]) -> int:
        """
        将因果关系添加到自进化系统

        Args:
            causal_edges: CausalGraph.edges

        Returns:
            添加的知识项数量
        """
        count = 0
        for edge in causal_edges:
            self.add_knowledge(
                knowledge_type="causal",
                content={
                    "from_node": edge.get("from_node", ""),
                    "to_node": edge.get("to_node", ""),
                    "cause_type": edge.get("cause_type", "unknown"),
                    "confidence": edge.get("confidence", 0.5),
                    "lag": edge.get("lag", 0)
                },
                initial_confidence=edge.get("confidence", 0.5)
            )
            count += 1

        return count

    # ============== 持久化 ==============

    def save_knowledge(self):
        """保存知识到文件"""
        try:
            data = {
                k: v.to_dict() for k, v in self.knowledge_base.items()
            }
            with open(self.knowledge_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"知识保存失败: {e}")

    def load_knowledge(self):
        """加载知识"""
        if not self.knowledge_file.exists():
            return

        try:
            with open(self.knowledge_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for kid, kdata in data.items():
                self.knowledge_base[kid] = KnowledgeItem(
                    knowledge_id=kdata["knowledge_id"],
                    knowledge_type=kdata["knowledge_type"],
                    content=kdata["content"],
                    confidence=kdata["confidence"],
                    last_feedback_at=kdata.get("last_feedback_at", ""),
                    feedback_count=kdata.get("feedback_count", 0),
                    created_at=kdata.get("created_at", ""),
                    access_count=kdata.get("access_count", 0),
                    compressed=kdata.get("compressed", False)
                )
        except Exception as e:
            print(f"知识加载失败: {e}")

    def save_bundles(self):
        """保存压缩包索引"""
        try:
            data = [b.to_dict() for b in self.compressed_bundles]
            with open(self.bundles_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"压缩包保存失败: {e}")

    def load_bundles(self):
        """加载压缩包索引"""
        if not self.bundles_file.exists():
            return

        try:
            with open(self.bundles_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for item in data:
                self.compressed_bundles.append(CompressedKnowledge(
                    bundle_id=item["bundle_id"],
                    created_at=item["created_at"],
                    expires_at=item["expires_at"],
                    items_count=item["items_count"],
                    compressed_data=item["compressed_data"],
                    original_size=item["original_size"],
                    compressed_size=item["compressed_size"],
                    compression_ratio=item["compression_ratio"],
                    metadata=item.get("metadata", {})
                ))
        except Exception as e:
            print(f"压缩包加载失败: {e}")

    # ============== 知识判断 ==============

    def make_decision(self, context: Dict) -> Dict:
        """
        基于压缩后的知识做判断

        Args:
            context: 包含state信息的上下文

        Returns:
            决策结果
        """
        state = context.get("state", {})
        state_key = f"{int(state.get('signal_strength', 0.5) * 4)}-{int(state.get('velocity', 0.5) * 4)}-{int(state.get('cross_platform', 0.5) * 4)}-{int(state.get('market_timing', 0.5) * 4)}"

        # 查询相关Q值知识
        q_knowledge = self.query_knowledge("q_value", min_confidence=0.1)

        relevant_q = []
        for item in q_knowledge:
            content = item.content
            if content.get("state") == state_key:
                relevant_q.append({
                    "action": content["action"],
                    "q_value": content["q_value"],
                    "confidence": item.confidence
                })

        if relevant_q:
            # 基于置信度加权选择
            best = max(relevant_q, key=lambda x: x["q_value"] * x["confidence"])
            return {
                "recommended_action": best["action"],
                "confidence": best["confidence"],
                "knowledge_source": "q_value",
                "alternatives": relevant_q[:3]
            }

        # 查询相关因果知识
        causal_knowledge = self.query_knowledge("causal", min_confidence=0.2)
        if causal_knowledge:
            return {
                "recommended_action": "因果推断",
                "confidence": causal_knowledge[0].confidence,
                "knowledge_source": "causal",
                "causal_info": [k.content for k in causal_knowledge[:3]]
            }

        return {
            "recommended_action": "待探索",
            "confidence": 0.0,
            "knowledge_source": "none"
        }


# ============== 主程序 ==============

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="自进化引擎 v4.3")
    parser.add_argument("--compress", action="store_true", help="执行知识压缩")
    parser.add_argument("--forget", action="store_true", help="应用遗忘机制")
    parser.add_argument("--status", action="store_true", help="查看状态")
    parser.add_argument("--report", action="store_true", help="遗忘报告")
    parser.add_argument("--add", nargs=2, metavar=("TYPE", "CONTENT"),
                       help="添加知识: type content_json")
    parser.add_argument("--query", nargs=2, metavar=("TYPE", "MIN_CONF"),
                       help="查询知识: type min_confidence")
    parser.add_argument("--decision", metavar="STATE", help="基于知识做决策")
    parser.add_argument("--demo", action="store_true", help="演示模式")

    args = parser.parse_args()

    print("🧬 自进化引擎 v4.3\n")
    print("  知识压缩 + 遗忘机制\n")

    # 初始化
    db = None
    try:
        from knowledge_graph import DBConnection
        db = DBConnection.get_instance()
        db.connect()
    except:
        pass

    manager = SelfEvolutionManager(db)

    if args.demo:
        print("🎯 演示模式\n")

        # 添加一些知识
        print("1. 添加知识项:")
        kid1 = manager.add_knowledge("rule", {"pattern": "GPU需求上升 → 云服务机会", "weight": 0.8}, 0.7)
        kid2 = manager.add_knowledge("q_value", {"state": "3-2-2-3", "action": "tool", "q_value": 2.5}, 0.6)
        kid3 = manager.add_knowledge("causal", {"from_node": "OpenClaw", "to_node": "GPU供应商", "confidence": 0.75}, 0.75)
        print(f"   添加3条知识: {kid1}, {kid2}, {kid3}")

        # 模拟反馈
        print("\n2. 模拟反馈:")
        manager.update_feedback(kid1, is_positive=True, engagement=150)
        manager.update_feedback(kid2, is_positive=True, engagement=80)
        print("   更新2条知识反馈")

        # 查询
        print("\n3. 查询知识:")
        rules = manager.query_knowledge("rule", min_confidence=0.1)
        print(f"   规则知识: {len(rules)} 条")

        # 遗忘报告
        print("\n4. 遗忘报告:")
        report = manager.get_forgetting_report()
        print(f"   总知识: {report['total_knowledge']}")
        print(f"   压缩包: {report['compressed_bundles']}")
        print(f"   阶段分布: {report['by_stage']}")

        # 做决策
        print("\n5. 决策示例:")
        context = {"state": {"signal_strength": 0.7, "velocity": 0.6, "cross_platform": 0.5, "market_timing": 0.7}}
        decision = manager.make_decision(context)
        print(f"   推荐动作: {decision['recommended_action']}")
        print(f"   置信度: {decision['confidence']:.0%}")
        print(f"   知识来源: {decision['knowledge_source']}")

        print("\n✅ 演示完成")

    elif args.compress:
        print("📦 执行知识压缩...\n")
        result = manager.compress_knowledge()
        if result["success"]:
            print(f"✓ 压缩完成")
            print(f"  压缩数量: {result['compressed_count']}")
            print(f"  保留数量: {result['kept_count']}")
            if result.get('bundle_id'):
                print(f"  压缩包ID: {result['bundle_id']}")
                print(f"  压缩率: {result['compression_ratio']:.1%}")

    elif args.forget:
        print("🧠 应用遗忘机制...\n")
        result = manager.apply_forgetting()
        print(f"✓ 遗忘处理完成")
        print(f"  衰减数量: {result['decayed_count']}")
        print(f"  遗忘数量: {result['forgotten_count']}")
        print(f"  活跃数量: {result['active_count']}")

    elif args.status:
        print("📊 系统状态:\n")
        print(f"  知识项: {len(manager.knowledge_base)}")
        print(f"  压缩包: {len(manager.compressed_bundles)}")

        if manager.knowledge_base:
            avg_conf = sum(k.confidence for k in manager.knowledge_base.values()) / len(manager.knowledge_base)
            print(f"  平均置信度: {avg_conf:.2f}")

    elif args.report:
        print("📈 遗忘报告:\n")
        report = manager.get_forgetting_report()
        print(f"  总知识: {report.get('total_knowledge', 0)}")
        print(f"  压缩包: {report.get('compressed_bundles', 0)}")
        if 'by_stage' in report:
            print(f"\n  阶段分布:")
            for stage, count in report['by_stage'].items():
                print(f"    {stage}: {count}")

    elif args.add:
        ktype, content_json = args.add
        content = json.loads(content_json)
        kid = manager.add_knowledge(ktype, content)
        print(f"✓ 添加知识: {kid}")

    elif args.query:
        ktype, min_conf = args.query
        items = manager.query_knowledge(ktype, float(min_conf))
        print(f"查询结果 ({len(items)} 条):\n")
        for item in items[:10]:
            print(f"  {item.knowledge_id}: {item.knowledge_type} (置信度: {item.confidence:.2f})")

    elif args.decision:
        # 解析state
        parts = args.decision.split(",")
        state = {
            "signal_strength": float(parts[0]) if len(parts) > 0 else 0.5,
            "velocity": float(parts[1]) if len(parts) > 1 else 0.5,
            "cross_platform": float(parts[2]) if len(parts) > 2 else 0.5,
            "market_timing": float(parts[3]) if len(parts) > 3 else 0.5
        }
        decision = manager.make_decision({"state": state})
        print(f"\n决策结果:")
        print(f"  推荐动作: {decision['recommended_action']}")
        print(f"  置信度: {decision.get('confidence', 0):.0%}")
        print(f"  知识来源: {decision['knowledge_source']}")

    else:
        print(__doc__)