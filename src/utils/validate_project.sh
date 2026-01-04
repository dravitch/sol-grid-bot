#!/usr/bin/env bash
set -e

echo "=================================================================="
echo "🔍 SOL GRID BOT - PROJECT VALIDATION"
echo "=================================================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0

# 1. Check Python version
echo "📌 Checking Python version..."
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
    echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION (OK)"
else
    echo -e "${RED}✗${NC} Python $PYTHON_VERSION (Need 3.11+)"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# 2. Check dependencies
echo "📌 Checking dependencies..."
REQUIRED_PACKAGES="pandas numpy pyyaml matplotlib tqdm"

for package in $REQUIRED_PACKAGES; do
    if python -c "import $package" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $package installed"
    else
        echo -e "${RED}✗${NC} $package missing"
        ERRORS=$((ERRORS + 1))
    fi
done
echo ""

# 3. Check file structure
echo "📌 Checking file structure..."
REQUIRED_FILES=(
    "src/core/grid_bot.py"
    "src/config/config_loader.py"
    "scripts/backtest.py"
    "scripts/optimize.py"
    "scripts/paper_trade.py"
    "config/default.yaml"
    "scripts/exchange_simulator.py"
    "README.md"
    "requirements.txt"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file"
    else
        echo -e "${RED}✗${NC} $file missing"
        ERRORS=$((ERRORS + 1))
    fi
done
echo ""

# 4. Check configs
echo "📌 Checking YAML configs..."
CONFIGS=(
    "config/default.yaml"
    "config/conservative.yaml"
    "config/aggressive.yaml"
    "config/optimized.yaml"
)

for config in "${CONFIGS[@]}"; do
    if [ -f "$config" ]; then
        if python -c "import yaml; yaml.safe_load(open('$config'))" 2>/dev/null; then
            echo -e "${GREEN}✓${NC} $config (valid YAML)"
        else
            echo -e "${RED}✗${NC} $config (invalid YAML)"
            ERRORS=$((ERRORS + 1))
        fi
    else
        echo -e "${YELLOW}⚠${NC} $config (optional, not found)"
    fi
done
echo ""

# 5. Check data
echo "📌 Checking data files..."
if [ -f "data/SOL_2021_2022.csv" ]; then
    LINES=$(wc -l < data/SOL_2021_2022.csv)
    if [ "$LINES" -gt 100 ]; then
        echo -e "${GREEN}✓${NC} data/SOL_2021_2022.csv ($LINES lines)"
    else
        echo -e "${RED}✗${NC} data/SOL_2021_2022.csv (too small: $LINES lines)"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${YELLOW}⚠${NC} data/SOL_2021_2022.csv (missing)"
    echo "   Run: python scripts/fetch_data.py"
fi
echo ""

# 6. Test imports
echo "📌 Testing imports..."
if python scripts/check_imports.py --dir . > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} All imports OK"
else
    echo -e "${YELLOW}⚠${NC} Some import issues detected"
    echo "   Run: python scripts/check_imports.py"
fi
echo ""

# 7. Quick functional tests
echo "📌 Running quick tests..."

# Test config loader
if python -c "from src.config.config_loader import load_config; load_config('config/default.yaml')" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Config loader works"
else
    echo -e "${RED}✗${NC} Config loader failed"
    ERRORS=$((ERRORS + 1))
fi

# Test exchange simulator
if python -c "from exchange_simulator import ExchangeSimulator; ExchangeSimulator(1000)" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Exchange simulator works"
else
    echo -e "${RED}✗${NC} Exchange simulator failed"
    ERRORS=$((ERRORS + 1))
fi

# Test grid bot
if python -c "from src.core.grid_bot import GridBotV3" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Grid bot imports OK"
else
    echo -e "${RED}✗${NC} Grid bot import failed"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Summary
echo "=================================================================="
echo "📊 VALIDATION SUMMARY"
echo "=================================================================="

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo ""
    echo "Ready to run:"
    echo "  python scripts/backtest.py --data data/SOL_2021_2022.csv"
    echo "  python scripts/optimize.py --data data/SOL_2021_2022.csv"
    echo "  python scripts/paper_trade.py --config config/default.yaml"
    exit 0
else
    echo -e "${RED}❌ Found $ERRORS error(s)${NC}"
    echo ""
    echo "Fix errors and run again: ./scripts/validate_project.sh"
    exit 1
fi