# 🤖 SOL Grid Bot

**Automated grid trading bot for SOL/USDT with backtesting, optimization, and paper trading.**

[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-experimental-orange.svg)]()

---

## ⚡ Quick Start

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/sol-grid-bot.git
cd sol-grid-bot

# 2. Install
pip install -r requirements.txt

# 3. Download data
python -c "import yfinance as yf; yf.download('SOL-USD', start='2021-10-31', end='2022-12-31').to_csv('data/SOL_2021_2022.csv')"

# 4. Run backtest
python scripts/backtest.py --data data/SOL_2021_2022.csv

# 5. Optimize parameters
python scripts/optimize.py --data data/SOL_2021_2022.csv

# 6. Paper trade (simulation)
python scripts/paper_trade.py
```

---

## 📖 What is Grid Trading?

Grid trading is a strategy that places buy and sell orders at regular intervals around a base price. This bot:

- **Opens SHORT positions** when price rises (sells high)
- **Closes positions** when price drops to take profit (buys low)
- **Uses leverage** to amplify returns (8x by default)
- **Manages risk** with liquidation price calculations

**Best for**: Range-bound or declining markets (like SOL 2021-2022: -95%)

---

## 🎯 Features

| Feature | Description | Script |
|---------|-------------|--------|
| **Backtesting** | Test strategy on historical data | `backtest.py` |
| **Optimization** | Find best parameters (grid size, leverage, etc.) | `optimize.py` |
| **Paper Trading** | Simulate live trading with virtual funds | `paper_trade.py` |
| **Risk Management** | Liquidation price, drawdown limits, position sizing | Built-in |

---

## 📊 Architecture

```
sol-grid-bot/
├── scripts/
│   ├── backtest.py          # Historical backtesting
│   ├── optimize.py          # Parameter optimization
│   └── paper_trade.py       # Paper trading simulator
│
├── src/
│   ├── core/
│   │   └── grid_bot.py      # GridBotV3 strategy
│   └── config/
│       └── config_loader.py # YAML config loader
│
├── config/
│   └── default.yaml         # Default parameters
│
├── exchange_simulator.py    # Virtual exchange for paper trading
├── data/                    # Historical price data
└── results/                 # Optimization results, charts
```

---

## ⚙️ Configuration

Edit `config/default.yaml` to customize strategy:

```yaml
trading:
  initial_capital: 1000      # Starting capital (USD)
  leverage: 8                # Leverage multiplier
  symbol: "SBTC/SUSDT:SUSDT"

grid_strategy:
  grid_size: 7               # Number of grid levels
  grid_ratio: 0.02           # 2% spacing between grids
  max_position_size: 0.3     # Max 30% capital per position

risk_management:
  max_portfolio_drawdown: 0.30      # Stop if 30% loss
  maintenance_margin: 0.05          # Exchange margin requirement
  min_liquidation_distance: 0.15    # Safety buffer
```

**Key Parameters**:
- `grid_size`: More grids = more trades, more fees
- `grid_ratio`: Wider spacing = fewer trades, bigger moves needed
- `leverage`: Higher = more profit/loss, higher liquidation risk
- `max_position_size`: Risk per trade (30% = conservative)

---

## 🚀 Usage

### 1. Backtest Strategy

Test on historical data to see performance:

```bash
python scripts/backtest.py --data data/SOL_2021_2022.csv --leverage 8
```

**Output**:
```
📊 SOL METRICS:
   Initial SOL:    4.9402
   Final SOL:      19.1316 (+287.3%)
   USD Value:      $189.02 (-81.1% from $1000)
   Total Trades:   25
   Win Rate:       88.0%
   Max Drawdown:   0.0%
   Liquidations:   0
```

**Interpretation**:
- ✅ SOL accumulation: 287% more SOL
- ⚠️ USD loss: Market dropped 95%, bot lost 81% (better than buy&hold)
- ✅ No liquidations = safe leverage usage

---

### 2. Optimize Parameters

Find best configuration for your data:

```bash
python scripts/optimize.py --data data/SOL_2021_2022.csv
```

Tests 1000 combinations of:
- `grid_size`: 3-50
- `grid_ratio`: 0.01-0.50
- `leverage`: 1-20x
- `max_position_size`: 0.1-1.0

**Output**: `results/optimization_YYYYMMDD_HHMMSS.csv`

**Top performers**:
```
🏆 #1: grid_size=50, grid_ratio=0.03, leverage=20x → +287% SOL
🏆 #2: grid_size=30, grid_ratio=0.03, leverage=15x → +264% SOL
🏆 #3: grid_size=10, grid_ratio=0.03, leverage=20x → +257% SOL
```

⚠️ **Warning**: Past performance ≠ future results. Always paper trade first.

---

### 3. Paper Trade (Simulation)

Test strategy in real-time simulation without risk:

```bash
python scripts/paper_trade.py
```

**Runs on historical data** with:
- Virtual $1000 capital
- Real order execution simulation
- Slippage and fees included
- Live equity tracking

**Output**:
```
Cycle 1/426 | Prix $202.42 | Cash $1000 | Equity $1000
✅ BUY 1.482060 @ $195.49 ($289.72)
🔴 SELL 1.482060 @ $155.21 | PnL: $-59.69 (-20.60%)
...
📊 RÉSUMÉ FINAL:
   Equity finale: $741.27
   PnL: -258.73 USD (-25.87%)
```

---

## 📈 Example Results

**Backtest on SOL 2021-2022** (market -95%):

| Strategy | SOL Change | USD Return | Trades | Liquidations |
|----------|-----------|------------|--------|--------------|
| **Grid Bot (8x)** | +287% | -81% | 25 | 0 |
| Buy & Hold | -95% | -95% | 0 | - |
| Sell & Hold | +1212% | +285% | 0 | - |

**Key Insight**: Grid bot accumulated 287% more SOL while market crashed. In a recovery, this would massively outperform.

---

## 🛡️ Risk Management

The bot includes multiple safety mechanisms:

1. **Liquidation Price Calculation**
   - Maintains safety buffer (50% by default)
   - Monitors distance to liquidation continuously

2. **Position Sizing**
   - Never risks more than `max_position_size` per trade
   - Reduces size as positions accumulate

3. **Drawdown Limits**
   - Stops trading if portfolio drawdown > 30%
   - Emergency stop-loss at 15% (optional)

4. **Adaptive Spacing**
   - Adjusts grid spacing based on volatility
   - Wider grids in high volatility = safer

⚠️ **Important**: Leverage amplifies both gains AND losses. Start with low leverage (2-3x) in paper trading.

---

## 📚 How It Works

### Grid Strategy Flow

```
1. Market Price: $200
2. Create grid levels: $196, $192, $188, $184, $180, $176, $172
3. Price rises to $196 → OPEN SHORT (sell high)
4. Price drops to $192 → CLOSE SHORT (buy low, take profit)
5. Repeat for each grid level
```

### SHORT Position Example

```
Entry: $196 (sell)
Exit:  $192 (buy)
Profit: $4 per SOL
With 8x leverage: $32 profit on $196 collateral
ROI: 16.3% per trade
```

**Why SHORT?**
- Grid bots profit from volatility
- In declining markets, SHORT positions capture downward moves
- Each bounce = profit opportunity

---

## 🧪 Development Status

**Current Version**: v0.1.0 (Experimental)

**Tested On**:
- SOL/USD historical data (2021-2022)
- 1000+ parameter combinations
- Paper trading with virtual exchange

**Known Limitations**:
- No live exchange integration yet (paper trading only)
- Optimized for declining/sideways markets
- Requires manual parameter tuning per market

**Roadmap**:
- [ ] Live exchange connectors (Binance, Bitget)
- [ ] Dynamic parameter adjustment
- [ ] Multi-asset support
- [ ] Web dashboard for monitoring
- [ ] Telegram alerts

---

## 📋 Requirements

```txt
pandas>=2.0.0
numpy>=1.24.0
pyyaml>=6.0
matplotlib>=3.7.0
tqdm>=4.65.0
yfinance>=0.2.0  # For data download
```

**Python**: 3.11 or higher

---

## 🤝 Contributing

This is an educational project. Contributions welcome:

1. Fork the repo
2. Create feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -m "Add my feature"`
4. Push: `git push origin feature/my-feature`
5. Open Pull Request

---

## ⚠️ Disclaimer

**THIS SOFTWARE IS FOR EDUCATIONAL PURPOSES ONLY.**

- **NOT FINANCIAL ADVICE**: Do not use real money without thorough testing.
- **HIGH RISK**: Cryptocurrency trading and leverage are extremely risky.
- **NO GUARANTEES**: Past performance does not indicate future results.
- **YOUR RESPONSIBILITY**: You are solely responsible for your trading decisions.

**The authors are not responsible for any financial losses.**

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

---

## 🙏 Acknowledgments

Inspired by:
- MiniTorch (Sasha Rush) - Educational ML frameworks
- TinyGrad (George Hotz) - Performance-focused design
- Grid trading strategies from traditional finance

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/YOUR_USERNAME/sol-grid-bot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/YOUR_USERNAME/sol-grid-bot/discussions)

---

**Built with ❤️ for the SOL community.**