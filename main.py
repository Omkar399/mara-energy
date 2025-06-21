from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
import httpx
import asyncio
import json
import os
from datetime import datetime, timedelta
import pytz
import random
from dataclasses import dataclass
from anthropic import Anthropic
import math
import time
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# Load environment variables
load_dotenv("config.env")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    asyncio.create_task(periodic_price_update())
    yield
    # Shutdown (if needed)

app = FastAPI(title="SLA-Smart Energy Arbitrage Platform", version="1.0.0", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global configuration
MARA_API_BASE = "https://mara-hackathon-api.onrender.com"
MARA_API_KEY = None  # Will be set after site creation
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# Initialize Claude client if API key is available
claude_client = None
if CLAUDE_API_KEY and CLAUDE_API_KEY != "your_claude_api_key_here":
    claude_client = Anthropic(api_key=CLAUDE_API_KEY)

# Multi-site configuration
MULTI_SITE_CONFIG = {
    "site_1_nordic": {
        "name": "Nordic Iceland",
        "location": {"lat": 64.1466, "lon": -21.9426, "timezone": "Atlantic/Reykjavik"},
        "climate": {"avg_temp": 35, "cooling_efficiency": 0.95, "renewable_energy": 0.9},
        "hardware_profile": {"gpu_ratio": 0.6, "asic_ratio": 0.4, "cooling_type": "free_air"},
        "power_capacity": 1000000,
        "energy_cost_multiplier": 0.6
    },
    "site_2_canada": {
        "name": "Canada Vancouver",
        "location": {"lat": 49.2827, "lon": -123.1207, "timezone": "America/Vancouver"},
        "climate": {"avg_temp": 50, "cooling_efficiency": 0.85, "renewable_energy": 0.7},
        "hardware_profile": {"gpu_ratio": 0.7, "asic_ratio": 0.3, "cooling_type": "hydro_cooled"},
        "power_capacity": 1000000,
        "energy_cost_multiplier": 0.7
    },
    "site_3_norway": {
        "name": "Norway Oslo",
        "location": {"lat": 59.9139, "lon": 10.7522, "timezone": "Europe/Oslo"},
        "climate": {"avg_temp": 42, "cooling_efficiency": 0.9, "renewable_energy": 0.95},
        "hardware_profile": {"gpu_ratio": 0.8, "asic_ratio": 0.2, "cooling_type": "immersion"},
        "power_capacity": 1000000,
        "energy_cost_multiplier": 0.5
    },
    "site_4_singapore": {
        "name": "Singapore Tropical",
        "location": {"lat": 1.3521, "lon": 103.8198, "timezone": "Asia/Singapore"},
        "climate": {"avg_temp": 84, "cooling_efficiency": 0.4, "renewable_energy": 0.3},
        "hardware_profile": {"gpu_ratio": 0.3, "asic_ratio": 0.7, "cooling_type": "advanced_ac"},
        "power_capacity": 1000000,
        "energy_cost_multiplier": 1.4
    },
    "site_5_texas": {
        "name": "Texas USA",
        "location": {"lat": 32.7767, "lon": -96.7970, "timezone": "America/Chicago"},
        "climate": {"avg_temp": 75, "cooling_efficiency": 0.6, "renewable_energy": 0.4},
        "hardware_profile": {"gpu_ratio": 0.5, "asic_ratio": 0.5, "cooling_type": "air_cooled"},
        "power_capacity": 1000000,
        "energy_cost_multiplier": 0.8
    },
    "site_6_ireland": {
        "name": "Ireland Dublin",
        "location": {"lat": 53.3498, "lon": -6.2603, "timezone": "Europe/Dublin"},
        "climate": {"avg_temp": 52, "cooling_efficiency": 0.8, "renewable_energy": 0.6},
        "hardware_profile": {"gpu_ratio": 0.6, "asic_ratio": 0.4, "cooling_type": "free_air"},
        "power_capacity": 1000000,
        "energy_cost_multiplier": 0.9
    },
    "site_7_japan": {
        "name": "Japan Tokyo",
        "location": {"lat": 35.6762, "lon": 139.6503, "timezone": "Asia/Tokyo"},
        "climate": {"avg_temp": 68, "cooling_efficiency": 0.7, "renewable_energy": 0.2},
        "hardware_profile": {"gpu_ratio": 0.8, "asic_ratio": 0.2, "cooling_type": "precision_ac"},
        "power_capacity": 1000000,
        "energy_cost_multiplier": 1.2
    },
    "site_8_australia": {
        "name": "Australia Sydney",
        "location": {"lat": -33.8688, "lon": 151.2093, "timezone": "Australia/Sydney"},
        "climate": {"avg_temp": 72, "cooling_efficiency": 0.65, "renewable_energy": 0.5},
        "hardware_profile": {"gpu_ratio": 0.4, "asic_ratio": 0.6, "cooling_type": "evaporative"},
        "power_capacity": 1000000,
        "energy_cost_multiplier": 1.0
    },
    "site_9_chile": {
        "name": "Chile Santiago",
        "location": {"lat": -33.4489, "lon": -70.6693, "timezone": "America/Santiago"},
        "climate": {"avg_temp": 60, "cooling_efficiency": 0.75, "renewable_energy": 0.8},
        "hardware_profile": {"gpu_ratio": 0.5, "asic_ratio": 0.5, "cooling_type": "air_cooled"},
        "power_capacity": 1000000,
        "energy_cost_multiplier": 0.7
    },
    "site_10_germany": {
        "name": "Germany Berlin",
        "location": {"lat": 52.5200, "lon": 13.4050, "timezone": "Europe/Berlin"},
        "climate": {"avg_temp": 55, "cooling_efficiency": 0.8, "renewable_energy": 0.6},
        "hardware_profile": {"gpu_ratio": 0.7, "asic_ratio": 0.3, "cooling_type": "district_cooling"},
        "power_capacity": 1000000,
        "energy_cost_multiplier": 1.1
    }
}

# SLA Tiers
SLA_TIERS = {
    "premium": {"uptime": 99.9, "price_multiplier": 3.5, "priority": 1},
    "standard": {"uptime": 95.0, "price_multiplier": 2.0, "priority": 2},
    "flexible": {"uptime": 90.0, "price_multiplier": 1.2, "priority": 3},
    "spot": {"uptime": 0.0, "price_multiplier": 0.4, "priority": 4}
}

# Global state
pricing_data = {}
is_initialized = False
site_hardware_inventory = {}  # Store distributed hardware inventory
global_state = {
    "mara_inventory": None,
    "current_prices": None,
    "site_allocations": {},
    "sla_commitments": {"premium": 0, "standard": 0, "flexible": 0, "spot": 0},
    "total_revenue": 0,
    "optimization_history": []
}

# Pydantic models
class SiteStatus(BaseModel):
    site_id: str
    name: str
    location: Dict
    current_temp: float
    local_time: str
    energy_price: float
    cooling_efficiency: float
    allocation: Dict
    revenue: float
    power_used: int
    sla_commitments: Dict

class GlobalOptimization(BaseModel):
    timestamp: str
    total_revenue: float
    climate_savings: float
    timezone_optimization: float
    sla_performance: Dict
    claude_reasoning: str

class SLARequest(BaseModel):
    tier: str
    power_requirement: int
    duration_hours: int

# Utility functions
def get_local_time(timezone_str: str) -> str:
    """Get current local time for a timezone"""
    tz = pytz.timezone(timezone_str)
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %Z")

def calculate_demand_multiplier(timezone_str: str) -> float:
    """Calculate demand multiplier based on business hours with dynamic variation"""
    tz = pytz.timezone(timezone_str)
    local_hour = datetime.now(tz).hour
    
    # Base demand multiplier
    if 9 <= local_hour <= 18:
        base_multiplier = 1.5  # Peak business hours
    elif 6 <= local_hour <= 9 or 18 <= local_hour <= 22:
        base_multiplier = 1.2  # Moderate hours
    else:
        base_multiplier = 0.8  # Off hours
    
    # Add dynamic variation based on time
    dynamic_factor = math.sin(time.time() / 50) * 0.3  # Oscillating factor
    return max(0.5, base_multiplier + dynamic_factor)  # Ensure minimum 0.5x

def simulate_weather(climate_config: Dict) -> Dict:
    """Simulate current temperature with more dramatic randomness for demo purposes"""
    base_temp = climate_config.get("avg_temp", 70)  # Default to 70F if not found
    # Add more dramatic randomness (-20 to +20 degrees) and time-based variation
    time_factor = math.sin(time.time() / 100) * 10  # Slow oscillation
    random_factor = random.uniform(-20, 20)
    current_temp = base_temp + time_factor + random_factor
    
    return {
        "temperature": current_temp,
        "base_temp": base_temp,
        "conditions": "simulated"
    }

async def get_mara_prices():
    """Fetch current prices from MARA API"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{MARA_API_BASE}/prices")
            if response.status_code == 200:
                prices = response.json()
                return prices[0] if prices else None
        except Exception as e:
            print(f"Error fetching MARA prices: {e}")
            # Return mock data if API fails
            return {
                "energy_price": 0.65,
                "hash_price": 8.5,
                "token_price": 2.9,
                "timestamp": datetime.now().isoformat()
            }

async def get_mara_inventory():
    """Fetch inventory from MARA API"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{MARA_API_BASE}/inventory")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error fetching MARA inventory: {e}")
            # Return mock data if API fails
            return {
                "inference": {
                    "asic": {"power": 15000, "tokens": 50000},
                    "gpu": {"power": 5000, "tokens": 1000}
                },
                "miners": {
                    "air": {"hashrate": 1000, "power": 3500},
                    "hydro": {"hashrate": 5000, "power": 5000},
                    "immersion": {"hashrate": 10000, "power": 10000}
                }
            }

def calculate_site_revenue(site_id: str, allocation: Dict, prices: Dict, site_config: Dict) -> float:
    """Calculate revenue for a specific site allocation"""
    if not global_state["mara_inventory"]:
        return 0
    
    inventory = global_state["mara_inventory"]
    total_revenue = 0
    
    # AI Inference revenue
    gpu_revenue = (allocation.get("gpu_compute", 0) * 
                  inventory["inference"]["gpu"]["tokens"] * 
                  prices["token_price"] * 
                  site_config["climate"]["cooling_efficiency"])
    
    asic_inference_revenue = (allocation.get("asic_compute", 0) * 
                             inventory["inference"]["asic"]["tokens"] * 
                             prices["token_price"] * 
                             site_config["climate"]["cooling_efficiency"])
    
    # Bitcoin mining revenue
    mining_revenue = 0
    for miner_type in ["air_miners", "hydro_miners", "immersion_miners"]:
        if miner_type in allocation:
            miner_key = miner_type.replace("_miners", "")
            mining_revenue += (allocation[miner_type] * 
                             inventory["miners"][miner_key]["hashrate"] * 
                             prices["hash_price"])
    
    total_revenue = gpu_revenue + asic_inference_revenue + mining_revenue
    
    # Apply timezone demand multiplier
    demand_multiplier = calculate_demand_multiplier(site_config["location"]["timezone"])
    total_revenue *= demand_multiplier
    
    return total_revenue

async def claude_optimizer(site_data: Dict, sla_commitments: Dict) -> str:
    """Use Claude to optimize global allocation"""
    try:
        if not claude_client:
            return """
            MOCK CLAUDE OPTIMIZATION (No API Key Configured):
            
            SITE PERFORMANCE RANKING:
            1. Nordic Iceland: 95% cooling efficiency, lowest energy costs (0.6x multiplier)
            2. Norway Oslo: 90% cooling efficiency, cheapest renewable energy (0.5x multiplier)  
            3. Canada Vancouver: 85% cooling efficiency, good hydro cooling (0.7x multiplier)
            4. Germany Berlin: 80% cooling efficiency, balanced performance (1.1x multiplier)
            5. Ireland Dublin: 80% cooling efficiency, free air cooling (0.9x multiplier)
            6. Chile Santiago: 75% cooling efficiency, good renewable mix (0.7x multiplier)
            7. Japan Tokyo: 70% cooling efficiency, precision cooling (1.2x multiplier)
            8. Australia Sydney: 65% cooling efficiency, evaporative cooling (1.0x multiplier)
            9. Texas USA: 60% cooling efficiency, moderate costs (0.8x multiplier)
            10. Singapore: 40% cooling efficiency, high cooling costs (1.4x multiplier)
            
            OPTIMAL ALLOCATION STRATEGY:
            - Route Premium SLA to Nordic/Norway sites for maximum efficiency
            - Balance Standard SLA across cold climate sites (Iceland, Norway, Canada)
            - Use moderate sites (Germany, Ireland, Chile) for flexible workloads
            - Route mining operations to Singapore/Texas during optimal conditions
            
            CLIMATE ARBITRAGE: Cold sites save 35-55% on cooling costs
            TIMEZONE OPTIMIZATION: Following business hours increases revenue by 20-30%
            
            ⚠️  To enable real Claude AI optimization, add your Claude API key to config.env
            """
        
        # Prepare comprehensive site data for Claude
        site_summary = []
        for site_id, site in site_data.items():
            site_config = MULTI_SITE_CONFIG[site_id]
            site_summary.append(f"""
            {site.name}:
            - Temperature: {site.current_temp:.1f}°F
            - Cooling Efficiency: {site.cooling_efficiency:.1%}
            - Energy Cost Multiplier: {site_config['energy_cost_multiplier']}x
            - Renewable Energy: {site_config['climate']['renewable_energy']:.1%}
            - Local Time: {site.local_time}
            - Current Revenue: ${site.revenue:,.2f}
            - Power Used: {site.power_used:,} MW
            """)
        
        # Real Claude API call
        message = claude_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            temperature=0.3,
            messages=[{
                "role": "user",
                "content": f"""
                You are an AI optimization expert managing a global network of 10 data centers for energy arbitrage between Bitcoin mining and AI inference services.

                CURRENT GLOBAL SITUATION:
                {chr(10).join(site_summary)}

                SLA COMMITMENTS:
                - Premium (99.9% uptime): {sla_commitments.get('premium', 0)} MW
                - Standard (95% uptime): {sla_commitments.get('standard', 0)} MW  
                - Flexible (90% uptime): {sla_commitments.get('flexible', 0)} MW
                - Spot (best effort): {sla_commitments.get('spot', 0)} MW

                OPTIMIZATION OBJECTIVES:
                1. Maximize total revenue across all sites
                2. Route workloads to sites with best cooling efficiency
                3. Leverage timezone differences for AI inference demand
                4. Prioritize renewable energy sites for ESG compliance
                5. Maintain SLA commitments with geographic redundancy

                Provide a comprehensive optimization strategy with specific allocation recommendations for each site.
                """
            }]
        )
        
        return message.content[0].text if message.content else "Claude optimization completed but no response received"
        
    except Exception as e:
        return f"Claude optimization error: {e}. Using fallback strategy based on cooling efficiency and energy costs."

def distribute_hardware_across_sites(mara_inventory: Dict) -> Dict:
    """Distribute MARA's hardware inventory across 10 sites based on their profiles"""
    
    # Total hardware to distribute (realistic quantities)
    total_hardware = {
        "miners": {
            "air": 500,      # 500 air miners total
            "hydro": 200,    # 200 hydro miners total  
            "immersion": 100 # 100 immersion miners total
        },
        "inference": {
            "gpu": 1000,     # 1000 GPU units total
            "asic": 300      # 300 ASIC inference units total
        }
    }
    
    site_inventories = {}
    
    for site_id, site_config in MULTI_SITE_CONFIG.items():
        gpu_ratio = site_config["hardware_profile"]["gpu_ratio"]
        asic_ratio = site_config["hardware_profile"]["asic_ratio"]
        cooling_efficiency = site_config["climate"]["cooling_efficiency"]
        
        # Distribute hardware based on site profile
        site_inventories[site_id] = {
            "miners": {
                "air": {
                    "hashrate": mara_inventory["miners"]["air"]["hashrate"],
                    "power": mara_inventory["miners"]["air"]["power"],
                    "available": int(total_hardware["miners"]["air"] * 0.1)  # 10% per site
                },
                "hydro": {
                    "hashrate": mara_inventory["miners"]["hydro"]["hashrate"],
                    "power": mara_inventory["miners"]["hydro"]["power"],
                    "available": int(total_hardware["miners"]["hydro"] * cooling_efficiency * 0.1)
                },
                "immersion": {
                    "hashrate": mara_inventory["miners"]["immersion"]["hashrate"],
                    "power": mara_inventory["miners"]["immersion"]["power"],
                    "available": int(total_hardware["miners"]["immersion"] * cooling_efficiency * 0.1)
                }
            },
            "inference": {
                "gpu": {
                    "tokens": mara_inventory["inference"]["gpu"]["tokens"],
                    "power": mara_inventory["inference"]["gpu"]["power"],
                    "available": int(total_hardware["inference"]["gpu"] * gpu_ratio * 0.1)
                },
                "asic": {
                    "tokens": mara_inventory["inference"]["asic"]["tokens"],
                    "power": mara_inventory["inference"]["asic"]["power"],
                    "available": int(total_hardware["inference"]["asic"] * asic_ratio * 0.1)
                }
            },
            "site_specs": {
                "power_capacity": site_config["power_capacity"],
                "cooling_efficiency": cooling_efficiency,
                "hardware_profile": site_config["hardware_profile"]
            }
        }
    
    return site_inventories

# API Endpoints

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main dashboard"""
    return FileResponse("static/index.html")

@app.post("/api/initialize")
async def initialize_system():
    global pricing_data, is_initialized, site_hardware_inventory
    
    try:
        # Fetch MARA pricing data (use /prices not /pricing)
        pricing_response = httpx.get("https://mara-hackathon-api.onrender.com/prices")
        pricing_response.raise_for_status()
        pricing_data_list = pricing_response.json()
        # Get the latest pricing data (first item in the list)
        pricing_data = pricing_data_list[0] if pricing_data_list else {}
        
        # Fetch MARA hardware inventory
        inventory_response = httpx.get("https://mara-hackathon-api.onrender.com/inventory")
        inventory_response.raise_for_status()
        mara_inventory = inventory_response.json()
        
        # Update global_state for optimize function
        global_state["current_prices"] = pricing_data
        global_state["mara_inventory"] = mara_inventory
        
        # Distribute hardware across sites
        site_hardware_inventory = distribute_hardware_across_sites(mara_inventory)
        
        is_initialized = True
        return {
            "status": "success", 
            "message": "System initialized with MARA pricing and distributed hardware inventory",
            "pricing_data": pricing_data,
            "mara_inventory": mara_inventory,
            "total_sites": len(site_hardware_inventory),
            "sample_site_inventory": list(site_hardware_inventory.keys())[:3]
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to initialize: {str(e)}"}

@app.get("/api/sites/status")
async def get_sites_status():
    """Get status of all sites including distributed hardware inventory"""
    global site_hardware_inventory, pricing_data, is_initialized
    
    if not is_initialized:
        return {"error": "System not initialized. Call /api/initialize first"}
    
    sites = []
    
    for site_id, site_config in MULTI_SITE_CONFIG.items():
        # Get site-specific hardware inventory
        site_inventory = site_hardware_inventory.get(site_id, {})
        
        # Simulate current usage (random allocation for demo)
        current_allocation = {
            "gpu_compute": random.randint(20, min(80, site_inventory.get("inference", {}).get("gpu", {}).get("available", 100))),
            "asic_compute": random.randint(5, min(30, site_inventory.get("inference", {}).get("asic", {}).get("available", 50))),
            "air_miners": random.randint(10, min(40, site_inventory.get("miners", {}).get("air", {}).get("available", 50))),
            "hydro_miners": random.randint(5, min(20, site_inventory.get("miners", {}).get("hydro", {}).get("available", 20))),
            "immersion_miners": random.randint(2, min(15, site_inventory.get("miners", {}).get("immersion", {}).get("available", 10)))
        }
        
        # Calculate power usage based on actual hardware
        power_used = 0
        if site_inventory:
            power_used += current_allocation["gpu_compute"] * site_inventory["inference"]["gpu"]["power"]
            power_used += current_allocation["asic_compute"] * site_inventory["inference"]["asic"]["power"]
            power_used += current_allocation["air_miners"] * site_inventory["miners"]["air"]["power"]
            power_used += current_allocation["hydro_miners"] * site_inventory["miners"]["hydro"]["power"]
            power_used += current_allocation["immersion_miners"] * site_inventory["miners"]["immersion"]["power"]
        
        # Weather simulation
        weather = simulate_weather(site_config["climate"])
        
        # Calculate site-specific pricing using MARA data
        site_pricing = {}
        if pricing_data:
            energy_multiplier = site_config["energy_cost_multiplier"]
            site_pricing = {
                "hash_price": pricing_data.get("hash_price", 1.0) * energy_multiplier,
                "token_price": pricing_data.get("token_price", 1.0) * energy_multiplier,
                "energy_price": pricing_data.get("energy_price", 1.0) * energy_multiplier
            }
        
        # Calculate revenue based on current allocation and pricing
        revenue = 0
        if site_pricing and current_allocation:
            # AI inference revenue
            gpu_revenue = (current_allocation.get("gpu_compute", 0) * 
                          site_inventory.get("inference", {}).get("gpu", {}).get("tokens", 1000) * 
                          site_pricing.get("token_price", 1.0) * 0.001)  # Scale down for realistic numbers
            
            asic_revenue = (current_allocation.get("asic_compute", 0) * 
                           site_inventory.get("inference", {}).get("asic", {}).get("tokens", 50000) * 
                           site_pricing.get("token_price", 1.0) * 0.001)
            
            # Mining revenue
            mining_revenue = (
                (current_allocation.get("air_miners", 0) * site_inventory.get("miners", {}).get("air", {}).get("hashrate", 1000) * site_pricing.get("hash_price", 8.5) * 0.001) +
                (current_allocation.get("hydro_miners", 0) * site_inventory.get("miners", {}).get("hydro", {}).get("hashrate", 5000) * site_pricing.get("hash_price", 8.5) * 0.001) +
                (current_allocation.get("immersion_miners", 0) * site_inventory.get("miners", {}).get("immersion", {}).get("hashrate", 10000) * site_pricing.get("hash_price", 8.5) * 0.001)
            )
            
            revenue = gpu_revenue + asic_revenue + mining_revenue
            
            # Apply timezone demand multiplier
            demand_multiplier = calculate_demand_multiplier(site_config["location"]["timezone"])
            revenue *= demand_multiplier
        
        site_status = {
            "site_id": site_id,  # Use site_id consistently
            "id": site_id,
            "name": site_config["name"],
            "location": site_config["location"],
            "timezone": site_config["location"]["timezone"],
            
            # Hardware inventory (actual available hardware)
            "hardware_inventory": site_inventory,
            
            # Current allocation
            "allocation": current_allocation,
            
            # Power and capacity
            "power_used": power_used,
            "power_capacity": site_config["power_capacity"],
            "power_utilization": min(100, (power_used / site_config["power_capacity"]) * 100),
            
            # Environmental
            "weather": weather,
            "cooling_efficiency": site_config["climate"]["cooling_efficiency"],
            
            # Economics
            "pricing": site_pricing,
            "energy_cost_multiplier": site_config["energy_cost_multiplier"],
            "revenue": revenue,  # Add revenue field
            
            # Performance metrics
            "uptime": random.uniform(98.5, 99.9),
            "efficiency_score": calculate_efficiency_score(site_config, weather),
            
            "last_updated": datetime.now().isoformat()
        }
        
        sites.append(site_status)
    
    return {
        "sites": sites,
        "total_sites": len(sites),
        "global_metrics": calculate_global_metrics(sites),
        "mara_pricing_source": "live" if pricing_data else "mock",
        "last_updated": datetime.now().isoformat()
    }

@app.post("/api/optimize")
async def optimize_global_allocation():
    """Run global optimization across all sites"""
    # Check if system is initialized - handle both None and empty dict cases
    if (not global_state.get("current_prices") or 
        not global_state.get("mara_inventory") or 
        not is_initialized):
        raise HTTPException(status_code=400, detail="System not initialized")
    
    # Get current site data
    sites_response = await get_sites_status()
    
    # Handle case where sites_response has an error
    if "error" in sites_response:
        raise HTTPException(status_code=400, detail=sites_response["error"])
    
    site_data = {site["site_id"]: site for site in sites_response["sites"]}
    
    # Run Claude optimization
    claude_reasoning = await claude_optimizer(site_data, global_state["sla_commitments"])
    
    # Implement basic optimization logic
    total_revenue = 0
    climate_savings = 0
    
    # Simple optimization: allocate more resources to efficient sites
    for site_id, site_config in MULTI_SITE_CONFIG.items():
        cooling_efficiency = site_config["climate"]["cooling_efficiency"]
        energy_multiplier = site_config["energy_cost_multiplier"]
        
        # Allocate more GPU compute to efficient sites
        gpu_allocation = int(50 * cooling_efficiency / energy_multiplier)
        asic_allocation = int(30 * (1 - cooling_efficiency))  # ASIC mining for less efficient sites
        
        # Store allocation
        global_state["site_allocations"][site_id] = {
            "gpu_compute": gpu_allocation,
            "asic_compute": asic_allocation,
            "immersion_miners": 10 if cooling_efficiency > 0.7 else 5
        }
        
        # Calculate revenue
        site_revenue = calculate_site_revenue(
            site_id, 
            global_state["site_allocations"][site_id], 
            global_state["current_prices"], 
            site_config
        )
        total_revenue += site_revenue
        
        # Calculate climate savings (higher efficiency = more savings)
        if cooling_efficiency > 0.8:
            climate_savings += site_revenue * 0.3  # 30% savings for high efficiency
    
    # Create optimization result
    optimization = GlobalOptimization(
        timestamp=datetime.now().isoformat(),
        total_revenue=total_revenue,
        climate_savings=climate_savings,
        timezone_optimization=total_revenue * 0.15,  # 15% from timezone optimization
        sla_performance={"premium": 99.9, "standard": 96.2, "flexible": 91.5, "spot": 85.0},
        claude_reasoning=claude_reasoning
    )
    
    # Store in history
    global_state["optimization_history"].append(optimization)
    global_state["total_revenue"] = total_revenue
    
    return optimization

@app.post("/api/sla/request")
async def request_sla(sla_request: SLARequest):
    """Request SLA allocation"""
    if sla_request.tier not in SLA_TIERS:
        raise HTTPException(status_code=400, detail="Invalid SLA tier")
    
    # Update SLA commitments
    global_state["sla_commitments"][sla_request.tier] += sla_request.power_requirement
    
    # Find optimal site for this SLA tier
    optimal_site = None
    best_score = 0
    
    for site_id, site_config in MULTI_SITE_CONFIG.items():
        # Score based on cooling efficiency and energy cost
        score = (site_config["climate"]["cooling_efficiency"] * 0.7 + 
                (1 - site_config["energy_cost_multiplier"]) * 0.3)
        
        if score > best_score:
            best_score = score
            optimal_site = site_id
    
    return {
        "sla_tier": sla_request.tier,
        "power_allocated": sla_request.power_requirement,
        "optimal_site": optimal_site,
        "estimated_uptime": SLA_TIERS[sla_request.tier]["uptime"],
        "price_multiplier": SLA_TIERS[sla_request.tier]["price_multiplier"]
    }

@app.get("/api/dashboard/metrics")
async def get_dashboard_metrics():
    """Get comprehensive dashboard metrics"""
    # Update current prices
    global_state["current_prices"] = await get_mara_prices()
    
    # Get sites status
    sites_response = await get_sites_status()
    
    # Handle case where sites_response might be an error or not have expected structure
    if "error" in sites_response or "sites" not in sites_response:
        return {
            "error": "System not initialized or sites data unavailable",
            "sites_response": sites_response
        }
    
    sites = sites_response["sites"]
    
    # Calculate revenue for each site if not present
    for site in sites:
        if "revenue" not in site:
            # Calculate revenue based on power usage and efficiency
            base_revenue = site.get("power_used", 0) * 0.1  # $0.1 per MW base rate
            efficiency_multiplier = site.get("cooling_efficiency", 1.0)
            site["revenue"] = base_revenue * efficiency_multiplier
        
        # Ensure required fields exist with defaults
        site.setdefault("site_id", site.get("id", "unknown"))
        site.setdefault("cooling_efficiency", 0.8)
        site.setdefault("power_used", 0)
    
    # Calculate global metrics with safe access
    total_power_used = sum(site.get("power_used", 0) for site in sites)
    total_revenue = sum(site.get("revenue", 0) for site in sites)
    
    # Calculate efficiency metrics with safe access
    cooling_efficiencies = [site.get("cooling_efficiency", 0.8) for site in sites]
    avg_cooling_efficiency = sum(cooling_efficiencies) / len(cooling_efficiencies) if cooling_efficiencies else 0.8
    
    # Calculate renewable energy usage safely
    renewable_energy_usage = 0
    if total_power_used > 0:
        renewable_energy_usage = sum(
            MULTI_SITE_CONFIG.get(site.get("site_id", site.get("id", "")), {}).get("climate", {}).get("renewable_energy", 0.5) * site.get("power_used", 0)
            for site in sites
        ) / total_power_used
    
    return {
        "global_metrics": {
            "total_revenue": total_revenue,
            "total_power_used": total_power_used,
            "avg_cooling_efficiency": avg_cooling_efficiency,
            "renewable_energy_usage": renewable_energy_usage,
            "active_sites": len(sites)
        },
        "sites": sites,
        "sla_commitments": global_state["sla_commitments"],
        "optimization_history": global_state["optimization_history"][-10:],  # Last 10 optimizations
        "current_prices": global_state["current_prices"]
    }

@app.get("/api/debug/state")
async def debug_global_state():
    """Debug endpoint to check global state"""
    return {
        "is_initialized": is_initialized,
        "has_current_prices": bool(global_state.get("current_prices")),
        "current_prices_value": global_state.get("current_prices"),
        "has_mara_inventory": bool(global_state.get("mara_inventory")),
        "mara_inventory_keys": list(global_state.get("mara_inventory", {}).keys()) if isinstance(global_state.get("mara_inventory"), dict) else None,
        "global_state_keys": list(global_state.keys())
    }

@app.get("/api/hardware/inventory")
async def get_hardware_inventory():
    """Get detailed hardware inventory across all sites"""
    global site_hardware_inventory, is_initialized
    
    if not is_initialized:
        return {"error": "System not initialized. Call /api/initialize first"}
    
    inventory_summary = {
        "total_inventory": {
            "miners": {"air": 0, "hydro": 0, "immersion": 0},
            "inference": {"gpu": 0, "asic": 0}
        },
        "site_breakdown": {},
        "hardware_specs": {}
    }
    
    for site_id, inventory in site_hardware_inventory.items():
        site_name = MULTI_SITE_CONFIG[site_id]["name"]
        
        # Add to site breakdown
        inventory_summary["site_breakdown"][site_name] = {
            "site_id": site_id,
            "location": MULTI_SITE_CONFIG[site_id]["location"],
            "hardware": {
                "miners": {
                    "air": inventory["miners"]["air"]["available"],
                    "hydro": inventory["miners"]["hydro"]["available"], 
                    "immersion": inventory["miners"]["immersion"]["available"]
                },
                "inference": {
                    "gpu": inventory["inference"]["gpu"]["available"],
                    "asic": inventory["inference"]["asic"]["available"]
                }
            },
            "power_capacity": inventory["site_specs"]["power_capacity"],
            "cooling_efficiency": inventory["site_specs"]["cooling_efficiency"]
        }
        
        # Add to totals
        inventory_summary["total_inventory"]["miners"]["air"] += inventory["miners"]["air"]["available"]
        inventory_summary["total_inventory"]["miners"]["hydro"] += inventory["miners"]["hydro"]["available"]
        inventory_summary["total_inventory"]["miners"]["immersion"] += inventory["miners"]["immersion"]["available"]
        inventory_summary["total_inventory"]["inference"]["gpu"] += inventory["inference"]["gpu"]["available"]
        inventory_summary["total_inventory"]["inference"]["asic"] += inventory["inference"]["asic"]["available"]
        
        # Store hardware specs (same across all sites from MARA)
        if not inventory_summary["hardware_specs"]:
            inventory_summary["hardware_specs"] = {
                "miners": {
                    "air": {"hashrate": inventory["miners"]["air"]["hashrate"], "power": inventory["miners"]["air"]["power"]},
                    "hydro": {"hashrate": inventory["miners"]["hydro"]["hashrate"], "power": inventory["miners"]["hydro"]["power"]},
                    "immersion": {"hashrate": inventory["miners"]["immersion"]["hashrate"], "power": inventory["miners"]["immersion"]["power"]}
                },
                "inference": {
                    "gpu": {"tokens": inventory["inference"]["gpu"]["tokens"], "power": inventory["inference"]["gpu"]["power"]},
                    "asic": {"tokens": inventory["inference"]["asic"]["tokens"], "power": inventory["inference"]["asic"]["power"]}
                }
            }
    
    return {
        "inventory": inventory_summary,
        "data_source": "MARA API + Site Distribution",
        "last_updated": datetime.now().isoformat()
    }

# Background task to update prices every 5 minutes
async def periodic_price_update():
    """Update prices every 5 minutes"""
    while True:
        try:
            global_state["current_prices"] = await get_mara_prices()
            await asyncio.sleep(300)  # 5 minutes
        except Exception as e:
            print(f"Error in periodic price update: {e}")
            await asyncio.sleep(60)  # Retry in 1 minute on error

def calculate_efficiency_score(site_config: Dict, weather: Dict) -> float:
    """Calculate site efficiency score based on various factors"""
    base_score = 80.0
    
    # Temperature efficiency (cooler is better)
    temp_factor = max(0.5, 1.0 - (weather["temperature"] - 20) / 50)
    
    # Cooling efficiency factor
    cooling_factor = site_config["climate"]["cooling_efficiency"]
    
    # Energy cost factor (lower cost is better)
    energy_factor = max(0.3, 1.0 / site_config["energy_cost_multiplier"])
    
    return min(100.0, base_score * temp_factor * cooling_factor * energy_factor)

def calculate_global_metrics(sites: List[Dict]) -> Dict:
    """Calculate global metrics across all sites"""
    if not sites:
        return {}
    
    total_power_used = sum(site["power_used"] for site in sites)
    total_power_capacity = sum(site["power_capacity"] for site in sites)
    avg_efficiency = sum(site["efficiency_score"] for site in sites) / len(sites)
    avg_uptime = sum(site["uptime"] for site in sites) / len(sites)
    
    # Count total hardware across all sites
    total_hardware = {
        "gpu_units": sum(site["hardware_inventory"].get("inference", {}).get("gpu", {}).get("available", 0) for site in sites),
        "asic_units": sum(site["hardware_inventory"].get("inference", {}).get("asic", {}).get("available", 0) for site in sites),
        "air_miners": sum(site["hardware_inventory"].get("miners", {}).get("air", {}).get("available", 0) for site in sites),
        "hydro_miners": sum(site["hardware_inventory"].get("miners", {}).get("hydro", {}).get("available", 0) for site in sites),
        "immersion_miners": sum(site["hardware_inventory"].get("miners", {}).get("immersion", {}).get("available", 0) for site in sites)
    }
    
    return {
        "total_power_used": total_power_used,
        "total_power_capacity": total_power_capacity,
        "global_utilization": (total_power_used / total_power_capacity) * 100 if total_power_capacity > 0 else 0,
        "average_efficiency": avg_efficiency,
        "average_uptime": avg_uptime,
        "total_hardware": total_hardware,
        "active_sites": len(sites)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 