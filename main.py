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
import re

# Import database module
from database import sla_db

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
    custom_asic_price: Optional[float] = None  # Custom price per ASIC per hour for competitive pricing

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
        
        # Get current market prices for profitability analysis
        current_prices = global_state.get("current_prices", {})
        hash_price = current_prices.get("hash_price", 8.5)
        token_price = current_prices.get("token_price", 2.9)
        energy_price = current_prices.get("energy_price", 0.65)
        
        # Calculate mining vs AI inference profitability
        mara_inventory = global_state.get("mara_inventory", {})
        
        # Mining profitability per unit
        mining_revenue_per_unit = hash_price * 1000  # hashrate * hash_price
        mining_power_cost_per_unit = energy_price * 3.5  # 3.5kW average power consumption
        mining_profit_margin = ((mining_revenue_per_unit - mining_power_cost_per_unit) / mining_revenue_per_unit) * 100
        
        # AI inference profitability per unit  
        ai_revenue_per_unit = token_price * 1000  # tokens * token_price
        ai_power_cost_per_unit = energy_price * 5.0  # 5kW average power consumption
        ai_profit_margin = ((ai_revenue_per_unit - ai_power_cost_per_unit) / ai_revenue_per_unit) * 100
        
        # Market analysis summary
        market_analysis = f"""
        CURRENT MARKET CONDITIONS (Real-time MARA API):
        - Hash Price: ${hash_price:.2f} (Bitcoin mining revenue per TH/s)
        - Token Price: ${token_price:.2f} (AI inference revenue per token)
        - Energy Price: ${energy_price:.2f} per kWh
        
        PROFITABILITY ANALYSIS:
        - Bitcoin Mining Profit Margin: {mining_profit_margin:.1f}%
        - AI Inference Profit Margin: {ai_profit_margin:.1f}%
        - Optimal Strategy: {'AI Inference' if ai_profit_margin > mining_profit_margin else 'Bitcoin Mining' if mining_profit_margin > 0 else 'Minimal Operations'}
        
        ARBITRAGE OPPORTUNITY: {abs(ai_profit_margin - mining_profit_margin):.1f}% profit difference between workloads
        """
        
        # Prepare comprehensive site data for Claude
        site_summary = []
        for site_id, site in site_data.items():
            site_config = MULTI_SITE_CONFIG[site_id]
            
            # Calculate site-specific profitability
            site_energy_multiplier = site_config['energy_cost_multiplier']
            site_mining_profit = mining_profit_margin - (site_energy_multiplier - 1) * 20  # Adjust for local energy costs
            site_ai_profit = ai_profit_margin - (site_energy_multiplier - 1) * 15
            
            site_summary.append(f"""
            {site['name']} ({site_id}):
            - Temperature: {site['weather']['temperature']:.1f}°F (Cooling: {site['cooling_efficiency']:.1%})
            - Energy Cost Multiplier: {site_energy_multiplier}x (${energy_price * site_energy_multiplier:.3f}/kWh)
            - Renewable Energy: {site_config['climate']['renewable_energy']:.1%}
            - Local Time: {site.get('local_time', 'N/A')} (Demand: {calculate_demand_multiplier(site_config['location']['timezone']):.2f}x)
            - Current Revenue: ${site.get('revenue', 0):,.2f}
            - Power Used: {site.get('power_used', 0):,} MW
            - Site Mining Profitability: {site_mining_profit:.1f}%
            - Site AI Profitability: {site_ai_profit:.1f}%
            - Optimal Workload: {'AI Inference' if site_ai_profit > site_mining_profit else 'Bitcoin Mining' if site_mining_profit > 0 else 'Reduce Operations'}
            """)
        
        # Real Claude API call with enhanced market context
        message = claude_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1500,
            temperature=0.3,
            messages=[{
                "role": "user",
                "content": f"""
                You are an AI optimization expert managing a global network of 10 data centers for energy arbitrage between Bitcoin mining and AI inference services.

                {market_analysis}

                CURRENT SITE CONDITIONS:
                {chr(10).join(site_summary)}

                CURRENT SLA COMMITMENTS:
                - Premium (99.9% uptime): {sla_commitments.get('premium', 0)} MW
                - Standard (95% uptime): {sla_commitments.get('standard', 0)} MW  
                - Flexible (90% uptime): {sla_commitments.get('flexible', 0)} MW
                - Spot (best effort): {sla_commitments.get('spot', 0)} MW

                CRITICAL OPTIMIZATION DECISIONS NEEDED:
                1. **Profitability Arbitrage**: Should we shift from Bitcoin mining to AI inference based on current margins?
                2. **Geographic Arbitrage**: Which sites have the best profit margins after accounting for energy costs?
                3. **Climate Arbitrage**: How can we leverage cooling efficiency differences for maximum profit?
                4. **Timezone Arbitrage**: Which sites are in peak demand periods for AI inference?
                5. **Energy Arbitrage**: Should we reduce operations at high-cost sites?

                PROVIDE SPECIFIC RECOMMENDATIONS:
                - For each site, specify exact allocation percentages between Bitcoin mining and AI inference
                - Identify which sites should prioritize AI inference based on current token prices
                - Recommend which sites should reduce Bitcoin mining if unprofitable
                - Suggest optimal SLA tier routing based on profitability and efficiency
                - Include specific percentage allocations (e.g., "Nordic Iceland: 70% AI inference, 30% Bitcoin mining")

                Make data-driven decisions based on the real profitability numbers provided above.
                """
            }]
        )
        
        return message.content[0].text if message.content else "Claude optimization completed but no response received"
        
    except Exception as e:
        return f"Claude optimization error: {e}. Using fallback strategy based on cooling efficiency and energy costs."

def distribute_hardware_across_sites(mara_inventory: Dict) -> Dict:
    """Distribute MARA's hardware inventory across 10 sites based on their profiles"""
    
    # Total hardware to distribute (increased realistic quantities for better capacity)
    total_hardware = {
        "miners": {
            "air": 2000,      # 2000 air miners total (increased from 500)
            "hydro": 1000,    # 1000 hydro miners total (increased from 200)
            "immersion": 500  # 500 immersion miners total (increased from 100)
        },
        "inference": {
            "gpu": 5000,     # 5000 GPU units total (increased from 1000)
            "asic": 2000     # 2000 ASIC inference units total (increased from 300)
        }
    }
    
    site_inventories = {}
    
    for site_id, site_config in MULTI_SITE_CONFIG.items():
        gpu_ratio = site_config["hardware_profile"]["gpu_ratio"]
        asic_ratio = site_config["hardware_profile"]["asic_ratio"]
        cooling_efficiency = site_config["climate"]["cooling_efficiency"]
        
        # Distribute hardware based on site profile (increased allocation per site)
        site_inventories[site_id] = {
            "miners": {
                "air": {
                    "hashrate": mara_inventory["miners"]["air"]["hashrate"],
                    "power": mara_inventory["miners"]["air"]["power"],
                    "available": int(total_hardware["miners"]["air"] * 0.15)  # 15% per site (increased from 10%)
                },
                "hydro": {
                    "hashrate": mara_inventory["miners"]["hydro"]["hashrate"],
                    "power": mara_inventory["miners"]["hydro"]["power"],
                    "available": int(total_hardware["miners"]["hydro"] * cooling_efficiency * 0.15)
                },
                "immersion": {
                    "hashrate": mara_inventory["miners"]["immersion"]["hashrate"],
                    "power": mara_inventory["miners"]["immersion"]["power"],
                    "available": int(total_hardware["miners"]["immersion"] * cooling_efficiency * 0.15)
                }
            },
            "inference": {
                "gpu": {
                    "tokens": mara_inventory["inference"]["gpu"]["tokens"],
                    "power": mara_inventory["inference"]["gpu"]["power"],
                    "available": int(total_hardware["inference"]["gpu"] * gpu_ratio * 0.15)  # 15% per site
                },
                "asic": {
                    "tokens": mara_inventory["inference"]["asic"]["tokens"],
                    "power": mara_inventory["inference"]["asic"]["power"],
                    "available": int(total_hardware["inference"]["asic"] * asic_ratio * 0.15)  # 15% per site
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
    
    # Implement Claude's optimization strategy
    total_revenue = 0
    climate_savings = 0
    
    for site_id, site_config in MULTI_SITE_CONFIG.items():
        # Get Claude's recommended allocation for this site
        claude_allocation = claude_allocations.get(site_id, {})
        
        # Apply Claude's recommendations or use intelligent fallback
        if claude_allocation:
            # Use Claude's specific recommendations
            gpu_allocation = claude_allocation.get("gpu_compute", 0)
            asic_allocation = claude_allocation.get("asic_compute", 0)
            mining_allocation = claude_allocation.get("mining_focus", 0)
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
        
        # Store allocation in global state
        global_state["site_allocations"][site_id] = {
            "gpu_compute": gpu_allocation,
            "asic_compute": asic_allocation,
            "air_miners": mining_allocation,
            "hydro_miners": mining_allocation // 2,
            "immersion_miners": mining_allocation // 4 if site_config["climate"]["cooling_efficiency"] > 0.8 else 0
        }
        
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
        
        # Parse percentage-based allocations from Claude's recommendations
        for line in lines:
            line = line.strip()
            
            # Look for specific percentage allocations
            for site_name, site_id in site_name_mapping.items():
                if site_name in line and '%' in line:
                    if site_id not in allocations:
                        allocations[site_id] = {}
                    
                    # Parse AI inference percentages
                    if 'ai inference' in line or 'ai workload' in line:
                        # Extract percentage numbers
                        import re
                        percentages = re.findall(r'(\d+)%', line)
                        if percentages:
                            ai_percentage = int(percentages[0])
                            # Convert percentage to allocation units
                            allocations[site_id]['gpu_compute'] = min(100, int(ai_percentage * 0.8))  # Scale to reasonable units
                            allocations[site_id]['ai_focus'] = ai_percentage
                    
                    # Parse Bitcoin mining percentages
                    elif 'bitcoin mining' in line or 'mining' in line:
                        import re
                        percentages = re.findall(r'(\d+)%', line)
                        if percentages:
                            mining_percentage = int(percentages[0])
                            allocations[site_id]['mining_focus'] = min(60, int(mining_percentage * 0.6))  # Scale to reasonable units
                            allocations[site_id]['asic_compute'] = min(50, int(mining_percentage * 0.5))
                    
                    # Parse "reduce operations" or "minimal operations"
                    elif 'reduce' in line or 'minimal' in line or 'shut down' in line:
                        allocations[site_id]['gpu_compute'] = 10  # Minimal AI operations
                        allocations[site_id]['mining_focus'] = 5   # Minimal mining
                        allocations[site_id]['asic_compute'] = 5
                        allocations[site_id]['operation_mode'] = 'reduced'
                    
                    # Parse "prioritize" or "focus on" recommendations
                    elif 'prioritize' in line or 'focus' in line:
                        if 'ai' in line or 'inference' in line:
                            allocations[site_id]['gpu_compute'] = 80  # High AI focus
                            allocations[site_id]['ai_focus'] = 70
                            allocations[site_id]['mining_focus'] = 20
                        elif 'mining' in line:
                            allocations[site_id]['mining_focus'] = 60  # High mining focus
                            allocations[site_id]['asic_compute'] = 40
                            allocations[site_id]['gpu_compute'] = 30
        
        # Enhanced parsing for market-driven decisions
        reasoning_lower = claude_reasoning.lower()
        
        # Look for overall market strategy recommendations
        if 'shift to ai inference' in reasoning_lower or 'ai inference more profitable' in reasoning_lower:
            # Apply AI-focused strategy to high-efficiency sites
            for site_id in ['site_1_nordic', 'site_3_norway', 'site_2_canada']:
                if site_id not in allocations:
                    allocations[site_id] = {}
                allocations[site_id]['gpu_compute'] = 85  # High AI allocation
                allocations[site_id]['ai_focus'] = 75
                allocations[site_id]['mining_focus'] = 25
                allocations[site_id]['strategy'] = 'ai_focused'
        
        elif 'bitcoin mining more profitable' in reasoning_lower or 'focus on mining' in reasoning_lower:
            # Apply mining-focused strategy to cost-effective sites
            for site_id in ['site_4_singapore', 'site_5_texas', 'site_9_chile']:
                if site_id not in allocations:
                    allocations[site_id] = {}
                allocations[site_id]['mining_focus'] = 70  # High mining allocation
                allocations[site_id]['asic_compute'] = 50
                allocations[site_id]['gpu_compute'] = 30
                allocations[site_id]['strategy'] = 'mining_focused'
        
        # Parse energy cost recommendations
        if 'high energy cost' in reasoning_lower or 'expensive energy' in reasoning_lower:
            # Reduce operations at high-cost sites
            high_cost_sites = ['site_4_singapore', 'site_7_japan']
            for site_id in high_cost_sites:
                if site_id not in allocations:
                    allocations[site_id] = {}
                allocations[site_id]['gpu_compute'] = 20  # Reduced operations
                allocations[site_id]['mining_focus'] = 15
                allocations[site_id]['asic_compute'] = 10
                allocations[site_id]['strategy'] = 'energy_conservation'
        
        # Parse cooling efficiency recommendations
        if 'cooling efficiency' in reasoning_lower or 'cold climate' in reasoning_lower:
            # Maximize operations at efficient sites
            efficient_sites = ['site_1_nordic', 'site_3_norway', 'site_2_canada']
            for site_id in efficient_sites:
                if site_id not in allocations:
                    allocations[site_id] = {}
                # Boost allocations for efficient sites
                current_gpu = allocations[site_id].get('gpu_compute', 60)
                current_mining = allocations[site_id].get('mining_focus', 30)
                allocations[site_id]['gpu_compute'] = min(100, current_gpu + 15)
                allocations[site_id]['mining_focus'] = min(60, current_mining + 10)
                allocations[site_id]['strategy'] = 'efficiency_maximized'
        
        # Apply specific site recommendations based on Claude's analysis
        site_specific_patterns = {
            'site_1_nordic': ['nordic iceland', 'iceland'],
            'site_3_norway': ['norway oslo', 'norway', 'oslo'],
            'site_2_canada': ['canada vancouver', 'vancouver', 'canada'],
            'site_6_ireland': ['ireland dublin', 'dublin', 'ireland'],
            'site_9_chile': ['chile santiago', 'santiago', 'chile'],
            'site_10_germany': ['germany berlin', 'berlin', 'germany'],
            'site_7_japan': ['japan tokyo', 'tokyo', 'japan'],
            'site_8_australia': ['australia sydney', 'sydney', 'australia'],
            'site_4_singapore': ['singapore'],
            'site_5_texas': ['texas', 'texas usa']
        }
        
        for site_id, patterns in site_specific_patterns.items():
            for pattern in patterns:
                if pattern in reasoning_lower:
                    if site_id not in allocations:
                        allocations[site_id] = {}
                    
                    # Look for specific recommendations near the site mention
                    site_context = reasoning_lower[max(0, reasoning_lower.find(pattern) - 200):reasoning_lower.find(pattern) + 200]
                    
                    if 'reduce' in site_context or 'minimal' in site_context:
                        allocations[site_id]['gpu_compute'] = 15
                        allocations[site_id]['mining_focus'] = 10
                        allocations[site_id]['operation_mode'] = 'reduced'
                    elif 'maximize' in site_context or 'increase' in site_context:
                        allocations[site_id]['gpu_compute'] = 90
                        allocations[site_id]['mining_focus'] = 50
                        allocations[site_id]['operation_mode'] = 'maximized'
                    elif 'ai' in site_context and 'focus' in site_context:
                        allocations[site_id]['gpu_compute'] = 80
                        allocations[site_id]['ai_focus'] = 70
                        allocations[site_id]['mining_focus'] = 30
                        allocations[site_id]['tier_focus'] = 'premium'
    
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
        
        # NEW: Competitive bid-based allocation for ASIC requests
        if remaining_capacity < sla_request.compute_units and sla_request.compute_type == 'asic' and sla_request.custom_asic_price is not None:
            # Check if we can displace Bitcoin mining with higher bid
            try:
                prices = global_state.get("current_prices", {})
                hash_price = prices.get("hash_price", 0.05)
                energy_price = prices.get("energy_price", 0.08)
                
                # Calculate Bitcoin mining profit per ASIC per hour at this site
                asic_hashrate = 100  # TH/s per ASIC
                site_energy_multiplier = site_config['energy_cost_multiplier']
                site_power_cost_per_hour = energy_price * site_energy_multiplier * 3.0  # 3kW per ASIC
                mining_revenue_per_hour = hash_price * asic_hashrate
                mining_profit_per_hour = mining_revenue_per_hour - site_power_cost_per_hour
                
                # If custom price beats mining profit, we can "displace" mining operations
                if sla_request.custom_asic_price > mining_profit_per_hour:
                    # Calculate how many ASICs we can theoretically displace from mining
                    total_asic_capacity = available_hardware  # Total ASICs at this site
                    
                    # We can use up to the total ASIC capacity if bid is competitive
                    if sla_request.compute_units <= total_asic_capacity:
                        remaining_capacity = total_asic_capacity - used_hardware
                        # Allow the request if we have enough total capacity (displacing mining)
                        if remaining_capacity >= sla_request.compute_units:
                            pass  # Continue with allocation
                        else:
                            # Even with displacement, not enough capacity
                            continue
                    else:
                        continue  # Request too large even with full displacement
                else:
                    # Bid not competitive enough to displace mining
                    continue
            except Exception as e:
                # If profitability calculation fails, fall back to standard capacity check
                if remaining_capacity < sla_request.compute_units:
                    continue
        elif remaining_capacity < sla_request.compute_units:
            # Standard capacity check for non-competitive bids
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
    
    # Initialize claude_bonus for all pricing types
    claude_bonus = 1.1 if optimal_site in preferred_sites else 1.0
    
    # Handle custom ASIC pricing vs standard pricing
    if sla_request.compute_type == 'asic' and sla_request.custom_asic_price is not None:
        # Use custom ASIC pricing - user is offering competitive rate
        custom_price_per_hour = sla_request.custom_asic_price
        
        # Get current Bitcoin mining profitability to validate the offer
        try:
            prices = global_state.get("current_prices", {})
            hash_price = prices.get("hash_price", 0.05)
            energy_price = prices.get("energy_price", 0.08)
            
            # Calculate Bitcoin mining profit per ASIC per hour at this site
            asic_hashrate = 100  # TH/s per ASIC
            site_energy_multiplier = site_config['energy_cost_multiplier']
            site_power_cost_per_hour = energy_price * site_energy_multiplier * 3.0  # 3kW per ASIC
            mining_revenue_per_hour = hash_price * asic_hashrate
            mining_profit_per_hour = mining_revenue_per_hour - site_power_cost_per_hour
            
            # Check if custom price beats mining profitability
            is_competitive = custom_price_per_hour > mining_profit_per_hour
            competitive_advantage = custom_price_per_hour - mining_profit_per_hour if is_competitive else 0
            
            # Calculate total revenue using custom pricing
            estimated_revenue = sla_request.compute_units * sla_request.duration_hours * custom_price_per_hour
            
            # Add competitive pricing details to SLA record
            pricing_details = {
                "custom_asic_pricing": True,
                "custom_price_per_hour": custom_price_per_hour,
                "mining_profit_per_hour": round(mining_profit_per_hour, 4),
                "is_competitive": is_competitive,
                "competitive_advantage": round(competitive_advantage, 4),
                "site_energy_cost_multiplier": site_energy_multiplier
            }
            
        except Exception as e:
            # Fallback if profitability calculation fails
            estimated_revenue = sla_request.compute_units * sla_request.duration_hours * custom_price_per_hour
            pricing_details = {
                "custom_asic_pricing": True,
                "custom_price_per_hour": custom_price_per_hour,
                "profitability_check_error": str(e)
            }
    else:
        # Use standard tier-based pricing
        base_rate = 100  # $100 per compute unit per hour
        tier_multiplier = SLA_TIERS[sla_request.tier]["price_multiplier"]
        efficiency_bonus = site_config["climate"]["cooling_efficiency"]
        
        estimated_revenue = (sla_request.compute_units * sla_request.duration_hours * 
                            base_rate * tier_multiplier * efficiency_bonus * claude_bonus)
        
        pricing_details = {
            "custom_asic_pricing": False,
            "base_rate": base_rate,
            "tier_multiplier": tier_multiplier,
            "efficiency_bonus": efficiency_bonus,
            "claude_bonus": claude_bonus
        }
    
    sla_record = {
        "sla_id": sla_id,
        "tier": sla_request.tier,
        "compute_type": sla_request.compute_type,
        "compute_units": sla_request.compute_units,
        "duration_hours": sla_request.duration_hours,
        "site_id": optimal_site,
        "created_at": datetime.now().isoformat(),
        "expires_at": expiration_time.isoformat(),
        "estimated_revenue": estimated_revenue,
        "status": "active",
        "claude_optimized": optimal_site in preferred_sites,
        "pricing_details": pricing_details
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
        "pricing_details": pricing_details,
        # NEW: Add capacity and displacement information
        "capacity_info": {
            "site_total_capacity": site_hardware_inventory.get(optimal_site, {}).get("inference", {}).get(sla_request.compute_type, {}).get("available", 0),
            "units_allocated": sla_request.compute_units,
            "competitive_displacement": sla_request.compute_type == 'asic' and sla_request.custom_asic_price is not None and pricing_details.get("is_competitive", False),
            "displacement_details": f"Displaced Bitcoin mining operations with {pricing_details.get('competitive_advantage', 0):.2f}$/hr advantage" if sla_request.compute_type == 'asic' and sla_request.custom_asic_price is not None and pricing_details.get("is_competitive", False) else None
        }
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
        
        # Basic pricing details for fallback
        pricing_details = {
            "custom_asic_pricing": sla_request.compute_type == 'asic' and sla_request.custom_asic_price is not None,
            "custom_price_per_hour": sla_request.custom_asic_price if sla_request.compute_type == 'asic' and sla_request.custom_asic_price is not None else None,
            "is_competitive": False,  # Fallback doesn't do competitive analysis
            "competitive_advantage": 0
        }
        
        sla_record = {
            "sla_id": sla_id,
            "tier": sla_request.tier,
            "compute_type": sla_request.compute_type,
            "compute_units": sla_request.compute_units,
            "duration_hours": sla_request.duration_hours,
            "site_id": site_id,
            "created_at": datetime.now().isoformat(),
            "expires_at": expiration_time.isoformat(),
            "estimated_revenue": estimated_revenue,
            "status": "active",
            "claude_optimized": False,
            "pricing_details": pricing_details
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
            "pricing_details": pricing_details,
            "capacity_info": {
                "site_total_capacity": site_hardware_inventory.get(site_id, {}).get("inference", {}).get(sla_request.compute_type, {}).get("available", 0),
                "units_allocated": sla_request.compute_units,
                "competitive_displacement": False,  # Fallback doesn't do displacement
                "displacement_details": None
            }
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

def calculate_site_workload_allocation(site_id: str, site_inventory: Dict) -> Dict:
    """Calculate actual workload allocation based on active SLAs and idle mining"""
    if not site_inventory:
        return {"gpu_compute": 0, "asic_compute": 0, "air_miners": 0, "hydro_miners": 0, "immersion_miners": 0}
    
    # Get available hardware for this site
    available_gpus = site_inventory.get("inference", {}).get("gpu", {}).get("available", 0)
    available_asics = site_inventory.get("inference", {}).get("asic", {}).get("available", 0)
    available_air_miners = site_inventory.get("miners", {}).get("air", {}).get("available", 0)
    available_hydro_miners = site_inventory.get("miners", {}).get("hydro", {}).get("available", 0)
    available_immersion_miners = site_inventory.get("miners", {}).get("immersion", {}).get("available", 0)
    
    # Initialize allocation
    allocation = {
        "gpu_compute": 0,
        "asic_compute": 0, 
        "air_miners": 0,
        "hydro_miners": 0,
        "immersion_miners": 0
    }
    
    # First, allocate resources to active SLAs for this site
    site_slas = global_state["active_slas"].get(site_id, [])
    
    for sla in site_slas:
        compute_type = sla["compute_type"]
        compute_units = sla["compute_units"]
        
        if compute_type == "gpu" and allocation["gpu_compute"] + compute_units <= available_gpus:
            allocation["gpu_compute"] += compute_units
        elif compute_type == "asic" and allocation["asic_compute"] + compute_units <= available_asics:
            allocation["asic_compute"] += compute_units
        elif compute_type == "mixed":
            # Split mixed workload between GPU and ASIC
            gpu_units = compute_units // 2
            asic_units = compute_units - gpu_units
            
            if allocation["gpu_compute"] + gpu_units <= available_gpus:
                allocation["gpu_compute"] += gpu_units
            if allocation["asic_compute"] + asic_units <= available_asics:
                allocation["asic_compute"] += asic_units
    
    # Second, use remaining hardware for Bitcoin mining (idle mining)
    remaining_gpus = available_gpus - allocation["gpu_compute"]
    remaining_asics = available_asics - allocation["asic_compute"]
    
    # Idle Bitcoin mining allocation - use remaining compute for mining
    # Convert remaining inference hardware to mining equivalent
    if remaining_gpus > 0:
        # Use remaining GPUs for mining (less efficient but still profitable)
        allocation["air_miners"] = min(available_air_miners, remaining_gpus // 2)  # 2 GPUs per air miner equivalent
    
    if remaining_asics > 0:
        # Use remaining ASICs for mining (more efficient)
        allocation["hydro_miners"] = min(available_hydro_miners, remaining_asics // 3)  # 3 ASICs per hydro miner equivalent
    
    # Always run some baseline mining on dedicated miners
    allocation["air_miners"] = max(allocation["air_miners"], min(available_air_miners, available_air_miners // 2))
    allocation["hydro_miners"] = max(allocation["hydro_miners"], min(available_hydro_miners, available_hydro_miners // 2))
    allocation["immersion_miners"] = min(available_immersion_miners, available_immersion_miners // 3)  # Premium miners run less frequently
    
    return allocation

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

@app.get("/api/mining/profitability")
async def get_mining_profitability():
    """Get current Bitcoin mining profitability data for competitive ASIC pricing"""
    try:
        # Get current MARA pricing data
        prices = global_state.get("current_prices", {})
        if not prices:
            # Fallback to API call if not in global state
            prices = await get_mara_prices()
        
        hash_price = prices.get("hash_price", 0.05)  # Default $0.05 per TH/s
        energy_price = prices.get("energy_price", 0.08)  # Default $0.08 per kWh
        
        # Calculate ASIC mining profitability per unit per hour
        asic_hashrate = 100  # TH/s per ASIC (typical)
        asic_power_consumption = 3.0  # kW per ASIC
        
        # Revenue per ASIC per hour
        mining_revenue_per_hour = hash_price * asic_hashrate  # $/TH/s * TH/s = $/hour
        
        # Cost per ASIC per hour  
        power_cost_per_hour = energy_price * asic_power_consumption  # $/kWh * kW = $/hour
        
        # Net profit per ASIC per hour
        net_profit_per_hour = mining_revenue_per_hour - power_cost_per_hour
        profit_margin = ((net_profit_per_hour / mining_revenue_per_hour) * 100) if mining_revenue_per_hour > 0 else 0
        
        # Calculate site-specific profitability
        site_profitability = {}
        for site_id, site_config in MULTI_SITE_CONFIG.items():
            site_energy_multiplier = site_config['energy_cost_multiplier']
            site_energy_cost = energy_price * site_energy_multiplier
            site_power_cost_per_hour = site_energy_cost * asic_power_consumption
            site_net_profit = mining_revenue_per_hour - site_power_cost_per_hour
            site_profit_margin = ((site_net_profit / mining_revenue_per_hour) * 100) if mining_revenue_per_hour > 0 else 0
            
            site_profitability[site_id] = {
                "site_name": site_config["name"],
                "energy_cost_multiplier": site_energy_multiplier,
                "site_energy_cost_per_kwh": round(site_energy_cost, 4),
                "power_cost_per_hour": round(site_power_cost_per_hour, 4),
                "net_profit_per_hour": round(site_net_profit, 4),
                "profit_margin_percent": round(site_profit_margin, 2),
                "break_even_price": round(site_net_profit, 4) if site_net_profit > 0 else 0,
                "recommended_competitive_price": round(site_net_profit * 1.1, 4) if site_net_profit > 0 else round(mining_revenue_per_hour * 0.9, 4)  # 10% above mining profit or 10% below mining revenue
            }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "global_mining_data": {
                "hash_price": hash_price,
                "energy_price": energy_price,
                "asic_specs": {
                    "hashrate_ths": asic_hashrate,
                    "power_consumption_kw": asic_power_consumption
                },
                "mining_revenue_per_hour": round(mining_revenue_per_hour, 4),
                "avg_power_cost_per_hour": round(power_cost_per_hour, 4),
                "avg_net_profit_per_hour": round(net_profit_per_hour, 4),
                "avg_profit_margin_percent": round(profit_margin, 2)
            },
            "site_specific_profitability": site_profitability,
            "pricing_recommendations": {
                "minimum_competitive_price": round(max(site_profitability[site]["break_even_price"] for site in site_profitability), 4),
                "average_competitive_price": round(sum(site_profitability[site]["recommended_competitive_price"] for site in site_profitability) / len(site_profitability), 4),
                "premium_competitive_price": round(max(site_profitability[site]["recommended_competitive_price"] for site in site_profitability), 4)
            },
            "market_analysis": {
                "is_mining_profitable": net_profit_per_hour > 0,
                "best_mining_sites": sorted(
                    [(site_id, data["profit_margin_percent"]) for site_id, data in site_profitability.items()],
                    key=lambda x: x[1], reverse=True
                )[:3],
                "arbitrage_opportunity": "High" if profit_margin > 20 else "Medium" if profit_margin > 10 else "Low"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate mining profitability: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 