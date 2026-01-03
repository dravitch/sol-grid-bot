"""
Grid Optimizer Extrême - Recherche exhaustive
1000 combinaisons pour trouver configuration optimale
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

import numpy as np
import pandas as pd
from itertools import product
import logging
from tqdm import tqdm
from datetime import datetime

from core.grid_bot import run_backtest
from data.data_loader import DataLoader

logging.basicConfig(level=logging.WARNING)  # Moins de bruit


class GridOptimizerExtreme:
    """Optimiseur avec recherche exhaustive sur grille étendue"""
    
    def __init__(self, data: pd.DataFrame, initial_capital: float = 1000):
        self.data = data
        self.initial_capital = initial_capital
        self.results = []
        
    def optimize(
        self,
        grid_size_range: list,
        grid_ratio_range: list,
        leverage_range: list,
        max_position_range: list,
        max_combinations: int = 1000,
        stop_loss_range: list = None
    ) -> pd.DataFrame:
        """
        Teste toutes combinaisons possibles
        
        Returns:
            DataFrame trié par SOL final (descendant)
        """
        # Génère toutes combinaisons
        all_combos = list(product(
            grid_size_range,
            grid_ratio_range,
            leverage_range,
            max_position_range
        ))
        
        # Sample si trop
        if len(all_combos) > max_combinations:
            np.random.seed(42)
            indices = np.random.choice(len(all_combos), max_combinations, replace=False)
            combos = [all_combos[i] for i in indices]
            print(f"🔬 Sampling {max_combinations} from {len(all_combos):,} combinations")
        else:
            combos = all_combos
            print(f"🔬 Testing {len(combos):,} combinations")
        
        print(f"📊 Search space:")
        print(f"   Grid Size:     {min(grid_size_range)} - {max(grid_size_range)}")
        print(f"   Grid Ratio:    {min(grid_ratio_range):.3f} - {max(grid_ratio_range):.3f}")
        print(f"   Leverage:      {min(leverage_range)}x - {max(leverage_range)}x")
        print(f"   Max Position:  {min(max_position_range):.2f} - {max(max_position_range):.2f}")
        print()
        
        # Teste chaque combo avec progress bar
        for grid_size, grid_ratio, leverage, max_pos in tqdm(combos, desc="🔄 Optimizing"):
            config = {
                'initial_capital': self.initial_capital,
                'grid_size': int(grid_size),
                'grid_ratio': float(grid_ratio),
                'leverage': float(leverage),
                'max_position_size': float(max_pos),
                'trading_fee': 0.001,
                'emergency_stop_loss': 0.15,
                'min_liq_distance': 0.50,
                'adaptive': True
            }
            
            try:
                results_df, bot = run_backtest(self.data, config)
                summary = bot.get_summary()
                
                # Calculate metrics
                returns = results_df['collateral_sol'].pct_change().dropna()
                sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0
                
                survival_rate = len(results_df) / len(self.data) * 100
                
                # Portfolio value final (USD)
                final_price = float(self.data['close'].iloc[-1])
                final_value_usd = summary['final_sol'] * final_price
                total_return_usd = (final_value_usd / self.initial_capital - 1) * 100
                
                self.results.append({
                    'grid_size': int(grid_size),
                    'grid_ratio': float(grid_ratio),
                    'leverage': float(leverage),
                    'max_position': float(max_pos),
                    'sol_initial': summary['initial_sol'],
                    'sol_final': summary['final_sol'],
                    'sol_change_pct': summary['sol_change_pct'],
                    'value_usd_final': final_value_usd,
                    'return_usd_pct': total_return_usd,
                    'liquidated': summary['liquidated'],
                    'survival_rate': survival_rate,
                    'total_trades': summary['total_trades'],
                    'win_rate': summary['win_rate'],
                    'sharpe_ratio': sharpe,
                    'max_drawdown': summary['drawdown_pct'],
                    'fees_paid': summary['total_fees_usd']
                })
                
            except Exception as e:
                # Skip failed configs
                continue
        
        # Convert to DataFrame
        results_df = pd.DataFrame(self.results)
        
        # Sort by SOL final (descending)
        results_df = results_df.sort_values('sol_final', ascending=False).reset_index(drop=True)
        
        return results_df
    
    def print_top_results(self, results_df: pd.DataFrame, top_n: int = 10):
        """Affiche top N résultats avec formatage"""
        
        print("\n" + "="*100)
        print(f"🏆 TOP {top_n} CONFIGURATIONS - CLASSEMENT PAR SOL FINAL")
        print("="*100)
        
        # Filter survivors only
        survivors = results_df[~results_df['liquidated']]
        
        if len(survivors) == 0:
            print("❌ AUCUNE CONFIGURATION N'A SURVÉCU!")
            print("\n🔴 Top 10 liquidées (pour analyse):")
            top_configs = results_df.head(top_n)
        else:
            print(f"✅ {len(survivors)}/{len(results_df)} configurations ont survécu ({len(survivors)/len(results_df)*100:.1f}%)")
            print(f"\n🏆 Top {min(top_n, len(survivors))} survivors:\n")
            top_configs = survivors.head(top_n)
        
        for idx, row in top_configs.iterrows():
            rank = idx + 1
            
            # Status emoji
            if row['liquidated']:
                status = "💀"
            elif row['return_usd_pct'] > 100:
                status = "🚀"
            elif row['return_usd_pct'] > 0:
                status = "✅"
            else:
                status = "📉"
            
            print(f"{status} #{rank}")
            print(f"   {'─'*90}")
            print(f"   📊 CONFIGURATION:")
            print(f"      Grid Size:     {row['grid_size']:>3} niveaux")
            print(f"      Grid Ratio:    {row['grid_ratio']:>6.3f} ({row['grid_ratio']*100:.1f}% spacing)")
            print(f"      Leverage:      {row['leverage']:>6.1f}x")
            print(f"      Max Position:  {row['max_position']:>6.2f} ({row['max_position']*100:.0f}%)")
            
            print(f"   💰 PERFORMANCE:")
            print(f"      SOL: {row['sol_initial']:.4f} → {row['sol_final']:.4f} ({row['sol_change_pct']:+.1f}%)")
            print(f"      USD: ${self.initial_capital:.0f} → ${row['value_usd_final']:.2f} ({row['return_usd_pct']:+.1f}%)")
            
            print(f"   📈 MÉTRIQUES:")
            print(f"      Trades:        {row['total_trades']:.0f}")
            print(f"      Win Rate:      {row['win_rate']:.1f}%")
            print(f"      Sharpe:        {row['sharpe_ratio']:.2f}")
            print(f"      Max DD:        {row['max_drawdown']:.1f}%")
            print(f"      Liquidé:       {'❌ OUI' if row['liquidated'] else '✅ NON'}")
            print()
        
        print("="*100)
        
        # Statistics
        print("\n📊 STATISTIQUES GLOBALES:")
        print(f"   Configurations testées:    {len(results_df):,}")
        print(f"   Survivors:                 {len(survivors):,} ({len(survivors)/len(results_df)*100:.1f}%)")
        print(f"   Liquidations:              {len(results_df[results_df['liquidated']]):,}")
        
        if len(survivors) > 0:
            print(f"\n   SOL Final:")
            print(f"      Median:                {survivors['sol_final'].median():.4f} SOL")
            print(f"      Mean:                  {survivors['sol_final'].mean():.4f} SOL")
            print(f"      Best:                  {survivors['sol_final'].max():.4f} SOL")
            print(f"      Worst (survivor):      {survivors['sol_final'].min():.4f} SOL")
            
            print(f"\n   USD Return:")
            print(f"      Median:                {survivors['return_usd_pct'].median():+.1f}%")
            print(f"      Mean:                  {survivors['return_usd_pct'].mean():+.1f}%")
            print(f"      Best:                  {survivors['return_usd_pct'].max():+.1f}%")
            print(f"      Worst (survivor):      {survivors['return_usd_pct'].min():+.1f}%")
        
        print("="*100)


# ============================================================================
# SCRIPT PRINCIPAL
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*100)
    print("🔬 SOL GRID BOT PRO - OPTIMISATION EXTRÊME")
    print("="*100)
    print()
    
    # Load data
    print("📥 Chargement données SOL-USD...")
    loader = DataLoader()
    data = loader.load_historical_data('SOL-USD', '2021-10-31', '2022-12-31')
    
    print(f"✅ {len(data)} jours chargés")
    print(f"   Prix: ${data['close'].iloc[0]:.2f} → ${data['close'].iloc[-1]:.2f} ({((data['close'].iloc[-1]/data['close'].iloc[0])-1)*100:.1f}%)")
    print()
    
    # Define search space (EXTRÊME)
    grid_size_range = [3, 5, 7, 10, 15, 20, 30, 50]
    grid_ratio_range = [0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20, 0.30, 0.50]
    leverage_range = [1, 2, 3, 5, 8, 10, 15, 20]
    max_position_range = [0.10, 0.15, 0.20, 0.30, 0.40, 0.50, 0.70, 1.0]
    
    # Initialize optimizer
    optimizer = GridOptimizerExtreme(data, initial_capital=1000)
    
    # Run optimization
    print("🚀 Lancement optimisation (1000 combinaisons)...")
    print()
    
    results_df = optimizer.optimize(
        grid_size_range,
        grid_ratio_range,
        leverage_range,
        max_position_range,
        max_combinations=1000
    )
    
    # Print top results
    optimizer.print_top_results(results_df, top_n=10)
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = Path('results') / f'optimization_{timestamp}.csv'
    output_path.parent.mkdir(exist_ok=True)
    
    results_df.to_csv(output_path, index=False)
    print(f"\n💾 Résultats complets sauvegardés: {output_path}")
    
    # Save top 10
    top10_path = Path('results') / f'top10_{timestamp}.csv'
    survivors = results_df[~results_df['liquidated']]
    if len(survivors) > 0:
        survivors.head(10).to_csv(top10_path, index=False)
        print(f"💾 Top 10 sauvegardé: {top10_path}")
    
    print("\n✅ Optimisation terminée!")