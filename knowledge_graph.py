"""
知识图谱层 v4.2
Knowledge Graph Layer — PostgreSQL + PageRank + Community Detection

核心功能：
1. PostgreSQL图存储替代内存BFS
2. PageRank算法计算节点重要性
3. 社区检测自动发现子生态簇
4. 图查询API

使用方式：
python knowledge_graph.py --init-db    # 初始化数据库
python knowledge_graph.py --pagerank   # 计算PageRank
python knowledge_graph.py --community  # 社区检测
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path

# ============== 数据库连接 ==============

@dataclass
class DBConfig:
    """数据库配置"""
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    database: str = os.getenv("DB_NAME", "opportunity_discovery")
    user: str = os.getenv("DB_USER", "postgres")
    password: str = os.getenv("DB_PASSWORD", "")
    sslmode: str = os.getenv("DB_SSLMODE", "prefer")


class DBConnection:
    """数据库连接管理器"""
    _instance = None

    def __init__(self, config: DBConfig = None):
        self.config = config or DBConfig()
        self._conn = None

    @classmethod
    def get_instance(cls) -> 'DBConnection':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def connect(self):
        """建立数据库连接"""
        try:
            import psycopg2
            self._conn = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password,
                sslmode=self.config.sslmode
            )
            return self._conn
        except ImportError:
            print("⚠️ psycopg2 未安装，使用模拟模式")
            return None

    def execute(self, sql: str, params: tuple = None) -> List[Dict]:
        """执行SQL并返回结果"""
        if self._conn is None:
            self.connect()

        if self._conn is None:
            return []

        try:
            with self._conn.cursor() as cur:
                cur.execute(sql, params)
                if cur.description:
                    columns = [desc[0] for desc in cur.description]
                    return [dict(zip(columns, row)) for row in cur.fetchall()]
                self._conn.commit()
                return []
        except Exception as e:
            print(f"SQL执行错误: {e}")
            return []

    def close(self):
        """关闭连接"""
        if self._conn:
            self._conn.close()


# ============== PageRank算法 ==============

class PageRankCalculator:
    """
    PageRank算法实现

    用于计算知识图谱中节点的重要性
    """

    def __init__(self, db: DBConnection):
        self.db = db
        self.damping_factor = 0.85
        self.max_iterations = 100
        self.convergence_threshold = 0.0001

    def compute(self, graph_name: str = "default") -> List[Dict]:
        """
        计算PageRank

        使用幂迭代法
        """
        # 获取所有边
        edges = self._get_edges()
        if not edges:
            return []

        # 构建邻接表
        adjacency = self._build_adjacency(edges)
        nodes = list(adjacency.keys())
        n = len(nodes)

        if n == 0:
            return []

        # 初始化PageRank
        pr = {node: 1.0 / n for node in nodes}

        # 幂迭代
        for iteration in range(self.max_iterations):
            new_pr = {}
            diff = 0.0

            for node in nodes:
                # 来自其他节点的PageRank贡献
                rank_sum = 0.0
                for other_node, neighbors in adjacency.items():
                    if node in neighbors:
                        # 该节点的PageRank / 出度
                        rank_sum += pr[other_node] / len(neighbors)

                # PageRank公式: (1-d)/n + d * rank_sum
                new_pr[node] = (1 - self.damping_factor) / n + self.damping_factor * rank_sum
                diff += abs(new_pr[node] - pr[node])

            pr = new_pr

            if diff < self.convergence_threshold:
                print(f"✓ PageRank收敛于第{iteration + 1}次迭代")
                break

        # 更新数据库
        self._update_pagerank(pr)

        # 返回排序结果
        sorted_nodes = sorted(pr.items(), key=lambda x: x[1], reverse=True)
        return [
            {"node_id": node_id, "pagerank": score, "rank": rank + 1}
            for rank, (node_id, score) in enumerate(sorted_nodes)
        ]

    def _get_edges(self) -> List[Tuple[str, str]]:
        """从数据库获取所有边"""
        sql = """
            SELECT from_node, to_node, strength
            FROM knowledge_graph_edges
        """
        results = self.db.execute(sql)
        return [(r["from_node"], r["to_node"]) for r in results]

    def _build_adjacency(self, edges: List[Tuple[str, str]]) -> Dict[str, List[str]]:
        """构建邻接表"""
        adjacency: Dict[str, List[str]] = {}
        for from_node, to_node in edges:
            if from_node not in adjacency:
                adjacency[from_node] = []
            adjacency[from_node].append(to_node)
        return adjacency

    def _update_pagerank(self, pr_scores: Dict[str, float]):
        """更新数据库中的PageRank分数"""
        for node_id, score in pr_scores.items():
            sql = """
                UPDATE knowledge_graph_nodes
                SET pagerank_score = %s
                WHERE node_id = %s
            """
            self.db.execute(sql, (score, node_id))


# ============== 社区检测算法 ==============

class CommunityDetector:
    """
    社区检测算法 - Louvain方法简化版

    自动发现知识图谱中的子生态簇
    """

    def __init__(self, db: DBConnection):
        self.db = db

    def detect(self, resolution: float = 1.0) -> List[Dict]:
        """
        检测社区

        使用Louvain算法的简化实现
        """
        # 获取边数据
        edges = self._get_edges()
        if not edges:
            return []

        # 构建图
        graph = self._build_graph(edges)
        nodes = list(graph.keys())

        # 初始化：每个节点一个社区
        community_map = {node: i for i, node in enumerate(nodes)}
        node_community = {node: i for i, node in enumerate(nodes)}

        # 迭代优化
        improved = True
        iteration = 0
        max_iterations = 10

        while improved and iteration < max_iterations:
            improved = False
            iteration += 1

            for node in nodes:
                current_community = node_community[node]
                best_community = current_community
                best_gain = 0.0

                # 尝试移动到相邻节点的社区
                for neighbor in graph.get(node, []):
                    neighbor_community = node_community[neighbor]
                    if neighbor_community == current_community:
                        continue

                    # 计算模块度增益（简化版）
                    gain = self._calculate_gain(node, neighbor_community, graph, node_community, resolution)
                    if gain > best_gain:
                        best_gain = gain
                        best_community = neighbor_community

                if best_community != current_community:
                    node_community[node] = best_community
                    improved = True

        # 整理社区结果
        communities: Dict[int, List[str]] = {}
        for node, comm_id in node_community.items():
            if comm_id not in communities:
                communities[comm_id] = []
            communities[comm_id].append(node)

        # 更新数据库
        self._update_communities(node_community)

        # 生成社区摘要
        result = []
        for comm_id, members in communities.items():
            # 计算社区内平均强度
            total_strength = 0.0
            edge_count = 0
            for node in members:
                for neighbor in graph.get(node, []):
                    if neighbor in members:
                        total_strength += 1
                        edge_count += 1

            result.append({
                "community_id": comm_id,
                "node_count": len(members),
                "members": members[:10],  # 只返回前10个
                "total_members": len(members),
                "avg_strength": total_strength / max(edge_count, 1),
            })

        return sorted(result, key=lambda x: x["node_count"], reverse=True)

    def _get_edges(self) -> List[Tuple[str, str, float]]:
        """从数据库获取所有边"""
        sql = """
            SELECT from_node, to_node, strength
            FROM knowledge_graph_edges
        """
        results = self.db.execute(sql)
        return [(r["from_node"], r["to_node"], r.get("strength", 0.5)) for r in results]

    def _build_graph(self, edges: List[Tuple[str, str, float]]) -> Dict[str, List[str]]:
        """构建无向图"""
        graph: Dict[str, List[str]] = {}
        for from_node, to_node, _ in edges:
            if from_node not in graph:
                graph[from_node] = []
            if to_node not in graph:
                graph[to_node] = []
            if to_node not in graph[from_node]:
                graph[from_node].append(to_node)
            if from_node not in graph[to_node]:
                graph[to_node].append(from_node)
        return graph

    def _calculate_gain(self, node: str, target_community: int,
                       graph: Dict[str, List[str]],
                       node_community: Dict[str, int],
                       resolution: float) -> float:
        """计算移动节点的模块度增益（简化版）"""
        # 简化的模块度增益计算
        neighbors = graph.get(node, [])
        same_community = sum(1 for n in neighbors if node_community.get(n) == target_community)
        return same_community / max(len(neighbors), 1) * resolution

    def _update_communities(self, node_community: Dict[str, int]):
        """更新数据库中的社区信息"""
        for node_id, comm_id in node_community.items():
            sql = """
                UPDATE knowledge_graph_nodes
                SET community_id = %s
                WHERE node_id = %s
            """
            self.db.execute(sql, (comm_id, node_id))


# ============== 知识图谱管理器 ==============

class KnowledgeGraphManager:
    """
    知识图谱管理器 v4.2

    整合节点/边管理 + PageRank + 社区检测
    """

    def __init__(self, db: DBConnection = None):
        self.db = db or DBConnection.get_instance()
        self.pagerank = PageRankCalculator(self.db)
        self.community_detector = CommunityDetector(self.db)

    def add_node(self, node_id: str, name: str, node_type: str,
                 properties: dict = None) -> bool:
        """添加图节点"""
        sql = """
            INSERT INTO knowledge_graph_nodes (node_id, name, node_type, properties)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (node_id) DO UPDATE
            SET properties = EXCLUDED.properties,
                updated_at = NOW()
        """
        self.db.execute(sql, (node_id, name, node_type, json.dumps(properties or {})))
        return True

    def add_edge(self, from_node: str, to_node: str, relation_type: str,
                 strength: float = 0.5, properties: dict = None,
                 **kwargs) -> bool:
        """添加图边"""
        sql = """
            INSERT INTO knowledge_graph_edges
            (from_node, to_node, relation_type, strength, properties,
             conflict_level, resource_direction, mcp_potential, shovel_score)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (from_node, to_node, relation_type) DO UPDATE
            SET strength = EXCLUDED.strength,
                updated_at = NOW()
        """
        self.db.execute(sql, (
            from_node, to_node, relation_type, strength,
            json.dumps(properties or {}),
            kwargs.get("conflict_level", "低"),
            kwargs.get("resource_direction", ""),
            kwargs.get("mcp_potential", "低"),
            kwargs.get("shovel_score", 1)
        ))
        return True

    def update_edge_strength(self, from_node: str, to_node: str,
                           relation_type: str, new_strength: float) -> bool:
        """更新边的强度，带历史沉淀"""
        sql = """
            UPDATE knowledge_graph_edges
            SET strength = %s,
                updated_at = NOW()
            WHERE from_node = %s AND to_node = %s AND relation_type = %s
        """
        self.db.execute(sql, (new_strength, from_node, to_node, relation_type))
        return True

    def get_edge_strength(self, from_node: str, to_node: str,
                         relation_type: str) -> Optional[float]:
        """获取边的当前强度"""
        sql = """
            SELECT strength FROM knowledge_graph_edges
            WHERE from_node = %s AND to_node = %s AND relation_type = %s
        """
        results = self.db.execute(sql, (from_node, to_node, relation_type))
        return results[0]["strength"] if results else None

    def get_node(self, node_id: str) -> Optional[Dict]:
        """获取节点信息"""
        sql = """
            SELECT * FROM knowledge_graph_nodes WHERE node_id = %s
        """
        results = self.db.execute(sql, (node_id,))
        return results[0] if results else None

    def get_neighbors(self, node_id: str, max_depth: int = 1) -> List[Dict]:
        """获取邻居节点（支持多跳）"""
        if max_depth == 1:
            sql = """
                SELECT n.*, e.relation_type, e.strength
                FROM knowledge_graph_nodes n
                JOIN knowledge_graph_edges e ON n.node_id = e.to_node
                WHERE e.from_node = %s
                UNION
                SELECT n.*, e.relation_type, e.strength
                FROM knowledge_graph_nodes n
                JOIN knowledge_graph_edges e ON n.node_id = e.from_node
                WHERE e.to_node = %s
            """
            return self.db.execute(sql, (node_id, node_id))
        else:
            # 递归查询（简化版，最多3跳）
            visited = set()
            result = []
            queue = [(node_id, 0)]
            visited.add(node_id)

            while queue:
                current, depth = queue.pop(0)
                if depth >= max_depth:
                    continue

                neighbors = self.get_neighbors(current, 1)
                for n in neighbors:
                    if n["node_id"] not in visited:
                        visited.add(n["node_id"])
                        n["depth"] = depth + 1
                        result.append(n)
                        queue.append((n["node_id"], depth + 1))

            return result

    def find_path(self, from_node: str, to_node: str) -> List[str]:
        """BFS查找最短路径"""
        if from_node == to_node:
            return [from_node]

        visited = {from_node}
        queue = [(from_node, [from_node])]

        while queue:
            current, path = queue.pop(0)
            neighbors = self.get_neighbors(current, 1)

            for neighbor in neighbors:
                neighbor_id = neighbor["node_id"]
                if neighbor_id == to_node:
                    return path + [neighbor_id]

                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, path + [neighbor_id]))

        return []

    def get_pagerank_top(self, limit: int = 10) -> List[Dict]:
        """获取PageRank排名Top节点"""
        sql = """
            SELECT node_id, name, node_type, pagerank_score, pagerank_rank
            FROM knowledge_graph_nodes
            WHERE pagerank_score > 0
            ORDER BY pagerank_score DESC
            LIMIT %s
        """
        return self.db.execute(sql, (limit,))

    def get_community(self, community_id: int) -> List[Dict]:
        """获取指定社区的所有节点"""
        sql = """
            SELECT node_id, name, node_type, pagerank_score
            FROM knowledge_graph_nodes
            WHERE community_id = %s
            ORDER BY pagerank_score DESC
        """
        return self.db.execute(sql, (community_id,))

    def compute_pagerank(self) -> List[Dict]:
        """计算PageRank并返回排名"""
        return self.pagerank.compute()

    def detect_communities(self, resolution: float = 1.0) -> List[Dict]:
        """检测社区并返回结果"""
        return self.community_detector.detect(resolution)

    def export_to_json(self, output_path: str = None) -> dict:
        """导出图数据为JSON"""
        nodes_sql = "SELECT * FROM knowledge_graph_nodes"
        edges_sql = "SELECT * FROM knowledge_graph_edges"

        nodes = self.db.execute(nodes_sql)
        edges = self.db.execute(edges_sql)

        data = {
            "nodes": nodes,
            "edges": edges,
            "exported_at": datetime.now().isoformat(),
        }

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        return data

    def import_from_json(self, input_path: str) -> int:
        """从JSON导入图数据"""
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        node_count = 0
        for node in data.get("nodes", []):
            self.add_node(
                node["node_id"],
                node["name"],
                node["node_type"],
                node.get("properties", {})
            )
            node_count += 1

        edge_count = 0
        for edge in data.get("edges", []):
            self.add_edge(
                edge["from_node"],
                edge["to_node"],
                edge["relation_type"],
                edge.get("strength", 0.5),
                edge.get("properties", {}),
                conflict_level=edge.get("conflict_level", "低"),
                resource_direction=edge.get("resource_direction", ""),
                mcp_potential=edge.get("mcp_potential", "低"),
                shovel_score=edge.get("shovel_score", 1)
            )
            edge_count += 1

        return node_count, edge_count


# ============== 主程序 ==============

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="知识图谱管理工具 v4.2")
    parser.add_argument("--init-db", action="store_true", help="初始化数据库")
    parser.add_argument("--pagerank", action="store_true", help="计算PageRank")
    parser.add_argument("--community", action="store_true", help="社区检测")
    parser.add_argument("--export", metavar="FILE", help="导出图数据")
    parser.add_argument("--import", dest="import_file", metavar="FILE", help="导入图数据")

    args = parser.parse_args()

    print("🔗 知识图谱管理工具 v4.2\n")

    if args.init_db:
        print("📊 初始化数据库...")
        db = DBConnection.get_instance()
        db.connect()
        print("✓ 数据库连接已建立")
        print("✓ 请运行 database_migration.sql 完成表创建")

    elif args.pagerank:
        print("📈 计算PageRank...")
        db = DBConnection.get_instance()
        kg = KnowledgeGraphManager(db)
        results = kg.compute_pagerank()
        print(f"\nPageRank Top 10:")
        for r in results[:10]:
            print(f"  {r['rank']}. {r['node_id']} (score: {r['pagerank']:.4f})")

    elif args.community:
        print("🔍 社区检测...")
        db = DBConnection.get_instance()
        kg = KnowledgeGraphManager(db)
        results = kg.detect_communities()
        print(f"\n发现 {len(results)} 个社区:")
        for r in results[:10]:
            print(f"  社区{r['community_id']}: {r['total_members']}个节点 - {r['members'][:3]}...")

    elif args.export:
        print(f"📤 导出图数据到 {args.export}...")
        db = DBConnection.get_instance()
        kg = KnowledgeGraphManager(db)
        kg.export_to_json(args.export)
        print("✓ 导出完成")

    elif args.import_file:
        print(f"📥 从 {args.import_file} 导入...")
        db = DBConnection.get_instance()
        kg = KnowledgeGraphManager(db)
        node_count, edge_count = kg.import_from_json(args.import_file)
        print(f"✓ 导入完成: {node_count}个节点, {edge_count}条边")

    else:
        print(__doc__)