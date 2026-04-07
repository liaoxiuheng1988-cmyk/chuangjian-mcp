"""
发现系统监控服务器 v1.0
Discovery System Monitoring Server

Flask API + HTML Dashboard for monitoring the discovery system

运行方式：
python3 monitoring_server.py
然后打开 http://localhost:5188

API端点：
- GET /              → HTML Dashboard
- GET /api/status   → 自进化系统状态
- GET /api/weights  → 维度权重数据
- GET /api/weights-history → 权重历史
- GET /api/events   → 事件历史
- GET /api/execution → 执行反馈统计
- GET /api/modules   → 各模块状态
- POST /api/reset-history → 重置历史数据（调试用）
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict
from flask import Flask, jsonify, render_template_string, send_file, request

# ============== 配置 ==============

BASE_DIR = Path("/home/admin1/aiagent/代理知识库/我的/opportunity_discovery")
STATE_FILE = BASE_DIR / "self_evolution_state.json"
LOGS_DIR = BASE_DIR / "logs"
WEIGHTS_HISTORY_FILE = BASE_DIR / "weights_history.json"
EVENTS_HISTORY_FILE = BASE_DIR / "events_history.json"

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# ============== 辅助函数 ==============

def load_json(filepath: Path, default=None):
    """加载 JSON 文件"""
    if default is None:
        default = {}
    try:
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return default


def save_json(filepath: Path, data):
    """保存 JSON 文件"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_state() -> dict:
    """获取自进化系统状态"""
    state = load_json(STATE_FILE, {})

    # 解析维度权重
    dimension_weights = {}
    if "dimension_weights" in state:
        for k, v in state["dimension_weights"].items():
            dimension_weights[k] = {
                "current": v.get("current_weight", 1.0),
                "base": v.get("base_weight", 1.0),
                "adjustments": v.get("adjustment_count", 0)
            }

    # 解析 KillChain 阈值
    killchain_thresholds = {}
    if "killchain_thresholds" in state:
        for k, v in state["killchain_thresholds"].items():
            killchain_thresholds[k] = {
                "current": v.get("current_threshold", 0),
                "base": v.get("base_threshold", 0)
            }

    # 解析模式置信度
    pattern_confidence = {}
    if "pattern_confidence" in state:
        for k, v in state["pattern_confidence"].items():
            pattern_confidence[k] = {
                "current": v.get("current_confidence", 0),
                "base": v.get("base_confidence", 0)
            }

    return {
        "state": state.get("state", "未知"),
        "last_learning_at": state.get("last_learning_at", ""),
        "dimension_weights": dimension_weights,
        "killchain_thresholds": killchain_thresholds,
        "pattern_confidence": pattern_confidence,
        "evolution_state": state
    }


def get_weights_history() -> List[dict]:
    """获取权重历史"""
    return load_json(WEIGHTS_HISTORY_FILE, [])


def get_events_history(limit: int = 100) -> List[dict]:
    """获取事件历史"""
    return load_json(EVENTS_HISTORY_FILE, [])[-limit:]


def get_execution_stats() -> dict:
    """获取执行反馈统计"""
    stats = {
        "total_runs": 0,
        "by_status": {},
        "by_node": {},
        "recent_failures": [],
        "success_rate": 0.0
    }

    if not LOGS_DIR.exists():
        return stats

    # 读取最近的日志文件
    log_files = sorted(LOGS_DIR.glob("feedback_*.log"))[-7:]  # 最近7天

    all_entries = []
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        all_entries.append(entry)
                    except:
                        continue
        except:
            continue

    stats["total_runs"] = len(all_entries)

    # 按状态统计
    for entry in all_entries:
        status = entry.get("status", "未知")
        stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

    # 按节点统计
    for entry in all_entries:
        node = entry.get("node", "未知")
        stats["by_node"][node] = stats["by_node"].get(node, 0) + 1

    # 最近失败
    failures = [e for e in all_entries if e.get("status") in ["失败", "FAILED"]]
    stats["recent_failures"] = failures[-10:]

    # 计算成功率
    completed = sum(1 for e in all_entries if e.get("status") in ["已完成", "COMPLETED"])
    if stats["total_runs"] > 0:
        stats["success_rate"] = completed / stats["total_runs"]

    return stats


# ============== v4.3 系统状态 ==============

def get_causal_stats() -> dict:
    """获取因果发现引擎状态"""
    try:
        from causal_engine import PCAlgorithm, CausalFilter, SCurvePredictor
        return {
            "status": "active",
            "algorithm": "PC Algorithm Simplified",
            "stages": ["引入期", "加速期", "成熟期", "衰退期"],
            "description": "因果发现 + S曲线预测"
        }
    except ImportError:
        return {"status": "unavailable", "error": "模块未安装"}


def get_threshold_monitor_stats() -> dict:
    """获取阈值监控状态"""
    try:
        from threshold_monitor import ThresholdMonitor, SIGNAL_THRESHOLDS
        import json as json_mod
        from pathlib import Path

        state_file = Path("/home/admin1/aiagent/代理知识库/我的/opportunity_discovery/threshold_monitor_state.json")
        alerts = []

        if state_file.exists():
            try:
                with open(state_file) as f:
                    data = json_mod.load(f)
                    prev_values = data.get("previous_values", {})
                    alerts = [
                        {"entity": k.split(":")[0], "metric": k.split(":")[1], "value": v.get("value")}
                        for k, v in prev_values.items() if v
                    ][:10]
            except:
                pass

        return {
            "status": "active",
            "thresholds": SIGNAL_THRESHOLDS,
            "monitored_count": len(alerts),
            "recent_alerts": alerts
        }
    except ImportError:
        return {"status": "unavailable", "error": "模块未安装"}


def get_self_evolution_stats() -> dict:
    """获取自进化系统状态"""
    try:
        from enhanced_engine.self_evolution import SelfEvolutionManager
        import json as json_mod
        from pathlib import Path

        knowledge_file = Path("/home/admin1/aiagent/代理知识库/我的/opportunity_discovery/self_evolution_knowledge.json")
        bundles_file = Path("/home/admin1/aiagent/代理知识库/我的/opportunity_discovery/compressed_bundles.json")

        knowledge_count = 0
        bundles_count = 0

        if knowledge_file.exists():
            try:
                with open(knowledge_file) as f:
                    data = json_mod.load(f)
                    knowledge_count = len(data)
            except:
                pass

        if bundles_file.exists():
            try:
                with open(bundles_file) as f:
                    data = json_mod.load(f)
                    bundles_count = len(data)
            except:
                pass

        return {
            "status": "active",
            "knowledge_items": knowledge_count,
            "compressed_bundles": bundles_count,
            "description": "知识压缩 + 遗忘机制"
        }
    except ImportError:
        return {"status": "unavailable", "error": "模块未安装"}


def get_data_retention_stats() -> dict:
    """获取数据保留策略状态"""
    from data_retention import RETENTION
    return {
        "status": "active",
        "retention_policy": {
            "signal_history_days": RETENTION["signal_history"]["raw_retention_days"],
            "embeddings_max": RETENTION["entity_embeddings"]["max_count"],
            "feedback_days": RETENTION["execution_feedback"]["raw_retention_days"]
        },
        "description": "数据滚动删除策略"
    }


def get_v43_system_status() -> dict:
    """获取 v4.3 完整系统状态"""
    return {
        "version": "v4.3",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "causal_engine": get_causal_stats(),
            "threshold_monitor": get_threshold_monitor_stats(),
            "self_evolution": get_self_evolution_stats(),
            "data_retention": get_data_retention_stats()
        }
    }


# ============== 权重历史记录 ==============

def record_weights_snapshot():
    """记录当前权重快照到历史"""
    state = load_json(STATE_FILE, {})
    if not state.get("dimension_weights"):
        return

    history = get_weights_history()

    snapshot = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "weights": {}
    }

    for k, v in state.get("dimension_weights", {}).items():
        snapshot["weights"][k] = v.get("current_weight", 1.0)

    history.append(snapshot)

    # 只保留最近100条
    if len(history) > 100:
        history = history[-100:]

    save_json(WEIGHTS_HISTORY_FILE, history)


def record_event_to_history(event_type: str, data: dict):
    """记录事件到历史"""
    history = get_events_history(limit=1000)

    event = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": event_type,
        "data": data
    }

    history.append(event)

    # 只保留最近1000条
    if len(history) > 1000:
        history = history[-1000:]

    save_json(EVENTS_HISTORY_FILE, history)


def get_projects() -> dict:
    """获取已发现的项目"""
    projects_dir = BASE_DIR / "discovered_projects"
    if not projects_dir.exists():
        return {"count": 0, "projects": []}

    # 读取最新的项目文件
    project_files = sorted(projects_dir.glob("projects_*.json"))
    if not project_files:
        return {"count": 0, "projects": []}

    latest_file = project_files[-1]
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except Exception:
        return {"count": 0, "projects": []}


# ============== Flask 路由 ==============

@app.route('/')
def index():
    """返回 HTML Dashboard"""
    return render_template_string(DASHBOARD_HTML)


@app.route('/api/status')
def api_status():
    """自进化系统状态"""
    return jsonify(get_state())


@app.route('/api/weights')
def api_weights():
    """维度权重数据（简化格式）"""
    state = get_state()
    weights = state.get("dimension_weights", {})

    # 转换为前端友好格式
    result = {
        "labels": list(weights.keys()),
        "datasets": [{
            "label": "当前权重",
            "data": [w.get("current", 1.0) for w in weights.values()]
        }]
    }
    return jsonify(result)


@app.route('/api/weights-history')
def api_weights_history():
    """权重历史趋势"""
    history = get_weights_history()

    # 转换为 Chart.js 格式
    labels = [h["timestamp"][:16] for h in history]  # 只显示到分钟

    datasets = defaultdict(lambda: {"label": "", "data": []})

    for h in history:
        for dim, weight in h.get("weights", {}).items():
            datasets[dim]["label"] = dim
            datasets[dim]["data"].append(weight)

    return jsonify({
        "labels": labels,
        "datasets": [datasets[dim] for dim in sorted(datasets.keys())]
    })


@app.route('/api/events')
def api_events():
    """事件历史"""
    limit = int(request.args.get('limit', 100)) if request.args.get('limit') else 100
    return jsonify(get_events_history(limit))


@app.route('/api/execution')
def api_execution():
    """执行反馈统计"""
    return jsonify(get_execution_stats())


@app.route('/api/projects')
def api_projects():
    """已发现项目列表"""
    return jsonify(get_projects())


@app.route('/api/modules')
def api_modules():
    """各模块状态"""
    return jsonify({
        "modules": [
            {"name": "MultiDimensionScanner", "status": "active", "description": "多维度扫描器"},
            {"name": "EnhancedDiscoveryEngine", "status": "active", "description": "增强发现引擎"},
            {"name": "DeepScanner", "status": "active", "description": "深度扫描器"},
            {"name": "EcosystemMiner", "status": "active", "description": "生态连锁挖掘"},
            {"name": "OpportunityValidator", "status": "active", "description": "机会验证器"},
            {"name": "StrategyGenerator", "status": "active", "description": "策略生成器"},
            {"name": "ExecutionPlanner", "status": "active", "description": "执行计划器"},
            {"name": "ExecutionEngine", "status": "active", "description": "执行引擎"},
            {"name": "SelfEvolutionManager", "status": "active", "description": "自进化管理器"},
            {"name": "EventBus", "status": "active", "description": "事件总线"}
        ],
        "event_types": [
            "validation.decision",
            "strategy.selected",
            "strategy.outcome",
            "task.completed",
            "milestone.reached",
            "scan.deep_completed",
            "plan.created",
            "checkpoint.completed"
        ]
    })


@app.route('/api/plans')
def api_plans():
    """执行计划列表"""
    try:
        from execution_persistence import ExecutionPlanPersistence
        persistence = ExecutionPlanPersistence()
        plans = persistence.list_plans()

        # 补充进度信息
        for plan in plans:
            progress = persistence.load_progress(plan.get('plan_id', ''))
            if progress:
                plan['progress'] = progress.get('progress', {})

        return jsonify({"plans": plans, "count": len(plans)})
    except Exception as e:
        return jsonify({"plans": [], "count": 0, "error": str(e)})


@app.route('/api/plans/<path:plan_name>')
def api_plan_detail(plan_name):
    """执行计划详情"""
    try:
        from execution_persistence import ExecutionPlanPersistence
        persistence = ExecutionPlanPersistence()

        # 查找计划
        plans = persistence.list_plans()
        plan_info = None
        for p in plans:
            if plan_name in p.get('plan_id', ''):
                plan_info = p
                break

        if not plan_info:
            return jsonify({"error": "计划不存在"}), 404

        # 加载完整计划
        plan = persistence.load_plan(plan_name)
        progress = persistence.load_progress(plan_name)
        checkpoints = persistence.list_checkpoints(plan_name)

        return jsonify({
            "plan": plan_info,
            "progress": progress,
            "checkpoints": [cp.to_dict() if hasattr(cp, 'to_dict') else cp for cp in checkpoints]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/plans/<path:plan_name>/tasks/<task_id>', methods=['PUT'])
def api_update_task(plan_name, task_id):
    """更新任务状态/进度"""
    try:
        from execution_engine.engine import ExecutionEngine, TaskStatus
        from execution_persistence import ExecutionPlanPersistence
        from evolution_event_bus import EventBus

        persistence = ExecutionPlanPersistence()
        event_bus = EventBus.get_instance()
        engine = ExecutionEngine(event_bus=event_bus, persistence=persistence)

        # 加载计划
        plan = persistence.load_plan(plan_name)
        if not plan:
            return jsonify({"error": "计划不存在"}), 404

        # 获取更新数据
        data = request.get_json()
        if not data:
            return jsonify({"error": "无更新数据"}), 400

        # 更新进度
        if 'progress' in data:
            engine.update_task_progress(plan, task_id, float(data['progress']), data.get('notes', ''))

        # 更新状态
        if 'status' in data:
            status_map = {
                "PENDING": TaskStatus.PENDING,
                "IN_PROGRESS": TaskStatus.IN_PROGRESS,
                "DONE": TaskStatus.DONE,
                "BLOCKED": TaskStatus.BLOCKED,
                "CANCELLED": TaskStatus.CANCELLED
            }
            status = status_map.get(data['status'], TaskStatus.PENDING)
            engine.update_task_status(plan, task_id, status, data.get('notes', ''))

        # 保存计划
        persistence.save_plan(plan)

        return jsonify({"status": "ok", "message": f"任务 {task_id} 已更新"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============== v4.3 API 端点 ==============

@app.route('/api/v43/status')
def api_v43_status():
    """v4.3 系统完整状态"""
    return jsonify(get_v43_system_status())


@app.route('/api/v43/causal')
def api_v43_causal():
    """因果发现引擎状态"""
    return jsonify(get_causal_stats())


@app.route('/api/v43/threshold')
def api_v43_threshold():
    """阈值监控状态"""
    return jsonify(get_threshold_monitor_stats())


@app.route('/api/v43/evolution')
def api_v43_evolution():
    """自进化系统状态"""
    return jsonify(get_self_evolution_stats())


@app.route('/api/v43/retention')
def api_v43_retention():
    """数据保留策略状态"""
    return jsonify(get_data_retention_stats())


@app.route('/api/reset-history', methods=['POST'])
def api_reset_history():
    """重置历史数据（调试用）"""
    save_json(WEIGHTS_HISTORY_FILE, [])
    save_json(EVENTS_HISTORY_FILE, [])
    return jsonify({"status": "ok", "message": "历史数据已重置"})


# ============== Dashboard HTML ==============

DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>发现系统监控面板 v4.3</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js"></script>
    <style>
        :root {
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-tertiary: #334155;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --accent-blue: #3b82f6;
            --accent-green: #22c55e;
            --accent-yellow: #eab308;
            --accent-red: #ef4444;
            --accent-purple: #8b5cf6;
            --accent-cyan: #06b6d4;
            --accent-orange: #f97316;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html { font-size: 14px; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Microsoft YaHei', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.5;
        }
        /* 响应式容器 */
        .container {
            max-width: 1600px;
            margin: 0 auto;
            padding: 16px;
        }
        /* 头部 */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
            padding: 16px 20px;
            background: var(--bg-secondary);
            border-radius: 12px;
            margin-bottom: 20px;
        }
        .header-title {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .header h1 {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-primary);
        }
        .version-badge {
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            background: linear-gradient(135deg, var(--accent-purple), var(--accent-blue));
            color: #fff;
        }
        .header-controls {
            display: flex;
            align-items: center;
            gap: 16px;
            flex-wrap: wrap;
        }
        .auto-refresh {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.875rem;
            color: var(--text-secondary);
            cursor: pointer;
        }
        .auto-refresh input { cursor: pointer; width: 16px; height: 16px; }
        .last-update {
            font-size: 0.75rem;
            color: var(--text-muted);
        }
        .refresh-btn {
            padding: 8px 20px;
            background: var(--accent-blue);
            color: #fff;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.875rem;
            font-weight: 500;
            transition: background 0.2s;
        }
        .refresh-btn:hover { background: #2563eb; }
        /* 统计卡片网格 */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 12px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 16px;
            text-align: center;
        }
        .stat-card.highlight {
            background: linear-gradient(135deg, var(--bg-secondary), #312e81);
        }
        .stat-value {
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 4px;
        }
        .stat-value.success { color: var(--accent-green); }
        .stat-value.warning { color: var(--accent-yellow); }
        .stat-value.error { color: var(--accent-red); }
        .stat-label {
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        /* 主网格布局 */
        .main-grid {
            display: grid;
            grid-template-columns: repeat(12, 1fr);
            gap: 16px;
        }
        .card {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 20px;
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        .card h2 {
            font-size: 0.875rem;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .card-subtitle {
            font-size: 0.7rem;
            color: var(--text-muted);
            margin-left: 8px;
        }
        /* 网格列跨度 */
        .col-3 { grid-column: span 3; }
        .col-4 { grid-column: span 4; }
        .col-6 { grid-column: span 6; }
        .col-12 { grid-column: span 12; }
        /* 图表容器 */
        .chart-container {
            position: relative;
            height: 220px;
        }
        /* 列表样式 */
        .list-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 12px;
            background: var(--bg-primary);
            border-radius: 8px;
            margin-bottom: 8px;
            font-size: 0.875rem;
        }
        .list-item:last-child { margin-bottom: 0; }
        .list-item-label { color: var(--text-secondary); }
        .list-item-value { font-weight: 600; color: var(--text-primary); }
        .badge {
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.7rem;
            font-weight: 600;
        }
        .badge-success { background: rgba(34, 197, 94, 0.2); color: var(--accent-green); }
        .badge-warning { background: rgba(234, 179, 8, 0.2); color: var(--accent-yellow); }
        .badge-error { background: rgba(239, 68, 68, 0.2); color: var(--accent-red); }
        .badge-info { background: rgba(59, 130, 246, 0.2); color: var(--accent-blue); }
        /* 进度条 */
        .progress-bar {
            height: 8px;
            background: var(--bg-primary);
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }
        .progress-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s;
        }
        /* v4.3 专用样式 */
        .v43-highlight {
            background: linear-gradient(135deg, var(--bg-secondary) 0%, #312e81 100%);
        }
        .v43-stats {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
        }
        .v43-stat {
            background: var(--bg-primary);
            border-radius: 8px;
            padding: 12px;
            text-align: center;
        }
        .v43-stat-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--accent-cyan);
        }
        .v43-stat-label {
            font-size: 0.7rem;
            color: var(--text-muted);
            margin-top: 4px;
        }
        /* 阶段标签 */
        .stage-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        .stage-tag {
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
        }
        .stage-intro { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
        .stage-accel { background: rgba(34, 197, 94, 0.2); color: #4ade80; }
        .stage-mature { background: rgba(234, 179, 8, 0.2); color: #facc15; }
        .stage-decline { background: rgba(239, 68, 68, 0.2); color: #f87171; }
        /* 阈值列表 */
        .threshold-list {
            max-height: 180px;
            overflow-y: auto;
        }
        .threshold-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 10px;
            background: var(--bg-primary);
            border-radius: 6px;
            margin-bottom: 6px;
            font-size: 0.8rem;
        }
        .threshold-item:last-child { margin-bottom: 0; }
        .threshold-metric { color: var(--text-secondary); }
        .threshold-value { color: var(--accent-green); font-weight: 600; }
        /* 时间线 */
        .timeline {
            max-height: 250px;
            overflow-y: auto;
        }
        .timeline-item {
            display: flex;
            gap: 12px;
            padding: 10px 0;
            border-bottom: 1px solid var(--bg-tertiary);
        }
        .timeline-item:last-child { border-bottom: none; }
        .timeline-time {
            font-size: 0.75rem;
            color: var(--text-muted);
            min-width: 70px;
        }
        .timeline-type {
            font-size: 0.7rem;
            padding: 2px 8px;
            border-radius: 4px;
            background: rgba(59, 130, 246, 0.2);
            color: var(--accent-blue);
            white-space: nowrap;
        }
        .timeline-data {
            font-size: 0.8rem;
            color: var(--text-secondary);
            word-break: break-all;
        }
        /* 项目卡片 */
        .projects-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 16px;
        }
        .project-card {
            background: var(--bg-primary);
            border-radius: 8px;
            padding: 16px;
            border-left: 4px solid var(--accent-blue);
        }
        .project-card.high { border-left-color: var(--accent-green); }
        .project-card.medium { border-left-color: var(--accent-yellow); }
        .project-name {
            font-size: 1rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 8px;
        }
        .project-desc {
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-bottom: 12px;
            line-height: 1.4;
        }
        .project-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }
        .project-tag {
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.7rem;
            background: var(--bg-tertiary);
            color: var(--text-secondary);
        }
        .project-score {
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.7rem;
            background: rgba(59, 130, 246, 0.2);
            color: var(--accent-blue);
            font-weight: 500;
        }
        /* 计划卡片 */
        .plans-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 16px;
        }
        .plan-card {
            background: var(--bg-primary);
            border-radius: 8px;
            padding: 16px;
            border-left: 4px solid var(--accent-green);
        }
        .plan-card.in-progress { border-left-color: var(--accent-blue); }
        .plan-card.blocked { border-left-color: var(--accent-red); }
        .plan-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        .plan-name {
            font-size: 1rem;
            font-weight: 600;
        }
        .plan-phase {
            font-size: 0.75rem;
            padding: 4px 10px;
            border-radius: 20px;
            background: var(--bg-tertiary);
            color: var(--text-secondary);
        }
        .plan-stats {
            display: flex;
            gap: 16px;
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 8px;
        }
        /* 滚动条样式 */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: var(--bg-primary); border-radius: 3px; }
        ::-webkit-scrollbar-thumb { background: var(--bg-tertiary); border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }
        /* 响应式断点 */
        @media (max-width: 1200px) {
            .col-3 { grid-column: span 6; }
            .col-4 { grid-column: span 6; }
        }
        @media (max-width: 900px) {
            .main-grid { grid-template-columns: repeat(6, 1fr); }
            .col-3, .col-4, .col-6 { grid-column: span 6; }
            .v43-stats { grid-template-columns: repeat(2, 1fr); }
        }
        @media (max-width: 600px) {
            html { font-size: 13px; }
            .container { padding: 12px; }
            .header { padding: 12px 16px; }
            .header h1 { font-size: 1.2rem; }
            .main-grid { grid-template-columns: 1fr; gap: 12px; }
            .col-3, .col-4, .col-6, .col-12 { grid-column: span 1; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); gap: 8px; }
            .v43-stats { grid-template-columns: repeat(2, 1fr); }
            .chart-container { height: 180px; }
            .projects-grid, .plans-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- 头部 -->
        <div class="header">
            <div class="header-title">
                <h1>发现系统监控面板</h1>
                <span class="version-badge">v4.3</span>
            </div>
            <div class="header-controls">
                <label class="auto-refresh">
                    <input type="checkbox" id="autoRefreshToggle" checked onchange="toggleAutoRefresh(this.checked)">
                    自动刷新
                </label>
                <span class="last-update" id="lastUpdate">--</span>
                <button class="refresh-btn" onclick="refreshAll()">刷新数据</button>
            </div>
        </div>

        <!-- 统计卡片 -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value" id="evoState">--</div>
                <div class="stat-label">系统状态</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="totalRuns">--</div>
                <div class="stat-label">总执行次数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value success" id="successRate">--</div>
                <div class="stat-label">成功率</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="adjustCount">--</div>
                <div class="stat-label">权重调整</div>
            </div>
            <div class="stat-card highlight">
                <div class="stat-value" id="v43KnowledgeCount">--</div>
                <div class="stat-label">知识项</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="v43AlertsCount">--</div>
                <div class="stat-label">阈值监控</div>
            </div>
        </div>

        <!-- 主网格 -->
        <div class="main-grid">
            <!-- v4.3 系统状态 -->
            <div class="card col-12 v43-highlight">
                <div class="card-header">
                    <h2>深度推理系统 <span class="card-subtitle">因果发现 · 阈值监控 · 自进化</span></h2>
                    <span class="last-update" id="v43UpdateTime">--</span>
                </div>
                <div class="v43-stats">
                    <div class="v43-stat">
                        <div class="v43-stat-value" id="v43KnowledgeCount2">--</div>
                        <div class="v43-stat-label">知识项</div>
                    </div>
                    <div class="v43-stat">
                        <div class="v43-stat-value" id="v43Bundles">--</div>
                        <div class="v43-stat-label">压缩包</div>
                    </div>
                    <div class="v43-stat">
                        <div class="v43-stat-value" id="v43CausalEdges">--</div>
                        <div class="v43-stat-label">因果边</div>
                    </div>
                    <div class="v43-stat">
                        <div class="v43-stat-value" id="v43RetentionDays">--</div>
                        <div class="v43-stat-label">数据保留</div>
                    </div>
                </div>
            </div>

            <!-- 维度权重雷达图 -->
            <div class="card col-6">
                <div class="card-header">
                    <h2>维度权重分布</h2>
                </div>
                <div class="chart-container">
                    <canvas id="weightsRadarChart"></canvas>
                </div>
            </div>

            <!-- 权重历史趋势 -->
            <div class="card col-6">
                <div class="card-header">
                    <h2>权重历史趋势</h2>
                </div>
                <div class="chart-container">
                    <canvas id="weightsHistoryChart"></canvas>
                </div>
            </div>

            <!-- 因果发现 -->
            <div class="card col-4">
                <div class="card-header">
                    <h2>因果发现 <span class="card-subtitle">PC Algorithm</span></h2>
                </div>
                <div id="v43CausalDetails">
                    <div style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 12px;">S曲线阶段预测</div>
                    <div class="stage-tags" id="v43StagesList"></div>
                </div>
            </div>

            <!-- 阈值监控 -->
            <div class="card col-4">
                <div class="card-header">
                    <h2>阈值监控 <span class="card-subtitle">实时预警</span></h2>
                </div>
                <div class="threshold-list" id="v43ThresholdList"></div>
            </div>

            <!-- 数据保留策略 -->
            <div class="card col-4">
                <div class="card-header">
                    <h2>数据策略 <span class="card-subtitle">滚动删除</span></h2>
                </div>
                <div id="v43RetentionDetails" style="font-size: 0.85rem;"></div>
            </div>

            <!-- KillChain 阈值 -->
            <div class="card col-6">
                <div class="card-header">
                    <h2>链路阈值</h2>
                </div>
                <div id="killchainThresholds"></div>
            </div>

            <!-- 连锁模式置信度 -->
            <div class="card col-6">
                <div class="card-header">
                    <h2>连锁模式置信度</h2>
                </div>
                <div id="patternConfidence"></div>
            </div>

            <!-- 模块状态 -->
            <div class="card col-4">
                <div class="card-header">
                    <h2>模块状态</h2>
                </div>
                <div id="moduleList"></div>
            </div>

            <!-- 事件时间线 -->
            <div class="card col-8">
                <div class="card-header">
                    <h2>最近事件</h2>
                </div>
                <div class="timeline" id="eventTimeline"></div>
            </div>

            <!-- 已发现项目 -->
            <div class="card col-12">
                <div class="card-header">
                    <h2>已发现项目</h2>
                </div>
                <div class="projects-grid" id="projectsGrid"></div>
            </div>

            <!-- 执行计划 -->
            <div class="card col-12">
                <div class="card-header">
                    <h2>执行计划</h2>
                </div>
                <div class="plans-grid" id="plansGrid"></div>
            </div>
        </div>
    </div>

    <script>
        let weightsRadarChart = null;
        let weightsHistoryChart = null;

        async function fetchJSON(url) {
            const resp = await fetch(url);
            return resp.json();
        }

        async function refreshAll() {
            await Promise.all([
                refreshStatus(),
                refreshExecution(),
                refreshWeights(),
                refreshWeightsHistory(),
                refreshModules(),
                refreshEvents(),
                refreshProjects(),
                refreshPlans(),
                refreshV43()
            ]);
            document.getElementById('lastUpdate').textContent = '更新: ' + new Date().toLocaleTimeString();
        }

        // v4.3 刷新函数
        async function refreshV43() {
            try {
                const [causal, threshold, evolution, retention] = await Promise.all([
                    fetchJSON('/api/v43/causal'),
                    fetchJSON('/api/v43/threshold'),
                    fetchJSON('/api/v43/evolution'),
                    fetchJSON('/api/v43/retention')
                ]);

                // 知识项
                const knowCount = evolution.knowledge_items || 0;
                document.getElementById('v43KnowledgeCount').textContent = knowCount;
                document.getElementById('v43KnowledgeCount2').textContent = knowCount;
                document.getElementById('v43Bundles').textContent = evolution.compressed_bundles || 0;

                // 阈值监控
                document.getElementById('v43AlertsCount').textContent = threshold.monitored_count || 0;

                // 渲染阈值列表
                const thresholds = threshold.thresholds || {};
                let threshHtml = '';
                Object.entries(thresholds).slice(0, 8).forEach(([key, val]) => {
                    const label = key.replace('_slope', '').replace('github', 'GitHub').replace('twitter', 'Twitter').replace('reddit', 'Reddit').replace('xiaohongshu', '小红书').replace('jobs', '招聘').replace('stars', '星标').replace('forks', '分叉').replace('mentions', '提及').replace('upvotes', '赞').replace('comments', '评').replace('likes', '赞').replace('retweets', '转').replace('notes', '笔记');
                    threshHtml += `
                        <div class="threshold-item">
                            <span class="threshold-metric">${label}</span>
                            <span class="threshold-value">${(val * 100).toFixed(0)}%</span>
                        </div>`;
                });
                document.getElementById('v43ThresholdList').innerHTML = threshHtml || '<div style="color:var(--text-muted);text-align:center;">暂无阈值配置</div>';

                // 因果发现 - S曲线阶段
                document.getElementById('v43CausalEdges').textContent = causal.stages ? causal.stages.length + ' 阶段' : '--';
                const stages = causal.stages || [];
                if (stages.length > 0) {
                    document.getElementById('v43StagesList').innerHTML = stages.map(s => {
                        const cls = s === '引入期' ? 'stage-intro' : s === '加速期' ? 'stage-accel' : s === '成熟期' ? 'stage-mature' : 'stage-decline';
                        return `<span class="stage-tag ${cls}">${s}</span>`;
                    }).join('');
                } else {
                    document.getElementById('v43StagesList').innerHTML = '<span style="color:var(--text-muted);">暂无数据</span>';
                }

                // 数据保留策略
                const policy = retention.retention_policy || {};
                document.getElementById('v43RetentionDays').textContent = (policy.signal_history_days || 365) + '天';
                document.getElementById('v43RetentionDetails').innerHTML = `
                    <div class="list-item">
                        <span class="list-item-label">信号历史</span>
                        <span class="list-item-value">${policy.signal_history_days || 365} 天</span>
                    </div>
                    <div class="list-item">
                        <span class="list-item-label">向量嵌入</span>
                        <span class="list-item-value">上限 ${((policy.embeddings_max || 30000) / 1000).toFixed(0)}k 条</span>
                    </div>
                    <div class="list-item">
                        <span class="list-item-label">执行反馈</span>
                        <span class="list-item-value">${policy.feedback_days || 90} 天</span>
                    </div>`;

                // 更新时间戳
                document.getElementById('v43UpdateTime').textContent = '更新: ' + new Date().toLocaleTimeString();

            } catch (e) {
                console.error('v4.3 refresh error:', e);
            }
        }

        async function refreshStatus() {
            const data = await fetchJSON('/api/status');
            document.getElementById('evoState').textContent = data.state || '--';

            let totalAdjust = 0;
            const weights = data.dimension_weights || {};
            Object.values(weights).forEach(w => totalAdjust += w.adjustments || 0);
            document.getElementById('adjustCount').textContent = totalAdjust;

            // 链路阈值
            const kc = data.killchain_thresholds || {};
            let kcHtml = '';
            Object.entries(kc).forEach(([key, val]) => {
                const bar = ((val.current / (val.base * 1.2)) * 100).toFixed(0);
                kcHtml += `
                    <div class="list-item">
                        <span class="list-item-label">${key}</span>
                        <span class="list-item-value">${val.current?.toFixed(1) || 0}</span>
                    </div>
                    <div class="progress-bar"><div class="progress-fill" style="width:${bar}%;background:var(--accent-yellow)"></div></div>`;
            });
            document.getElementById('killchainThresholds').innerHTML = kcHtml;

            // 连锁模式置信度
            const pc = data.pattern_confidence || {};
            let pcHtml = '';
            Object.entries(pc).forEach(([key, val]) => {
                const pct = ((val.current || 0) * 100).toFixed(0);
                const color = pct > 80 ? 'var(--accent-green)' : pct > 60 ? 'var(--accent-yellow)' : 'var(--accent-red)';
                pcHtml += `
                    <div class="list-item">
                        <span class="list-item-label">${key}</span>
                        <span class="list-item-value" style="color:${color}">${pct}%</span>
                    </div>
                    <div class="progress-bar"><div class="progress-fill" style="width:${pct}%;background:${color}"></div></div>`;
            });
            document.getElementById('patternConfidence').innerHTML = pcHtml;
        }

        async function refreshExecution() {
            const data = await fetchJSON('/api/execution');
            document.getElementById('totalRuns').textContent = data.total_runs || 0;
            document.getElementById('successRate').textContent = data.success_rate ? (data.success_rate * 100).toFixed(0) + '%' : '--';
        }

        async function refreshWeights() {
            const data = await fetchJSON('/api/weights');
            const ctx = document.getElementById('weightsRadarChart').getContext('2d');
            if (weightsRadarChart) weightsRadarChart.destroy();

            weightsRadarChart = new Chart(ctx, {
                type: 'radar',
                data: {
                    labels: data.labels || [],
                    datasets: [{
                        label: '当前权重',
                        data: data.datasets?.[0]?.data || [],
                        backgroundColor: 'rgba(59, 130, 246, 0.2)',
                        borderColor: 'rgba(59, 130, 246, 1)',
                        borderWidth: 2,
                        pointBackgroundColor: 'rgba(59, 130, 246, 1)'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        r: {
                            beginAtZero: true,
                            min: 0,
                            max: 2.5,
                            ticks: { color: '#64748b', backdropColor: 'transparent', stepSize: 0.5 },
                            grid: { color: '#334155' },
                            angleLines: { color: '#334155' },
                            pointLabels: { color: '#e2e8f0', font: { size: 11 } }
                        }
                    },
                    plugins: { legend: { display: false } }
                }
            });
        }

        async function refreshWeightsHistory() {
            const data = await fetchJSON('/api/weights-history');
            const ctx = document.getElementById('weightsHistoryChart').getContext('2d');
            if (weightsHistoryChart) weightsHistoryChart.destroy();

            const colors = ['#3b82f6', '#22c55e', '#eab308', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316'];

            weightsHistoryChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.labels || [],
                    datasets: data.datasets?.map((ds, i) => ({
                        label: ds.label,
                        data: ds.data || [],
                        borderColor: colors[i % colors.length],
                        backgroundColor: 'transparent',
                        tension: 0.3,
                        spanGaps: true
                    })) || []
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { intersect: false, mode: 'index' },
                    scales: {
                        x: { ticks: { color: '#64748b', maxRotation: 45, maxTicksLimit: 10 }, grid: { color: '#334155' } },
                        y: { min: 0, ticks: { color: '#64748b', stepSize: 0.5 }, grid: { color: '#334155' } }
                    },
                    plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8', boxWidth: 12, padding: 8 } } }
                }
            });
        }

        async function refreshModules() {
            const data = await fetchJSON('/api/modules');
            const modules = data.modules || [];
            let html = '';
            modules.forEach(m => {
                const statusClass = m.status === 'active' ? 'badge-success' : m.status === 'error' ? 'badge-error' : 'badge-warning';
                html += `
                    <div class="list-item">
                        <span class="list-item-label">${m.description || m.name}</span>
                        <span class="badge ${statusClass}">${m.status === 'active' ? '运行中' : m.status}</span>
                    </div>`;
            });
            document.getElementById('moduleList').innerHTML = html;
        }

        async function refreshEvents() {
            const data = await fetchJSON('/api/events');
            const events = Array.isArray(data) ? data.slice(-20).reverse() : [];
            let html = '';
            events.forEach(e => {
                const time = e.timestamp ? e.timestamp.slice(11, 19) : '--';
                const type = e.type || '未知';
                const dataStr = JSON.stringify(e.data || {}).slice(0, 60);
                html += `
                    <div class="timeline-item">
                        <span class="timeline-time">${time}</span>
                        <span class="timeline-type">${type}</span>
                        <span class="timeline-data">${dataStr}</span>
                    </div>`;
            });
            document.getElementById('eventTimeline').innerHTML = html || '<div style="color:var(--text-muted);text-align:center;padding:20px;">暂无事件</div>';
        }

        async function refreshProjects() {
            const data = await fetchJSON('/api/projects');
            const projects = data.projects || [];
            if (projects.length === 0) {
                document.getElementById('projectsGrid').innerHTML = '<div style="color:var(--text-muted);text-align:center;padding:40px;">暂未发现项目</div>';
                return;
            }
            let html = '';
            projects.forEach(p => {
                const priorityClass = p.priority === 1 ? 'high' : p.priority === 2 ? 'medium' : '';
                const score = p.opportunity_score || 0;
                html += `
                    <div class="project-card ${priorityClass}">
                        <div class="project-name">${p.name || '未知项目'}</div>
                        <div class="project-desc">${p.description || '无描述'}</div>
                        <div class="project-meta">
                            <span class="project-score">评分 ${score.toFixed(1)}</span>
                            <span class="project-tag">${p.project_type || '未知类型'}</span>
                            <span class="project-tag">窗口 ${p.window_months || 0}月</span>
                        </div>
                    </div>`;
            });
            document.getElementById('projectsGrid').innerHTML = html;
        }

        async function refreshPlans() {
            const data = await fetchJSON('/api/plans');
            const plans = data.plans || [];
            if (plans.length === 0) {
                document.getElementById('plansGrid').innerHTML = '<div style="color:var(--text-muted);text-align:center;padding:40px;">暂无执行计划</div>';
                return;
            }
            let html = '';
            plans.forEach(p => {
                const progress = p.progress || {};
                const phase72h = progress['72h'] || {};
                const phase7d = progress['7d'] || {};
                const phase30d = progress['30d'] || {};
                const totalTasks = (phase72h.total_tasks || 0) + (phase7d.total_tasks || 0) + (phase30d.total_tasks || 0);
                const completedTasks = (phase72h.completed_tasks || 0) + (phase7d.completed_tasks || 0) + (phase30d.completed_tasks || 0);
                const overallPct = totalTasks > 0 ? (completedTasks / totalTasks * 100).toFixed(0) : 0;
                let currentPhase = '72小时';
                if (phase72h.completed_tasks === phase72h.total_tasks && phase72h.total_tasks > 0) currentPhase = '7天';
                if (phase7d.completed_tasks === phase7d.total_tasks && phase7d.total_tasks > 0) currentPhase = '30天';
                const barColor = overallPct >= 70 ? 'var(--accent-green)' : overallPct >= 30 ? 'var(--accent-blue)' : 'var(--text-muted)';
                html += `
                    <div class="plan-card in-progress">
                        <div class="plan-header">
                            <span class="plan-name">${p.plan_id || '未知计划'}</span>
                            <span class="plan-phase">${currentPhase}</span>
                        </div>
                        <div class="progress-bar"><div class="progress-fill" style="width:${overallPct}%;background:${barColor}"></div></div>
                        <div class="plan-stats">
                            <span>进度 ${overallPct}%</span>
                            <span>任务 ${completedTasks}/${totalTasks}</span>
                        </div>
                    </div>`;
            });
            document.getElementById('plansGrid').innerHTML = html;
        }

        // 初始化
        refreshAll();

        // 自动刷新控制
        let autoRefreshInterval = setInterval(refreshAll, 30000);
        function toggleAutoRefresh(enabled) {
            if (enabled) {
                autoRefreshInterval = setInterval(refreshAll, 30000);
            } else {
                clearInterval(autoRefreshInterval);
            }
        }

        // v4.3 数据常驻每10秒刷新
        setInterval(refreshV43, 10000);
    </script>
</body>
</html>'''

# ============== 启动 ==============

if __name__ == '__main__':
    print("""
╔═══════════════════════════════════════════════════════╗
║       发现系统监控面板 v4.3                             ║
╠═══════════════════════════════════════════════════════╣
║  Dashboard:  http://localhost:5188                    ║
║  API Base:   http://localhost:5188/api               ║
║                                                       ║
║  v4.3 Endpoints:                                      ║
║    /api/v43/status      - v4.3完整状态               ║
║    /api/v43/causal     - 因果发现引擎                ║
║    /api/v43/threshold   - 阈值监控                   ║
║    /api/v43/evolution   - 自进化系统                   ║
║    /api/v43/retention  - 数据保留策略                ║
║                                                       ║
║  Legacy Endpoints:                                    ║
║    /api/status          - 自进化系统状态              ║
║    /api/weights         - 维度权重                    ║
║    /api/weights-history - 权重历史                    ║
║    /api/events          - 事件历史                     ║
║    /api/execution       - 执行统计                     ║
║    /api/modules         - 模块状态                     ║
╚═══════════════════════════════════════════════════════╝
    """)

    # 确保目录存在
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    app.run(host='0.0.0.0', port=5188, debug=False)
