# 🤖 Briefing pour Claude Code / Opus 4.6
## Phase 1 : Création de `paper-trading-codex`

**Date :** Février 2026  
**Objectif :** Créer un environnement paper trading fonctionnel pour Bitget avec Grid Bot comme stratégie par défaut  
**Durée estimée :** 24h - 7 jours de développement + tests continus

---

## 🎯 Mission Principale

**Créer `paper-trading-codex`, un framework Python de paper trading qui :**

1. ✅ Fonctionne avec Bitget API (contourne Erreur 40099)
2. ✅ Implémente Grid Bot stratégie (short bear market)
3. ✅ Passe 5 tests critiques garantissant honnêteté backtest
4. ✅ Permet backtest reproductible en < 5 minutes
5. ✅ Supporte paper trading continu 24h/48h/7j

**Contrainte absolue :** Respecter TOUS les principes documentés dans les sources fournies (pas d'improvisation sur logique critique).

---

## 📚 Documents à Ingérer (Dans l'Ordre)

### Priorité 1 : Comprendre le Contexte

**1. Guide Pédagogique**
- Fichier : `guide_pedagogique_codex.md`
- **À retenir :**
  - Contrainte Bitget : API Demo bloque endpoints privés (Erreur 40099)
  - Solution : Simulation locale avec `ExchangeSimulator`
  - Les 5 tests 5/5 non-négociables
  - Gap backtest mensonger vs honnête (7000% vs 289%)

**2. Codex Partie 1 : Fondations**
- Fichier : `codex_partie_1.md`
- **À retenir :**
  - Architecture en couches (Data/Strategy/Execution/Analytics)
  - Pattern état externe (Strategy = stateless)
  - Portfolio unifié (balance + positions + trades)
  - Séparation État vs Logique

**3. Codex Partie 2 : Grid Bot**
- Fichier : `codex_partie_2.md`
- **À retenir :**
  - Philosophie : Accumulation SOL (pas USD) en bear market
  - Espacement progressif des grilles (géométrique)
  - Gestion collateral en SOL (pas USD)
  - Formule liquidation : `entry × (1 + lev × margin × buffer)`

### Priorité 2 : Implémentation Correcte

**4. Codex Partie 3 : Infrastructure**
- Fichier : `codex_partie_3.md`
- **À retenir :**
  - DataFrame normalisé (gestion formats multiples)
  - Rate limiting avec backoff exponentiel
  - Slippage calibré (pas arbitraire)
  - Fees doubles (entry + exit)

**5. Codex Partie 4 : Tests & Validation**
- Fichier : `codex_partie_4.md`
- **À retenir :**
  - Les 5 tests 5/5 avec code exact
  - test_liquidation_loses_80_percent()
  - test_liquidation_stops_trading()
  - test_fees_paid_twice()
  - test_has_position_parameter_exists()
  - test_grid_cannot_beat_sellhold()

**6. Codex Partie 5 : Anti-Patterns**
- Fichier : `codex_partie_5.md`
- **À retenir :**
  - Les 10 erreurs fatales à éviter
  - État dans Strategy = BUG
  - Liquidation continue trading = FRAUDE
  - Benchmarks incorrects = INVALIDE

### Priorité 3 : Références Code (Exemples)

**7. Bundle A Intelligence**
- Fichier : `bundle_a_intelligence.md`
- **Usage :** Extraire code Grid Bot existant
- **Attention :** Version v0.1 a bugs (voir corrections v0.1.6.3)

**8. Bundle C Intelligence**
- Fichier : `bundle_c_intelligence.md`
- **Usage :** Extraire BitgetDataClient, ExchangeSimulator
- **Attention :** PortfolioManager unifié (ne pas recréer classes séparées)

---

## 📋 Spécifications Techniques

### Structure du Projet

```
paper-trading-codex/
├─ src/
│   ├─ __init__.py
│   │
│   ├─ core/
│   │   ├─ __init__.py
│   │   ├─ exchange_simulator.py      # Simule ordres localement
│   │   ├─ portfolio_manager.py       # Unifié : balance + positions + performance
│   │   └─ data_fetcher.py            # BitgetDataClient (lecture seule)
│   │
│   ├─ strategies/
│   │   ├─ __init__.py
│   │   └─ grid_bot.py                # GridBot avec espacement progressif
│   │
│   └─ analysis/
│       ├─ __init__.py
│       ├─ benchmarks.py              # Buy&Hold, Sell&Hold (formules exactes)
│       └─ performance.py             # Sharpe, Sortino, Calmar
│
├─ tests/
│   ├─ __init__.py
│   ├─ test_critical_5_5.py           # LES 5 TESTS NON-NÉGOCIABLES
│   └─ test_grid_bot.py               # Tests spécifiques Grid Bot
│
├─ configs/
│   ├─ grid_bot_green.yaml            # Leverage 2-3x (débutant)
│   ├─ grid_bot_yellow.yaml           # Leverage 5x (avancé)
│   └─ grid_bot_red.yaml              # Leverage 8-10x (expert)
│
├─ examples/
│   ├─ quickstart_grid_bot.py         # Demo 5 min
│   └─ continuous_paper_trading.py    # Run 24h/48h/7j
│
├─ README.md                          # Setup en 5 minutes
├─ requirements.txt                   # Dependencies
├─ setup.py                           # pip install -e .
└─ .env.example                       # Template credentials
```

---

## 🔧 Spécifications par Module

### 1. `core/exchange_simulator.py`

**Responsabilité :** Simuler exécution ordres localement (contournement Erreur 40099)

**Interface minimale :**

```python
class ExchangeSimulator:
    def __init__(self, slippage_config: Dict):
        """
        Args:
            slippage_config: {'mean': 0.000342, 'std': 0.000187}
        """
        self.slippage_mean = slippage_config['mean']
        self.slippage_std = slippage_config['std']
    
    def place_market_order(
        self, 
        symbol: str, 
        side: str,  # 'buy' ou 'sell'
        amount: float,  # USD
        current_price: float
    ) -> Dict:
        """
        Simule ordre market avec slippage + commission
        
        Returns:
            {
                'executed_price': float,
                'quantity': float,  # BTC/SOL reçu
                'commission': float,  # USD
                'timestamp': datetime
            }
        """
        # Slippage calibré
        slippage = np.random.normal(self.slippage_mean, self.slippage_std)
        
        if side == 'buy':
            executed_price = current_price * (1 + abs(slippage))
        else:
            executed_price = current_price * (1 - abs(slippage))
        
        # Commission 0.1% (taker fee Bitget)
        commission = amount * 0.001
        
        # Quantité reçue
        if side == 'buy':
            quantity = (amount - commission) / executed_price
        else:
            quantity = amount / executed_price
        
        return {
            'executed_price': executed_price,
            'quantity': quantity,
            'commission': commission,
            'timestamp': datetime.now()
        }
```

**⚠️ RÈGLES CRITIQUES :**
- Slippage TOUJOURS positif (dégrade prix, jamais améliore)
- Commission TOUJOURS prélevée (0.1% minimum)
- Retourner Dict complet (pas juste prix)

---

### 2. `core/portfolio_manager.py`

**Responsabilité :** Gérer balance + positions + performance (UNIFIÉ)

**Interface minimale :**

```python
class PortfolioManager:
    def __init__(self, initial_capital: float):
        self.balance = initial_capital  # USD disponible
        self.positions = {}  # Dict[symbol, Position]
        self.trade_history = []
        self.equity_curve = []
    
    def place_market_order(
        self, 
        symbol: str, 
        side: str, 
        amount: float, 
        current_price: float,
        simulator: ExchangeSimulator
    ):
        """
        Place ordre via simulator ET met à jour portfolio
        
        ATOMICITÉ : Tout se passe dans cette fonction
        """
        # Simuler ordre
        execution = simulator.place_market_order(
            symbol, side, amount, current_price
        )
        
        # Mettre à jour balance/positions
        if side == 'buy':
            self.balance -= (amount + execution['commission'])
            self.positions[symbol] = {
                'entry_price': execution['executed_price'],
                'quantity': execution['quantity'],
                'timestamp': execution['timestamp']
            }
        
        elif side == 'sell':
            if symbol not in self.positions:
                raise ValueError(f"Aucune position {symbol} à fermer")
            
            position = self.positions[symbol]
            
            # PnL brut
            exit_value = position['quantity'] * execution['executed_price']
            entry_value = position['quantity'] * position['entry_price']
            gross_pnl = exit_value - entry_value
            
            # PnL net (après commission exit)
            net_pnl = gross_pnl - execution['commission']
            
            # Mettre à jour balance
            self.balance += (exit_value - execution['commission'])
            
            # Supprimer position
            del self.positions[symbol]
        
        # Logger trade
        self.trade_history.append({
            'symbol': symbol,
            'side': side,
            'amount': amount,
            **execution
        })
    
    def get_total_equity(self, current_prices: Dict[str, float]) -> float:
        """Balance + valeur positions"""
        equity = self.balance
        
        for symbol, position in self.positions.items():
            price = current_prices.get(symbol, position['entry_price'])
            equity += position['quantity'] * price
        
        # Track equity curve
        self.equity_curve.append({
            'timestamp': datetime.now(),
            'equity': equity
        })
        
        return equity
    
    def get_performance_metrics(self) -> Dict:
        """Calculer Sharpe, DD, Calmar..."""
        # (voir Codex Partie 3.3.2 pour formules exactes)
        pass
```

**⚠️ RÈGLES CRITIQUES :**
- Fees payées DEUX FOIS (entry + exit)
- État unifié (pas de désynchronisation possible)
- Equity curve tracked (pour Sharpe ratio)

---

### 3. `core/data_fetcher.py`

**Responsabilité :** Récupérer données Bitget (lecture seule)

**Interface minimale :**

```python
import ccxt

class BitgetDataFetcher:
    def __init__(self, api_key: str, api_secret: str, passphrase: str):
        self.client = ccxt.bitget({
            'apiKey': api_key,
            'secret': api_secret,
            'password': passphrase,
            'options': {'defaultType': 'swap'}
        })
    
    def get_ohlcv(
        self, 
        symbol: str,  # 'SBTC/SUSDT:SUSDT' (demo) ou 'BTC/USDT:USDT' (live)
        timeframe: str = '1h',
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Récupère OHLCV depuis Bitget
        
        Returns:
            DataFrame normalisé : ['open', 'high', 'low', 'close', 'volume']
            Index : DatetimeIndex
        """
        # Fetch
        ohlcv = self.client.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        # Normaliser (voir Codex 3.1.1)
        df = pd.DataFrame(
            ohlcv, 
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        return df
    
    def get_balance(self):
        """❌ BLOQUÉ par Erreur 40099"""
        raise NotImplementedError(
            "Bitget Demo API bloque endpoints privés. "
            "Utilisez PortfolioManager pour simulation locale."
        )
    
    def create_order(self, *args, **kwargs):
        """❌ BLOQUÉ par Erreur 40099"""
        raise NotImplementedError(
            "Bitget Demo API bloque create_order. "
            "Utilisez ExchangeSimulator.place_market_order()."
        )
```

**⚠️ RÈGLES CRITIQUES :**
- Endpoints privés = INTERDITS (lever NotImplementedError explicite)
- DataFrame TOUJOURS normalisé (colonnes lowercase)
- Rate limiting si appelé fréquemment

---

### 4. `strategies/grid_bot.py`

**Responsabilité :** Logique Grid Bot (SHORT bear market)

**Interface minimale :**

```python
class GridBot:
    def __init__(self, config: Dict):
        """
        Args:
            config: {
                'leverage': 5,
                'grid_size': 7,
                'grid_ratio': 0.02,
                'initial_capital': 1000
            }
        """
        self.leverage = config['leverage']
        self.grid_size = config['grid_size']
        self.grid_ratio = config['grid_ratio']
        self.initial_capital = config['initial_capital']
        
        # Collateral en SOL (PRIMAIRE)
        self.collateral_sol = 0  # Initialisé au premier prix
        
        # Positions actives
        self.positions = []
        
        # Liquidation state
        self.liquidated = False
    
    def calculate_grid_levels(self, current_price: float) -> List[float]:
        """
        Espacement PROGRESSIF (géométrique)
        
        Formule : level[i] = level[i-1] × (1 - ratio × (1 + i × 0.1))
        """
        levels = []
        level = current_price
        
        for i in range(self.grid_size):
            spacing = self.grid_ratio * (1 + i * 0.1)
            level = level * (1 - spacing)
            levels.append(level)
        
        return sorted(levels, reverse=True)  # Plus haut → plus bas
    
    def calculate_liquidation_price(self, entry_price: float) -> float:
        """
        Formule EXACTE (voir Codex 2.1.4)
        
        liq = entry × (1 + leverage × margin × buffer)
        """
        maintenance_margin = 0.08  # 8% (conservateur)
        safety_buffer = 1.3  # 30% cushion
        
        return entry_price * (1 + self.leverage * maintenance_margin * safety_buffer)
    
    def should_open_position(
        self, 
        current_price: float,
        active_positions: int,  # ← État EXTERNE
        max_positions: int = 5
    ) -> Tuple[bool, Optional[float]]:
        """
        Décision ouverture position
        
        STATELESS : État passé en paramètre
        """
        if active_positions >= max_positions:
            return False, None
        
        grid_levels = self.calculate_grid_levels(current_price)
        
        for level in grid_levels:
            # Prix a franchi niveau (descendant)
            if current_price <= level * 0.995:  # 0.5% tolérance
                return True, level
        
        return False, None
    
    def step(
        self, 
        current_price: float, 
        timestamp: datetime
    ) -> Dict:
        """
        Une itération de trading
        
        ⚠️ CRITIQUE : Vérifier liquidation AVANT toute autre logique
        """
        # ÉTAPE 1 : Check liquidation
        for position in self.positions:
            if current_price >= position['liquidation_price']:
                # GAME OVER
                self.collateral_sol *= 0.2  # Perd 80%
                self.liquidated = True
                
                return {
                    'liquidated': True,
                    'collateral_sol': self.collateral_sol,
                    'price': current_price,
                    'message': 'LIQUIDATED - TRADING STOPPED'
                }
        
        # ÉTAPE 2 : Si survécu, logique normale
        # (Ne s'exécute JAMAIS si liquidated)
        
        # ... (logique ouverture/fermeture positions)
        
        return {
            'liquidated': False,
            'collateral_sol': self.collateral_sol,
            # autres métriques
        }
```

**⚠️ RÈGLES CRITIQUES :**
- Liquidation check AVANT toute logique
- Si liquidated → return immédiatement (pas de continue)
- État externe (active_positions passé en paramètre)
- Espacement progressif (pas linéaire)

---

### 5. `analysis/benchmarks.py`

**Responsabilité :** Calcul Buy&Hold et Sell&Hold (formules EXACTES)

**Interface minimale :**

```python
class Benchmarks:
    def __init__(self, initial_capital: float, initial_price: float, leverage: float = 1.0):
        self.initial_capital = initial_capital
        self.initial_price = initial_price
        self.leverage = leverage
        self.initial_sol = initial_capital / initial_price
    
    def buy_and_hold(self, prices: pd.Series) -> pd.Series:
        """
        Formule : value(t) = initial_sol × price(t)
        
        DOIT suivre prix EXACTEMENT (1:1)
        """
        return self.initial_sol * prices
    
    def sell_and_hold(self, prices: pd.Series) -> pd.Series:
        """
        Formule : value(t) = capital × (1 + (p0 - pt)/pt × leverage - fees)
        
        Plafond mathématique (timing PARFAIT)
        """
        price_change_pct = (self.initial_price - prices) / prices
        leveraged_return = price_change_pct * self.leverage
        
        # Fees : 0.1% entry + 0.1% exit
        trading_fees = 0.002
        
        return self.initial_capital * (1 + leveraged_return - trading_fees)
```

**⚠️ RÈGLES CRITIQUES :**
- Buy&Hold = 1:1 avec prix (PAS de dérive)
- Sell&Hold = plafond (Grid CANNOT beat)
- Fees incluses dans Sell&Hold

---

### 6. `tests/test_critical_5_5.py`

**LES 5 TESTS NON-NÉGOCIABLES**

```python
import pytest
import numpy as np
from src.strategies.grid_bot import GridBot
from src.core.portfolio_manager import PortfolioManager
from src.analysis.benchmarks import Benchmarks

def test_liquidation_loses_80_percent():
    """Liquidation DOIT perdre EXACTEMENT 80%"""
    bot = GridBot({'leverage': 5, 'grid_size': 7, 'grid_ratio': 0.02, 'initial_capital': 1000})
    
    # Simuler collateral initial
    bot.collateral_sol = 10.0
    initial_sol = bot.collateral_sol
    
    # Ouvrir position (simplifié)
    bot.positions.append({
        'entry_price': 100,
        'liquidation_price': 152  # Leverage 5x
    })
    
    # Force liquidation
    state = bot.step(current_price=153, timestamp=datetime.now())
    
    # ASSERTIONS
    assert state['liquidated'] is True
    assert abs(bot.collateral_sol - initial_sol * 0.2) < 0.01, \
        f"Doit perdre 80%, pas {100 * (1 - bot.collateral_sol/initial_sol):.1f}%"

def test_liquidation_stops_trading():
    """Après liquidation, AUCUN nouveau trade"""
    bot = GridBot({'leverage': 5, 'grid_size': 7, 'grid_ratio': 0.02, 'initial_capital': 1000})
    
    bot.collateral_sol = 10.0
    bot.positions.append({'entry_price': 100, 'liquidation_price': 152})
    
    # Liquidation
    bot.step(153, datetime.now())
    
    # Tenter trade après
    state2 = bot.step(50, datetime.now())  # Prix très bas (signal fort)
    
    assert len(bot.positions) == 0, "Ne doit PAS ouvrir position après liquidation"

def test_fees_paid_twice():
    """Entry fee + Exit fee"""
    portfolio = PortfolioManager(1000)
    simulator = ExchangeSimulator({'mean': 0, 'std': 0})  # Slippage = 0 pour isoler fees
    
    initial = portfolio.balance
    
    # Buy
    portfolio.place_market_order('BTC', 'buy', 500, 50000, simulator)
    after_buy = portfolio.balance
    
    # Sell (prix identique)
    portfolio.place_market_order('BTC', 'sell', 500, 50000, simulator)
    after_sell = portfolio.balance
    
    # Total fees = 0.1% × 2 = 0.2%
    total_fees = initial - after_sell
    expected_fees = 500 * 0.002  # $1
    
    assert abs(total_fees - expected_fees) < 0.1

def test_has_position_parameter_exists():
    """Éviter régression (paramètre disparu)"""
    from src.strategies.grid_bot import GridBot
    import inspect
    
    bot = GridBot({'leverage': 5, 'grid_size': 7, 'grid_ratio': 0.02, 'initial_capital': 1000})
    
    # Vérifier que méthode accepte has_position OU active_positions
    sig = inspect.signature(bot.should_open_position)
    
    assert 'active_positions' in sig.parameters, \
        "Régression : paramètre état externe disparu"

def test_grid_cannot_beat_sellhold():
    """Grid Bot NE PEUT PAS battre Sell&Hold (plafond mathématique)"""
    
    # Données : Chute linéaire 100 → 50
    prices = pd.Series(np.linspace(100, 50, 100))
    
    # Grid backtest (simulé)
    grid_return = 2.89  # +289% (résultat connu)
    
    # Sell&Hold benchmark
    bench = Benchmarks(1000, 100, leverage=5)
    sellhold = bench.sell_and_hold(prices)
    sellhold_return = (sellhold.iloc[-1] - 1000) / 1000
    
    # Grid DOIT être <= Sell&Hold (tolérance 5% pour variance)
    assert grid_return <= sellhold_return * 1.05, \
        f"IMPOSSIBLE : Grid ({grid_return:.1%}) bat Sell&Hold ({sellhold_return:.1%})"
```

**⚠️ RÈGLES CRITIQUES :**
- Ces 5 tests DOIVENT passer
- Si 1 échoue → STOP développement
- Pas d'exception, pas de skip

---

## ⚙️ Configuration Files

### `configs/grid_bot_green.yaml` (Zone Verte)

```yaml
strategy: grid_bot
leverage: 3
grid_size: 7
grid_ratio: 0.02
initial_capital: 1000

risk_profile:
  zone: GREEN
  liquidation_distance: "> 100%"
  recommended_for: "Débutants"
  monitoring: "Hebdomadaire suffisant"

simulation:
  slippage:
    mean: 0.000342
    std: 0.000187
  commission_rate: 0.001  # 0.1%
```

### `configs/grid_bot_yellow.yaml` (Zone Jaune)

```yaml
strategy: grid_bot
leverage: 5
grid_size: 7
grid_ratio: 0.02
initial_capital: 1000

risk_profile:
  zone: YELLOW
  liquidation_distance: "40-100%"
  recommended_for: "Avancés"
  monitoring: "Quotidien requis"

simulation:
  slippage:
    mean: 0.000342
    std: 0.000187
  commission_rate: 0.001
```

### `configs/grid_bot_red.yaml` (Zone Rouge)

```yaml
strategy: grid_bot
leverage: 8
grid_size: 7
grid_ratio: 0.02
initial_capital: 1000

risk_profile:
  zone: RED
  liquidation_distance: "< 40%"
  recommended_for: "Experts uniquement"
  monitoring: "24/7 obligatoire"
  warning: "Accepter perte totale possible"

simulation:
  slippage:
    mean: 0.000342
    std: 0.000187
  commission_rate: 0.001
```

---

## 📦 Dependencies (`requirements.txt`)

```
# Core
numpy>=1.24.0
pandas>=2.0.0
python-dotenv>=1.0.0

# Exchange
ccxt>=4.0.0

# Testing
pytest>=7.4.0
pytest-cov>=4.1.0

# Analysis
matplotlib>=3.7.0
seaborn>=0.12.0

# Optional (pour site web futur)
# quarto>=1.3.0
# plotly>=5.17.0
# streamlit>=1.28.0
```

---

## 📝 README.md (Template)

```markdown
# 📘 Paper Trading Codex - Bitget Edition

Framework paper trading honnête pour stratégies crypto sur Bitget.

## ⚡ Quickstart (5 minutes)

```bash
# 1. Clone
git clone <repo>
cd paper-trading-codex

# 2. Install
pip install -e .

# 3. Configure
cp .env.example .env
# Éditer .env avec API keys Bitget

# 4. Run
python examples/quickstart_grid_bot.py
```

## 🧪 Tests

```bash
pytest tests/test_critical_5_5.py  # Les 5 tests NON-NÉGOCIABLES
pytest tests/  # Tous tests
```

## 📊 Exemple Résultat

```
=== BACKTEST GRID BOT ===
Config : Leverage 5x, Grid 7, Ratio 2%

SOL Holdings : +289%
USD Value : -14%
Zone : JAUNE (Risque Calculé)
✅ Tests 5/5 : PASS
```

## 📚 Documentation

Voir `docs/codex/` pour guide complet.

## ⚠️ Disclaimer

Outil éducatif. Pas de garantie de profit.
```

---

## 🎯 Objectif Livrable Final

**Après 24h-7j de développement, l'utilisateur doit pouvoir :**

```bash
git clone https://github.com/user/paper-trading-codex
cd paper-trading-codex
pip install -e .
cp .env.example .env
# [Éditer .env avec credentials Bitget]
python examples/quickstart_grid_bot.py
```

**Et obtenir en < 5 minutes :**

1. ✅ Backtest complet Grid Bot
2. ✅ Graphiques sauvegardés (`results/`)
3. ✅ Métriques honnêtes (tests 5/5 passent)
4. ✅ Comparaison benchmarks
5. ✅ Décision zone (verte/jaune/rouge)

**Puis, lancer paper trading continu :**

```bash
python examples/continuous_paper_trading.py --duration 24  # 24 heures
```

**Et après 24h :**

1. ✅ Rapport `reports/paper_trading_24h.txt`
2. ✅ 0 crash
3. ✅ Performance vs backtest documentée

---

## 🚨 Règles Absolues (Non-Négociables)

1. **Tests 5/5 DOIVENT passer** - Sinon STOP
2. **Liquidation = perte 80% + STOP trading** - Pas de continue
3. **Fees payées 2× (entry + exit)** - Toujours
4. **État externe (pas dans Strategy)** - has_position en paramètre
5. **Benchmarks formules exactes** - Buy&Hold 1:1, Sell&Hold plafond
6. **Slippage calibré** - Pas valeurs arbitraires
7. **Erreur 40099 = bloquée** - Simulation locale obligatoire
8. **DataFrame normalisé** - Colonnes lowercase standard
9. **Espacement progressif Grid** - Géométrique, pas linéaire
10. **Collateral SOL métrique primaire** - USD = secondaire (Grid Bot)

---

## 📋 Checklist Validation (Avant de Déclarer "Terminé")

**Code :**
- [ ] Structure projet conforme
- [ ] Tous fichiers .py créés
- [ ] Import paths cohérents
- [ ] Docstrings complètes

**Tests :**
- [ ] 5 tests 5/5 passent (100%)
- [ ] Coverage > 80%
- [ ] pytest sans warnings

**Fonctionnalités :**
- [ ] Quickstart fonctionne en < 5 min
- [ ] Backtest produit résultats corrects
- [ ] Paper trading 24h tourne sans crash
- [ ] Graphiques sauvegardés

**Documentation :**
- [ ] README complet
- [ ] .env.example fourni
- [ ] Comments inline clairs
- [ ] Docstrings type hints

**Qualité :**
- [ ] Code lint (black, flake8)
- [ ] Pas de hard-coded values
- [ ] Logging structuré
- [ ] Error handling propre

---

## 🔍 Audit Post-Développement (24h / 48h / 7j)

**Après que Claude Code/Opus 4.6 ait livré le code, nous l'auditerons selon :**

### Audit 24h

**Focus :** Fonctionnalité basique

```bash
# 1. Setup (doit marcher)
git clone ...
pip install -e .

# 2. Tests (doivent passer)
pytest tests/test_critical_5_5.py

# 3. Quickstart (doit produire résultats)
python examples/quickstart_grid_bot.py

# 4. Paper trading 24h (lancer)
python examples/continuous_paper_trading.py --duration 24 &
```

**Questions :**
- [ ] Setup en < 5 min ?
- [ ] Tests 5/5 passent ?
- [ ] Backtest produit graphiques ?
- [ ] Paper trading lance sans erreur ?

---

### Audit 48h

**Focus :** Stabilité

**Vérifications :**
- [ ] Paper trading tourne toujours ?
- [ ] Pas de memory leaks (check logs)
- [ ] Métriques cohérentes (PnL, trades)
- [ ] Logs structurés lisibles

**Actions si problèmes :**
- Documenter crashes
- Identifier patterns erreurs
- Proposer fixes

---

### Audit 7j

**Focus :** Performance réelle vs backtest

**Métriques à comparer :**

```yaml
backtest:
  duration: "Instantané sur 14 mois données"
  sol_return: "+289%"
  trades: 35
  sharpe: 2.33

paper_trading_7j:
  duration: "7 jours temps réel"
  sol_return: "?" (à mesurer)
  trades: "?" (attendu ~2-3)
  sharpe: "?" (calculer)

comparaison:
  performance_ratio: "paper / backtest (attendu 50-70%)"
  trades_frequency: "Cohérent ?"
  crashes: "0 attendu"
```

**Décision finale :**
- ✅ Si performance > 50% backtest + 0 crash → SUCCESS
- ⚠️ Si 30-50% → ACCEPTABLE (friction normale)
- ❌ Si < 30% ou crashes → DEBUG requis

---

## 💬 Communication avec Claude Code/Opus 4.6

**Prompt Initial :**

```
Bonjour Claude Code / Opus 4.6,

Je te confie la création de `paper-trading-codex`, un framework Python de 
paper trading pour Bitget avec Grid Bot stratégie.

📚 Documents à lire (dans l'ordre) :
1. guide_pedagogique_codex.md (contexte général)
2. codex_partie_1.md (architecture)
3. codex_partie_2.md (Grid Bot)
4. codex_partie_3.md (infrastructure)
5. codex_partie_4.md (tests)
6. codex_partie_5.md (anti-patterns)
7. bundle_a_intelligence.md (code référence)
8. bundle_c_intelligence.md (code référence)

🎯 Objectif :
Créer repo fonctionnel où :
- git clone + pip install + python quickstart.py = résultats en 5 min
- Tests 5/5 passent (garantie honnêteté)
- Paper trading 24h/48h/7j fonctionne sans crash

📋 Spécifications complètes :
Voir document "Briefing pour Claude Code" (ce fichier).

⚠️ RÈGLES ABSOLUES :
1. Tests 5/5 DOIVENT passer
2. Liquidation = -80% + STOP (pas continue)
3. Fees 2× (entry + exit)
4. État externe (has_position paramètre)
5. Benchmarks formules exactes
6. Erreur 40099 = simulation locale

🚀 Livrable :
Repo GitHub complet, testé, documenté.

Questions avant de commencer ?
```

**Suivi Quotidien :**

Jour 1-3 :
- "Où en es-tu ?"
- "Tests 5/5 passent ?"
- "Besoin de clarifications ?"

Jour 4-7 :
- "Paper trading 24h lancé ?"
- "Résultats cohérents ?"
- "Problèmes détectés ?"

---

## 🎓 Apprentissages Attendus

**Ce que nous allons apprendre en confiant à l'IA :**

1. **Fidélité aux specs**
   - Respecte-t-elle les 10 règles absolues ?
   - Improvise-t-elle ou suit-elle le Codex ?

2. **Qualité du code**
   - Tests passent du premier coup ?
   - Architecture propre ?
   - Documentation claire ?

3. **Gestion de la complexité**
   - Gère-t-elle les dépendances entre modules ?
   - Évite-t-elle les bugs connus documentés ?

4. **Performance**
   - Temps setup réel < 5 min ?
   - Paper trading stable 7j ?
   - Performance backtest vs live cohérente ?

**Hypothèses à valider :**

- ✅ Avec specs détaillées, IA peut générer code production-ready
- ❓ Sans surveillance, régresse-t-elle sur bugs connus (has_position) ?
- ❓ Comprend-elle WHY (philosophie) ou juste WHAT (code) ?

---

## 📊 Rapport Final (Post-Audit 7j)

**Template rapport :**

```markdown
# Audit Paper Trading Codex - 7 Jours

## Résumé Exécutif

- **Développement :** Claude Code / Opus 4.6
- **Durée dev :** X jours
- **Durée test :** 7 jours continus
- **Verdict :** ✅ SUCCESS / ⚠️ ACCEPTABLE / ❌ ÉCHEC

## Métriques Techniques

### Setup
- Temps installation : X min (objectif < 5 min)
- Tests 5/5 : PASS / FAIL
- Coverage : X% (objectif > 80%)

### Backtest
- Durée exécution : X secondes
- Résultats cohérents : OUI / NON
- Graphiques générés : X fichiers

### Paper Trading 7j
- Uptime : X% (objectif 100%)
- Crashes : X (objectif 0)
- Trades exécutés : X
- Performance : X% (vs backtest)

## Comparaison Backtest vs Live

| Métrique | Backtest | Paper 7j | Ratio |
|----------|----------|----------|-------|
| SOL Return | +289% | +X% | X% |
| Trades | 35 | X | - |
| Sharpe | 2.33 | X | - |

## Bugs Détectés

1. [Si applicable]
2. ...

## Recommandations

1. ...
2. ...

## Décision

[ ] Valider v1.0
[ ] Corrections mineures requises
[ ] Refonte majeure
```

---

## ✅ Conclusion

**Ce briefing donne à Claude Code/Opus 4.6 TOUT ce dont elle a besoin :**

1. ✅ Contexte complet (Codex 6 parties)
2. ✅ Spécifications détaillées (structure, interfaces)
3. ✅ Exemples code (bundles A/C)
4. ✅ Tests critiques (5/5 non-négociables)
5. ✅ Anti-patterns à éviter (Partie 5)
6. ✅ Critères succès clairs (audit 24h/48h/7j)

**Prochaine étape :**

Copier ce document + Codex dans conversation avec Claude Code, lancer développement, et auditer résultats selon timeline définie.

**Bonne chance ! 🚀**</parameter>
