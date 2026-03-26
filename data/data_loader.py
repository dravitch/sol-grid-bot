"""
DataLoader - Chargement CSV robuste avec standards MIF.
Source: data_loader.py original + corrections DeepSeek.
Usage: DataLoader.load_csv("data/SOL_2021_2022.csv")
"""
import logging
import math
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class DataLoader:
    """Charge et valide données prix depuis fichiers CSV."""

    @staticmethod
    def load_csv(filepath: str, reset_index: bool = True) -> pd.DataFrame:
        """
        Charge données prix depuis CSV avec standards MIF.

        Args:
            filepath: Chemin vers le CSV
            reset_index: Si True, index entier (pour itération)

        Returns:
            DataFrame avec colonnes OHLCV normalisées

        Raises:
            ValueError: Fichier manquant ou colonne 'close' absente
        """
        path = Path(filepath)
        if not path.exists():
            raise ValueError(f"File not found: {filepath}")

        try:
            df = pd.read_csv(filepath, index_col=0, parse_dates=True)
        except Exception:
            df = pd.read_csv(filepath)

        # Standardize column names (lowercase)
        df.columns = df.columns.str.lower()

        if "close" not in df.columns:
            raise ValueError(
                f"CSV must have 'close' column. Found: {df.columns.tolist()}"
            )

        # Keep OHLCV columns
        ohlcv_cols = ["open", "high", "low", "close", "volume"]
        available_cols = [col for col in ohlcv_cols if col in df.columns]
        if not available_cols:
            available_cols = ["close"]

        result = df[available_cols].copy()

        # Drop NaN
        initial_len = len(result)
        result = result.dropna()
        dropped = initial_len - len(result)
        if dropped > 0:
            logger.info("Dropped %d rows with NaN values", dropped)

        if len(result) == 0:
            raise ValueError("No valid data after removing NaN values")

        # Validate OHLC coherence
        if all(col in result.columns for col in ["open", "high", "low", "close"]):
            valid_ohlc = (
                (result["high"] >= result["low"])
                & (result["high"] >= result["close"])
                & (result["high"] >= result["open"])
                & (result["low"] <= result["close"])
                & (result["low"] <= result["open"])
            )
            invalid_count = (~valid_ohlc).sum()
            if invalid_count > 0:
                logger.warning(
                    "Found %d rows with invalid OHLC relationships", invalid_count
                )
                result = result[valid_ohlc]

        if reset_index:
            result = result.reset_index(drop=True)

        logger.info(
            "Loaded %d clean data points from %s. Price range: $%.2f - $%.2f",
            len(result),
            filepath,
            result["close"].min(),
            result["close"].max(),
        )
        return result

    @staticmethod
    def validate_data_quality(df: pd.DataFrame) -> dict:
        """
        Métriques qualité MIF.

        Returns:
            Dict avec quality_score (0-1), outliers, etc.
        """
        metrics = {
            "total_rows": len(df),
            "missing_values": int(df.isnull().sum().sum()),
            "completeness": 1
            - (df.isnull().sum().sum() / (len(df) * len(df.columns))),
        }

        if "close" in df.columns:
            price_changes = df["close"].pct_change().abs()
            metrics["max_price_jump"] = float(price_changes.max())
            metrics["avg_price_change"] = float(price_changes.mean())
            mean_change = price_changes.mean()
            std_change = price_changes.std()
            outliers = price_changes > (mean_change + 10 * std_change)
            metrics["outlier_count"] = int(outliers.sum())

        quality_score = metrics["completeness"]
        if metrics.get("outlier_count", 0) > 0:
            quality_score *= 0.9
        metrics["quality_score"] = quality_score

        return metrics

    @staticmethod
    def infer_timeframe(df: pd.DataFrame) -> str:
        """
        Infère le timeframe depuis l'index DatetimeIndex.

        Returns:
            '1h', '4h', '1d', '1w' ou 'unknown'
        """
        if not isinstance(df.index, pd.DatetimeIndex) or len(df) < 3:
            return "unknown"

        deltas = pd.Series(df.index).diff().dropna()
        median_hours = deltas.median().total_seconds() / 3600

        if median_hours < 2:
            return "1h"
        elif median_hours < 6:
            return "4h"
        elif median_hours < 48:
            return "1d"
        else:
            return "1w"


def validate_timeframe_consistency(config: dict, timeframe: str) -> list:
    """
    Vérifie cohérence paramètres / timeframe.

    Grid Ratio (γ) recommandé par timeframe :
    - 1h  : γ = 0.5-3.0%
    - 4h  : γ = 2-4%
    - 1d  : γ = 3-15%
    - 1w  : γ = 10-20%

    Safety Buffer (β) recommandé :
    - 1h  : β = 1.0-3.0x
    - 1d  : β = 2.5-8.0x

    Returns:
        Liste de warnings (vide si tout est cohérent)
    """
    rules = {
        "1h": {"max_grid_ratio": 0.03, "min_safety_buffer": 1.0, "max_safety_buffer": 3.0},
        "4h": {"max_grid_ratio": 0.06, "min_safety_buffer": 1.5, "max_safety_buffer": 5.0},
        "1d": {"max_grid_ratio": 0.15, "min_safety_buffer": 2.5, "max_safety_buffer": 8.0},
        "1w": {"max_grid_ratio": 0.25, "min_safety_buffer": 4.0, "max_safety_buffer": 12.0},
    }

    if timeframe not in rules:
        return []

    rule = rules[timeframe]
    warnings = []
    gr = config.get("grid_ratio", 0)
    sb = config.get("safety_buffer", 0)

    if gr > rule["max_grid_ratio"]:
        warnings.append(
            f"grid_ratio={gr:.3f} > max {rule['max_grid_ratio']:.3f} pour {timeframe}"
        )
    if sb < rule["min_safety_buffer"]:
        warnings.append(
            f"safety_buffer={sb} < min {rule['min_safety_buffer']} pour {timeframe}"
        )
    if sb > rule["max_safety_buffer"]:
        warnings.append(
            f"safety_buffer={sb} > max {rule['max_safety_buffer']} pour {timeframe}"
        )

    return warnings


def adapt_config_to_timeframe(base_config: dict, source_tf: str, target_tf: str) -> dict:
    """
    Adapte une config d'un timeframe source vers un timeframe cible.

    Physique financière :
    - grid_ratio  : proportionnel à √(temps)
    - safety_buffer : proportionnel au temps (linéaire) avec CAP
    - grid_size   : inversement proportionnel

    Args:
        base_config: Config originale (calibrée pour source_tf)
        source_tf: Timeframe source ('1h', '4h', '1d')
        target_tf: Timeframe cible

    Returns:
        Config adaptée (copie)
    """
    hours_map = {
        "1m": 1 / 60, "5m": 5 / 60, "15m": 0.25,
        "1h": 1, "4h": 4, "1d": 24, "1w": 168,
    }

    if source_tf not in hours_map or target_tf not in hours_map:
        return dict(base_config)

    source_hours = hours_map[source_tf]
    target_hours = hours_map[target_tf]
    config = dict(base_config)

    # grid_ratio : √t (volatilité scale en racine du temps)
    if "grid_ratio" in config:
        ratio_factor = math.sqrt(target_hours / source_hours)
        config["grid_ratio"] = round(config["grid_ratio"] * ratio_factor, 4)

    # safety_buffer : linéaire avec CAP par timeframe
    buffer_caps = {"1h": 3.0, "4h": 5.0, "1d": 8.0, "1w": 12.0}
    if "safety_buffer" in config:
        buffer_factor = target_hours / source_hours
        raw_buffer = config["safety_buffer"] * buffer_factor
        cap = buffer_caps.get(target_tf, 8.0)
        config["safety_buffer"] = round(min(raw_buffer, cap), 1)

    # grid_size : inversement proportionnel
    if "grid_size" in config:
        size_factor = source_hours / target_hours
        config["grid_size"] = max(2, int(config["grid_size"] * size_factor))

    logger.info(
        "Config adaptée %s → %s : grid_ratio=%.4f, safety_buffer=%.1f, grid_size=%d",
        source_tf, target_tf,
        config.get("grid_ratio", 0),
        config.get("safety_buffer", 0),
        config.get("grid_size", 0),
    )
    return config
