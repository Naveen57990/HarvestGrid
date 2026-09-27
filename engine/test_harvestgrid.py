"""
HarvestGrid Deterministic Test Suite
100% deterministic, zero network dependency, ultra-fast execution (<0.005s).
"""

import unittest
from harvestgrid.engine.decay_model import DecayModel
from harvestgrid.engine.pantry_balancer import PantryBalancer, PantryNode
from harvestgrid.engine.vrp_router import VRPRouter, DonorSurplus, RescueVehicle, haversine_distance_miles

class TestHarvestGrid(unittest.TestCase):
    def setUp(self):
        self.decay = DecayModel()
        self.balancer = PantryBalancer()
        
        # Seed Des Moines Area Pantries
        self.p1 = PantryNode("P1", "Des Moines North Pantry", 41.6005, -93.6091, weekly_served_households=850, community_vulnerability_index=0.85, current_produce_stock_lbs=120, target_capacity_lbs=800)
        self.p2 = PantryNode("P2", "East Side Community Food Center", 41.5868, -93.5700, weekly_served_households=520, community_vulnerability_index=0.72, current_produce_stock_lbs=300, target_capacity_lbs=600)
        self.p3 = PantryNode("P3", "West Des Moines Outreach", 41.5772, -93.7114, weekly_served_households=210, community_vulnerability_index=0.35, current_produce_stock_lbs=450, target_capacity_lbs=500)
        
        for p in [self.p1, self.p2, self.p3]:
            self.balancer.register_pantry(p)
            
        self.router = VRPRouter(self.decay, self.balancer)

    def test_01_arrhenius_baseline_decay(self):
        """Test decay rate at optimal refrigeration (4°C) is exactly 1.0."""
        rate = self.decay.calculate_decay_rate("leafy_greens", 4.0)
        self.assertEqual(rate, 1.0)
        
        res = self.decay.estimate_remaining_shelf_life("leafy_greens", 72.0, 4.0, transit_duration_hours=2.0)
        self.assertEqual(res["remaining_shelf_life_hours"], 70.0)
        self.assertEqual(res["spoilage_risk"], "LOW")

    def test_02_arrhenius_thermal_acceleration(self):
        """Test elevated temperature accelerates decay by Q10 power law."""
        # 24°C = 20°C above optimal (4°C) -> Q10^(20/10) = 2.8^2 = 7.84
        rate = self.decay.calculate_decay_rate("leafy_greens", 24.0)
        self.assertAlmostEqual(rate, 7.84, delta=0.01)
        
        res = self.decay.estimate_remaining_shelf_life("leafy_greens", 24.0, 24.0, transit_duration_hours=2.0)
        # 24.0 initial - (2.0 * 7.84) = 8.32 hours remaining
        self.assertAlmostEqual(res["remaining_shelf_life_hours"], 8.32, places=2)

    def test_03_critical_spoilage_threshold(self):
        """Test detection of critical threshold and pantry viability."""
        res = self.decay.estimate_remaining_shelf_life("berries", initial_hours_remaining=6.0, ambient_temp_c=25.0, transit_duration_hours=1.0)
        self.assertEqual(res["spoilage_risk"], "CRITICAL_IMMINENT_LOSS")

    def test_04_haversine_distance(self):
        """Test GPS distance calculation between Des Moines and Ames (approx 30-35 miles)."""
        # Des Moines (41.5868, -93.6250) to Ames (42.0308, -93.6319)
        dist = haversine_distance_miles(41.5868, -93.6250, 42.0308, -93.6319)
        self.assertGreaterEqual(dist, 28.0)
        self.assertLessEqual(dist, 35.0)

    def test_05_pantry_urgency_scoring(self):
        """Test that high-deficit, high-vulnerability pantries receive highest urgency score."""
        p1_score = self.balancer.calculate_urgency_score("P1")
        p3_score = self.balancer.calculate_urgency_score("P3")
        self.assertGreater(p1_score, p3_score)
        self.assertGreaterEqual(p1_score, 70.0)

    def test_06_pantry_prioritization_ranking(self):
        """Test pantry sorting puts most critical community node first."""
        prioritized = self.balancer.get_prioritized_pantries()
        self.assertEqual(prioritized[0]["pantry_id"], "P1")
        self.assertEqual(prioritized[-1]["pantry_id"], "P3")

    def test_07_vrp_dispatch_plan_execution(self):
        """Test complete vehicle routing and delivery plan."""
        donor = DonorSurplus("D1", "Central Iowa Berry Farm", 41.6500, -93.5500, "berries", quantity_lbs=400, initial_hours_remaining=18.0)
        vehicle = RescueVehicle("VAN_01", capacity_lbs=600, avg_speed_mph=35.0, has_active_refrigeration=False)
        
        plan = self.router.solve_dispatch_plan([donor], [vehicle], ambient_temp_c=22.0)
        self.assertEqual(len(plan["routes"]), 1)
        self.assertEqual(plan["summary"]["total_lbs_rescued"], 400.0)
        self.assertGreater(plan["summary"]["total_meals_provided"], 300)
        self.assertGreater(plan["summary"]["co2_emissions_avoided_kg"], 400.0)

    def test_08_refrigerated_vs_ambient_decay(self):
        """Test active refrigeration protects perishable cargo over long distance."""
        donor = DonorSurplus("D2", "Organic Greens Producer", 41.7000, -93.4000, "leafy_greens", quantity_lbs=500, initial_hours_remaining=12.0)
        v_ambient = RescueVehicle("VAN_A", capacity_lbs=500, has_active_refrigeration=False)
        v_reefer = RescueVehicle("VAN_B", capacity_lbs=500, has_active_refrigeration=True)
        
        plan_ambient = self.router.solve_dispatch_plan([donor], [v_ambient], ambient_temp_c=30.0)
        plan_reefer = self.router.solve_dispatch_plan([donor], [v_reefer], ambient_temp_c=30.0)
        
        ambient_last_stop = plan_ambient["routes"][0]["stops"][-1]
        reefer_last_stop = plan_reefer["routes"][0]["stops"][-1]
        
        self.assertGreater(reefer_last_stop["remaining_shelf_life_hours"], ambient_last_stop["remaining_shelf_life_hours"])

if __name__ == "__main__":
    unittest.main()
