"""
Portfolio Manager pour Grid Bot SOL
Gestion du collatéral en SOL/USD, tracking PnL, et conversions
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class Trade:
    """Représente une transaction complète"""

    timestamp: datetime
    symbol: str
    side: str
    quantity: float
    price: float
    amount_usd: float
    leverage: float
    fees: float
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None


@dataclass
class Position:
    """Position ouverte dans le portfolio"""

    symbol: str
    entry_price: float
    quantity: float
    leverage: float
    liquidation_price: float
    grid_level: float
    opened_at: datetime = field(default_factory=datetime.now)
    peak_price: float = 0.0

    def __post_init__(self):
        if self.peak_price == 0.0:
            self.peak_price = self.entry_price

    @property
    def current_value_usd(self) -> float:
        """Valeur actuelle de la position"""
        return abs(self.quantity) * self.entry_price

    @property
    def is_short(self) -> bool:
        return self.quantity < 0


class Portfolio:
    """
    Gestionnaire de portfolio pour Grid Bot avec tracking SOL/USD.

    Suit précisément:
    - Collatéral en SOL (actif réel sur Bitget)
    - Conversion USD/SOL dynamique
    - PnL réalisé et non-réalisé
    - Historique des trades
    """

    def __init__(
        self,
        initial_capital: float,
        initial_price: float,
        leverage: float = 1.0,
        trading_fee: float = 0.001,
    ):
        """
        Initialise le portfolio.

        Args:
            initial_capital: Capital initial en USD
            initial_price: Prix initial SOL/USD
            leverage: Levier par défaut
            trading_fee: Taux de frais (0.001 = 0.1%)
        """
        self.initial_capital = initial_capital
        self.initial_price = initial_price
        self.leverage = leverage
        self.trading_fee = trading_fee

        # Collatéral en SOL (actif principal)
        self.initial_collateral_sol = initial_capital / initial_price
        self.collateral_sol = self.initial_collateral_sol

        # Capital USD (pour tracking)
        self.current_capital = initial_capital

        # Positions et trades
        self.positions: List[Position] = []
        self.trades: List[Trade] = []

        # Stats
        self.total_fees_paid = 0.0
        self.realized_pnl = 0.0
        self.peak_capital = initial_capital

    def get_current_value(self, current_price: float) -> float:
        """
        Calcule la valeur actuelle du portfolio en USD.

        Args:
            current_price: Prix actuel SOL/USD

        Returns:
            Valeur totale en USD
        """
        return self.collateral_sol * current_price

    def get_unrealized_pnl(self, current_price: float) -> float:
        """
        Calcule le PnL non-réalisé des positions ouvertes.

        Args:
            current_price: Prix actuel SOL/USD

        Returns:
            PnL non-réalisé en USD
        """
        unrealized = 0.0
        for pos in self.positions:
            if pos.is_short:
                pnl = (
                    (pos.entry_price - current_price) * abs(pos.quantity) * pos.leverage
                )
            else:
                pnl = (current_price - pos.entry_price) * pos.quantity * pos.leverage
            unrealized += pnl

        return unrealized

    def update_from_trade(
        self, pnl_usd: float, current_price: float, timestamp: datetime = None
    ) -> None:
        """
        Met à jour le portfolio après un trade.

        Convertit le PnL USD en SOL et ajuste le collatéral.

        Args:
            pnl_usd: Profit/Perte en USD
            current_price: Prix actuel SOL/USD
            timestamp: Timestamp du trade
        """
        # Conversion PnL USD -> SOL
        pnl_sol = pnl_usd / current_price

        # Mise à jour collatéral
        self.collateral_sol += pnl_sol
        self.current_capital += pnl_usd

        # Stats
        self.realized_pnl += pnl_usd
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital

    def add_position(self, position: Position) -> None:
        """Ajoute une position au portfolio"""
        self.positions.append(position)

    def remove_position(self, position: Position) -> None:
        """Retire une position du portfolio"""
        if position in self.positions:
            self.positions.remove(position)

    def get_position_by_symbol(self, symbol: str) -> Optional[Position]:
        """Récupère une position par symbole"""
        for pos in self.positions:
            if pos.symbol == symbol:
                return pos
        return None

    def record_trade(self, trade: Trade) -> None:
        """Enregistre un trade dans l'historique"""
        self.trades.append(trade)
        self.total_fees_paid += trade.fees

    def get_summary(self, current_price: float) -> Dict:
        """
        Résumé complet du portfolio.

        Args:
            current_price: Prix actuel SOL/USD

        Returns:
            Dictionnaire avec toutes les métriques
        """
        current_value = self.get_current_value(current_price)
        unrealized_pnl = self.get_unrealized_pnl(current_price)
        total_pnl = self.realized_pnl + unrealized_pnl

        # Calcul drawdown
        drawdown = (self.peak_capital - current_value) / self.peak_capital

        # Stats trades
        closed_trades = [t for t in self.trades if t.pnl is not None]
        winning_trades = [t for t in closed_trades if t.pnl > 0]

        return {
            "initial_capital": self.initial_capital,
            "current_value": current_value,
            "initial_sol": self.initial_collateral_sol,
            "current_sol": self.collateral_sol,
            "sol_change": self.collateral_sol - self.initial_collateral_sol,
            "sol_change_pct": (
                (self.collateral_sol / self.initial_collateral_sol - 1) * 100
            ),
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "total_pnl": total_pnl,
            "total_pnl_pct": (total_pnl / self.initial_capital) * 100,
            "drawdown": drawdown,
            "drawdown_pct": drawdown * 100,
            "active_positions": len(self.positions),
            "total_trades": len(closed_trades),
            "winning_trades": len(winning_trades),
            "win_rate": (
                (len(winning_trades) / len(closed_trades) * 100) if closed_trades else 0
            ),
            "total_fees": self.total_fees_paid,
            "avg_trade_pnl": (
                (self.realized_pnl / len(closed_trades)) if closed_trades else 0
            ),
        }

    def print_summary(self, current_price: float) -> None:
        """Affiche un résumé lisible du portfolio"""
        summary = self.get_summary(current_price)

        print("\n" + "=" * 60)
        print("📊 PORTFOLIO SUMMARY")
        print("=" * 60)
        print(f"💰 Capital Initial:     ${summary['initial_capital']:,.2f}")
        print(f"💼 Valeur Actuelle:     ${summary['current_value']:,.2f}")
        print(
            f"📈 PnL Total:           "
            f"${summary['total_pnl']:+,.2f} "
            f"({summary['total_pnl_pct']:+.2f}%)"
        )
        print(f"   - Réalisé:           ${summary['realized_pnl']:+,.2f}")
        print(f"   - Non-réalisé:       " f"${summary['unrealized_pnl']:+,.2f}")
        print("\n🪙 SOL Holdings:")
        print(f"   Initial:             {summary['initial_sol']:.4f} SOL")
        print(f"   Actuel:              {summary['current_sol']:.4f} SOL")
        print(
            f"   Change:              "
            f"{summary['sol_change']:+.4f} SOL "
            f"({summary['sol_change_pct']:+.2f}%)"
        )
        print("\n📊 Trading Stats:")
        print(f"   Positions actives:   {summary['active_positions']}")
        print(f"   Total trades:        {summary['total_trades']}")
        print(f"   Win rate:            {summary['win_rate']:.1f}%")
        print(f"   Avg trade PnL:       ${summary['avg_trade_pnl']:+.2f}")
        print("\n💸 Coûts:")
        print(f"   Total frais:         ${summary['total_fees']:.2f}")
        print(f"   Drawdown max:        {summary['drawdown_pct']:.2f}%")
        print("=" * 60 + "\n")


# Fonctions utilitaires
def usd_to_sol(amount_usd: float, price: float) -> float:
    """Convertit USD en SOL"""
    return amount_usd / price


def sol_to_usd(amount_sol: float, price: float) -> float:
    """Convertit SOL en USD"""
    return amount_sol * price


def calculate_position_pnl(
    entry_price: float,
    exit_price: float,
    quantity: float,
    leverage: float,
    is_short: bool = True,
) -> float:
    """
    Calcule le PnL d'une position.

    Args:
        entry_price: Prix d'entrée
        exit_price: Prix de sortie
        quantity: Quantité (valeur absolue)
        leverage: Levier utilisé
        is_short: True si position short

    Returns:
        PnL en USD
    """
    price_change = exit_price - entry_price

    if is_short:
        pnl = -price_change * quantity * leverage
    else:
        pnl = price_change * quantity * leverage

    return pnl
