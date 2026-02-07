const API_BASE = 'https://scamsense-60h2.onrender.com';
const WS_BASE = 'wss://scamsense-60h2.onrender.com';


const mouse = { x: null, y: null, radius: 150 };
window.addEventListener('mousemove', (e) => {
    mouse.x = e.x;
    mouse.y = e.y;
    // Update tilt for all glass cards
    document.querySelectorAll('.glass-card').forEach(card => matchTilt(card, e));
});

function matchTilt(card, e) {
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Only tilt if mouse is near/over the card
    if (x > -50 && x < rect.width + 50 && y > -50 && y < rect.height + 50) {
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;
        const rotateX = ((y - centerY) / centerY) * -5; // Max 5 deg tilt
        const rotateY = ((x - centerX) / centerX) * 5;

        card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
    } else {
        card.style.transform = 'perspective(1000px) rotateX(0) rotateY(0)';
    }
}


class ParticleSystem {
    constructor() {
        this.canvas = document.getElementById('canvas-container');
        this.ctx = this.canvas.getContext('2d');
        this.particles = [];
        this.resize();
        window.addEventListener('resize', () => this.resize());
        this.initParticles();
        this.animate();
    }

    resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
        this.initParticles(); // Re-init on resize to keep density correct
    }

    initParticles() {
        this.particles = [];
        const count = Math.min(window.innerWidth / 30, 40); // Optimized count heavily
        for (let i = 0; i < count; i++) {
            this.particles.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height,
                vx: (Math.random() - 0.5) * 1, // Faster
                vy: (Math.random() - 0.5) * 1,
                size: Math.random() * 2 + 1,
                baseX: Math.random() * this.canvas.width, // Remember base pos if we wanted spring physics
                baseY: Math.random() * this.canvas.height
            });
        }
    }

    animate() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        this.particles.forEach(p => {
            // Mouse Repulsion/Attraction
            if (mouse.x != null) {
                let dx = mouse.x - p.x;
                let dy = mouse.y - p.y;
                let distance = Math.sqrt(dx * dx + dy * dy);

                // Mouse interaction zone
                if (distance < mouse.radius) {
                    const forceDirectionX = dx / distance;
                    const forceDirectionY = dy / distance;
                    const force = (mouse.radius - distance) / mouse.radius;
                    // Push away
                    const directionX = forceDirectionX * force * 3;
                    const directionY = forceDirectionY * force * 3;
                    p.x -= directionX;
                    p.y -= directionY;
                }
            }

            p.x += p.vx;
            p.y += p.vy;

            // Bounce off edges
            if (p.x < 0 || p.x > this.canvas.width) p.vx *= -1;
            if (p.y < 0 || p.y > this.canvas.height) p.vy *= -1;

            this.ctx.beginPath();
            this.ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            this.ctx.fillStyle = `rgba(99, 102, 241, ${0.6 + (p.size / 10)})`; // Even Brighter
            this.ctx.fill();
        });

        // Draw connections
        this.particles.forEach((p1, i) => {
            this.particles.slice(i + 1).forEach(p2 => {
                const dx = p1.x - p2.x;
                const dy = p1.y - p2.y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < 120) {
                    this.ctx.beginPath();
                    this.ctx.moveTo(p1.x, p1.y);
                    this.ctx.lineTo(p2.x, p2.y);
                    this.ctx.strokeStyle = `rgba(139, 92, 246, ${0.15 * (1 - dist / 120)})`; // Purple lines
                    this.ctx.lineWidth = 1;
                    this.ctx.stroke();
                }
            });
        });

        // Connect to mouse
        if (mouse.x != null) {
            this.particles.forEach(p => {
                const dx = p.x - mouse.x;
                const dy = p.y - mouse.y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < 150) {
                    this.ctx.beginPath();
                    this.ctx.moveTo(p.x, p.y);
                    this.ctx.lineTo(mouse.x, mouse.y);
                    this.ctx.strokeStyle = `rgba(16, 185, 129, ${0.2 * (1 - dist / 150)})`; // Green connection to user
                    this.ctx.stroke();
                }
            });
        }

        requestAnimationFrame(() => this.animate());
    }
}


let authToken = localStorage.getItem('scamshield_token');
let userId = localStorage.getItem('scamshield_user_id');
let websocket = null;
let alerts = [];
let statsChart = null;

const elements = {
    loading: document.getElementById('loading'),
    loginScreen: document.getElementById('login-screen'),
    dashboard: document.getElementById('dashboard'),
    loginForm: document.getElementById('login-form'),
    registerForm: document.getElementById('register-form'),
    testForm: document.getElementById('analyzer-form'),
    stats: {
        blocked: document.getElementById('stat-blocked'),
        today: document.getElementById('stat-today'),
        score: document.getElementById('stat-score')
    },
    alertsContainer: document.getElementById('alerts-list'),
    resultBox: document.getElementById('result-box')
};

function init() {
    new ParticleSystem();

    // Instant Load
    elements.loading.classList.add('hidden');
    if (authToken) {
        showDashboard();
    } else {
        showLogin();
    }

    setupEventListeners();
}

function setupEventListeners() {
    // Auth switching
    document.getElementById('show-register').onclick = (e) => { e.preventDefault(); showRegister(); };
    document.getElementById('show-login').onclick = (e) => { e.preventDefault(); showLogin(); };

    // Forms
    elements.loginForm.onsubmit = handleLogin;
    elements.registerForm.onsubmit = handleRegister;
    elements.testForm.onsubmit = handleAnalysis;

    // Logout
    document.getElementById('logout-btn').onclick = logout;

    // Button ripples
    document.querySelectorAll('button').forEach(btn => {
        btn.addEventListener('click', function (e) {
            let x = e.clientX - e.target.offsetLeft;
            let y = e.clientY - e.target.offsetTop;
            let ripples = document.createElement('span');
            ripples.style.left = x + 'px';
            ripples.style.top = y + 'px';
            this.appendChild(ripples);
            setTimeout(() => {
                ripples.remove()
            }, 1000);
        })
    });
}

// Auth links
const loginSwitch = document.querySelector('.auth-switch:not(#register-switch)');
const registerSwitch = document.getElementById('register-switch');

function showLogin() {
    elements.loginScreen.classList.remove('hidden');
    elements.dashboard.classList.add('hidden');
    elements.loginForm.classList.remove('hidden');
    elements.registerForm.classList.add('hidden');

    // Show "Create Account" link, hide "Login" link
    loginSwitch.classList.remove('hidden');
    registerSwitch.classList.add('hidden');
}

function showRegister() {
    elements.registerForm.classList.remove('hidden');
    elements.loginForm.classList.add('hidden');

    // Show "Login" link, hide "Create Account" link
    loginSwitch.classList.add('hidden');
    registerSwitch.classList.remove('hidden');
}

async function showDashboard() {
    elements.loginScreen.classList.add('hidden');
    elements.dashboard.classList.remove('hidden');

    // Non-blocking initialization
    connectWebSocket();
    loadStats();
    initChart();
}

// Call API helper
async function apiCall(endpoint, method = 'GET', body = null) {
    const headers = { 'Content-Type': 'application/json' };
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`;

    const response = await fetch(`${API_BASE}${endpoint}`, {
        method,
        headers,
        body: body ? JSON.stringify(body) : null
    });

    if (response.status === 401) {
        logout();
        throw new Error('Session expired');
    }

    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'API Error');
    }

    return response.json();
}

async function handleLogin(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button');
    const originalText = btn.innerText;
    btn.innerText = 'Logging in...';
    btn.disabled = true;

    try {
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const data = await apiCall('/api/v1/auth/login', 'POST', { email, password });

        saveSession(data.access_token);
        await showDashboard();
    } catch (err) {
        alert(err.message);
    } finally {
        btn.innerText = originalText;
        btn.disabled = false;
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button');
    btn.innerText = 'Creating Account...';
    btn.disabled = true;

    try {
        const email = document.getElementById('reg-email').value;
        const password = document.getElementById('reg-password').value;
        const data = await apiCall('/api/v1/auth/register', 'POST', { email, password });

        saveSession(data.access_token);
        await showDashboard();
    } catch (err) {
        alert(err.message);
    } finally {
        btn.innerText = 'Create Account';
        btn.disabled = false;
    }
}

async function handleAnalysis(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button');
    btn.innerHTML = '<div class="spinner"></div> Analyzing...';
    btn.disabled = true;
    elements.resultBox.classList.add('hidden');

    try {
        const sender = document.getElementById('sender').value;
        const message = document.getElementById('message').value;
        const result = await apiCall('/api/v1/analyze', 'POST', { sender, message });

        displayResult(result);
        await loadStats();
        updateChart(result.risk_score); // Add data point to chart
    } catch (err) {
        alert(err.message);
    } finally {
        btn.innerHTML = 'Analyze Message';
        btn.disabled = false;
    }
}

function displayResult(result) {
    elements.resultBox.classList.remove('hidden');
    elements.resultBox.className = `result-box ${result.decision}`;

    // Update content
    document.getElementById('res-decision').innerText = result.decision;
    document.getElementById('res-score').innerText = `${result.risk_score}/100`;
    document.getElementById('risk-fill').style.width = `${result.risk_score}%`;
    document.getElementById('risk-fill').style.backgroundColor =
        result.risk_score > 70 ? '#ef4444' : (result.risk_score > 40 ? '#f59e0b' : '#10b981');

    // Tactics
    const tacticsContainer = document.getElementById('res-tactics');
    tacticsContainer.innerHTML = '';
    const tactics = result.analysis?.detected_tactics || [];

    if (tactics.length === 0) {
        tacticsContainer.innerHTML = '<span class="tag">No suspicious tactics detected</span>';
    } else {
        tactics.forEach(t => {
            const tag = document.createElement('span');
            tag.className = 'tag';
            tag.innerText = t;
            tacticsContainer.appendChild(tag);
        });
    }

    // Typing effect for explanation
    const expContainer = document.getElementById('res-explanation');
    expContainer.innerText = '';
    const text = result.analysis?.llm_analysis?.explanation || result.analysis?.explanation || "Based on our AI analysis, this message appears to be safe.";
    typeText(expContainer, text);
}

function typeText(element, text, index = 0) {
    if (index < text.length) {
        element.innerHTML += text.charAt(index);
        // Random typing speed for realism
        setTimeout(() => typeText(element, text, index + 1), 10 + Math.random() * 20);
    }
}

function saveSession(token) {
    authToken = token;
    const payload = JSON.parse(atob(token.split('.')[1]));
    userId = payload.sub;
    localStorage.setItem('scamshield_token', token);
    localStorage.setItem('scamshield_user_id', userId);
}

function logout() {
    authToken = null;
    userId = null;
    localStorage.clear();
    location.reload();
}

async function loadStats() {
    try {
        const stats = await apiCall('/api/v1/stats');
        animateValue(elements.stats.blocked, parseInt(elements.stats.blocked.innerText), stats.total_blocked, 1000);
        elements.stats.today.innerText = stats.blocked_today;
        elements.stats.score.innerText = `${Math.round(stats.protection_score)}%`;
    } catch (e) {
        console.error(e);
    }
}

function animateValue(obj, start, end, duration) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        obj.innerHTML = Math.floor(progress * (end - start) + start);
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

// Chart.js implementation
function initChart() {
    const ctx = document.getElementById('activity-chart');
    if (!ctx) return;

    // Check if Chart.js is loaded
    if (typeof Chart === 'undefined') {
        console.warn('Chart.js not loaded. Falling back.');
        ctx.parentElement.innerHTML = '<div style="text-align:center; padding: 2rem; color: rgba(255,255,255,0.5)">Chart unavailable (Network error)</div>';
        return;
    }

    // Dummy initial data for visual appeal
    const initialData = [12, 19, 3, 5, 2, 3, 10, 15, 20, 25];

    try {
        statsChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10'],
                datasets: [{
                    label: 'Threat Intensity',
                    data: initialData,
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.2)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: { display: false },
                    y: { display: false, min: 0, max: 100 }
                },
                animation: {
                    y: { duration: 2000, easing: 'easeOutQuart' }
                }
            }
        });
    } catch (e) {
        console.error('Chart init failed:', e);
    }
}

function updateChart(newScore) {
    if (!statsChart) return;
    statsChart.data.datasets[0].data.shift(); // Remove oldest
    statsChart.data.datasets[0].data.push(newScore); // Add newest
    statsChart.update();
}

// WebSocket
function connectWebSocket() {
    if (!userId) return;
    websocket = new WebSocket(`${WS_BASE}/ws/${userId}`);

    websocket.onopen = () => {
        const status = document.getElementById('connection-status');
        if (status) status.className = 'status-badge connected';
    };

    websocket.onmessage = (event) => {
        if (event.data === 'pong') return;
        try {
            const alert = JSON.parse(event.data);
            addAlert(alert);
            new Notification("Scam Alert!", { body: `Blocked message from ${alert.sender}` });
            updateChart(alert.risk_score);
        } catch (e) { }
    };

    websocket.onclose = () => {
        const status = document.getElementById('connection-status');
        if (status) status.className = 'status-badge disconnected';
        setTimeout(connectWebSocket, 5000);
    };
}

function addAlert(alert) {
    const div = document.createElement('div');
    div.className = `alert-item ${alert.risk_score > 70 ? 'block' : 'warn'}`;
    div.innerHTML = `
        <div class="alert-icon">${alert.risk_score > 70 ? '[!]' : '[i]'}</div>
        <div class="alert-info">
            <h4>${alert.sender}</h4>
            <div class="alert-meta">Risk: ${alert.risk_score}% • ${new Date().toLocaleTimeString()}</div>
        </div>
    `;
    const emptyMsg = document.getElementById('empty-alerts');
    if (emptyMsg) emptyMsg.remove();
    elements.alertsContainer.prepend(div);
    div.animate([
        { transform: 'translateX(-20px)', opacity: 0 },
        { transform: 'translateX(0)', opacity: 1 }
    ], { duration: 400, easing: 'ease-out' });
}

// Init notification permission
if ("Notification" in window) Notification.requestPermission();

// Start
init();
