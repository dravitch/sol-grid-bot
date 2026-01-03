"""
Grid Optimizer - Recherche Paramètres Optimaux
Objectif: Maximiser SOL final SANS liquidation
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from itertools import product
import logging
from tqdm import tqdm

from src.core.grid_bot import run_backtest


class GridOptimizer:
    """
    Optimiseur pour trouver meilleurs paramètres grid
    Focus: Survie + Accumulation SOL
    """

    def __init__(self, data: pd.DataFrame, initial_capital: float = 1000):
        self.data = data
        self.initial_capital = initial_capital
        self.results = []

    def optimize(
        self,
        grid_size_range: List[int],
        grid_ratio_range: List[float],
        leverage_range: List[float],
        max_position_range: List[float],
        max_combinations: int = 1000,
    ) -> pd.DataFrame:
        """
        Teste toutes combinaisons et retourne meilleures
        """
        # Génère toutes combinaisons
        all_combos = list(
            product(
                grid_size_range, grid_ratio_range, leverage_range, max_position_range
            )
        )

        # Sample si trop
        if len(all_combos) > max_combinations:
            np.random.seed(42)
            indices = np.random.choice(len(all_combos), max_combinations, replace=False)
            combos = [all_combos[i] for i in indices]
            logging.info(
                f"Sampling {max_combinations} from {len(all_combos)} combinations"
            )
        else:
            combos = all_combos

        logging.info(f"Testing {len(combos)} parameter combinations...")

        # Teste chaque combo
        for grid_size, grid_ratio, leverage, max_pos in tqdm(combos, desc="Optimizing"):
            config = {
                "initial_capital": self.initial_capital,
                "grid_size": grid_size,
                "grid_ratio": grid_ratio,
                "leverage": leverage,
                "max_position_size": max_pos,
                "trading_fee": 0.001,
            }

            try:
                results_df, bot = run_backtest(self.data, config)
                summary = bot.get_summary()

                from src.analysis.sol_metrics import calculate_sharpe_ratio_sol

                sharpe = calculate_sharpe_ratio_sol(results_df["collateral_sol"])

                survival_rate = len(results_df) / len(self.data) * 100

                self.results.append(
                    {
                        "grid_size": grid_size,
                        "grid_ratio": grid_ratio,
                        "leverage": leverage,
                        "max_position": max_pos,
                        "sol_final": summary["final_sol"],
                        "sol_change_pct": summary["sol_change_pct"],
                        "liquidated": summary["liquidated"],
                        "survival_rate": survival_rate,
                        "total_trades": summary["total_trades"],
                        "liquidations": summary["liquidations"],
                        "sharpe_ratio": sharpe,
                        "max_drawdown": summary["drawdown_pct"],
                        "fees_paid": summary["total_fees_usd"],
                    }
                )

            except Exception as e:
                logging.warning(f"Failed combo: {e}")
                continue

        results_df = pd.DataFrame(self.results)
        results_df = results_df.sort_values("sol_final", ascending=False)

        return results_df

    def find_survival_zone(self, results_df: pd.DataFrame) -> Dict:
        """Identifie la zone de paramètres qui SURVIVENT"""
        survivors = results_df[~results_df["liquidated"]]

        if len(survivors) == 0:
            return {
                "survival_count": 0,
                "survival_rate": 0.0,
                "message": "AUCUNE CONFIG NE SURVIT - Réduire leverage!",
            }

        best_survivor = survivors.iloc[0]
        leverage_range = (survivors["leverage"].min(), survivors["leverage"].max())
        position_range = (
            survivors["max_position"].min(),
            survivors["max_position"].max(),
        )

        return {
            "survival_count": len(survivors),
            "survival_rate": len(survivors) / len(results_df) * 100,
            "best_config": {
                "grid_size": int(best_survivor["grid_size"]),
                "grid_ratio": float(best_survivor["grid_ratio"]),
                "leverage": float(best_survivor["leverage"]),
                "max_position": float(best_survivor["max_position"]),
                "sol_final": float(best_survivor["sol_final"]),
                "sharpe": float(best_survivor["sharpe_ratio"]),
            },
            "optimal_leverage_range": leverage_range,
            "optimal_position_range": position_range,
            "median_sol_final": float(survivors["sol_final"].median()),
            "median_sharpe": float(survivors["sharpe_ratio"].median()),
        }

    def plot_heatmap(self, results_df: pd.DataFrame, save_path: str = None):
        """Heatmap: Leverage vs Max Position → SOL Final"""
        import matplotlib.pyplot as plt

        pivot = results_df.pivot_table(
            values="sol_final", index="leverage", columns="max_position", aggfunc="mean"
        )

        fig, axes = plt.subplots(1, 2, figsize=(16, 6))

        # SOL Final
        ax = axes[0]
        im = ax.imshow(pivot.values, cmap="RdYlGn", aspect="auto")
        ax.set_xticks(range(len(pivot.columns)))
        ax.set_yticks(range(len(pivot.index)))
        ax.set_xticklabels([f"{x:.2f}" for x in pivot.columns])
        ax.set_yticklabels([f"{x:.1f}x" for x in pivot.index])
        ax.set_xlabel("Max Position Size")
        ax.set_ylabel("Leverage")
        ax.set_title("SOL Final by Parameters")
        plt.colorbar(im, ax=ax, label="Final SOL")

        for i in range(len(pivot.index)):
            for j in range(len(pivot.columns)):
                value = pivot.values[i, j]
                if not np.isnan(value):
                    color = "white" if value < pivot.values.mean() else "black"
                    ax.text(
                        j,
                        i,
                        f"{value:.1f}",
                        ha="center",
                        va="center",
                        color=color,
                        fontsize=8,
                    )

        # Liquidation Rate
        ax = axes[1]
        liq_pivot = results_df.pivot_table(
            values="liquidated",
            index="leverage",
            columns="max_position",
            aggfunc=lambda x: (x.sum() / len(x) * 100),
        )

        im2 = ax.imshow(
            liq_pivot.values, cmap="RdYlGn_r", aspect="auto", vmin=0, vmax=100
        )
        ax.set_xticks(range(len(liq_pivot.columns)))
        ax.set_yticks(range(len(liq_pivot.index)))
        ax.set_xticklabels([f"{x:.2f}" for x in liq_pivot.columns])
        ax.set_yticklabels([f"{x:.1f}x" for x in liq_pivot.index])
        ax.set_xlabel("Max Position Size")
        ax.set_ylabel("Leverage")
        ax.set_title("Liquidation Rate (%)")
        plt.colorbar(im2, ax=ax, label="Liquidation %")

        for i in range(len(liq_pivot.index)):
            for j in range(len(liq_pivot.columns)):
                value = liq_pivot.values[i, j]
                if not np.isnan(value):
                    color = "white" if value > 50 else "black"
                    ax.text(
                        j,
                        i,
                        f"{value:.0f}%",
                        ha="center",
                        va="center",
                        color=color,
                        fontsize=8,
                    )

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            logging.info(f"Heatmap saved: {save_path}")
        else:
            plt.show()


def print_optimization_results(results_df: pd.DataFrame, survival_zone: Dict):
    """Affiche résultats optimisation"""

    print("\n" + "=" * 70)
    print("🎯 OPTIMIZATION RESULTS - SURVIVAL ZONE")
    print("=" * 70)

    total_tested = len(results_df)
    survivors = results_df[~results_df["liquidated"]]

    print(f"\n📊 GLOBAL STATS:")
    print(f"   Total configs tested:  {total_tested}")
    print(
        f"   Survivors:             {len(survivors)} ({len(survivors)/total_tested*100:.1f}%)"
    )
    print(f"   Liquidated:            {total_tested - len(survivors)}")

    if len(survivors) == 0:
        print("\n⚠️  NO CONFIGURATION SURVIVED!")
        print("   → Reduce leverage or increase position spacing")
        return

    print(f"\n🏆 TOP 10 SURVIVORS:")
    for idx, row in survivors.head(10).iterrows():
        print(f"\n{idx+1}. SOL: {row['sol_final']:.2f} (+{row['sol_change_pct']:.0f}%)")
        print(
            f"   Lev: {row['leverage']:.1f}x, Grid: {row['grid_size']}, Ratio: {row['grid_ratio']:.3f}, Pos: {row['max_position']:.2f}"
        )

    best = survival_zone["best_config"]
    print(f"\n✅ BEST CONFIG:")
    print(f"   Leverage:      {best['leverage']:.1f}x")
    print(f"   Grid Size:     {best['grid_size']}")
    print(f"   Grid Ratio:    {best['grid_ratio']:.3f}")
    print(f"   Max Position:  {best['max_position']:.2f}")
    print(f"   → SOL Final:   {best['sol_final']:.2f}")
    print("=" * 70 + "\n")
