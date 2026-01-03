"""
SOL Grid Bot Pro - Mode Paper Trading
Architecture inspirée de paper_trading_live.py
Compatible avec GridBotV3 via wrapper stratégie
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

import pandas as pd
import numpy as np

from exchange_simulator import ExchangeSimulator
from src.core.grid_bot import GridBotV3

# === CONFIGURATION ===
USE_HISTORICAL_REPLAY = True
DATA_FILE = "data/SOL_2021_2022.csv"
SLEEP_BETWEEN_CYCLES = 0.3
SYMBOL = "SBTC/SUSDT:SUSDT"

CONFIG = {
    'initial_capital': 1000,
    'grid_size': 7,
    'grid_ratio': 0.02,
    'leverage': 8,
    'max_position_size': 0.3,
    'trading_fee': 0.001
}
# =====================


class GridBotStrategy:
    """
    Wrapper pour GridBotV3 qui expose une interface stratégie unifiée
    Compatible avec l'architecture paper trading
    """
    
    def __init__(self, config: Dict, initial_price: float):
        self.config = config
        self.bot = GridBotV3(
            config=config,
            initial_capital=config['initial_capital'],
            initial_price=initial_price
        )
        self.price_history = []
        
    def analyze_signal(self, data: pd.DataFrame, current_price: float, 
                      has_position: bool) -> Dict:
        """
        Analyse et retourne signal de trading
        
        Returns:
            {
                'action': 'BUY' | 'SELL' | 'HOLD',
                'amount': float (si BUY/SELL),
                'metadata': dict
            }
        """
        # Mise à jour historique prix
        self.price_history.append(current_price)
        if len(self.price_history) > 100:
            self.price_history.pop(0)
        
        # Construire price_series pour volatilité
        price_series = pd.Series(self.price_history)
        
        # Appeler la logique de GridBotV3
        state = self.bot.step(
            current_price=current_price,
            price_series=price_series,
            timestamp=datetime.now()
        )
        
        # Déterminer action basée sur l'état du bot
        # GridBotV3 gère ses positions en interne, on extrait juste l'action
        
        if not has_position and len(self.bot.positions) > 0:
            # Bot vient d'ouvrir une position
            latest_pos = self.bot.positions[-1]
            return {
                'action': 'BUY',
                'amount': latest_pos['size'] * current_price,
                'metadata': {
                    'grid_level': latest_pos['grid_level'],
                    'leverage': latest_pos['leverage'],
                    'state': state
                }
            }
        
        elif has_position and len(self.bot.positions) == 0:
            # Bot vient de fermer la position
            return {
                'action': 'SELL',
                'amount': None,  # Fermeture complète
                'metadata': {
                    'reason': 'take_profit',
                    'state': state
                }
            }
        
        else:
            # Pas de changement
            return {
                'action': 'HOLD',
                'amount': None,
                'metadata': {'state': state}
            }


class PaperTradingEngine:
    """
    Moteur de paper trading générique
    Compatible avec n'importe quelle stratégie
    """
    
    def __init__(self, symbol: str, strategy, simulator: ExchangeSimulator):
        self.symbol = symbol
        self.strategy = strategy
        self.simulator = simulator
        self.iterations = 0
        
    def execute_signal(self, signal: Dict, current_price: float) -> bool:
        """
        Exécute le signal de trading
        
        Returns:
            True si ordre exécuté
        """
        action = signal['action']
        position = self.simulator.get_position(self.symbol)
        has_position = position is not None
        
        if action == 'BUY' and not has_position:
            amount = signal.get('amount', self.simulator.balance * 0.5)
            
            if amount > 100:
                try:
                    order = self.simulator.place_market_order(
                        self.symbol, 'buy', amount, current_price
                    )
                    logging.info(
                        f"✅ BUY {order['quantity']:.6f} @ ${current_price:.2f} "
                        f"(${amount:.2f})"
                    )
                    return True
                except Exception as e:
                    logging.error(f"❌ Erreur BUY: {e}")
                    return False
        
        elif action == 'SELL' and has_position:
            try:
                order = self.simulator.place_market_order(
                    self.symbol, 'sell', position['quantity'], current_price
                )
                pnl_color = "+" if order['pnl'] > 0 else ""
                logging.info(
                    f"🔴 SELL {order['quantity']:.6f} @ ${current_price:.2f} "
                    f"| PnL: {pnl_color}${order['pnl']:.2f} ({pnl_color}{order['pnl_percent']:.2f}%)"
                )
                return True
            except Exception as e:
                logging.error(f"❌ Erreur SELL: {e}")
                return False
        
        return False
    
    def print_status(self, current_price: float, signal: Dict):
        """Affiche statut actuel"""
        position = self.simulator.get_position(self.symbol)
        
        logging.info(f"\n{'='*70}")
        logging.info(f"CYCLE {self.iterations} | Prix ${current_price:.2f}")
        logging.info(f"Signal: {signal['action']}")
        
        if position:
            pnl_sign = "+" if position['unrealized_pnl'] > 0 else ""
            logging.info(
                f"Position: {position['quantity']:.6f} @ ${position['avg_price']:.2f} "
                f"| PnL: {pnl_sign}${position['unrealized_pnl']:.2f}"
            )
        else:
            logging.info("Position: Aucune")
        
        summary = self.simulator.get_summary()
        logging.info(
            f"Cash: ${summary['current_balance']:.2f} | "
            f"Equity: ${summary['total_equity']:.2f} | "
            f"Trades: {summary['total_trades']}"
        )
        logging.info(f"{'='*70}\n")


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logging.info("=== SOL GRID BOT PRO - MODE PAPER TRADING ===")
    logging.info(f"Leverage: {CONFIG['leverage']}x")
    logging.info(f"Grid size: {CONFIG['grid_size']}")
    logging.info(f"Capital initial: ${CONFIG['initial_capital']}\n")

    # 1. Initialisation simulateur
    simulator = ExchangeSimulator(
        initial_balance=CONFIG['initial_capital'],
        base_currency='USDT'
    )

    # 2. Chargement données
    if USE_HISTORICAL_REPLAY:
        data = pd.read_csv(DATA_FILE, index_col=0, parse_dates=True)
        data = data[['close']].dropna().sort_index()
        initial_price = float(data['close'].iloc[0])
        logging.info(f"✅ {len(data)} bougies chargées | Prix initial: ${initial_price:.2f}\n")
    else:
        data = pd.DataFrame({'close': [100.0] * 500})
        initial_price = 100.0
        logging.info("Mode test prix fixe\n")

    # 3. Initialisation stratégie
    strategy = GridBotStrategy(CONFIG, initial_price)

    # 4. Initialisation moteur
    engine = PaperTradingEngine(SYMBOL, strategy, simulator)

    # 5. Loop principal
    try:
        for i, (timestamp, row) in enumerate(data.iterrows()):
            current_price = float(row['close'])
            engine.iterations = i + 1
            
            # Mise à jour prix positions
            simulator.update_prices({SYMBOL: current_price})
            
            # Analyse signal
            position = simulator.get_position(SYMBOL)
            has_position = position is not None
            
            signal = strategy.analyze_signal(data[:i+1], current_price, has_position)
            
            # Exécution
            engine.execute_signal(signal, current_price)
            
            # Status périodique
            if i % 50 == 0:
                engine.print_status(current_price, signal)
            
            await asyncio.sleep(SLEEP_BETWEEN_CYCLES)

    except KeyboardInterrupt:
        logging.info("\n⚠️  Arrêt manuel")

    finally:
        # Résumé final
        final_price = float(data['close'].iloc[-1]) if len(data) > 0 else initial_price
        current_prices = {SYMBOL: final_price}
        
        logging.info("\n" + "="*70)
        logging.info("📊 RÉSUMÉ FINAL PAPER TRADING")
        logging.info("="*70)
        
        simulator.print_summary(current_prices)
        
        equity = simulator.get_total_equity(current_prices)
        pnl = equity - CONFIG['initial_capital']
        pnl_pct = (pnl / CONFIG['initial_capital']) * 100
        
        logging.info(f"\nEquity finale: ${equity:.2f}")
        logging.info(f"PnL: {pnl:+.2f} USD ({pnl_pct:+.2f}%)")
        logging.info("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())