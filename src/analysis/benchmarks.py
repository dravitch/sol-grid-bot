"""
Benchmarks corrects pour validation Grid Bot

Buy & Hold et Sell & Hold avec calculs précis
"""

from typing import Dict

import pandas as pd


class Benchmarks:
    """
    Calcule les benchmarks Buy & Hold et Sell & Hold.

    Used pour comparer performance du Grid Bot.
    """

    def __init__(
        self,
        initial_capital: float,
        initial_price: float,
        leverage: float = 1.0,
        trading_fee: float = 0.001,
    ):
        """
        Args:
            initial_capital: Capital initial en USD
            initial_price: Prix initial SOL/USD
            leverage: Levier pour Sell & Hold
            trading_fee: Frais de trading (0.001 = 0.1%)
        """
        self.initial_capital = initial_capital
        self.initial_price = initial_price
        self.leverage = leverage
        self.trading_fee = trading_fee
        self.initial_sol = initial_capital / initial_price

    def buy_and_hold(self, prices: pd.Series) -> pd.Series:
        """
        Buy & Hold: Achète SOL au début et garde.

        Formule simple:
            valeur(t) = initial_sol * prix(t)

        Args:
            prices: Série de prix SOL/USD

        Returns:
            Série de valeurs USD dans le temps
        """
        return prices * self.initial_sol

    def sell_and_hold(self, prices: pd.Series, trading_fee: float = None) -> pd.Series:
        """
        Sell & Hold: Short avec levier constant.

        Simulation d'un short unique:
        1. Position = (capital * leverage) / prix_initial
        2. PnL = (prix_initial - prix_actuel) / prix_initial * leverage
        3. Valeur = capital * (1 + PnL) - fees

        Args:
            prices: Série de prix SOL/USD
            trading_fee: Override des frais (optionnel)

        Returns:
            Série de valeurs USD dans le temps
        """
        fee = trading_fee if trading_fee is not None else self.trading_fee

        # Position size en SOL
        position_size = (self.initial_capital * self.leverage) / self.initial_price

        # Frais d'entrée (une seule fois)
        entry_fee = position_size * self.initial_price * fee

        # Variation de prix en %
        price_changes = (self.initial_price - prices) / self.initial_price

        # PnL avec levier
        pnl_pct = price_changes * self.leverage

        # Valeur du portfolio
        values = self.initial_capital * (1 + pnl_pct) - entry_fee

        # return pd.Series(values, index=prices.index)
        return pd.Series(values.squeeze(), index=prices.index)

    def compare(self, prices: pd.Series, strategy_values: pd.Series) -> Dict:
        """
        Compare la stratégie aux benchmarks.

        Args:
            prices: Prix historiques SOL/USD
            strategy_values: Valeurs du Grid Bot

        Returns:
            Dict avec tous les benchmarks et métriques
        """
        buy_hold = self.buy_and_hold(prices)
        sell_hold = self.sell_and_hold(prices)

        # Calcul returns finaux
        buy_hold_return = (buy_hold.iloc[-1] / self.initial_capital - 1) * 100
        sell_hold_return = (sell_hold.iloc[-1] / self.initial_capital - 1) * 100
        strategy_return = (strategy_values.iloc[-1] / self.initial_capital - 1) * 100

        # Comparaisons
        beat_buy_hold = strategy_return > buy_hold_return
        beat_sell_hold = strategy_return > sell_hold_return

        return {
            "buy_hold_values": buy_hold,
            "sell_hold_values": sell_hold,
            "strategy_values": strategy_values,
            "buy_hold_return": buy_hold_return,
            "sell_hold_return": sell_hold_return,
            "strategy_return": strategy_return,
            "beat_buy_hold": beat_buy_hold,
            "beat_sell_hold": beat_sell_hold,
            "outperformance_vs_buy_hold": strategy_return - buy_hold_return,
            "outperformance_vs_sell_hold": (strategy_return - sell_hold_return),
        }

    def print_comparison(self, comparison: Dict) -> None:
        """
        Affiche une comparaison lisible.

        Args:
            comparison: Résultat de compare()
        """
        print("\n" + "=" * 60)
        print("📊 BENCHMARK COMPARISON")
        print("=" * 60)

        print(f"💰 Initial Capital: ${self.initial_capital:,.2f}")
        print(f"📈 Initial Price: ${self.initial_price:.2f}")
        print(f"⚡ Leverage (Sell&Hold): {self.leverage}x")

        print("\n📉 FINAL RETURNS:")
        print(f"   Buy & Hold:      " f"{comparison['buy_hold_return']:+.2f}%")
        print(f"   Sell & Hold:     " f"{comparison['sell_hold_return']:+.2f}%")
        print(f"   Grid Strategy:   " f"{comparison['strategy_return']:+.2f}%")

        print("\n🎯 PERFORMANCE:")
        if comparison["beat_buy_hold"]:
            print("   ✅ Beat Buy & Hold!")
            print(
                f"      Outperformance: "
                f"{comparison['outperformance_vs_buy_hold']:+.2f}%"
            )
        else:
            print("   ❌ Below Buy & Hold")
            print(
                f"      Underperformance: "
                f"{comparison['outperformance_vs_buy_hold']:+.2f}%"
            )

        if comparison["beat_sell_hold"]:
            print("   ✅ Beat Sell & Hold!")
            print(
                f"      Outperformance: "
                f"{comparison['outperformance_vs_sell_hold']:+.2f}%"
            )
        else:
            print("   ❌ Below Sell & Hold")
            print(
                f"      Underperformance: "
                f"{comparison['outperformance_vs_sell_hold']:+.2f}%"
            )

        print("=" * 60 + "\n")


def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """
    Calcule le Sharpe Ratio.

    Args:
        returns: Série de returns (déjà en %)
        risk_free_rate: Taux sans risque annualisé

    Returns:
        Sharpe ratio (annualisé si returns quotidiens)
    """
    if len(returns) < 2:
        return 0.0

    excess_returns = returns - (risk_free_rate / 252)  # Daily risk-free

    if excess_returns.std() == 0:
        return 0.0

    # Annualisé (assume daily returns)
    sharpe = (excess_returns.mean() / excess_returns.std()) * (252**0.5)

    return sharpe


def calculate_max_drawdown(values: pd.Series) -> float:
    """
    Calcule le drawdown maximum.

    Args:
        values: Série de valeurs de portfolio

    Returns:
        Max drawdown en % (positif)
    """
    if len(values) < 2:
        return 0.0

    # Calcul des peaks
    cumulative_max = values.expanding().max()

    # Drawdowns
    drawdowns = (values - cumulative_max) / cumulative_max

    return abs(drawdowns.min()) * 100


def calculate_sortino_ratio(
    returns: pd.Series, target_return: float = 0.0, risk_free_rate: float = 0.0
) -> float:
    """
    Calcule le Sortino Ratio (comme Sharpe mais uniquement downside).

    Args:
        returns: Série de returns
        target_return: Return cible
        risk_free_rate: Taux sans risque

    Returns:
        Sortino ratio (annualisé)
    """
    if len(returns) < 2:
        return 0.0

    excess_returns = returns - (risk_free_rate / 252)

    # Downside deviation (seulement returns négatifs)
    downside_returns = excess_returns[excess_returns < target_return]

    if len(downside_returns) == 0 or downside_returns.std() == 0:
        return 0.0

    downside_std = downside_returns.std()

    # Annualisé
    sortino = (excess_returns.mean() / downside_std) * (252**0.5)

    return sortino
