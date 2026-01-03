# Data Directory

This directory contains historical price data for backtesting.

## Quick Download

```bash
# SOL/USD 2021-2022 (used in examples)
python -c "import yfinance as yf; yf.download('SOL-USD', start='2021-10-31', end='2022-12-31').to_csv('data/SOL_2021_2022.csv')"
```

## Manual Download

1. Install yfinance:
   ```bash
   pip install yfinance
   ```

2. Download custom date range:
   ```python
   import yfinance as yf
   
   data = yf.download(
       'SOL-USD',
       start='2021-01-01',
       end='2023-12-31',
       interval='1d'
   )
   data.to_csv('data/SOL_custom.csv')
   ```

## Data Format

CSV files should have these columns:
- `Date` (index)
- `Open`
- `High`
- `Low`
- `Close`
- `Volume`

Example:
```csv
Date,Open,High,Low,Close,Volume
2021-10-31,202.42,210.15,195.30,205.87,1234567
2021-11-01,205.87,215.20,200.10,208.45,2345678
...
```

## Notes

- Files in this directory are ignored by git (`.gitignore`)
- Download size: ~50KB per year of daily data
- Use 1-hour or 15-min intervals for more granular backtests