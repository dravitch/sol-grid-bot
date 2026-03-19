# Changelog

Toutes les modifications notables de ce projet sont documentées ici.
Format basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/).

---

## [0.2.0] - 2026-03-19

### Ajouté
- `scripts/run_optimization_lp.py` — optimiseur LP silencieux avec analyse des patterns gagnants,
  frontière efficiente risque/rendement, et reprise depuis checkpoint
- `data/data_loader.py` — chargeur CSV robuste : validation OHLC, inférence de timeframe,
  adaptation de config entre timeframes (`adapt_config_to_timeframe`)
- `data/generate_test_data.py` — génération de données synthétiques SOL bear market 2021-2022
  reproductibles (crashs LUNA et FTX inclus), alternative à yfinance si réseau indisponible
- `logs/` — répertoire de logs (créé automatiquement, exclu du git)

### Corrigé

#### `scripts/paper_trade.py`
- **Import critique** : `from exchange_simulator import ExchangeSimulator` échouait car `scripts/`
  n'était pas dans `sys.path`. Correction : ajout de `scripts_dir` au `sys.path`.
- **Performance** : `--sleep` par défaut réduit de `0.3s` à `0.0s` (replay 427 bougies en < 1s
  au lieu de ~2 minutes)

#### `scripts/run_optimization_lp.py` (6 bugs vs version originale)
1. **Import inexistant** : `from src.core.backtest import run_backtest` → `src/core/backtest.py`
   n'existe pas. Corrigé vers `src.core.grid_bot.run_backtest`.
2. **Crash à l'import** : `logging.FileHandler('logs/...')` appelé avant la création du
   répertoire `logs/`. Ajout de `Path("logs").mkdir(exist_ok=True)` avant `logging.basicConfig`.
3. **Config mismatch critique** : `run_backtest` attend un dict plat (`config["leverage"]`,
   `config["grid_size"]`...) mais l'optimiseur passait le dict YAML nested
   (`config["trading"]["leverage"]`...). Ajout de `flatten_config()` pour la conversion.
4. **Clé manquante** : `summary.get('volatility')` retournait toujours `0` car la clé réelle
   dans `bot.get_summary()` est `avg_volatility`. Corrigé.
5. **Fichiers manquants** : `top_100_configurations.csv` et `lp_optimization_complete_*.csv`
   mentionnés dans le rapport final mais jamais sauvegardés. Implémentés.
6. **Paramètre inutile** : `emergency_stop_loss` dans `param_ranges` n'est pas utilisé par
   `GridBotV3`. Remplacé par `safety_buffer` qui affecte réellement les prix de liquidation.

### Supprimé
- `.venv_papertrading/` — environnement virtuel Python de 34 Mo committé par erreur.
  Supprimé du tracking git et ajouté au `.gitignore`.

### Modifié
- `README.md` — mis à jour vers v0.2.0 : tableau de statut des composants, architecture
  complète, commandes corrigées, résultats réels documentés
- `.gitignore` — ajout de `.venv_papertrading/`

### Statut fonctionnel

| Composant | v0.1.0 | v0.2.0 |
|-----------|--------|--------|
| GridBotV3 | ✅ | ✅ |
| Paper Trading | ⚠️ Fragile | ✅ |
| Backtesting | ✅ | ✅ |
| Optimisation | ❌ Cassé | ✅ |
| Config Loader | ✅ | ✅ |
| DataLoader | ❌ Manquant | ✅ |
| Exchange Simulator | ✅ | ✅ |
| **Global** | **~70%** | **~95%** |

---

## [0.1.0] - 2026-03-18

### Ajouté
- Version initiale expérimentale
- `GridBotV3` — stratégie de grid trading SHORT configurable via YAML
- `scripts/backtest.py` — backtesting sur données historiques avec graphiques
- `scripts/paper_trade.py` — paper trading en mode replay (version initiale, import cassé)
- `scripts/exchange_simulator.py` — simulateur d'exchange virtuel
- `scripts/optimize.py` — optimiseur de paramètres (cassé, `DataLoader` manquant)
- `src/core/grid_strategy.py`, `portfolio.py`, `risk_manager.py`
- `src/analysis/sol_metrics.py`, `benchmarks.py`
- `config/default.yaml`, `conservative.yaml`, `aggressive.yaml`, `optimized.yaml`
- `data/fetch_sol_yahoo.py` — téléchargement données SOL-USD via yfinance
- Documentation README complète

### Limitations connues v0.1.0
- `paper_trade.py` : import `exchange_simulator` cassé (sys.path incomplet)
- `optimize.py` : import `DataLoader` cassé (fichier inexistant)
- `.venv_papertrading/` committé par erreur dans le repo (34 Mo)
- Données historiques CSV non incluses (yfinance requis)
