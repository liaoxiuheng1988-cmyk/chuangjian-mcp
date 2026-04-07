"""
双写管理器 v4.2
Dual Write Manager — JSON + PostgreSQL 双重存储

核心功能：
1. 所有分析结果同时写入JSON和PostgreSQL
2. 保持向后兼容
3. 自动同步

使用方式：
python dual_write.py --sync
python dual_write.py --status
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# ============== 配置 ==============

BASE_DIR = Path("/home/admin1/aiagent/代理知识库/我的/opportunity_discovery")
JSON_DATA_DIR = BASE_DIR / "discovered_projects"


# ============== 双写结果 ==============

@dataclass
class DualWriteResult:
    """双写结果"""
    success: bool
    json_written: bool
    db_written: bool
    json_path: str = ""
    error: str = ""


# ============== 双写管理器 ==============

class DualWriteManager:
    """
    双写管理器 v4.2

    确保数据同时写入JSON文件和PostgreSQL
    """

    def __init__(self, kg_manager=None, signal_manager=None, search_manager=None):
        # 知识图谱管理器
        self.kg = kg_manager
        # 时序信号管理器
        self.signals = signal_manager
        # 语义搜索管理器
        self.search = search_manager

        # JSON数据目录
        self.json_dir = JSON_DATA_DIR
        self.json_dir.mkdir(parents=True, exist_ok=True)

    # ============== 节点写入 ==============

    def write_node(self, node_id: str, name: str, node_type: str,
                   properties: dict = None, **kwargs) -> DualWriteResult:
        """
        写入节点到JSON和数据库

        Args:
            node_id: 节点ID
            name: 节点名称
            node_type: 节点类型
            properties: 节点属性
            **kwargs: 额外参数（pagerank_score等）

        Returns:
            DualWriteResult
        """
        result = DualWriteResult(success=False, json_written=False, db_written=False)

        # 1. 写入JSON
        try:
            json_path = self.json_dir / f"node_{node_id}.json"
            node_data = {
                "node_id": node_id,
                "name": name,
                "node_type": node_type,
                "properties": properties or {},
                "written_at": datetime.now().isoformat(),
            }
            node_data.update(kwargs)

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(node_data, f, ensure_ascii=False, indent=2)

            result.json_written = True
            result.json_path = str(json_path)
        except Exception as e:
            result.error = f"JSON写入失败: {e}"

        # 2. 写入数据库
        if self.kg:
            try:
                self.kg.add_node(node_id, name, node_type, properties)
                result.db_written = True
            except Exception as e:
                result.error += f" | DB写入失败: {e}"

        result.success = result.json_written
        return result

    # ============== 边写入 ==============

    def write_edge(self, from_node: str, to_node: str,
                   relation_type: str, strength: float = 0.5,
                   properties: dict = None, **kwargs) -> DualWriteResult:
        """
        写入关系到JSON和数据库
        """
        result = DualWriteResult(success=False, json_written=False, db_written=False)

        # 1. 写入JSON
        try:
            edge_id = f"{from_node}_{to_node}_{relation_type}"
            json_path = self.json_dir / f"edge_{edge_id}.json"
            edge_data = {
                "edge_id": edge_id,
                "from_node": from_node,
                "to_node": to_node,
                "relation_type": relation_type,
                "strength": strength,
                "properties": properties or {},
                "written_at": datetime.now().isoformat(),
            }
            edge_data.update(kwargs)

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(edge_data, f, ensure_ascii=False, indent=2)

            result.json_written = True
            result.json_path = str(json_path)
        except Exception as e:
            result.error = f"JSON写入失败: {e}"

        # 2. 写入数据库
        if self.kg:
            try:
                self.kg.add_edge(from_node, to_node, relation_type,
                               strength, properties, **kwargs)
                result.db_written = True
            except Exception as e:
                result.error += f" | DB写入失败: {e}"

        result.success = result.json_written
        return result

    # ============== 分析结果写入 ==============

    def write_discovery_result(self, core_node: str, analysis_result: dict,
                             opportunities: List[dict] = None) -> DualWriteResult:
        """
        写入发现结果到JSON和数据库

        Args:
            core_node: 核心节点名称
            analysis_result: 分析结果字典
            opportunities: 机会列表

        Returns:
            DualWriteResult
        """
        result = DualWriteResult(success=False, json_written=False, db_written=False)

        # 1. 写入JSON文件
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_filename = f"discovery_{core_node}_{timestamp}.json"
            json_path = self.json_dir / json_filename

            full_result = {
                "core_node": core_node,
                "analysis_result": analysis_result,
                "opportunities": opportunities or [],
                "written_at": datetime.now().isoformat(),
            }

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(full_result, f, ensure_ascii=False, indent=2)

            result.json_written = True
            result.json_path = str(json_path)
        except Exception as e:
            result.error = f"JSON写入失败: {e}"

        # 2. 写入数据库（节点和边）
        if self.kg:
            try:
                # 写入核心节点
                self.kg.add_node(
                    f"core_{core_node}",
                    core_node,
                    "CORE",
                    {"analysis_result": analysis_result}
                )

                # 写入发现的节点
                for node in analysis_result.get("nodes", {}).values():
                    self.kg.add_node(
                        node.get("node_id", ""),
                        node.get("name", ""),
                        node.get("type", "UNKNOWN"),
                        node.get("properties", {})
                    )

                # 写入关系
                for rel in analysis_result.get("relationships", []):
                    self.kg.add_edge(
                        rel.get("node_a", ""),
                        rel.get("node_b", ""),
                        rel.get("relation_type", "UNKNOWN"),
                        rel.get("strength", 0.5),
                        conflict_level=rel.get("conflict_level", "低"),
                        mcp_potential=rel.get("mcp_potential", "低"),
                        shovel_score=rel.get("shovel_score", 1)
                    )

                result.db_written = True
            except Exception as e:
                result.error += f" | DB写入失败: {e}"

        # 3. 写入向量嵌入
        if self.search and opportunities:
            try:
                for opp in opportunities:
                    entity_id = f"opp_{core_node}_{opp.get('node_name', 'unknown')}"
                    text = f"{opp.get('node_name', '')} {opp.get('shovel_form', '')} {opp.get('execution_tip', '')}"
                    self.search.add_embedding(
                        entity_id=entity_id,
                        entity_name=opp.get('node_name', ''),
                        entity_type="opportunity",
                        text_to_embed=text,
                        metadata=opp
                    )
            except Exception as e:
                result.error += f" | 向量写入失败: {e}"

        result.success = result.json_written
        return result

    # ============== 信号写入 ==============

    def write_signal(self, platform: str, entity: str, metric: str,
                   value: float, metadata: dict = None) -> bool:
        """
        写入时序信号
        """
        if self.signals:
            try:
                self.signals.record_signal(platform, entity, metric, value, metadata)
                return True
            except Exception as e:
                print(f"信号写入失败: {e}")
                return False
        return False

    # ============== 读取操作 ==============

    def read_node(self, node_id: str) -> Optional[dict]:
        """从JSON读取节点"""
        json_path = self.json_dir / f"node_{node_id}.json"
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def read_discovery_result(self, core_node: str) -> Optional[dict]:
        """读取最新的发现结果"""
        pattern = f"discovery_{core_node}_*.json"
        matching = list(self.json_dir.glob(pattern))
        if not matching:
            return None

        # 返回最新的
        latest = sorted(matching, key=lambda p: p.stat().st_mtime)[-1]
        with open(latest, 'r', encoding='utf-8') as f:
            return json.load(f)

    # ============== 同步操作 ==============

    def sync_from_json_to_db(self) -> Dict[str, int]:
        """
        从JSON同步数据到数据库

        Returns:
            {"nodes": count, "edges": count}
        """
        if not self.kg:
            return {"nodes": 0, "edges": 0}

        node_count = 0
        edge_count = 0

        # 同步节点
        for json_file in self.json_dir.glob("node_*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.kg.add_node(
                    data["node_id"],
                    data["name"],
                    data["node_type"],
                    data.get("properties", {})
                )
                node_count += 1
            except Exception as e:
                print(f"同步节点失败 {json_file}: {e}")

        # 同步边
        for json_file in self.json_dir.glob("edge_*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.kg.add_edge(
                    data["from_node"],
                    data["to_node"],
                    data["relation_type"],
                    data.get("strength", 0.5),
                    data.get("properties", {})
                )
                edge_count += 1
            except Exception as e:
                print(f"同步边失败 {json_file}: {e}")

        return {"nodes": node_count, "edges": edge_count}

    def get_status(self) -> Dict:
        """获取双写状态"""
        json_files = list(self.json_dir.glob("*.json"))
        node_files = list(self.json_dir.glob("node_*.json"))
        edge_files = list(self.json_dir.glob("edge_*.json"))
        discovery_files = list(self.json_dir.glob("discovery_*.json"))

        return {
            "json_dir": str(self.json_dir),
            "total_files": len(json_files),
            "node_files": len(node_files),
            "edge_files": len(edge_files),
            "discovery_files": len(discovery_files),
            "db_connected": self.kg is not None,
            "signals_connected": self.signals is not None,
            "search_connected": self.search is not None,
        }


# ============== 主程序 ==============

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="双写管理工具 v4.2")
    parser.add_argument("--sync", action="store_true", help="同步JSON到数据库")
    parser.add_argument("--status", action="store_true", help="显示状态")
    parser.add_argument("--demo", action="store_true", help="演示模式")

    args = parser.parse_args()

    print("📦 双写管理工具 v4.2\n")

    dual_write = DualWriteManager()

    if args.status:
        print("📊 双写状态:")
        status = dual_write.get_status()
        for k, v in status.items():
            print(f"  {k}: {v}")

    elif args.sync:
        print("🔄 同步JSON到数据库...")
        result = dual_write.sync_from_json_to_db()
        print(f"✓ 同步完成: {result['nodes']}个节点, {result['edges']}条边")

    elif args.demo:
        print("🎯 演示双写...")
        result = dual_write.write_node(
            "demo_node_001",
            "OpenClaw",
            "CORE",
            {"version": "4.2"},
            pagerank_score=1.0
        )
        print(f"写入结果: {result.success}")
        print(f"  JSON: {result.json_written} -> {result.json_path}")
        print(f"  DB: {result.db_written}")

    else:
        print(__doc__)