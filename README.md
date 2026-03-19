# SOL Grid Bot

**Automated SHORT grid trading bot for SOL/USDT with backtesting, optimization, and paper trading.**

[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-v0.2.0--beta-blue.svg)]()

---

## Status des composants

| Composant | Statut | Description |
|-----------|--------|-------------|
| `GridBotV3` — moteur core | ✅ Opérationnel | Stratégie grid SHORT, levier adaptatif |
| `paper_trade.py` | ✅ Opérationnel | Replay historique, simulateur exchange |
| `backtest.py` | ✅ Opérationnel | Backtesting avec graphiques |
| `run_optimization_lp.py` | ✅ Opérationnel | Optimisation silencieuse + analyse patterns |
| `config_loader.py` | ✅ Opérationnel | Chargement YAML robuste avec dataclasses |
| `data_loader.py` | ✅ Opérationnel | CSV + validation OHLC + adaptation timeframe |
| Exchange Simulator | ✅ Opérationnel | Ordres virtuels, PnL, positions |
| Live exchange | ⏳ Non implémenté | Roadmap v0.3.0 |

**Fonctionnalité globale : ~95% opérationnel** (v0.1.0 était 70%)

---

## Démarrage rapide

```bash
# 1. Cloner
git clone https://github.com/YOUR_USERNAME/sol-grid-bot.git
cd sol-grid-bot

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Générer les données de test (SOL bear market 2021-2022)
python data/generate_test_data.py
# Alternative : télécharger depuis Yahoo Finance
# python data/fetch_sol_yahoo.py

# 4. Backtester
python scripts/backtest.py --data data/SOL_2021_2022.csv --leverage 8

# 5. Paper trader
python scripts/paper_trade.py --data data/SOL_2021_2022.csv

# 6. Optimiser les paramètres
python scripts/run_optimization_lp.py
```

---

## Qu'est-ce que le Grid Trading ?

Le grid trading place des ordres d'achat/vente à intervalles réguliers autour d'un prix de base. Ce bot :

- **Ouvre des positions SHORT** quand le prix monte (vend haut)
- **Ferme les positions** quand le prix baisse pour prendre le profit (achète bas)
- **Utilise le levier** pour amplifier les rendements (5x par défaut)
- **Gère le risque** avec calcul de prix de liquidation et limites de drawdown

**Idéal pour** : marchés baissiers ou en range (ex. SOL 2021-2022 : -95%)

---

## Architecture

```
sol-grid-bot/
├── scripts/
│   ├── backtest.py              # Backtesting historique
│   ├── paper_trade.py           # Paper trading (replay)
│   ├── run_optimization_lp.py   # Optimisation silencieuse + analyse patterns
│   └── exchange_simulator.py    # Simulateur d'exchange virtuel
│
├── src/
│   ├── core/
│   │   ├── grid_bot.py          # GridBotV3 — stratégie principale
│   │   ├── grid_strategy.py     # Stratégie simplifiée
│   │   ├── portfolio.py         # Gestion de portefeuille
│   │   └── risk_manager.py      # Gestion du risque
│   ├── config/
│   │   └── config_loader.py     # Chargeur YAML + dataclasses
│   └── analysis/
│       ├── sol_metrics.py       # Métriques SOL
│       └── benchmarks.py        # Buy&Hold / Sell&Hold
│
├── data/
│   ├── data_loader.py           # Chargeur CSV robuste + validation OHLC
│   ├── generate_test_data.py    # Génère données synthétiques SOL
│   └── fetch_sol_yahoo.py       # Télécharge depuis Yahoo Finance
│
├── config/
│   ├── default.yaml             # Paramètres par défaut
│   ├── conservative.yaml        # Levier bas, grilles larges
│   ├── aggressive.yaml          # Levier élevé, grilles serrées
│   └── optimized.yaml           # Résultats d'optimisation
│
└── results_lp_silent/           # Résultats d'optimisation (généré)
```

---

## Configuration

Éditez `config/default.yaml` :

```yaml
trading:
  initial_capital: 1000      # Capital initial (USD)
  leverage: 5                # Multiplicateur de levier
  symbol: "SOL/USDT"

grid_strategy:
  grid_size: 7               # Nombre de niveaux de grille
  grid_ratio: 0.03           # 3% d'espacement entre grilles
  max_position_size: 0.25    # Max 25% du capital par position
  max_simultaneous_positions: 5

risk_management:
  max_portfolio_drawdown: 0.30   # Stop si 30% de perte
  maintenance_margin: 0.05       # Marge de maintenance exchange
  safety_buffer: 1.5             # Buffer liquidation (×1.5)
  adaptive_leverage:
    enabled: false               # Levier adaptatif selon volatilité
```

**Paramètres clés** :
- `grid_size` : plus de grilles = plus de trades, plus de frais
- `grid_ratio` : espacement plus large = moins de trades, mouvements plus grands
- `leverage` : plus élevé = plus de gain/perte, risque de liquidation plus élevé
- `safety_buffer` : distance de sécurité avant liquidation

---

## Utilisation

### 1. Backtest

```bash
python scripts/backtest.py --data data/SOL_2021_2022.csv --leverage 8

# Analyse de frontière (teste leverage 1x à 20x)
python scripts/backtest.py --data data/SOL_2021_2022.csv --frontier
```

**Résultats typiques (SOL 2021-2022, -97%)** :

| Stratégie | Variation SOL | Retour USD | Trades | Liquidations |
|-----------|--------------|------------|--------|--------------|
| **Grid Bot (5x)** | +1051% | -60% | 72 | 0 |
| Buy & Hold | -97% | -97% | 0 | — |
| Sell & Hold | +3233% | +670% | 0 | — |

---

### 2. Paper Trading

```bash
# Replay rapide (données historiques)
python scripts/paper_trade.py --data data/SOL_2021_2022.csv

# Config agressive
python scripts/paper_trade.py --config config/aggressive.yaml

# Avec délai entre cycles (pour observation)
python scripts/paper_trade.py --sleep 0.1
```

**Output** :
```
CYCLE 1 | Prix $265.17 | Signal: HOLD | Cash: $1000.00 | Equity: $1000.00
✅ BUY 0.942792 @ $261.16 ($246.22)
🔴 SELL 0.942792 @ $184.87 | PnL: -$71.93 (-29.21%)
...
RÉSUMÉ FINAL PAPER TRADING
💰 Equity finale: $424.57
📊 PnL: -575.43 USD (-57.54%)
```

---

### 3. Optimisation des paramètres

```bash
python scripts/run_optimization_lp.py
```

Teste ~15 000 combinaisons de :
- `leverage` : 3–10x
- `grid_size` : 5, 7, 10, 15, 20
- `grid_ratio` : 0.015–0.035
- `max_position_size` : 0.15–0.35
- `max_portfolio_drawdown` : 0.25–0.45
- `safety_buffer` : 1.2–3.0

**Fichiers générés** dans `results_lp_silent/` :
- `top_100_configurations.csv` — top 100 par score composite
- `winning_patterns_analysis.json` — patterns des configs gagnantes
- `parameter_performance_analysis.csv` — performance par paramètre
- `lp_optimization_complete_*.csv` — résultats complets

**Reprise automatique** : interrompez avec `Ctrl+C`, relancez → reprend depuis le checkpoint.

---

### 4. Charger des données custom

```python
from data.data_loader import DataLoader

df = DataLoader.load_csv("data/mon_fichier.csv")
quality = DataLoader.validate_data_quality(df)
timeframe = DataLoader.infer_timeframe(df)
```

---

## Gestion du risque

Le bot inclut plusieurs mécanismes de sécurité :

1. **Prix de liquidation** — buffer de sécurité configurable (`safety_buffer`)
2. **Taille de position** — réduite progressivement avec le nombre de positions ouvertes
3. **Limite de drawdown** — arrêt si perte > `max_portfolio_drawdown`
4. **Levier adaptatif** — réduit en haute volatilité (optionnel)

> **Important** : Le levier amplifie gains ET pertes. Commencer avec 2–3x en paper trading.

---

## Comment ça fonctionne

```
Prix marché : $200
Niveaux de grille : $194, $188, $182, $176, $170, $164, $158

Prix monte à $194 → OUVRE SHORT (vend haut)
Prix descend à $188 → FERME SHORT (achète bas, prend profit)
Profit : $6/SOL × levier × taille de position
Répété pour chaque niveau de grille
```

---

## Prérequis

```
pandas>=2.0.0
numpy>=1.24.0
pyyaml>=6.0
matplotlib>=3.7.0
tqdm>=4.65.0
yfinance>=0.2.0   # Pour fetch_sol_yahoo.py uniquement
```

**Python** : 3.11+

---

## Roadmap

- [x] Backtesting sur données historiques
- [x] Paper trading avec simulateur d'exchange
- [x] Optimisation multi-paramètres avec analyse des patterns
- [x] DataLoader robuste avec validation OHLC
- [x] Génération de données synthétiques reproductibles
- [ ] Connecteurs exchange live (Binance, Bitget)
- [ ] Dashboard web de monitoring
- [ ] Support multi-actifs
- [ ] Alertes Telegram
- [ ] Ajustement dynamique des paramètres en live

---

## Avertissement

**CE LOGICIEL EST À DES FINS ÉDUCATIVES UNIQUEMENT.**

- **PAS DE CONSEIL FINANCIER** : Ne pas utiliser avec de l'argent réel sans tests approfondis.
- **RISQUE ÉLEVÉ** : Le trading de crypto et le levier sont extrêmement risqués.
- **AUCUNE GARANTIE** : Les performances passées n'indiquent pas les résultats futurs.
- **VOTRE RESPONSABILITÉ** : Vous êtes seul responsable de vos décisions de trading.

---

## Licence

MIT — voir [LICENSE](LICENSE)

---

## Contributing

1. Fork le repo
2. Créer une branche : `git checkout -b feature/ma-feature`
3. Commit : `git commit -m "feat: ajouter ma feature"`
4. Push : `git push origin feature/ma-feature`
5. Ouvrir une Pull Request
