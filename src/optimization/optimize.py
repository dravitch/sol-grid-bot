"""
Optimization Script - Trouve Paramètres Optimaux
Usage: python optimize.py --data data/SOL_2021_2022.csv
"""

import os
import sys
import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# from src.optimization.grid_optimizer import GridOptimizer, print_optimization_results
from grid_optimizer import GridOptimizer, print_optimization_results
from main import load_data

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def main():
    parser = argparse.ArgumentParser(description="Grid Bot Optimization")
    parser.add_argument("--data", required=True, help="Path to CSV data")
    parser.add_argument(
        "--mode",
        choices=["quick", "medium", "extensive"],
        default="medium",
        help="Optimization mode",
    )
    parser.add_argument("--save-plots", action="store_true", help="Save plots")

    args = parser.parse_args()

    # Load data
    data = load_data(args.data)

    # Define search space based on mode
    if args.mode == "quick":
        # Quick test (100 combos)
        grid_size_range = [5, 7]
        grid_ratio_range = [0.02, 0.03, 0.05]
        leverage_range = [2, 3, 5]
        max_position_range = [0.2, 0.3]
        max_combinations = 100

    elif args.mode == "medium":
        # Medium test (500 combos)
        grid_size_range = [3, 5, 7, 10]
        grid_ratio_range = [0.015, 0.02, 0.03, 0.05]
        leverage_range = [1.5, 2, 3, 5, 8]
        max_position_range = [0.15, 0.2, 0.25, 0.3]
        max_combinations = 500

    else:  # extensive
        # Full search (1000+ combos)
        grid_size_range = [3, 5, 7, 10, 15, 20]
        grid_ratio_range = [0.01, 0.015, 0.02, 0.03, 0.05, 0.08]
        leverage_range = [1, 1.5, 2, 3, 5, 8, 10]
        max_position_range = [0.1, 0.15, 0.2, 0.25, 0.3, 0.4]
        max_combinations = 1000

    logging.info(f"Starting {args.mode} optimization...")
    logging.info(
        f"Search space: {len(grid_size_range) * len(grid_ratio_range) * len(leverage_range) * len(max_position_range)} combinations"
    )

    # Run optimization
    optimizer = GridOptimizer(data)
    results_df = optimizer.optimize(
        grid_size_range,
        grid_ratio_range,
        leverage_range,
        max_position_range,
        max_combinations,
    )

    # Save results
    Path("results").mkdir(exist_ok=True)
    results_df.to_csv("results/optimization_results.csv", index=False)
    logging.info("Results saved: results/optimization_results.csv")

    # Find survival zone
    survival_zone = optimizer.find_survival_zone(results_df)

    # Print results
    print_optimization_results(results_df, survival_zone)

    # Plot heatmaps
    if args.save_plots:
        optimizer.plot_heatmap(results_df, "results/optimization_heatmap.png")

    # Save best config
    if survival_zone["survival_count"] > 0:
        best_config = survival_zone["best_config"]

        import yaml

        config_path = "config/optimized.yaml"

        config_yaml = {
            "trading": {
                "symbol": "SOL-USD",
                "initial_capital": 1000,
                "grid_size": best_config["grid_size"],
                "grid_ratio": best_config["grid_ratio"],
                "leverage": best_config["leverage"],
                "max_position_size": best_config["max_position"],
                "trading_fee": 0.001,
            },
            "risk_management": {"maintenance_margin": 0.05, "safety_buffer": 1.5},
            "performance": {
                "sol_final": best_config["sol_final"],
                "sharpe_ratio": best_config["sharpe"],
            },
        }

        Path("config").mkdir(exist_ok=True)
        with open(config_path, "w") as f:
            yaml.dump(config_yaml, f, default_flow_style=False)

        logging.info(f"Best config saved: {config_path}")


if __name__ == "__main__":
    main()
