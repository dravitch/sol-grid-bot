"""
Grid Bot v3 - 100% Configurable via YAML
Lit tous les paramètres de la config
"""

import logging
from typing import Dict, List, Tuple
from datetime import datetime
import pandas as pd
import numpy as np


class GridBotV3:
    """
    Grid Bot complètement configurable
    Tous les paramètres viennent du YAML
    """

    def __init__(self, initial_capital: float, initial_price: float, config: Dict):
        """
        Args:
            initial_capital: Capital initial USD
            initial_price: Prix initial de l'actif
            config: Dict avec tous paramètres (du YAML)
        """
        # Config trading
        self.initial_capital = initial_capital
        self.initial_price = initial_price
        self.leverage = config["leverage"]
        self.maker_fee = config.get("maker_fee", 0.0005)
        self.taker_fee = config.get("trading_fee", 0.001)

        # Config grille
        self.grid_size = config["grid_size"]
        self.grid_ratio = config["grid_ratio"]
        self.max_position_size = config["max_position_size"]
        self.max_simultaneous_positions = config.get(
            "max_simultaneous_positions", self.grid_size
        )
        self.min_grid_distance = config.get("min_grid_distance", 0.01)
        self.adaptive_spacing = config.get("adaptive_spacing", False)

        # Config risque
        self.max_portfolio_drawdown = config.get("max_portfolio_drawdown", 0.30)
        self.max_position_drawdown = config.get("max_position_drawdown", 0.15)
        self.maintenance_margin = config.get("maintenance_margin", 0.05)
        self.safety_buffer = config.get("safety_buffer", 1.5)
        self.min_liquidation_distance = config.get("min_liquidation_distance", 0.15)
        self.volatility_lookback = config.get("volatility_lookback", 20)

        # Levier adaptatif
        self.adaptive_leverage = config.get("adaptive_leverage", False)
        self.leverage_multiplier_low = config.get("leverage_multiplier_low", 1.0)
        self.leverage_multiplier_high = config.get("leverage_multiplier_high", 1.0)

        # État
        self.collateral_sol = initial_capital / initial_price
        self.initial_sol = self.collateral_sol
        self.positions = []
        self.trades_history = []
        self.grid_levels = []

        # Métriques
        self.total_fees_paid = 0.0
        self.liquidation_count = 0
        self.peak_sol = self.collateral_sol
        self.volatility_history = []

        logging.info(
            f"GridBotV3 initialized: "
            f"capital=${initial_capital}, leverage={self.leverage}x, "
            f"grid_size={self.grid_size}, grid_ratio={self.grid_ratio}"
        )

    def _calculate_volatility(self, price_series: pd.Series) -> float:
        """Calcule volatilité sur lookback window"""
        if len(price_series) < self.volatility_lookback:
            return 0.02  # Défaut

        recent = price_series.iloc[-self.volatility_lookback :]
        returns = recent.pct_change().dropna()

        return returns.std() if len(returns) > 0 else 0.02

    def _adjust_leverage_for_volatility(self, current_volatility: float) -> float:
        """Ajuste leverage selon volatilité si enabled"""
        if not self.adaptive_leverage:
            return self.leverage

        # Low volatility: augmente leverage
        if current_volatility < 0.01:
            adjusted = self.leverage * self.leverage_multiplier_low
            logging.debug(f"Low vol: leverage {self.leverage:.1f}x → {adjusted:.1f}x")
            return adjusted

        # High volatility: réduit leverage
        if current_volatility > 0.05:
            adjusted = self.leverage * self.leverage_multiplier_high
            logging.debug(f"High vol: leverage {self.leverage:.1f}x → {adjusted:.1f}x")
            return adjusted

        return self.leverage

    def _calculate_grid_levels(self, current_price: float) -> List[float]:
        """
        Calcule niveaux de grille avec espacement adaptatif optionnel
        """
        levels = []
        level = current_price

        for i in range(self.grid_size):
            # Espacement progressif
            spacing = self.grid_ratio * (1 + i * 0.1)

            # Respecte min_grid_distance
            if spacing < self.min_grid_distance:
                spacing = self.min_grid_distance

            level = level * (1 - spacing)
            levels.append(level)

        return sorted(levels, reverse=True)  # Descending

    def _calculate_position_size(self, price: float) -> float:
        """
        Calcule taille position selon:
        - Capital disponible
        - Positions ouvertes
        - Max position size
        """
        portfolio_value_usd = self.collateral_sol * price

        # Réduction selon positions existantes
        position_count_factor = 1.0 - (len(self.positions) * 0.1)
        position_count_factor = max(0.3, position_count_factor)

        # Applique max_position_size
        available_size = self.max_position_size * position_count_factor
        position_value = portfolio_value_usd * available_size

        return position_value / price

    def _calculate_liquidation_price(
        self, entry_price: float, current_leverage: float
    ) -> float:
        """Prix liquidation avec leverage courant"""
        margin_ratio = current_leverage * self.maintenance_margin * self.safety_buffer
        return entry_price * (1 + margin_ratio)

    def _open_position(
        self, entry_price: float, grid_level: float, timestamp: datetime
    ) -> bool:
        """Ouvre position SHORT"""

        # Vérification max simultaneous
        if len(self.positions) >= self.max_simultaneous_positions:
            return False

        # Calcul leverage courant (adaptatif ou fixe)
        current_leverage = self.leverage

        size = self._calculate_position_size(entry_price)
        if size <= 0:
            return False

        # Frais entrée
        entry_fee_usd = size * entry_price * self.maker_fee
        entry_fee_sol = entry_fee_usd / entry_price

        self.collateral_sol -= entry_fee_sol
        self.total_fees_paid += entry_fee_usd

        liquidation_price = self._calculate_liquidation_price(
            entry_price, current_leverage
        )

        position = {
            "entry_price": entry_price,
            "size": size,
            "grid_level": grid_level,
            "liquidation_price": liquidation_price,
            "entry_time": timestamp,
            "entry_sol_collateral": self.collateral_sol,
            "entry_fee_paid": entry_fee_usd,
            "leverage": current_leverage,
        }

        self.positions.append(position)

        logging.debug(
            f"Position opened: ${entry_price:.2f}, "
            f"size={size:.4f} SOL, lev={current_leverage:.1f}x, liq=${liquidation_price:.2f}"
        )

        return True

    def _close_position(
        self,
        position: dict,
        exit_price: float,
        timestamp: datetime,
        reason: str = "take_profit",
    ) -> float:
        """Ferme position"""

        # Frais sortie
        exit_fee_usd = position["size"] * exit_price * self.taker_fee

        # PnL brut (SHORT)
        price_change = position["entry_price"] - exit_price
        pnl_per_sol = price_change * position["leverage"]
        gross_pnl_usd = pnl_per_sol * position["size"]

        # PnL net
        net_pnl_usd = gross_pnl_usd - exit_fee_usd
        pnl_in_sol = net_pnl_usd / exit_price

        # Mise à jour
        self.collateral_sol += pnl_in_sol
        self.total_fees_paid += exit_fee_usd

        if self.collateral_sol > self.peak_sol:
            self.peak_sol = self.collateral_sol

        # Record trade
        total_fees = position.get("entry_fee_paid", 0) + exit_fee_usd

        trade = {
            "entry_time": position["entry_time"],
            "exit_time": timestamp,
            "entry_price": position["entry_price"],
            "exit_price": exit_price,
            "size": position["size"],
            "pnl_usd": net_pnl_usd,
            "pnl_sol": pnl_in_sol,
            "fees": total_fees,
            "reason": reason,
            "leverage": position["leverage"],
        }
        self.trades_history.append(trade)

        return net_pnl_usd

    def step(
        self, current_price: float, price_series: pd.Series, timestamp: datetime
    ) -> Dict:
        """Exécute un pas de stratégie"""

        # Calcule volatilité
        current_vol = self._calculate_volatility(price_series)
        self.volatility_history.append(current_vol)

        # Ajuste leverage selon volatilité
        if self.adaptive_leverage:
            adjusted_lev = self._adjust_leverage_for_volatility(current_vol)
            # TODO: réappliquer à positions ouvertes?

        # Check liquidations
        for i, position in enumerate(self.positions[:]):
            if current_price >= position["liquidation_price"]:
                self.collateral_sol *= 0.2
                self.positions.remove(position)
                self.liquidation_count += 1

                logging.error(f"💀 LIQUIDATION at ${current_price:.2f} - GAME OVER")

                return {
                    "timestamp": timestamp,
                    "price": current_price,
                    "collateral_sol": self.collateral_sol,
                    "portfolio_value_usd": self.collateral_sol * current_price,
                    "active_positions": len(self.positions),
                    "total_trades": len(self.trades_history),
                    "liquidations": self.liquidation_count,
                    "liquidated": True,
                    "volatility": current_vol,
                }

            # Take profit
            if current_price <= position["grid_level"] * 0.98:
                self._close_position(position, current_price, timestamp, "take_profit")
                self.positions.remove(position)

        # Update grid si nécessaire
        if not self.grid_levels or current_price < min(self.grid_levels) * 0.95:
            self.grid_levels = self._calculate_grid_levels(current_price)

        # Open new positions
        if len(self.positions) < self.max_simultaneous_positions:
            for level in self.grid_levels:
                if abs(current_price - level) / level < 0.02:
                    if not any(
                        abs(p["entry_price"] - current_price) / current_price < 0.01
                        for p in self.positions
                    ):
                        self._open_position(current_price, level, timestamp)
                        break

        # Return state
        portfolio_value = self.collateral_sol * current_price

        return {
            "timestamp": timestamp,
            "price": current_price,
            "collateral_sol": self.collateral_sol,
            "portfolio_value_usd": portfolio_value,
            "active_positions": len(self.positions),
            "total_trades": len(self.trades_history),
            "liquidations": self.liquidation_count,
            "liquidated": False,
            "volatility": current_vol,
        }

    def get_summary(self) -> Dict:
        """Résumé final"""

        sol_change = self.collateral_sol - self.initial_sol
        sol_change_pct = (sol_change / self.initial_sol) * 100

        exposed_sol = sum(abs(p["size"]) for p in self.positions)
        owned_sol = self.collateral_sol

        drawdown_sol = self.peak_sol - self.collateral_sol
        drawdown_pct = (drawdown_sol / self.peak_sol) * 100 if self.peak_sol > 0 else 0

        # Drawdown réel après liquidation
        if self.liquidation_count > 0:
            real_drawdown_pct = 80.0
        else:
            real_drawdown_pct = drawdown_pct

        winning_trades = [t for t in self.trades_history if t["pnl_usd"] > 0]
        win_rate = (
            len(winning_trades) / len(self.trades_history) * 100
            if self.trades_history
            else 0
        )

        return {
            "initial_sol": self.initial_sol,
            "final_sol": self.collateral_sol,
            "owned_sol": owned_sol,
            "exposed_sol": exposed_sol,
            "sol_change": sol_change,
            "sol_change_pct": sol_change_pct,
            "total_trades": len(self.trades_history),
            "liquidations": self.liquidation_count,
            "win_rate": win_rate,
            "total_fees_usd": self.total_fees_paid,
            "drawdown_sol": drawdown_sol,
            "drawdown_pct": drawdown_pct,
            "real_drawdown_pct": real_drawdown_pct,
            "peak_sol": self.peak_sol,
            "liquidated": self.liquidation_count > 0,
            "avg_volatility": (
                np.mean(self.volatility_history) if self.volatility_history else 0
            ),
        }


def run_backtest(data: pd.DataFrame, config: Dict) -> Tuple[pd.DataFrame, GridBotV3]:
    """Exécute backtest avec GridBotV3"""

    initial_price = float(data["close"].iloc[0])

    bot = GridBotV3(
        initial_capital=config["initial_capital"],
        initial_price=initial_price,
        config=config,
    )

    results = []
    liquidated = False

    for idx, (timestamp, row) in enumerate(data.iterrows()):
        current_price = float(row["close"])

        # Price series jusqu'à now pour volatilité
        price_series = data["close"].iloc[: idx + 1]

        state = bot.step(current_price, price_series, timestamp)
        results.append(state)

        if state.get("liquidated", False):
            liquidated = True
            break

    results_df = pd.DataFrame(results).set_index("timestamp")

    if liquidated:
        logging.warning(
            f"Backtest stopped: liquidation at {len(results)}/{len(data)} bars"
        )

    return results_df, bot
