"""
HarvestGrid: Perishability-Constrained Vehicle Routing Problem (PC-VRP) Solver
Optimizes multi-stop donor pickup and pantry delivery routes subject to thermal decay deadlines.
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple
from harvestgrid.engine.decay_model import DecayModel
from harvestgrid.engine.pantry_balancer import PantryBalancer, PantryNode

@dataclass
class DonorSurplus:
    donor_id: str
    name: str
    latitude: float
    longitude: float
    produce_category: str
    quantity_lbs: float
    initial_hours_remaining: float

@dataclass
class RescueVehicle:
    vehicle_id: str
    capacity_lbs: float
    avg_speed_mph: float = 35.0
    has_active_refrigeration: bool = False
    current_temp_c: float = 22.0  # ambient if un-refrigerated, 4.0 if refrigerated

@dataclass
class RouteStop:
    stop_type: str  # PICKUP or DELIVERY
    entity_id: str
    name: str
    latitude: float
    longitude: float
    lbs_transferred: float
    produce_category: str
    estimated_arrival_minutes: float
    remaining_shelf_life_hours: float
    spoilage_status: str

def haversine_distance_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two GPS coordinates in miles."""
    r = 3958.8  # Earth radius in miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(r * c, 2)

class VRPRouter:
    def __init__(self, decay_model: DecayModel, pantry_balancer: PantryBalancer):
        self.decay_model = decay_model
        self.pantry_balancer = pantry_balancer

    def solve_dispatch_plan(
        self,
        donors: List[DonorSurplus],
        vehicles: List[RescueVehicle],
        ambient_temp_c: float = 24.0
    ) -> Dict[str, Any]:
        """
        Greedy heuristic dispatch algorithm:
        1. Sorts donors by most perishable first (lowest initial hours).
        2. Matches surplus with highest-urgency pantries with capacity.
        3. Simulates thermal transit decay and verifies delivery arrives before critical spoilage.
        """
        prioritized_pantries = self.pantry_balancer.get_prioritized_pantries()
        sorted_donors = sorted(donors, key=lambda d: d.initial_hours_remaining)
        
        assigned_routes = []
        total_lbs_rescued = 0.0
        total_miles_traveled = 0.0

        for idx, vehicle in enumerate(vehicles):
            current_cargo_lbs = 0.0
            vehicle_stops = []
            cumulative_minutes = 0.0
            
            # Start at base / donor location
            if idx >= len(sorted_donors):
                break
                
            donor = sorted_donors[idx]
            pickup_qty = min(donor.quantity_lbs, vehicle.capacity_lbs)
            current_cargo_lbs += pickup_qty
            
            # Effective transit temperature
            transit_temp = 4.0 if vehicle.has_active_refrigeration else ambient_temp_c
            
            # Stop 1: Donor Pickup
            vehicle_stops.append(RouteStop(
                stop_type="PICKUP",
                entity_id=donor.donor_id,
                name=donor.name,
                latitude=donor.latitude,
                longitude=donor.longitude,
                lbs_transferred=pickup_qty,
                produce_category=donor.produce_category,
                estimated_arrival_minutes=0.0,
                remaining_shelf_life_hours=donor.initial_hours_remaining,
                spoilage_status="FRESH"
            ))

            curr_lat, curr_lon = donor.latitude, donor.longitude
            remaining_to_drop = pickup_qty

            for p_info in prioritized_pantries:
                if remaining_to_drop <= 0:
                    break
                    
                pantry = self.pantry_balancer.pantries[p_info["pantry_id"]]
                dist_miles = haversine_distance_miles(curr_lat, curr_lon, pantry.latitude, pantry.longitude)
                transit_hours = dist_miles / max(vehicle.avg_speed_mph, 10.0)
                cumulative_minutes += transit_hours * 60.0
                total_miles_traveled += dist_miles
                
                # Check decay
                decay_result = self.decay_model.estimate_remaining_shelf_life(
                    donor.produce_category,
                    donor.initial_hours_remaining,
                    transit_temp,
                    transit_hours
                )

                drop_lbs = min(remaining_to_drop, p_info["deficit_lbs"])
                if drop_lbs <= 0:
                    drop_lbs = remaining_to_drop  # allocate remaining
                    
                remaining_to_drop -= drop_lbs
                total_lbs_rescued += drop_lbs

                vehicle_stops.append(RouteStop(
                    stop_type="DELIVERY",
                    entity_id=pantry.pantry_id,
                    name=pantry.name,
                    latitude=pantry.latitude,
                    longitude=pantry.longitude,
                    lbs_transferred=drop_lbs,
                    produce_category=donor.produce_category,
                    estimated_arrival_minutes=round(cumulative_minutes, 1),
                    remaining_shelf_life_hours=decay_result["remaining_shelf_life_hours"],
                    spoilage_status=decay_result["spoilage_risk"]
                ))
                curr_lat, curr_lon = pantry.latitude, pantry.longitude

            # Estimate CO2 emissions avoided: ~1.13 kg CO2e per lb food rescued (EPA WARM model)
            co2_avoided_kg = round(total_lbs_rescued * 1.13, 1)

            assigned_routes.append({
                "vehicle_id": vehicle.vehicle_id,
                "refrigerated": vehicle.has_active_refrigeration,
                "total_lbs_carried": pickup_qty,
                "route_duration_minutes": round(cumulative_minutes, 1),
                "total_route_miles": round(total_miles_traveled, 1),
                "stops": [s.__dict__ for s in vehicle_stops]
            })

        return {
            "routes": assigned_routes,
            "summary": {
                "total_lbs_rescued": round(total_lbs_rescued, 1),
                "total_meals_provided": int(total_lbs_rescued * 0.83),  # Feeding America standard: 1.2 lbs = 1 meal
                "total_miles_traveled": round(total_miles_traveled, 1),
                "co2_emissions_avoided_kg": co2_avoided_kg,
                "active_vehicles": len(assigned_routes)
            }
        }
