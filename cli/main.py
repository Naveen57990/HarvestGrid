"""
HarvestGrid Tactical CLI: Perishable Food Rescue & Logistics Dispatcher
"""

import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from harvestgrid.engine.decay_model import DecayModel
from harvestgrid.engine.pantry_balancer import PantryBalancer, PantryNode
from harvestgrid.engine.vrp_router import VRPRouter, DonorSurplus, RescueVehicle

def print_banner():
    banner = """
\033[1;32m██╗  ██╗ █████╗ ██████╗ ██╗   ██╗███████╗███████╗████████╗ ██████╗ ██████╗ ██╗██████╗ 
██║  ██║██╔══██╗██╔══██╗██║   ██║██╔════╝██╔════╝╚══██╔══╝██╔════╝ ██╔══██╗██║██╔══██╗
███████║███████║██████╔╝██║   ██║█████╗  ███████╗   ██║   ██║  ███╗██████╔╝██║██║  ██║
██╔══██║██╔══██║██╔══██╗╚██╗ ██╔╝██╔══╝  ╚════██║   ██║   ██║   ██║██╔══██╗██║██║  ██║
██║  ██║██║  ██║██║  ██║ ╚████╔╝ ███████╗███████║   ██║   ╚██████╔╝██║  ██║██║██████╔╝
╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚══════╝╚══════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝╚═════╝ \033[0m
  \033[1;33m► Perishable Food Rescue Logistics & Cold-Chain Decay Engine\033[0m
  \033[90mArrhenius Shelf-Life Modeling • Community Pantry Balancer • 0.000s Core\033[0m
"""
    print(banner)

def run_dispatch_simulation(region: str = "des_moines"):
    print_banner()
    decay = DecayModel()
    balancer = PantryBalancer()

    print(f"\033[1;36m[+] Initializing Logistics Dispatch for Region: '{region.upper()}'\033[0m")
    
    if region == "des_moines":
        balancer.register_pantry(PantryNode("DSM_01", "Des Moines North Community Pantry", 41.6005, -93.6091, 850, 0.85, 120, 800))
        balancer.register_pantry(PantryNode("DSM_02", "East Side Food Rescue Hub", 41.5868, -93.5700, 520, 0.72, 300, 600))
        balancer.register_pantry(PantryNode("DSM_03", "Southridge Family Support Center", 41.5300, -93.5950, 410, 0.65, 200, 500))
        
        donors = [
            DonorSurplus("DONOR_A", "Capital City Farm Co-op", 41.6400, -93.5800, "berries", 450, 16.0),
            DonorSurplus("DONOR_B", "Prairie Greens Greenhouse", 41.6700, -93.6500, "leafy_greens", 600, 24.0)
        ]
        vehicles = [
            RescueVehicle("RESCUE_VAN_1", capacity_lbs=600, avg_speed_mph=35.0, has_active_refrigeration=False),
            RescueVehicle("REEFER_TRUCK_2", capacity_lbs=1200, avg_speed_mph=30.0, has_active_refrigeration=True)
        ]
    else:
        balancer.register_pantry(PantryNode("AMES_01", "Story County Relief Pantry", 42.0308, -93.6319, 650, 0.78, 150, 700))
        balancer.register_pantry(PantryNode("AMES_02", "Campus Community Food Shelf", 42.0250, -93.6450, 320, 0.55, 100, 400))
        
        donors = [
            DonorSurplus("DONOR_AG", "ISU Research Orchard", 42.0500, -93.6200, "orchard_fruits", 800, 48.0)
        ]
        vehicles = [
            RescueVehicle("AMES_VAN_1", capacity_lbs=800, avg_speed_mph=30.0, has_active_refrigeration=True)
        ]

    router = VRPRouter(decay, balancer)
    plan = router.solve_dispatch_plan(donors, vehicles, ambient_temp_c=26.0)

    print(f"\033[1;35m[*] Optimized {len(plan['routes'])} Rescue Routes across {len(balancer.pantries)} Community Pantries:\033[0m\n")

    for r_idx, r in enumerate(plan["routes"]):
        reefer_tag = "\033[1;36m[ACTIVE REEFER 4°C]\033[0m" if r["refrigerated"] else "\033[1;33m[AMBIENT 26°C]\033[0m"
        print(f"\033[1;34m--- [ROUTE {r_idx+1}: {r['vehicle_id']} {reefer_tag} | Cargo: {r['total_lbs_carried']} lbs | Est. Time: {r['route_duration_minutes']} min] ---\033[0m")
        for s_idx, stop in enumerate(r["stops"]):
            icon = "🚜 PICKUP" if stop["stop_type"] == "PICKUP" else "🏢 DELIVER"
            status_color = "\033[1;32m" if stop["spoilage_status"] in ["FRESH", "LOW"] else "\033[1;31m"
            print(f"  {s_idx+1}. {icon} \033[1;37m{stop['name']}\033[0m ({stop['lbs_transferred']} lbs of {stop['produce_category']})")
            print(f"     └─ ETA: +{stop['estimated_arrival_minutes']:.1f}m | Viability: {status_color}{stop['remaining_shelf_life_hours']:.1f}h remaining ({stop['spoilage_status']})\033[0m")
        print()

    s = plan["summary"]
    print("\033[1;32m========================================================\033[0m")
    print(f"\033[1;32m✔ Food Rescue Complete! Total Rescued: {s['total_lbs_rescued']} lbs ({s['total_meals_provided']} Meals)\033[0m")
    print(f"\033[1;32m✔ Environmental Impact: {s['co2_emissions_avoided_kg']} kg CO2e Emissions Avoided\033[0m")
    print("\033[1;32m========================================================\033[0m")

if __name__ == "__main__":
    reg = sys.argv[1] if len(sys.argv) > 1 else "des_moines"
    run_dispatch_simulation(reg)
