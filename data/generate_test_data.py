"""
Génère données synthétiques SOL-USD pour tests paper trading.
Reproduit le bear market 2021-2022 : ~$260 → ~$7 (-97%)
Inclut les crashs LUNA (mai 2022) et FTX (novembre 2022).

Usage:
    python data/generate_test_data.py
"""
import numpy as np
import pandas as pd
from pathlib import Path


def generate_sol_bear_market(
    start_price: float = 260.0,
    end_price: float = 7.0,
    start_date: str = "2021-10-31",
    end_date: str = "2022-12-31",
    daily_vol: float = 0.055,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Génère données OHLCV synthétiques réalistes pour SOL bear market.

    Args:
        start_price: Prix initial (~260$ oct 2021)
        end_price: Prix final (~7$ dec 2022)
        start_date: Date de début
        end_date: Date de fin
        daily_vol: Volatilité journalière (5.5% pour SOL)
        seed: Graine aléatoire pour reproductibilité

    Returns:
        DataFrame OHLCV avec index DatetimeIndex
    """
    np.random.seed(seed)

    dates = pd.date_range(start_date, end_date, freq="D")
    n = len(dates)

    # Drift pour atteindre end_price depuis start_price
    daily_drift = np.log(end_price / start_price) / n

    # Geometric Brownian Motion
    log_returns = np.random.normal(daily_drift, daily_vol, n)

    # Crashs majeurs historiques
    luna_idx = int(n * 185 / 427)   # LUNA crash mai 2022
    ftx_idx = int(n * 370 / 427)    # FTX crash nov 2022
    log_returns[luna_idx] -= 0.30
    log_returns[luna_idx + 1] -= 0.25
    log_returns[ftx_idx] -= 0.35
    log_returns[ftx_idx + 1] -= 0.20

    close_prices = start_price * np.exp(np.cumsum(log_returns))
    close_prices = np.clip(close_prices, 3.0, start_price * 1.1)

    # OHLCV
    intraday_vol = 0.025
    df = pd.DataFrame(index=dates)
    df.index.name = "Date"
    df["open"] = close_prices * (1 + np.random.normal(0, intraday_vol, n))
    df["high"] = close_prices * (1 + np.abs(np.random.normal(0.02, intraday_vol, n)))
    df["low"] = close_prices * (1 - np.abs(np.random.normal(0.02, intraday_vol, n)))
    df["close"] = close_prices
    df["volume"] = np.random.uniform(1e8, 8e8, n)

    # Cohérence OHLC
    df["high"] = df[["high", "close", "open"]].max(axis=1) * 1.005
    df["low"] = df[["low", "close", "open"]].min(axis=1) * 0.995

    return df.round(6)


def main():
    output_path = Path("data/SOL_2021_2022.csv")
    Path("data").mkdir(exist_ok=True)

    print("Generating synthetic SOL-USD bear market data...")
    df = generate_sol_bear_market()

    df.to_csv(output_path)

    print(f"Saved {len(df)} rows to {output_path}")
    print(f"Price range: ${df['close'].iloc[0]:.2f} -> ${df['close'].iloc[-1]:.2f} "
          f"({((df['close'].iloc[-1]/df['close'].iloc[0])-1)*100:.1f}%)")
    print(f"Date range: {df.index[0].date()} -> {df.index[-1].date()}")


if __name__ == "__main__":
    main()
