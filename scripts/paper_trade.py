"""
SOL Grid Bot Pro - Mode Paper Trading
Architecture propre avec argparse + config YAML
Compatible avec GridBotV3 via wrapper stratégie
"""

# Ajoute la racine du projet au PYTHONPATH
# Permet les imports comme from config.config_loader import load_config
# même quand on lance depuis scripts/

import sys
from pathlib import Path

import asyncio
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# === CORRECTION IMPORT : Ajout racine au PYTHONPATH ===
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

# Configuration logging (doit venir après les imports de base)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

import pandas as pd
import numpy as np
from exchange_simulator import ExchangeSimulator
from src.core.grid_bot import GridBotV3

# from config.config_loader import load_config
from src.config.config_loader import load_config

# Log de confirmation (optionnel, tu peux supprimer plus tard)
logging.info(f"Racine projet ajoutée au PYTHONPATH : {project_root}")


def parse_arguments():
    """Parse arguments CLI"""
    parser = argparse.ArgumentParser(
        description="SOL Grid Bot - Paper Trading Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Mode replay avec config par défaut
  python paper_trade.py

  # Config conservative
  python paper_trade.py --config config/conservative.yaml

  # Config aggressive avec données custom
  python paper_trade.py --config config/aggressive.yaml --data data/SOL_2023.csv

  # Mode live (futur)
  python paper_trade.py --mode live --config config/default.yaml
        """,
    )

    parser.add_argument(
        "--config",
        type=str,
        default="config/default.yaml",
        help="Chemin vers fichier YAML de configuration (default: config/default.yaml)",
    )

    parser.add_argument(
        "--data",
        type=str,
        default="data/SOL_2021_2022.csv",
        help="Fichier CSV avec données historiques (default: data/SOL_2021_2022.csv)",
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=["replay", "live"],
        default="replay",
        help="Mode: replay (historique) ou live (temps réel, WIP)",
    )

    parser.add_argument(
        "--sleep",
        type=float,
        default=0.3,
        help="Délai entre cycles en secondes (default: 0.3)",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Niveau de logging (default: INFO)",
    )

    parser.add_argument(
        "--symbol",
        type=str,
        default="SBTC/SUSDT:SUSDT",
        help="Symbole trading (default: SBTC/SUSDT:SUSDT)",
    )

    return parser.parse_args()


def dataclass_to_dict(config_dataclass) -> Dict:
    """
    Convertit config dataclass en dict plat pour GridBotV3

    Args:
        config_dataclass: GridBotConfig dataclass

    Returns:
        Dict avec clés plates pour GridBotV3
    """
    return {
        "initial_capital": config_dataclass.trading.initial_capital,
        "leverage": config_dataclass.trading.leverage,
        "grid_size": config_dataclass.grid_strategy.grid_size,
        "grid_ratio": config_dataclass.grid_strategy.grid_ratio,
        "max_position_size": config_dataclass.grid_strategy.max_position_size,
        "trading_fee": config_dataclass.trading.taker_fee,
        "maker_fee": config_dataclass.trading.maker_fee,
        "max_simultaneous_positions": config_dataclass.grid_strategy.max_simultaneous_positions,
        "min_grid_distance": config_dataclass.grid_strategy.min_grid_distance,
        "adaptive_spacing": config_dataclass.grid_strategy.adaptive_spacing,
        "maintenance_margin": config_dataclass.risk_management.maintenance_margin,
        "safety_buffer": config_dataclass.risk_management.safety_buffer,
        "max_portfolio_drawdown": config_dataclass.risk_management.max_portfolio_drawdown,
        "volatility_lookback": config_dataclass.risk_management.volatility_lookback,
        "adaptive_leverage": config_dataclass.risk_management.adaptive_leverage_enabled,
    }


class GridBotStrategy:
    """
    Wrapper pour GridBotV3 qui expose une interface stratégie unifiée
    Compatible avec l'architecture paper trading
    """

    def __init__(self, config: Dict, initial_price: float):
        self.config = config
        self.bot = GridBotV3(
            config=config,
            initial_capital=config["initial_capital"],
            initial_price=initial_price,
        )
        self.price_history = []

    def analyze_signal(
        self, data: pd.DataFrame, current_price: float, has_position: bool
    ) -> Dict:
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
            timestamp=datetime.now(),
        )

        # Déterminer action basée sur l'état du bot
        if not has_position and len(self.bot.positions) > 0:
            # Bot vient d'ouvrir une position
            latest_pos = self.bot.positions[-1]
            return {
                "action": "BUY",
                "amount": latest_pos["size"] * current_price,
                "metadata": {
                    "grid_level": latest_pos["grid_level"],
                    "leverage": latest_pos["leverage"],
                    "state": state,
                },
            }

        elif has_position and len(self.bot.positions) == 0:
            # Bot vient de fermer la position
            return {
                "action": "SELL",
                "amount": None,
                "metadata": {"reason": "take_profit", "state": state},
            }

        else:
            # Pas de changement
            return {"action": "HOLD", "amount": None, "metadata": {"state": state}}


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
        action = signal["action"]
        position = self.simulator.get_position(self.symbol)
        has_position = position is not None

        if action == "BUY" and not has_position:
            amount = signal.get("amount", self.simulator.balance * 0.5)

            if amount > 100:
                try:
                    order = self.simulator.place_market_order(
                        self.symbol, "buy", amount, current_price
                    )
                    logging.info(
                        f"✅ BUY {order['quantity']:.6f} @ ${current_price:.2f} "
                        f"(${amount:.2f})"
                    )
                    return True
                except Exception as e:
                    logging.error(f"❌ Erreur BUY: {e}")
                    return False

        elif action == "SELL" and has_position:
            try:
                order = self.simulator.place_market_order(
                    self.symbol, "sell", position["quantity"], current_price
                )
                pnl_color = "+" if order["pnl"] > 0 else ""
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
            pnl_sign = "+" if position["unrealized_pnl"] > 0 else ""
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
    # Parse arguments
    args = parse_arguments()

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # Vérifier fichiers
    if not Path(args.config).exists():
        logging.error(f"❌ Config file not found: {args.config}")
        return

    if args.mode == "replay" and not Path(args.data).exists():
        logging.error(f"❌ Data file not found: {args.data}")
        return

    # Chargement config
    logging.info(f"📝 Loading config: {args.config}")
    config_dataclass = load_config(args.config)
    config = dataclass_to_dict(config_dataclass)

    # Header
    logging.info("\n" + "=" * 70)
    logging.info("🤖 SOL GRID BOT PRO - MODE PAPER TRADING")
    logging.info("=" * 70)
    logging.info(f"Config: {args.config}")
    logging.info(f"Mode: {args.mode}")
    logging.info(f"Symbol: {args.symbol}")
    logging.info(f"Leverage: {config['leverage']}x")
    logging.info(f"Grid size: {config['grid_size']}")
    logging.info(f"Grid ratio: {config['grid_ratio']}")
    logging.info(f"Capital initial: ${config['initial_capital']}")
    logging.info("=" * 70 + "\n")

    # Initialisation simulateur
    simulator = ExchangeSimulator(
        initial_balance=config["initial_capital"], base_currency="USDT"
    )

    # Chargement données
    if args.mode == "replay":
        logging.info(f"📂 Loading data: {args.data}")
        data = pd.read_csv(args.data, index_col=0, parse_dates=True)
        data = data[["close"]].dropna().sort_index()
        initial_price = float(data["close"].iloc[0])
        logging.info(
            f"✅ {len(data)} bougies chargées | "
            f"Prix initial: ${initial_price:.2f} | "
            f"Période: {data.index[0]} → {data.index[-1]}\n"
        )
    else:
        logging.error("❌ Mode 'live' pas encore implémenté")
        return

    # Initialisation stratégie
    strategy = GridBotStrategy(config, initial_price)

    # Initialisation moteur
    engine = PaperTradingEngine(args.symbol, strategy, simulator)

    # Loop principal
    try:
        for i, (timestamp, row) in enumerate(data.iterrows()):
            current_price = float(row["close"])
            engine.iterations = i + 1

            # Mise à jour prix positions
            simulator.update_prices({args.symbol: current_price})

            # Analyse signal
            position = simulator.get_position(args.symbol)
            has_position = position is not None

            signal = strategy.analyze_signal(data[: i + 1], current_price, has_position)

            # Exécution
            engine.execute_signal(signal, current_price)

            # Status périodique
            if i % 50 == 0:
                engine.print_status(current_price, signal)

            await asyncio.sleep(args.sleep)

    except KeyboardInterrupt:
        logging.info("\n⚠️  Arrêt manuel")

    finally:
        # Résumé final
        final_price = float(data["close"].iloc[-1]) if len(data) > 0 else initial_price
        current_prices = {args.symbol: final_price}

        logging.info("\n" + "=" * 70)
        logging.info("📊 RÉSUMÉ FINAL PAPER TRADING")
        logging.info("=" * 70)

        simulator.print_summary(current_prices)

        equity = simulator.get_total_equity(current_prices)
        pnl = equity - config["initial_capital"]
        pnl_pct = (pnl / config["initial_capital"]) * 100

        logging.info(f"\n💰 Equity finale: ${equity:.2f}")
        logging.info(f"📊 PnL: {pnl:+.2f} USD ({pnl_pct:+.2f}%)")
        logging.info("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
