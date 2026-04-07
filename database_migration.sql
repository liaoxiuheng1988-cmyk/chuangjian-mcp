-- ============================================================
-- 发现系统 v4.2 数据库迁移脚本
-- TimescaleDB + pgvector 扩展安装
-- ============================================================
-- 运行方式: psql -d your_database -f database_migration.sql
-- ============================================================

-- 1. 安装扩展
CREATE EXTENSION IF NOT EXISTS pgvector CASCADE;
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- 2. 创建时序信号表 (signal_history)
-- ============================================================
CREATE TABLE IF NOT EXISTS signal_history (
    id BIGSERIAL PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,          -- 信号来源平台: github, reddit, twitter, etc.
    entity VARCHAR(200) NOT NULL,           -- 实体名称: 项目名/公司名
    metric VARCHAR(50) NOT NULL,           -- 指标类型: stars, forks, issues, upvotes, likes
    value FLOAT NOT NULL,                   -- 指标值
    value_delta FLOAT,                      -- 相对上次的变化量
    timestamp TIMESTAMPTZ NOT NULL,         -- 信号时间戳
    metadata JSONB DEFAULT '{}',           -- 额外元数据
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 创建时序超表
SELECT create_hypertable('signal_history', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_signal_entity ON signal_history (entity, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_signal_platform_metric ON signal_history (platform, metric, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_signal_entity_metric ON signal_history (entity, metric, timestamp DESC);

-- 3. 创建实体向量表 (entity_embeddings)
-- ============================================================
CREATE TABLE IF NOT EXISTS entity_embeddings (
    id BIGSERIAL PRIMARY KEY,
    entity_id VARCHAR(100) NOT NULL UNIQUE,  -- 实体唯一ID
    entity_name VARCHAR(200) NOT NULL,        -- 实体名称
    entity_type VARCHAR(50),                  -- 实体类型: project, tool, platform, etc.
    embedding VECTOR(768),                   -- 向量嵌入 (sentence-transformers default 768)
    dimension INTEGER DEFAULT 768,           -- 向量维度
    model_name VARCHAR(100),                 -- 生成向量的模型名
    metadata JSONB DEFAULT '{}',             -- 额外元数据
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 创建向量相似度索引 (HNSW)
CREATE INDEX IF NOT EXISTS idx_embedding_hnsw ON entity_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- 创建GIN索引用于JSONB查询
CREATE INDEX IF NOT EXISTS idx_entity_metadata ON entity_embeddings USING GIN (metadata);

-- 4. 创建知识图谱节点表 (knowledge_graph_nodes)
-- ============================================================
CREATE TABLE IF NOT EXISTS knowledge_graph_nodes (
    id BIGSERIAL PRIMARY KEY,
    node_id VARCHAR(100) NOT NULL UNIQUE,    -- 节点唯一ID
    name VARCHAR(200) NOT NULL,               -- 节点名称
    node_type VARCHAR(50) NOT NULL,          -- 节点类型: CORE, INFRASTRUCTURE, SERVICE, DERIVATIVE, etc.
    properties JSONB DEFAULT '{}',            -- 节点属性
    -- PageRank相关
    pagerank_score FLOAT DEFAULT 0.0,        -- PageRank分数
    pagerank_rank INTEGER,                    -- PageRank排名
    -- 社区检测相关
    community_id INTEGER,                      -- 社区ID
    community_name VARCHAR(100),               -- 社区名称
    -- 统计
    in_degree INTEGER DEFAULT 0,              -- 入度
    out_degree INTEGER DEFAULT 0,             -- 出度
    metadata JSONB DEFAULT '{}',              -- 额外元数据
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_kg_node_type ON knowledge_graph_nodes (node_type);
CREATE INDEX IF NOT EXISTS idx_kg_node_pagerank ON knowledge_graph_nodes (pagerank_score DESC);
CREATE INDEX IF NOT EXISTS idx_kg_node_community ON knowledge_graph_nodes (community_id);
CREATE INDEX IF NOT EXISTS idx_kg_node_metadata ON knowledge_graph_nodes USING GIN (properties);

-- 5. 创建知识图谱边表 (knowledge_graph_edges)
-- ============================================================
CREATE TABLE IF NOT EXISTS knowledge_graph_edges (
    id BIGSERIAL PRIMARY KEY,
    from_node VARCHAR(100) NOT NULL,          -- 起始节点ID
    to_node VARCHAR(100) NOT NULL,           -- 目标节点ID
    relation_type VARCHAR(50) NOT NULL,       -- 关系类型: SUPPLY, DEPENDENCY, COMPETITION, etc.
    strength FLOAT DEFAULT 0.5,              -- 关系强度 0-1
    properties JSONB DEFAULT '{}',            -- 关系属性
    -- 增强属性
    conflict_level VARCHAR(10) DEFAULT '低', -- 利益冲突程度: 高/中/低
    resource_direction VARCHAR(20),           -- 资源流向: upstream/downstream
    mcp_potential VARCHAR(10) DEFAULT '低',  -- MCP集成潜力: 高/中/低
    shovel_score INTEGER DEFAULT 1,           -- 卖铲子机会评分 1-10
    metadata JSONB DEFAULT '{}',              -- 额外元数据
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    -- 约束
    UNIQUE (from_node, to_node, relation_type)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_kg_edge_from ON knowledge_graph_edges (from_node);
CREATE INDEX IF NOT EXISTS idx_kg_edge_to ON knowledge_graph_edges (to_node);
CREATE INDEX IF NOT EXISTS idx_kg_edge_type ON knowledge_graph_edges (relation_type);
CREATE INDEX IF NOT EXISTS idx_kg_edge_strength ON knowledge_graph_edges (strength DESC);

-- 6. 创建连续聚合视图 (用于斜率计算)
-- ============================================================
-- 7日信号斜率
CREATE MATERIALIZED VIEW IF NOT EXISTS signal_slope_7d AS
SELECT
    entity,
    metric,
    platform,
    time_bucket('1 day', timestamp) AS bucket,
    AVG(value) as avg_value,
    COUNT(*) as sample_count
FROM signal_history
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY entity, metric, platform, time_bucket('1 day', timestamp);

CREATE UNIQUE INDEX IF NOT EXISTS idx_slope_7d ON signal_slope_7d (entity, metric, platform, bucket);

-- 30日信号斜率
CREATE MATERIALIZED VIEW IF NOT EXISTS signal_slope_30d AS
SELECT
    entity,
    metric,
    platform,
    time_bucket('1 day', timestamp) AS bucket,
    AVG(value) as avg_value,
    COUNT(*) as sample_count
FROM signal_history
WHERE timestamp > NOW() - INTERVAL '30 days'
GROUP BY entity, metric, platform, time_bucket('1 day', timestamp);

CREATE UNIQUE INDEX IF NOT EXISTS idx_slope_30d ON signal_slope_30d (entity, metric, platform, bucket);

-- 7. 创建函数和触发器
-- ============================================================
-- 自动更新 updated_at 触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER update_entity_embeddings_updated_at
    BEFORE UPDATE ON entity_embeddings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER update_kg_nodes_updated_at
    BEFORE UPDATE ON knowledge_graph_nodes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER update_kg_edges_updated_at
    BEFORE UPDATE ON knowledge_graph_edges
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 8. 权限设置 (根据需要调整)
-- ============================================================
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO your_app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO your_app_user;

-- 9. 验证安装
-- ============================================================
SELECT 'TimescaleDB extension' AS component,
       extname AS name,
       extversion AS version
FROM pg_extension
WHERE extname IN ('timescaledb', 'vector');

-- 10. 显示创建完成的表
-- ============================================================
\dt knowledge_graph_*
\dt signal_history
\dt entity_embeddings

-- ============================================================
-- 迁移完成
-- ============================================================
-- 下一步:
-- 1. 运行 python3 main.py 初始化数据
-- 2. 执行 SELECT compute_pagerank(); 计算PageRank
-- 3. 执行 SELECT detect_communities(); 进行社区检测
-- ============================================================