"""
Risk Manager - Production Ready
Gestion liquidation, stops, et limites exposition
"""

import logging
from typing import Dict, Optional


class RiskManager:
    """Gestionnaire risque avec calculs liquidation précis"""

    def __init__(self, config: dict):
        self.maintenance_margin = config.get("maintenance_margin", 0.08)
        self.safety_buffer = config.get("safety_buffer", 1.3)
        self.max_drawdown = config.get("max_drawdown", 0.15)
        self.emergency_stop = config.get("emergency_stop_loss", 0.02)

        self.peak_value = None

    def calculate_liquidation_price(
        self, entry_price: float, leverage: float, is_short: bool = True
    ) -> float:
        """
        Calcule prix liquidation pour position short

        Formula short: liq = entry * (1 + leverage * margin * buffer)
        """
        if is_short:
            liq = entry_price * (
                1 + (leverage * self.maintenance_margin * self.safety_buffer)
            )
        else:
            liq = entry_price * (
                1 - (leverage * self.maintenance_margin * self.safety_buffer)
            )

        return liq

    def validate_order(
        self, portfolio_value: float, current_price: float, size: float, leverage: float
    ) -> bool:
        """
        Valide qu'un ordre est safe

        Returns:
            True si ordre OK
        """
        # Valeur position
        position_value = size * current_price * leverage

        # Check exposition totale
        if position_value > portfolio_value * 0.8:
            logging.warning("Position too large vs portfolio")
            return False

        # Check liquidation price safe
        liq_price = self.calculate_liquidation_price(
            current_price, leverage, is_short=True
        )

        # Doit avoir au moins 40% de marge (plus strict)
        margin = (liq_price - current_price) / current_price
        if margin < 0.40:
            logging.debug(f"Liquidation too close: {margin:.1%} (need >40%)")
            return False

        return True

    def check_drawdown(self, current_value: float, initial_value: float) -> Dict:
        """
        Vérifie drawdown actuel

        Returns:
            {status, drawdown, should_stop}
        """
        # Update peak
        if self.peak_value is None or current_value > self.peak_value:
            self.peak_value = current_value

        # Calcul drawdown
        drawdown = (self.peak_value - current_value) / self.peak_value

        status = "ok"
        should_stop = False

        if drawdown > self.max_drawdown:
            status = "critical"
            should_stop = True
            logging.error(f"Max drawdown exceeded: {drawdown:.1%}")
        elif drawdown > self.max_drawdown * 0.7:
            status = "warning"
            logging.warning(f"High drawdown: {drawdown:.1%}")

        return {"status": status, "drawdown": drawdown, "should_stop": should_stop}

    def check_position_risk(self, position: Dict, current_price: float) -> Dict:
        """
        Évalue risque position individuelle

        Returns:
            {status, distance_to_liq, should_close}
        """
        liq_price = position["liquidation_price"]

        # Distance à liquidation
        if position["size"] < 0:  # Short
            distance = (liq_price - current_price) / current_price
        else:  # Long
            distance = (current_price - liq_price) / current_price

        status = "safe"
        should_close = False

        if distance < 0.10:  # Moins de 10%
            status = "critical"
            should_close = True
        elif distance < 0.20:  # Moins de 20%
            status = "warning"

        return {
            "status": status,
            "distance_to_liquidation": distance,
            "should_close": should_close,
        }
