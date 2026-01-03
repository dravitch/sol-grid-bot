"""
Téléchargement SOL-USD depuis Yahoo Finance
CORRIGÉ - Format CSV propre
"""

import pandas as pd
import yfinance as yf
from pathlib import Path


def fetch_historical_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Télécharge données historiques propres
    
    Returns:
        DataFrame avec Date index et colonnes: open, high, low, close, volume
    """
    print(f"📥 Downloading {symbol} from {start_date} to {end_date}...")
    
    # Téléchargement
    df = yf.download(symbol, start=start_date, end=end_date, auto_adjust=False)
    
    if df.empty:
        raise ValueError(f"No data received for {symbol}")
    
    # Nettoyage: garde seulement OHLCV
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
    
    # Renommage en lowercase
    df.columns = ['open', 'high', 'low', 'close', 'volume']
    
    # Force conversion numérique
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Supprime lignes avec NaN
    df = df.dropna()
    
    # Arrondit pour réduire taille fichier
    df = df.round(6)
    
    print(f"✅ Downloaded {len(df)} clean data points")
    print(f"   Date range: {df.index[0]} to {df.index[-1]}")
    print(f"   Columns: {list(df.columns)}")
    print(f"\n📊 Sample data:")
    print(df.head(3))
    
    return df


def main():
    """Télécharge et sauvegarde SOL-USD"""
    
    # Configuration
    symbol = "SOL-USD"
    start_date = "2021-10-31"
    end_date = "2022-12-31"
    output_file = "data/SOL_2021_2022.csv"
    
    # Création dossier data si nécessaire
    Path("data").mkdir(exist_ok=True)
    
    # Téléchargement
    df = fetch_historical_data(symbol, start_date, end_date)
    
    # Sauvegarde avec format propre
    df.to_csv(output_file, index=True, float_format='%.6f')
    
    print(f"\n💾 Saved to: {output_file}")
    print(f"📦 File size: {Path(output_file).stat().st_size / 1024:.1f} KB")
    
    # Validation
    print("\n🔍 Validation:")
    test_df = pd.read_csv(output_file, index_col=0, parse_dates=True)
    print(f"   ✓ Rows: {len(test_df)}")
    print(f"   ✓ Columns: {list(test_df.columns)}")
    print(f"   ✓ Data types:\n{test_df.dtypes}")
    print(f"   ✓ First close price: ${test_df['close'].iloc[0]:.2f}")
    print(f"   ✓ Last close price: ${test_df['close'].iloc[-1]:.2f}")


if __name__ == "__main__":
    main()
