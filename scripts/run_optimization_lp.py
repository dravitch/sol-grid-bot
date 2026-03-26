#!/usr/bin/env python3
# scripts/run_optimization_lp.py
"""
Optimiseur LP silencieux avec analyse des patterns gagnants.
Fixes appliqués :
  - Import run_backtest depuis src.core.grid_bot (pas backtest.py inexistant)
  - Création de logs/ avant logging.FileHandler
  - flatten_config() : convertit config YAML nested → dict plat pour GridBotV3
  - volatility : utilise avg_volatility (clé réelle du summary)
  - Sauvegarde top_100 et lp_optimization_complete
"""
import sys
import os
from pathlib import Path

# === PYTHONPATH : projet root ===
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

import itertools
import json
import logging
import pickle
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
import yaml
from tqdm import tqdm
import time

# ⚠️ Créer logs/ AVANT d'instancier FileHandler
Path("logs").mkdir(exist_ok=True)

logging.getLogger().setLevel(logging.ERROR)
warnings.filterwarnings("ignore")
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/optimization_silent.log"),
        logging.StreamHandler(),
    ],
)

# FIX CRITIQUE #1 : run_backtest est dans grid_bot.py, pas backtest.py
from src.core.grid_bot import run_backtest


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================


def load_config(config_path: str) -> dict:
    """Charge la configuration YAML brute (dict nested)."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def flatten_config(nested: dict) -> dict:
    """
    FIX CRITIQUE #3 : Convertit config YAML nested vers dict plat attendu par GridBotV3.

    GridBotV3.__init__ utilise config["leverage"], config["grid_size"], etc.
    mais le YAML a trading.leverage, grid_strategy.grid_size, etc.
    """
    trading = nested.get("trading", {})
    grid = nested.get("grid_strategy", {})
    risk = nested.get("risk_management", {})
    adaptive = risk.get("adaptive_leverage", {})

    return {
        "initial_capital": trading.get("initial_capital", 1000.0),
        "leverage": trading.get("leverage", 5.0),
        "grid_size": grid.get("grid_size", 7),
        "grid_ratio": grid.get("grid_ratio", 0.02),
        "max_position_size": grid.get("max_position_size", 0.25),
        "trading_fee": trading.get("taker_fee", 0.001),
        "maker_fee": trading.get("maker_fee", 0.0005),
        "max_simultaneous_positions": grid.get("max_simultaneous_positions", 5),
        "min_grid_distance": grid.get("min_grid_distance", 0.01),
        "adaptive_spacing": grid.get("adaptive_spacing", False),
        "maintenance_margin": risk.get("maintenance_margin", 0.05),
        "safety_buffer": risk.get("safety_buffer", 1.5),
        "max_portfolio_drawdown": risk.get("max_portfolio_drawdown", 0.30),
        "volatility_lookback": risk.get("volatility_lookback", 20),
        "adaptive_leverage": adaptive.get("enabled", False),
        "leverage_multiplier_low": adaptive.get("leverage_multiplier_low", 1.0),
        "leverage_multiplier_high": adaptive.get("leverage_multiplier_high", 1.0),
    }


def load_data(file_path: str) -> pd.DataFrame:
    """Charge les données historiques depuis CSV."""
    print(f"📊 Loading data from {file_path}...")
    data = pd.read_csv(file_path)

    date_col = next((c for c in ["timestamp", "date", "Date"] if c in data.columns), None)
    if date_col:
        data[date_col] = pd.to_datetime(data[date_col], errors="coerce")
        data = data.set_index(date_col)
    else:
        data.index = pd.date_range(start="2021-01-01", periods=len(data), freq="D")

    required = ["open", "high", "low", "close"]
    missing = [c for c in required if c not in data.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes: {missing}")

    print(f"✅ Data loaded: {len(data)} periods from {data.index[0]} to {data.index[-1]}")
    return data


def analyze_backtest_results_silent(bot, data: pd.DataFrame) -> dict:
    """Analyse silencieuse des résultats de backtest."""
    try:
        summary = bot.get_summary()
        final_price = float(data["close"].iloc[-1]) if len(data) > 0 else 100.0

        return {
            "initial_sol": summary.get("initial_sol", 0),
            "final_sol": summary.get("final_sol", 0),
            "sol_growth_pct": summary.get("sol_change_pct", 0),
            "total_trades": summary.get("total_trades", 0),
            "liquidations": summary.get("liquidations", 0),
            "win_rate": summary.get("win_rate", 0),
            "total_fees_usd": summary.get("total_fees_usd", 0),
            "max_drawdown": summary.get("real_drawdown_pct", summary.get("drawdown_pct", 0)),
            "peak_sol": summary.get("peak_sol", summary.get("initial_sol", 0)),
            "initial_value_usd": summary.get("initial_sol", 0) * bot.initial_price,
            "final_value_usd": summary.get("final_sol", 0) * final_price,
            # FIX #4 : clé réelle est avg_volatility, pas volatility
            "sharpe_ratio": summary.get("sharpe_ratio", 0),
            "volatility": summary.get("avg_volatility", 0),
            "success": True,
            "error": None,
        }
    except Exception as e:
        return {
            "initial_sol": 0, "final_sol": 0, "sol_growth_pct": 0,
            "total_trades": 0, "liquidations": 1, "win_rate": 0,
            "total_fees_usd": 0, "max_drawdown": 100, "peak_sol": 0,
            "initial_value_usd": 0, "final_value_usd": 0,
            "sharpe_ratio": 0, "volatility": 0,
            "success": False, "error": str(e),
        }


# ============================================================================
# CLASSE PRINCIPALE
# ============================================================================


class LPOptimizerSilent:
    """Optimiseur silencieux avec barre de progression unique et analyse des patterns."""

    def __init__(self, config_template: dict, data: pd.DataFrame, param_ranges: dict, output_dir: str = "results_lp_silent"):
        self.config_template = config_template
        self.data = data
        self.param_ranges = param_ranges
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.results = []
        self.best_score = 0.0
        self.best_config = None
        self.start_time = None

        self.param_names = list(param_ranges.keys())
        self.param_combinations = list(itertools.product(*param_ranges.values()))
        self.total_combinations = len(self.param_combinations)
        self.current_iteration = 0
        self.successful_count = 0

    def calculate_score(self, stats: dict) -> float:
        """Score composite : croissance SOL + drawdown + win rate + activité."""
        try:
            growth_score = min(stats["sol_growth_pct"] / 100.0, 2.0)
            dd_penalty = max(0, (abs(stats["max_drawdown"]) - 20) / 80.0)
            dd_score = max(0, 1.0 - dd_penalty)
            win_score = stats["win_rate"] / 100.0
            n = stats["total_trades"]
            trade_score = 0.3 if n < 50 else 0.8 if n < 200 else 0.6 if n < 500 else 0.3
            return max(0.0, growth_score * 0.4 + dd_score * 0.3 + win_score * 0.2 + trade_score * 0.1)
        except Exception:
            return 0.0

    def _calculate_correlation(self, param_values: list, scores: list) -> float:
        """Corrélation entre valeurs d'un paramètre et scores."""
        try:
            if len(param_values) < 2:
                return 0.0
            numeric_vals, numeric_scores = [], []
            for v, s in zip(param_values, scores):
                try:
                    numeric_vals.append(float(v) if isinstance(v, (int, float)) else hash(str(v)) % 1000)
                    numeric_scores.append(s)
                except Exception:
                    continue
            if len(numeric_vals) >= 2:
                return float(np.corrcoef(numeric_vals, numeric_scores)[0, 1])
        except Exception:
            pass
        return 0.0

    def load_checkpoint(self) -> int:
        """Charge la progression existante. Retourne l'index de reprise."""
        checkpoint_file = self.output_dir / "optimization_checkpoint.pkl"
        if checkpoint_file.exists():
            try:
                with open(checkpoint_file, "rb") as f:
                    data = pickle.load(f)
                self.results = data.get("results", [])
                self.best_score = data.get("best_score", 0.0)
                self.best_config = data.get("best_config", None)
                completed = len(self.results)
                print(f"🔄 Reprise depuis checkpoint: {completed}/{self.total_combinations}")
                return completed
            except Exception as e:
                print(f"❌ Erreur chargement checkpoint: {e}")
        return 0

    def create_progress_bar(self, total: int, initial: int = 0):
        return tqdm(
            total=total,
            initial=initial,
            desc="🚀 Optimisation LP",
            unit="test",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}, {postfix}]",
            position=0,
            leave=True,
        )

    def update_progress_stats(self, pbar, completed: int, total: int, start_time: float):
        elapsed = time.time() - start_time
        if completed > 0:
            rate = completed / elapsed
            eta = (total - completed) / rate
            success_rate = self.successful_count / completed * 100
            pbar.set_postfix_str(
                f"ETA:{eta/3600:.1f}h | Speed:{rate*3600:.0f}/h | "
                f"Success:{success_rate:.1f}% | Best:{self.best_score:.3f}"
            )
        pbar.update(1)

    def run_silent_backtest(self, nested_config: dict) -> dict:
        """
        FIX CRITIQUE #3 : flatten le config nested avant d'appeler run_backtest.
        run_backtest(data, config) attend config["leverage"], config["grid_size"], etc.
        """
        orig_level = logging.getLogger().level
        try:
            logging.getLogger().setLevel(logging.CRITICAL)
            flat_config = flatten_config(nested_config)
            portfolio_df, bot = run_backtest(self.data, flat_config)
            return analyze_backtest_results_silent(bot, self.data)
        except Exception as e:
            return {
                "success": False, "error": str(e),
                "initial_sol": 0, "final_sol": 0, "sol_growth_pct": 0,
                "max_drawdown": 100, "total_trades": 0, "win_rate": 0,
                "liquidations": 1, "sharpe_ratio": 0, "volatility": 0,
            }
        finally:
            logging.getLogger().setLevel(orig_level)

    def _analyze_winning_patterns(self, successful_runs: list) -> dict:
        if not successful_runs:
            return {}
        analysis = {}
        for param in self.param_names:
            param_values = [r[param] for r in successful_runs]
            scores = [r.get("score", 0) for r in successful_runs]
            unique_values = list(set(param_values))
            value_performance = []
            for value in unique_values:
                runs = [r for r in successful_runs if r[param] == value]
                s = [r.get("score", 0) for r in runs]
                if s:
                    value_performance.append({
                        "value": value,
                        "count": len(runs),
                        "avg_score": float(np.mean(s)),
                        "max_score": float(max(s)),
                        "avg_sol_growth": float(np.mean([r.get("sol_growth_pct", 0) for r in runs])),
                        "avg_drawdown": float(np.mean([r.get("max_drawdown", 0) for r in runs])),
                        "avg_trades": float(np.mean([r.get("total_trades", 0) for r in runs])),
                    })
            value_performance.sort(key=lambda x: x["avg_score"], reverse=True)
            analysis[param] = {
                "optimal_range": self._find_optimal_range(value_performance),
                "value_performance": value_performance,
                "correlation_with_score": self._calculate_correlation(param_values, scores),
                "most_common_winning_value": max(set(param_values), key=param_values.count),
            }
        return analysis

    def _find_optimal_range(self, value_performance: list) -> dict:
        if not value_performance:
            return {}
        top = value_performance[: max(1, len(value_performance) // 3)]
        numeric = [v["value"] for v in top if isinstance(v["value"], (int, float))]
        if numeric:
            return {"min": min(numeric), "max": max(numeric), "avg": float(np.mean(numeric)),
                    "optimal_values": [v["value"] for v in top]}
        return {"optimal_values": [v["value"] for v in top], "best_value": top[0]["value"]}

    def _calculate_risk_boundaries(self, successful_runs: list) -> dict:
        if not successful_runs:
            return {}
        drawdowns = [r.get("max_drawdown", 0) for r in successful_runs]
        scores = [r.get("score", 0) for r in successful_runs]
        sol_growth = [r.get("sol_growth_pct", 0) for r in successful_runs]
        p25 = float(np.percentile(drawdowns, 25))
        p75 = float(np.percentile(drawdowns, 75))
        low = [r for r in successful_runs if r.get("max_drawdown", 0) <= p25]
        mid = [r for r in successful_runs if p25 < r.get("max_drawdown", 0) <= p75]
        high = [r for r in successful_runs if r.get("max_drawdown", 0) > p75]

        def profile(runs):
            if not runs:
                return {"count": 0, "avg_score": 0, "avg_sol_growth": 0, "avg_drawdown": 0}
            return {
                "count": len(runs),
                "avg_score": float(np.mean([r.get("score", 0) for r in runs])),
                "avg_sol_growth": float(np.mean([r.get("sol_growth_pct", 0) for r in runs])),
                "avg_drawdown": float(np.mean([r.get("max_drawdown", 0) for r in runs])),
            }

        corr_score = float(np.corrcoef(drawdowns, scores)[0, 1]) if len(drawdowns) > 1 else 0
        corr_growth = float(np.corrcoef(drawdowns, sol_growth)[0, 1]) if len(drawdowns) > 1 else 0

        return {
            "risk_thresholds": {"low_risk_max_drawdown": p25, "high_risk_min_drawdown": p75},
            "risk_profiles": {"low_risk": profile(low), "medium_risk": profile(mid), "high_risk": profile(high)},
            "risk_reward_analysis": {
                "correlation_drawdown_score": corr_score,
                "correlation_drawdown_growth": corr_growth,
                "efficient_frontier": self._calculate_efficient_frontier(successful_runs),
            },
        }

    def _calculate_efficient_frontier(self, successful_runs: list) -> dict:
        if len(successful_runs) < 10:
            return {}
        ratios = []
        for r in successful_runs:
            risk = abs(r.get("max_drawdown", 0))
            ret = r.get("sol_growth_pct", 0)
            if risk > 0:
                ratios.append({
                    "return": ret, "risk": risk, "score": r.get("score", 0),
                    "risk_reward_ratio": ret / risk,
                    "parameters": {p: r[p] for p in self.param_names if p in r},
                })
        ratios.sort(key=lambda x: x["risk_reward_ratio"], reverse=True)
        return {
            "best_risk_reward_ratios": ratios[:10],
            "avg_risk_reward_ratio": float(np.mean([r["risk_reward_ratio"] for r in ratios])) if ratios else 0,
            "max_risk_reward_ratio": float(max(r["risk_reward_ratio"] for r in ratios)) if ratios else 0,
        }

    def _save_checkpoint_silent(self, completed: int, pbar):
        try:
            successful_runs = [r for r in self.results if r.get("success", False)]
            winning_analysis = None
            if successful_runs:
                top_configs = sorted(successful_runs, key=lambda x: x.get("score", 0), reverse=True)[:20]
                winning_analysis = {
                    "top_configurations": top_configs,
                    "parameter_patterns": self._analyze_winning_patterns(successful_runs),
                    "risk_boundaries": self._calculate_risk_boundaries(successful_runs),
                    "successful_count": len(successful_runs),
                    "success_rate": len(successful_runs) / len(self.results) * 100,
                }

            checkpoint_data = {
                "results": self.results,
                "best_score": self.best_score,
                "best_config": self.best_config,
                "completed_count": completed,
                "timestamp": datetime.now().isoformat(),
                "winning_analysis": winning_analysis,
            }
            with open(self.output_dir / "optimization_checkpoint.pkl", "wb") as f:
                pickle.dump(checkpoint_data, f)

            if winning_analysis:
                with open(self.output_dir / "winning_patterns_analysis.json", "w") as f:
                    json.dump(winning_analysis, f, indent=2, default=str)

            progress_stats = {
                "total_tests": self.total_combinations,
                "completed_tests": completed,
                "progress_pct": completed / self.total_combinations * 100,
                "elapsed_hours": (time.time() - self.start_time) / 3600,
                "success_rate": len(successful_runs) / completed * 100 if completed > 0 else 0,
                "best_score": self.best_score,
                "winning_configs_count": len(successful_runs),
                "last_update": datetime.now().isoformat(),
            }
            with open(self.output_dir / "progress_stats.json", "w") as f:
                json.dump(progress_stats, f, indent=2)
        except Exception as e:
            pbar.write(f"⚠️ Erreur sauvegarde: {e}")

    def generate_comprehensive_report(self, results_df: pd.DataFrame):
        print("\n" + "=" * 80)
        print("🎯 RAPPORT COMPLET - CARTOGRAPHIE DU RISQUE")
        print("=" * 80)
        successful = results_df[results_df["success"] == True]
        print(f"\n📊 STATISTIQUES GLOBALES:")
        print(f"   Tests totaux:              {len(results_df):,}")
        print(f"   Configurations réussies:   {len(successful):,}")
        print(f"   Taux de succès:            {len(successful)/len(results_df)*100:.1f}%")
        if len(successful) > 0:
            analysis_file = self.output_dir / "winning_patterns_analysis.json"
            if analysis_file.exists():
                with open(analysis_file, "r") as f:
                    analysis = json.load(f)
                self._print_pattern_analysis(analysis)
                self._print_risk_analysis(analysis)
                self._print_efficient_frontier(analysis)
            self._save_insights_csv(results_df)

    def _print_pattern_analysis(self, analysis: dict):
        print(f"\n🔍 PATTERNS DES CONFIGURATIONS GAGNANTES:")
        for param, insights in analysis.get("parameter_patterns", {}).items():
            vp = insights.get("value_performance", [])
            if vp:
                best = vp[0]
                opt = insights.get("optimal_range", {})
                print(f"\n📈 {param.upper()}:")
                print(f"   🎯 Plage optimale: {opt.get('min', 'N/A')} - {opt.get('max', 'N/A')}")
                print(f"   ⭐ Meilleure valeur: {best['value']} (score: {best['avg_score']:.3f})")
                print(f"   📊 Performance: +{best['avg_sol_growth']:.1f}% SOL, {best['avg_drawdown']:.1f}% DD")
                print(f"   🔢 Corrélation avec score: {insights.get('correlation_with_score', 0):.3f}")

    def _print_risk_analysis(self, analysis: dict):
        rb = analysis.get("risk_boundaries", {})
        thresholds = rb.get("risk_thresholds", {})
        print(f"\n⚠️  ANALYSE RISQUE/RENDEMENT:")
        print(f"   Seuils: Low risk ≤{thresholds.get('low_risk_max_drawdown', 0):.1f}% | "
              f"High risk >{thresholds.get('high_risk_min_drawdown', 0):.1f}%")
        for level, profile in rb.get("risk_profiles", {}).items():
            print(f"\n   {level.upper().replace('_', ' ')}:")
            print(f"      Configurations: {profile['count']}")
            print(f"      Score moyen: {profile['avg_score']:.3f}")
            print(f"      Croissance SOL: +{profile['avg_sol_growth']:.1f}%")
            print(f"      Drawdown moyen: {profile['avg_drawdown']:.1f}%")

    def _print_efficient_frontier(self, analysis: dict):
        frontier = (analysis.get("risk_boundaries", {})
                    .get("risk_reward_analysis", {})
                    .get("efficient_frontier", {})
                    .get("best_risk_reward_ratios", []))
        if frontier:
            print(f"\n🎯 FRONTIÈRE EFFICIENTE (Top 5 ratio risque/rendement):")
            for i, cfg in enumerate(frontier[:5], 1):
                print(f"\n   #{i} - Ratio: {cfg['risk_reward_ratio']:.2f}")
                print(f"      Rendement: +{cfg['return']:.1f}% | Risque: {cfg['risk']:.1f}%")
                print(f"      Score: {cfg['score']:.3f}")
                key_params = {k: v for k, v in cfg.get("parameters", {}).items()
                              if any(x in k for x in ["leverage", "drawdown", "size"])}
                print(f"      Paramètres: {key_params}")

    def _save_insights_csv(self, results_df: pd.DataFrame):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            successful = results_df[results_df["success"] == True]

            # FIX #5 : fichiers mentionnés dans le rapport mais jamais sauvegardés
            if len(successful) > 0:
                successful.to_csv(self.output_dir / "winning_configurations_detailed.csv", index=False)
                top100 = successful.nlargest(100, "score")
                top100.to_csv(self.output_dir / "top_100_configurations.csv", index=False)

            results_df.to_csv(
                self.output_dir / f"lp_optimization_complete_{timestamp}.csv", index=False
            )

            param_rows = []
            for param in self.param_names:
                if param in successful.columns:
                    grouped = successful.groupby(param).agg(
                        avg_score=("score", "mean"),
                        max_score=("score", "max"),
                        config_count=("score", "count"),
                        avg_sol_growth=("sol_growth_pct", "mean"),
                        avg_drawdown=("max_drawdown", "mean"),
                        avg_trades=("total_trades", "mean"),
                    ).round(3).reset_index()
                    grouped.insert(0, "parameter", param)
                    param_rows.append(grouped)

            if param_rows:
                pd.concat(param_rows, ignore_index=True).to_csv(
                    self.output_dir / "parameter_performance_analysis.csv", index=False
                )

            print(f"\n💾 FICHIERS D'ANALYSE SAUVEGARDÉS dans {self.output_dir}/:")
            print(f"   - lp_optimization_complete_{timestamp}.csv")
            print(f"   - winning_configurations_detailed.csv")
            print(f"   - top_100_configurations.csv")
            print(f"   - parameter_performance_analysis.csv")
            print(f"   - winning_patterns_analysis.json")
        except Exception as e:
            print(f"⚠️ Erreur sauvegarde CSV: {e}")

    def run_optimization_silent(self) -> pd.DataFrame:
        """Lance l'optimisation complète."""
        print("\n" + "=" * 80)
        print("🚀 LP OPTIMIZER - MODE SILENCIEUX AVEC ANALYSE")
        print("=" * 80)
        start_index = self.load_checkpoint()
        self.start_time = time.time()
        print(f"📊 Combinaisons: {self.total_combinations:,}")
        print(f"⏱️  Estimation: {self.total_combinations * 8 / 3600:.1f}h")
        print(f"💾 Dossier: {self.output_dir}/")
        print("\n🎯 Barre de progression active - Analyse des patterns activée\n")

        pbar = self.create_progress_bar(self.total_combinations, start_index)
        checkpoint_interval = 100

        for i, combo in enumerate(self.param_combinations[start_index:], start_index):
            self.current_iteration = i
            try:
                # Copie profonde du template
                test_config = yaml.safe_load(yaml.dump(self.config_template))

                # Appliquer paramètres via notation pointée
                for j, param_name in enumerate(self.param_names):
                    keys = param_name.split(".")
                    current = test_config
                    for key in keys[:-1]:
                        if key not in current:
                            current[key] = {}
                        current = current[key]
                    current[keys[-1]] = combo[j]

                # Synchroniser grid.* → grid_strategy.* (si utilisé)
                if "grid" in test_config and "grid_strategy" in test_config:
                    for key in test_config["grid"]:
                        test_config["grid_strategy"][key] = test_config["grid"][key]

                # Backtest silencieux (config nested → flatten automatique)
                stats = self.run_silent_backtest(test_config)
                score = self.calculate_score(stats)

                max_dd_config = (
                    test_config.get("risk_management", {}).get("max_portfolio_drawdown", 0.30)
                )
                success = (
                    abs(stats["max_drawdown"]) / 100 <= max_dd_config
                    and stats["liquidations"] == 0
                    and stats["final_sol"] > stats["initial_sol"]
                )

                if success:
                    self.successful_count += 1

                result = {
                    **{self.param_names[j]: combo[j] for j in range(len(self.param_names))},
                    "score": score,
                    "success": success,
                    "final_sol": stats["final_sol"],
                    "sol_growth_pct": stats["sol_growth_pct"],
                    "final_usd": stats["final_value_usd"],
                    "max_drawdown": stats["max_drawdown"],
                    "total_trades": stats["total_trades"],
                    "win_rate": stats["win_rate"],
                    "sharpe_ratio": stats["sharpe_ratio"],
                    "volatility": stats["volatility"],
                    "config_hash": hash(str(combo)),
                }

                if not success:
                    failures = []
                    if abs(stats["max_drawdown"]) / 100 > max_dd_config:
                        failures.append("drawdown")
                    if stats["liquidations"] > 0:
                        failures.append("liquidation")
                    if stats["final_sol"] <= stats["initial_sol"]:
                        failures.append("no_growth")
                    result["failure_reason"] = ", ".join(failures)

                self.results.append(result)

                if success and score > self.best_score:
                    self.best_score = score
                    self.best_config = result.copy()
                    pbar.write(
                        f"🎉 NOUVEAU RECORD! Score: {score:.4f} | "
                        f"SOL: +{stats['sol_growth_pct']:.1f}% | Trades: {stats['total_trades']}"
                    )

            except Exception as e:
                self.results.append({
                    **{self.param_names[j]: combo[j] for j in range(len(self.param_names))},
                    "score": 0, "success": False,
                    "failure_reason": f"error: {e}",
                    "sol_growth_pct": 0, "max_drawdown": 0,
                    "config_hash": hash(str(combo)),
                })

            self.update_progress_stats(pbar, i + 1, self.total_combinations, self.start_time)

            if (i + 1) % checkpoint_interval == 0:
                self._save_checkpoint_silent(i + 1, pbar)

        pbar.close()
        self._save_checkpoint_silent(self.total_combinations, pbar)
        return pd.DataFrame(self.results)


# ============================================================================
# MAIN
# ============================================================================


def main_silent():
    """Point d'entrée principal."""
    output_dir = "results_lp_silent"
    os.makedirs(output_dir, exist_ok=True)

    print("\n" + "=" * 80)
    print("🚀 LP OPTIMIZER - ANALYSE COMPLÈTE DES PATTERNS")
    print("=" * 80)

    try:
        base_config = load_config("config/default.yaml")
        print("✅ Configuration chargée")
    except Exception as e:
        print(f"❌ Erreur config: {e}")
        return

    param_ranges = {
        "trading.leverage": [3, 4, 5, 6, 7, 8, 9, 10],
        "grid_strategy.grid_size": [5, 7, 10, 15, 20],
        "grid_strategy.grid_ratio": [0.015, 0.018, 0.02, 0.025, 0.03, 0.035],
        "grid_strategy.max_position_size": [0.15, 0.20, 0.25, 0.30, 0.35],
        "risk_management.max_portfolio_drawdown": [0.25, 0.30, 0.35, 0.40, 0.45],
        # Note: emergency_stop_loss supprimé — non utilisé par GridBotV3
        # Remplacé par safety_buffer qui affecte réellement les liquidations
        "risk_management.safety_buffer": [1.2, 1.5, 2.0, 2.5, 3.0],
    }

    total = int(np.prod([len(v) for v in param_ranges.values()]))
    print(f"📊 Combinaisons: {total:,}")
    print(f"⏱️  Estimation: {total * 8 / 3600:.1f}h")
    print("🔇 Mode silencieux — barre unique avec ETA et stats en direct")
    print("🔍 Analyse patterns gagnants + frontière efficiente\n")

    try:
        data = load_data("data/SOL_2021_2022.csv")
    except Exception as e:
        print(f"❌ Erreur données: {e}")
        print("💡 Générer les données: python data/generate_test_data.py")
        return

    optimizer = LPOptimizerSilent(base_config, data, param_ranges, output_dir)

    response = input("❓ Démarrer optimisation avec analyse patterns? (o/n): ")
    if response.lower() not in ["o", "oui", "y", "yes"]:
        print("❌ Annulé")
        return

    try:
        print("\n🎯 DÉMARRAGE OPTIMISATION...")
        print("   (Ctrl+C pour interrompre et sauvegarder)\n")

        results_df = optimizer.run_optimization_silent()

        print(f"\n✅ OPTIMISATION TERMINÉE!")
        optimizer.generate_comprehensive_report(results_df)

        print(f"""
📁 Dossier: {output_dir}/
📊 FICHIERS:
   • lp_optimization_complete_*.csv       → Tous les résultats
   • winning_configurations_detailed.csv  → Configs gagnantes
   • top_100_configurations.csv           → Top 100 par score
   • parameter_performance_analysis.csv   → Perf par paramètre
   • winning_patterns_analysis.json       → Analyse complète
        """)

    except KeyboardInterrupt:
        print(f"\n\n⚠️ INTERRUPTION MANUELLE — sauvegarde en cours...")
        if optimizer.results:
            results_df = pd.DataFrame(optimizer.results)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_df.to_csv(f"{output_dir}/partial_results_{ts}.csv", index=False)
            if len(results_df[results_df["success"] == True]) >= 10:
                optimizer.generate_comprehensive_report(results_df)
            else:
                print(f"⚠️ Données insuffisantes pour rapport complet.")
            print("✅ Résultats partiels sauvegardés")

    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main_silent()
