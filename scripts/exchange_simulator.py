#!/usr/bin/env python3
"""
exchange_simulator.py
Simulateur d'exchange pour paper trading
Version corrigée avec update_prices() et unrealized_pnl
"""

from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd


class ExchangeSimulator:
    """
    Simulateur d'exchange pour paper trading
    Gère les ordres virtuels, balance, et positions
    """

    def __init__(self, initial_balance: float = 10000, base_currency: str = 'USDT'):
        """
        Initialise le simulateur

        Args:
            initial_balance: Capital initial en USDT
            base_currency: Devise de base (USDT par défaut)
        """
        self.initial_balance = initial_balance
        self.base_currency = base_currency

        # État du compte
        self.balance = initial_balance
        self.positions: Dict[str, Dict] = {}
        self.orders: List[Dict] = []
        self.trade_history: List[Dict] = []

        print(f"💰 ExchangeSimulator initialisé avec {initial_balance} {base_currency}")

    def get_balance(self) -> float:
        """Retourne le solde cash disponible"""
        return self.balance

    def get_positions(self) -> Dict:
        """Retourne toutes les positions ouvertes"""
        return self.positions.copy()

    def get_position(self, symbol: str) -> Optional[Dict]:
        """
        Retourne la position pour un symbole

        Args:
            symbol: Symbole de la paire (ex: 'SBTC/SUSDT:SUSDT')

        Returns:
            Dict avec info position ou None si pas de position
        """
        return self.positions.get(symbol)

    def update_prices(self, current_prices: Dict[str, float]):
        """
        Met à jour les prix courants des positions et calcule PnL unrealized

        Args:
            current_prices: Dict {symbol: current_price}
        """
        for symbol, current_price in current_prices.items():
            if symbol in self.positions:
                pos = self.positions[symbol]
                pos['current_price'] = current_price

                # Calculer PnL unrealized
                pnl = (current_price - pos['avg_price']) * pos['quantity']
                pnl_percent = ((current_price / pos['avg_price']) - 1) * 100

                pos['unrealized_pnl'] = pnl
                pos['unrealized_pnl_percent'] = pnl_percent

    def place_market_order(self, symbol: str, side: str, amount: float,
                          current_price: float) -> Dict:
        """
        Place un ordre market (exécution immédiate)

        Args:
            symbol: Symbole de la paire
            side: 'buy' ou 'sell'
            amount: Quantité à acheter/vendre (en USDT pour buy, en unités pour sell)
            current_price: Prix actuel du marché

        Returns:
            Dict avec détails de l'ordre exécuté
        """
        timestamp = datetime.now()

        if side.lower() == 'buy':
            return self._execute_buy(symbol, amount, current_price, timestamp)
        elif side.lower() == 'sell':
            return self._execute_sell(symbol, amount, current_price, timestamp)
        else:
            raise ValueError(f"Side invalide: {side}. Doit être 'buy' ou 'sell'")

    def _execute_buy(self, symbol: str, amount_usdt: float, price: float,
                     timestamp: datetime) -> Dict:
        """
        Exécute un ordre d'achat

        Args:
            symbol: Symbole
            amount_usdt: Montant en USDT à investir
            price: Prix d'achat
            timestamp: Timestamp de l'ordre
        """
        # Vérifier fonds suffisants
        if amount_usdt > self.balance:
            raise ValueError(
                f"Fonds insuffisants. Besoin: {amount_usdt} USDT, "
                f"Disponible: {self.balance} USDT"
            )

        # Calculer quantité
        quantity = amount_usdt / price

        # Mettre à jour balance
        self.balance -= amount_usdt

        # Créer ou mettre à jour position
        if symbol in self.positions:
            # Position existante: calculer prix moyen
            pos = self.positions[symbol]
            old_quantity = pos['quantity']
            old_avg_price = pos['avg_price']

            new_quantity = old_quantity + quantity
            new_avg_price = (
                (old_quantity * old_avg_price + quantity * price) / new_quantity
            )

            self.positions[symbol] = {
                'quantity': new_quantity,
                'avg_price': new_avg_price,
                'current_price': price,
                'side': 'long',
                'opened_at': pos['opened_at'],
                'updated_at': timestamp,
                'unrealized_pnl': 0.0,
                'unrealized_pnl_percent': 0.0
            }
        else:
            # Nouvelle position
            self.positions[symbol] = {
                'quantity': quantity,
                'avg_price': price,
                'current_price': price,
                'side': 'long',
                'opened_at': timestamp,
                'updated_at': timestamp,
                'unrealized_pnl': 0.0,
                'unrealized_pnl_percent': 0.0
            }

        # Enregistrer l'ordre
        order = {
            'symbol': symbol,
            'side': 'buy',
            'type': 'market',
            'amount_usdt': amount_usdt,
            'quantity': quantity,
            'price': price,
            'timestamp': timestamp,
            'status': 'filled'
        }

        self.orders.append(order)
        self.trade_history.append(order)

        print(f"✅ BUY {quantity:.8f} {symbol} @ ${price:.2f} (Total: ${amount_usdt:.2f})")

        return order

    def _execute_sell(self, symbol: str, quantity: float, price: float,
                      timestamp: datetime) -> Dict:
        """
        Exécute un ordre de vente

        Args:
            symbol: Symbole
            quantity: Quantité à vendre (en unités crypto)
            price: Prix de vente
            timestamp: Timestamp de l'ordre
        """
        # Vérifier que la position existe
        if symbol not in self.positions:
            raise ValueError(f"Aucune position ouverte pour {symbol}")

        pos = self.positions[symbol]

        # Vérifier quantité suffisante
        if quantity > pos['quantity']:
            raise ValueError(
                f"Quantité insuffisante. Demandé: {quantity}, "
                f"Disponible: {pos['quantity']}"
            )

        # Calculer montant de la vente
        amount_usdt = quantity * price

        # Calculer PnL
        pnl = (price - pos['avg_price']) * quantity
        pnl_percent = ((price / pos['avg_price']) - 1) * 100

        # Mettre à jour balance
        self.balance += amount_usdt

        # Mettre à jour ou fermer position
        if quantity >= pos['quantity']:
            # Fermer complètement la position
            del self.positions[symbol]
            print(f"🔴 CLOSE {symbol} @ ${price:.2f} | PnL: ${pnl:+.2f} ({pnl_percent:+.2f}%)")
        else:
            # Réduire la position
            pos['quantity'] -= quantity
            pos['current_price'] = price
            pos['updated_at'] = timestamp
            print(f"📉 SELL {quantity:.8f} {symbol} @ ${price:.2f} | PnL: ${pnl:+.2f}")

        # Enregistrer l'ordre
        order = {
            'symbol': symbol,
            'side': 'sell',
            'type': 'market',
            'quantity': quantity,
            'price': price,
            'amount_usdt': amount_usdt,
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'timestamp': timestamp,
            'status': 'filled'
        }

        self.orders.append(order)
        self.trade_history.append(order)

        return order

    def calculate_pnl(self, symbol: str, current_price: float) -> Dict:
        """
        Calcule le PnL d'une position

        Args:
            symbol: Symbole
            current_price: Prix actuel du marché

        Returns:
            Dict avec PnL unrealized
        """
        if symbol not in self.positions:
            return {'pnl': 0, 'pnl_percent': 0}

        pos = self.positions[symbol]
        pnl = (current_price - pos['avg_price']) * pos['quantity']
        pnl_percent = ((current_price / pos['avg_price']) - 1) * 100

        return {
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'unrealized': True
        }

    def get_total_equity(self, current_prices: Dict[str, float]) -> float:
        """
        Calcule l'equity totale (cash + valeur des positions)

        Args:
            current_prices: Dict {symbol: current_price}

        Returns:
            Equity totale en USDT
        """
        equity = self.balance

        for symbol, pos in self.positions.items():
            current_price = current_prices.get(symbol, pos['current_price'])
            position_value = pos['quantity'] * current_price
            equity += position_value

        return equity

    def get_summary(self, current_prices: Optional[Dict[str, float]] = None) -> Dict:
        """
        Retourne un résumé complet du compte

        Args:
            current_prices: Dict optionnel avec prix actuels

        Returns:
            Dict avec résumé complet
        """
        if current_prices is None:
            current_prices = {}

        equity = self.get_total_equity(current_prices)

        # Calculer PnL total unrealized
        total_pnl = 0
        for symbol, pos in self.positions.items():
            current_price = current_prices.get(symbol, pos['current_price'])
            pnl_info = self.calculate_pnl(symbol, current_price)
            total_pnl += pnl_info['pnl']

        # Stats des trades
        total_trades = len(self.trade_history)
        winning_trades = len([t for t in self.trade_history
                             if t.get('pnl', 0) > 0])

        return {
            'initial_balance': self.initial_balance,
            'current_balance': self.balance,
            'total_equity': equity,
            'total_pnl': equity - self.initial_balance,
            'total_pnl_percent': ((equity / self.initial_balance) - 1) * 100,
            'unrealized_pnl': total_pnl,
            'open_positions': len(self.positions),
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0
        }

    def print_summary(self, current_prices: Optional[Dict[str, float]] = None):
        """Affiche un résumé lisible du compte"""
        summary = self.get_summary(current_prices)

        print(f"\n{'='*60}")
        print(f"📊 RÉSUMÉ DU COMPTE")
        print(f"{'='*60}")
        print(f"💰 Balance (Cash):        ${summary['current_balance']:,.2f}")
        print(f"💼 Equity totale:         ${summary['total_equity']:,.2f}")
        print(f"📈 PnL total:             ${summary['total_pnl']:+,.2f} "
              f"({summary['total_pnl_percent']:+.2f}%)")
        print(f"📊 PnL non réalisé:       ${summary['unrealized_pnl']:+,.2f}")
        print(f"📢 Positions ouvertes:    {summary['open_positions']}")
        print(f"🔢 Trades total:          {summary['total_trades']}")
        print(f"✅ Win rate:              {summary['win_rate']:.1f}%")
        print(f"{'='*60}\n")

    def reset(self):
        """Réinitialise le simulateur à l'état initial"""
        self.balance = self.initial_balance
        self.positions = {}
        self.orders = []
        self.trade_history = []
        print(f"🔄 Simulateur réinitialisé")


# ============================================================================
# TESTS
# ============================================================================

def run_tests():
    """Tests de base du simulateur"""
    print("\n" + "="*60)
    print("🧪 TESTS DU SIMULATEUR")
    print("="*60 + "\n")

    # Initialiser
    sim = ExchangeSimulator(initial_balance=10000)

    # Test 1: Acheter BTC
    print("TEST 1: Acheter BTC")
    order1 = sim.place_market_order('SBTC/SUSDT:SUSDT', 'buy', 5000, 50000)
    assert sim.balance == 5000, "Balance incorrecte après achat"
    assert 'SBTC/SUSDT:SUSDT' in sim.positions
    print("✅ Test 1 réussi\n")

    # Test 2: Update prices
    print("TEST 2: Update prices et PnL unrealized")
    sim.update_prices({'SBTC/SUSDT:SUSDT': 52000})
    pos = sim.get_position('SBTC/SUSDT:SUSDT')
    assert 'unrealized_pnl' in pos
    print(f"PnL unrealized: ${pos['unrealized_pnl']:.2f} ({pos['unrealized_pnl_percent']:.2f}%)")
    print("✅ Test 2 réussi\n")

    # Test 3: Acheter plus de BTC (prix moyen)
    print("TEST 3: Acheter plus de BTC")
    order2 = sim.place_market_order('SBTC/SUSDT:SUSDT', 'buy', 2000, 51000)
    pos = sim.get_position('SBTC/SUSDT:SUSDT')
    assert pos['quantity'] > 0.1, "Quantité incorrecte"
    print("✅ Test 3 réussi\n")

    # Test 4: Calculer PnL
    print("TEST 4: Calculer PnL")
    pnl = sim.calculate_pnl('SBTC/SUSDT:SUSDT', 53000)
    print(f"PnL à 53000$: ${pnl['pnl']:.2f} ({pnl['pnl_percent']:.2f}%)")
    print("✅ Test 4 réussi\n")

    # Test 5: Vendre partiellement
    print("TEST 5: Vendre partiellement")
    pos = sim.get_position('SBTC/SUSDT:SUSDT')
    sell_qty = pos['quantity'] / 2
    order3 = sim.place_market_order('SBTC/SUSDT:SUSDT', 'sell', sell_qty, 52000)
    assert 'SBTC/SUSDT:SUSDT' in sim.positions
    print("✅ Test 5 réussi\n")

    # Test 6: Fermer position
    print("TEST 6: Fermer position complète")
    pos = sim.get_position('SBTC/SUSDT:SUSDT')
    order4 = sim.place_market_order('SBTC/SUSDT:SUSDT', 'sell', pos['quantity'], 53000)
    assert 'SBTC/SUSDT:SUSDT' not in sim.positions
    print("✅ Test 6 réussi\n")

    # Test 7: Résumé
    print("TEST 7: Résumé du compte")
    sim.print_summary()
    print("✅ Test 7 réussi\n")

    print("="*60)
    print("✅ TOUS LES TESTS RÉUSSIS")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_tests()