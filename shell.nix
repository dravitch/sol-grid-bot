{ pkgs ? import <nixpkgs> {} }:

let
  pythonEnv = pkgs.python312.withPackages (ps: with ps; [
    # Core scientific
    numpy
    pandas
    scipy
    matplotlib
    requests
    aiohttp
    pyyaml
    colorama
    python-dateutil
    pytz
    
    # Data acquisition
    requests
    beautifulsoup4
    lxml
    
    # Technical analysis
    # TA-Lib wrapper sera installé via pip (nécessite compilation)
    
    # Backtesting libraries disponibles dans nixpkgs
    # (la plupart nécessitent pip malheureusement)
  ]);
in
pkgs.mkShell {
  buildInputs = [
    pythonEnv
    pkgs.ta-lib           # Bibliothèque C TA-Lib
    pkgs.gcc              # Compilateur pour packages natifs
    pkgs.pkg-config       # Pour trouver les bibliothèques
    
    # Dépendances C pour compilation
    pkgs.stdenv.cc.cc.lib
    pkgs.zlib
    pkgs.openssl
    pkgs.libffi
  ];

  shellHook = ''
    echo "🔧 Initialisation de l'environnement Paper Trading..."

    # ===================================================================
    # 1. CONFIGURATION DES CHEMINS DE BIBLIOTHÈQUES C
    # ===================================================================
    export LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib}/lib:${pkgs.zlib}/lib:${pkgs.ta-lib}/lib:${pkgs.openssl.out}/lib:$LD_LIBRARY_PATH"
    export TA_LIBRARY_PATH=${pkgs.ta-lib}/lib
    export TA_INCLUDE_PATH=${pkgs.ta-lib}/include
    
    # PKG_CONFIG pour trouver les libs
    export PKG_CONFIG_PATH="${pkgs.openssl.dev}/lib/pkgconfig:${pkgs.zlib}/lib/pkgconfig:$PKG_CONFIG_PATH"

    # ===================================================================
    # 2. CRÉATION D'UN ENVIRONNEMENT VIRTUEL LOCAL (PIP)
    # ===================================================================
    VENV_DIR=".venv_papertrading"
    
    if [ ! -d "$VENV_DIR" ]; then
      echo "📦 Création de l'environnement virtuel Python..."
      python -m venv "$VENV_DIR"
    fi
    
    # Activer l'environnement virtuel
    source "$VENV_DIR/bin/activate"
    
    # Mettre à jour pip
    pip install --upgrade pip setuptools wheel --quiet

    # ===================================================================
    # 3. INSTALLATION DES PACKAGES PYTHON (PIP)
    # ===================================================================
    echo "📦 Installation des dépendances de backtesting..."
    
    # Packages essentiels pour data
    pip install --quiet yfinance requests-cache ccxt
    pip install --quiet requests aiohttp pyyaml colorama python-dateutil pytz seaborn

    
    # TA-Lib wrapper (nécessite compilation)
    pip install --quiet TA-Lib
    
    # Backtesting libraries
    echo "   • VectorBT..."
    pip install --quiet vectorbt
    
    echo "   • Backtesting.py..."
    pip install --quiet backtesting
    
    echo "   • Backtrader..."
    pip install --quiet backtrader
    
    # Librairies optionnelles mais utiles
    pip install --quiet jupyter ipython

    # ===================================================================
    # 4. VÉRIFICATIONS
    # ===================================================================
    echo ""
    echo "✅ Environnement PaperTrading prêt!"
    echo "🐍 Python: $(python --version)"
    echo ""
    echo "📊 Vérification des packages:"
    
    python -c "import numpy; print('   ✓ numpy:', numpy.__version__)" 2>/dev/null || echo "   ✗ numpy manquant"
    python -c "import pandas; print('   ✓ pandas:', pandas.__version__)" 2>/dev/null || echo "   ✗ pandas manquant"
    python -c "import talib; print('   ✓ TA-Lib:', talib.__version__)" 2>/dev/null || echo "   ✗ TA-Lib manquant"
    python -c "import yfinance; print('   ✓ yfinance:', yfinance.__version__)" 2>/dev/null || echo "   ✗ yfinance manquant"
    python -c "import vectorbt; print('   ✓ VectorBT:', vectorbt.__version__)" 2>/dev/null || echo "   ✗ VectorBT manquant"
    python -c "import backtesting; print('   ✓ Backtesting.py: OK')" 2>/dev/null || echo "   ✗ Backtesting.py manquant"
    python -c "import backtrader; print('   ✓ Backtrader:', backtrader.__version__)" 2>/dev/null || echo "   ✗ Backtrader manquant"
    python -c "import ccxt; print('   ✓ ccxt:', ccxt.__version__)" 2>/dev/null || echo "   ✗ ccxt manquant"
    python -c "import requests; print('   ✓ requests:', requests.__version__)" 2>/dev/null || echo "   ✗ requests manquant"
    python -c "import aiohttp; print('   ✓ aiohttp:', aiohttp.__version__)" 2>/dev/null || echo "   ✗ aiohttp manquant"
    python -c "import yaml; print('   ✓ PyYAML:', yaml.__version__)" 2>/dev/null || echo "   ✗ PyYAML manquant"
    python -c "import colorama; print('   ✓ colorama:', colorama.__version__)" 2>/dev/null || echo "   ✗ colorama manquant"
    python -c "import dateutil; print('   ✓ python-dateutil: OK')" 2>/dev/null || echo "   ✗ python-dateutil manquant"
    python -c "import pytz; print('   ✓ pytz:', pytz.__version__)" 2>/dev/null || echo "   ✗ pytz manquant"
    python -c "import seaborn; print('   ✓ seaborn:', seaborn.__version__)" 2>/dev/null || echo "   ✗ seaborn manquant"
    python -c "import xdg-open; print('   ✓ eog:', xdg-open.__version__)" 2>/dev/null || echo "   ✗ xdg-open manquant"
    

    echo ""
    echo -e "🚀 Lancez votre test avec:\n   python examples/quickstart.py\n   python examples/full_example.py"
    echo ""
    # Note pour l'utilisateur
    echo "💡 Note: L'environnement virtuel (.venv_papertrading) est automatiquement activé"
    echo "   Pour désactiver: deactivate"
    echo ""
  '';
  
  # Variables d'environnement permanentes
  PYTHON_KEYRING_BACKEND = "keyring.backends.null.Keyring";  # Évite les erreurs keyring
}
