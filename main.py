"""
发现系统 v4.2 主程序
Discovery System Main — 数据基础设施升级版

整合所有模块：
1. 深度分析引擎 (DeepEcosystemMiner)
2. 知识图谱 (KnowledgeGraph)
3. 时序信号 (TimeSeriesSignals)
4. 语义搜索 (SemanticSearch)
5. 双写支持 (DualWrite)

使用方式：
python main.py --core OpenClaw --depth 3
python main.py --pagerank
python main.py --community
python main.py --status
"""

import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

import argparse
from datetime import datetime
from typing import Dict, List, Optional

# ============== 组件初始化 ==============

def init_components():
    """初始化所有组件"""
    from knowledge_graph import DBConnection, KnowledgeGraphManager
    from time_series_signals import TimeSeriesSignalManager
    from semantic_search import VectorSearchManager, EmbeddingGenerator
    from dual_write import DualWriteManager

    # 数据库连接
    db = DBConnection.get_instance()
    db.connect()

    # 知识图谱管理器
    kg = KnowledgeGraphManager(db)

    # 时序信号管理器
    signals = TimeSeriesSignalManager(db)

    # 向量搜索管理器
    embedding_gen = EmbeddingGenerator()
    search = VectorSearchManager(db, embedding_gen)

    # 双写管理器
    dual_write = DualWriteManager(kg, signals, search)

    return {
        "db": db,
        "kg": kg,
        "signals": signals,
        "search": search,
        "embedding_gen": embedding_gen,
        "dual_write": dual_write,
    }


# ============== 主分析流程 ==============

def run_discovery(core_node: str, depth: int = 3,
                  components: Dict = None) -> Dict:
    """
    运行发现流程

    Args:
        core_node: 核心节点名称
        depth: 发现深度
        components: 组件字典

    Returns:
        分析结果
    """
    if components is None:
        components = init_components()

    from ecological_chain.deep_miner import DeepEcosystemMiner

    print(f"\n🔍 开始深度发现: {core_node} (深度={depth})")
    print("=" * 60)

    # 1. 初始化深度分析引擎
    miner = DeepEcosystemMiner()
    miner._event_bus = None  # 禁用事件总线简化输出

    # 2. 执行发现
    start_time = datetime.now()
    result = miner.deep_discover(core_node, depth)
    elapsed = (datetime.now() - start_time).total_seconds()

    print(f"\n✓ 发现完成 (耗时: {elapsed:.2f}s)")
    print(f"  总节点数: {result.get_total_nodes()}")
    print(f"  总关系数: {len(result.relationships)}")
    print(f"  发现深度: {result.depth_reached}")

    # 3. 双写结果
    print("\n📦 写入数据...")
    dual_write = components["dual_write"]

    # 构建分析摘要
    analysis_summary = {
        "core_node": result.core_node,
        "depth_reached": result.depth_reached,
        "layer_summary": result.layer_summary,
        "total_nodes": result.get_total_nodes(),
        "total_relationships": len(result.relationships),
        "self_reflection": result.self_reflection,
    }

    # 写入发现结果
    dw_result = dual_write.write_discovery_result(
        core_node=core_node,
        analysis_result=analysis_summary,
        opportunities=result.opportunities
    )
    print(f"  发现结果: {'✓' if dw_result.success else '✗'}")

    # 写入节点
    node_count = 0
    for node_id, node in result.all_nodes.items():
        dw = dual_write.write_node(
            node_id, node.name, node.node_type.value,
            properties={"depth": node.depth, "parent": node.parent_id}
        )
        if dw.success:
            node_count += 1

    # 写入关系
    edge_count = 0
    for rel in result.relationships:
        dw = dual_write.write_edge(
            rel.node_a, rel.node_b, rel.relation_type, rel.strength,
            conflict_level=rel.conflict_level,
            mcp_potential=rel.mcp_potential,
            shovel_score=rel.shovel_score
        )
        if dw.success:
            edge_count += 1

    print(f"  节点写入: {node_count}")
    print(f"  边写入: {edge_count}")

    # 4. 写入向量嵌入
    print("\n🔢 生成向量嵌入...")
    search = components["search"]
    for opp in result.opportunities[:5]:  # 只嵌入Top5机会
        entity_id = f"opp_{core_node}_{opp.get('node_name', 'unknown')}"
        text = f"{opp.get('node_name', '')} {opp.get('shovel_form', '')} {opp.get('execution_tip', '')}"
        search.add_embedding(entity_id, opp.get('node_name', ''),
                           "opportunity", text, opp)
    print(f"  已嵌入 {min(5, len(result.opportunities))} 个机会")

    # 5. 写入时序信号
    print("\n📈 记录时序信号...")
    signals = components["signals"]
    signals.record_signal("discovery_system", core_node, "discoveries", 1)
    signals.record_signal("discovery_system", core_node, "nodes", result.get_total_nodes())
    signals.record_signal("discovery_system", core_node, "relationships", len(result.relationships))
    print("  ✓ 信号已记录")

    # 6. 返回结果
    return {
        "result": result,
        "discovery_result": dw_result,
        "node_count": node_count,
        "edge_count": edge_count,
        "elapsed_seconds": elapsed,
    }


# ============== PageRank计算 ==============

def run_pagerank(components: Dict = None):
    """计算PageRank"""
    if components is None:
        components = init_components()

    print("\n📈 计算PageRank...")
    kg = components["kg"]

    results = kg.compute_pagerank()
    print(f"\nPageRank Top 10:")
    for r in results[:10]:
        print(f"  {r['rank']:2d}. {r['node_id']:<30} (score: {r['pagerank']:.6f})")

    return results


# ============== 社区检测 ==============

def run_community_detection(components: Dict = None):
    """执行社区检测"""
    if components is None:
        components = init_components()

    print("\n🔍 社区检测...")
    kg = components["kg"]

    results = kg.detect_communities()
    print(f"\n发现 {len(results)} 个社区:")
    for r in results[:10]:
        print(f"  社区{r['community_id']:3d}: {r['total_members']:2d}个节点 " +
              f"平均强度:{r['avg_strength']:.2f}")
        print(f"    成员: {', '.join(r['members'][:5])}...")

    return results


# ============== 状态显示 ==============

def show_status(components: Dict = None):
    """显示系统状态"""
    if components is None:
        components = init_components()

    print("\n📊 系统状态")
    print("=" * 60)

    # 双写状态
    dw = components["dual_write"]
    status = dw.get_status()
    print("\n双写状态:")
    print(f"  JSON目录: {status['json_dir']}")
    print(f"  节点文件: {status['node_files']}")
    print(f"  边文件: {status['edge_files']}")
    print(f"  发现文件: {status['discovery_files']}")
    print(f"  数据库: {'✓ 已连接' if status['db_connected'] else '✗ 未连接'}")
    print(f"  信号系统: {'✓ 已连接' if status['signals_connected'] else '✗ 未连接'}")
    print(f"  向量搜索: {'✓ 已连接' if status['search_connected'] else '✗ 未连接'}")

    # 向量统计
    search = components["search"]
    stats = search.get_embedding_stats()
    if stats:
        print("\n向量嵌入:")
        print(f"  总数: {stats.get('total', 0)}")
        print(f"  类型数: {stats.get('types', 0)}")
        print(f"  平均维度: {stats.get('avg_dimension', 0):.0f}")


# ============== 主程序 ==============

def main():
    parser = argparse.ArgumentParser(
        description="发现系统 v4.2 - 数据基础设施升级版",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--core", default="OpenClaw", help="核心节点名称")
    parser.add_argument("--depth", type=int, default=3, help="发现深度 (1-5)")
    parser.add_argument("--pagerank", action="store_true", help="计算PageRank")
    parser.add_argument("--community", action="store_true", help="社区检测")
    parser.add_argument("--status", action="store_true", help="显示状态")
    parser.add_argument("--all", action="store_true", help="运行完整流程")
    parser.add_argument("--skip-db", action="store_true", help="跳过数据库操作")

    args = parser.parse_args()

    print("""
╔══════════════════════════════════════════════════════════════╗
║                 发现系统 v4.2                              ║
║          数据基础设施升级 (PostgreSQL + TimescaleDB)        ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # 根据参数决定执行流程
    if args.skip_db:
        print("⚠️ 数据库操作已跳过")
        components = None
    else:
        print("🔗 初始化组件...")
        try:
            components = init_components()
            print("✓ 组件初始化完成")
        except Exception as e:
            print(f"⚠️ 组件初始化失败: {e}")
            print("  使用演示模式")
            components = None

    if args.status:
        show_status(components)
        return

    if args.pagerank:
        run_pagerank(components)
        return

    if args.community:
        run_community_detection(components)
        return

    if args.all or args.core:
        # 运行发现
        result = run_discovery(args.core, args.depth, components)

        # 如果是完整流程，额外运行PageRank和社区检测
        if args.all and components:
            print("\n" + "=" * 60)
            print("📊 后续分析")
            print("=" * 60)

            run_pagerank(components)
            run_community_detection(components)
            show_status(components)

        print("\n" + "=" * 60)
        print("✅ 处理完成")
        print("=" * 60)
        return

    # 默认：显示帮助
    parser.print_help()


if __name__ == "__main__":
    main()