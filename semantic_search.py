"""
向量嵌入与语义搜索 v4.2
Vector Embeddings & Semantic Search — sentence-transformers + pgvector

核心功能：
1. sentence-transformers生成机会描述向量
2. 存入entity_embeddings表
3. 向量相似度搜索（替代BM25）
4. 语义聚类

使用方式：
python semantic_search.py --embed "OpenClaw生态机会分析"
python semantic_search.py --search "AI编程工具" --top 5
python semantic_search.py --cluster
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

# ============== 向量嵌入生成器 ==============

class EmbeddingGenerator:
    """
    向量嵌入生成器

    使用sentence-transformers生成文本向量
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self.dimension = 384  # all-MiniLM-L6-v2的维度

    def load_model(self):
        """加载模型"""
        if self.model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
            print(f"✓ 模型加载成功: {self.model_name} (dim={self.dimension})")
        except ImportError:
            print("⚠️ sentence-transformers 未安装，使用模拟模式")
            print("  安装命令: pip install sentence-transformers")
            self.model = None

    def encode(self, texts: List[str]) -> List[List[float]]:
        """
        生成文本向量

        Args:
            texts: 文本列表

        Returns:
            向量列表
        """
        self.load_model()

        if self.model is None:
            # 模拟模式：返回随机向量
            import random
            return [[random.random() for _ in range(self.dimension)] for _ in texts]

        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def encode_single(self, text: str) -> List[float]:
        """生成单个文本向量"""
        return self.encode([text])[0]


# ============== 向量搜索管理器 ==============

@dataclass
class SearchResult:
    """搜索结果"""
    entity_id: str
    entity_name: str
    similarity: float
    metadata: dict


class VectorSearchManager:
    """
    向量搜索管理器 v4.2

    1. 存储实体向量到PostgreSQL
    2. 向量相似度搜索
    3. 语义聚类
    """

    def __init__(self, db=None, embedding_generator: EmbeddingGenerator = None):
        self.db = db
        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        self.model_name = self.embedding_generator.model_name

    def add_embedding(self, entity_id: str, entity_name: str,
                    entity_type: str = "opportunity",
                    text_to_embed: str = None,
                    metadata: dict = None) -> bool:
        """
        添加实体向量

        Args:
            entity_id: 实体ID
            entity_name: 实体名称
            entity_type: 实体类型
            text_to_embed: 用于生成向量的文本（如果为None，用entity_name）
            metadata: 额外元数据

        Returns:
            是否成功
        """
        if self.db is None:
            print("⚠️ 数据库未连接")
            return False

        # 生成向量
        text = text_to_embed or entity_name
        vector = self.embedding_generator.encode_single(text)

        # 存入数据库
        sql = """
            INSERT INTO entity_embeddings
            (entity_id, entity_name, entity_type, embedding, dimension, model_name, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (entity_id) DO UPDATE
            SET embedding = EXCLUDED.embedding,
                entity_name = EXCLUDED.entity_name,
                metadata = EXCLUDED.metadata,
                updated_at = NOW()
        """
        self.db.execute(sql, (
            entity_id, entity_name, entity_type,
            json.dumps(vector),  # pgvector接受JSON数组
            self.embedding_generator.dimension,
            self.model_name,
            json.dumps(metadata or {})
        ))
        return True

    def search_similar(self, query: str, top_k: int = 5,
                      entity_type: str = None,
                      min_similarity: float = 0.0) -> List[SearchResult]:
        """
        语义搜索相似实体

        Args:
            query: 查询文本
            top_k: 返回数量
            entity_type: 过滤实体类型
            min_similarity: 最低相似度

        Returns:
            SearchResult列表
        """
        if self.db is None:
            return []

        # 生成查询向量
        query_vector = self.embedding_generator.encode_single(query)

        # 构建SQL（使用cosine相似度）
        sql = """
            SELECT
                entity_id,
                entity_name,
                entity_type,
                metadata,
                1 - (embedding <=> %s) AS similarity
            FROM entity_embeddings
            WHERE 1=1
        """
        params = [json.dumps(query_vector)]

        if entity_type:
            sql += " AND entity_type = %s"
            params.append(entity_type)

        sql += """
            ORDER BY embedding <=> %s
            LIMIT %s
        """
        params.append(json.dumps(query_vector))
        params.append(top_k)

        results = self.db.execute(sql, tuple(params))

        search_results = []
        for r in results:
            similarity = r.get("similarity", 0.0)
            if similarity >= min_similarity:
                search_results.append(SearchResult(
                    entity_id=r["entity_id"],
                    entity_name=r["entity_name"],
                    similarity=similarity,
                    metadata=r.get("metadata", {})
                ))

        return search_results

    def search_hybrid(self, query: str, keyword_filter: str = None,
                     top_k: int = 5) -> List[SearchResult]:
        """
        混合搜索（向量 + 关键词）

        Args:
            query: 查询文本
            keyword_filter: 关键词过滤
            top_k: 返回数量

        Returns:
            SearchResult列表
        """
        if self.db is None:
            return []

        # 生成查询向量
        query_vector = self.embedding_generator.encode_single(query)

        sql = """
            SELECT
                entity_id,
                entity_name,
                entity_type,
                metadata,
                1 - (embedding <=> %s) AS vector_similarity
            FROM entity_embeddings
            WHERE 1=1
        """
        params = [json.dumps(query_vector)]

        if keyword_filter:
            sql += " AND entity_name LIKE %s"
            params.append(f"%{keyword_filter}%")

        sql += """
            ORDER BY vector_similarity DESC
            LIMIT %s
        """
        params.append(top_k)

        results = self.db.execute(sql, tuple(params))

        return [
            SearchResult(
                entity_id=r["entity_id"],
                entity_name=r["entity_name"],
                similarity=r.get("vector_similarity", 0.0),
                metadata=r.get("metadata", {})
            )
            for r in results
        ]

    def cluster_entities(self, entity_type: str = None,
                        min_similarity: float = 0.7) -> List[List[str]]:
        """
        语义聚类

        使用简单的层次聚类
        """
        if self.db is None:
            return []

        # 获取所有实体向量
        sql = "SELECT entity_id, entity_name, embedding FROM entity_embeddings"
        params = []

        if entity_type:
            sql += " WHERE entity_type = %s"
            params.append(entity_type)

        results = self.db.execute(sql, tuple(params))

        if not results:
            return []

        # 简化的聚类：基于相似度阈值
        clusters: List[List[str]] = []
        assigned = set()

        for r in results:
            entity_id = r["entity_id"]
            if entity_id in assigned:
                continue

            # 创建新簇
            cluster = [entity_id]
            assigned.add(entity_id)

            # 找相似实体
            for other in results:
                other_id = other["entity_id"]
                if other_id in assigned:
                    continue

                # 计算相似度
                sim = self._cosine_similarity(
                    json.loads(r["embedding"]),
                    json.loads(other["embedding"])
                )

                if sim >= min_similarity:
                    cluster.append(other_id)
                    assigned.add(other_id)

            clusters.append(cluster)

        return clusters

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def get_embedding_stats(self) -> Dict:
        """获取嵌入统计"""
        if self.db is None:
            return {}

        sql = """
            SELECT
                COUNT(*) as total,
                COUNT(DISTINCT entity_type) as types,
                AVG(dimension) as avg_dimension
            FROM entity_embeddings
        """
        results = self.db.execute(sql)
        return results[0] if results else {}


# ============== 主程序 ==============

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="语义搜索工具 v4.2")
    parser.add_argument("--embed", metavar="TEXT", help="生成嵌入向量")
    parser.add_argument("--search", metavar="QUERY", help="搜索相似实体")
    parser.add_argument("--top", type=int, default=5, help="返回数量")
    parser.add_argument("--cluster", action="store_true", help="执行聚类")
    parser.add_argument("--stats", action="store_true", help="显示统计")
    parser.add_argument("--demo", action="store_true", help="演示模式（不需DB）")

    args = parser.parse_args()

    print("🔍 语义搜索工具 v4.2\n")

    # 初始化组件
    db = None
    if not args.demo:
        try:
            from knowledge_graph import DBConnection
            db = DBConnection.get_instance()
            db.connect()
        except Exception as e:
            print(f"⚠️ 数据库连接失败: {e}")
            print("  使用演示模式")
            args.demo = True

    embedding_gen = EmbeddingGenerator()
    search_mgr = VectorSearchManager(db, embedding_gen)

    if args.embed:
        print(f"📝 生成嵌入: {args.embed[:50]}...")
        vector = embedding_gen.encode_single(args.embed)
        print(f"✓ 向量维度: {len(vector)}")
        print(f"  前5维: {vector[:5]}")

        if db:
            # 存入数据库
            entity_id = f"demo_{uuid.uuid4().hex[:8]}"
            success = search_mgr.add_embedding(
                entity_id, args.embed[:30], "demo",
                args.embed
            )
            print(f"{'✓' if success else '⚠️'} 已存储到数据库" if success else "")

    elif args.search:
        print(f"🔎 搜索: {args.search}")
        results = search_mgr.search_similar(args.search, top_k=args.top)
        print(f"\n找到 {len(results)} 个结果:")
        for i, r in enumerate(results, 1):
            print(f"  {i}. {r.entity_name} (相似度: {r.similarity:.4f})")

    elif args.cluster:
        print("🔗 执行语义聚类...")
        clusters = search_mgr.cluster_entities()
        print(f"\n发现 {len(clusters)} 个簇:")
        for i, cluster in enumerate(clusters[:10], 1):
            print(f"  簇{i}: {len(cluster)}个实体 - {cluster[:3]}...")

    elif args.stats:
        print("📊 嵌入统计:")
        stats = search_mgr.get_embedding_stats()
        for k, v in stats.items():
            print(f"  {k}: {v}")

    elif args.demo:
        # 演示模式
        print("🎯 演示: 语义搜索")
        test_queries = [
            "AI编程助手工具",
            "开源大模型",
            "开发者工作流自动化",
        ]
        for q in test_queries:
            vector = embedding_gen.encode_single(q)
            print(f"\n  查询: {q}")
            print(f"    向量维度: {len(vector)}")

        print("\n✓ 演示完成")
        print("  提示: 使用 --demo 模式不需要数据库连接")

    else:
        print(__doc__)