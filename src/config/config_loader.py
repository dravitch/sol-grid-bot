"""
Config Loader - Charge et valide configuration YAML
Version tolérante : accepte configs minimales et complètes
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class TradingConfig:
    symbol: str
    initial_capital: float
    leverage: float
    maker_fee: float
    taker_fee: float
    funding_rate: float
    max_position_size: Optional[float] = None


@dataclass
class GridStrategyConfig:
    grid_size: int
    grid_ratio: float
    max_position_size: float
    adaptive_spacing: bool
    min_grid_distance: float
    max_simultaneous_positions: int
    rebalance_threshold: float


@dataclass
class RiskManagementConfig:
    max_portfolio_drawdown: float
    max_position_drawdown: float
    maintenance_margin: float
    safety_buffer: float
    min_liquidation_distance: float
    volatility_lookback: int
    adaptive_leverage_enabled: bool
    leverage_multiplier_low: float
    leverage_multiplier_high: float


@dataclass
class PerformanceConfig:
    target_asset_growth: float
    max_drawdown_acceptable: float
    min_sharpe_ratio: float
    benchmark_comparison: bool


@dataclass
class OptimizationConfig:
    grid_size_range: list
    grid_ratio_range: list
    leverage_range: list
    max_position_range: list
    strategy: str
    max_combinations: int
    survival_threshold: float


class GridBotConfig:
    """Configuration complète du Grid Bot avec valeurs par défaut"""

    def __init__(self, config_path: str = None):
        self.config_path = (
            Path(config_path) if config_path else Path("config/default.yaml")
        )
        self.raw_config = self._load_yaml()

        # Parse configs avec fallbacks
        self.trading = self._parse_trading()
        self.grid_strategy = self._parse_grid_strategy()
        self.risk_management = self._parse_risk_management()
        self.performance = self._parse_performance()
        self.optimization = self._parse_optimization()

        logging.info(f"Config loaded from {self.config_path}")

    def _load_yaml(self) -> Dict[str, Any]:
        """Charge YAML"""
        if not self.config_path.exists():
            logging.error(f"Config not found: {self.config_path}")
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, "r") as f:
            config = yaml.safe_load(f)

        return config

    def _parse_trading(self) -> TradingConfig:
        """Parse trading config avec valeurs par défaut"""
        t = self.raw_config.get("trading", {})

        return TradingConfig(
            symbol=t.get("symbol", "SOL/USDT"),
            initial_capital=float(t.get("initial_capital", 1000)),
            leverage=float(t.get("leverage", 8)),
            maker_fee=float(t.get("maker_fee", 0.0002)),
            taker_fee=float(t.get("taker_fee", 0.0005)),
            funding_rate=float(t.get("funding_rate", 0.0)),
            max_position_size=(
                float(t.get("max_position_size", 0.3))
                if "max_position_size" in t
                else None
            ),
        )

    def _parse_grid_strategy(self) -> GridStrategyConfig:
        """Parse grid strategy avec valeurs par défaut"""
        g = self.raw_config.get("grid_strategy", {})

        # Fallback sur trading.max_position_size si pas dans grid_strategy
        max_pos = float(
            g.get(
                "max_position_size",
                self.raw_config.get("trading", {}).get("max_position_size", 0.3),
            )
        )

        return GridStrategyConfig(
            grid_size=int(g.get("grid_size", 7)),
            grid_ratio=float(g.get("grid_ratio", 0.02)),
            max_position_size=max_pos,
            adaptive_spacing=bool(g.get("adaptive_spacing", False)),
            min_grid_distance=float(g.get("min_grid_distance", 0.01)),
            max_simultaneous_positions=int(g.get("max_simultaneous_positions", 5)),
            rebalance_threshold=float(g.get("rebalance_threshold", 0.05)),
        )

    def _parse_risk_management(self) -> RiskManagementConfig:
        """Parse risk management avec valeurs par défaut"""
        r = self.raw_config.get("risk_management", {})
        adaptive = r.get("adaptive_leverage", {})

        return RiskManagementConfig(
            max_portfolio_drawdown=float(r.get("max_portfolio_drawdown", 0.30)),
            max_position_drawdown=float(r.get("max_position_drawdown", 0.15)),
            maintenance_margin=float(r.get("maintenance_margin", 0.05)),
            safety_buffer=float(r.get("safety_buffer", 1.5)),
            min_liquidation_distance=float(r.get("min_liquidation_distance", 0.15)),
            volatility_lookback=int(r.get("volatility_lookback", 20)),
            adaptive_leverage_enabled=bool(adaptive.get("enabled", False)),
            leverage_multiplier_low=float(adaptive.get("leverage_multiplier_low", 1.0)),
            leverage_multiplier_high=float(
                adaptive.get("leverage_multiplier_high", 1.0)
            ),
        )

    def _parse_performance(self) -> PerformanceConfig:
        """Parse performance avec valeurs par défaut"""
        p = self.raw_config.get("performance", {})

        return PerformanceConfig(
            target_asset_growth=float(p.get("target_asset_growth", 100)),
            max_drawdown_acceptable=float(p.get("max_drawdown_acceptable", 25)),
            min_sharpe_ratio=float(p.get("min_sharpe_ratio", 1.0)),
            benchmark_comparison=bool(p.get("benchmark_comparison", True)),
        )

    def _parse_optimization(self) -> OptimizationConfig:
        """Parse optimization avec valeurs par défaut"""
        o = self.raw_config.get("optimization", {})

        return OptimizationConfig(
            grid_size_range=o.get("grid_size_range", [5, 7, 10]),
            grid_ratio_range=o.get("grid_ratio_range", [0.02, 0.03, 0.05]),
            leverage_range=o.get("leverage_range", [2, 3, 5, 8]),
            max_position_range=o.get("max_position_range", [0.15, 0.25, 0.30]),
            strategy=o.get("strategy", "frontier"),
            max_combinations=int(o.get("max_combinations", 500)),
            survival_threshold=float(o.get("survival_threshold", 0.5)),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dict pour backtest"""
        return {
            "initial_capital": self.trading.initial_capital,
            "grid_size": self.grid_strategy.grid_size,
            "grid_ratio": self.grid_strategy.grid_ratio,
            "leverage": self.trading.leverage,
            "max_position_size": self.grid_strategy.max_position_size,
            "trading_fee": self.trading.taker_fee,
            "maker_fee": self.trading.maker_fee,
            "max_simultaneous_positions": self.grid_strategy.max_simultaneous_positions,
            "min_grid_distance": self.grid_strategy.min_grid_distance,
            "adaptive_spacing": self.grid_strategy.adaptive_spacing,
            "maintenance_margin": self.risk_management.maintenance_margin,
            "safety_buffer": self.risk_management.safety_buffer,
            "max_portfolio_drawdown": self.risk_management.max_portfolio_drawdown,
            "volatility_lookback": self.risk_management.volatility_lookback,
            "adaptive_leverage": self.risk_management.adaptive_leverage_enabled,
        }

    def __repr__(self):
        return (
            f"GridBotConfig(\n"
            f"  trading={self.trading},\n"
            f"  grid_strategy={self.grid_strategy},\n"
            f"  risk_management={self.risk_management},\n"
            f"  performance={self.performance},\n"
            f"  optimization={self.optimization}\n"
            f")"
        )


def load_config(config_path: str = None) -> GridBotConfig:
    """Load config from YAML file"""
    return GridBotConfig(config_path)
