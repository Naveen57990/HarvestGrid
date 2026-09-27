"""
HarvestGrid: Arrhenius Perishability & Cold-Chain Decay Model
Calculates shelf-life degradation kinetics and critical delivery time windows
based on ambient temperature exposure and commodity sensitivity tiers.
"""

from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class ProduceProfile:
    category: str
    baseline_shelf_life_hours: float  # at 4°C baseline
    q10_factor: float                 # temperature sensitivity coefficient
    optimal_temp_c: float = 4.0
    critical_threshold_hours: float = 4.0  # emergency dispatch trigger

PRODUCE_CATALOG: Dict[str, ProduceProfile] = {
    "leafy_greens": ProduceProfile("leafy_greens", baseline_shelf_life_hours=72.0, q10_factor=2.8, critical_threshold_hours=6.0),
    "berries": ProduceProfile("berries", baseline_shelf_life_hours=48.0, q10_factor=3.2, critical_threshold_hours=4.0),
    "dairy_prepared": ProduceProfile("dairy_prepared", baseline_shelf_life_hours=36.0, q10_factor=3.5, critical_threshold_hours=3.0),
    "orchard_fruits": ProduceProfile("orchard_fruits", baseline_shelf_life_hours=168.0, q10_factor=2.2, critical_threshold_hours=12.0),
    "root_vegetables": ProduceProfile("root_vegetables", baseline_shelf_life_hours=336.0, q10_factor=1.8, critical_threshold_hours=24.0),
}

class DecayModel:
    def __init__(self):
        self.catalog = PRODUCE_CATALOG

    def calculate_decay_rate(self, produce_category: str, ambient_temp_c: float) -> float:
        """
        Calculates Arrhenius acceleration factor relative to optimal 4°C baseline:
        k_factor = Q10 ** ((T - T_optimal) / 10)
        """
        profile = self.catalog.get(produce_category, self.catalog["leafy_greens"])
        temp_delta = ambient_temp_c - profile.optimal_temp_c
        if temp_delta <= 0:
            return 1.0  # optimal refrigeration preservation
        
        acceleration = profile.q10_factor ** (temp_delta / 10.0)
        return round(acceleration, 3)

    def estimate_remaining_shelf_life(
        self,
        produce_category: str,
        initial_hours_remaining: float,
        ambient_temp_c: float,
        transit_duration_hours: float
    ) -> Dict[str, Any]:
        """
        Calculates effective shelf-life loss during transit and predicts remaining viability.
        """
        profile = self.catalog.get(produce_category, self.catalog["leafy_greens"])
        decay_factor = self.calculate_decay_rate(produce_category, ambient_temp_c)
        
        # Effective hours consumed = transit duration * acceleration factor
        effective_hours_lost = transit_duration_hours * decay_factor
        remaining_hours = max(0.0, initial_hours_remaining - effective_hours_lost)
        
        spoilage_risk = "LOW"
        if remaining_hours <= profile.critical_threshold_hours:
            spoilage_risk = "CRITICAL_IMMINENT_LOSS"
        elif remaining_hours <= profile.critical_threshold_hours * 2.0:
            spoilage_risk = "ELEVATED"
            
        viability_pct = round((remaining_hours / max(profile.baseline_shelf_life_hours, 0.001)) * 100, 1)

        return {
            "produce_category": produce_category,
            "ambient_temp_c": ambient_temp_c,
            "decay_acceleration_factor": decay_factor,
            "transit_duration_hours": transit_duration_hours,
            "effective_hours_lost": round(effective_hours_lost, 2),
            "remaining_shelf_life_hours": round(remaining_hours, 2),
            "viability_pct": min(100.0, max(0.0, viability_pct)),
            "spoilage_risk": spoilage_risk,
            "is_viable_for_pantry": remaining_hours >= profile.critical_threshold_hours
        }
