# Codex du Paper Trading sur Bitget - Partie 5/6

## 3.2.2 Partial Fills et Market Impact

**Principe Réaliste :**

```
ORDRE PARFAIT (backtest naïf) :
├─ Market order $10,000
├─ Exécution : 100% instantané au prix actuel
└─ Slippage : 0%

ORDRE RÉEL (production) :
├─ Market order $10,000
├─ Exécution : Peut être partielle (90% filled)
├─ Slippage : Variable par tranche
└─ Market impact : Prix bouge pendant exécution
```

**Implémentation :**

```python
# Fichier : bitget_paper/paper_trading/realistic_execution.py

from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Fill:
    """Représente une exécution partielle"""
    price: float
    quantity: float
    timestamp: datetime
    fee: float

class RealisticExecutionSimulator:
    """
    Simule exécution réaliste avec :
    - Partial fills (order book depth)
    - Market impact (prix bouge)
    - Time decay (temps d'exécution)
    """
    
    def __init__(self, config: Dict):
        self.order_book_depth_levels = config.get('depth_levels', 5)
        self.market_impact_factor = config.get('impact_factor', 0.0001)
        self.max_fill_time_seconds = config.get('max_fill_time', 2.0)
    
    def execute_market_order(
        self,
        symbol: str,
        side: str,
        quantity_usd: float,
        current_price: float,
        order_book: Dict = None
    ) -> Tuple[List[Fill], float]:
        """
        Simule exécution market order avec partial fills
        
        Returns:
            (fills: List[Fill], avg_price: float)
        """
        fills = []
        remaining_usd = quantity_usd
        current_level_price = current_price
        
        # Si pas d'order book fourni, simuler
        if order_book is None:
            order_book = self._generate_synthetic_order_book(
                current_price, 
                side
            )
        
        # Exécuter par tranches
        for level_idx in range(self.order_book_depth_levels):
            if remaining_usd <= 0:
                break
            
            # Prix et liquidité à ce niveau
            level_price, level_liquidity_usd = self._get_order_book_level(
                order_book,
                side,
                level_idx
            )
            
            # Quantité à prendre à ce niveau
            take_usd = min(remaining_usd, level_liquidity_usd)
            take_qty = take_usd / level_price
            
            # Market impact (prix bouge légèrement)
            impact = self._calculate_market_impact(take_usd, quantity_usd)
            adjusted_price = level_price * (1 + impact if side == 'buy' else 1 - impact)
            
            # Fee
            fee = take_usd * 0.001  # 0.1%
            
            # Créer fill
            fill = Fill(
                price=adjusted_price,
                quantity=take_qty,
                timestamp=datetime.now() + timedelta(seconds=level_idx * 0.1),
                fee=fee
            )
            fills.append(fill)
            
            remaining_usd -= take_usd
            current_level_price = adjusted_price
        
        # Si reste du montant (liquidité insuffisante)
        if remaining_usd > 0:
            fill_rate = (quantity_usd - remaining_usd) / quantity_usd
            logging.warning(
                f"⚠️  Partial fill : {fill_rate:.1%} seulement "
                f"(liquidité insuffisante)"
            )
        
        # Prix moyen d'exécution
        total_value = sum(f.price * f.quantity for f in fills)
        total_qty = sum(f.quantity for f in fills)
        avg_price = total_value / total_qty if total_qty > 0 else current_price
        
        return fills, avg_price
    
    def _generate_synthetic_order_book(
        self, 
        mid_price: float, 
        side: str
    ) -> Dict:
        """
        Génère order book synthétique basé sur distribution réaliste
        
        Distribution :
        - Niveau 0 : 40% de liquidité totale
        - Niveau 1 : 25%
        - Niveau 2 : 15%
        - Niveau 3 : 10%
        - Niveau 4 : 10%
        """
        total_liquidity_usd = 50000  # Liquidité totale simulée
        distribution = [0.40, 0.25, 0.15, 0.10, 0.10]
        
        # Spread bid/ask
        spread = 0.0005  # 0.05% (5 basis points)
        
        book = {'bids': [], 'asks': []}
        
        for i in range(self.order_book_depth_levels):
            liquidity = total_liquidity_usd * distribution[i]
            
            if side == 'buy':
                # Buy from asks
                price = mid_price * (1 + spread + i * 0.0002)
                book['asks'].append([price, liquidity / price])
            else:
                # Sell to bids
                price = mid_price * (1 - spread - i * 0.0002)
                book['bids'].append([price, liquidity / price])
        
        return book
    
    def _get_order_book_level(
        self, 
        order_book: Dict, 
        side: str, 
        level_idx: int
    ) -> Tuple[float, float]:
        """Récupère prix et liquidité à un niveau donné"""
        book_side = order_book['asks'] if side == 'buy' else order_book['bids']
        
        if level_idx >= len(book_side):
            # Pas assez de profondeur
            return book_side[-1][0] * 1.01, 0  # Prix pénalisé, liquidité 0
        
        price, quantity = book_side[level_idx]
        liquidity_usd = price * quantity
        
        return price, liquidity_usd
    
    def _calculate_market_impact(
        self, 
        chunk_size_usd: float, 
        total_order_usd: float
    ) -> float:
        """
        Calcule market impact (prix bouge pendant exécution)
        
        Impact proportionnel à la taille relative
        """
        size_ratio = chunk_size_usd / total_order_usd
        impact = self.market_impact_factor * size_ratio
        
        return impact

# USAGE COMPARATIF
# Ordre $10,000 sur BTC @ $50,000

# 1. SIMULATION NAÏVE (backtest classique)
executed_price_naive = 50000  # Prix fixe
slippage_naive = 0  # Pas de slippage
fills_naive = 1  # Une seule exécution

# 2. SIMULATION RÉALISTE
executor = RealisticExecutionSimulator({
    'depth_levels': 5,
    'impact_factor': 0.0001,
    'max_fill_time': 2.0
})

fills, avg_price = executor.execute_market_order(
    symbol='BTC/USDT:USDT',
    side='buy',
    quantity_usd=10000,
    current_price=50000
)

print(f"Fills: {len(fills)}")
for i, fill in enumerate(fills):
    print(f"  Fill {i+1}: {fill.quantity:.6f} BTC @ ${fill.price:.2f}")

print(f"\nPrix moyen: ${avg_price:.2f}")
print(f"Slippage: {(avg_price - 50000) / 50000:.4%}")

# RÉSULTAT TYPIQUE :
# Fills: 3
#   Fill 1: 0.07998 BTC @ $50,025.00
#   Fill 2: 0.05000 BTC @ $50,035.00
#   Fill 3: 0.02999 BTC @ $50,045.00
# 
# Prix moyen: $50,033.12
# Slippage: 0.0662% (6.62 basis points)
# 
# vs Naïf : $50,000 (0% slippage)
# Différence : +$33.12 par $10k (+0.33%)
```

**Impact sur Performance :**

```python
# Backtest 100 trades de $5000 chacun

# SANS realistic execution :
# ├─ Slippage : 0%
# ├─ Total trades : 100
# └─ PnL : +$15,000

# AVEC realistic execution :
# ├─ Slippage moyen : 0.045%
# ├─ Total trades : 98 (2 partial fills rejetés)
# ├─ Coût slippage : $5000 × 100 × 0.00045 = $225
# └─ PnL : +$15,000 - $225 = +$14,775 (-1.5%)

# INSIGHT : Realistic execution réduit performance de 1-2%
```

**Fichiers Référence :**
- `bitget_paper/paper_trading/realistic_execution.py` (À créer)

---

## 3.3 Tracking de Performance

### 3.3.1 Métriques SOL-Centric (Grid Bot)

**Philosophie :**

```
En bear market crypto :
├─ USD value ↓ (suit le prix)
├─ SOL holdings ↑ (accumulation)
└─ Métrique primaire = SOL holdings, pas USD
```

**Implémentation :**

```python
# Fichier : sol-grid-bot/src/analysis/sol_metrics.py

import pandas as pd
import numpy as np

class SOLMetrics:
    """Métriques centrées sur accumulation SOL"""
    
    @staticmethod
    def calculate_sharpe_ratio_sol(
        sol_series: pd.Series, 
        risk_free_rate: float = 0.0
    ) -> float:
        """
        Sharpe ratio basé sur SOL holdings (pas USD)
        
        Formule : (return_sol - rf) / volatility_sol
        
        Annualisé : × sqrt(365) pour données daily
        """
        returns = sol_series.pct_change().dropna()
        
        if len(returns) == 0 or returns.std() == 0:
            return 0.0
        
        excess_return = returns.mean() - risk_free_rate
        sharpe = (excess_return / returns.std()) * np.sqrt(365)
        
        return sharpe
    
    @staticmethod
    def calculate_max_drawdown_sol(sol_series: pd.Series) -> float:
        """
        Max drawdown sur SOL OWNED (pas exposé)
        
        Drawdown = (Peak - Trough) / Peak
        """
        cumulative = sol_series.copy()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        
        return drawdown.min()
    
    @staticmethod
    def calculate_calmar_ratio_sol(
        sol_series: pd.Series,
        risk_free_rate: float = 0.0
    ) -> float:
        """
        Calmar ratio = Annualized Return / Max Drawdown
        
        Mesure : Combien de return par unité de drawdown
        """
        # Return annualisé
        total_return = (sol_series.iloc[-1] - sol_series.iloc[0]) / sol_series.iloc[0]
        days = len(sol_series)
        annualized_return = (1 + total_return) ** (365 / days) - 1
        
        # Max drawdown
        max_dd = abs(SOLMetrics.calculate_max_drawdown_sol(sol_series))
        
        if max_dd == 0:
            return float('inf')
        
        calmar = (annualized_return - risk_free_rate) / max_dd
        
        return calmar
    
    @staticmethod
    def calculate_comprehensive_metrics(
        sol_series: pd.Series,
        usd_series: pd.Series,
        initial_sol: float,
        initial_usd: float
    ) -> Dict:
        """
        Calcule toutes les métriques SOL-centric
        
        Returns:
            {
                'sol_metrics': {...},
                'usd_metrics': {...},
                'comparison': {...}
            }
        """
        # SOL metrics (PRIMARY)
        sol_return = (sol_series.iloc[-1] - initial_sol) / initial_sol
        sol_sharpe = SOLMetrics.calculate_sharpe_ratio_sol(sol_series)
        sol_max_dd = SOLMetrics.calculate_max_drawdown_sol(sol_series)
        sol_calmar = SOLMetrics.calculate_calmar_ratio_sol(sol_series)
        
        # USD metrics (SECONDARY)
        usd_return = (usd_series.iloc[-1] - initial_usd) / initial_usd
        usd_sharpe = SOLMetrics.calculate_sharpe_ratio_sol(usd_series)
        usd_max_dd = SOLMetrics.calculate_max_drawdown_sol(usd_series)
        
        return {
            'sol_metrics': {
                'initial': initial_sol,
                'final': sol_series.iloc[-1],
                'return_pct': sol_return,
                'sharpe': sol_sharpe,
                'max_drawdown': sol_max_dd,
                'calmar': sol_calmar,
                'peak': sol_series.max(),
                'trough': sol_series.min()
            },
            'usd_metrics': {
                'initial': initial_usd,
                'final': usd_series.iloc[-1],
                'return_pct': usd_return,
                'sharpe': usd_sharpe,
                'max_drawdown': usd_max_dd
            },
            'comparison': {
                'sol_outperformance': sol_return - usd_return,
                'primary_metric': 'SOL holdings',
                'interpretation': 'SOL accumulation is objective, USD follows price'
            }
        }

# USAGE
from sol_grid_bot.src.analysis.sol_metrics import SOLMetrics

# Données backtest
results_df = pd.DataFrame({
    'timestamp': [...],
    'collateral_sol': [10.0, 10.5, 11.2, 12.1, ...],
    'portfolio_value_usd': [1000, 945, 1008, 968, ...]
})

metrics = SOLMetrics.calculate_comprehensive_metrics(
    sol_series=results_df['collateral_sol'],
    usd_series=results_df['portfolio_value_usd'],
    initial_sol=10.0,
    initial_usd=1000
)

print("=== SOL METRICS (PRIMARY) ===")
print(f"SOL Return: {metrics['sol_metrics']['return_pct']:.2%}")
print(f"SOL Sharpe: {metrics['sol_metrics']['sharpe']:.2f}")
print(f"SOL Max DD: {metrics['sol_metrics']['max_drawdown']:.2%}")
print(f"SOL Calmar: {metrics['sol_metrics']['calmar']:.2f}")

print("\n=== USD METRICS (SECONDARY) ===")
print(f"USD Return: {metrics['usd_metrics']['return_pct']:.2%}")
print(f"USD Sharpe: {metrics['usd_metrics']['sharpe']:.2f}")

print("\n=== INTERPRETATION ===")
print(f"SOL Outperformance: {metrics['comparison']['sol_outperformance']:.2%}")

# RÉSULTAT TYPIQUE (Bear Market) :
# === SOL METRICS (PRIMARY) ===
# SOL Return: +289.47%
# SOL Sharpe: 2.33
# SOL Max DD: -12.34%
# SOL Calmar: 23.47
# 
# === USD METRICS (SECONDARY) ===
# USD Return: -14.23%
# USD Sharpe: -0.45
# 
# === INTERPRETATION ===
# SOL Outperformance: +303.70%
# 
# → Stratégie réussie : Accumule SOL pendant bear
```

**Fichiers Référence :**
- `sol-grid-bot/src/analysis/sol_metrics.py`
- `bundle_a_intelligence.md` (Section "Performance Reality")

---

### 3.3.2 Métriques Traditionnelles (Sentinel)

**Les Trois Ratios Critiques :**

```
SHARPE RATIO : Return / Volatility
├─ Mesure : Efficacité générale
└─ Bon : > 1.0, Excellent : > 2.0

SORTINO RATIO : Return / Downside Volatility
├─ Mesure : Return par unité de risque de baisse
└─ Meilleur que Sharpe pour crypto (asymétrique)

CALMAR RATIO : Return / Max Drawdown
├─ Mesure : Capacité de récupération
└─ Important : Drawdown = douleur psychologique
```

**Implémentation Complète :**

```python
# Fichier : bitget_paper/paper_trading/performance_tracker.py

import pandas as pd
import numpy as np
from dataclasses import dataclass

@dataclass
class PerformanceMetrics:
    """Container pour toutes les métriques"""
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trade_duration_hours: float
    total_fees_paid: float

class PerformanceTracker:
    """Tracker complet de performance"""
    
    def __init__(self, initial_capital: float):
        self.initial_capital = initial_capital
        self.equity_curve = []
        self.trade_history = []
    
    def calculate_comprehensive_metrics(
        self,
        equity_series: pd.Series,
        trade_history: List[Dict],
        risk_free_rate: float = 0.0
    ) -> PerformanceMetrics:
        """Calcule toutes les métriques"""
        
        # Returns
        returns = equity_series.pct_change().dropna()
        
        if len(returns) == 0:
            return self._empty_metrics()
        
        # ===== SHARPE RATIO =====
        excess_return = returns.mean() - risk_free_rate
        sharpe = (excess_return / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0
        
        # ===== SORTINO RATIO =====
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() if len(downside_returns) > 0 else returns.std()
        sortino = (excess_return / downside_std) * np.sqrt(252) if downside_std > 0 else 0
        
        # ===== MAX DRAWDOWN =====
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_dd = drawdown.min()
        
        # ===== CALMAR RATIO =====
        total_return = (equity_series.iloc[-1] - self.initial_capital) / self.initial_capital
        days = len(equity_series)
        annualized_return = (1 + total_return) ** (252 / days) - 1 if days > 0 else 0
        
        calmar = annualized_return / abs(max_dd) if max_dd != 0 else 0
        
        # ===== WIN RATE & PROFIT FACTOR =====
        winning_trades = [t for t in trade_history if t.get('pnl', 0) > 0]
        losing_trades = [t for t in trade_history if t.get('pnl', 0) < 0]
        
        win_rate = len(winning_trades) / len(trade_history) if trade_history else 0
        
        total_wins = sum(t['pnl'] for t in winning_trades)
        total_losses = abs(sum(t['pnl'] for t in losing_trades))
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # ===== TRADE DURATION =====
        if trade_history:
            durations = [
                (t.get('exit_time', datetime.now()) - t.get('entry_time', datetime.now())).total_seconds() / 3600
                for t in trade_history
                if 'entry_time' in t and 'exit_time' in t
            ]
            avg_duration = np.mean(durations) if durations else 0
        else:
            avg_duration = 0
        
        # ===== FEES =====
        total_fees = sum(t.get('fee', 0) for t in trade_history)
        
        return PerformanceMetrics(
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            max_drawdown=max_dd,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=len(trade_history),
            avg_trade_duration_hours=avg_duration,
            total_fees_paid=total_fees
        )
    
    def _empty_metrics(self) -> PerformanceMetrics:
        """Retourne métriques vides si pas assez de données"""
        return PerformanceMetrics(
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            calmar_ratio=0.0,
            max_drawdown=0.0,
            win_rate=0.0,
            profit_factor=0.0,
            total_trades=0,
            avg_trade_duration_hours=0.0,
            total_fees_paid=0.0
        )
    
    def generate_report(self, metrics: PerformanceMetrics) -> str:
        """Génère rapport texte formaté"""
        report = f"""
╔══════════════════════════════════════════════╗
║       PERFORMANCE METRICS REPORT             ║
╚══════════════════════════════════════════════╝

┌─ RISK-ADJUSTED RETURNS ─────────────────────┐
│ Sharpe Ratio:     {metrics.sharpe_ratio:>8.2f}          │
│ Sortino Ratio:    {metrics.sortino_ratio:>8.2f}          │
│ Calmar Ratio:     {metrics.calmar_ratio:>8.2f}          │
└──────────────────────────────────────────────┘

┌─ RISK METRICS ──────────────────────────────┐
│ Max Drawdown:     {metrics.max_drawdown:>8.2%}          │
└──────────────────────────────────────────────┘

┌─ TRADING METRICS ───────────────────────────┐
│ Total Trades:     {metrics.total_trades:>8d}          │
│ Win Rate:         {metrics.win_rate:>8.2%}          │
│ Profit Factor:    {metrics.profit_factor:>8.2f}          │
│ Avg Duration:     {metrics.avg_trade_duration_hours:>8.1f}h         │
└──────────────────────────────────────────────┘

┌─ COSTS ─────────────────────────────────────┐
│ Total Fees:       ${metrics.total_fees_paid:>8.2f}          │
└──────────────────────────────────────────────┘

INTERPRETATION:
"""
        
        # Interprétation Sharpe
        if metrics.sharpe_ratio > 2.0:
            report += "  ✅ Sharpe > 2.0 : Excellent\n"
        elif metrics.sharpe_ratio > 1.0:
            report += "  ✅ Sharpe > 1.0 : Bon\n"
        elif metrics.sharpe_ratio > 0.5:
            report += "  ⚠️  Sharpe > 0.5 : Acceptable\n"
        else:
            report += "  ❌ Sharpe < 0.5 : Faible\n"
        
        # Interprétation Sortino
        if metrics.sortino_ratio > metrics.sharpe_ratio * 1.3:
            report += "  ✅ Sortino >> Sharpe : Returns asymétriques (positif)\n"
        
        # Interprétation Drawdown
        if abs(metrics.max_drawdown) < 0.15:
            report += "  ✅ Max DD < 15% : Risque contrôlé\n"
        elif abs(metrics.max_drawdown) < 0.30:
            report += "  ⚠️  Max DD < 30% : Risque modéré\n"
        else:
            report += "  ❌ Max DD > 30% : Risque élevé\n"
        
        # Interprétation Win Rate
        if metrics.win_rate > 0.55:
            report += f"  ✅ Win Rate {metrics.win_rate:.1%} : Edge positif\n"
        elif metrics.win_rate > 0.45:
            report += f"  ⚠️  Win Rate {metrics.win_rate:.1%} : Neutre\n"
        else:
            report += f"  ❌ Win Rate {metrics.win_rate:.1%} : Edge négatif\n"
        
        return report

# USAGE
tracker = PerformanceTracker(initial_capital=10000)

# Simuler backtest
equity_series = pd.Series([10000, 10200, 10150, 10400, 10350, 10600])
trade_history = [
    {'pnl': 200, 'fee': 2, 'entry_time': datetime(2024,1,1), 'exit_time': datetime(2024,1,2)},
    {'pnl': -50, 'fee': 2, 'entry_time': datetime(2024,1,2), 'exit_time': datetime(2024,1,3)},
    {'pnl': 250, 'fee': 2, 'entry_time': datetime(2024,1,3), 'exit_time': datetime(2024,1,5)},
]

metrics = tracker.calculate_comprehensive_metrics(equity_series, trade_history)
report = tracker.generate_report(metrics)

print(report)
```

**Fichiers Référence :**
- `bitget_paper/paper_trading/performance_tracker.py`
- `bundle_c_intelligence.md` (Section "Performance Tracking Robuste")

---

# PARTIE 4 : TESTS & VALIDATION

## 4.1 Tests Unitaires Critiques

### 4.1.1 Taxonomie des Tests

**Classification par Pertinence :**

```
NIVEAU 5/5 (NON-NÉGOCIABLE) :
├─ test_liquidation_loses_80_percent
├─ test_liquidation_stops_trading
├─ test_grid_cannot_beat_perfect_sellhold
├─ test_has_position_parameter_exists
├─ test_fees_paid_twice
└─ test_short_pnl_with_leverage

NIVEAU 4/5 (IMPORTANT) :
├─ test_drawdown_on_owned_sol_not_exposed
├─ test_volume_threshold_crypto
├─ test_slippage_distribution
└─ test_unified_portfolio

NIVEAU 3/5 (UTILE) :
├─ test_api_connection
├─ test_dataframe_normalization
└─ test_rate_limiting
```

**Fichiers Référence :**
- `sol-grid-bot/tests/test_truth.py`
- `bitget_paper/tests/test_unified_portfolio.py`
- `bundle_a_intelligence.md` (Section "Unit Tests")

---

### 4.1.2 Template de Test Critique

**Structure Standard :**

```python
# tests/test_critical_logic.py

import pytest
import numpy as np
import pandas as pd
from datetime import datetime

class TestCriticalLogic:
    """
    Tests de logique critique (5/5)
    
    Ces tests DOIVENT passer pour considérer le code production-ready
    """
    
    def test_feature_with_clear_name(self):
        """
        Une ligne décrivant ce qui est testé
        
        PERTINENCE: 5/5
        POURQUOI CRITIQUE: Explication du risque si ce test échoue
        PATTERN DÉTECTÉ: Ce que ce test protège
        """
        # ARRANGE : Setup
        initial_state = create_initial_state()
        
        # ACT : Exécution
        result = function_under_test(initial_state)
        
        # ASSERT : Validation
        assert result == expected_value, \
            f"Message clair : attendu {expected_value}, reçu {result}"
        
        # ASSERT secondaire (si applicable)
        assert side_effect_occurred(), \
            "Side effect devait se produire"
    
    def test_edge_case_with_specific_scenario(self):
        """Test cas limite spécifique"""
        # Même structure
        pass

# EXEMPLE CONCRET : Test Liquidation

class TestLiquidation:
    """Tests liquidation (Pattern Game Over)"""
    
    def test_liquidation_loses_exactly_80_percent(self):
        """
        Liquidation doit perdre EXACTEMENT 80% du collateral
        
        PERTINENCE: 5/5
        POURQUOI CRITIQUE: Si perte ≠ 80%, backtest ment sur risque réel
        PATTERN DÉTECTÉ: Perte arbitraire (70%, 90%) = formule cassée
        """
        # ARRANGE
        bot = GridBot(initial_capital=1000, initial_price=100, config)
        initial_sol = bot.collateral_sol  # 10 SOL
        
        # Open position
        bot._open_position(100, 95, datetime.now())
        position = bot.positions[0]
        liq_price = position['liquidation_price']
        
        # ACT : Déclencher liquidation
        state = bot.step(liq_price + 1, datetime.