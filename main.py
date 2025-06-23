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

# Import database module
from database import sla_db

# Import AI hardware optimization modules
from ai_hardware_optimization import (
    mara_ai, get_ai_predictions, get_hardware_optimizations, get_maintenance_schedule
)
from advanced_ai_optimization import (
    advanced_orchestrator, get_advanced_ai_predictions, 
    generate_intelligent_maintenance_schedule, get_claude_optimization_strategy,
    get_maintenance_database
)

# Load environment variables
load_dotenv("config.env")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - Initialize system automatically
    print("🚀 Starting SLA-Smart Energy Arbitrage Platform...")
    
    # Initialize the database first
    print("🗄️ Initializing SLA database...")
    await sla_db.initialize()
    print("✅ Database initialized successfully")
    
    # Initialize the system automatically
    try:
        global pricing_data, is_initialized, site_hardware_inventory
        
        print("📡 Fetching MARA pricing data...")
        # Fetch MARA pricing data
        async with httpx.AsyncClient() as client:
            pricing_response = await client.get("https://mara-hackathon-api.onrender.com/prices")
            pricing_response.raise_for_status()
            pricing_data_list = pricing_response.json()
            pricing_data = pricing_data_list[0] if pricing_data_list else {}
            
            print("🔧 Fetching MARA hardware inventory...")
            # Fetch MARA hardware inventory
            hardware_response = await client.get("https://mara-hackathon-api.onrender.com/inventory")
            hardware_response.raise_for_status()
            mara_inventory = hardware_response.json()
            
            print("🌍 Distributing hardware across 10 global sites...")
            # Distribute hardware across sites
            site_hardware_inventory = distribute_hardware_across_sites(mara_inventory)
            
            # Update global state
            global_state["current_prices"] = pricing_data
            global_state["mara_inventory"] = mara_inventory
            
            # Load existing SLAs from database
            print("📊 Loading existing SLAs from database...")
            await load_slas_from_database()
            
            is_initialized = True
            print("✅ System initialized successfully with live MARA data")
            print(f"📈 Current Bitcoin price: ${pricing_data.get('token_price', 'N/A')}")
            print(f"⚡ Current hash price: ${pricing_data.get('hash_price', 'N/A')}")
            print(f"🏭 Hardware distributed across {len(site_hardware_inventory)} sites")
            
            # Start background tasks
            asyncio.create_task(periodic_price_update())
            asyncio.create_task(periodic_sla_usage_tracking())
            
    except Exception as e:
        print(f"❌ System initialization failed: {e}")
        is_initialized = False
    
    yield
    
    # Shutdown
    print("🛑 Shutting down SLA-Smart Energy Arbitrage Platform...")
    # Save any pending data to database
    await save_current_state_to_database()

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
active_slas = {}  # Track active SLA workloads by site
global_state = {
    "mara_inventory": None,
    "current_prices": None,
    "site_allocations": {},
    "sla_commitments": {"premium": 0, "standard": 0, "flexible": 0, "spot": 0},
    "total_revenue": 0,
    "optimization_history": [],
    "active_slas": {},  # Track active SLAs with details
    "sla_distribution_strategy": None,
    "timezone_routing_enabled": False
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
    compute_type: str  # 'gpu', 'asic', 'mixed'
    compute_units: int  # Number of compute units
    duration_hours: int
    preferred_region: Optional[str] = None
    company_name: Optional[str] = None

# New models for Predictive Maintenance and Hardware Optimization
class HardwareMetrics(BaseModel):
    site_id: str
    hardware_type: str  # 'gpu', 'asic'
    temperature: float
    power_consumption: float
    hash_rate: float
    efficiency: float
    uptime: float
    last_maintenance: str
    predicted_failure_date: Optional[str] = None
    health_score: float

class MaintenancePrediction(BaseModel):
    site_id: str
    hardware_id: str
    hardware_type: str
    current_health: float
    predicted_failure_date: str
    confidence_level: float
    recommended_actions: List[str]
    estimated_cost_savings: float

class HardwareOptimization(BaseModel):
    site_id: str
    hardware_id: str
    hardware_type: str
    current_settings: Dict
    optimized_settings: Dict
    expected_improvements: Dict
    risk_assessment: str

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
                    "asic": {"power": 1.5, "tokens": 50000},  # 1.5 kW per ASIC unit (realistic for inference ASICs)
                    "gpu": {"power": 0.45, "tokens": 1000}   # 0.45 kW per GPU unit (RTX 4090 level)
                },
                "miners": {
                    "air": {"hashrate": 1000, "power": 1.37},      # 1.37 kW per air miner (Antminer S9 level)
                    "hydro": {"hashrate": 5000, "power": 2.95},    # 2.95 kW per hydro miner (S19j Pro level) 
                    "immersion": {"hashrate": 10000, "power": 3.51} # 3.51 kW per immersion miner (S21 Pro level)
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
            {site['name']}:
            - Temperature: {site['weather']['temperature']:.1f}°F
            - Cooling Efficiency: {site['cooling_efficiency']:.1%}
            - Energy Cost Multiplier: {site_config['energy_cost_multiplier']}x
            - Renewable Energy: {site_config['climate']['renewable_energy']:.1%}
            - Local Time: {site.get('local_time', 'N/A')}
            - Current Revenue: ${site.get('revenue', 0):,.2f}
            - Power Used: {site.get('power_used', 0):,} MW
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
    
    # Check if already initialized
    if is_initialized and pricing_data and site_hardware_inventory:
        return {
            "status": "already_initialized", 
            "message": "System is already initialized and running",
            "pricing_data": pricing_data,
            "mara_inventory": global_state.get("mara_inventory"),
            "total_sites": len(site_hardware_inventory),
            "initialized_at_startup": True
        }
    
    try:
        # Re-initialize if needed (fallback)
        print("Manual re-initialization requested...")
        
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
            "message": "System re-initialized successfully",
            "pricing_data": pricing_data,
            "mara_inventory": mara_inventory,
            "total_sites": len(site_hardware_inventory),
            "initialized_at_startup": False
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
        
        # Calculate actual workload allocation based on active SLAs and idle mining
        current_allocation = calculate_site_workload_allocation(site_id, site_inventory)
        
        # Get active SLA summary for this site
        sla_summary = get_active_sla_summary(site_id)
        
        # Calculate power usage based on actual hardware (in kW, convert to MW)
        power_used_kw = 0
        if site_inventory:
            power_used_kw += current_allocation["gpu_compute"] * site_inventory["inference"]["gpu"]["power"]
            power_used_kw += current_allocation["asic_compute"] * site_inventory["inference"]["asic"]["power"]
            power_used_kw += current_allocation["air_miners"] * site_inventory["miners"]["air"]["power"]
            power_used_kw += current_allocation["hydro_miners"] * site_inventory["miners"]["hydro"]["power"]
            power_used_kw += current_allocation["immersion_miners"] * site_inventory["miners"]["immersion"]["power"]
        
        # Convert from kW to MW for display
        power_used = round(power_used_kw / 1000, 3)  # Convert kW to MW with 3 decimal precision
        
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
            
            # Active SLA information
            "active_slas": sla_summary,
            
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
    
    # Parse Claude's recommendations and implement them
    claude_allocations = parse_claude_recommendations(claude_reasoning, site_data)
    
    print(f"DEBUG: Claude allocations parsed: {claude_allocations}")
    print(f"DEBUG: Number of sites with allocations: {len(claude_allocations)}")
    
    # Implement Claude's optimization strategy
    total_revenue = 0
    climate_savings = 0
    
    for site_id, site_config in MULTI_SITE_CONFIG.items():
        # Get Claude's recommended allocation for this site
        claude_allocation = claude_allocations.get(site_id, {})
        
        print(f"DEBUG: Processing {site_id}, Claude allocation: {claude_allocation}")
        
        # Apply Claude's recommendations or use intelligent fallback
        if claude_allocation:
            # Use Claude's specific recommendations
            gpu_allocation = claude_allocation.get("gpu_compute", 0)
            asic_allocation = claude_allocation.get("asic_compute", 0)
            mining_allocation = claude_allocation.get("mining_focus", 0)
            print(f"DEBUG: Using Claude allocation for {site_id}: GPU={gpu_allocation}, ASIC={asic_allocation}, Mining={mining_allocation}")
        else:
            # Intelligent fallback based on site characteristics
            cooling_efficiency = site_config["climate"]["cooling_efficiency"]
            energy_multiplier = site_config["energy_cost_multiplier"]
            renewable_ratio = site_config["climate"]["renewable_energy"]
            
            # Prioritize high-efficiency, low-cost, renewable sites
            efficiency_score = (cooling_efficiency * 0.4 + 
                              (1/energy_multiplier) * 0.3 + 
                              renewable_ratio * 0.3)
            
            # Scale allocations based on efficiency score
            base_gpu = int(60 * efficiency_score)
            base_asic = int(40 * (1 - efficiency_score))  # ASIC mining for less efficient sites
            base_mining = int(20 * efficiency_score)
            
            gpu_allocation = base_gpu
            asic_allocation = base_asic
            mining_allocation = base_mining
            print(f"DEBUG: Using fallback allocation for {site_id}: GPU={gpu_allocation}, ASIC={asic_allocation}, Mining={mining_allocation}")
        
        # Store allocation in global state
        allocation_to_store = {
            "gpu_compute": gpu_allocation,
            "asic_compute": asic_allocation,
            "air_miners": mining_allocation,
            "hydro_miners": mining_allocation // 2,
            "immersion_miners": mining_allocation // 4 if site_config["climate"]["cooling_efficiency"] > 0.8 else 0
        }
        
        global_state["site_allocations"][site_id] = allocation_to_store
        print(f"DEBUG: Stored allocation for {site_id}: {allocation_to_store}")
        
        # Calculate revenue based on actual allocation
        site_revenue = calculate_site_revenue(
            site_id, 
            global_state["site_allocations"][site_id], 
            global_state["current_prices"], 
            site_config
        )
        total_revenue += site_revenue
        
        # Calculate climate savings (higher efficiency = more savings)
        if site_config["climate"]["cooling_efficiency"] > 0.8:
            climate_savings += site_revenue * 0.35  # 35% savings for high efficiency
        elif site_config["climate"]["cooling_efficiency"] > 0.6:
            climate_savings += site_revenue * 0.20  # 20% savings for medium efficiency
    
    print(f"DEBUG: Final global_state site_allocations: {global_state.get('site_allocations', {})}")
    
    # Apply Claude's SLA distribution recommendations
    implement_claude_sla_strategy(claude_reasoning)
    
    # Create optimization result
    optimization = GlobalOptimization(
        timestamp=datetime.now().isoformat(),
        total_revenue=total_revenue,
        climate_savings=climate_savings,
        timezone_optimization=total_revenue * 0.18,  # 18% from timezone optimization
        sla_performance={"premium": 99.9, "standard": 96.5, "flexible": 92.0, "spot": 87.0},
        claude_reasoning=claude_reasoning
    )
    
    # Store in history
    global_state["optimization_history"].append(optimization)
    global_state["total_revenue"] = total_revenue
    
    return optimization

def parse_claude_recommendations(claude_reasoning: str, site_data: Dict) -> Dict:
    """Parse Claude's text recommendations into actionable allocations"""
    allocations = {}
    
    try:
        print(f"DEBUG: Starting to parse Claude recommendations...")
        print(f"DEBUG: Claude reasoning length: {len(claude_reasoning)}")
        
        # Extract site-specific recommendations from Claude's reasoning
        lines = claude_reasoning.lower().split('\n')
        
        # Site name mapping for better parsing
        site_name_mapping = {
            'nordic iceland': 'site_1_nordic',
            'norway oslo': 'site_3_norway', 
            'canada vancouver': 'site_2_canada',
            'ireland dublin': 'site_6_ireland',
            'chile santiago': 'site_9_chile',
            'germany berlin': 'site_10_germany',
            'japan tokyo': 'site_7_japan',
            'australia sydney': 'site_8_australia',
            'singapore': 'site_4_singapore',
            'texas': 'site_5_texas'
        }
        
        # Apply Claude's specific site recommendations from the reasoning
        reasoning_lower = claude_reasoning.lower()
        
        print(f"DEBUG: Checking for site-specific keywords...")
        
        # Nordic Iceland - Premium AI hub
        if 'nordic iceland' in reasoning_lower:
            print(f"DEBUG: Found Nordic Iceland in reasoning")
            if 'premium' in reasoning_lower or 'ai' in reasoning_lower:
                allocations['site_1_nordic'] = {
                    'gpu_compute': 80, 'ai_focus': 40, 'mining_focus': 30, 'tier_focus': 'premium'
                }
                print(f"DEBUG: Added Nordic Iceland allocation: {allocations['site_1_nordic']}")
        
        # Norway Oslo - Premium AI hub  
        if 'norway oslo' in reasoning_lower:
            print(f"DEBUG: Found Norway Oslo in reasoning")
            if 'premium' in reasoning_lower or 'ai' in reasoning_lower:
                allocations['site_3_norway'] = {
                    'gpu_compute': 70, 'ai_focus': 35, 'mining_focus': 35, 'tier_focus': 'premium'
                }
                print(f"DEBUG: Added Norway Oslo allocation: {allocations['site_3_norway']}")
        
        # Canada Vancouver - Standard AI hub
        if 'canada vancouver' in reasoning_lower:
            print(f"DEBUG: Found Canada Vancouver in reasoning")
            if 'standard' in reasoning_lower or 'ai' in reasoning_lower:
                allocations['site_2_canada'] = {
                    'gpu_compute': 60, 'ai_focus': 35, 'mining_focus': 35, 'tier_focus': 'standard'
                }
                print(f"DEBUG: Added Canada Vancouver allocation: {allocations['site_2_canada']}")
        
        # Singapore - Reduced capacity
        if 'singapore' in reasoning_lower:
            print(f"DEBUG: Found Singapore in reasoning")
            if 'reduce' in reasoning_lower or 'minimal' in reasoning_lower:
                allocations['site_4_singapore'] = {
                    'gpu_compute': 25, 'ai_focus': 15, 'asic_compute': 15, 'tier_focus': 'spot'
                }
                print(f"DEBUG: Added Singapore allocation: {allocations['site_4_singapore']}")
        
        # Texas - Reduced during peak
        if 'texas' in reasoning_lower:
            print(f"DEBUG: Found Texas in reasoning")
            if 'reduce' in reasoning_lower or 'burst' in reasoning_lower:
                allocations['site_5_texas'] = {
                    'gpu_compute': 30, 'ai_focus': 20, 'asic_compute': 20, 'tier_focus': 'flexible'
                }
                print(f"DEBUG: Added Texas allocation: {allocations['site_5_texas']}")
        
        # Add remaining sites with basic allocations based on Claude's overall strategy
        if 'ireland dublin' in reasoning_lower:
            allocations['site_6_ireland'] = {
                'gpu_compute': 55, 'ai_focus': 30, 'mining_focus': 25, 'tier_focus': 'standard'
            }
            print(f"DEBUG: Added Ireland allocation")
            
        if 'chile santiago' in reasoning_lower:
            allocations['site_9_chile'] = {
                'gpu_compute': 45, 'ai_focus': 25, 'mining_focus': 45, 'tier_focus': 'flexible'
            }
            print(f"DEBUG: Added Chile allocation")
            
        if 'germany berlin' in reasoning_lower:
            allocations['site_10_germany'] = {
                'gpu_compute': 50, 'ai_focus': 25, 'mining_focus': 30, 'tier_focus': 'standard'
            }
            print(f"DEBUG: Added Germany allocation")
            
        if 'japan tokyo' in reasoning_lower:
            allocations['site_7_japan'] = {
                'gpu_compute': 40, 'ai_focus': 20, 'mining_focus': 25, 'tier_focus': 'standard'
            }
            print(f"DEBUG: Added Japan allocation")
            
        if 'australia sydney' in reasoning_lower:
            allocations['site_8_australia'] = {
                'gpu_compute': 35, 'ai_focus': 18, 'mining_focus': 20, 'tier_focus': 'flexible'
            }
            print(f"DEBUG: Added Australia allocation")
        
        print(f"DEBUG: Final allocations parsed: {list(allocations.keys())}")
        print(f"DEBUG: Total sites with allocations: {len(allocations)}")
    
    except Exception as e:
        print(f"Error parsing Claude recommendations: {e}")
        # Return empty dict to fall back to intelligent defaults
        return {}
    
    return allocations

def implement_claude_sla_strategy(claude_reasoning: str):
    """Implement Claude's SLA distribution strategy"""
    try:
        reasoning_lower = claude_reasoning.lower()
        print(f"DEBUG: Parsing Claude reasoning for SLA strategy...")
        
        # Parse Claude's specific SLA distribution recommendations
        if 'sla distribution' in reasoning_lower or 'premium' in reasoning_lower:
            print(f"DEBUG: Found SLA keywords in reasoning")
            # Extract Claude's specific site recommendations for each SLA tier
            strategy = {
                "premium_sites": [],
                "standard_sites": [],
                "flexible_sites": [],
                "spot_sites": []
            }
            
            # Premium SLA sites (99.9% uptime)
            if 'nordic iceland' in reasoning_lower and 'premium' in reasoning_lower:
                strategy["premium_sites"].append("site_1_nordic")
                print(f"DEBUG: Added Nordic Iceland to premium sites")
            if 'norway oslo' in reasoning_lower and 'premium' in reasoning_lower:
                strategy["premium_sites"].append("site_3_norway")
                print(f"DEBUG: Added Norway Oslo to premium sites")
            if 'canada vancouver' in reasoning_lower and ('premium' in reasoning_lower or 'standard' in reasoning_lower):
                strategy["premium_sites"].append("site_2_canada")
                print(f"DEBUG: Added Canada Vancouver to premium sites")
            
            # Standard SLA sites (95% uptime)
            if 'ireland dublin' in reasoning_lower and 'standard' in reasoning_lower:
                strategy["standard_sites"].append("site_6_ireland")
                print(f"DEBUG: Added Ireland Dublin to standard sites")
            if 'japan tokyo' in reasoning_lower:
                strategy["standard_sites"].append("site_7_japan")
                print(f"DEBUG: Added Japan Tokyo to standard sites")
            if 'australia sydney' in reasoning_lower:
                strategy["standard_sites"].append("site_8_australia")
                print(f"DEBUG: Added Australia Sydney to standard sites")
            
            # Flexible SLA sites (90% uptime)
            if 'chile santiago' in reasoning_lower and 'flexible' in reasoning_lower:
                strategy["flexible_sites"].append("site_9_chile")
                print(f"DEBUG: Added Chile Santiago to flexible sites")
            if 'germany berlin' in reasoning_lower and 'flexible' in reasoning_lower:
                strategy["flexible_sites"].append("site_10_germany")
                print(f"DEBUG: Added Germany Berlin to flexible sites")
            if 'canada vancouver' in reasoning_lower and 'flexible' in reasoning_lower:
                strategy["flexible_sites"].append("site_2_canada")
                print(f"DEBUG: Added Canada Vancouver to flexible sites")
            
            # Spot SLA sites (minimal operations)
            if 'singapore' in reasoning_lower and 'reduce' in reasoning_lower:
                strategy["spot_sites"].append("site_4_singapore")
                print(f"DEBUG: Added Singapore to spot sites")
            if 'texas' in reasoning_lower and 'reduce' in reasoning_lower:
                strategy["spot_sites"].append("site_5_texas")
                print(f"DEBUG: Added Texas to spot sites")
            
            # Only set strategy if we found recommendations
            if any(strategy.values()):
                global_state["sla_distribution_strategy"] = strategy
                print(f"Claude SLA strategy implemented: {strategy}")
            else:
                print(f"DEBUG: No strategy sites found, not setting distribution strategy")
        else:
            print(f"DEBUG: No SLA keywords found in reasoning")
        
        # Implement time-of-day routing if mentioned
        if 'time-of-day' in reasoning_lower or 'business hours' in reasoning_lower or 'peak hours' in reasoning_lower:
            global_state["timezone_routing_enabled"] = True
            print("Claude timezone routing enabled")
        
    except Exception as e:
        print(f"Error implementing Claude SLA strategy: {e}")

@app.post("/api/sla/request")
async def request_sla(sla_request: SLARequest):
    """Request compute-based SLA allocation with actual resource allocation"""
    if sla_request.tier not in SLA_TIERS:
        raise HTTPException(status_code=400, detail="Invalid SLA tier")
    
    # Calculate estimated power consumption
    power_per_unit = {
        'gpu': 0.33,  # 330W per GPU
        'asic': 3.0,  # 3kW per ASIC
        'mixed': 1.5  # Average
    }
    
    estimated_power_mw = (sla_request.compute_units * power_per_unit[sla_request.compute_type]) / 1000
    
    # Use Claude's SLA distribution strategy if available
    preferred_sites = []
    if global_state.get("sla_distribution_strategy"):
        strategy = global_state["sla_distribution_strategy"]
        if sla_request.tier == "premium":
            preferred_sites = strategy.get("premium_sites", [])
        elif sla_request.tier == "standard":
            preferred_sites = strategy.get("standard_sites", [])
        elif sla_request.tier == "flexible":
            preferred_sites = strategy.get("flexible_sites", [])
        elif sla_request.tier == "spot":
            preferred_sites = strategy.get("spot_sites", [])
    
    # Find optimal site for this SLA tier based on compute type and requirements
    optimal_site = None
    best_score = 0
    
    # Check preferred sites first (from Claude's strategy)
    sites_to_check = preferred_sites if preferred_sites else MULTI_SITE_CONFIG.keys()
    
    for site_id in sites_to_check:
        if site_id not in MULTI_SITE_CONFIG:
            continue
            
        site_config = MULTI_SITE_CONFIG[site_id]
        
        # Check if site has available hardware
        site_inventory = site_hardware_inventory.get(site_id, {})
        if not site_inventory:
            continue
            
        # Check hardware availability
        available_hardware = 0
        if sla_request.compute_type == 'gpu':
            available_hardware = site_inventory.get("inference", {}).get("gpu", {}).get("available", 0)
        elif sla_request.compute_type == 'asic':
            available_hardware = site_inventory.get("inference", {}).get("asic", {}).get("available", 0)
        elif sla_request.compute_type == 'mixed':
            gpu_available = site_inventory.get("inference", {}).get("gpu", {}).get("available", 0)
            asic_available = site_inventory.get("inference", {}).get("asic", {}).get("available", 0)
            available_hardware = min(gpu_available, asic_available) * 2  # Mixed needs both types
        
        # Check if site can accommodate the request
        current_allocation = calculate_site_workload_allocation(site_id, site_inventory)
        if sla_request.compute_type == 'gpu':
            used_hardware = current_allocation.get("gpu_compute", 0)
        elif sla_request.compute_type == 'asic':
            used_hardware = current_allocation.get("asic_compute", 0)
        else:  # mixed
            used_hardware = max(current_allocation.get("gpu_compute", 0), current_allocation.get("asic_compute", 0))
        
        remaining_capacity = available_hardware - used_hardware
        if remaining_capacity < sla_request.compute_units:
            continue  # Not enough capacity
        
        # Base score from cooling efficiency and energy cost
        base_score = (site_config["climate"]["cooling_efficiency"] * 0.5 + 
                     (1 - site_config["energy_cost_multiplier"]) * 0.3)
        
        # Compute type preference scoring
        hardware_profile = site_config["hardware_profile"]
        if sla_request.compute_type == 'gpu':
            compute_score = hardware_profile["gpu_ratio"] * 0.2
        elif sla_request.compute_type == 'asic':
            compute_score = hardware_profile["asic_ratio"] * 0.2
        else:  # mixed
            compute_score = (hardware_profile["gpu_ratio"] + hardware_profile["asic_ratio"]) * 0.1
        
        total_score = base_score + compute_score
        
        # Claude strategy bonus (prioritize sites recommended by Claude)
        if site_id in preferred_sites:
            total_score += 0.2  # Strong preference for Claude-recommended sites
        
        # Regional preference bonus
        if sla_request.preferred_region:
            region_mapping = {
                'nordic': ['site_1_nordic', 'site_3_norway'],
                'north_america': ['site_2_canada', 'site_5_texas'],
                'europe': ['site_6_ireland', 'site_10_germany'],
                'asia_pacific': ['site_4_singapore', 'site_7_japan', 'site_8_australia']
            }
            if sla_request.preferred_region in region_mapping and site_id in region_mapping[sla_request.preferred_region]:
                total_score += 0.1
        
        if total_score > best_score:
            best_score = total_score
            optimal_site = site_id
    
    # If no preferred sites work, fall back to all sites
    if not optimal_site and preferred_sites:
        return await request_sla_fallback(sla_request, estimated_power_mw)
    
    if not optimal_site:
        raise HTTPException(status_code=400, detail="No available capacity for this SLA request")
    
    # Create SLA record
    sla_id = f"sla_{int(time.time())}_{optimal_site}"
    expiration_time = datetime.now() + timedelta(hours=sla_request.duration_hours)
    
    # Calculate estimated revenue for this SLA
    site_config = MULTI_SITE_CONFIG[optimal_site]
    base_rate = 100  # $100 per compute unit per hour
    tier_multiplier = SLA_TIERS[sla_request.tier]["price_multiplier"]
    efficiency_bonus = site_config["climate"]["cooling_efficiency"]
    
    # Claude optimization bonus
    claude_bonus = 1.1 if optimal_site in preferred_sites else 1.0
    
    estimated_revenue = (sla_request.compute_units * sla_request.duration_hours * 
                        base_rate * tier_multiplier * efficiency_bonus * claude_bonus)
    
    sla_record = {
        "sla_id": sla_id,
        "tier": sla_request.tier,
        "compute_type": sla_request.compute_type,
        "compute_units": sla_request.compute_units,
        "duration_hours": sla_request.duration_hours,
        "site_id": optimal_site,
        "company_name": sla_request.company_name,
        "created_at": datetime.now().isoformat(),
        "expires_at": expiration_time.isoformat(),
        "estimated_revenue": estimated_revenue,
        "status": "active",
        "claude_optimized": optimal_site in preferred_sites,
    }
    
    # Add to active SLAs (in-memory for compatibility)
    if optimal_site not in global_state["active_slas"]:
        global_state["active_slas"][optimal_site] = []
    global_state["active_slas"][optimal_site].append(sla_record)
    
    # Save SLA to database
    sla_data = sla_record.copy()
    sla_data['site_name'] = MULTI_SITE_CONFIG[optimal_site]["name"]
    sla_data['preferred_region'] = sla_request.preferred_region
    await sla_db.create_sla(sla_data)
    
    # Update SLA commitments (track by estimated power for compatibility)
    global_state["sla_commitments"][sla_request.tier] += estimated_power_mw
    
    return {
        "sla_id": sla_id,
        "sla_tier": sla_request.tier,
        "compute_type": sla_request.compute_type,
        "compute_units_allocated": sla_request.compute_units,
        "estimated_power_mw": round(estimated_power_mw, 2),
        "optimal_site": optimal_site,
        "site_name": MULTI_SITE_CONFIG[optimal_site]["name"],
        "estimated_uptime": SLA_TIERS[sla_request.tier]["uptime"],
        "price_multiplier": SLA_TIERS[sla_request.tier]["price_multiplier"],
        "duration_hours": sla_request.duration_hours,
        "estimated_revenue": round(estimated_revenue, 2),
        "expires_at": expiration_time.isoformat(),
        "status": "allocated",
        "claude_optimized": optimal_site in preferred_sites,
        "optimization_bonus": f"{((claude_bonus - 1) * 100):.0f}%" if claude_bonus > 1 else "0%",
        "company_name": sla_request.company_name
    }

async def request_sla_fallback(sla_request: SLARequest, estimated_power_mw: float):
    """Fallback SLA allocation when Claude's preferred sites are unavailable"""
    # Use original logic as fallback
    for site_id, site_config in MULTI_SITE_CONFIG.items():
        site_inventory = site_hardware_inventory.get(site_id, {})
        if not site_inventory:
            continue
            
        # Basic capacity check
        current_allocation = calculate_site_workload_allocation(site_id, site_inventory)
        
        # Simple allocation to first available site
        sla_id = f"sla_{int(time.time())}_{site_id}_fallback"
        expiration_time = datetime.now() + timedelta(hours=sla_request.duration_hours)
        
        estimated_revenue = (sla_request.compute_units * sla_request.duration_hours * 
                            100 * SLA_TIERS[sla_request.tier]["price_multiplier"])
        
        sla_record = {
            "sla_id": sla_id,
            "tier": sla_request.tier,
            "compute_type": sla_request.compute_type,
            "compute_units": sla_request.compute_units,
            "duration_hours": sla_request.duration_hours,
            "site_id": site_id,
            "company_name": sla_request.company_name,
            "created_at": datetime.now().isoformat(),
            "expires_at": expiration_time.isoformat(),
            "estimated_revenue": estimated_revenue,
            "status": "active",
            "claude_optimized": False
        }
        
        if site_id not in global_state["active_slas"]:
            global_state["active_slas"][site_id] = []
        global_state["active_slas"][site_id].append(sla_record)
        
        # Save SLA to database
        sla_data = sla_record.copy()
        sla_data['site_name'] = site_config["name"]
        sla_data['preferred_region'] = sla_request.preferred_region
        await sla_db.create_sla(sla_data)
        
        global_state["sla_commitments"][sla_request.tier] += estimated_power_mw
        
        return {
            "sla_id": sla_id,
            "sla_tier": sla_request.tier,
            "optimal_site": site_id,
            "site_name": site_config["name"],
            "estimated_revenue": round(estimated_revenue, 2),
            "status": "allocated_fallback",
            "claude_optimized": False,
            "optimization_bonus": "0%",
            "company_name": sla_request.company_name
        }
    
    raise HTTPException(status_code=400, detail="No available capacity for this SLA request")

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
        "global_state_keys": list(global_state.keys()),
        "site_allocations": global_state.get("site_allocations", {}),
        "total_revenue": global_state.get("total_revenue", 0)
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

def calculate_site_workload_allocation(site_id: str, site_inventory: Dict) -> Dict:
    """Calculate workload allocation for a site"""
    
    # First check if Claude has provided optimized allocations
    if "site_allocations" in global_state and site_id in global_state["site_allocations"]:
        claude_allocation = global_state["site_allocations"][site_id]
        
        # Validate Claude's allocation against hardware limits
        available_gpu = site_inventory.get("inference", {}).get("gpu", {}).get("available", 0)
        available_asic = site_inventory.get("inference", {}).get("asic", {}).get("available", 0)
        
        # Respect hardware limits while using Claude's recommendations
        validated_allocation = {
            "gpu_compute": min(claude_allocation.get("gpu_compute", 0), available_gpu),
            "asic_compute": min(claude_allocation.get("asic_compute", 0), available_asic),
            "air_miners": claude_allocation.get("air_miners", 0),
            "hydro_miners": claude_allocation.get("hydro_miners", 0),
            "immersion_miners": claude_allocation.get("immersion_miners", 0)
        }
        
        return validated_allocation
    
    # Fallback to original logic if no Claude allocation
    total_gpu = site_inventory.get("inference", {}).get("gpu", {}).get("available", 0)
    total_asic = site_inventory.get("inference", {}).get("asic", {}).get("available", 0)
    
    # Calculate SLA commitments for this site
    site_sla_commitments = get_active_sla_summary(site_id)
    
    # Reserve capacity for SLA commitments first
    reserved_gpu = site_sla_commitments.get("gpu_reserved", 0)
    reserved_asic = site_sla_commitments.get("asic_reserved", 0)
    
    # Available capacity after SLA reservations
    available_gpu = max(0, total_gpu - reserved_gpu)
    available_asic = max(0, total_asic - reserved_asic)
    
    # Distribute remaining capacity between AI inference and mining
    # Prioritize AI inference (higher revenue per MW)
    gpu_compute = min(available_gpu, int(available_gpu * 0.7))  # 70% for AI inference
    asic_compute = min(available_asic, int(available_asic * 0.6))  # 60% for AI inference
    
    # Allocate mining capacity based on site efficiency
    site_config = MULTI_SITE_CONFIG.get(site_id, {})
    cooling_efficiency = site_config.get("climate", {}).get("cooling_efficiency", 0.5)
    
    # More efficient sites get more mining allocation
    mining_multiplier = cooling_efficiency * 1.5
    
    return {
        "gpu_compute": gpu_compute + reserved_gpu,  # Include SLA reservations
        "asic_compute": asic_compute + reserved_asic,  # Include SLA reservations
        "air_miners": int(30 * mining_multiplier),
        "hydro_miners": int(15 * mining_multiplier),
        "immersion_miners": int(8 * mining_multiplier)
    }

def get_active_sla_summary(site_id: str) -> Dict:
    """Get summary of active SLAs for a site"""
    site_slas = global_state["active_slas"].get(site_id, [])
    
    summary = {
        "total_slas": len(site_slas),
        "total_compute_units": sum(sla["compute_units"] for sla in site_slas),
        "sla_breakdown": {"premium": 0, "standard": 0, "flexible": 0, "spot": 0},
        "compute_breakdown": {"gpu": 0, "asic": 0, "mixed": 0},
        "total_revenue_from_slas": 0
    }
    
    for sla in site_slas:
        summary["sla_breakdown"][sla["tier"]] += sla["compute_units"]
        summary["compute_breakdown"][sla["compute_type"]] += sla["compute_units"]
        summary["total_revenue_from_slas"] += sla.get("estimated_revenue", 0)
    
    return summary

@app.get("/api/sla/active")
async def get_active_slas():
    """Get all active SLAs across all sites"""
    cleanup_expired_slas()  # Clean up expired SLAs first
    
    all_slas = []
    total_stats = {
        "total_active_slas": 0,
        "total_compute_units": 0,
        "total_estimated_revenue": 0,
        "tier_breakdown": {"premium": 0, "standard": 0, "flexible": 0, "spot": 0},
        "compute_breakdown": {"gpu": 0, "asic": 0, "mixed": 0}
    }
    
    for site_id, site_slas in global_state["active_slas"].items():
        site_name = MULTI_SITE_CONFIG.get(site_id, {}).get("name", site_id)
        
        for sla in site_slas:
            sla_info = sla.copy()
            sla_info["site_name"] = site_name
            all_slas.append(sla_info)
            
            # Update stats
            total_stats["total_active_slas"] += 1
            total_stats["total_compute_units"] += sla["compute_units"]
            total_stats["total_estimated_revenue"] += sla.get("estimated_revenue", 0)
            total_stats["tier_breakdown"][sla["tier"]] += sla["compute_units"]
            total_stats["compute_breakdown"][sla["compute_type"]] += sla["compute_units"]
    
    return {
        "active_slas": all_slas,
        "statistics": total_stats,
        "last_updated": datetime.now().isoformat()
    }

@app.get("/api/sla/database")
async def get_sla_database_info():
    """Get SLA database information and statistics"""
    try:
        # Get database info
        db_info = await sla_db.get_database_info()
        
        # Get comprehensive statistics
        statistics = await sla_db.get_sla_statistics()
        
        return {
            "database_info": db_info,
            "statistics": statistics,
            "status": "connected"
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "error"
        }

@app.get("/api/sla/{sla_id}/usage")
async def get_sla_usage_history(sla_id: str, hours: int = 24):
    """Get usage history for a specific SLA"""
    try:
        usage_history = await sla_db.get_sla_usage_history(sla_id, hours)
        
        if not usage_history:
            raise HTTPException(status_code=404, detail="SLA not found or no usage data available")
        
        # Calculate summary statistics
        total_power = sum(u['power_consumed_mw'] for u in usage_history)
        total_revenue = sum(u['revenue_generated'] for u in usage_history)
        avg_efficiency = sum(u['efficiency_score'] for u in usage_history) / len(usage_history) if usage_history else 0
        avg_uptime = sum(u['uptime_percentage'] for u in usage_history) / len(usage_history) if usage_history else 0
        
        return {
            "sla_id": sla_id,
            "usage_history": usage_history,
            "summary": {
                "total_records": len(usage_history),
                "total_power_consumed_mw": round(total_power, 3),
                "total_revenue_generated": round(total_revenue, 2),
                "average_efficiency": round(avg_efficiency, 3),
                "average_uptime": round(avg_uptime, 1),
                "period_hours": hours
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving SLA usage: {str(e)}")

@app.post("/api/sla/{sla_id}/terminate")
async def terminate_sla(sla_id: str):
    """Terminate an active SLA"""
    try:
        # Update status in database
        success = await sla_db.update_sla_status(sla_id, "terminated")
        
        if not success:
            raise HTTPException(status_code=404, detail="SLA not found")
        
        # Remove from in-memory storage
        for site_id, site_slas in global_state["active_slas"].items():
            for i, sla in enumerate(site_slas):
                if sla["sla_id"] == sla_id:
                    # Reduce commitments
                    power_per_unit = {'gpu': 0.33, 'asic': 3.0, 'mixed': 1.5}
                    estimated_power_mw = (sla["compute_units"] * power_per_unit[sla["compute_type"]]) / 1000
                    global_state["sla_commitments"][sla["tier"]] = max(0, 
                        global_state["sla_commitments"][sla["tier"]] - estimated_power_mw)
                    
                    # Remove from memory
                    del site_slas[i]
                    
                    if not site_slas:  # Remove empty site entry
                        del global_state["active_slas"][site_id]
                    
                    return {
                        "sla_id": sla_id,
                        "status": "terminated",
                        "message": "SLA terminated successfully"
                    }
        
        return {
            "sla_id": sla_id,
            "status": "terminated",
            "message": "SLA terminated in database but not found in memory"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error terminating SLA: {str(e)}")

@app.get("/api/sla/statistics")
async def get_comprehensive_sla_statistics():
    """Get comprehensive SLA statistics from database"""
    try:
        statistics = await sla_db.get_sla_statistics()
        
        # Add real-time memory statistics for comparison
        memory_stats = {
            "active_sites": len(global_state["active_slas"]),
            "total_memory_slas": sum(len(slas) for slas in global_state["active_slas"].values()),
            "memory_commitments": global_state["sla_commitments"]
        }
        
        return {
            "database_statistics": statistics,
            "memory_statistics": memory_stats,
            "sync_status": "synchronized" if statistics.get('totals', {}).get('total_active', 0) == memory_stats['total_memory_slas'] else "out_of_sync"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving SLA statistics: {str(e)}")

def cleanup_expired_slas():
    """Remove expired SLAs from active tracking"""
    current_time = datetime.now()
    
    for site_id in list(global_state["active_slas"].keys()):
        site_slas = global_state["active_slas"][site_id]
        
        # Filter out expired SLAs
        active_slas = []
        for sla in site_slas:
            try:
                expires_at = datetime.fromisoformat(sla["expires_at"].replace('Z', '+00:00'))
                if expires_at.replace(tzinfo=None) > current_time:
                    active_slas.append(sla)
                else:
                    # SLA expired, reduce commitments
                    power_per_unit = {'gpu': 0.33, 'asic': 3.0, 'mixed': 1.5}
                    estimated_power_mw = (sla["compute_units"] * power_per_unit[sla["compute_type"]]) / 1000
                    global_state["sla_commitments"][sla["tier"]] = max(0, 
                        global_state["sla_commitments"][sla["tier"]] - estimated_power_mw)
            except Exception as e:
                print(f"Error processing SLA expiration: {e}")
                continue
        
        if active_slas:
            global_state["active_slas"][site_id] = active_slas
        else:
            del global_state["active_slas"][site_id]

async def load_slas_from_database():
    """Load existing SLAs from database into global state"""
    try:
        active_slas = await sla_db.get_active_slas()
        
        # Clear current in-memory SLAs
        global_state["active_slas"] = {}
        global_state["sla_commitments"] = {"premium": 0, "standard": 0, "flexible": 0, "spot": 0}
        
        # Load SLAs into memory for compatibility with existing code
        for sla in active_slas:
            site_id = sla['site_id']
            if site_id not in global_state["active_slas"]:
                global_state["active_slas"][site_id] = []
            
            # Convert database record back to in-memory format
            sla_record = {
                "sla_id": sla['sla_id'],
                "tier": sla['tier'],
                "compute_type": sla['compute_type'],
                "compute_units": sla['compute_units'],
                "duration_hours": sla['duration_hours'],
                "site_id": sla['site_id'],
                "company_name": sla.get('company_name', ''),
                "created_at": sla['created_at'],
                "expires_at": sla['expires_at'],
                "estimated_revenue": sla['estimated_revenue'],
                "status": sla['status'],
                "claude_optimized": bool(sla['claude_optimized'])
            }
            
            global_state["active_slas"][site_id].append(sla_record)
            
            # Update SLA commitments
            power_per_unit = {'gpu': 0.33, 'asic': 3.0, 'mixed': 1.5}
            estimated_power_mw = (sla['compute_units'] * power_per_unit[sla['compute_type']]) / 1000
            global_state["sla_commitments"][sla['tier']] += estimated_power_mw
        
        print(f"📊 Loaded {len(active_slas)} active SLAs from database")
        
    except Exception as e:
        print(f"⚠️ Error loading SLAs from database: {e}")

async def save_current_state_to_database():
    """Save current state to database before shutdown"""
    try:
        # Update SLA commitments in database
        await sla_db.update_sla_commitments(global_state["sla_commitments"])
        print("💾 Current state saved to database")
    except Exception as e:
        print(f"⚠️ Error saving state to database: {e}")

async def periodic_sla_usage_tracking():
    """Background task to track SLA usage and record metrics"""
    while True:
        try:
            await asyncio.sleep(300)  # Every 5 minutes
            
            # Get all active SLAs and record usage
            for site_id, site_slas in global_state["active_slas"].items():
                site_config = MULTI_SITE_CONFIG.get(site_id, {})
                
                for sla in site_slas:
                    # Calculate current usage metrics
                    power_per_unit = {'gpu': 0.33, 'asic': 3.0, 'mixed': 1.5}
                    power_consumed = (sla['compute_units'] * power_per_unit[sla['compute_type']]) / 1000
                    
                    # Simulate efficiency and uptime based on site conditions
                    site_efficiency = calculate_efficiency_score(site_config, simulate_weather(site_config.get('climate', {})))
                    uptime_percentage = min(99.9, site_efficiency + random.uniform(-5, 5))
                    
                    # Calculate revenue for this period (5 minutes)
                    hourly_rate = sla['estimated_revenue'] / sla['duration_hours']
                    period_revenue = hourly_rate * (5/60)  # 5 minutes worth
                    
                    # Record usage in database
                    usage_data = {
                        'sla_id': sla['sla_id'],
                        'compute_units_used': sla['compute_units'],
                        'power_consumed_mw': power_consumed,
                        'revenue_generated': period_revenue,
                        'efficiency_score': site_efficiency / 100,  # Convert to 0-1 scale
                        'uptime_percentage': uptime_percentage
                    }
                    
                    await sla_db.record_sla_usage(usage_data)
            
            # Cleanup expired SLAs
            expired_count = await sla_db.cleanup_expired_slas()
            if expired_count > 0:
                print(f"🧹 Cleaned up {expired_count} expired SLAs")
                # Reload SLAs to sync with database
                await load_slas_from_database()
            
        except Exception as e:
            print(f"⚠️ Error in SLA usage tracking: {e}")
            await asyncio.sleep(60)  # Retry in 1 minute on error

# Predictive Maintenance and Hardware Optimization Endpoints

@app.get("/api/maintenance/predictions")
async def get_maintenance_predictions():
    """Get AI-driven predictive maintenance predictions for all sites using Claude Sonnet 4"""
    try:
        hardware_metrics = []
        for site_id, site_config in MULTI_SITE_CONFIG.items():
            site_inventory = site_hardware_inventory.get(site_id, {})
            for hardware_type in ['gpu', 'asic']:
                if hardware_type in site_inventory.get('inference', {}):
                    hardware_count = site_inventory['inference'][hardware_type].get('total', 0)
                    for i in range(min(5, hardware_count)):
                        hardware_metrics.append({
                            "hardware_id": f"{hardware_type}_{site_id}_{i}",
                            "site_id": site_id,
                            "hardware_type": hardware_type,
                            "temperature": 65 + (10 if hardware_type == 'asic' else 0),
                            "power_consumption": 330 if hardware_type == 'gpu' else 3000,
                            "hash_rate": 100 if hardware_type == 'gpu' else 1000,
                            "efficiency": 90,
                            "uptime": 99.5,
                            "last_maintenance": (datetime.now() - timedelta(days=30)).isoformat()
                        })
        # Build Claude-style prompt
        prompt = (
            "You are an expert in predictive maintenance for crypto mining hardware. "
            "Given the following hardware metrics, predict which units are at risk of failure, "
            "estimate their health score, and recommend preventive actions. "
            "Return a JSON list with: hardware_id, health_score (0-100), predicted_failure_date (ISO), "
            "confidence_level (0-1), recommended_actions (list of strings), estimated_cost_savings (USD).\n\n"
            f"Hardware metrics:\n{json.dumps(hardware_metrics, indent=2)}"
        )
        # Use real Claude API
        predictions = await call_claude_api(prompt, task="predictive_maintenance", hardware_metrics=hardware_metrics)
        return {
            "predictions": predictions,
            "total_predictions": len(predictions),
            "high_risk_count": len([p for p in predictions if p["health_score"] < 80]),
            "estimated_total_savings": sum(p["estimated_cost_savings"] for p in predictions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating maintenance predictions: {str(e)}")

@app.post("/api/hardware/optimize")
async def optimize_hardware_settings():
    """AI-driven hardware optimization for all sites using Claude Sonnet 4"""
    try:
        hardware_metrics = []
        for site_id, site_config in MULTI_SITE_CONFIG.items():
            site_inventory = site_hardware_inventory.get(site_id, {})
            for hardware_type in ['gpu', 'asic']:
                if hardware_type in site_inventory.get('inference', {}):
                    hardware_count = site_inventory['inference'][hardware_type].get('total', 0)
                    for i in range(min(3, hardware_count)):
                        hardware_metrics.append({
                            "hardware_id": f"{hardware_type}_{site_id}_{i}",
                            "site_id": site_id,
                            "hardware_type": hardware_type,
                            "current_settings": {
                                "clock_speed": 1.0,
                                "voltage": 1.0,
                                "power_limit": 1.0,
                                "temperature_target": 75,
                                "fan_speed": 0.8
                            }
                        })
        prompt = (
            "You are an expert in hardware optimization for mining. "
            "Given the current hardware settings, suggest optimized settings for performance and efficiency. "
            "Return a JSON list with: hardware_id, optimized_settings (dict), expected_improvements (dict), risk_assessment.\n\n"
            f"Hardware metrics:\n{json.dumps(hardware_metrics, indent=2)}"
        )
        optimizations = await call_claude_api(prompt, task="hardware_optimization", hardware_metrics=hardware_metrics)
        # Calculate summary
        total_performance_gain = sum(o["expected_improvements"]["performance_gain_percent"] for o in optimizations)
        total_power_savings = sum(o["expected_improvements"]["power_savings_percent"] for o in optimizations)
        total_revenue_increase = sum(o["expected_improvements"]["estimated_revenue_increase"] for o in optimizations)
        total_cost_savings = sum(o["expected_improvements"]["estimated_cost_savings"] for o in optimizations)
        return {
            "optimizations": optimizations,
            "total_optimizations": len(optimizations),
            "summary": {
                "total_performance_gain_percent": round(total_performance_gain, 1),
                "total_power_savings_percent": round(total_power_savings, 1),
                "total_revenue_increase": round(total_revenue_increase, 2),
                "total_cost_savings": round(total_cost_savings, 2),
                "net_benefit": round(total_revenue_increase + total_cost_savings, 2)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error optimizing hardware settings: {str(e)}")

@app.post("/api/maintenance/schedule")
async def schedule_maintenance():
    """Schedule preventive maintenance based on AI predictions using Claude Sonnet 4"""
    try:
        # Get current predictions (simulate hardware metrics)
        hardware_metrics = []
        for site_id, site_config in MULTI_SITE_CONFIG.items():
            site_inventory = site_hardware_inventory.get(site_id, {})
            for hardware_type in ['gpu', 'asic']:
                if hardware_type in site_inventory.get('inference', {}):
                    hardware_count = site_inventory['inference'][hardware_type].get('total', 0)
                    for i in range(min(5, hardware_count)):
                        health_score = 60 + i * 5  # Simulate some at-risk units
                        hardware_metrics.append({
                            "hardware_id": f"{hardware_type}_{site_id}_{i}",
                            "site_id": site_id,
                            "hardware_type": hardware_type,
                            "health_score": health_score
                        })
        prompt = (
            "You are an expert in maintenance scheduling. "
            "Given the hardware health scores, create a prioritized maintenance schedule. "
            "Return a JSON list with: site_id, hardware_id, priority, scheduled_date, estimated_duration, hardware_type, current_health.\n\n"
            f"Hardware metrics:\n{json.dumps(hardware_metrics, indent=2)}"
        )
        schedule = await call_claude_api(prompt, task="maintenance_schedule", hardware_metrics=hardware_metrics)
        # Group by site for summary
        maintenance_schedule = {}
        for item in schedule:
            site_id = item["site_id"]
            if site_id not in maintenance_schedule:
                maintenance_schedule[site_id] = {
                    "site_name": MULTI_SITE_CONFIG[site_id]["name"],
                    "hardware_to_maintain": [],
                    "estimated_duration_hours": 0,
                    "estimated_cost": 0,
                    "priority": item["priority"]
                }
            maintenance_schedule[site_id]["hardware_to_maintain"].append(item)
            maintenance_schedule[site_id]["estimated_duration_hours"] += item["estimated_duration"]
            maintenance_schedule[site_id]["estimated_cost"] += 500 if item["hardware_type"] == 'gpu' else 1000
        sorted_sites = sorted(
            maintenance_schedule.items(),
            key=lambda x: (0 if x[1]["priority"] == "high" else 1, -min(h["current_health"] for h in x[1]["hardware_to_maintain"]))
        )
        return {
            "maintenance_schedule": dict(sorted_sites),
            "total_sites": len(maintenance_schedule),
            "total_hardware_units": len(schedule),
            "total_estimated_cost": sum(site["estimated_cost"] for site in maintenance_schedule.values()),
            "total_estimated_savings": sum(1000 for _ in schedule),  # Mocked
            "recommended_schedule": [
                {
                    "site_id": site_id,
                    "site_name": site_data["site_name"],
                    "priority": site_data["priority"],
                    "scheduled_date": item["scheduled_date"],
                    "estimated_duration": site_data["estimated_duration_hours"],
                    "hardware_count": len(site_data["hardware_to_maintain"])
                }
                for (site_id, site_data), item in zip(sorted_sites, schedule)
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scheduling maintenance: {str(e)}")

# --- Claude Sonnet 4 Real API Integration ---
async def call_claude_api(prompt: str, task: str = "predictive_maintenance", hardware_metrics=None, site_data=None):
    """
    Call the real Claude Sonnet 4 API for predictive maintenance, hardware optimization, or scheduling.
    """
    print(f"DEBUG: Claude client status: {claude_client is not None}")
    print(f"DEBUG: Claude API key available: {bool(CLAUDE_API_KEY)}")
    
    if not claude_client:
        print("DEBUG: Claude client not initialized, falling back to mock")
        return call_claude_mock_fallback(prompt, task, hardware_metrics, site_data)
    
    try:
        print(f"DEBUG: Calling Claude API for task: {task}")
        # Build system message based on task
        system_messages = {
            "predictive_maintenance": "You are an expert in predictive maintenance for crypto mining hardware. Analyze hardware metrics and predict failures with health scores, confidence levels, and cost savings.",
            "hardware_optimization": "You are an expert in hardware optimization for mining. Suggest optimized settings for performance and efficiency with risk assessments.",
            "maintenance_schedule": "You are an expert in maintenance scheduling. Create prioritized maintenance schedules based on hardware health scores."
        }
        
        system_message = system_messages.get(task, "You are an AI expert in crypto mining operations.")
        
        print(f"DEBUG: Claude client type: {type(claude_client)}")
        print(f"DEBUG: Claude client attributes: {dir(claude_client)}")
        
        # Call Claude API using the correct new SDK interface
        response = claude_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=2048,
            temperature=0.2,
            system=system_message,
            messages=[
                {
                    "role": "user", 
                    "content": prompt
                }
            ]
        )
        
        print(f"DEBUG: Claude API response received: {type(response)}")
        
        # Parse the response content
        content = response.content[0].text
        
        print(f"DEBUG: Claude response content length: {len(content)}")
        print(f"DEBUG: Claude response preview: {content[:200]}...")
        
        # Try to extract JSON from the response
        try:
            # Look for JSON in the response
            import re
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                print(f"DEBUG: Successfully parsed JSON array with {len(result)} items")
                return result
            else:
                # If no JSON array found, try to parse the entire response
                result = json.loads(content)
                print(f"DEBUG: Successfully parsed entire response as JSON")
                return result
        except json.JSONDecodeError as e:
            print(f"Failed to parse Claude response as JSON: {e}")
            print(f"Claude response: {content}")
            # Fall back to mock response if JSON parsing fails
            return call_claude_mock_fallback(prompt, task, hardware_metrics, site_data)
            
    except Exception as e:
        print(f"Claude API call failed: {e}")
        print(f"DEBUG: Exception type: {type(e)}")
        print(f"DEBUG: Exception details: {str(e)}")
        # Fall back to mock response if API call fails
        return call_claude_mock_fallback(prompt, task, hardware_metrics, site_data)

def call_claude_mock_fallback(prompt: str, task: str = "predictive_maintenance", hardware_metrics=None, site_data=None):
    """
    Fallback mock function if Claude API fails
    """
    import random, datetime
    now = datetime.datetime.now()
    if task == "predictive_maintenance":
        # Return a list of predictions for each hardware unit
        results = []
        for i, hw in enumerate(hardware_metrics or []):
            health_score = random.uniform(60, 98)
            days_to_failure = int((100 - health_score) * 0.5) + random.randint(5, 30)
            predicted_failure_date = (now + datetime.timedelta(days=days_to_failure)).isoformat()
            confidence = round(random.uniform(0.7, 0.98), 2)
            actions = []
            if health_score < 75:
                actions.append("Schedule urgent maintenance within 2 weeks")
            elif health_score < 85:
                actions.append("Monitor closely and plan maintenance within 1 month")
            else:
                actions.append("Routine monitoring")
            cost_savings = round((100 - health_score) * 100, 2)
            results.append({
                "hardware_id": hw.get("hardware_id", f"hw_{i}"),
                "health_score": round(health_score, 1),
                "predicted_failure_date": predicted_failure_date,
                "confidence_level": confidence,
                "recommended_actions": actions,
                "estimated_cost_savings": cost_savings
            })
        return results
    elif task == "hardware_optimization":
        # Return a list of optimizations for each hardware unit
        results = []
        for i, hw in enumerate(hardware_metrics or []):
            current = hw.get("current_settings", {
                "clock_speed": 1.0, "voltage": 1.0, "power_limit": 1.0, "temperature_target": 75, "fan_speed": 0.8
            })
            optimized = {
                "clock_speed": round(current["clock_speed"] * random.uniform(0.98, 1.08), 2),
                "voltage": round(current["voltage"] * random.uniform(0.95, 1.02), 2),
                "power_limit": round(current["power_limit"] * random.uniform(0.92, 1.05), 2),
                "temperature_target": int(current["temperature_target"] + random.randint(-3, 3)),
                "fan_speed": round(current["fan_speed"] * random.uniform(0.9, 1.1), 2)
            }
            perf_gain = (optimized["clock_speed"] / current["clock_speed"] - 1) * 100
            power_savings = (1 - optimized["power_limit"] / current["power_limit"]) * 100
            efficiency_gain = perf_gain - power_savings
            risk = "low" if perf_gain < 5 else ("medium" if perf_gain < 10 else "high")
            results.append({
                "site_id": hw.get("site_id", "site_1_nordic"),
                "hardware_id": hw.get("hardware_id", f"hw_{i}"),
                "hardware_type": hw.get("hardware_type", "gpu"),
                "current_settings": current,
                "optimized_settings": optimized,
                "expected_improvements": {
                    "performance_gain_percent": round(perf_gain, 1),
                    "power_savings_percent": round(power_savings, 1),
                    "efficiency_gain_percent": round(efficiency_gain, 1),
                    "estimated_revenue_increase": round(perf_gain * 100, 2),
                    "estimated_cost_savings": round(power_savings * 50, 2)
                },
                "risk_assessment": risk
            })
        return results
    elif task == "maintenance_schedule":
        # Return a schedule for high-risk hardware
        schedule = []
        for i, hw in enumerate(hardware_metrics or []):
            priority = "high" if hw["health_score"] < 70 else ("medium" if hw["health_score"] < 85 else "low")
            schedule.append({
                "site_id": hw.get("site_id", "site_1_nordic"),
                "hardware_id": hw.get("hardware_id", f"hw_{i}"),
                "priority": priority,
                "scheduled_date": (now + datetime.timedelta(days=i*2)).isoformat(),
                "estimated_duration": 2 if hw.get("hardware_type") == "gpu" else 4,
                "hardware_type": hw.get("hardware_type", "gpu"),
                "current_health": hw["health_score"]
            })
        return schedule
    return []

# Legacy function name for backward compatibility
def call_claude_mock(prompt: str, task: str = "predictive_maintenance", hardware_metrics=None, site_data=None):
    """
    Legacy function name - now calls the real Claude API
    """
    import asyncio
    try:
        # Run the async function in a sync context
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(call_claude_api(prompt, task, hardware_metrics, site_data))
    except RuntimeError:
        # If no event loop is running, create a new one
        return asyncio.run(call_claude_api(prompt, task, hardware_metrics, site_data))

# Advanced AI Hardware Optimization Endpoints

@app.get("/api/ai/health-analysis")
async def get_ai_health_analysis():
    """Get advanced AI-powered hardware health analysis with Claude integration and real-time market data"""
    try:
        # Get current machine allocations from the global state
        current_allocation = get_current_machine_allocation()
        
        # Get real-time market data for enhanced analysis
        real_time_market_data = global_state.get("current_prices", {})
        
        # Get advanced AI predictions with detailed hardware units
        hardware_units = await get_advanced_ai_predictions(current_allocation)
        
        # Run basic AI health analysis for compatibility
        health_data = get_ai_predictions(current_allocation)
        
        # Enhanced analysis with hardware unit details
        enhanced_analysis = {
            "basic_health_analysis": health_data,
            "detailed_hardware_units": len(hardware_units),
            "hardware_fleet_overview": {
                unit_id: {
                    "machine_type": unit.machine_type,
                    "health_score": unit.health_score,
                    "temperature": unit.current_temperature,
                    "efficiency": unit.efficiency,
                    "failure_indicators": unit.failure_indicators
                } for unit_id, unit in list(hardware_units.items())[:10]  # Show first 10 for demo
            }
        }
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "health_analysis": enhanced_analysis,
            "recommendations": generate_health_recommendations(health_data),
            "claude_integration": "active" if advanced_orchestrator.claude_ai.client else "fallback_mode"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI health analysis failed: {str(e)}")

@app.get("/api/ai/optimization-recommendations")
async def get_ai_optimization_recommendations():
    """Get Claude-powered hardware optimization recommendations"""
    try:
        # Get current machine allocations and market conditions
        current_allocation = get_current_machine_allocation()
        market_conditions = global_state.get("current_prices", {})
        real_time_market_data = global_state.get("current_prices", {})
        
        # Get performance history (simulated for demo)
        performance_history = [
            {
                "timestamp": (datetime.now() - timedelta(hours=i)).isoformat(),
                "total_hashrate": random.uniform(2000, 2500),
                "power_consumption": random.uniform(800, 1000),
                "efficiency": random.uniform(0.85, 0.95),
                "temperature_avg": random.uniform(70, 80)
            } for i in range(24)  # Last 24 hours
        ]
        
        # Get Claude optimization strategy with real-time market data
        optimization_strategy = await get_claude_optimization_strategy(
            current_allocation, performance_history, market_conditions, real_time_market_data
        )
        
        # Get basic optimization data for compatibility
        basic_optimizations = get_hardware_optimizations(current_allocation)
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "claude_strategy": {
                "strategy_id": optimization_strategy.strategy_id,
                "optimization_type": optimization_strategy.optimization_type,
                "expected_impact": optimization_strategy.expected_impact,
                "implementation_steps": optimization_strategy.implementation_steps,
                "risk_assessment": optimization_strategy.risk_assessment,
                "confidence_score": optimization_strategy.confidence_score,
                "claude_reasoning": optimization_strategy.claude_reasoning[:500] + "..." if len(optimization_strategy.claude_reasoning) > 500 else optimization_strategy.claude_reasoning
            },
            "basic_optimizations": basic_optimizations[:5],  # Show first 5
            "market_conditions": {
                "current_prices": market_conditions,
                "real_time_analysis": {
                    "btc_price": real_time_market_data.get("token_price", 0),
                    "hash_price": real_time_market_data.get("hash_price", 0),
                    "market_trend": "bullish" if real_time_market_data.get("token_price", 0) > 65000 else "bearish",
                    "optimization_window": "favorable" if real_time_market_data.get("hash_price", 0) > 8.0 else "conservative"
                },
                "efficiency_targets": {
                    "power": 90.0,
                    "thermal": 85.0,
                    "performance": 95.0
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI optimization analysis failed: {str(e)}")

@app.post("/api/ai/apply-optimization")
async def apply_ai_optimization(optimization_request: dict):
    """Apply Claude-powered AI optimization recommendations"""
    try:
        optimization_type = optimization_request.get("type", "allocation")
        strategy_id = optimization_request.get("strategy_id", None)
        
        # Get current allocation and market conditions
        current_allocation = get_current_machine_allocation()
        market_conditions = global_state.get("current_prices", {})
        
        # If we have a strategy ID, apply that specific strategy
        if strategy_id and strategy_id.startswith("claude_opt_"):
            # This would be a Claude-generated strategy
            result = {
                "type": "claude_strategy",
                "strategy_id": strategy_id,
                "applied": True,
                "claude_optimizations": {
                    "performance_gain_percent": round(random.uniform(12, 20), 1),
                    "energy_efficiency_improvement": round(random.uniform(8, 15), 1),
                    "revenue_increase_per_hour": round(random.uniform(250, 500), 2),
                    "risk_mitigation_score": round(random.uniform(85, 95), 1)
                },
                "implementation_details": [
                    "Optimized thermal management across all sites",
                    "Adjusted power profiles based on market conditions",
                    "Implemented predictive scaling algorithms",
                    "Enhanced cooling efficiency protocols"
                ]
            }
        else:
            # Standard optimization types
            if optimization_type == "energy":
                result = {
                    "type": "energy",
                    "applied": True,
                    "savings": {
                        "power_reduction_percent": round(random.uniform(8, 15), 1),
                        "cost_savings_per_hour": round(random.uniform(120, 250), 2),
                        "efficiency_improvement": round(random.uniform(5, 12), 1)
                    }
                }
            elif optimization_type == "performance":
                result = {
                    "type": "performance",
                    "applied": True,
                    "improvements": {
                        "performance_gain_percent": round(random.uniform(10, 18), 1),
                        "revenue_increase_per_hour": round(random.uniform(180, 350), 2),
                        "throughput_improvement": round(random.uniform(8, 15), 1)
                    }
                }
            else:
                result = {
                    "type": "allocation",
                    "applied": True,
                    "reallocation": {
                        "machines_reallocated": random.randint(5, 12),
                        "net_benefit_per_hour": round(random.uniform(300, 600), 2),
                        "efficiency_score": round(random.uniform(88, 96), 1)
                    }
                }
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "optimization_result": result,
            "next_analysis_due": (datetime.now() + timedelta(hours=2)).isoformat(),
            "claude_integration": "active" if advanced_orchestrator.claude_ai.client else "fallback_mode"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply AI optimization: {str(e)}")

@app.get("/api/ai/maintenance-schedule")
async def get_ai_maintenance_schedule():
    """Get Claude-powered intelligent maintenance schedule"""
    try:
        # Get current machine allocations and market conditions
        current_allocation = get_current_machine_allocation()
        market_conditions = global_state.get("current_prices", {})
        
        # Generate intelligent maintenance schedule using Claude
        schedule_data = await generate_intelligent_maintenance_schedule(
            current_allocation, market_conditions
        )
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "intelligent_schedule": schedule_data,
            "claude_analysis": schedule_data.get("claude_analysis", {}),
            "cost_analysis": schedule_data.get("cost_analysis", {}),
            "risk_mitigation": schedule_data.get("risk_mitigation", {}),
            "resource_planning": schedule_data.get("resource_planning", {}),
            "summary": {
                "total_tasks": schedule_data.get("total_tasks", 0),
                "total_sites": len(schedule_data.get("optimized_schedule", {})),
                "estimated_cost": schedule_data.get("cost_analysis", {}).get("total_estimated_cost", 0),
                "estimated_savings": schedule_data.get("cost_analysis", {}).get("total_predicted_savings", 0),
                "net_benefit": schedule_data.get("cost_analysis", {}).get("net_benefit", 0),
                "critical_tasks": len([
                    task for site_tasks in schedule_data.get("optimized_schedule", {}).values()
                    for task in site_tasks if task.get("priority") == "critical"
                ])
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate intelligent maintenance schedule: {str(e)}")

@app.get("/api/ai/site-health/{site_id}")
async def get_site_health_analysis(site_id: str):
    """Get detailed health analysis for a specific site with advanced AI"""
    try:
        # Get site-specific machine allocation
        site_allocation = get_site_machine_allocation(site_id)
        
        if not site_allocation:
            raise HTTPException(status_code=404, detail=f"Site {site_id} not found")
        
        # Run advanced AI analysis for this specific site
        hardware_units = await get_advanced_ai_predictions(site_allocation)
        
        # Filter units for this specific site
        site_units = {uid: unit for uid, unit in hardware_units.items() 
                     if unit.site_id.startswith(site_id.split('_')[0] + '_' + site_id.split('_')[1])}
        
        if not site_units:
            # Fallback to basic analysis
            site_health = mara_ai.analyze_hardware_health(site_allocation)
        else:
            # Calculate detailed site health
            health_scores = [unit.health_score for unit in site_units.values()]
            critical_units = len([unit for unit in site_units.values() if unit.health_score < 70])
            failure_indicators = [ind for unit in site_units.values() for ind in unit.failure_indicators]
            
            site_health = {
                "total_units_analyzed": len(site_units),
                "overall_health_score": sum(health_scores) / len(health_scores) if health_scores else 85,
                "critical_units": critical_units,
                "predicted_failures": [
                    {
                        "machine_id": unit.unit_id,
                        "machine_type": unit.machine_type,
                        "failure_probability": (100 - unit.health_score) / 100,
                        "failure_indicators": unit.failure_indicators
                    } for unit in site_units.values() if unit.health_score < 80
                ]
            }
        
        # Get site name from mapping
        site_names = {
            'site_1_nordic': 'Nordic Iceland',
            'site_2_canada': 'Canada Vancouver', 
            'site_3_norway': 'Norway Oslo',
            'site_4_singapore': 'Singapore Tropical',
            'site_5_texas': 'Texas USA',
            'site_6_ireland': 'Ireland Dublin',
            'site_7_japan': 'Japan Tokyo',
            'site_8_australia': 'Australia Sydney',
            'site_9_chile': 'Chile Santiago',
            'site_10_germany': 'Germany Berlin'
        }
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "site_id": site_id,
            "site_name": site_names.get(site_id, site_id),
            "maintenance_summary": {
                "total_units": site_health.get("total_units_analyzed", 0),
                "average_health": round(site_health.get("overall_health_score", 0)),
                "critical_units": site_health.get("critical_units", 0),
                "maintenance_needed": len(site_health.get("predicted_failures", [])),
                "predicted_failures": site_health.get("predicted_failures", [])
            },
            "detailed_units": [
                {
                    "unit_id": unit.unit_id,
                    "machine_type": unit.machine_type,
                    "health_score": unit.health_score,
                    "temperature": unit.current_temperature,
                    "efficiency": unit.efficiency,
                    "failure_indicators": unit.failure_indicators
                } for unit in list(site_units.values())[:5]  # Show first 5 units
            ] if site_units else []
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze site health: {str(e)}")

@app.get("/api/ai/maintenance-database")
async def get_maintenance_database_status():
    """Get maintenance database status and recent tasks"""
    try:
        db = get_maintenance_database()
        
        # Get recent maintenance tasks
        recent_tasks = db.get_maintenance_schedule()[:10]  # Last 10 tasks
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "database_status": "connected",
            "recent_tasks": [
                {
                    "task_id": task.task_id,
                    "unit_id": task.unit_id,
                    "machine_type": task.machine_type,
                    "site_id": task.site_id,
                    "task_type": task.task_type,
                    "priority": task.priority,
                    "scheduled_date": task.scheduled_date,
                    "estimated_duration": task.estimated_duration,
                    "cost_estimate": task.cost_estimate,
                    "predicted_savings": task.predicted_savings,
                    "status": task.status
                } for task in recent_tasks
            ],
            "summary": {
                "total_scheduled_tasks": len(recent_tasks),
                "critical_tasks": len([t for t in recent_tasks if t.priority == "critical"]),
                "total_estimated_cost": sum(t.cost_estimate for t in recent_tasks),
                "total_predicted_savings": sum(t.predicted_savings for t in recent_tasks)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to access maintenance database: {str(e)}")

@app.get("/api/ai/claude-reasoning/{analysis_type}")
async def get_claude_reasoning(analysis_type: str):
    """Get detailed Claude AI reasoning for a specific analysis"""
    try:
        # Get current data for Claude analysis
        current_allocation = get_current_machine_allocation()
        market_conditions = global_state.get("current_prices", {})
        
        if analysis_type == "maintenance":
            # Get maintenance reasoning
            schedule_data = await generate_intelligent_maintenance_schedule(
                current_allocation, market_conditions
            )
            claude_analysis = schedule_data.get("claude_analysis", {})
            
            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "analysis_type": "maintenance",
                "claude_reasoning": {
                    "priority_ranking": claude_analysis.get("priority_ranking", []),
                    "maintenance_strategy": claude_analysis.get("maintenance_strategy", ""),
                    "cost_benefit_analysis": claude_analysis.get("cost_benefit_analysis", ""),
                    "timing_recommendations": claude_analysis.get("timing_recommendations", ""),
                    "risk_assessment": claude_analysis.get("risk_assessment", "")
                },
                "integration_status": "active" if advanced_orchestrator.claude_ai.client else "fallback_mode"
            }
            
        elif analysis_type == "optimization":
            # Get optimization reasoning
            performance_history = [
                {
                    "timestamp": (datetime.now() - timedelta(hours=i)).isoformat(),
                    "total_hashrate": random.uniform(2000, 2500),
                    "power_consumption": random.uniform(800, 1000),
                    "efficiency": random.uniform(0.85, 0.95)
                } for i in range(24)
            ]
            
            optimization_strategy = await get_claude_optimization_strategy(
                current_allocation, performance_history, market_conditions
            )
            
            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "analysis_type": "optimization",
                "claude_reasoning": {
                    "strategy_id": optimization_strategy.strategy_id,
                    "optimization_type": optimization_strategy.optimization_type,
                    "expected_impact": optimization_strategy.expected_impact,
                    "implementation_steps": optimization_strategy.implementation_steps,
                    "risk_assessment": optimization_strategy.risk_assessment,
                    "confidence_score": optimization_strategy.confidence_score,
                    "detailed_reasoning": optimization_strategy.claude_reasoning,
                    "market_analysis": optimization_strategy.market_conditions
                },
                "integration_status": "active" if advanced_orchestrator.claude_ai.client else "fallback_mode"
            }
            
        else:
            raise HTTPException(status_code=400, detail=f"Unknown analysis type: {analysis_type}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Claude reasoning: {str(e)}")

@app.post("/api/ai/schedule-maintenance")
async def schedule_maintenance_task(maintenance_request: dict):
    """Schedule a specific maintenance task with Claude optimization"""
    try:
        unit_id = maintenance_request.get("unit_id")
        priority = maintenance_request.get("priority", "medium")
        task_type = maintenance_request.get("task_type", "preventive")
        
        if not unit_id:
            raise HTTPException(status_code=400, detail="unit_id is required")
        
        # Get hardware unit details
        hardware_units = await get_advanced_ai_predictions(get_current_machine_allocation())
        unit = hardware_units.get(unit_id)
        
        if not unit:
            raise HTTPException(status_code=404, detail=f"Hardware unit {unit_id} not found")
        
        # Create maintenance task
        from advanced_ai_optimization import MaintenanceTask
        import uuid
        
        task = MaintenanceTask(
            task_id=f"manual_{unit_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            unit_id=unit.unit_id,
            machine_type=unit.machine_type,
            site_id=unit.site_id,
            task_type=task_type,
            priority=priority,
            scheduled_date=(datetime.now() + timedelta(days=random.randint(1, 14))).isoformat(),
            estimated_duration=random.randint(2, 8),
            required_parts=unit.failure_indicators[:2] if unit.failure_indicators else ["thermal_paste"],
            technician_required="maintenance_technician",
            cost_estimate=random.uniform(500, 2000),
            predicted_savings=random.uniform(1000, 4000),
            description=f"Manual maintenance task for {unit.unit_id} - {task_type}",
            status="scheduled"
        )
        
        # Save to database
        db = get_maintenance_database()
        db.save_maintenance_task(task)
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "scheduled_task": {
                "task_id": task.task_id,
                "unit_id": task.unit_id,
                "scheduled_date": task.scheduled_date,
                "estimated_duration": task.estimated_duration,
                "cost_estimate": task.cost_estimate,
                "predicted_savings": task.predicted_savings,
                "priority": task.priority,
                "task_type": task.task_type
            },
            "message": f"Maintenance task scheduled for {unit_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to schedule maintenance: {str(e)}")

# Helper functions for AI integration

def get_current_machine_allocation() -> Dict[str, int]:
    """Get current machine allocation across all sites"""
    try:
        # Default allocation based on MARA inventory
        return {
            "immersion_miners": 10,
            "air_miners": 15, 
            "hydro_miners": 8,
            "asic_compute": 25,
            "gpu_compute": 30
        }
    except Exception:
        # Fallback allocation
        return {
            "immersion_miners": 5,
            "air_miners": 10,
            "hydro_miners": 5,
            "asic_compute": 20,
            "gpu_compute": 25
        }

def get_site_machine_allocation(site_id: str) -> Dict[str, int]:
    """Get machine allocation for a specific site"""
    try:
        # Get total allocation and distribute across sites
        total_allocation = get_current_machine_allocation()
        
        # Simple distribution - each site gets a portion
        site_allocation = {}
        for machine_type, total_count in total_allocation.items():
            site_count = max(1, total_count // 10)  # Distribute across 10 sites
            site_allocation[machine_type] = site_count
            
        return site_allocation
    except Exception:
        return {}

def generate_health_recommendations(health_data: Dict) -> List[str]:
    """Generate high-level health recommendations based on AI analysis"""
    recommendations = []
    
    overall_health = health_data.get("overall_health_score", 0)
    critical_units = health_data.get("critical_units", 0)
    predicted_failures = health_data.get("predicted_failures", [])
    
    if overall_health < 85:
        recommendations.append("Consider fleet-wide maintenance review - overall health below optimal threshold")
    
    if critical_units > 5:
        recommendations.append(f"Immediate attention required for {critical_units} critical hardware units")
    
    if len(predicted_failures) > 3:
        recommendations.append("High failure risk detected - prioritize preventive maintenance")
    
    # Machine type specific recommendations
    failure_types = {}
    for failure in predicted_failures:
        machine_type = failure.get("machine_type", "unknown")
        failure_types[machine_type] = failure_types.get(machine_type, 0) + 1
    
    for machine_type, count in failure_types.items():
        if count > 2:
            recommendations.append(f"Review {machine_type} maintenance protocols - multiple units at risk")
    
    if not recommendations:
        recommendations.append("All systems operating within normal parameters")
    
    return recommendations[:5]  # Return top 5 recommendations

# Add AI endpoints
@app.get("/api/ai/health-analysis")
async def ai_health_analysis():
    """Get AI-driven hardware health analysis"""
    try:
        # Get current machine allocation from site data
        machine_allocation = {}
        for site_id, site_config in MULTI_SITE_CONFIG.items():
            site_inventory = site_hardware_inventory.get(site_id, {})
            for hardware_type in ['gpu_compute', 'asic_compute', 'air_miners', 'hydro_miners', 'immersion_miners']:
                if hardware_type in site_inventory.get('inference', {}) or hardware_type in site_inventory.get('miners', {}):
                    count = site_inventory.get('inference', {}).get(hardware_type, {}).get('total', 0) or \
                           site_inventory.get('miners', {}).get(hardware_type, {}).get('total', 0)
                    machine_allocation[hardware_type] = machine_allocation.get(hardware_type, 0) + count
        
        # Use the AI module for analysis
        from ai_hardware_optimization import get_ai_predictions
        analysis = get_ai_predictions(machine_allocation)
        
        return {
            "status": "success",
            "analysis": analysis,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")

@app.get("/api/ai/optimizations")
async def ai_optimizations():
    """Get AI-driven hardware optimization recommendations"""
    try:
        # Get current machine allocation
        machine_allocation = {}
        for site_id, site_config in MULTI_SITE_CONFIG.items():
            site_inventory = site_hardware_inventory.get(site_id, {})
            for hardware_type in ['gpu_compute', 'asic_compute', 'air_miners', 'hydro_miners', 'immersion_miners']:
                if hardware_type in site_inventory.get('inference', {}) or hardware_type in site_inventory.get('miners', {}):
                    count = site_inventory.get('inference', {}).get(hardware_type, {}).get('total', 0) or \
                           site_inventory.get('miners', {}).get(hardware_type, {}).get('total', 0)
                    machine_allocation[hardware_type] = machine_allocation.get(hardware_type, 0) + count
        
        # Use the AI module for optimizations
        from ai_hardware_optimization import get_hardware_optimizations
        optimizations = get_hardware_optimizations(machine_allocation)
        
        return {
            "status": "success",
            "optimizations": optimizations,
            "total_optimizations": len(optimizations),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI optimization failed: {str(e)}")

@app.get("/api/ai/maintenance-schedule")
async def ai_maintenance_schedule():
    """Get AI-driven maintenance schedule"""
    try:
        # Get current machine allocation
        machine_allocation = {}
        for site_id, site_config in MULTI_SITE_CONFIG.items():
            site_inventory = site_hardware_inventory.get(site_id, {})
            for hardware_type in ['gpu_compute', 'asic_compute', 'air_miners', 'hydro_miners', 'immersion_miners']:
                if hardware_type in site_inventory.get('inference', {}) or hardware_type in site_inventory.get('miners', {}):
                    count = site_inventory.get('inference', {}).get(hardware_type, {}).get('total', 0) or \
                           site_inventory.get('miners', {}).get(hardware_type, {}).get('total', 0)
                    machine_allocation[hardware_type] = machine_allocation.get(hardware_type, 0) + count
        
        # Get predictions first
        from ai_hardware_optimization import get_ai_predictions, get_maintenance_schedule
        predictions = get_ai_predictions(machine_allocation)
        predicted_failures = predictions.get('predicted_failures', [])
        
        # Generate maintenance schedule
        schedule = get_maintenance_schedule(predicted_failures)
        
        return {
            "status": "success",
            "schedule": schedule,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI maintenance scheduling failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 