"""
时序信号系统 v4.2
Time-Series Signal System — 斜率计算 + 爆发期判断

核心功能：
1. signal_history 表记录时序变化
2. 计算7日/30日斜率替代绝对值
3. 爆发期自动判断

使用方式：
python time_series_signals.py --record "OpenClaw" --metric stars --value 1500
python time_series_signals.py --analyze "OpenClaw"
python time_series_signals.py --slope "OpenClaw"
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

# ============== 数据库连接（复用knowledge_graph的连接）==============

try:
    from knowledge_graph import DBConnection, DBConfig
except ImportError:
    DBConnection = None
    DBConfig = None


# ============== 斜率计算器 ==============

@dataclass
class SignalSlope:
    """信号斜率数据"""
    entity: str
    metric: str
    slope_7d: float = 0.0      # 7日斜率 (每日变化量)
    slope_30d: float = 0.0    # 30日斜率
    trend_7d: str = "stable"   # 趋势: rising/falling/stable
    trend_30d: str = "stable"
    burst_detected: bool = False
    burst_intensity: float = 0.0  # 爆发强度 0-1

    def to_dict(self) -> dict:
        return {
            "entity": self.entity,
            "metric": self.metric,
            "slope_7d": round(self.slope_7d, 4),
            "slope_30d": round(self.slope_30d, 4),
            "trend_7d": self.trend_7d,
            "trend_30d": self.trend_30d,
            "burst_detected": self.burst_detected,
            "burst_intensity": round(self.burst_intensity, 3),
        }


class SlopeCalculator:
    """
    斜率计算器

    使用线性回归计算信号变化斜率
    """

    def __init__(self, db: DBConnection = None):
        self.db = db

    def calculate_slope(self, entity: str, metric: str,
                        days: int = 7) -> Optional[float]:
        """
        计算斜率（每日变化量）

        使用简单线性回归: slope = (n*sum(xy) - sum(x)*sum(y)) / (n*sum(x^2) - sum(x)^2)
        """
        if self.db is None:
            return 0.0

        # 获取时间序列数据
        sql = """
            SELECT timestamp, value
            FROM signal_history
            WHERE entity = %s AND metric = %s
            AND timestamp > NOW() - INTERVAL '%s days'
            ORDER BY timestamp ASC
        """
        results = self.db.execute(sql, (entity, metric, days))

        if len(results) < 2:
            return 0.0

        # 线性回归
        n = len(results)
        x_vals = list(range(n))  # 时间索引
        y_vals = [r["value"] for r in results]

        sum_x = sum(x_vals)
        sum_y = sum(y_vals)
        sum_xy = sum(x * y for x, y in zip(x_vals, y_vals))
        sum_x2 = sum(x ** 2 for x in x_vals)

        denominator = n * sum_x2 - sum_x ** 2
        if abs(denominator) < 1e-10:
            return 0.0

        slope = (n * sum_xy - sum_x * sum_y) / denominator
        return slope

    def detect_burst(self, slope: float, threshold: float = 2.0) -> tuple:
        """
        检测爆发

        Args:
            slope: 斜率
            threshold: 爆发阈值（标准差倍数）

        Returns:
            (burst_detected, intensity)
        """
        # 斜率大于阈值表示爆发
        if abs(slope) > threshold:
            # 爆发强度：归一化到0-1
            intensity = min(1.0, abs(slope) / (threshold * 2))
            return True, intensity
        return False, 0.0

    def calculate_trend(self, slope: float, threshold: float = 0.1) -> str:
        """
        判断趋势

        Args:
            slope: 斜率
            threshold: 判断阈值

        Returns:
            rising / falling / stable
        """
        if slope > threshold:
            return "rising"
        elif slope < -threshold:
            return "falling"
        return "stable"


# ============== 时序信号管理器 ==============

class TimeSeriesSignalManager:
    """
    时序信号管理器 v4.2

    1. 记录信号时序变化
    2. 计算斜率
    3. 判断爆发期
    """

    def __init__(self, db: DBConnection = None):
        self.db = db or (DBConnection.get_instance() if DBConnection else None)
        self.slope_calc = SlopeCalculator(self.db)

    def record_signal(self, platform: str, entity: str, metric: str,
                     value: float, metadata: dict = None) -> bool:
        """
        记录信号

        Args:
            platform: 来源平台
            entity: 实体名称
            metric: 指标类型 (stars, forks, upvotes, likes)
            value: 指标值
            metadata: 额外数据

        Returns:
            是否成功
        """
        if self.db is None:
            print("⚠️ 数据库未连接，跳过记录")
            return False

        # 计算相对上次的差值
        last_value = self._get_last_value(entity, metric)
        value_delta = value - last_value if last_value else 0.0

        sql = """
            INSERT INTO signal_history
            (platform, entity, metric, value, value_delta, timestamp, metadata)
            VALUES (%s, %s, %s, %s, %s, NOW(), %s)
        """
        self.db.execute(sql, (
            platform, entity, metric, value, value_delta,
            json.dumps(metadata or {})
        ))
        return True

    def _get_last_value(self, entity: str, metric: str) -> Optional[float]:
        """获取上一次的指标值"""
        sql = """
            SELECT value FROM signal_history
            WHERE entity = %s AND metric = %s
            ORDER BY timestamp DESC
            LIMIT 1
        """
        results = self.db.execute(sql, (entity, metric))
        return results[0]["value"] if results else None

    def get_signal_slope(self, entity: str, metric: str) -> SignalSlope:
        """
        获取信号斜率数据

        Returns:
            SignalSlope 对象
        """
        slope_7d = self.slope_calc.calculate_slope(entity, metric, 7)
        slope_30d = self.slope_calc.calculate_slope(entity, metric, 30)

        # 判断趋势
        trend_7d = self.slope_calc.calculate_trend(slope_7d)
        trend_30d = self.slope_calc.calculate_trend(slope_30d)

        # 检测爆发
        burst_7d, intensity_7d = self.slope_calc.detect_burst(slope_7d)
        burst_30d, intensity_30d = self.slope_calc.detect_burst(slope_30d)

        return SignalSlope(
            entity=entity,
            metric=metric,
            slope_7d=slope_7d,
            slope_30d=slope_30d,
            trend_7d=trend_7d,
            trend_30d=trend_30d,
            burst_detected=burst_7d or burst_30d,
            burst_intensity=max(intensity_7d, intensity_30d),
        )

    def analyze_entity(self, entity: str) -> Dict[str, SignalSlope]:
        """
        分析实体的所有指标

        Returns:
            {metric: SignalSlope}
        """
        if self.db is None:
            return {}

        # 获取该实体所有指标类型
        sql = """
            SELECT DISTINCT metric FROM signal_history
            WHERE entity = %s
        """
        results = self.db.execute(sql, (entity,))
        metrics = [r["metric"] for r in results]

        return {
            metric: self.get_signal_slope(entity, metric)
            for metric in metrics
        }

    def get_burst_signals(self, min_intensity: float = 0.5) -> List[SignalSlope]:
        """
        获取所有检测到爆发的信号

        Args:
            min_intensity: 最小爆发强度

        Returns:
            SignalSlope列表
        """
        if self.db is None:
            return []

        # 获取最近有数据的实体
        sql = """
            SELECT DISTINCT entity, metric FROM signal_history
            WHERE timestamp > NOW() - INTERVAL '7 days'
        """
        results = self.db.execute(sql)

        burst_signals = []
        for row in results:
            slope = self.get_signal_slope(row["entity"], row["metric"])
            if slope.burst_detected and slope.burst_intensity >= min_intensity:
                burst_signals.append(slope)

        return sorted(burst_signals, key=lambda x: x.burst_intensity, reverse=True)

    def get_signal_history(self, entity: str, metric: str,
                          days: int = 30) -> List[Dict]:
        """
        获取信号历史

        Returns:
            时间序列数据列表
        """
        if self.db is None:
            return []

        sql = """
            SELECT timestamp, value, value_delta
            FROM signal_history
            WHERE entity = %s AND metric = %s
            AND timestamp > NOW() - INTERVAL '%s days'
            ORDER BY timestamp ASC
        """
        return self.db.execute(sql, (entity, metric, days))


# ============== 爆发期判断 ==============

class BurstDetector:
    """
    爆发期判断器

    基于斜率和历史数据判断是否处于爆发期
    """

    # 爆发期判断阈值
    SLOPE_THRESHOLD = 2.0      # 斜率阈值
    ABSOLUTE_VALUE_THRESHOLD = 100  # 绝对值阈值（用于参考）
    BURST_INTENSITY_THRESHOLD = 0.5  # 爆发强度阈值

    def __init__(self, signal_manager: TimeSeriesSignalManager):
        self.signal_manager = signal_manager

    def is_burst_period(self, entity: str, metric: str) -> tuple:
        """
        判断是否处于爆发期

        Returns:
            (is_burst, confidence, reason)
        """
        slope = self.signal_manager.get_signal_slope(entity, metric)

        if not slope.burst_detected:
            return False, 0.0, f"斜率{slope.slope_7d:.2f}未达阈值"

        # 综合判断
        reasons = []
        confidence = 0.0

        if slope.trend_7d == "rising" and slope.trend_30d == "rising":
            confidence += 0.4
            reasons.append("7日和30日均上升")

        if slope.burst_intensity > 0.7:
            confidence += 0.3
            reasons.append(f"爆发强度{slope.burst_intensity:.2f}高")

        if slope.slope_7d > slope.slope_30d * 1.5:
            confidence += 0.2
            reasons.append("7日增速快于30日")

        is_burst = confidence > 0.5
        return is_burst, min(1.0, confidence), " | ".join(reasons)

    def get_burst_report(self, entity: str) -> Dict:
        """生成爆发报告"""
        slopes = self.signal_manager.analyze_entity(entity)

        metrics_burst = []
        for metric, slope in slopes.items():
            is_burst, confidence, reason = self.is_burst_period(entity, metric)
            if is_burst:
                metrics_burst.append({
                    "metric": metric,
                    "confidence": confidence,
                    "reason": reason,
                    "slope_7d": slope.slope_7d,
                    "slope_30d": slope.slope_30d,
                })

        return {
            "entity": entity,
            "timestamp": datetime.now().isoformat(),
            "total_metrics": len(slopes),
            "burst_metrics": len(metrics_burst),
            "burst_details": metrics_burst,
            "overall_burst": len(metrics_burst) > 0,
        }


# ============== 主程序 ==============

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="时序信号工具 v4.2")
    parser.add_argument("--record", nargs=4, metavar=("PLATFORM", "ENTITY", "METRIC", "VALUE"),
                       help="记录信号: platform entity metric value")
    parser.add_argument("--analyze", metavar="ENTITY", help="分析实体信号")
    parser.add_argument("--slope", metavar="ENTITY", help="计算实体斜率")
    parser.add_argument("--burst", action="store_true", help="显示所有爆发信号")
    parser.add_argument("--history", nargs=3, metavar=("ENTITY", "METRIC", "DAYS"),
                       help="获取历史: entity metric days")

    args = parser.parse_args()

    print("📈 时序信号系统 v4.2\n")

    db = None
    if DBConnection:
        db = DBConnection.get_instance()
        db.connect()

    signal_manager = TimeSeriesSignalManager(db)

    if args.record:
        platform, entity, metric, value = args.record
        success = signal_manager.record_signal(
            platform, entity, metric, float(value)
        )
        print(f"{'✓' if success else '⚠️'} 记录信号: {entity}/{metric} = {value}")

    elif args.analyze:
        print(f"📊 分析 {args.analyze} 的信号...\n")
        slopes = signal_manager.analyze_entity(args.analyze)
        for metric, slope in slopes.items():
            print(f"  {metric}:")
            print(f"    7日斜率: {slope.slope_7d:.4f} ({slope.trend_7d})")
            print(f"    30日斜率: {slope.slope_30d:.4f} ({slope.trend_30d})")
            print(f"    爆发: {'是' if slope.burst_detected else '否'} (强度: {slope.burst_intensity:.2f})")

    elif args.slope:
        print(f"📈 {args.slope} 斜率计算\n")
        slope = signal_manager.get_signal_slope(args.slope, "stars")
        print(f"  7日斜率: {slope.slope_7d:.4f} ({slope.trend_7d})")
        print(f"  30日斜率: {slope.slope_30d:.4f} ({slope.trend_30d})")
        print(f"  爆发检测: {'是' if slope.burst_detected else '否'}")
        print(f"  爆发强度: {slope.burst_intensity:.3f}")

    elif args.burst:
        print("🔥 爆发信号\n")
        bursts = signal_manager.get_burst_signals()
        for b in bursts[:10]:
            print(f"  {b.entity}/{b.metric}: 强度{b.burst_intensity:.3f} ({b.trend_7d})")

    elif args.history:
        entity, metric, days = args.history
        print(f"📜 {entity}/{metric} 历史 (最近{days}天)\n")
        history = signal_manager.get_signal_history(entity, metric, int(days))
        for h in history[-10:]:
            print(f"  {h['timestamp']}: {h['value']} (delta: {h.get('value_delta', 0):+.0f})")

    else:
        print(__doc__)