# Codex du Paper Trading sur Bitget - Partie 2/6

## 2.1.4 Liquidation : Le Game Over Absolu

**Principe Non-Négociable :**

```
Liquidation = Perte de 80% du collateral + ARRÊT IMMÉDIAT
≠ "Continue trading avec 20% restant"
```

**Source :** `bundle_a_intelligence.md` (Corrections Timeline)

**L'Erreur de l'IA (v0.1) :**

```python
# ❌ VERSION BUGUÉE (IA initiale)
def step(self, current_price, timestamp):
    for position in self.positions:
        if current_price >= position['liquidation_price']:
            # Liquidation
            self.collateral_sol *= 0.2  # Perte 80%
            self.positions.remove(position)
            
            # ❌ CONTINUE TRADING après liquidation !
            # ... reste du code qui ouvre de nouvelles positions
```

**Résultat Frauduleux :**

```
Backtest v0.1 :
├─ SOL : 4.94 → 7020.17 SOL (+142,000%) 🚀
├─ Trades : 483
├─ Liquidations : 20
└─ ❌ MENSONGE : Continued trading après 20 liquidations
```

**La Correction Critique :**

```python
# ✅ VERSION CORRIGÉE
def step(self, current_price, timestamp):
    """
    CHECK LIQUIDATION FIRST - avant toute autre logique
    """
    # ÉTAPE 1 : Vérifier liquidations
    for i, position in enumerate(self.positions):
        if current_price >= position['liquidation_price']:
            # GAME OVER
            self.collateral_sol *= 0.2  # Perte 80%
            self.liquidation_count += 1
            
            logging.error(f"💀 LIQUIDATION at ${current_price:.2f}")
            logging.error(f"Position: {position}")
            logging.error(f"Collateral: {self.collateral_sol:.2f} SOL (-80%)")
            
            # RETURN IMMÉDIATEMENT
            return {
                'liquidated': True,
                'collateral_sol': self.collateral_sol,
                'price': current_price,
                'liquidation_count': self.liquidation_count,
                'message': 'LIQUIDATED - TRADING STOPPED'
            }
    
    # ÉTAPE 2 : Si survécu, continuer logique normale
    # (cette partie ne s'exécute JAMAIS si liquidation)
    # ...

# USAGE DANS BACKTEST
for timestamp, row in data.iterrows():
    state = bot.step(row['close'], timestamp)
    
    if state.get('liquidated'):
        print(f"❌ Liquidation à {timestamp}")
        print(f"Final SOL: {state['collateral_sol']:.2f} (-80%)")
        break  # STOP backtest immédiatement
```

**Résultat Honnête :**

```
Backtest v0.1.6.3 (corrigé) :
├─ Leverage 5x : 
│   ├─ SOL : 4.94 → 19.24 SOL (+289%)
│   ├─ Liquidations : 0
│   └─ ✅ Survie : 100% de la période
│
├─ Leverage 8x :
│   ├─ SOL : 4.94 → 0.99 SOL (-80%)
│   ├─ Liquidations : 1 (à 35% de la période)
│   └─ ❌ Échec : Liquidé tôt
```

**Calcul du Prix de Liquidation :**

```python
def _calculate_liquidation_price(self, entry_price: float) -> float:
    """
    Formule : entry × (1 + leverage × margin × safety_buffer)
    
    Paramètres Bitget :
    ├─ maintenance_margin : 0.05 (5%, minimum théorique)
    ├─ safety_buffer : 1.3 (30% de marge supplémentaire)
    └─ leverage : Variable (2x, 5x, 8x, 10x...)
    """
    maintenance_margin = 0.08  # 8% au lieu de 5% (conservateur)
    safety_buffer = 1.3  # 30% de cushion
    
    margin_ratio = self.leverage * maintenance_margin * safety_buffer
    return entry_price * (1 + margin_ratio)

# EXEMPLES
entry_price = 100

# Leverage 5x
liq_5x = 100 * (1 + 5 * 0.08 * 1.3)
liq_5x = 100 * (1 + 0.52)
liq_5x = 152  # Liquidation à +52%

# Leverage 8x
liq_8x = 100 * (1 + 8 * 0.08 * 1.3)
liq_8x = 100 * (1 + 0.832)
liq_8x = 183.2  # Liquidation à +83.2%

# Leverage 10x
liq_10x = 100 * (1 + 10 * 0.08 * 1.3)
liq_10x = 100 * (1 + 1.04)
liq_10x = 204  # Liquidation à +104% (suicide)
```

**Pourquoi 30% de Safety Buffer ?**

```
Sans buffer (théorique) :
├─ Maintenance margin : 5%
├─ Leverage 5x : Liquidation à +25%
└─ ❌ Risque : Bitget peut liquider AVANT 25% (slippage, volatilité)

Avec buffer 30% (réaliste) :
├─ Maintenance margin : 8% (vs 5%)
├─ Safety multiplier : 1.3x
├─ Leverage 5x : Liquidation à +52%
└─ ✅ Protection : Survit à flash crash de 40%
```

**Test Unitaire Critique :**

```python
# tests/test_truth.py

def test_liquidation_loses_80_percent():
    """LIQUIDATION DOIT PERDRE EXACTEMENT 80%"""
    bot = GridBot(1000, 100, config={'leverage': 10})
    initial_sol = bot.collateral_sol  # 10 SOL
    
    # Ouvre position
    bot._open_position(100, 95, datetime.now())
    position = bot.positions[0]
    liq_price = position['liquidation_price']
    
    # Force liquidation
    state = bot.step(liq_price + 1, datetime.now())
    
    # ASSERTIONS CRITIQUES
    assert state['liquidated'] is True, "Doit marquer comme liquidé"
    assert abs(bot.collateral_sol - initial_sol * 0.2) < 0.1, \
        f"Doit perdre 80%, pas {100 * (1 - bot.collateral_sol/initial_sol):.1f}%"
    
    # Vérifier que trading s'arrête
    state2 = bot.step(50, datetime.now())  # Tenter de continuer
    assert len(bot.positions) == 0, "Ne doit pas ouvrir de nouvelles positions"

def test_liquidation_stops_trading():
    """APRÈS LIQUIDATION, AUCUN NOUVEAU TRADE"""
    bot = GridBot(1000, 100, config={'leverage': 10})
    
    # Force liquidation
    bot._open_position(100, 95, datetime.now())
    liq_price = bot.positions[0]['liquidation_price']
    state1 = bot.step(liq_price + 1, datetime.now())
    
    assert state1['liquidated'] is True
    
    # Tenter de trader après
    state2 = bot.step(50, datetime.now())  # Prix très bas (signal BUY)
    
    # DOIT échouer silencieusement ou retourner état liquidé
    assert len(bot.positions) == 0, "Ne doit PAS ouvrir position après liquidation"
    assert bot.collateral_sol == state1['collateral_sol'], \
        "Collateral ne doit PAS changer après liquidation"
```

**Fichiers Référence :**
- `sol-grid-bot/src/core/grid_bot.py` (Ligne 287-312)
- `sol-grid-bot/tests/test_truth.py`
- `bundle_a_intelligence.md` (Section "Anti-Bug Patterns")

---

### 2.1.5 Benchmarks Honnêtes : Le Plafond Mathématique

**Principe Fondamental :**

```
Sur un marché en BAISSE LINÉAIRE :
├─ Sell & Hold = PLAFOND (short au top, close au bottom)
├─ Grid Bot = APPROCHE du plafond (timing imparfait + fees)
└─ Grid CANNOT beat Sell&Hold (mathématiquement impossible)
```

**Source :** `bundle_a_intelligence.md` (Section "Performance Reality")

**Formules des Benchmarks :**

```python
# Fichier : sol-grid-bot/src/analysis/benchmarks.py

class Benchmarks:
    def __init__(self, initial_capital: float, initial_price: float, leverage: float = 1.0):
        self.initial_capital = initial_capital
        self.initial_price = initial_price
        self.leverage = leverage
        
        # Conversion USD → SOL
        self.initial_sol = initial_capital / initial_price
    
    def buy_and_hold(self, prices: pd.Series) -> pd.Series:
        """
        Buy & Hold : Garde SOL initial, valeur suit le prix
        
        Formule : value(t) = initial_sol × price(t)
        """
        return self.initial_sol * prices
    
    def sell_and_hold(self, prices: pd.Series) -> pd.Series:
        """
        Sell & Hold : Short au début, close à la fin
        
        Formule : value(t) = capital × (1 + pnl_pct × leverage) - fees
        
        PnL% = (initial_price - current_price) / current_price
        Leverage amplifie le return
        Fees = 0.1% × 2 (entry + exit)
        """
        price_change_pct = (self.initial_price - prices) / prices
        leveraged_return = price_change_pct * self.leverage
        
        # Fees : 0.1% entry + 0.1% exit
        trading_fees = 0.002  # 0.2% total
        
        return self.initial_capital * (1 + leveraged_return - trading_fees)

# EXEMPLE CONCRET
initial_capital = 1000
initial_price = 100
leverage = 5

bench = Benchmarks(initial_capital, initial_price, leverage)

# Scénario : Prix baisse de 100 → 20 (-80%)
prices = pd.Series([100, 90, 80, 70, 60, 50, 40, 30, 20])

# Buy & Hold
buy_hold = bench.buy_and_hold(prices)
# [1000, 900, 800, 700, 600, 500, 400, 300, 200]
# Final : $200 (-80%)

# Sell & Hold (5x leverage)
sell_hold = bench.sell_and_hold(prices)
# Prix change : (100-20)/20 = 4.0 (400%)
# Leveraged : 4.0 × 5 = 20.0 (2000%)
# Fees : -0.2%
# Final : 1000 × (1 + 20.0 - 0.002) = $20,980
# Return : +1998%
```

**Test de Réalisme :**

```python
# tests/test_truth.py

def test_grid_cannot_beat_perfect_sellhold():
    """
    Grid Bot CANNOT beat Sell&Hold sur chute linéaire
    
    Raison : Sell&Hold = timing PARFAIT (impossible)
    Grid = timing IMPARFAIT + fees multiples
    """
    # Données : Chute linéaire 100 → 50
    dates = pd.date_range('2021-01-01', periods=100, freq='D')
    prices = np.linspace(100, 50, 100)
    data = pd.DataFrame({'close': prices}, index=dates)
    
    # Grid Bot backtest
    config = {'leverage': 2, 'grid_ratio': 0.02, 'grid_size': 5}
    bot = GridBot(1000, 100, config)
    results_df, bot_final = run_backtest(data, bot)
    
    # Sell & Hold benchmark
    bench = Benchmarks(1000, 100, leverage=2)
    sell_hold = bench.sell_and_hold(data['close'])
    
    # Grid DOIT être <= Sell&Hold (tolérance 5%)
    grid_return = (bot_final.collateral_sol - bot.initial_sol) / bot.initial_sol
    sellhold_return = (sell_hold.iloc[-1] - 1000) / 1000
    
    assert grid_return <= sellhold_return * 1.05, \
        f"Grid ({grid_return:.2%}) ne peut pas battre Sell&Hold ({sellhold_return:.2%})"

def test_buy_hold_follows_price_exactly():
    """Buy&Hold DOIT suivre le prix exactement (1:1)"""
    prices = pd.Series([100, 110, 95, 105, 90])
    
    bench = Benchmarks(1000, 100, leverage=1)
    buy_hold = bench.buy_and_hold(prices)
    
    # Formule : 10 SOL × prix
    expected = prices * 10  # [1000, 1100, 950, 1050, 900]
    
    assert np.allclose(buy_hold, expected, atol=0.01), \
        "Buy&Hold doit suivre le prix exactement (pas de dérive)"
```

**Résultats Réels (SOL Oct 2021 - Dec 2022) :**

```
Prix SOL : $100 → $22 (-78%)

Buy & Hold :
├─ SOL : 10 → 10 (inchangé)
├─ USD : $1000 → $220 (-78%)
└─ Return : -78% ❌

Sell & Hold (5x leverage) :
├─ Price change : (100-22)/22 = 354%
├─ Leveraged : 354% × 5 = 1770%
├─ Fees : -0.2%
├─ Final : $1000 × 17.698 = $17,698
└─ Return : +1670% ✅ (plafond théorique)

Grid Bot (5x leverage) :
├─ SOL : 4.94 → 19.24 (+289%)
├─ USD : $494 → $423 (-14%)
├─ Trades : 35
├─ Fees : $12.45
└─ Return SOL : +289% ✅ (approche Sell&Hold)

VALIDATION :
Grid (+289%) < Sell&Hold (+1670%) ✅
Grid > Buy&Hold (-78%) ✅
Grid accumule SOL pendant bear ✅
```

**L'Intelligence du Benchmark :**

> "Sell & Hold n'est pas un concurrent. C'est le PLAFOND PHYSIQUE de performance pour une stratégie short sur chute linéaire. Grid peut approcher ce plafond, jamais le dépasser (sauf avec chance extrême sur timing)."

**Fichiers Référence :**
- `sol-grid-bot/src/analysis/benchmarks.py`
- `sol-grid-bot/tests/test_truth.py`
- `bundle_a_intelligence.md` (Section "Benchmark Comparison")

---

## 2.2 Sentinel Cross v414 (Mean-Reversion)

### 2.2.1 Philosophie : Contexte Multi-Niveaux

**Principe Fondamental :**

```
Signal BRUT (RSI < 30) ≠ Signal VALIDE
Signal VALIDE = Conditions multiples EN MÊME TEMPS

Cascade de Validation :
1. Volatilité → Ajuste les seuils
2. RSI extrême → Détecte oversold/overbought
3. Trend confirmé → Valide la direction
4. Volume acceptable → Confirme la conviction
5. État position → Oriente l'action (entry vs exit)
```

**Source :** `bundle_b_intelligence.md`, `bundle_c_intelligence.md`

**L'Évolution des Seuils (Corrections 2024-11-12) :**

| Paramètre | v041.3 (ancien) | v041.4 (corrigé) | Raison |
|-----------|-----------------|------------------|--------|
| **rsi_oversold** | 35 | 30 | Trop permissif (signaux prématurés) |
| **rsi_overbought** | 65 | 70 | Trop permissif (exits trop tôt) |
| **volume_threshold** | 1.1 (actions) | 0.4 (crypto) | Crypto = patterns volume différents |
| **adaptive_lookback** | 252 (1 an) | 63 (3 mois) | Crypto = cycles plus courts |
| **trend_confirmation** | Prix > SMA | Prix > SMA ET pente > 0 | Double validation |

**Implémentation :**

```python
# Fichier : bitget_paper/strategy/sentinel_v414.py

class SentinelCrossV414:
    def __init__(self, config: Dict):
        # PARAMÈTRES FIXES (MIF certifiés)
        self.rsi_period = 14
        self.ma_period = 50
        self.volume_ma_period = 20
        self.volatility_threshold = 0.50  # 50% annualisé
        
        # PARAMÈTRES OPTIMISÉS (crypto-specific)
        self.volume_threshold = 0.4  # Relaxé pour crypto
        self.adaptive_lookback = 63  # ~3 mois
        self.rsi_low_vol_oversold = 30  # Corrigé (était 35)
        self.rsi_low_vol_overbought = 70  # Corrigé (était 65)
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Génère signaux avec cascade de conditions
        """
        df = data.copy()
        
        # ===== NIVEAU 1 : INDICATEURS =====
        df['rsi'] = self._calculate_rsi(df['close'], self.rsi_period)
        df['sma'] = df['close'].rolling(self.ma_period).mean()
        df['sma_slope'] = df['sma'].diff()
        df['volume_ma'] = df['volume'].rolling(self.volume_ma_period).mean()
        
        # Volatilité annualisée
        returns = df['close'].pct_change()
        df['volatility'] = returns.rolling(20).std() * np.sqrt(252)
        
        # ===== NIVEAU 2 : SEUILS ADAPTATIFS =====
        df['high_volatility'] = df['volatility'] > self.volatility_threshold
        
        # Seuils RSI dynamiques (percentiles sur lookback)
        df['rsi_20th'] = df['rsi'].rolling(self.adaptive_lookback).quantile(0.20)
        df['rsi_80th'] = df['rsi'].rolling(self.adaptive_lookback).quantile(0.80)
        
        # Application conditionnelle
        df['rsi_oversold'] = np.where(
            df['high_volatility'],
            df['rsi'] < df['rsi_20th'],  # Adaptatif
            df['rsi'] < self.rsi_low_vol_oversold  # Fixe 30
        )
        
        df['rsi_overbought'] = np.where(
            df['high_volatility'],
            df['rsi'] > df['rsi_80th'],  # Adaptatif
            df['rsi'] > self.rsi_low_vol_overbought  # Fixe 70
        )
        
        # ===== NIVEAU 3 : TREND CONFIRMATION =====
        df['trending_up'] = (
            (df['close'] > df['sma']) &  # Prix au-dessus SMA
            (df['sma_slope'] > 0)  # ET pente positive
        )
        
        df['trending_down'] = (
            (df['close'] < df['sma']) &
            (df['sma_slope'] < 0)
        )
        
        # ===== NIVEAU 4 : VOLUME VALIDATION =====
        df['volume_spike'] = df['volume'] > (df['volume_ma'] * self.volume_threshold)
        
        # ===== NIVEAU 5 : CONDITIONS FINALES =====
        # Entry : (Oversold OU Trend up) ET Volume
        df['entry_condition'] = (
            (df['rsi_oversold'] | df['trending_up']) &
            df['volume_spike']
        )
        
        # Exit : Overbought uniquement (pas trending_down !)
        df['exit_condition'] = df['rsi_overbought']
        
        return df
    
    def analyze_current_signal(
        self, 
        data: pd.DataFrame, 
        has_position: bool = False  # ✅ CRITIQUE
    ) -> Dict:
        """
        Analyse signal avec CONTEXTE position
        """
        df = self.generate_signals(data)
        latest = df.iloc[-1]
        
        analysis = {
            'timestamp': latest.name if hasattr(latest, 'name') else datetime.now(),
            'price': latest['close'],
            'rsi': latest['rsi'],
            'volatility': latest['volatility'],
            'signal': 'HOLD',  # Default
            'confidence': 0.0,
            'conditions': {},
            'message': ''
        }
        
        # ===== LOGIQUE CONTEXTUELLE =====
        if has_position:
            # MODE GESTION : Cherche sortie
            if latest['exit_condition']:
                analysis['signal'] = 'SELL'
                analysis['confidence'] = 0.85
                analysis['message'] = 'Take profit : RSI overbought'
            else:
                analysis['message'] = 'Hold position'
        
        else:
            # MODE RECHERCHE : Cherche entrée
            if latest['entry_condition']:
                analysis['signal'] = 'BUY'
                
                # Confidence basée sur nombre de conditions remplies
                conditions_met = sum([
                    latest['rsi_oversold'],
                    latest['trending_up'],
                    latest['volume_spike']
                ])
                analysis['confidence'] = 0.6 + (conditions_met * 0.1)
                
                reasons = []
                if latest['rsi_oversold']:
                    reasons.append('RSI oversold')
                if latest['trending_up']:
                    reasons.append('Trend haussier confirmé')
                if latest['volume_spike']:
                    reasons.append('Volume acceptable')
                
                analysis['message'] = ' + '.join(reasons)
        
        # Contexte pour debugging
        analysis['conditions'] = {
            'rsi_oversold': bool(latest['rsi_oversold']),
            'rsi_overbought': bool(latest['rsi_overbought']),
            'trending_up': bool(latest['trending_up']),
            'trending_down': bool(latest['trending_down']),
            'volume_spike': bool(latest['volume_spike']),
            'high_volatility': bool(latest['high_volatility'])
        }
        
        return analysis
```

**Exemple de Décision Contextuelle :**

```python
# Scénario : RSI = 28 (oversold), Prix > SMA, Volume OK, PAS de position

data = load_ohlcv('BTC/USDT', '1h', 100)
strategy = SentinelCrossV414(config)

analysis = strategy.analyze_current_signal(data, has_position=False)

# Résultat :
{
    'signal': 'BUY',
    'confidence': 0.8,  # 0.6 + 3×0.1 (3 conditions)
    'message': 'RSI oversold + Trend haussier confirmé + Volume acceptable',
    'conditions': {
        'rsi_oversold': True,
        'trending_up': True,
        'volume_spike': True,
        # ...
    }
}

# MÊME scénario AVEC position :
analysis2 = strategy.analyze_current_signal(data, has_position=True)

# Résultat différent :
{
    'signal': 'HOLD',
    'confidence': 0.0,
    'message': 'Hold position',  # Pas de nouveau BUY si déjà en position
}
```

**Fichiers Référence :**
- `bitget_paper/strategy/sentinel_v414.py`
- `bundle_b_intelligence.md` (Section "Decision Flow")
- `bundle_c_intelligence.md` (Section "Strategy Corrections")