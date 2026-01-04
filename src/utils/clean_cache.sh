#!/usr/bin/env bash
set -euo pipefail

echo "🧹 Nettoyage des fichiers cache Python…"

# Supprimer tous les dossiers __pycache__
find . -type d -name "__pycache__" -exec rm -rf {} +

# Supprimer tous les fichiers .pyc
find . -type f -name "*.pyc" -delete

echo "✨ Nettoyage terminé."
