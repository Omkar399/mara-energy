"""
AI Hardware Optimization Module for MARA Energy Platform
Provides predictive maintenance, hardware optimization, and maintenance scheduling capabilities.
"""

import json
import random
import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class HardwareMetrics:
    """Hardware metrics for AI analysis"""
    machine_type: str
    machine_id: str
    temperature: float
    power_consumption: float
    hash_rate: float
    efficiency: float
    uptime: float
    last_maintenance: str
    health_score: float

@dataclass
class MaintenancePrediction:
    """Maintenance prediction result"""
    machine_type: str
    machine_id: str
    failure_probability: float
    estimated_failure_date: str
    recommended_action: str
    confidence_level: float
    estimated_cost_savings: float

@dataclass
class OptimizationRecommendation:
    """Hardware optimization recommendation"""
    machine_type: str
    machine_id: str
    current_settings: Dict
    optimized_settings: Dict
    expected_improvements: Dict
    risk_assessment: str

class MARAHardwareAI:
    """AI engine for hardware analysis and optimization"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.prediction_models = {
            'immersion_miners': self._create_prediction_model('immersion'),
            'air_miners': self._create_prediction_model('air'),
            'hydro_miners': self._create_prediction_model('hydro'),
            'asic_compute': self._create_prediction_model('asic'),
            'gpu_compute': self._create_prediction_model('gpu')
        }
    
    def _create_prediction_model(self, machine_type: str):
        """Create a prediction model for a machine type"""
        base_rates = {
            'air_miners': 0.02,      # 2% base failure rate
            'hydro_miners': 0.015,   # 1.5% base failure rate  
            'immersion_miners': 0.01, # 1% base failure rate (most reliable)
            'asic_compute': 0.03,    # 3% base failure rate
            'gpu_compute': 0.025     # 2.5% base failure rate
        }
        return {
            'base_rate': base_rates.get(machine_type, 0.02),
            'machine_type': machine_type
        }
    
    def analyze_hardware_health(self, machine_allocation: Dict[str, int]) -> Dict:
        """Analyze hardware health across all machine types"""
        health_analysis = {}
        total_units = 0
        critical_units = 0
        predicted_failures = []
        
        for machine_type, count in machine_allocation.items():
            if count > 0:
                type_health = self._assess_machine_type_health(machine_type, count)
                health_analysis[machine_type] = type_health
                total_units += count
                critical_units += type_health.get('critical_units', 0)
                predicted_failures.extend(type_health.get('predicted_failures', []))
        
        overall_health_score = self._calculate_overall_health(health_analysis)
        
        return {
            'overall_health_score': overall_health_score,
            'machine_health': health_analysis,
            'critical_units': critical_units,
            'total_units_analyzed': total_units,
            'predicted_failures': predicted_failures,
            'critical_alerts': self._generate_alerts(health_analysis)
        }
    
    def _assess_machine_type_health(self, machine_type: str, count: int) -> Dict:
        """Assess health for a specific machine type"""
        model = self.prediction_models.get(machine_type, self.prediction_models['air_miners'])
        base_failure_rate = model['base_rate']
        
        # Simulate health scores for each unit
        health_scores = []
        predicted_failures = []
        critical_units = 0
        
        for i in range(count):
            # Generate realistic health scores
            if machine_type == 'immersion_miners':
                health_score = random.uniform(85, 98)  # Most reliable
            elif machine_type == 'asic_compute':
                health_score = random.uniform(70, 95)  # Higher failure rate
            else:
                health_score = random.uniform(75, 96)  # Standard range
            
            health_scores.append(health_score)
            
            # Calculate failure probability
            failure_probability = self._calculate_failure_probability(
                base_failure_rate, health_score, machine_type
            )
            
            if failure_probability > 0.1:  # 10% threshold
                predicted_failure = MaintenancePrediction(
                    machine_type=machine_type,
                    machine_id=f"{machine_type}_{i+1}",
                    failure_probability=failure_probability,
                    estimated_failure_date=self._calculate_failure_date(failure_probability),
                    recommended_action=self._get_recommended_action(machine_type, failure_probability),
                    confidence_level=random.uniform(0.7, 0.95),
                    estimated_cost_savings=random.uniform(500, 2000)
                )
                predicted_failures.append(predicted_failure.__dict__)
            
            if health_score < 70:
                critical_units += 1
        
        return {
            'average_health': sum(health_scores) / len(health_scores),
            'critical_units': critical_units,
            'predicted_failures': predicted_failures,
            'total_units': count
        }
    
    def _calculate_failure_probability(self, base_rate: float, health_score: float, machine_type: str) -> float:
        """Calculate failure probability based on health score and machine type"""
        # Health score impact (lower health = higher failure probability)
        health_factor = (100 - health_score) / 100
        
        # Machine type specific factors
        type_factors = {
            'immersion_miners': 0.8,  # Most reliable
            'hydro_miners': 0.9,
            'air_miners': 1.0,
            'gpu_compute': 1.2,
            'asic_compute': 1.5  # Most prone to failures
        }
        
        type_factor = type_factors.get(machine_type, 1.0)
        
        # Calculate final probability
        probability = base_rate * health_factor * type_factor
        
        # Add some randomness
        probability += random.uniform(-0.01, 0.02)
        
        return max(0.0, min(probability, 0.95))  # Clamp between 0 and 95%
    
    def _calculate_failure_date(self, failure_probability: float) -> str:
        """Calculate estimated failure date based on probability"""
        # Higher probability = sooner failure
        days_to_failure = int((1 - failure_probability) * 30) + random.randint(1, 14)
        failure_date = datetime.datetime.now() + datetime.timedelta(days=days_to_failure)
        return failure_date.isoformat()
    
    def _get_recommended_action(self, machine_type: str, failure_probability: float) -> str:
        """Get recommended action based on machine type and failure probability"""
        if failure_probability > 0.3:
            return "immediate_maintenance"
        elif failure_probability > 0.15:
            return "schedule_maintenance_soon"
        elif failure_probability > 0.1:
            return "monitor_closely"
        else:
            return "routine_monitoring"
    
    def _calculate_overall_health(self, health_analysis: Dict) -> float:
        """Calculate overall health score from all machine types"""
        total_health = 0
        total_weight = 0
        
        for machine_type, analysis in health_analysis.items():
            weight = analysis.get('total_units', 1)
            health = analysis.get('average_health', 85)
            total_health += health * weight
            total_weight += weight
        
        return total_health / total_weight if total_weight > 0 else 85.0
    
    def _generate_alerts(self, health_analysis: Dict) -> List[Dict]:
        """Generate critical alerts from health analysis"""
        alerts = []
        
        for machine_type, analysis in health_analysis.items():
            critical_units = analysis.get('critical_units', 0)
            if critical_units > 0:
                alerts.append({
                    'type': 'critical',
                    'machine_type': machine_type,
                    'message': f"{critical_units} {machine_type} units require immediate attention",
                    'priority': 'high'
                })
        
        return alerts

# Global AI instance
mara_ai = MARAHardwareAI()

def get_ai_predictions(machine_allocation: Dict[str, int]) -> Dict:
    """Get AI predictions for hardware health and failures"""
    return mara_ai.analyze_hardware_health(machine_allocation)

def get_hardware_optimizations(machine_allocation: Dict[str, int]) -> List[Dict]:
    """Get hardware optimization recommendations"""
    optimizations = []
    
    for machine_type, count in machine_allocation.items():
        if count > 0:
            for i in range(min(3, count)):  # Limit to 3 optimizations per type
                optimization = _generate_optimization(machine_type, i+1)
                optimizations.append(optimization)
    
    return optimizations

def _generate_optimization(machine_type: str, machine_id: int) -> Dict:
    """Generate optimization recommendation for a specific machine"""
    current_settings = _get_default_settings(machine_type)
    optimized_settings = _optimize_settings(current_settings, machine_type)
    
    # Calculate improvements
    performance_gain = random.uniform(5, 15)
    power_savings = random.uniform(3, 10)
    efficiency_gain = performance_gain - power_savings
    
    return {
        'site_id': f'site_{random.randint(1, 10)}',
        'hardware_id': f'{machine_type}_{machine_id}',
        'hardware_type': machine_type,
        'current_settings': current_settings,
        'optimized_settings': optimized_settings,
        'expected_improvements': {
            'performance_gain_percent': round(performance_gain, 1),
            'power_savings_percent': round(power_savings, 1),
            'efficiency_gain_percent': round(efficiency_gain, 1),
            'estimated_revenue_increase': round(performance_gain * 100, 2),
            'estimated_cost_savings': round(power_savings * 50, 2)
        },
        'risk_assessment': 'low' if performance_gain < 8 else 'medium'
    }

def _get_default_settings(machine_type: str) -> Dict:
    """Get default settings for a machine type"""
    if machine_type == 'gpu_compute':
        return {
            'clock_speed': 1.0,
            'voltage': 1.0,
            'power_limit': 1.0,
            'temperature_target': 75,
            'fan_speed': 0.8
        }
    elif machine_type == 'asic_compute':
        return {
            'clock_speed': 1.0,
            'voltage': 1.0,
            'power_limit': 1.0,
            'temperature_target': 80,
            'fan_speed': 0.9
        }
    else:  # Mining hardware
        return {
            'hash_rate_target': 1.0,
            'power_limit': 1.0,
            'temperature_target': 70,
            'cooling_flow': 0.8
        }

def _optimize_settings(current_settings: Dict, machine_type: str) -> Dict:
    """Optimize settings for a machine type"""
    optimized = current_settings.copy()
    
    if machine_type == 'gpu_compute':
        optimized['clock_speed'] = round(current_settings['clock_speed'] * random.uniform(0.98, 1.08), 2)
        optimized['voltage'] = round(current_settings['voltage'] * random.uniform(0.95, 1.02), 2)
        optimized['power_limit'] = round(current_settings['power_limit'] * random.uniform(0.92, 1.05), 2)
        optimized['temperature_target'] = int(current_settings['temperature_target'] + random.randint(-3, 3))
        optimized['fan_speed'] = round(current_settings['fan_speed'] * random.uniform(0.9, 1.1), 2)
    elif machine_type == 'asic_compute':
        optimized['clock_speed'] = round(current_settings['clock_speed'] * random.uniform(0.97, 1.06), 2)
        optimized['voltage'] = round(current_settings['voltage'] * random.uniform(0.94, 1.01), 2)
        optimized['power_limit'] = round(current_settings['power_limit'] * random.uniform(0.90, 1.03), 2)
        optimized['temperature_target'] = int(current_settings['temperature_target'] + random.randint(-2, 2))
        optimized['fan_speed'] = round(current_settings['fan_speed'] * random.uniform(0.85, 1.05), 2)
    else:  # Mining hardware
        optimized['hash_rate_target'] = round(current_settings['hash_rate_target'] * random.uniform(0.95, 1.05), 2)
        optimized['power_limit'] = round(current_settings['power_limit'] * random.uniform(0.90, 1.02), 2)
        optimized['temperature_target'] = int(current_settings['temperature_target'] + random.randint(-2, 2))
        optimized['cooling_flow'] = round(current_settings['cooling_flow'] * random.uniform(0.85, 1.05), 2)
    
    return optimized

def get_maintenance_schedule(predicted_failures: List[Dict]) -> Dict:
    """Generate maintenance schedule based on predicted failures"""
    schedule = []
    total_estimated_cost = 0
    
    for failure in predicted_failures:
        priority = 'high' if failure['failure_probability'] > 0.2 else 'medium'
        
        schedule_item = {
            'site_id': f'site_{random.randint(1, 10)}',
            'hardware_id': failure['machine_id'],
            'priority': priority,
            'scheduled_date': failure['estimated_failure_date'],
            'estimated_duration': random.randint(2, 6),
            'hardware_type': failure['machine_type'],
            'current_health': random.uniform(60, 85),
            'failure_probability': failure['failure_probability']
        }
        schedule.append(schedule_item)
        
        # Estimate cost savings
        cost_savings = failure.get('estimated_cost_savings', 1000)
        total_estimated_cost += cost_savings
    
    # Group by site
    maintenance_schedule = {}
    for item in schedule:
        site_id = item['site_id']
        if site_id not in maintenance_schedule:
            maintenance_schedule[site_id] = {
                'site_name': f'Site {site_id.split("_")[1]}',
                'hardware_to_maintain': [],
                'estimated_duration_hours': 0,
                'estimated_cost': 0,
                'priority': item['priority']
            }
        maintenance_schedule[site_id]['hardware_to_maintain'].append(item)
        maintenance_schedule[site_id]['estimated_duration_hours'] += item['estimated_duration']
        maintenance_schedule[site_id]['estimated_cost'] += 500 if item['hardware_type'] == 'gpu_compute' else 1000
    
    return {
        'maintenance_schedule': maintenance_schedule,
        'total_sites': len(maintenance_schedule),
        'total_hardware_units': len(schedule),
        'total_estimated_cost': total_estimated_cost,
        'total_estimated_savings': total_estimated_cost * 2,  # Assume 2x cost savings
        'recommended_schedule': schedule
    }