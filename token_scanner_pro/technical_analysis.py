"""
Technical Analysis Module for Token Scanner Pro
Calculates RSI, MACD, Bollinger Bands, EMA, Support/Resistance, Fibonacci levels
"""

import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime


class TechnicalAnalysis:
    """
    Advanced technical analysis for established tokens
    Requires OHLCV data (Open, High, Low, Close, Volume)
    """

    @staticmethod
    def calculate_rsi(closes: List[float], period: int = 14) -> Optional[float]:
        """
        Calculate Relative Strength Index (RSI)

        Args:
            closes: List of closing prices
            period: RSI period (default 14)

        Returns:
            RSI value (0-100) or None if insufficient data
            < 30 = Oversold (buy signal)
            > 70 = Overbought (sell signal)
        """
        if len(closes) < period + 1:
            return None

        closes = np.array(closes)
        deltas = np.diff(closes)

        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])

        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return round(rsi, 2)

    @staticmethod
    def calculate_macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[Dict[str, float]]:
        """
        Calculate MACD (Moving Average Convergence Divergence)

        Args:
            closes: List of closing prices
            fast: Fast EMA period (default 12)
            slow: Slow EMA period (default 26)
            signal: Signal line period (default 9)

        Returns:
            Dict with macd_line, signal_line, histogram
            Histogram > 0 = Bullish
            Histogram < 0 = Bearish
        """
        if len(closes) < slow + signal:
            return None

        closes = np.array(closes)

        # Calculate EMAs
        ema_fast = TechnicalAnalysis._calculate_ema(closes, fast)
        ema_slow = TechnicalAnalysis._calculate_ema(closes, slow)

        macd_line = ema_fast - ema_slow
        signal_line = TechnicalAnalysis._calculate_ema(macd_line, signal)
        histogram = macd_line - signal_line

        return {
            "macd_line": round(float(macd_line[-1]), 6),
            "signal_line": round(float(signal_line[-1]), 6),
            "histogram": round(float(histogram[-1]), 6),
            "trend": "bullish" if histogram[-1] > 0 else "bearish"
        }

    @staticmethod
    def calculate_bollinger_bands(closes: List[float], period: int = 20, std_dev: float = 2.0) -> Optional[Dict[str, float]]:
        """
        Calculate Bollinger Bands

        Args:
            closes: List of closing prices
            period: Moving average period (default 20)
            std_dev: Standard deviation multiplier (default 2.0)

        Returns:
            Dict with upper_band, middle_band, lower_band, bandwidth
        """
        if len(closes) < period:
            return None

        closes = np.array(closes)
        middle_band = np.mean(closes[-period:])
        std = np.std(closes[-period:])

        upper_band = middle_band + (std_dev * std)
        lower_band = middle_band - (std_dev * std)

        bandwidth = ((upper_band - lower_band) / middle_band) * 100

        current_price = closes[-1]
        position = "above_upper" if current_price > upper_band else \
                   "below_lower" if current_price < lower_band else \
                   "within_bands"

        return {
            "upper_band": round(float(upper_band), 8),
            "middle_band": round(float(middle_band), 8),
            "lower_band": round(float(lower_band), 8),
            "bandwidth": round(float(bandwidth), 2),
            "current_price": round(float(current_price), 8),
            "position": position
        }

    @staticmethod
    def calculate_emas(closes: List[float], periods: List[int] = [9, 20, 50, 200]) -> Dict[str, Any]:
        """
        Calculate multiple Exponential Moving Averages

        Args:
            closes: List of closing prices
            periods: List of EMA periods to calculate

        Returns:
            Dict with EMA values and trend signals
        """
        if len(closes) < max(periods):
            return {"error": "Insufficient data for EMA calculation"}

        closes = np.array(closes)
        emas = {}

        for period in periods:
            if len(closes) >= period:
                ema_value = TechnicalAnalysis._calculate_ema(closes, period)[-1]
                emas[f"ema_{period}"] = round(float(ema_value), 8)

        # Golden Cross / Death Cross detection
        signals = {}
        if "ema_50" in emas and "ema_200" in emas:
            if emas["ema_50"] > emas["ema_200"]:
                signals["golden_cross"] = True  # Bullish
                signals["trend"] = "uptrend"
            else:
                signals["death_cross"] = True  # Bearish
                signals["trend"] = "downtrend"

        # Current price vs EMAs
        current_price = closes[-1]
        signals["above_ema_20"] = current_price > emas.get("ema_20", 0) if "ema_20" in emas else None
        signals["above_ema_50"] = current_price > emas.get("ema_50", 0) if "ema_50" in emas else None

        return {
            "emas": emas,
            "signals": signals,
            "current_price": round(float(current_price), 8)
        }

    @staticmethod
    def find_support_resistance(highs: List[float], lows: List[float], closes: List[float], sensitivity: float = 0.02) -> Dict[str, Any]:
        """
        Find support and resistance levels

        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of closing prices
            sensitivity: Price change threshold (default 2%)

        Returns:
            Dict with support and resistance levels
        """
        if len(highs) < 20 or len(lows) < 20:
            return {"error": "Insufficient data"}

        highs = np.array(highs)
        lows = np.array(lows)
        current_price = closes[-1]

        # Find local maxima (resistance)
        resistance_levels = []
        for i in range(2, len(highs) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
               highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                resistance_levels.append(float(highs[i]))

        # Find local minima (support)
        support_levels = []
        for i in range(2, len(lows) - 2):
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
               lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                support_levels.append(float(lows[i]))

        # Cluster similar levels
        resistance_levels = TechnicalAnalysis._cluster_levels(resistance_levels, sensitivity)
        support_levels = TechnicalAnalysis._cluster_levels(support_levels, sensitivity)

        # Sort and filter
        resistance_levels = sorted([r for r in resistance_levels if r > current_price])[:3]
        support_levels = sorted([s for s in support_levels if s < current_price], reverse=True)[:3]

        return {
            "resistance": [round(r, 8) for r in resistance_levels],
            "support": [round(s, 8) for s in support_levels],
            "current_price": round(float(current_price), 8),
            "nearest_resistance": round(resistance_levels[0], 8) if resistance_levels else None,
            "nearest_support": round(support_levels[0], 8) if support_levels else None
        }

    @staticmethod
    def calculate_fibonacci_levels(highs: List[float], lows: List[float], lookback: int = 50) -> Dict[str, float]:
        """
        Calculate Fibonacci retracement levels

        Args:
            highs: List of high prices
            lows: List of low prices
            lookback: Period to find high/low (default 50)

        Returns:
            Dict with Fibonacci levels
        """
        if len(highs) < lookback or len(lows) < lookback:
            return {"error": "Insufficient data"}

        recent_high = max(highs[-lookback:])
        recent_low = min(lows[-lookback:])

        diff = recent_high - recent_low

        # Fibonacci retracement levels
        levels = {
            "high": round(float(recent_high), 8),
            "low": round(float(recent_low), 8),
            "fib_0": round(float(recent_high), 8),  # 0% (high)
            "fib_23_6": round(float(recent_high - 0.236 * diff), 8),
            "fib_38_2": round(float(recent_high - 0.382 * diff), 8),
            "fib_50": round(float(recent_high - 0.5 * diff), 8),
            "fib_61_8": round(float(recent_high - 0.618 * diff), 8),
            "fib_78_6": round(float(recent_high - 0.786 * diff), 8),
            "fib_100": round(float(recent_low), 8),  # 100% (low)
        }

        # Fibonacci extension levels (targets)
        levels["fib_161_8"] = round(float(recent_high + 0.618 * diff), 8)
        levels["fib_261_8"] = round(float(recent_high + 1.618 * diff), 8)

        return levels

    @staticmethod
    def analyze_trend(closes: List[float], highs: List[float], lows: List[float], period: int = 20) -> Dict[str, Any]:
        """
        Comprehensive trend analysis

        Args:
            closes: List of closing prices
            highs: List of high prices
            lows: List of low prices
            period: Analysis period (default 20)

        Returns:
            Dict with trend direction, strength, and signals
        """
        if len(closes) < period:
            return {"error": "Insufficient data"}

        closes = np.array(closes)
        highs = np.array(highs)
        lows = np.array(lows)

        # Calculate trend direction using linear regression
        x = np.arange(len(closes[-period:]))
        slope, intercept = np.polyfit(x, closes[-period:], 1)

        # Trend strength (R-squared)
        y_pred = slope * x + intercept
        ss_res = np.sum((closes[-period:] - y_pred) ** 2)
        ss_tot = np.sum((closes[-period:] - np.mean(closes[-period:])) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

        # Higher highs / Lower lows
        recent_highs = highs[-period:]
        recent_lows = lows[-period:]

        higher_highs = sum(1 for i in range(1, len(recent_highs)) if recent_highs[i] > recent_highs[i-1])
        lower_lows = sum(1 for i in range(1, len(recent_lows)) if recent_lows[i] < recent_lows[i-1])

        # Trend determination
        if slope > 0 and r_squared > 0.5:
            trend = "strong_uptrend"
        elif slope > 0:
            trend = "weak_uptrend"
        elif slope < 0 and r_squared > 0.5:
            trend = "strong_downtrend"
        elif slope < 0:
            trend = "weak_downtrend"
        else:
            trend = "sideways"

        # Price change
        price_change_pct = ((closes[-1] - closes[-period]) / closes[-period]) * 100

        return {
            "trend": trend,
            "strength": round(float(r_squared), 3),
            "slope": round(float(slope), 8),
            "price_change_pct": round(float(price_change_pct), 2),
            "higher_highs_count": int(higher_highs),
            "lower_lows_count": int(lower_lows),
            "trend_signal": "bullish" if slope > 0 else "bearish"
        }

    @staticmethod
    def generate_trading_signal(rsi: Optional[float], macd: Optional[Dict],
                                bollinger: Optional[Dict], trend: Dict) -> Dict[str, Any]:
        """
        Generate overall trading signal based on all indicators

        Returns:
            Dict with signal (BUY/SELL/HOLD), confidence, and reasoning
        """
        signals = []
        confidence = 0

        # RSI signals
        if rsi is not None:
            if rsi < 30:
                signals.append("RSI oversold - BUY signal")
                confidence += 25
            elif rsi > 70:
                signals.append("RSI overbought - SELL signal")
                confidence -= 25
            elif 40 <= rsi <= 60:
                signals.append("RSI neutral")

        # MACD signals
        if macd is not None:
            if macd["trend"] == "bullish":
                signals.append("MACD bullish cross - BUY signal")
                confidence += 20
            else:
                signals.append("MACD bearish cross - SELL signal")
                confidence -= 20

        # Bollinger Bands signals
        if bollinger is not None:
            if bollinger["position"] == "below_lower":
                signals.append("Price below Bollinger lower band - BUY signal")
                confidence += 15
            elif bollinger["position"] == "above_upper":
                signals.append("Price above Bollinger upper band - SELL signal")
                confidence -= 15

        # Trend signals
        if "error" not in trend:
            if "strong_uptrend" in trend.get("trend", ""):
                signals.append("Strong uptrend detected - BUY signal")
                confidence += 30
            elif "strong_downtrend" in trend.get("trend", ""):
                signals.append("Strong downtrend detected - SELL signal")
                confidence -= 30
            elif "weak_uptrend" in trend.get("trend", ""):
                signals.append("Weak uptrend - HOLD/BUY")
                confidence += 10

        # Determine final signal
        if confidence >= 40:
            final_signal = "STRONG_BUY"
        elif confidence >= 20:
            final_signal = "BUY"
        elif confidence <= -40:
            final_signal = "STRONG_SELL"
        elif confidence <= -20:
            final_signal = "SELL"
        else:
            final_signal = "HOLD"

        return {
            "signal": final_signal,
            "confidence": abs(confidence),
            "signals": signals,
            "recommendation": TechnicalAnalysis._get_recommendation(final_signal)
        }

    # ==================== HELPER METHODS ====================

    @staticmethod
    def _calculate_ema(data: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average"""
        ema = np.zeros_like(data)
        ema[0] = data[0]
        multiplier = 2 / (period + 1)

        for i in range(1, len(data)):
            ema[i] = (data[i] * multiplier) + (ema[i-1] * (1 - multiplier))

        return ema

    @staticmethod
    def _cluster_levels(levels: List[float], sensitivity: float) -> List[float]:
        """Cluster similar price levels together"""
        if not levels:
            return []

        levels = sorted(levels)
        clustered = [levels[0]]

        for level in levels[1:]:
            if abs(level - clustered[-1]) / clustered[-1] > sensitivity:
                clustered.append(level)

        return clustered

    @staticmethod
    def _get_recommendation(signal: str) -> str:
        """Get human-readable recommendation"""
        recommendations = {
            "STRONG_BUY": "Excellent buy opportunity - Multiple indicators confirm strong uptrend",
            "BUY": "Good buy opportunity - Indicators suggest upward movement",
            "HOLD": "Hold position - Mixed signals, wait for clearer trend",
            "SELL": "Consider selling - Indicators suggest downward pressure",
            "STRONG_SELL": "Strong sell signal - Multiple indicators confirm downtrend"
        }
        return recommendations.get(signal, "No clear signal")
