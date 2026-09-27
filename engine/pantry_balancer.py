"""
HarvestGrid: Community Pantry Vulnerability & Demand Balancer
Calculates dynamic deficit urgency scores based on poverty index, household reach, and current stock.
"""

from dataclasses import dataclass
from typing import Dict, List, Any

@dataclass
class PantryNode:
    pantry_id: str
    name: str
    latitude: float
    longitude: float
    weekly_served_households: int
    community_vulnerability_index: float  # 0.0 to 1.0 (CDC SVI / USDA Food Desert indicator)
    current_produce_stock_lbs: float
    target_capacity_lbs: float
    refrigeration_available: bool = True

class PantryBalancer:
    def __init__(self):
        self.pantries: Dict[str, PantryNode] = {}

    def register_pantry(self, pantry: PantryNode) -> None:
        self.pantries[pantry.pantry_id] = pantry

    def calculate_urgency_score(self, pantry_id: str) -> float:
        """
        Urgency = (Deficit Ratio * 0.5) + (Vulnerability Index * 0.3) + (Scale Factor * 0.2)
        Score normalized between 0.0 and 100.0.
        """
        p = self.pantries[pantry_id]
        deficit_lbs = max(0.0, p.target_capacity_lbs - p.current_produce_stock_lbs)
        deficit_ratio = deficit_lbs / max(p.target_capacity_lbs, 1.0)
        
        # Scale factor normalized to 1000 households
        scale_factor = min(1.0, p.weekly_served_households / 1000.0)
        
        raw_score = (deficit_ratio * 50.0) + (p.community_vulnerability_index * 30.0) + (scale_factor * 20.0)
        return round(min(100.0, max(0.0, raw_score)), 2)

    def get_prioritized_pantries(self) -> List[Dict[str, Any]]:
        """Returns pantries ranked by critical replenishment urgency."""
        results = []
        for p_id, p in self.pantries.items():
            urgency = self.calculate_urgency_score(p_id)
            deficit = max(0.0, p.target_capacity_lbs - p.current_produce_stock_lbs)
            results.append({
                "pantry_id": p.pantry_id,
                "name": p.name,
                "urgency_score": urgency,
                "deficit_lbs": deficit,
                "vulnerability_index": p.community_vulnerability_index,
                "refrigeration": p.refrigeration_available,
                "is_critical": urgency >= 65.0
            })
        return sorted(results, key=lambda x: x["urgency_score"], reverse=True)
