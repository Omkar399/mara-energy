// Global state
let systemInitialized = false;
let updateInterval = null;
let worldMap = null;
let revenueChart = null;
let efficiencyChart = null;
let optimizationHistory = [];
let lastOptimizationTime = null;
let activityPaused = false;
let activityCount = 0;

// API base URL
const API_BASE = '';

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    initializeCharts();
    initializeMap();
    showWelcomeMessage();
});

// Show welcome message
function showWelcomeMessage() {
    showNotification('🚀 Welcome to SLA-Smart Energy Arbitrage Platform! Click "Initialize System" to begin.', 'info', 5000);
}

// Event listeners
function initializeEventListeners() {
    // Initialize system button
    document.getElementById('initializeBtn').addEventListener('click', initializeSystem);
    
    // Optimize button with enhanced feedback
    document.getElementById('optimizeBtn').addEventListener('click', optimizeSystemWithAnimation);
    
    // SLA request button
    document.getElementById('requestSlaBtn').addEventListener('click', requestSLAWithFeedback);
    
    // Auto-optimize toggle
    const autoOptimizeToggle = createAutoOptimizeToggle();
    document.querySelector('.header-controls').appendChild(autoOptimizeToggle);
    
    // Activity feed controls
    document.getElementById('pauseActivityBtn').addEventListener('click', toggleActivityFeed);
    document.getElementById('clearActivityBtn').addEventListener('click', clearActivityFeed);
    
    // Enhanced SLA form validation and preview
    document.getElementById('slaTypeSelect').addEventListener('change', updateSLAPreview);
    document.getElementById('computeType').addEventListener('change', updateSLAPreview);
    document.getElementById('computeUnits').addEventListener('input', handleSLAFormInput);
    document.getElementById('durationHours').addEventListener('input', handleSLAFormInput);
    document.getElementById('preferredRegion').addEventListener('change', updateSLAPreview);
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);
}

// Activity feed management
function addActivityItem(type, title, description, icon = null) {
    if (activityPaused) return;
    
    const feed = document.getElementById('activityFeed');
    const item = document.createElement('div');
    item.className = `activity-item ${type}`;
    
    const iconClass = icon || getDefaultIcon(type);
    const timeStr = new Date().toLocaleTimeString();
    
    item.innerHTML = `
        <div class="activity-icon">
            <i class="${iconClass}"></i>
        </div>
        <div class="activity-content">
            <div class="activity-title">${title}</div>
            <div class="activity-description">${description}</div>
            <div class="activity-time">${timeStr}</div>
        </div>
    `;
    
    // Insert at the top (after welcome message if it exists)
    const welcomeItem = feed.querySelector('.activity-item.welcome');
    if (welcomeItem && feed.children.length === 1) {
        feed.appendChild(item);
    } else {
        feed.insertBefore(item, welcomeItem ? welcomeItem.nextSibling : feed.firstChild);
    }
    
    // Limit to 50 items
    while (feed.children.length > 50) {
        feed.removeChild(feed.lastChild);
    }
    
    // Auto-scroll to show new item
    if (!activityPaused) {
        item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    
    activityCount++;
}

function getDefaultIcon(type) {
    const icons = {
        'system': 'fas fa-cog',
        'ai': 'fas fa-brain',
        'sla': 'fas fa-handshake',
        'error': 'fas fa-exclamation-triangle',
        'success': 'fas fa-check-circle',
        'warning': 'fas fa-exclamation-circle'
    };
    return icons[type] || 'fas fa-info-circle';
}

function toggleActivityFeed() {
    const btn = document.getElementById('pauseActivityBtn');
    const feed = document.querySelector('.activity-feed');
    
    activityPaused = !activityPaused;
    
    if (activityPaused) {
        btn.innerHTML = '<i class="fas fa-play"></i> Resume';
        feed.classList.add('paused');
        addActivityItem('system', 'Activity Feed Paused', 'Live updates paused by user', 'fas fa-pause');
    } else {
        btn.innerHTML = '<i class="fas fa-pause"></i> Pause';
        feed.classList.remove('paused');
        addActivityItem('system', 'Activity Feed Resumed', 'Live updates resumed', 'fas fa-play');
    }
}

function clearActivityFeed() {
    const feed = document.getElementById('activityFeed');
    const welcomeItem = feed.querySelector('.activity-item.welcome');
    
    // Keep only the welcome message
    feed.innerHTML = '';
    if (welcomeItem) {
        feed.appendChild(welcomeItem);
    }
    
    activityCount = 0;
    addActivityItem('system', 'Activity Feed Cleared', 'Activity history cleared by user', 'fas fa-trash');
}

// Enhanced SLA form handling
function handleSLAFormInput() {
    validateSLAForm();
    updateSLAPreview();
}

function updateSLAPreview() {
    const tier = document.getElementById('slaTypeSelect').value;
    const computeType = document.getElementById('computeType').value;
    const computeUnits = parseInt(document.getElementById('computeUnits').value) || 0;
    const durationHours = parseInt(document.getElementById('durationHours').value) || 0;
    const region = document.getElementById('preferredRegion').value;
    
    // Update preview values
    document.getElementById('previewTier').textContent = tier.toUpperCase();
    document.getElementById('previewCompute').textContent = computeUnits > 0 ? `${computeUnits.toLocaleString()} ${computeType.toUpperCase()}` : '-';
    document.getElementById('previewDuration').textContent = durationHours > 0 ? `${durationHours} hours` : '-';
    
    // Calculate cost, uptime, and estimated power
    if (computeUnits > 0 && durationHours > 0) {
        const multipliers = { premium: 3.5, standard: 2.0, flexible: 1.2, spot: 0.4 };
        const uptimeGuarantees = { premium: '99.9%', standard: '95.0%', flexible: '90.0%', spot: 'Best Effort' };
        
        // Estimate power consumption based on compute type
        const powerPerUnit = {
            'gpu': 0.33, // 330W per GPU
            'asic': 3.0, // 3kW per ASIC
            'mixed': 1.5  // Average
        };
        
        const estimatedPowerMW = (computeUnits * powerPerUnit[computeType]) / 1000; // Convert to MW
        const baseCostPerMW = 100; // $100 per MW per hour
        const estimatedCost = estimatedPowerMW * durationHours * baseCostPerMW * multipliers[tier];
        
        document.getElementById('previewCost').textContent = formatCurrency(estimatedCost);
        document.getElementById('previewUptime').textContent = uptimeGuarantees[tier];
        document.getElementById('previewPower').textContent = formatNumber(estimatedPowerMW) + ' MW';
    } else {
        document.getElementById('previewCost').textContent = '-';
        document.getElementById('previewUptime').textContent = '-';
        document.getElementById('previewPower').textContent = '-';
    }
}

// Initialize system with enhanced feedback
async function initializeSystem() {
    showLoading(true, 'Connecting to MARA API and initializing 10 global data centers...');
    updateSystemStatus('initializing');
    addActivityItem('system', 'System Initialization Started', 'Connecting to MARA API and initializing global data centers...', 'fas fa-rocket');
    
    try {
        // Show initialization steps
        showNotification('🔌 Connecting to MARA API...', 'info', 2000);
        
        const response = await fetch(`${API_BASE}/api/initialize`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error('Failed to initialize system');
        }
        
        const data = await response.json();
        
        // Show success with details
        showNotification(`✅ System initialized! Connected to ${data.total_sites} data centers with live MARA pricing.`, 'success', 4000);
        addActivityItem('system', 'System Initialization Complete', `Successfully connected to ${data.total_sites} global data centers with live MARA pricing data`, 'fas fa-check-circle');
        
        systemInitialized = true;
        updateSystemStatus('online');
        document.getElementById('optimizeBtn').disabled = false;
        
        // Animate the initialization
        animateSystemInitialization();
        
        // Start periodic updates
        startPeriodicUpdates();
        
        // Initial data load with animation
        await updateDashboardWithAnimation();
        
        // Show AI is ready
        showNotification('🤖 Claude AI Optimizer is now active and analyzing your global infrastructure!', 'success', 3000);
        addActivityItem('ai', 'Claude AI Activated', 'AI optimizer is now analyzing global energy patterns and ready for optimization requests', 'fas fa-brain');
        
    } catch (error) {
        console.error('Initialization error:', error);
        showNotification('❌ Failed to initialize system: ' + error.message, 'error');
        updateSystemStatus('error');
        addActivityItem('error', 'System Initialization Failed', `Error: ${error.message}`, 'fas fa-exclamation-triangle');
    } finally {
        showLoading(false);
    }
}

// Animate system initialization
function animateSystemInitialization() {
    const statusDot = document.querySelector('.status-dot');
    statusDot.classList.add('pulse-animation');
    
    // Animate metric cards
    const metricCards = document.querySelectorAll('.metric-card');
    metricCards.forEach((card, index) => {
        setTimeout(() => {
            card.classList.add('animate-in');
        }, index * 200);
    });
}

// Enhanced optimize system with animation
async function optimizeSystemWithAnimation() {
    if (!systemInitialized) {
        showNotification('⚠️ Please initialize the system first!', 'warning');
        return;
    }
    
    // Show AI thinking animation
    showAIThinking(true);
    showLoading(true, 'Claude AI is analyzing global energy patterns and optimizing allocations...');
    addActivityItem('ai', 'AI Optimization Started', 'Claude AI is analyzing 10 data centers across different time zones for optimal energy allocation', 'fas fa-brain');
    
    // Add visual feedback to optimize button
    const optimizeBtn = document.getElementById('optimizeBtn');
    optimizeBtn.classList.add('optimizing');
    optimizeBtn.innerHTML = '<i class="fas fa-brain fa-spin"></i> Optimizing...';
    
    try {
        showNotification('🧠 Claude AI is analyzing 10 data centers across different time zones...', 'info', 3000);
        
        const response = await fetch(`${API_BASE}/api/optimize`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error('Failed to optimize system');
        }
        
        const data = await response.json();
        lastOptimizationTime = new Date();
        optimizationHistory.push(data);
        
        // Animate the Claude reasoning update
        await updateClaudeReasoningWithAnimation(data.claude_reasoning);
        
        // Update metrics with animation
        animateMetricUpdate('climateSavings', data.climate_savings);
        animateMetricUpdate('timezoneOptimization', data.timezone_optimization);
        
        // Show optimization results
        const savingsPercent = ((data.climate_savings / data.total_revenue) * 100).toFixed(1);
        showNotification(`🎯 Optimization complete! Generated $${data.climate_savings.toLocaleString()} in climate savings (${savingsPercent}% improvement)`, 'success', 5000);
        
        // Add detailed activity log
        const recommendations = extractRecommendations(data.claude_reasoning);
        addActivityItem('ai', 'AI Optimization Complete', 
            `Generated $${data.climate_savings.toLocaleString()} in climate savings (${savingsPercent}% improvement). Key recommendations: ${recommendations.slice(0, 2).join(', ')}`, 
            'fas fa-check-circle');
        
        // Refresh dashboard with animation
        await updateDashboardWithAnimation();
        
        // Show specific AI recommendations
        showAIRecommendations(data);
        
    } catch (error) {
        console.error('Optimization error:', error);
        showNotification('❌ Failed to optimize system: ' + error.message, 'error');
        addActivityItem('error', 'AI Optimization Failed', `Error during optimization: ${error.message}`, 'fas fa-exclamation-triangle');
    } finally {
        showLoading(false);
        showAIThinking(false);
        
        // Reset optimize button
        optimizeBtn.classList.remove('optimizing');
        optimizeBtn.innerHTML = '<i class="fas fa-brain"></i> AI Optimize';
    }
}

// Show AI thinking animation
function showAIThinking(show) {
    const claudePanel = document.querySelector('.claude-panel');
    const indicator = document.querySelector('.claude-indicator');
    
    if (show) {
        claudePanel.classList.add('ai-thinking');
        indicator.innerHTML = `
            <div class="thinking-dots">
                <div class="dot"></div>
                <div class="dot"></div>
                <div class="dot"></div>
            </div>
            <span>Claude AI is analyzing...</span>
        `;
    } else {
        claudePanel.classList.remove('ai-thinking');
        indicator.innerHTML = `
            <div class="pulse-dot"></div>
            <span>AI Analysis Complete</span>
        `;
    }
}

// Update Claude reasoning with animation
async function updateClaudeReasoningWithAnimation(reasoning) {
    const reasoningElement = document.getElementById('claudeReasoning');
    
    // Fade out
    reasoningElement.style.opacity = '0';
    
    await new Promise(resolve => setTimeout(resolve, 300));
    
    // Update content with typewriter effect
    reasoningElement.innerHTML = '';
    await typeWriter(reasoningElement, reasoning, 20);
    
    // Fade in
    reasoningElement.style.opacity = '1';
}

// Typewriter effect
async function typeWriter(element, text, speed = 50) {
    const lines = text.split('\n');
    
    for (let line of lines) {
        const p = document.createElement('p');
        element.appendChild(p);
        
        for (let char of line) {
            p.textContent += char;
            await new Promise(resolve => setTimeout(resolve, speed));
        }
    }
}

// Animate metric update
function animateMetricUpdate(elementId, newValue) {
    const element = document.getElementById(elementId);
    const currentValue = parseFloat(element.textContent.replace(/[$,]/g, '')) || 0;
    
    // Animate the number counting up
    const duration = 1000;
    const steps = 30;
    const increment = (newValue - currentValue) / steps;
    let step = 0;
    
    const interval = setInterval(() => {
        step++;
        const value = currentValue + (increment * step);
        element.textContent = formatCurrency(value);
        element.classList.add('metric-updated');
        
        if (step >= steps) {
            clearInterval(interval);
            element.textContent = formatCurrency(newValue);
            setTimeout(() => element.classList.remove('metric-updated'), 2000);
        }
    }, duration / steps);
}

// Show AI recommendations
function showAIRecommendations(optimizationData) {
    const recommendations = extractRecommendations(optimizationData.claude_reasoning);
    
    if (recommendations.length > 0) {
        const message = `🤖 AI Recommendations:\n${recommendations.join('\n')}`;
        showNotification(message, 'info', 8000);
    }
}

// Extract recommendations from Claude reasoning
function extractRecommendations(reasoning) {
    const recommendations = [];
    const lines = reasoning.split('\n');
    
    lines.forEach(line => {
        if (line.includes('Route') || line.includes('Balance') || line.includes('Use') || line.includes('Optimize')) {
            recommendations.push('• ' + line.trim());
        }
    });
    
    return recommendations.slice(0, 3); // Top 3 recommendations
}

// Enhanced SLA request with feedback
async function requestSLAWithFeedback() {
    const tier = document.getElementById('slaTypeSelect').value;
    const computeType = document.getElementById('computeType').value;
    const computeUnits = parseInt(document.getElementById('computeUnits').value);
    const durationHours = parseInt(document.getElementById('durationHours').value);
    const preferredRegion = document.getElementById('preferredRegion').value;
    
    if (!validateSLAInputs(tier, computeUnits, durationHours)) {
        return;
    }
    
    // Show SLA processing animation
    const slaBtn = document.getElementById('requestSlaBtn');
    slaBtn.classList.add('processing');
    slaBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    
    addActivityItem('sla', 'SLA Request Submitted', 
        `Processing ${tier.toUpperCase()} SLA request for ${computeUnits.toLocaleString()} ${computeType.toUpperCase()} over ${durationHours} hours`, 
        'fas fa-paper-plane');
    
    try {
        showNotification(`🔄 Processing ${tier.toUpperCase()} SLA request for ${computeUnits} ${computeType.toUpperCase()}...`, 'info', 2000);
        
        const response = await fetch(`${API_BASE}/api/sla/request`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tier: tier,
                compute_type: computeType,
                compute_units: computeUnits,
                duration_hours: durationHours,
                preferred_region: preferredRegion
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to request SLA');
        }
        
        const data = await response.json();
        
        // Show success with site details
        const siteConfig = getSiteConfig(data.optimal_site);
        const siteName = siteConfig ? siteConfig.name : data.optimal_site;
        
        showNotification(`✅ ${tier.toUpperCase()} SLA allocated successfully!\n📍 Site: ${siteName}\n💻 Compute: ${data.compute_units_allocated} ${data.compute_type.toUpperCase()}\n⚡ Est. Power: ${data.estimated_power_mw} MW\n⏱️ Duration: ${durationHours} hours\n🎯 Uptime: ${data.estimated_uptime}%`, 'success', 6000);
        
        // Add detailed activity log
        const costEstimate = computeUnits * durationHours * 100 * {'premium': 3.5, 'standard': 2.0, 'flexible': 1.2, 'spot': 0.4}[tier] * (data.estimated_power_mw);
        addActivityItem('sla', 'SLA Request Approved', 
            `${tier.toUpperCase()} SLA allocated to ${siteName}: ${data.compute_units_allocated} ${data.compute_type.toUpperCase()} units (${data.estimated_power_mw} MW) with ${data.estimated_uptime}% uptime guarantee. Est. cost: ${formatCurrency(costEstimate)}`, 
            'fas fa-handshake');
        
        // Animate the SLA tier card
        animateSLATierUpdate(tier, computeUnits);
        
        // Clear form with animation
        clearSLAFormWithAnimation();
        
        // Update dashboard
        await updateDashboardWithAnimation();
        
        // Trigger auto-optimization if enabled
        if (document.getElementById('autoOptimizeToggle').checked) {
            setTimeout(() => {
                showNotification('🤖 Auto-optimization triggered by new SLA request...', 'info', 2000);
                addActivityItem('ai', 'Auto-Optimization Triggered', 'New SLA request triggered automatic system optimization', 'fas fa-cog');
                optimizeSystemWithAnimation();
            }, 2000);
        }
        
    } catch (error) {
        console.error('SLA request error:', error);
        showNotification('❌ Failed to request SLA: ' + error.message, 'error');
        addActivityItem('error', 'SLA Request Failed', `Error processing SLA request: ${error.message}`, 'fas fa-exclamation-triangle');
    } finally {
        slaBtn.classList.remove('processing');
        slaBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Create SLA Request';
    }
}

// Validate SLA inputs with real-time feedback
function validateSLAInputs(tier, computeUnits, durationHours) {
    const errors = [];
    
    if (!computeUnits || computeUnits < 1) {
        errors.push('Compute units must be at least 1');
    }
    if (computeUnits > 100000) {
        errors.push('Compute units cannot exceed 100,000');
    }
    if (!durationHours || durationHours < 1) {
        errors.push('Duration must be at least 1 hour');
    }
    if (durationHours > 8760) {
        errors.push('Duration cannot exceed 8,760 hours (1 year)');
    }
    
    if (errors.length > 0) {
        showNotification('⚠️ Please fix the following:\n' + errors.join('\n'), 'warning', 4000);
        return false;
    }
    
    return true;
}

// Real-time SLA form validation
function validateSLAForm() {
    const computeInput = document.getElementById('computeUnits');
    const durationInput = document.getElementById('durationHours');
    const submitBtn = document.getElementById('requestSlaBtn');
    
    const compute = parseInt(computeInput.value);
    const duration = parseInt(durationInput.value);
    
    // Visual feedback for inputs
    computeInput.classList.toggle('invalid', compute < 1 || compute > 100000);
    durationInput.classList.toggle('invalid', duration < 1 || duration > 8760);
    
    // Enable/disable submit button
    const isValid = compute >= 1 && compute <= 100000 && duration >= 1 && duration <= 8760;
    submitBtn.disabled = !isValid;
    
    return isValid;
}

// Show estimated SLA cost
function showEstimatedSLACost(compute, duration) {
    const tier = document.getElementById('slaTypeSelect').value;
    const multipliers = { premium: 3.5, standard: 2.0, flexible: 1.2, spot: 0.4 };
    const baseCost = 0.1; // $0.1 per MW per hour
    
    const estimatedCost = compute * duration * baseCost * multipliers[tier];
    
    let costDisplay = document.getElementById('estimatedCost');
    if (!costDisplay) {
        costDisplay = document.createElement('div');
        costDisplay.id = 'estimatedCost';
        costDisplay.className = 'estimated-cost';
        document.querySelector('.sla-request-form').appendChild(costDisplay);
    }
    
    costDisplay.innerHTML = `💰 Estimated Cost: ${formatCurrency(estimatedCost)}`;
}

// Animate SLA tier update
function animateSLATierUpdate(tier, computeUnits) {
    const tierElement = document.querySelector(`.sla-tier.${tier}`);
    tierElement.classList.add('tier-updated');
    
    setTimeout(() => {
        tierElement.classList.remove('tier-updated');
    }, 2000);
}

// Clear SLA form with animation
function clearSLAFormWithAnimation() {
    const inputs = ['computeUnits', 'durationHours'];
    inputs.forEach(inputId => {
        const input = document.getElementById(inputId);
        input.style.transform = 'scale(0.95)';
        input.value = '';
        setTimeout(() => {
            input.style.transform = 'scale(1)';
        }, 200);
    });
    
    // Remove estimated cost
    const costDisplay = document.getElementById('estimatedCost');
    if (costDisplay) {
        costDisplay.remove();
    }
}

// Get site configuration
function getSiteConfig(siteId) {
    const siteConfigs = {
        'site_1_nordic': { name: 'Nordic Iceland' },
        'site_2_canada': { name: 'Canada Vancouver' },
        'site_3_norway': { name: 'Norway Oslo' },
        'site_4_singapore': { name: 'Singapore Tropical' },
        'site_5_texas': { name: 'Texas USA' },
        'site_6_ireland': { name: 'Ireland Dublin' },
        'site_7_japan': { name: 'Japan Tokyo' },
        'site_8_australia': { name: 'Australia Sydney' },
        'site_9_chile': { name: 'Chile Santiago' },
        'site_10_germany': { name: 'Germany Berlin' }
    };
    return siteConfigs[siteId];
}

// Toggle auto-optimization
function toggleAutoOptimization(event) {
    const isEnabled = event.target.checked;
    
    if (isEnabled) {
        showNotification('🤖 Auto-optimization enabled! System will optimize every 5 minutes.', 'success', 3000);
        addActivityItem('system', 'Auto-Optimization Enabled', 'System will now automatically optimize every 5 minutes', 'fas fa-cog');
        startAutoOptimization();
    } else {
        showNotification('⏸️ Auto-optimization disabled.', 'info', 2000);
        addActivityItem('system', 'Auto-Optimization Disabled', 'Automatic optimization has been turned off', 'fas fa-pause');
        stopAutoOptimization();
    }
}

// Auto-optimization functionality
let autoOptimizeInterval = null;

function startAutoOptimization() {
    if (autoOptimizeInterval) return;
    
    autoOptimizeInterval = setInterval(() => {
        if (systemInitialized) {
            showNotification('🔄 Auto-optimization running...', 'info', 2000);
            addActivityItem('ai', 'Auto-Optimization Running', 'Scheduled optimization cycle initiated', 'fas fa-clock');
            optimizeSystemWithAnimation();
        }
    }, 300000); // 5 minutes
}

function stopAutoOptimization() {
    if (autoOptimizeInterval) {
        clearInterval(autoOptimizeInterval);
        autoOptimizeInterval = null;
    }
}

// Enhanced dashboard update with activity logging
async function updateDashboardWithAnimation() {
    if (!systemInitialized) return;
    
    try {
        console.log('Starting dashboard update...');
        const response = await fetch(`${API_BASE}/api/dashboard/metrics`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Dashboard data received:', data);
        
        // Validate required data structure
        if (!data.global_metrics) {
            throw new Error('Missing global_metrics in response');
        }
        if (!data.sites || !Array.isArray(data.sites)) {
            throw new Error('Missing or invalid sites data in response');
        }
        
        // Update global metrics with animation
        updateGlobalMetricsWithAnimation(data.global_metrics);
        
        // Update sites with stagger animation
        updateSitesWithAnimation(data.sites);
        
        // Update SLA commitments and summary
        if (data.sla_commitments) {
            updateSLACommitments(data.sla_commitments);
            updateSLASummary(data.sla_commitments);
        }
        
        // Update map with pulse effect
        updateMapMarkersWithAnimation(data.sites);
        
        // Update charts
        updateCharts(data);
        
        // Show last update time
        showLastUpdateTime();
        
        // Log significant changes
        if (data.global_metrics.total_revenue > 0) {
            const revenueChange = data.global_metrics.total_revenue - (window.lastRevenue || 0);
            if (Math.abs(revenueChange) > 100) {
                const changeType = revenueChange > 0 ? 'increased' : 'decreased';
                addActivityItem('system', 'Revenue Update', 
                    `Total revenue ${changeType} by ${formatCurrency(Math.abs(revenueChange))} to ${formatCurrency(data.global_metrics.total_revenue)}`, 
                    revenueChange > 0 ? 'fas fa-arrow-up' : 'fas fa-arrow-down');
            }
            window.lastRevenue = data.global_metrics.total_revenue;
        }
        
        console.log('Dashboard update completed successfully');
        
    } catch (error) {
        console.error('Dashboard update error:', error);
        showNotification(`⚠️ Dashboard update failed: ${error.message}. Retrying...`, 'warning', 3000);
        addActivityItem('error', 'Dashboard Update Failed', `Error: ${error.message}. Will retry in 30 seconds.`, 'fas fa-exclamation-triangle');
        
        // Try to provide more specific error information
        if (error.message.includes('fetch')) {
            addActivityItem('error', 'Network Error', 'Unable to connect to server. Check if the server is running.', 'fas fa-wifi');
        }
    }
}

// Update global metrics with animation
function updateGlobalMetricsWithAnimation(metrics) {
    const updates = [
        { id: 'totalRevenue', value: formatCurrency(metrics.total_revenue) },
        { id: 'totalPower', value: formatNumber(metrics.total_power_used) + ' MW' },
        { id: 'coolingEfficiency', value: formatPercentage(metrics.avg_cooling_efficiency) },
        { id: 'renewableEnergy', value: formatPercentage(metrics.renewable_energy_usage) }
    ];
    
    updates.forEach((update, index) => {
        setTimeout(() => {
            const element = document.getElementById(update.id);
            if (!element) {
                console.warn(`Element with ID '${update.id}' not found`);
                return;
            }
            
            element.style.transform = 'scale(1.05)';
            element.textContent = update.value;
            element.classList.add('metric-pulse');
            
            setTimeout(() => {
                element.style.transform = 'scale(1)';
                element.classList.remove('metric-pulse');
            }, 300);
        }, index * 100);
    });
}

// Update sites with stagger animation
function updateSitesWithAnimation(sites) {
    const container = document.getElementById('sitesContainer');
    if (!container) {
        console.warn('Sites container not found');
        return;
    }
    
    // Fade out existing cards
    const existingCards = container.querySelectorAll('.site-card');
    existingCards.forEach(card => card.style.opacity = '0');
    
    setTimeout(() => {
        container.innerHTML = '';
        
        sites.forEach((site, index) => {
            setTimeout(() => {
                const siteCard = createSiteCard(site);
                siteCard.style.opacity = '0';
                siteCard.style.transform = 'translateY(20px)';
                container.appendChild(siteCard);
                
                // Animate in
                setTimeout(() => {
                    siteCard.style.opacity = '1';
                    siteCard.style.transform = 'translateY(0)';
                }, 50);
            }, index * 100);
        });
    }, 200);
}

// Create site card HTML element
function createSiteCard(site) {
    const card = document.createElement('div');
    card.className = `site-card ${getEfficiencyClass(site.cooling_efficiency)}`;
    
    card.innerHTML = `
        <div class="site-header">
            <div class="site-name">${site.name}</div>
            <div class="site-temp">
                <i class="fas fa-thermometer-half"></i>
                ${Math.round(site.weather.temperature)}°F
            </div>
        </div>
        <div class="site-metrics">
            <div class="site-metric">
                <span class="site-metric-label">Revenue</span>
                <span class="site-metric-value">${formatCurrency(site.revenue)}</span>
            </div>
            <div class="site-metric">
                <span class="site-metric-label">Power</span>
                <span class="site-metric-value">${formatNumber(site.power_used)} MW</span>
            </div>
            <div class="site-metric">
                <span class="site-metric-label">Efficiency</span>
                <span class="site-metric-value">${formatPercentage(site.cooling_efficiency)}</span>
            </div>
            <div class="site-metric">
                <span class="site-metric-label">Uptime</span>
                <span class="site-metric-value">${site.uptime.toFixed(1)}%</span>
            </div>
        </div>
    `;
    
    return card;
}

// Update map markers with animation
function updateMapMarkersWithAnimation(sites) {
    try {
        updateMapMarkers(sites);
        
        // Add pulse effect to map
        const mapElement = document.getElementById('worldMap');
        if (mapElement) {
            mapElement.classList.add('map-update-pulse');
            
            setTimeout(() => {
                mapElement.classList.remove('map-update-pulse');
            }, 1000);
        }
    } catch (error) {
        console.warn('Error updating map markers:', error);
    }
}

// Show last update time
function showLastUpdateTime() {
    try {
        let updateTimeElement = document.getElementById('lastUpdateTime');
        if (!updateTimeElement) {
            updateTimeElement = document.createElement('div');
            updateTimeElement.id = 'lastUpdateTime';
            updateTimeElement.className = 'last-update-time';
            
            const headerContent = document.querySelector('.header-content');
            if (headerContent) {
                headerContent.appendChild(updateTimeElement);
            } else {
                console.warn('Header content element not found');
                return;
            }
        }
        
        const now = new Date();
        updateTimeElement.textContent = `Last updated: ${now.toLocaleTimeString()}`;
    } catch (error) {
        console.warn('Error updating last update time:', error);
    }
}

// Update dashboard
async function updateDashboard() {
    return updateDashboardWithAnimation();
}

// Initialize world map
function initializeMap() {
    worldMap = L.map('worldMap').setView([30, 0], 2);
    
    // Dark theme tile layer
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '© OpenStreetMap © CartoDB',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(worldMap);
    
    // Disable zoom control for cleaner look
    worldMap.zoomControl.remove();
}

// Update map markers
function updateMapMarkers(sites) {
    if (!worldMap) return;
    
    // Clear existing markers
    worldMap.eachLayer(layer => {
        if (layer instanceof L.CircleMarker || layer instanceof L.Marker) {
            worldMap.removeLayer(layer);
        }
    });
    
    // Add new markers
    sites.forEach(site => {
        const efficiency = site.cooling_efficiency;
        const color = efficiency > 0.8 ? '#10b981' : efficiency > 0.6 ? '#f59e0b' : '#ef4444';
        
        const marker = L.circleMarker([site.location.lat, site.location.lon], {
            radius: 8 + (site.power_used / 50000), // Size based on power usage
            fillColor: color,
            color: '#fff',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.8
        }).addTo(worldMap);
        
        // Popup with site details
        marker.bindPopup(`
            <div style="color: #000;">
                <h3>${site.name}</h3>
                <p><strong>Temperature:</strong> ${Math.round(site.weather.temperature)}°F</p>
                <p><strong>Efficiency:</strong> ${formatPercentage(site.cooling_efficiency)}</p>
                <p><strong>Revenue:</strong> ${formatCurrency(site.revenue)}</p>
                <p><strong>Power:</strong> ${formatNumber(site.power_used)} MW</p>
            </div>
        `);
    });
}

// Initialize charts
function initializeCharts() {
    // Revenue chart
    const revenueCtx = document.getElementById('revenueChart').getContext('2d');
    revenueChart = new Chart(revenueCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Total Revenue',
                data: [],
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: '#f8fafc'
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: '#cbd5e1'
                    },
                    grid: {
                        color: 'rgba(203, 213, 225, 0.1)'
                    }
                },
                y: {
                    ticks: {
                        color: '#cbd5e1',
                        callback: function(value) {
                            return '$' + formatNumber(value);
                        }
                    },
                    grid: {
                        color: 'rgba(203, 213, 225, 0.1)'
                    }
                }
            }
        }
    });
    
    // Efficiency chart
    const efficiencyCtx = document.getElementById('efficiencyChart').getContext('2d');
    efficiencyChart = new Chart(efficiencyCtx, {
        type: 'doughnut',
        data: {
            labels: ['High Efficiency', 'Medium Efficiency', 'Low Efficiency'],
            datasets: [{
                data: [0, 0, 0],
                backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#f8fafc',
                        padding: 20
                    }
                }
            }
        }
    });
}

// Update charts
function updateCharts(data) {
    // Update revenue chart
    if (revenueChart && data.optimization_history) {
        const history = data.optimization_history.slice(-10); // Last 10 points
        const labels = history.map((_, index) => `T-${history.length - index - 1}`);
        const revenues = history.map(h => h.total_revenue);
        
        revenueChart.data.labels = labels;
        revenueChart.data.datasets[0].data = revenues;
        revenueChart.update();
    }
    
    // Update efficiency chart
    if (efficiencyChart && data.sites) {
        const highEff = data.sites.filter(s => s.cooling_efficiency > 0.8).length;
        const mediumEff = data.sites.filter(s => s.cooling_efficiency >= 0.6 && s.cooling_efficiency <= 0.8).length;
        const lowEff = data.sites.filter(s => s.cooling_efficiency < 0.6).length;
        
        efficiencyChart.data.datasets[0].data = [highEff, mediumEff, lowEff];
        efficiencyChart.update();
    }
}

// Utility functions
function formatCurrency(value) {
    if (value === null || value === undefined || isNaN(value)) return '$0';
    if (value === 0) return '$0';
    if (value < 1000) return '$' + value.toFixed(2);
    if (value < 1000000) return '$' + (value / 1000).toFixed(1) + 'K';
    return '$' + (value / 1000000).toFixed(1) + 'M';
}

function formatNumber(value) {
    if (value === null || value === undefined || isNaN(value)) return '0';
    if (value === 0) return '0';
    if (value < 1000) return value.toFixed(0);
    if (value < 1000000) return (value / 1000).toFixed(1) + 'K';
    return (value / 1000000).toFixed(1) + 'M';
}

function formatPercentage(value) {
    if (value === null || value === undefined || isNaN(value)) return '0%';
    return (value * 100).toFixed(1) + '%';
}

function formatTime(timeString) {
    try {
        const date = new Date(timeString);
        return date.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit',
            timeZoneName: 'short'
        });
    } catch {
        return timeString.split(' ').slice(-2).join(' '); // Just show time and timezone
    }
}

function getEfficiencyClass(efficiency) {
    if (efficiency > 0.8) return 'high-efficiency';
    if (efficiency >= 0.6) return 'medium-efficiency';
    return 'low-efficiency';
}

function updateSystemStatus(status) {
    const statusElement = document.getElementById('systemStatus');
    const dot = statusElement.querySelector('.status-dot');
    const text = statusElement.querySelector('span');
    
    if (status === 'online') {
        dot.className = 'status-dot online';
        text.textContent = 'Online';
    } else {
        dot.className = 'status-dot offline';
        text.textContent = 'Offline';
    }
}

function showLoading(show, message = 'Loading...') {
    const overlay = document.getElementById('loadingOverlay');
    if (show) {
        overlay.classList.remove('hidden');
        const loadingText = overlay.querySelector('p');
        if (loadingText) {
            loadingText.textContent = message;
        }
    } else {
        overlay.classList.add('hidden');
    }
}

function showNotification(message, type = 'info', duration = 5000) {
    const container = document.getElementById('notifications');
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    container.appendChild(notification);
    
    // Auto remove after duration
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, duration);
}

function startPeriodicUpdates() {
    // Update dashboard every 30 seconds
    updateInterval = setInterval(updateDashboard, 30000);
}

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (updateInterval) {
        clearInterval(updateInterval);
    }
});

// Update SLA summary
function updateSLASummary(commitments) {
    const totalSLAs = Object.values(commitments).filter(val => val > 0).length;
    const totalPower = Object.values(commitments).reduce((sum, val) => sum + val, 0);
    
    // Calculate weighted average uptime
    const uptimeWeights = { premium: 99.9, standard: 95.0, flexible: 90.0, spot: 80.0 };
    let weightedUptime = 0;
    let totalWeight = 0;
    
    Object.entries(commitments).forEach(([tier, power]) => {
        if (power > 0) {
            weightedUptime += uptimeWeights[tier] * power;
            totalWeight += power;
        }
    });
    
    const avgUptime = totalWeight > 0 ? (weightedUptime / totalWeight).toFixed(1) : 0;
    
    const summaryElements = [
        { id: 'totalActiveSLAs', value: totalSLAs },
        { id: 'totalCommittedPower', value: formatNumber(totalPower) + ' MW' },
        { id: 'avgUptimeGuarantee', value: avgUptime + '%' }
    ];
    
    summaryElements.forEach(({ id, value }) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        } else {
            console.warn(`Element with ID '${id}' not found`);
        }
    });
}

// Update SLA commitments display
function updateSLACommitments(commitments) {
    // Update individual tier allocations
    const elements = [
        { id: 'premiumAllocation', value: formatNumber(commitments.premium || 0) + ' MW' },
        { id: 'standardAllocation', value: formatNumber(commitments.standard || 0) + ' MW' },
        { id: 'flexibleAllocation', value: formatNumber(commitments.flexible || 0) + ' MW' },
        { id: 'spotAllocation', value: formatNumber(commitments.spot || 0) + ' MW' }
    ];
    
    elements.forEach(({ id, value }) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        } else {
            console.warn(`Element with ID '${id}' not found`);
        }
    });
}

// Create auto-optimize toggle
function createAutoOptimizeToggle() {
    const toggleContainer = document.createElement('div');
    toggleContainer.className = 'auto-optimize-toggle';
    toggleContainer.innerHTML = `
        <label class="toggle-switch">
            <input type="checkbox" id="autoOptimizeToggle">
            <span class="toggle-slider"></span>
            <span class="toggle-label">Auto-Optimize</span>
        </label>
    `;
    
    const toggle = toggleContainer.querySelector('#autoOptimizeToggle');
    toggle.addEventListener('change', toggleAutoOptimization);
    
    return toggleContainer;
}

// Handle keyboard shortcuts
function handleKeyboardShortcuts(event) {
    if (event.ctrlKey || event.metaKey) {
        switch(event.key) {
            case 'i':
                event.preventDefault();
                if (!systemInitialized) initializeSystem();
                break;
            case 'o':
                event.preventDefault();
                if (systemInitialized) optimizeSystemWithAnimation();
                break;
            case 's':
                event.preventDefault();
                document.getElementById('slaTypeSelect').focus();
                break;
        }
    }
} 