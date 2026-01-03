"""
Grid Strategy - Production Ready
Short grid avec spacing adaptatif et gestion positions
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime


class GridStrategy:
    """Stratégie Grid Short avec niveaux adaptatifs"""

    def __init__(self, config: dict):
        self.grid_size = config.get("grid_size", 5)
        self.grid_ratio = config.get("grid_ratio", 0.03)
        self.max_positions = config.get("max_positions", 3)
        self.position_size = config.get("position_size", 0.15)

        self.grid_levels = []
        self.last_update_price = None

    def calculate_grid_levels(self, current_price: float) -> List[float]:
        """
        Calcule niveaux de grille en dessous du prix actuel

        Returns:
            Liste prix décroissants (plus haut niveau en premier)
        """
        levels = []
        level = current_price

        for i in range(self.grid_size):
            level = level * (1 - self.grid_ratio)
            levels.append(level)

        return sorted(levels, reverse=True)

    def should_update_grid(self, current_price: float) -> bool:
        """Vérifie si grille doit être recalculée"""
        if not self.grid_levels:
            return True

        # Recalcule si prix sort de la grille
        if current_price < min(self.grid_levels):
            return True

        # Recalcule si prix monte trop au-dessus
        if current_price > max(self.grid_levels) * 1.05:
            return True

        return False

    def check_signal(
        self, current_price: float, active_positions: int, portfolio_value: float
    ) -> Optional[Dict]:
        """
        Vérifie si signal d'entrée

        Returns:
            Dict avec {side, size, level} ou None
        """
        # Update grid si nécessaire
        if self.should_update_grid(current_price):
            self.grid_levels = self.calculate_grid_levels(current_price)
            self.last_update_price = current_price

        # Pas de nouveau trade si max atteint
        if active_positions >= self.max_positions:
            return None

        # Cherche niveau franchi
        for level in self.grid_levels:
            # Prix au-dessus du niveau = signal short
            if current_price >= level * 1.005:  # 0.5% buffer
                # Calcul taille position
                position_value = portfolio_value * self.position_size
                size = position_value / current_price

                return {
                    "side": "sell",
                    "size": size,
                    "level": level,
                    "price": current_price,
                }

        return None

    def should_close_position(
        self, position: Dict, current_price: float
    ) -> Tuple[bool, str]:
        """
        Vérifie si position doit être fermée

        Returns:
            (should_close, reason)
        """
        # Take profit si prix atteint niveau grid
        if current_price <= position["grid_level"]:
            return True, "take_profit"

        # Stop loss si prix monte trop
        if current_price >= position["entry_price"] * 1.15:
            return True, "stop_loss"

        return False, ""
