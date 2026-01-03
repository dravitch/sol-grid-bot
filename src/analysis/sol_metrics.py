"""
Métriques de Performance centrées sur SOL
Focus: Accumulation d'actifs, pas USD
"""

import numpy as np
import pandas as pd
from typing import Dict, List


def calculate_sol_returns(sol_series: pd.Series) -> pd.Series:
    """Calcule returns journaliers en SOL"""
    return sol_series.pct_change().dropna()


def calculate_sharpe_ratio_sol(
    sol_series: pd.Series, risk_free_rate: float = 0.0
) -> float:
    """
    Sharpe Ratio basé sur SOL holdings

    Mesure: Rendement SOL / Volatilité SOL
    """
    returns = calculate_sol_returns(sol_series)

    if len(returns) == 0 or returns.std() == 0:
        return 0.0

    excess_returns = returns - risk_free_rate / 365
    sharpe = (excess_returns.mean() / returns.std()) * np.sqrt(365)

    return sharpe


def calculate_sortino_ratio_sol(
    sol_series: pd.Series, risk_free_rate: float = 0.0
) -> float:
    """
    Sortino Ratio - Pénalise seulement downside volatility
    """
    returns = calculate_sol_returns(sol_series)

    if len(returns) == 0:
        return 0.0

    excess_returns = returns - risk_free_rate / 365
    downside_returns = returns[returns < 0]

    if len(downside_returns) == 0 or downside_returns.std() == 0:
        return float("inf") if excess_returns.mean() > 0 else 0.0

    sortino = (excess_returns.mean() / downside_returns.std()) * np.sqrt(365)

    return sortino


def calculate_max_drawdown_sol(sol_series: pd.Series) -> Dict:
    """
    Max Drawdown en SOL

    Returns:
        {max_dd_pct, max_dd_sol, peak_sol, trough_sol}
    """
    cummax = sol_series.cummax()
    drawdown = cummax - sol_series
    drawdown_pct = (drawdown / cummax) * 100

    max_dd_idx = drawdown_pct.idxmax()

    return {
        "max_dd_pct": drawdown_pct.max(),
        "max_dd_sol": drawdown.max(),
        "peak_sol": cummax[max_dd_idx],
        "trough_sol": sol_series[max_dd_idx],
        "max_dd_date": max_dd_idx,
    }


def calculate_calmar_ratio_sol(sol_series: pd.Series) -> float:
    """
    Calmar Ratio = Rendement annualisé / Max Drawdown
    """
    if len(sol_series) < 2:
        return 0.0

    total_return = (sol_series.iloc[-1] / sol_series.iloc[0]) - 1
    days = (sol_series.index[-1] - sol_series.index[0]).days
    annual_return = (1 + total_return) ** (365 / days) - 1

    max_dd = calculate_max_drawdown_sol(sol_series)["max_dd_pct"]

    if max_dd == 0:
        return float("inf") if annual_return > 0 else 0.0

    return (annual_return * 100) / max_dd


def calculate_win_rate(trades: List[Dict]) -> Dict:
    """
    Statistiques win rate
    """
    if not trades:
        return {
            "win_rate": 0.0,
            "avg_win_sol": 0.0,
            "avg_loss_sol": 0.0,
            "profit_factor": 0.0,
        }

    winning = [t for t in trades if t["pnl_sol"] > 0]
    losing = [t for t in trades if t["pnl_sol"] < 0]

    win_rate = len(winning) / len(trades) * 100

    avg_win = np.mean([t["pnl_sol"] for t in winning]) if winning else 0.0
    avg_loss = np.mean([t["pnl_sol"] for t in losing]) if losing else 0.0

    total_wins = sum(t["pnl_sol"] for t in winning)
    total_losses = abs(sum(t["pnl_sol"] for t in losing))

    profit_factor = total_wins / total_losses if total_losses > 0 else float("inf")

    return {
        "win_rate": win_rate,
        "avg_win_sol": avg_win,
        "avg_loss_sol": avg_loss,
        "profit_factor": profit_factor,
    }


def calculate_risk_frontier(
    leverage_range: List[float], results: Dict[float, Dict]
) -> pd.DataFrame:
    """
    Calcule frontière du risque

    Pour chaque leverage:
    - SOL final moyen
    - Taux liquidation
    - Sharpe ratio
    - Max drawdown

    Returns:
        DataFrame avec metrics par leverage
    """
    frontier = []

    for lev in leverage_range:
        if lev not in results:
            continue

        result = results[lev]

        frontier.append(
            {
                "leverage": lev,
                "sol_final": result["sol_final"],
                "sol_change_pct": result["sol_change_pct"],
                "liquidation_rate": (
                    result["liquidations"] / result["total_trades"] * 100
                    if result["total_trades"] > 0
                    else 0
                ),
                "sharpe_ratio": result["sharpe_ratio"],
                "max_drawdown": result["max_drawdown"],
                "total_trades": result["total_trades"],
            }
        )

    return pd.DataFrame(frontier).sort_values("leverage")


def print_sol_metrics(bot, results_df: pd.DataFrame):
    """
    Affiche métriques SOL de manière HONNÊTE
    """
    summary = bot.get_summary()
    sol_series = results_df["collateral_sol"]

    print("\n" + "=" * 70)
    print("📊 PERFORMANCE MÉTRIQUES - VÉRITÉ ABSOLUE")
    print("=" * 70)

    print(f"\n🪙 SOL REALITY CHECK:")
    print(f"   Initial (owned):       {summary['initial_sol']:.4f} SOL")
    print(f"   Final (owned):         {summary['final_sol']:.4f} SOL")
    print(f"   Currently Exposed:     {summary['exposed_sol']:.4f} SOL")
    print(
        f"   Change (owned):        {summary['sol_change']:+.4f} SOL ({summary['sol_change_pct']:+.2f}%)"
    )
    print(f"   Peak (owned, not exposed): {summary['peak_sol']:.4f} SOL")

    print(f"\n📈 TRADING STATS:")
    print(f"   Total Trades:   {summary['total_trades']}")
    if summary["total_trades"] > 0:
        print(
            f"   Liquidations:   {summary['liquidations']} ({summary['liquidations']/summary['total_trades']*100:.1f}%)"
        )
        print(f"   Win Rate:       {summary['win_rate']:.1f}%")
        print(f"   Total Fees:     ${summary['total_fees_usd']:.2f}")
    else:
        print(f"   ⚠️  NO TRADES EXECUTED")
        print(f"   Liquidations:   {summary['liquidations']}")

    # Sharpe & Sortino (ajustés sur SOL owned)
    sharpe = calculate_sharpe_ratio_sol(sol_series)
    sortino = calculate_sortino_ratio_sol(sol_series)
    calmar = calculate_calmar_ratio_sol(sol_series)

    print(f"\n📊 RISK-ADJUSTED RETURNS (on owned SOL):")
    print(f"   Sharpe Ratio:   {sharpe:.2f}")
    print(f"   Sortino Ratio:  {sortino:.2f}")
    print(f"   Calmar Ratio:   {calmar:.2f}")

    # Drawdown RÉEL
    dd = calculate_max_drawdown_sol(sol_series)
    print(f"\n⚠️  DRAWDOWN ANALYSIS (on owned SOL):")
    print(f"   Max DD (SOL):   {dd['max_dd_sol']:.4f} SOL")
    print(f"   Max DD (%):     {dd['max_dd_pct']:.2f}%")

    if summary["liquidated"]:
        print(f"   💀 REAL LOSS:    {summary['real_drawdown_pct']:.0f}% (liquidation)")
        print(f"   Survival Rate:   {len(results_df)/426*100:.1f}% of period")

    print(f"   Peak → Trough:  {dd['peak_sol']:.4f} → {dd['trough_sol']:.4f} SOL")

    print("=" * 70 + "\n")
