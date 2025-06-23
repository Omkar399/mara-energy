// Global state
let systemInitialized = true; // System is always initialized on startup
let updateInterval = null;
let worldMap = null;
let revenueChart = null;
let efficiencyChart = null;
let optimizationHistory = [];
let lastOptimizationTime = null;
let activityPaused = false;
let activityCount = 0;
let activeSLAs = []; // Store all SLAs
let slaStats = {
    total: 0,
    active: 0,
    revenue: 0,
    avgUptime: 0
};

// API base URL
const API_BASE = '';

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    initializeTabNavigation();
    initializeCharts();
    initializeMap();
    showWelcomeMessage();
    
    // Load SLAs on startup
    loadSLAsOnStartup();
    
    // Start the dashboard immediately since system is auto-initialized
    setTimeout(() => {
        startDashboard();
    }, 1000); // Small delay to let the UI settle
});

// Tab Navigation Functions
function initializeTabNavigation() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabId = button.getAttribute('data-tab');
            switchTab(tabId);
        });
    });
    
    // Set default active tab
    switchTab('dashboard');
}

function switchTab(tabId) {
    // Update tab buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');
    
    // Update tab contents
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(tabId).classList.add('active');
    
    // Load tab-specific data
    if (tabId === 'sla-management') {
        loadSLAManagement();
    } else if (tabId === 'maintenance-optimization') {
        loadMaintenanceOptimization();
    } else if (tabId === 'ai-intelligence') {
        loadAIIntelligence();
    }
}

// SLA Management Functions
async function loadSLAsOnStartup() {
    try {
        // Always load from database instead of localStorage
        const success = await fetchSLAsFromBackend();
        
        if (success) {
            updateSLAStats();
            addActivityItem('system', 'SLAs Loaded', `${activeSLAs.length} SLA agreements loaded from database`, 'fas fa-handshake');
        } else {
            // If database fetch fails, start with empty array
            activeSLAs = [];
            updateSLAStats();
            addActivityItem('system', 'SLAs Initialized', 'Started with empty SLA database', 'fas fa-handshake');
        }
    } catch (error) {
        console.error('Error loading SLAs:', error);
        activeSLAs = [];
        updateSLAStats();
        addActivityItem('error', 'SLA Load Error', 'Failed to load SLA data from database', 'fas fa-exclamation-triangle');
    }
}

function saveSLAsToStorage() {
    try {
        localStorage.setItem('activeSLAs', JSON.stringify(activeSLAs));
    } catch (error) {
        console.error('Error saving SLAs:', error);
    }
}

// Fetch SLAs from backend API to keep frontend synchronized
async function fetchSLAsFromBackend() {
    try {
        const response = await fetch(`${API_BASE}/api/sla/active`);
        if (response.ok) {
            const data = await response.json();
            const backendSLAs = data.active_slas || [];
            
            // Convert backend SLA format to frontend format
            const convertedSLAs = backendSLAs.map(sla => ({
                id: sla.sla_id || `SLA-${Date.now()}`,
                companyName: sla.company_name || 'Unknown Client',
                tier: sla.tier,
                computeType: sla.compute_type,
                computeUnits: sla.compute_units,
                duration: sla.duration_hours,
                siteId: sla.site_id,
                allocatedSite: sla.site_name || 'Unknown Site',
                status: sla.status || 'active',
                createdAt: sla.created_at,
                expiresAt: sla.expires_at,
                cost: sla.estimated_revenue || 0,
                claudeOptimized: sla.claude_optimized || false,
                region: sla.preferred_region || 'any',
                uptime: 95.0,  // Default SLA uptime
                currentUptime: 95.0  // Default current uptime
            }));
            
            // Replace activeSLAs completely with database data (don't merge)
            activeSLAs = convertedSLAs;
            saveSLAsToStorage();
            updateSLAStats();
            
            return true;
        }
    } catch (error) {
        console.error('Error fetching SLAs from backend:', error);
    }
    return false;
}

function updateSLAStats() {
    const activeSLAsCount = activeSLAs.filter(sla => sla.status === 'active').length;
    const totalRevenue = activeSLAs.reduce((sum, sla) => sum + sla.cost, 0);
    const avgUptime = activeSLAs.length > 0 ? 
        activeSLAs.reduce((sum, sla) => sum + sla.currentUptime, 0) / activeSLAs.length : 0;
    
    slaStats = {
        total: activeSLAs.length,
        active: activeSLAsCount,
        revenue: totalRevenue,
        avgUptime: avgUptime
    };
}

function loadSLAManagement() {
    // Fetch latest SLAs from backend first
    fetchSLAsFromBackend().then(() => {
        updateSLAStats();
        renderSLAStats();
        renderSLATable();
        setupSLAFilters();
    });
}

function loadMaintenanceOptimization() {
    // Initialize maintenance and optimization tab
    addActivityItem('system', 'Maintenance & Optimization Tab', 'Loading AI-powered maintenance and hardware optimization features', 'fas fa-tools');
    
    // Load initial maintenance predictions
    predictMaintenance();
}

function renderSLAStats() {
    const statsContainer = document.getElementById('slaStatsGrid');
    if (!statsContainer) return;
    
    statsContainer.innerHTML = `
        <div class="sla-stat-card">
            <div class="stat-icon">
                <i class="fas fa-handshake"></i>
            </div>
            <div class="stat-content">
                <h3>Total SLAs</h3>
                <div class="stat-value">${slaStats.total}</div>
                <div class="stat-change">All time agreements</div>
            </div>
        </div>
        <div class="sla-stat-card">
            <div class="stat-icon">
                <i class="fas fa-check-circle"></i>
            </div>
            <div class="stat-content">
                <h3>Active SLAs</h3>
                <div class="stat-value">${slaStats.active}</div>
                <div class="stat-change">Currently running</div>
            </div>
        </div>
        <div class="sla-stat-card">
            <div class="stat-icon">
                <i class="fas fa-dollar-sign"></i>
            </div>
            <div class="stat-content">
                <h3>Total Revenue</h3>
                <div class="stat-value">${formatCurrency(slaStats.revenue)}</div>
                <div class="stat-change">From all SLAs</div>
            </div>
        </div>
        <div class="sla-stat-card">
            <div class="stat-icon">
                <i class="fas fa-chart-line"></i>
            </div>
            <div class="stat-content">
                <h3>Average Uptime</h3>
                <div class="stat-value">${formatPercentage(slaStats.avgUptime)}</div>
                <div class="stat-change">Across all SLAs</div>
            </div>
        </div>
    `;
}

function renderSLATable() {
    const tableBody = document.getElementById('slaTableBody');
    if (!tableBody) return;
    
    tableBody.innerHTML = '';
    
    activeSLAs.forEach(sla => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${sla.id}</td>
            <td class="company-name">${sla.companyName || 'Unknown Client'}</td>
            <td><span class="sla-tier-badge ${sla.tier}">${sla.tier}</span></td>
            <td>${sla.computeType.toUpperCase()}</td>
            <td>${sla.computeUnits.toLocaleString()}</td>
            <td>${sla.allocatedSite}</td>
            <td>${sla.duration} hrs</td>
            <td>${formatCurrency(sla.cost)}</td>
            <td><span class="sla-status ${sla.status}">${sla.status}</span></td>
            <td>${formatTime(sla.createdAt)}</td>
            <td>${formatTime(sla.expiresAt)}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn-action btn-view" onclick="viewSLADetails('${sla.id}')" title="View Details">
                        <i class="fas fa-eye"></i>
                    </button>
                    ${sla.status === 'active' ? `
                        <button class="btn-action btn-terminate" onclick="terminateSLA('${sla.id}')" title="Terminate SLA">
                            <i class="fas fa-times"></i>
                        </button>
                    ` : ''}
                </div>
            </td>
        `;
        tableBody.appendChild(row);
    });
}

function setupSLAFilters() {
    const statusFilter = document.getElementById('statusFilter');
    const tierFilter = document.getElementById('tierFilter');
    
    if (statusFilter) {
        statusFilter.addEventListener('change', filterSLATable);
    }
    if (tierFilter) {
        tierFilter.addEventListener('change', filterSLATable);
    }
}

function filterSLATable() {
    const statusFilter = document.getElementById('statusFilter').value;
    const tierFilter = document.getElementById('tierFilter').value;
    
    const filteredSLAs = activeSLAs.filter(sla => {
        const statusMatch = statusFilter === 'all' || sla.status === statusFilter;
        const tierMatch = tierFilter === 'all' || sla.tier === tierFilter;
        return statusMatch && tierMatch;
    });
    
    renderFilteredSLATable(filteredSLAs);
}

function renderFilteredSLATable(slas) {
    const tableBody = document.getElementById('slaTableBody');
    if (!tableBody) return;
    
    tableBody.innerHTML = '';
    
    slas.forEach(sla => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${sla.id}</td>
            <td class="company-name">${sla.companyName || 'Unknown Client'}</td>
            <td><span class="sla-tier-badge ${sla.tier}">${sla.tier}</span></td>
            <td>${sla.computeType.toUpperCase()}</td>
            <td>${sla.computeUnits.toLocaleString()}</td>
            <td>${sla.allocatedSite}</td>
            <td>${sla.duration} hrs</td>
            <td>${formatCurrency(sla.cost)}</td>
            <td><span class="sla-status ${sla.status}">${sla.status}</span></td>
            <td>${formatTime(sla.createdAt)}</td>
            <td>${formatTime(sla.expiresAt)}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn-action btn-view" onclick="viewSLADetails('${sla.id}')" title="View Details">
                        <i class="fas fa-eye"></i>
                    </button>
                    ${sla.status === 'active' ? `
                        <button class="btn-action btn-terminate" onclick="terminateSLA('${sla.id}')" title="Terminate SLA">
                            <i class="fas fa-times"></i>
                        </button>
                    ` : ''}
                </div>
            </td>
        `;
        tableBody.appendChild(row);
    });
}

function viewSLADetails(slaId) {
    const sla = activeSLAs.find(s => s.id === slaId);
    if (!sla) return;
    
    const modal = document.getElementById('slaModal');
    const modalBody = document.getElementById('slaModalBody');
    
    modalBody.innerHTML = `
        <div class="sla-details-grid">
            <div class="detail-item">
                <strong>SLA ID:</strong> ${sla.id}
            </div>
            <div class="detail-item">
                <strong>Company/Client:</strong> ${sla.companyName || 'Unknown Client'}
            </div>
            <div class="detail-item">
                <strong>Tier:</strong> <span class="sla-tier-badge ${sla.tier}">${sla.tier}</span>
            </div>
            <div class="detail-item">
                <strong>Compute Resources:</strong> ${sla.computeUnits.toLocaleString()} ${sla.computeType.toUpperCase()}
            </div>
            <div class="detail-item">
                <strong>Allocated Site:</strong> ${sla.allocatedSite}
            </div>
            <div class="detail-item">
                <strong>Duration:</strong> ${sla.duration} hours
            </div>
            <div class="detail-item">
                <strong>Cost:</strong> ${formatCurrency(sla.cost)}
            </div>
            <div class="detail-item">
                <strong>Status:</strong> <span class="sla-status ${sla.status}">${sla.status}</span>
            </div>
            <div class="detail-item">
                <strong>Guaranteed Uptime:</strong> ${formatPercentage(sla.uptime)}
            </div>
            <div class="detail-item">
                <strong>Current Uptime:</strong> ${formatPercentage(sla.currentUptime)}
            </div>
            <div class="detail-item">
                <strong>Created:</strong> ${formatTime(sla.createdAt)}
            </div>
            <div class="detail-item">
                <strong>Expires:</strong> ${formatTime(sla.expiresAt)}
            </div>
            <div class="detail-item">
                <strong>Region Preference:</strong> ${sla.region}
            </div>
        </div>
    `;
    
    modal.classList.remove('hidden');
}

function terminateSLA(slaId) {
    if (!confirm('Are you sure you want to terminate this SLA? This action cannot be undone.')) {
        return;
    }
    
    const slaIndex = activeSLAs.findIndex(s => s.id === slaId);
    if (slaIndex === -1) return;
    
    activeSLAs[slaIndex].status = 'terminated';
    activeSLAs[slaIndex].terminatedAt = new Date().toISOString();
    
    saveSLAsToStorage();
    loadSLAManagement();
    
    addActivityItem('sla', 'SLA Terminated', `SLA ${slaId} has been terminated by user`, 'fas fa-times-circle');
    showNotification(`SLA ${slaId} has been terminated`, 'warning', 3000);
}

function closeSLAModal() {
    document.getElementById('slaModal').classList.add('hidden');
}

function refreshSLAData() {
    loadSLAManagement();
    addActivityItem('system', 'SLA Data Refreshed', 'SLA management data has been refreshed', 'fas fa-sync-alt');
    showNotification('SLA data refreshed', 'success', 2000);
}

function exportSLAData() {
    const dataStr = JSON.stringify(activeSLAs, null, 2);
    const dataBlob = new Blob([dataStr], {type: 'application/json'});
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `sla-data-${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    URL.revokeObjectURL(url);
    
    addActivityItem('system', 'SLA Data Exported', 'SLA data exported to JSON file', 'fas fa-download');
    showNotification('SLA data exported successfully', 'success', 3000);
}

// Show welcome message
function showWelcomeMessage() {
    showNotification('🚀 SLA-Smart Energy Arbitrage Platform is online! System auto-initialized with live MARA data.', 'success', 5000);
}

// Start dashboard functionality
async function startDashboard() {
    updateSystemStatus('online');
    addActivityItem('system', 'System Online', 'Connected to MARA API with live pricing data across 10 global sites', 'fas fa-check-circle');
    
    // Start periodic updates
    startPeriodicUpdates();
    
    // Load initial data
    await updateDashboardWithAnimation();
    
    // Show system ready notification
    setTimeout(() => {
        addActivityItem('system', 'Dashboard Ready', 'Real-time monitoring active. Ready for AI optimization and SLA requests.', 'fas fa-tachometer-alt');
    }, 2000);
}

// Event listeners
function initializeEventListeners() {
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
    
    // SLA management controls
    document.getElementById('refreshSLAsBtn').addEventListener('click', refreshSLAData);
    document.getElementById('exportSLAsBtn').addEventListener('click', exportSLAData);
    
    // Enhanced SLA form validation and preview
    document.getElementById('slaTypeSelect').addEventListener('change', updateSLAPreview);
    document.getElementById('computeType').addEventListener('change', updateSLAPreview);
    document.getElementById('computeUnits').addEventListener('input', handleSLAFormInput);
    document.getElementById('durationHours').addEventListener('input', handleSLAFormInput);
    document.getElementById('preferredRegion').addEventListener('change', updateSLAPreview);
    document.getElementById('companyName').addEventListener('input', updateSLAPreview);
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);
    
    // Maintenance & Optimization event listeners
    document.getElementById('predictMaintenanceBtn').addEventListener('click', predictMaintenance);
    document.getElementById('optimizeHardwareBtn').addEventListener('click', optimizeHardware);
    document.getElementById('scheduleMaintenanceBtn').addEventListener('click', scheduleMaintenance);
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
    const companyName = document.getElementById('companyName').value.trim();
    
    // Update preview values
    document.getElementById('previewCompany').textContent = companyName || '-';
    document.getElementById('previewTier').textContent = tier.toUpperCase();
    document.getElementById('previewCompute').textContent = computeUnits > 0 ? `${computeUnits.toLocaleString()} ${computeType.toUpperCase()}` : '-';
    document.getElementById('previewDuration').textContent = durationHours > 0 ? `${durationHours} hours` : '-';
    document.getElementById('previewRegion').textContent = region === 'any' ? 'Any Available' : region.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
    
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

// Enhanced optimize system with animation
async function optimizeSystemWithAnimation() {
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
    const companyName = document.getElementById('companyName').value.trim();
    
    // Add null checks before using toUpperCase()
    if (!tier || !computeType) {
        showNotification('⚠️ Please select both SLA tier and compute type', 'warning', 4000);
        return;
    }
    
    if (!validateSLAInputs(tier, computeUnits, durationHours, companyName)) {
        return;
    }
    
    // Show SLA processing animation
    const slaBtn = document.getElementById('requestSlaBtn');
    slaBtn.classList.add('processing');
    slaBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    
    addActivityItem('sla', 'SLA Request Submitted', 
        `Processing ${tier.toUpperCase()} SLA request for ${companyName || 'Unknown Client'}: ${computeUnits.toLocaleString()} ${computeType.toUpperCase()} over ${durationHours} hours`, 
        'fas fa-paper-plane');
    
    try {
        showNotification(`🔄 Processing ${tier.toUpperCase()} SLA request for ${companyName || 'client'}: ${computeUnits} ${computeType.toUpperCase()}...`, 'info', 2000);
        
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
                preferred_region: preferredRegion === 'any' ? null : preferredRegion,
                company_name: companyName
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to request SLA');
        }
        
        const data = await response.json();
        
        // Show success with site details
        const siteConfig = getSiteConfig(data.optimal_site);
        const siteName = siteConfig ? siteConfig.name : data.optimal_site;
        
        // Calculate expiration time for display
        const expirationDate = new Date(data.expires_at);
        const expirationStr = expirationDate.toLocaleString();
        
        // Fetch updated SLAs from backend to keep synchronized
        await fetchSLAsFromBackend();
        
        showNotification(`✅ ${tier.toUpperCase()} SLA allocated successfully!\n🏢 Client: ${companyName || 'Unknown Client'}\n📍 Site: ${siteName}\n💻 Compute: ${data.compute_units_allocated} ${data.compute_type.toUpperCase()}\n⚡ Est. Power: ${data.estimated_power_mw} MW\n💰 Est. Revenue: ${formatCurrency(data.estimated_revenue)}\n⏱️ Duration: ${durationHours} hours\n🎯 Uptime: ${data.estimated_uptime}%\n⏰ Expires: ${expirationStr}`, 'success', 8000);
        
        // Add detailed activity log with workload allocation info
        addActivityItem('sla', 'SLA Request Approved', 
            `${tier.toUpperCase()} SLA for ${companyName || 'Unknown Client'} allocated to ${siteName}: ${data.compute_units_allocated} ${data.compute_type.toUpperCase()} units (${data.estimated_power_mw} MW) with ${data.estimated_uptime}% uptime guarantee. Est. revenue: ${formatCurrency(data.estimated_revenue)}. Expires: ${expirationStr}`, 
            'fas fa-handshake');
        
        // Show workload impact
        addActivityItem('system', 'Workload Allocation Updated', 
            `Site ${siteName} now running AI inference workload for ${companyName || 'client'}. ${computeUnits} ${computeType.toUpperCase()} units allocated, remaining capacity will continue Bitcoin mining.`, 
            'fas fa-cogs');
        
        // Animate the SLA tier card
        animateSLATierUpdate(tier, computeUnits);
        
        // Clear form with animation
        clearSLAFormWithAnimation();
        
        // Update dashboard to show new workload allocation
        await updateDashboardWithAnimation();
        
        // Show active SLAs summary
        await updateActiveSLAsSummary();
        
        // Refresh SLA management table to show the new SLA
        if (document.querySelector('[data-tab="sla-management"]').classList.contains('active')) {
            loadSLAManagement();
        }
        
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
        slaBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Create SLA Agreement';
    }
}

// Validate SLA inputs with real-time feedback
function validateSLAInputs(tier, computeUnits, durationHours, companyName) {
    const errors = [];
    
    if (!companyName || companyName.trim().length === 0) {
        errors.push('Company/Client name is required');
    }
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
    const inputs = ['companyName', 'computeUnits', 'durationHours'];
    inputs.forEach(inputId => {
        const input = document.getElementById(inputId);
        input.style.transform = 'scale(0.95)';
        input.value = '';
        setTimeout(() => {
            input.style.transform = 'scale(1)';
        }, 200);
    });
    
    // Reset selects to default values
    document.getElementById('slaTypeSelect').value = 'premium';
    document.getElementById('computeType').value = 'gpu';
    document.getElementById('preferredRegion').value = 'any';
    
    // Update preview to reflect cleared form
    updateSLAPreview();
    
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
        showNotification('🔄 Auto-optimization running...', 'info', 2000);
        addActivityItem('ai', 'Auto-Optimization Running', 'Scheduled optimization cycle initiated', 'fas fa-clock');
        optimizeSystemWithAnimation();
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
    
    // Calculate workload breakdown
    const allocation = site.allocation || {};
    const activeSLAs = site.active_slas || {};
    
    // AI Inference workload (from SLAs)
    const aiWorkload = (allocation.gpu_compute || 0) + (allocation.asic_compute || 0);
    
    // Bitcoin Mining workload (idle mining)
    const miningWorkload = (allocation.air_miners || 0) + (allocation.hydro_miners || 0) + (allocation.immersion_miners || 0);
    
    // Workload status
    let workloadStatus = '';
    if (activeSLAs.total_slas > 0) {
        workloadStatus = `<div class="workload-status ai-active">
            <i class="fas fa-brain"></i>
            <span>AI Inference: ${activeSLAs.total_slas} SLAs (${activeSLAs.total_compute_units} units)</span>
        </div>`;
    }
    
    if (miningWorkload > 0) {
        workloadStatus += `<div class="workload-status mining-active">
            <i class="fas fa-coins"></i>
            <span>Bitcoin Mining: ${miningWorkload} miners (idle capacity)</span>
        </div>`;
    }
    
    if (!workloadStatus) {
        workloadStatus = `<div class="workload-status idle">
            <i class="fas fa-pause"></i>
            <span>Idle - No active workloads</span>
        </div>`;
    }
    
    card.innerHTML = `
        <div class="site-header">
            <div class="site-name">${site.name}</div>
            <div class="site-temp">
                <i class="fas fa-thermometer-half"></i>
                ${Math.round(site.weather.temperature)}°F
            </div>
        </div>
        
        ${workloadStatus}
        
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
        
        <div class="allocation-breakdown">
            <h4>Resource Allocation</h4>
            <div class="allocation-grid">
                <div class="allocation-item">
                    <span class="allocation-label">GPU Compute:</span>
                    <span class="allocation-value">${allocation.gpu_compute || 0}</span>
                </div>
                <div class="allocation-item">
                    <span class="allocation-label">ASIC Compute:</span>
                    <span class="allocation-value">${allocation.asic_compute || 0}</span>
                </div>
                <div class="allocation-item">
                    <span class="allocation-label">Air Miners:</span>
                    <span class="allocation-value">${allocation.air_miners || 0}</span>
                </div>
                <div class="allocation-item">
                    <span class="allocation-label">Hydro Miners:</span>
                    <span class="allocation-value">${allocation.hydro_miners || 0}</span>
                </div>
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
            case 'o':
                event.preventDefault();
                optimizeSystemWithAnimation();
                break;
            case 's':
                event.preventDefault();
                document.getElementById('slaTypeSelect').focus();
                break;
        }
    }
}

// Update active SLAs summary
async function updateActiveSLAsSummary() {
    try {
        const response = await fetch(`${API_BASE}/api/sla/active`);
        
        if (!response.ok) {
            console.warn('Failed to fetch active SLAs');
            return;
        }
        
        const data = await response.json();
        const stats = data.statistics;
        
        // Update SLA summary in the panel
        updateSLASummary({
            premium: stats.tier_breakdown.premium,
            standard: stats.tier_breakdown.standard,
            flexible: stats.tier_breakdown.flexible,
            spot: stats.tier_breakdown.spot
        });
        
        // Add activity item if there are active SLAs
        if (stats.total_active_slas > 0) {
            addActivityItem('system', 'Active SLAs Summary', 
                `Currently running ${stats.total_active_slas} SLAs with ${stats.total_compute_units} total compute units generating ${formatCurrency(stats.total_estimated_revenue)} estimated revenue`, 
                'fas fa-chart-line');
        }
        
    } catch (error) {
        console.warn('Error updating active SLAs summary:', error);
    }
}

// Maintenance & Optimization Functions

async function predictMaintenance() {
    try {
        showLoading(true, 'AI is analyzing hardware health and predicting maintenance needs...');
        addActivityItem('ai', 'Predictive Maintenance Started', 'AI analyzing hardware health across all sites for predictive maintenance', 'fas fa-crystal-ball');
        
        const response = await fetch(`${API_BASE}/api/maintenance/predictions`);
        
        if (!response.ok) {
            throw new Error('Failed to get maintenance predictions');
        }
        
        const data = await response.json();
        
        // Update maintenance metrics
        updateMaintenanceMetrics(data);
        
        // Update site maintenance status
        await updateSiteMaintenanceStatus();
        
        showLoading(false);
        showNotification(`🔮 Predictive maintenance analysis complete! Found ${data.high_risk_count} high-risk hardware units with $${data.estimated_total_savings.toLocaleString()} potential savings`, 'success', 5000);
        addActivityItem('ai', 'Predictive Maintenance Complete', `Analyzed ${data.total_predictions} hardware units, identified ${data.high_risk_count} high-risk items`, 'fas fa-check-circle');
        
    } catch (error) {
        showLoading(false);
        console.error('Error predicting maintenance:', error);
        showNotification('❌ Failed to predict maintenance: ' + error.message, 'error', 5000);
        addActivityItem('error', 'Maintenance Prediction Failed', 'Failed to analyze hardware health for predictive maintenance', 'fas fa-exclamation-triangle');
    }
}

async function optimizeHardware() {
    try {
        showLoading(true, 'AI is optimizing hardware settings for maximum performance and efficiency...');
        addActivityItem('ai', 'Hardware Optimization Started', 'AI optimizing clock speeds, voltage, and power settings across all hardware', 'fas fa-rocket');
        
        const response = await fetch(`${API_BASE}/api/hardware/optimize`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error('Failed to optimize hardware');
        }
        
        const data = await response.json();
        
        // Update optimization results
        updateOptimizationResults(data);
        
        // Update hardware optimization details
        updateHardwareOptimizationDetails(data.optimizations);
        
        showLoading(false);
        showNotification(`🚀 Hardware optimization complete! Expected ${data.summary.total_performance_gain_percent}% performance gain and $${data.summary.net_benefit.toLocaleString()} net benefit`, 'success', 5000);
        addActivityItem('ai', 'Hardware Optimization Complete', `Optimized ${data.total_optimizations} hardware units with ${data.summary.total_performance_gain_percent}% performance gain`, 'fas fa-check-circle');
        
    } catch (error) {
        showLoading(false);
        console.error('Error optimizing hardware:', error);
        showNotification('❌ Failed to optimize hardware: ' + error.message, 'error', 5000);
        addActivityItem('error', 'Hardware Optimization Failed', 'Failed to optimize hardware settings for performance and efficiency', 'fas fa-exclamation-triangle');
    }
}

async function scheduleMaintenance() {
    try {
        showLoading(true, 'AI is scheduling preventive maintenance based on predictions...');
        addActivityItem('ai', 'Maintenance Scheduling Started', 'AI creating optimal maintenance schedule based on hardware health predictions', 'fas fa-calendar-alt');
        
        const response = await fetch(`${API_BASE}/api/maintenance/schedule`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error('Failed to schedule maintenance');
        }
        
        const data = await response.json();
        
        // Update maintenance schedule
        updateMaintenanceSchedule(data);
        
        showLoading(false);
        showNotification(`📅 Maintenance schedule created! ${data.total_sites} sites scheduled with $${data.total_estimated_savings.toLocaleString()} potential savings`, 'success', 5000);
        addActivityItem('ai', 'Maintenance Schedule Complete', `Scheduled maintenance for ${data.total_hardware_units} hardware units across ${data.total_sites} sites`, 'fas fa-check-circle');
        
    } catch (error) {
        showLoading(false);
        console.error('Error scheduling maintenance:', error);
        showNotification('❌ Failed to schedule maintenance: ' + error.message, 'error', 5000);
        addActivityItem('error', 'Maintenance Scheduling Failed', 'Failed to create optimal maintenance schedule', 'fas fa-exclamation-triangle');
    }
}

function updateMaintenanceMetrics(data) {
    // Update maintenance overview metrics
    const criticalCount = data.high_risk_count;
    const maintenanceDue = Math.floor(criticalCount * 0.7); // Estimate maintenance due within 30 days
    const potentialSavings = data.estimated_total_savings;
    const avgHealth = 85; // Simulated average health score
    
    // Animate metric updates
    animateMetricUpdate('criticalHardwareCount', criticalCount);
    animateMetricUpdate('maintenanceDueCount', maintenanceDue);
    animateMetricUpdate('potentialSavings', formatCurrency(potentialSavings));
    animateMetricUpdate('avgHealthScore', avgHealth + '%');
}

function updateOptimizationResults(data) {
    const summary = data.summary;
    
    // Update optimization metrics with animation
    animateMetricUpdate('performanceGain', summary.total_performance_gain_percent + '%');
    animateMetricUpdate('powerSavings', summary.total_power_savings_percent + '%');
    animateMetricUpdate('revenueIncrease', formatCurrency(summary.total_revenue_increase));
    animateMetricUpdate('costSavings', formatCurrency(summary.total_cost_savings));
}

async function updateSiteMaintenanceStatus() {
    try {
        const siteIds = ['site_1_nordic', 'site_2_canada', 'site_3_norway', 'site_4_singapore', 'site_5_texas', 
                        'site_6_ireland', 'site_7_japan', 'site_8_australia', 'site_9_chile', 'site_10_germany'];
        
        const container = document.getElementById('siteMaintenanceContainer');
        container.innerHTML = '';
        
        for (const siteId of siteIds) {
            try {
                const response = await fetch(`${API_BASE}/api/maintenance/site/${siteId}`);
                if (response.ok) {
                    const data = await response.json();
                    const card = createSiteMaintenanceCard(data);
                    container.appendChild(card);
                }
            } catch (error) {
                console.warn(`Failed to get maintenance status for ${siteId}:`, error);
            }
        }
    } catch (error) {
        console.error('Error updating site maintenance status:', error);
    }
}

function createSiteMaintenanceCard(data) {
    const card = document.createElement('div');
    card.className = 'site-maintenance-card';
    
    const healthClass = getHealthClass(data.maintenance_summary.average_health);
    const healthText = getHealthText(data.maintenance_summary.average_health);
    
    card.innerHTML = `
        <div class="site-maintenance-header">
            <div class="site-maintenance-name">${data.site_name}</div>
            <div class="site-maintenance-health ${healthClass}">${healthText}</div>
        </div>
        <div class="site-maintenance-stats">
            <div class="site-maintenance-stat">
                <div class="site-maintenance-stat-label">Total Units</div>
                <div class="site-maintenance-stat-value">${data.maintenance_summary.total_units}</div>
            </div>
            <div class="site-maintenance-stat">
                <div class="site-maintenance-stat-label">Avg Health</div>
                <div class="site-maintenance-stat-value">${data.maintenance_summary.average_health}%</div>
            </div>
            <div class="site-maintenance-stat">
                <div class="site-maintenance-stat-label">Critical</div>
                <div class="site-maintenance-stat-value">${data.maintenance_summary.critical_units}</div>
            </div>
            <div class="site-maintenance-stat">
                <div class="site-maintenance-stat-label">Need Maintenance</div>
                <div class="site-maintenance-stat-value">${data.maintenance_summary.maintenance_needed}</div>
            </div>
        </div>
        <div class="site-maintenance-actions">
            <button class="btn-maintenance view" onclick="viewSiteMaintenance('${data.site_id}')">View Details</button>
            <button class="btn-maintenance schedule" onclick="scheduleSiteMaintenance('${data.site_id}')">Schedule</button>
        </div>
    `;
    
    return card;
}

function getHealthClass(health) {
    if (health >= 90) return 'excellent';
    if (health >= 80) return 'good';
    if (health >= 70) return 'warning';
    return 'critical';
}

function getHealthText(health) {
    if (health >= 90) return 'Excellent';
    if (health >= 80) return 'Good';
    if (health >= 70) return 'Warning';
    return 'Critical';
}

function updateMaintenanceSchedule(data) {
    const container = document.getElementById('maintenanceScheduleContainer');
    container.innerHTML = '';
    
    data.recommended_schedule.forEach((schedule, index) => {
        const item = document.createElement('div');
        item.className = 'maintenance-schedule-item';
        
        const scheduledDate = new Date(schedule.scheduled_date);
        const formattedDate = scheduledDate.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric', 
            year: 'numeric' 
        });
        
        item.innerHTML = `
            <div class="maintenance-schedule-info">
                <div class="maintenance-schedule-site">${schedule.site_name}</div>
                <div class="maintenance-schedule-details">
                    <span>Scheduled: ${formattedDate}</span>
                    <span>Duration: ${schedule.estimated_duration}h</span>
                    <span>Hardware: ${schedule.hardware_count} units</span>
                </div>
            </div>
            <div class="maintenance-schedule-priority ${schedule.priority}">${schedule.priority}</div>
        `;
        
        container.appendChild(item);
    });
}

function updateHardwareOptimizationDetails(optimizations) {
    const container = document.getElementById('hardwareOptimizationContainer');
    container.innerHTML = '';
    
    // Show first 6 optimizations
    optimizations.slice(0, 6).forEach(optimization => {
        const card = document.createElement('div');
        card.className = 'hardware-optimization-card';
        
        const settingsHtml = Object.entries(optimization.optimized_settings)
            .map(([key, value]) => `
                <div class="hardware-setting">
                    <div class="hardware-setting-label">${key.replace(/_/g, ' ').toUpperCase()}</div>
                    <div class="hardware-setting-value">${typeof value === 'number' ? value.toFixed(2) : value}</div>
                </div>
            `).join('');
        
        const improvementsHtml = Object.entries(optimization.expected_improvements)
            .map(([key, value]) => {
                const isPositive = key.includes('gain') || key.includes('savings') || key.includes('increase');
                const displayValue = typeof value === 'number' ? 
                    (isPositive ? '+' : '') + value.toFixed(1) + (key.includes('percent') ? '%' : '') :
                    formatCurrency(value);
                
                return `
                    <div class="hardware-improvement">
                        <div class="hardware-improvement-label">${key.replace(/_/g, ' ').toUpperCase()}</div>
                        <div class="hardware-improvement-value ${isPositive ? 'positive' : 'negative'}">${displayValue}</div>
                    </div>
                `;
            }).join('');
        
        card.innerHTML = `
            <div class="hardware-optimization-header">
                <div class="hardware-optimization-id">${optimization.hardware_id}</div>
                <div class="hardware-optimization-type ${optimization.hardware_type}">${optimization.hardware_type.toUpperCase()}</div>
            </div>
            <div class="hardware-optimization-settings">
                ${settingsHtml}
            </div>
            <div class="hardware-optimization-improvements">
                ${improvementsHtml}
            </div>
            <div class="hardware-optimization-risk ${optimization.risk_assessment}">${optimization.risk_assessment} Risk</div>
        `;
        
        container.appendChild(card);
    });
}

// Site maintenance action functions
function viewSiteMaintenance(siteId) {
    showNotification(`Viewing detailed maintenance status for ${siteId}`, 'info', 3000);
    addActivityItem('system', 'Site Maintenance View', `Viewing detailed maintenance status for site ${siteId}`, 'fas fa-eye');
}

function scheduleSiteMaintenance(siteId) {
    showNotification(`Scheduling maintenance for ${siteId}`, 'info', 3000);
    addActivityItem('system', 'Site Maintenance Schedule', `Scheduling maintenance for site ${siteId}`, 'fas fa-calendar-plus');
}

// Enhanced AI Intelligence Functions
async function loadAIIntelligence() {
    addActivityItem('ai', 'AI Intelligence Dashboard Loading', 'Loading Claude-powered hardware health analysis and optimization recommendations', 'fas fa-brain');
    
    // Initialize enhanced AI dashboard components
    await updateAdvancedAIHealthAnalysis();
    await updateClaudeOptimizationRecommendations();
    await loadMaintenanceDatabase();
    initializeAICharts();
    
    // Set up periodic AI updates with Claude integration
    startAdvancedAIMonitoring();
}

async function updateAdvancedAIHealthAnalysis() {
    try {
        showLoading(true, 'Claude AI analyzing hardware health across all sites...');
        
        // Get advanced AI health analysis from the enhanced API
        const response = await fetch(`${API_BASE}/api/ai/health-analysis`);
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        const data = await response.json();
        const healthAnalysis = data.health_analysis;
        
        // Update health score with enhanced data
        const overallHealth = healthAnalysis.basic_health_analysis.overall_health_score;
        updateHealthScore(overallHealth);
        
        // Update machine health matrix with detailed hardware units
        updateEnhancedMachineHealthMatrix(healthAnalysis);
        
        // Update predictive alerts with advanced failure predictions
        updateAdvancedPredictiveAlerts(healthAnalysis.basic_health_analysis.predicted_failures);
        
        showLoading(false);
        
        const detailedUnits = healthAnalysis.detailed_hardware_units || 0;
        const claudeStatus = data.claude_integration === 'active' ? 'Claude AI Active' : 'Fallback Mode';
        
        addActivityItem('ai', 'Advanced Health Analysis Complete', 
            `${claudeStatus}: Analyzed ${detailedUnits} detailed hardware units, health score: ${overallHealth.toFixed(1)}%`, 
            'fas fa-check-circle');
        
    } catch (error) {
        showLoading(false);
        console.error('Advanced AI health analysis error:', error);
        addActivityItem('error', 'Advanced AI Analysis Failed', 'Failed to analyze hardware health with Claude AI', 'fas fa-exclamation-triangle');
        
        // Fallback to basic analysis
        await updateAIHealthAnalysisFallback();
    }
}

async function updateClaudeOptimizationRecommendations() {
    try {
        // Get Claude-powered optimization recommendations
        const response = await fetch(`${API_BASE}/api/ai/optimization-recommendations`);
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        const data = await response.json();
        const claudeStrategy = data.claude_strategy;
        
        // Update efficiency metrics with Claude strategy data
        updateClaudeEfficiencyMetrics(claudeStrategy);
        
        // Update optimization cards with Claude recommendations
        updateClaudeOptimizationCards(claudeStrategy, data.basic_optimizations);
        
        const claudeStatus = claudeStrategy ? 'Claude AI Active' : 'Basic Mode';
        addActivityItem('ai', 'Claude Optimization Complete', 
            `${claudeStatus}: Generated ${claudeStrategy.expected_impact.performance || 0}% performance improvement strategy`, 
            'fas fa-rocket');
        
    } catch (error) {
        console.error('Claude optimization analysis error:', error);
        addActivityItem('error', 'Claude Optimization Failed', 'Failed to generate Claude optimization recommendations', 'fas fa-exclamation-triangle');
        
        // Fallback to basic optimization
        await updateAIOptimizationRecommendationsFallback();
    }
}

async function loadMaintenanceDatabase() {
    try {
        // Load maintenance database status and recent tasks
        const response = await fetch(`${API_BASE}/api/ai/maintenance-database`);
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Update maintenance dashboard with database info
        updateMaintenanceDatabaseStatus(data);
        
        addActivityItem('ai', 'Maintenance Database Loaded', 
            `Connected to maintenance database: ${data.summary.total_scheduled_tasks} tasks, ${data.summary.critical_tasks} critical`, 
            'fas fa-database');
        
    } catch (error) {
        console.error('Maintenance database load error:', error);
        addActivityItem('error', 'Maintenance Database Error', 'Failed to load maintenance database', 'fas fa-exclamation-triangle');
    }
}

// Fallback functions for when Claude API is not available
async function updateAIHealthAnalysisFallback() {
    const currentMachines = {
        'immersion_miners': 10, 'air_miners': 15, 'hydro_miners': 8, 'asic_compute': 25, 'gpu_compute': 30
    };
    
    const healthData = await simulateAIHealthAnalysis(currentMachines);
    updateHealthScore(healthData.overall_health_score);
    updateMachineHealthMatrix(healthData);
    updatePredictiveAlerts(healthData.predicted_failures);
}

async function updateAIOptimizationRecommendationsFallback() {
    const currentMachines = {
        'immersion_miners': 10, 'air_miners': 15, 'hydro_miners': 8, 'asic_compute': 25, 'gpu_compute': 30
    };
    
    const optimizationData = await simulateAIOptimization(currentMachines);
    updateEfficiencyMetrics(optimizationData);
    updateOptimizationCards(optimizationData);
}

function updateHealthScore(healthScore) {
    const scoreElement = document.getElementById('overallHealthScore');
    const statusElement = document.getElementById('healthStatus');
    
    if (scoreElement && statusElement) {
        // Animate score update
        scoreElement.style.setProperty('--score', healthScore);
        scoreElement.textContent = Math.round(healthScore) + '%';
        
        // Update status based on score
        statusElement.classList.remove('optimal', 'good', 'critical');
        if (healthScore >= 90) {
            statusElement.textContent = 'Optimal';
            statusElement.classList.add('optimal');
        } else if (healthScore >= 80) {
            statusElement.textContent = 'Good';
            statusElement.classList.add('good');
        } else {
            statusElement.textContent = 'Critical';
            statusElement.classList.add('critical');
        }
        
        // Add pulse animation
        scoreElement.style.animation = 'none';
        scoreElement.offsetHeight; // Trigger reflow
        scoreElement.style.animation = 'healthPulse 3s ease-in-out infinite';
    }
}

function updateMachineHealthMatrix(healthData) {
    const container = document.getElementById('machineHealthGrid');
    if (!container) return;
    
    container.innerHTML = '';
    
    const machineTypes = {
        'immersion_miners': { name: 'Immersion Miners', count: 10, icon: 'fas fa-water' },
        'air_miners': { name: 'Air Miners', count: 15, icon: 'fas fa-wind' },
        'hydro_miners': { name: 'Hydro Miners', count: 8, icon: 'fas fa-tint' },
        'asic_compute': { name: 'ASIC Compute', count: 25, icon: 'fas fa-microchip' },
        'gpu_compute': { name: 'GPU Compute', count: 30, icon: 'fas fa-desktop' }
    };
    
    Object.entries(machineTypes).forEach(([type, info]) => {
        const group = document.createElement('div');
        group.className = 'machine-group';
        
        // Simulate health status for each unit
        const units = [];
        for (let i = 1; i <= info.count; i++) {
            const healthRandom = Math.random();
            let status = 'healthy';
            if (healthRandom < 0.05) status = 'critical';
            else if (healthRandom < 0.15) status = 'warning';
            
            units.push({ id: i, status });
        }
        
        const healthyCount = units.filter(u => u.status === 'healthy').length;
        const warningCount = units.filter(u => u.status === 'warning').length;
        const criticalCount = units.filter(u => u.status === 'critical').length;
        
        const avgHealth = ((healthyCount * 95) + (warningCount * 75) + (criticalCount * 40)) / info.count;
        const predictedUptime = Math.max(95, avgHealth + Math.random() * 5);
        
        group.innerHTML = `
            <h4><i class="${info.icon}"></i> ${info.name} (${info.count} units)</h4>
            <div class="machine-status-row">
                ${units.map(unit => `
                    <div class="machine-item ${unit.status}">
                        Unit ${unit.id}${unit.status === 'critical' ? ' 🔴' : unit.status === 'warning' ? ' ⚠️' : ''}
                    </div>
                `).join('')}
            </div>
            <div class="group-stats">
                Avg Health: ${Math.round(avgHealth)}% | Predicted Uptime: ${predictedUptime.toFixed(1)}%
                <br>Healthy: ${healthyCount} | Warning: ${warningCount} | Critical: ${criticalCount}
            </div>
        `;
        
        container.appendChild(group);
    });
}

function updatePredictiveAlerts(predictedFailures) {
    const container = document.getElementById('predictiveAlertsList');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (predictedFailures.length === 0) {
        container.innerHTML = `
            <div class="alert good">
                <div class="alert-icon"><i class="fas fa-check-circle"></i></div>
                <div class="alert-content">
                    <strong>All Systems Healthy</strong>
                    <p>No critical failure predictions detected. All hardware operating within normal parameters.</p>
                    <span class="timestamp">Last analyzed: ${new Date().toLocaleTimeString()}</span>
                </div>
            </div>
        `;
        return;
    }
    
    predictedFailures.slice(0, 5).forEach(failure => {
        const alert = document.createElement('div');
        alert.className = `alert ${failure.priority}`;
        
        const failureDate = new Date(failure.estimated_failure_date);
        const timeUntilFailure = Math.ceil((failureDate - new Date()) / (1000 * 60 * 60)); // hours
        
        const iconMap = {
            'immersion_miners': 'fas fa-water',
            'air_miners': 'fas fa-wind',
            'hydro_miners': 'fas fa-tint',
            'asic_compute': 'fas fa-microchip',
            'gpu_compute': 'fas fa-desktop'
        };
        
        const actionMap = {
            'coolant_system_check': 'Optimize Cooling',
            'immediate_coolant_replacement': 'Replace Coolant',
            'fan_cleaning_and_replacement': 'Service Fans',
            'thermal_system_overhaul': 'Thermal Service',
            'pump_inspection_and_cleaning': 'Service Pump',
            'cooling_loop_replacement': 'Replace Loop',
            'thermal_paste_replacement': 'Replace Thermal Paste',
            'complete_thermal_analysis': 'Thermal Analysis',
            'gpu_cleaning_and_optimization': 'Optimize GPU',
            'gpu_replacement_planning': 'Plan Replacement'
        };
        
        alert.innerHTML = `
            <div class="alert-icon">
                <i class="${iconMap[failure.machine_type] || 'fas fa-exclamation-triangle'}"></i>
            </div>
            <div class="alert-content">
                <strong>${failure.machine_id.replace(/_/g, ' ').toUpperCase()}</strong>
                <p>${Math.round(failure.failure_probability * 100)}% failure probability - ${timeUntilFailure}h until predicted failure</p>
                <span class="timestamp">Predicted failure: ${failureDate.toLocaleString()}</span>
            </div>
            <button class="alert-action" onclick="scheduleMaintenanceAction('${failure.machine_id}', '${failure.recommended_action}')">
                ${actionMap[failure.recommended_action] || 'Schedule Maintenance'}
            </button>
        `;
        
        container.appendChild(alert);
    });
}

function updateEfficiencyMetrics(optimizationData) {
    const summary = optimizationData.summary;
    
    // Update power efficiency
    const currentEfficiency = 87.3 + (summary.total_power_savings_percent || 0);
    const efficiencyElement = document.getElementById('currentEfficiency');
    if (efficiencyElement) {
        efficiencyElement.textContent = `${currentEfficiency.toFixed(1)}%`;
    }
    
    // Update revenue potential
    const additionalRevenue = summary.net_benefit || 0;
    const revenueElement = document.getElementById('additionalRevenue');
    if (revenueElement) {
        revenueElement.textContent = `+$${additionalRevenue.toFixed(2)}/hour`;
    }
}

function updateOptimizationCards(optimizationData) {
    const container = document.getElementById('aiOptimizationCards');
    if (!container) return;
    
    const summary = optimizationData.summary;
    
    container.innerHTML = `
        <div class="opt-card energy">
            <h4><i class="fas fa-leaf"></i> Energy Optimization</h4>
            <div class="savings">Potential savings: ${summary.total_power_savings_percent}%</div>
            <div class="recommendation">
                Optimize cooling systems and reduce power consumption through AI-driven efficiency improvements
            </div>
            <button class="apply-opt" onclick="applyAIOptimization('energy')">
                Apply (-$${(summary.total_cost_savings || 0).toFixed(2)}/hour energy cost)
            </button>
        </div>
        
        <div class="opt-card performance">
            <h4><i class="fas fa-rocket"></i> Performance Optimization</h4>
            <div class="increase">Potential increase: +${summary.total_performance_gain_percent}% performance</div>
            <div class="recommendation">
                Optimize clock speeds, voltage, and thermal management based on current operating conditions
            </div>
            <button class="apply-opt" onclick="applyAIOptimization('performance')">
                Apply (+$${summary.total_revenue_increase.toFixed(2)}/hour revenue)
            </button>
        </div>
        
        <div class="opt-card allocation">
            <h4><i class="fas fa-balance-scale"></i> Resource Allocation</h4>
            <div class="revenue">Net benefit: +$${summary.net_benefit.toFixed(2)}/hour</div>
            <div class="recommendation">
                Reallocate compute resources based on current market conditions and efficiency metrics
            </div>
            <button class="apply-opt" onclick="applyAIOptimization('allocation')">
                Optimize Resource Allocation
            </button>
        </div>
    `;
}

function initializeAICharts() {
    // Health Trend Chart
    const healthCtx = document.getElementById('healthTrendChart');
    if (healthCtx) {
        new Chart(healthCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: ['6h ago', '5h ago', '4h ago', '3h ago', '2h ago', '1h ago', 'Now'],
                datasets: [{
                    label: 'Overall Health %',
                    data: [89, 91, 88, 92, 90, 87, 89],
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: '#cbd5e1' }, grid: { color: 'rgba(203, 213, 225, 0.1)' } },
                    y: { 
                        ticks: { color: '#cbd5e1' }, 
                        grid: { color: 'rgba(203, 213, 225, 0.1)' },
                        min: 80,
                        max: 100
                    }
                }
            }
        });
    }
    
    // Optimization Impact Chart
    const impactCtx = document.getElementById('optimizationImpactChart');
    if (impactCtx) {
        new Chart(impactCtx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: ['Performance', 'Efficiency', 'Cost Savings', 'Revenue'],
                datasets: [{
                    data: [12.5, 8.3, 156.50, 89.25],
                    backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: '#cbd5e1' }, grid: { color: 'rgba(203, 213, 225, 0.1)' } },
                    y: { ticks: { color: '#cbd5e1' }, grid: { color: 'rgba(203, 213, 225, 0.1)' } }
                }
            }
        });
    }
    
    // Failure Predictions Chart
    const predictionsCtx = document.getElementById('predictionsChart');
    if (predictionsCtx) {
        new Chart(predictionsCtx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['Healthy', 'At Risk', 'Critical'],
                datasets: [{
                    data: [82, 15, 3],
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
                        labels: { color: '#f8fafc', padding: 20 }
                    }
                }
            }
        });
    }
}

async function applyAIOptimization(type) {
    try {
        showLoading(true, `Applying AI ${type} optimization...`);
        addActivityItem('ai', 'AI Optimization Started', `Applying ${type} optimization recommendations`, 'fas fa-cogs');
        
        // Simulate optimization application
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Simulate results
        const results = {
            energy: { savings: 89.50, metric: 'energy cost reduction' },
            performance: { savings: 156.30, metric: 'revenue increase' },
            allocation: { savings: 234.70, metric: 'net benefit' }
        };
        
        const result = results[type];
        
        showLoading(false);
        showNotification(`✅ ${type.charAt(0).toUpperCase() + type.slice(1)} optimization applied successfully! Generated $${result.savings}/hour ${result.metric}`, 'success', 5000);
        addActivityItem('ai', 'AI Optimization Complete', `${type} optimization applied: +$${result.savings}/hour ${result.metric}`, 'fas fa-check-circle');
        
        // Refresh AI analysis
        setTimeout(() => {
            updateAIHealthAnalysis();
            updateAIOptimizationRecommendations();
        }, 1000);
        
    } catch (error) {
        showLoading(false);
        console.error('AI optimization error:', error);
        showNotification('❌ Failed to apply optimization: ' + error.message, 'error');
        addActivityItem('error', 'AI Optimization Failed', `Error applying ${type} optimization`, 'fas fa-exclamation-triangle');
    }
}

function scheduleMaintenanceAction(machineId, action) {
    showNotification(`Scheduling ${action.replace(/_/g, ' ')} for ${machineId}`, 'success', 3000);
    addActivityItem('ai', 'Maintenance Scheduled', `Scheduled ${action.replace(/_/g, ' ')} for ${machineId}`, 'fas fa-calendar-check');
}

// Enhanced AI Functions for Claude Integration

function updateEnhancedMachineHealthMatrix(healthAnalysis) {
    const container = document.getElementById('machineHealthGrid');
    if (!container) return;
    
    container.innerHTML = '';
    
    const hardwareOverview = healthAnalysis.hardware_fleet_overview || {};
    const machineTypes = {
        'immersion_miners': { name: 'Immersion Miners', count: 10, icon: 'fas fa-water' },
        'air_miners': { name: 'Air Miners', count: 15, icon: 'fas fa-wind' },
        'hydro_miners': { name: 'Hydro Miners', count: 8, icon: 'fas fa-tint' },
        'asic_compute': { name: 'ASIC Compute', count: 25, icon: 'fas fa-microchip' },
        'gpu_compute': { name: 'GPU Compute', count: 30, icon: 'fas fa-desktop' }
    };
    
    Object.entries(machineTypes).forEach(([type, info]) => {
        const group = document.createElement('div');
        group.className = 'machine-group enhanced';
        
        // Get real hardware units for this type
        const typeUnits = Object.values(hardwareOverview).filter(unit => unit.machine_type === type);
        const actualCount = typeUnits.length || info.count;
        
        // Calculate real health statistics
        let healthyCount = 0, warningCount = 0, criticalCount = 0;
        
        if (typeUnits.length > 0) {
            typeUnits.forEach(unit => {
                if (unit.health_score >= 85) healthyCount++;
                else if (unit.health_score >= 70) warningCount++;
                else criticalCount++;
            });
        } else {
            // Fallback simulation
            healthyCount = Math.floor(actualCount * 0.8);
            warningCount = Math.floor(actualCount * 0.15);
            criticalCount = actualCount - healthyCount - warningCount;
        }
        
        const avgHealth = typeUnits.length > 0 ? 
            typeUnits.reduce((sum, unit) => sum + unit.health_score, 0) / typeUnits.length :
            85 + Math.random() * 10;
        
        const predictedUptime = Math.max(95, avgHealth + Math.random() * 5);
        
        // Create unit grid with real data
        const unitElements = [];
        for (let i = 0; i < actualCount; i++) {
            const unit = typeUnits[i];
            let status = 'healthy';
            
            if (unit) {
                if (unit.health_score < 70) status = 'critical';
                else if (unit.health_score < 85) status = 'warning';
                
                // Show failure indicators if any
                const indicators = unit.failure_indicators?.length > 0 ? 
                    ` (${unit.failure_indicators.slice(0, 2).join(', ')})` : '';
                
                unitElements.push(`
                    <div class="machine-item ${status}" title="Health: ${unit.health_score.toFixed(1)}%${indicators}">
                        Unit ${i + 1}${status === 'critical' ? ' 🔴' : status === 'warning' ? ' ⚠️' : ''}
                    </div>
                `);
            } else {
                // Fallback for units without detailed data
                const healthRandom = Math.random();
                if (healthRandom < 0.05) status = 'critical';
                else if (healthRandom < 0.15) status = 'warning';
                
                unitElements.push(`
                    <div class="machine-item ${status}">
                        Unit ${i + 1}${status === 'critical' ? ' 🔴' : status === 'warning' ? ' ⚠️' : ''}
                    </div>
                `);
            }
        }
        
        group.innerHTML = `
            <h4><i class="${info.icon}"></i> ${info.name} (${actualCount} units)</h4>
            <div class="machine-status-row">
                ${unitElements.join('')}
            </div>
            <div class="group-stats enhanced">
                Avg Health: ${Math.round(avgHealth)}% | Predicted Uptime: ${predictedUptime.toFixed(1)}%
                <br>Healthy: ${healthyCount} | Warning: ${warningCount} | Critical: ${criticalCount}
                ${typeUnits.length > 0 ? '<br><span class="claude-enhanced">📡 Claude AI Enhanced</span>' : ''}
            </div>
        `;
        
        container.appendChild(group);
    });
}

function updateAdvancedPredictiveAlerts(predictedFailures) {
    const container = document.getElementById('predictiveAlertsList');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (!predictedFailures || predictedFailures.length === 0) {
        container.innerHTML = `
            <div class="alert good claude-enhanced">
                <div class="alert-icon"><i class="fas fa-check-circle"></i></div>
                <div class="alert-content">
                    <strong>All Systems Healthy - Claude AI Verified</strong>
                    <p>No critical failure predictions detected. Claude AI confirms all hardware operating within normal parameters.</p>
                    <span class="timestamp">Last analyzed: ${new Date().toLocaleTimeString()}</span>
                </div>
            </div>
        `;
        return;
    }
    
    predictedFailures.slice(0, 5).forEach(failure => {
        const alert = document.createElement('div');
        alert.className = `alert ${failure.priority} claude-enhanced`;
        
        const failureDate = new Date(failure.estimated_failure_date);
        const timeUntilFailure = Math.ceil((failureDate - new Date()) / (1000 * 60 * 60));
        
        const iconMap = {
            'immersion_miners': 'fas fa-water',
            'air_miners': 'fas fa-wind',
            'hydro_miners': 'fas fa-tint',
            'asic_compute': 'fas fa-microchip',
            'gpu_compute': 'fas fa-desktop'
        };
        
        const actionMap = {
            'immediate_maintenance': 'Emergency Maintenance',
            'schedule_maintenance_soon': 'Schedule Soon',
            'monitor_closely': 'Monitor Closely',
            'routine_monitoring': 'Routine Check'
        };
        
        alert.innerHTML = `
            <div class="alert-icon">
                <i class="${iconMap[failure.machine_type] || 'fas fa-exclamation-triangle'}"></i>
            </div>
            <div class="alert-content">
                <strong>${failure.machine_id.replace(/_/g, ' ').toUpperCase()}</strong>
                <p>Claude AI predicts ${Math.round(failure.failure_probability * 100)}% failure probability - ${timeUntilFailure}h until predicted failure</p>
                <span class="timestamp">Claude prediction: ${failureDate.toLocaleString()}</span>
            </div>
            <button class="alert-action" onclick="scheduleClaudeMaintenanceAction('${failure.machine_id}', '${failure.recommended_action}')">
                ${actionMap[failure.recommended_action] || 'Schedule Maintenance'}
            </button>
        `;
        
        container.appendChild(alert);
    });
}

function updateClaudeEfficiencyMetrics(claudeStrategy) {
    // Update power efficiency with Claude data
    const currentEfficiency = 87.3 + (claudeStrategy.expected_impact.efficiency || 0);
    const efficiencyElement = document.getElementById('currentEfficiency');
    if (efficiencyElement) {
        efficiencyElement.textContent = `${currentEfficiency.toFixed(1)}%`;
        efficiencyElement.classList.add('claude-enhanced');
    }
    
    // Update revenue potential with Claude predictions
    const additionalRevenue = claudeStrategy.expected_impact.revenue || 0;
    const revenueElement = document.getElementById('additionalRevenue');
    if (revenueElement) {
        revenueElement.textContent = `+$${additionalRevenue.toFixed(2)}/hour`;
        revenueElement.classList.add('claude-enhanced');
    }
}

function updateClaudeOptimizationCards(claudeStrategy, basicOptimizations) {
    const container = document.getElementById('aiOptimizationCards');
    if (!container) return;
    
    const impact = claudeStrategy.expected_impact;
    const steps = claudeStrategy.implementation_steps || [];
    
    container.innerHTML = `
        <div class="opt-card energy claude-powered">
            <h4><i class="fas fa-leaf"></i> Claude Energy Optimization</h4>
            <div class="savings">Potential savings: ${impact.efficiency || 8.5}%</div>
            <div class="recommendation">
                ${steps[0] || 'Optimize cooling systems and reduce power consumption through Claude AI analysis'}
            </div>
            <div class="claude-confidence">Confidence: ${Math.round((claudeStrategy.confidence_score || 0.85) * 100)}%</div>
            <button class="apply-opt" onclick="applyClaudeOptimization('energy', '${claudeStrategy.strategy_id}')">
                Apply Claude Strategy (-$${(impact.efficiency * 20 || 156).toFixed(2)}/hour energy cost)
            </button>
        </div>
        
        <div class="opt-card performance claude-powered">
            <h4><i class="fas fa-rocket"></i> Claude Performance Optimization</h4>
            <div class="increase">Potential increase: +${impact.performance || 12.5}% performance</div>
            <div class="recommendation">
                ${steps[1] || 'Optimize hardware settings based on Claude AI market analysis and thermal profiling'}
            </div>
            <div class="claude-confidence">Confidence: ${Math.round((claudeStrategy.confidence_score || 0.85) * 100)}%</div>
            <button class="apply-opt" onclick="applyClaudeOptimization('performance', '${claudeStrategy.strategy_id}')">
                Apply Claude Strategy (+$${(impact.revenue || 234).toFixed(2)}/hour revenue)
            </button>
        </div>
        
        <div class="opt-card allocation claude-powered">
            <h4><i class="fas fa-brain"></i> Claude Strategic Allocation</h4>
            <div class="revenue">Claude analysis: +$${(impact.revenue || 234).toFixed(2)}/hour</div>
            <div class="recommendation">
                ${claudeStrategy.claude_reasoning ? claudeStrategy.claude_reasoning.substring(0, 100) + '...' : 'Reallocate resources based on Claude AI market intelligence'}
            </div>
            <div class="claude-confidence">Risk: ${claudeStrategy.risk_assessment || 'low'}</div>
            <button class="apply-opt" onclick="applyClaudeOptimization('allocation', '${claudeStrategy.strategy_id}')">
                Apply Full Claude Strategy
            </button>
        </div>
    `;
}

function updateMaintenanceDatabaseStatus(data) {
    // Add a maintenance database status indicator
    const aiHeader = document.querySelector('.ai-header');
    if (aiHeader && !document.getElementById('maintenanceDbStatus')) {
        const dbStatusCard = document.createElement('div');
        dbStatusCard.id = 'maintenanceDbStatus';
        dbStatusCard.className = 'ai-metric-card maintenance-db';
        dbStatusCard.innerHTML = `
            <h3><i class="fas fa-database"></i> Maintenance Database</h3>
            <div class="db-status active">Connected</div>
            <div class="db-stats">
                <div>Tasks: ${data.summary.total_scheduled_tasks}</div>
                <div>Critical: ${data.summary.critical_tasks}</div>
                <div>Savings: $${data.summary.total_predicted_savings.toLocaleString()}</div>
            </div>
        `;
        aiHeader.appendChild(dbStatusCard);
    }
}

async function applyClaudeOptimization(type, strategyId) {
    try {
        showLoading(true, `Applying Claude AI ${type} optimization strategy...`);
        addActivityItem('ai', 'Claude Optimization Started', `Applying Claude AI ${type} optimization with strategy ${strategyId}`, 'fas fa-brain');
        
        const response = await fetch(`${API_BASE}/api/ai/apply-optimization`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type, strategy_id: strategyId })
        });
        
        if (!response.ok) {
            throw new Error(`Optimization failed: ${response.status}`);
        }
        
        const data = await response.json();
        const result = data.optimization_result;
        
        showLoading(false);
        
        if (result.type === 'claude_strategy') {
            const improvements = result.claude_optimizations;
            showNotification(`✅ Claude AI optimization applied successfully! 
Performance: +${improvements.performance_gain_percent}% 
Efficiency: +${improvements.energy_efficiency_improvement}% 
Revenue: +$${improvements.revenue_increase_per_hour}/hour`, 'success', 8000);
            
            addActivityItem('ai', 'Claude Optimization Complete', 
                `Claude strategy applied: +${improvements.performance_gain_percent}% performance, +$${improvements.revenue_increase_per_hour}/hour revenue`, 
                'fas fa-check-circle');
        } else {
            // Handle standard optimization results
            const metrics = result.savings || result.improvements || result.reallocation;
            const metricKeys = Object.keys(metrics);
            const primaryMetric = metrics[metricKeys[0]];
            
            showNotification(`✅ ${type.charAt(0).toUpperCase() + type.slice(1)} optimization applied! Primary improvement: ${primaryMetric}`, 'success', 5000);
            addActivityItem('ai', 'Optimization Complete', `${type} optimization applied successfully`, 'fas fa-check-circle');
        }
        
        // Refresh AI analysis after optimization
        setTimeout(() => {
            updateAdvancedAIHealthAnalysis();
            updateClaudeOptimizationRecommendations();
        }, 1000);
        
    } catch (error) {
        showLoading(false);
        console.error('Claude optimization error:', error);
        showNotification('❌ Failed to apply Claude optimization: ' + error.message, 'error');
        addActivityItem('error', 'Claude Optimization Failed', `Error applying ${type} optimization`, 'fas fa-exclamation-triangle');
    }
}

function scheduleClaudeMaintenanceAction(machineId, action) {
    showNotification(`Scheduling Claude AI ${action.replace(/_/g, ' ')} for ${machineId}`, 'success', 3000);
    addActivityItem('ai', 'Claude Maintenance Scheduled', `Claude AI scheduled ${action.replace(/_/g, ' ')} for ${machineId}`, 'fas fa-calendar-check');
}

let aiMonitoringInterval = null;

function startAdvancedAIMonitoring() {
    if (aiMonitoringInterval) return;
    
    // Update advanced AI analysis every 3 minutes (Claude API has rate limits)
    aiMonitoringInterval = setInterval(() => {
        updateAdvancedAIHealthAnalysis();
        updateClaudeOptimizationRecommendations();
    }, 180000);
    
    addActivityItem('ai', 'Advanced AI Monitoring Started', 'Real-time Claude AI hardware monitoring and optimization active', 'fas fa-brain');
}

function stopAIMonitoring() {
    if (aiMonitoringInterval) {
        clearInterval(aiMonitoringInterval);
        aiMonitoringInterval = null;
        addActivityItem('ai', 'AI Monitoring Stopped', 'Real-time AI monitoring paused', 'fas fa-pause');
    }
}

// AI Simulation Functions
async function simulateAIHealthAnalysis(machineAllocation) {
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    const total_units = Object.values(machineAllocation).reduce((sum, count) => sum + count, 0);
    const critical_count = Math.floor(Math.random() * 5) + 1; // 1-5 critical units
    const overall_health = 85 + Math.random() * 10; // 85-95% health
    
    // Generate predicted failures
    const predicted_failures = [];
    const machine_types = Object.keys(machineAllocation);
    
    for (let i = 0; i < critical_count; i++) {
        const machine_type = machine_types[Math.floor(Math.random() * machine_types.length)];
        const failure_prob = 0.3 + Math.random() * 0.4; // 30-70% failure probability
        const days_ahead = failure_prob > 0.6 ? Math.random() * 7 : Math.random() * 30;
        
        const actions = {
            'immersion_miners': ['coolant_system_check', 'immediate_coolant_replacement'],
            'air_miners': ['fan_cleaning_and_replacement', 'thermal_system_overhaul'],
            'hydro_miners': ['pump_inspection_and_cleaning', 'cooling_loop_replacement'],
            'asic_compute': ['thermal_paste_replacement', 'complete_thermal_analysis'],
            'gpu_compute': ['gpu_cleaning_and_optimization', 'gpu_replacement_planning']
        };
        
        const machine_actions = actions[machine_type] || ['general_maintenance_check'];
        const recommended_action = machine_actions[Math.floor(Math.random() * machine_actions.length)];
        
        predicted_failures.push({
            machine_type,
            machine_id: `${machine_type}_${i + 1}`,
            failure_probability: failure_prob,
            estimated_failure_date: new Date(Date.now() + days_ahead * 24 * 60 * 60 * 1000).toISOString(),
            recommended_action,
            priority: failure_prob > 0.6 ? 'critical' : 'high'
        });
    }
    
    return {
        overall_health_score: overall_health,
        total_units_analyzed: total_units,
        critical_units: critical_count,
        predicted_failures
    };
}

async function simulateAIOptimization(machineAllocation) {
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    const total_optimizations = Object.values(machineAllocation).reduce((sum, count) => sum + Math.min(count, 5), 0);
    
    return {
        optimizations: [], // Not needed for dashboard display
        total_optimizations,
        summary: {
            total_performance_gain_percent: 8.5 + Math.random() * 7, // 8.5-15.5%
            total_power_savings_percent: 3.2 + Math.random() * 5, // 3.2-8.2%
            total_revenue_increase: 125.50 + Math.random() * 200, // $125-325
            total_cost_savings: 89.25 + Math.random() * 100, // $89-189
            net_benefit: 234.70 + Math.random() * 150 // $234-384
        }
    };
}

// Add AI Intelligence button event listener
document.addEventListener('DOMContentLoaded', function() {
    // Add event listener for Apply AI Optimizations button
    const applyOptBtn = document.getElementById('applyOptimizationsBtn');
    if (applyOptBtn) {
        applyOptBtn.addEventListener('click', () => {
            applyAIOptimization('allocation');
        });
    }
}); 