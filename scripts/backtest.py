"""
Main Backtest - Version Production
Focus: Accumulation SOL + Frontière du Risque
"""

import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import logging
from pathlib import Path

from src.core.grid_bot import GridBotV3, run_backtest
from src.analysis.sol_metrics import print_sol_metrics, calculate_risk_frontier
from src.analysis.benchmarks import Benchmarks

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def load_data(filepath: str) -> pd.DataFrame:
    """Charge données historiques"""
    data = pd.read_csv(filepath, index_col=0, parse_dates=True)
    
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors='coerce')
    
    data = data.dropna(subset=['close'])
    
    # Sort by date (ascending)
    data = data.sort_index()
    
    logging.info(f"Loaded {len(data)} data points")
    logging.info(f"Date range: {data.index[0].date()} to {data.index[-1].date()}")
    logging.info(f"Price range: ${data['close'].min():.2f} - ${data['close'].max():.2f}")
    logging.info(f"First price: ${data['close'].iloc[0]:.2f}, Last price: ${data['close'].iloc[-1]:.2f}")
    
    return data


def plot_performance(results_df: pd.DataFrame, bot: GridBotV3, save_path: str = None):
    """Visualisation performance"""
    
    fig, axes = plt.subplots(3, 2, figsize=(16, 12))
    fig.suptitle('Grid Bot Performance Analysis - SOL Focused', fontsize=16, fontweight='bold')
    
    # 1. SOL Accumulation
    ax = axes[0, 0]
    ax.plot(results_df.index, results_df['collateral_sol'], linewidth=2, color='green')
    ax.axhline(bot.initial_sol, color='gray', linestyle='--', alpha=0.5, label='Initial')
    ax.set_title('SOL Accumulation Over Time')
    ax.set_ylabel('SOL Holdings')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 2. Portfolio Value USD
    ax = axes[0, 1]
    ax.plot(results_df.index, results_df['portfolio_value_usd'], linewidth=2, color='blue')
    ax.axhline(bot.initial_capital, color='gray', linestyle='--', alpha=0.5, label='Initial')
    ax.set_title('Portfolio Value (USD)')
    ax.set_ylabel('USD')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 3. Price Action
    ax = axes[1, 0]
    ax.plot(results_df.index, results_df['price'], linewidth=1.5, color='orange')
    ax.set_title('SOL/USD Price')
    ax.set_ylabel('Price (USD)')
    ax.grid(True, alpha=0.3)
    
    # 4. Active Positions
    ax = axes[1, 1]
    ax.plot(results_df.index, results_df['active_positions'], linewidth=2, color='purple')
    ax.set_title('Active Positions')
    ax.set_ylabel('Number of Positions')
    ax.grid(True, alpha=0.3)
    
    # 5. SOL Returns Distribution
    ax = axes[2, 0]
    sol_returns = results_df['collateral_sol'].pct_change().dropna() * 100
    ax.hist(sol_returns, bins=50, color='green', alpha=0.7, edgecolor='black')
    ax.axvline(0, color='red', linestyle='--', linewidth=2)
    ax.set_title('Daily SOL Returns Distribution')
    ax.set_xlabel('Return (%)')
    ax.set_ylabel('Frequency')
    ax.grid(True, alpha=0.3)
    
    # 6. Drawdown
    ax = axes[2, 1]
    cummax = results_df['collateral_sol'].cummax()
    drawdown = (cummax - results_df['collateral_sol']) / cummax * 100
    ax.fill_between(results_df.index, drawdown, alpha=0.3, color='red')
    ax.plot(results_df.index, drawdown, linewidth=1.5, color='darkred')
    ax.set_title('Drawdown (SOL %)')
    ax.set_ylabel('Drawdown (%)')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logging.info(f"Chart saved: {save_path}")
    else:
        plt.show()


def run_leverage_frontier_analysis(
    data: pd.DataFrame,
    base_config: dict,
    leverage_range: list
) -> pd.DataFrame:
    """
    Analyse frontière du risque sur différents leverages
    """
    logging.info(f"Running leverage frontier analysis: {leverage_range}")
    
    results = {}
    
    for leverage in leverage_range:
        config = base_config.copy()
        config['leverage'] = leverage
        
        logging.info(f"Testing leverage {leverage}x...")
        
        results_df, bot = run_backtest(data, config)
        summary = bot.get_summary()
        
        from src.analysis.sol_metrics import calculate_sharpe_ratio_sol
        sharpe = calculate_sharpe_ratio_sol(results_df['collateral_sol'])
        
        results[leverage] = {
            'sol_final': summary['final_sol'],
            'sol_change_pct': summary['sol_change_pct'],
            'total_trades': summary['total_trades'],
            'liquidations': summary['liquidations'],
            'sharpe_ratio': sharpe,
            'max_drawdown': summary['drawdown_pct']
        }
    
    frontier_df = calculate_risk_frontier(leverage_range, results)
    
    return frontier_df


def plot_risk_frontier(frontier_df: pd.DataFrame, save_path: str = None):
    """Visualise frontière du risque"""
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Risk Frontier Analysis - Leverage Impact', fontsize=16, fontweight='bold')
    
    # 1. SOL Final vs Leverage
    ax = axes[0, 0]
    ax.plot(frontier_df['leverage'], frontier_df['sol_final'], 
            marker='o', linewidth=2, markersize=8, color='green')
    ax.set_xlabel('Leverage')
    ax.set_ylabel('Final SOL Holdings')
    ax.set_title('SOL Accumulation by Leverage')
    ax.grid(True, alpha=0.3)
    
    # 2. Sharpe Ratio vs Leverage
    ax = axes[0, 1]
    ax.plot(frontier_df['leverage'], frontier_df['sharpe_ratio'], 
            marker='o', linewidth=2, markersize=8, color='blue')
    ax.axhline(0, color='red', linestyle='--', alpha=0.5)
    ax.set_xlabel('Leverage')
    ax.set_ylabel('Sharpe Ratio')
    ax.set_title('Risk-Adjusted Returns by Leverage')
    ax.grid(True, alpha=0.3)
    
    # 3. Liquidation Rate vs Leverage
    ax = axes[1, 0]
    ax.plot(frontier_df['leverage'], frontier_df['liquidation_rate'], 
            marker='o', linewidth=2, markersize=8, color='red')
    ax.set_xlabel('Leverage')
    ax.set_ylabel('Liquidation Rate (%)')
    ax.set_title('Liquidation Risk by Leverage')
    ax.grid(True, alpha=0.3)
    
    # 4. Risk-Return Scatter
    ax = axes[1, 1]
    scatter = ax.scatter(frontier_df['max_drawdown'], frontier_df['sol_change_pct'],
                        c=frontier_df['leverage'], s=200, cmap='viridis', 
                        edgecolors='black', linewidth=1.5)
    
    # Annotations
    for _, row in frontier_df.iterrows():
        ax.annotate(f"{row['leverage']:.0f}x", 
                   (row['max_drawdown'], row['sol_change_pct']),
                   fontsize=9, ha='center')
    
    ax.set_xlabel('Max Drawdown (%)')
    ax.set_ylabel('SOL Change (%)')
    ax.set_title('Risk-Return Profile')
    ax.grid(True, alpha=0.3)
    
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Leverage')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logging.info(f"Frontier chart saved: {save_path}")
    else:
        plt.show()


def main():
    parser = argparse.ArgumentParser(description='Grid Bot Backtest - SOL Focused')
    parser.add_argument('--data', required=True, help='Path to CSV data')
    parser.add_argument('--leverage', type=float, default=8, help='Leverage to use')
    parser.add_argument('--frontier', action='store_true', help='Run frontier analysis')
    parser.add_argument('--plot', action='store_true', help='Show plots')
    parser.add_argument('--save-plots', action='store_true', help='Save plots as PNG')
    
    args = parser.parse_args()
    
    # Load data
    data = load_data(args.data)
    
    # Base config (from proven v0.1.6.3)
    base_config = {
        'initial_capital': 1000,
        'grid_size': 7,
        'grid_ratio': 0.02,
        'leverage': args.leverage,
        'max_position_size': 0.3,
        'trading_fee': 0.001
    }
    
    # Run main backtest
    logging.info(f"Running backtest with leverage {args.leverage}x...")
    results_df, bot = run_backtest(data, base_config)
    
    # Print metrics
    print_sol_metrics(bot, results_df)
    
    # Benchmarks
    initial_price = float(data['close'].iloc[0])
    bench = Benchmarks(base_config['initial_capital'], initial_price, args.leverage)
    
    buy_hold = bench.buy_and_hold(data['close'])
    sell_hold = bench.sell_and_hold(data['close'])
    
    print("\n📊 BENCHMARK COMPARISON:")
    print(f"   Buy & Hold:  {(buy_hold.iloc[-1]/base_config['initial_capital']-1)*100:+.2f}%")
    print(f"   Sell & Hold: {(sell_hold.iloc[-1]/base_config['initial_capital']-1)*100:+.2f}%")
    print(f"   Grid Bot:    {bot.get_summary()['sol_change_pct']:+.2f}% (SOL)\n")
    
    # Plots
    if args.plot or args.save_plots:
        save_path = 'results/performance.png' if args.save_plots else None
        Path('results').mkdir(exist_ok=True)
        plot_performance(results_df, bot, save_path)
    
    # Frontier analysis
    if args.frontier:
        logging.info("Running risk frontier analysis...")
        leverage_range = [1, 2, 3, 5, 8, 10, 15, 20]
        frontier_df = run_leverage_frontier_analysis(data, base_config, leverage_range)
        
        print("\n" + "=" * 70)
        print("🎯 RISK FRONTIER ANALYSIS")
        print("=" * 70)
        print(frontier_df.to_string(index=False))
        print("=" * 70 + "\n")
        
        if args.plot or args.save_plots:
            save_path = 'results/risk_frontier.png' if args.save_plots else None
            plot_risk_frontier(frontier_df, save_path)


if __name__ == "__main__":
    main()