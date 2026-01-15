document.addEventListener('DOMContentLoaded', () => {
    // --- Globals ---
    // Comparison Tab Elements
    const team1Select = document.getElementById('team1-select');
    const team2Select = document.getElementById('team2-select');
    const statsContainer = document.getElementById('stats-container');
    const team1Display = document.getElementById('team1-display');
    const team2Display = document.getElementById('team2-display');

    // Simulation Tab Elements
    const simTeam1Select = document.getElementById('sim-team1');
    const simTeam2Select = document.getElementById('sim-team2');
    const btnRunSim = document.getElementById('btn-run-sim');
    const simResults = document.getElementById('sim-results');

    // Player Tab Elements
    const playerSearchInput = document.getElementById('player-search');
    const searchResultsList = document.getElementById('search-results');
    const playerProfile = document.getElementById('player-profile');
    const pName = document.getElementById('p-name');
    const pTeam = document.getElementById('p-team');
    const pMatches = document.getElementById('p-matches');
    const pRating = document.getElementById('p-rating');
    const chartCanvas = document.getElementById('ratingChart');
    let ratingChartInstance = null;

    // Explore Tab Elements
    const exploreTeamSelect = document.getElementById('explore-team-select');
    const playerGrid = document.getElementById('player-grid');
    const playerModal = document.getElementById('player-modal');
    const modalClose = document.querySelector('.modal-close');
    const modalOverlay = document.querySelector('.modal-overlay');
    const radarChartCanvas = document.getElementById('player-radar-chart');
    let radarChartInstance = null;

    // Tab Navigation
    const tabBtns = document.querySelectorAll('.nav-btn');
    const tabContents = document.querySelectorAll('.view-section');

    let selectedTeam1 = null;
    let selectedTeam2 = null;

    // --- Initialization ---
    if (typeof teamData !== 'undefined' && teamData.length > 0) {
        populateAllSelectors();
        initTabs();
        initExploreTab();
    } else {
        console.error("No data found. Ensure data.js is loaded.");
        alert("Data not found. Please run the ingestion script.");
    }

    // --- Functions ---
    function populateAllSelectors() {
        const teamNames = teamData.map(t => t.name).sort();

        // Helper to populate a specific select element
        const fillSelect = (select) => {
            teamNames.forEach(name => {
                select.add(new Option(name, name));
            });
        };

        fillSelect(team1Select);
        fillSelect(team2Select);
        fillSelect(simTeam1Select);
        fillSelect(simTeam2Select);
    }

    function initTabs() {
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const targetId = btn.getAttribute('data-tab');

                // Toggle Buttons
                tabBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                // Toggle Content
                tabContents.forEach(content => {
                    if (content.id === targetId) {
                        content.classList.remove('hidden');
                        content.classList.add('active');
                    } else {
                        content.classList.add('hidden');
                        content.classList.remove('active');
                    }
                });
            });
        });
    }

    // --- Event Listeners (Comparison) ---
    team1Select.addEventListener('change', (e) => {
        selectedTeam1 = teamData.find(t => t.name === e.target.value);
        updateComparisonInterface();
    });

    team2Select.addEventListener('change', (e) => {
        selectedTeam2 = teamData.find(t => t.name === e.target.value);
        updateComparisonInterface();
    });

    // --- Slider Event Listeners ---
    const team1AdjSlider = document.getElementById('team1-adjustment');
    const team2AdjSlider = document.getElementById('team2-adjustment');
    const team1AdjValue = document.getElementById('team1-adj-value');
    const team2AdjValue = document.getElementById('team2-adj-value');

    if (team1AdjSlider && team1AdjValue) {
        team1AdjSlider.addEventListener('input', (e) => {
            const val = e.target.value;
            team1AdjValue.textContent = val > 0 ? `+${val}` : val;
        });
    }

    if (team2AdjSlider && team2AdjValue) {
        team2AdjSlider.addEventListener('input', (e) => {
            const val = e.target.value;
            team2AdjValue.textContent = val > 0 ? `+${val}` : val;
        });
    }

    // --- Event Listeners (Simulation) ---
    if (btnRunSim) {
        btnRunSim.addEventListener('click', async () => {
            const t1 = simTeam1Select.value;
            const t2 = simTeam2Select.value;
            // Combined script doesn't need type

            if (!t1 || !t2) {
                alert("Please select both teams first.");
                return;
            }

            // UI Loading State
            btnRunSim.disabled = true;
            btnRunSim.innerText = "Running Simulation...";
            simResults.innerHTML = '<div class="loading">Running combined analysis (Markov + Simulations)...</div>';
            simResults.classList.remove('hidden');

            try {
                // Get adjustment values
                const team1Adj = parseFloat(team1AdjSlider?.value || 0);
                const team2Adj = parseFloat(team2AdjSlider?.value || 0);

                const response = await fetch('/api/simulate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        team1: t1,
                        team2: t2,
                        team1_adj: team1Adj,
                        team2_adj: team2Adj
                    })
                });

                if (!response.ok) {
                    const errorText = await response.text();
                    try {
                        const errData = JSON.parse(errorText);
                        throw new Error(errData.error || "Simulation failed. Check backend console.");
                    } catch (e) {
                        // If JSON parse fails, it's likely an HTML error page (500/502/504)
                        throw new Error(`Server Error (${response.status}): ${errorText.substring(0, 100)}...`);
                    }
                }

                const data = await response.json();

                // Render Results (Modified for Combined Output)
                simResults.innerHTML = `
                    <div class="result-card">
                        <div class="result-images-container" style="display: flex; gap: 20px; justify-content: center; flex-wrap: wrap;">
                            <div class="img-wrapper">
                                <h4>${t1}</h4>
                                ${data.team1_logo_url ? `<img src="${data.team1_logo_url}" alt="${t1} Logo" class="result-img" style="max-width: 200px; max-height: 200px; object-fit: contain;">` : ''}
                            </div>
                            <div class="img-wrapper">
                                <h4>${t2}</h4>
                                ${data.team2_logo_url ? `<img src="${data.team2_logo_url}" alt="${t2} Logo" class="result-img" style="max-width: 200px; max-height: 200px; object-fit: contain;">` : ''}
                            </div>
                        </div>
                        
                        <div class="result-details">
                            <h3>Combined Analysis</h3>
                            <div class="prob-grid">
                                <div class="prob-item">
                                    <span class="label">${t1} Win</span>
                                    <span class="value win">${data.win_prob}%</span>
                                </div>
                                <div class="prob-item">
                                    <span class="label">Draw</span>
                                    <span class="value draw">${data.draw_prob}%</span>
                                </div>
                                <div class="prob-item">
                                    <span class="label">${t2} Win</span>
                                    <span class="value lose">${data.lose_prob}%</span>
                                </div>
                            </div>
                            <div class="predicted-score">
                                Headline Score: <span class="score-val">${data.predicted_score}</span>
                                <div style="font-size: 0.8em; margin-top: 5px; color: #aaa;">
                                    Expected: ${data.exp_home_goals} - ${data.exp_away_goals}
                                </div>
                            </div>
                        </div>
                    </div>
                `;

            } catch (error) {
                console.error(error);
                simResults.innerHTML = `<div class="error">Error: ${error.message}. Is server.py running?</div>`;
            } finally {
                btnRunSim.disabled = false;
                btnRunSim.innerText = "Run Simulation";
            }
        });
    }

    // --- Event Listeners (Player Stats) ---
    if (playerSearchInput) {
        playerSearchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            searchResultsList.innerHTML = '';

            if (query.length < 2) {
                searchResultsList.classList.add('hidden');
                return;
            }

            if (typeof playerData === 'undefined') {
                console.error("playerData not found");
                return;
            }

            const matches = playerData.filter(p => p.name.toLowerCase().includes(query)).slice(0, 10);

            if (matches.length > 0) {
                searchResultsList.classList.remove('hidden');
                matches.forEach(player => {
                    const li = document.createElement('li');
                    li.innerHTML = `<strong>${player.name}</strong> <span style="font-size:0.8em; color:#ccc">(${player.team})</span>`;
                    li.addEventListener('click', () => {
                        selectPlayer(player);
                        searchResultsList.classList.add('hidden');
                        playerSearchInput.value = player.name;
                    });
                    searchResultsList.appendChild(li);
                });
            } else {
                searchResultsList.classList.add('hidden');
            }
        });
    }

    function selectPlayer(player) {
        playerProfile.classList.remove('hidden');
        pName.innerText = player.name;
        pTeam.innerText = player.team;
        pMatches.innerText = player.games;
        pRating.innerText = player.avg_rating;

        // Render Chart
        renderChart(player.ratings);
    }

    function renderChart(ratings) {
        if (ratingChartInstance) {
            ratingChartInstance.destroy();
        }

        // Generate Labels (Opponent Names if available, else Match X)
        // Check if ratings contains objects or numbers (backward compatibility)
        const isObject = ratings.length > 0 && typeof ratings[0] === 'object';

        const labels = isObject
            ? ratings.map(r => `vs ${r.opponent}`)
            : ratings.map((_, i) => `Match ${i + 1}`);

        const dataPoints = isObject
            ? ratings.map(r => r.rating)
            : ratings;

        ratingChartInstance = new Chart(chartCanvas, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Player Rating',
                    data: dataPoints,
                    borderColor: '#4facfe',
                    backgroundColor: 'rgba(79, 172, 254, 0.2)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: '#fff',
                    pointBorderColor: '#00f2fe'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: false,
                        suggestedMin: 5,
                        suggestedMax: 10,
                        grid: { color: 'rgba(255,255,255,0.1)' },
                        ticks: { color: '#ccc' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#ccc', maxRotation: 45, minRotation: 45 }
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return `Rating: ${context.parsed.y}`;
                            }
                        }
                    }
                }
            }
        });
    }

    // --- Render Logic ---
    function updateComparisonInterface() {
        // Update Headers
        if (selectedTeam1) {
            team1Display.innerHTML = `<h2>${selectedTeam1.name}</h2>`;
        }
        if (selectedTeam2) {
            team2Display.innerHTML = `<h2>${selectedTeam2.name}</h2>`;
        }

        // Render Stats if both selected
        if (selectedTeam1 && selectedTeam2) {
            renderComparison(selectedTeam1, selectedTeam2, statsContainer);
            statsContainer.classList.remove('hidden');
        } else {
            statsContainer.classList.add('hidden');
        }
    }

    function renderComparison(t1, t2, container) {
        container.innerHTML = ''; // Clear previous

        const metrics = [
            { key: 'win_rate', label: 'Win Rate', format: '%' },
            { key: 'avg_goals_scored', label: 'Goals Scored (Avg)', format: '' },
            { key: 'avg_goals_conceded', label: 'Goals Conceded (Avg)', format: '' },
            { key: 'avg_shots', label: 'Shots per Match', format: '' },
            { key: 'avg_possession', label: 'Possession', format: '%' },
            { key: 'avg_corners', label: 'Corners (Avg)', format: '' }
        ];

        metrics.forEach((metric, index) => {
            const val1 = t1.stats[metric.key];
            const val2 = t2.stats[metric.key];

            // Normalize
            const max = Math.max(val1, val2) || 1;

            const row = document.createElement('div');
            row.className = 'stat-row';
            row.style.animationDelay = `${index * 0.1}s`;

            // Display formatting
            let disp1, disp2;
            if (metric.label.includes('Possession') || metric.label.includes('Win Rate')) {
                disp1 = Math.round(val1 * 100) + '%';
                disp2 = Math.round(val2 * 100) + '%';
            } else {
                disp1 = val1.toFixed(2);
                disp2 = val2.toFixed(2);
            }

            row.innerHTML = `
                <div class="stat-label">${metric.label}</div>
                <div class="bar-container">
                    <div class="stat-value left">${disp1}</div>
                    <div class="bar-wrapper">
                        <div class="bar-fill left" style="width: 0%"></div>
                    </div>
                    <div class="bar-wrapper">
                        <div class="bar-fill right" style="width: 0%"></div>
                    </div>
                    <div class="stat-value right">${disp2}</div>
                </div>
            `;

            container.appendChild(row);

            // Animate bar widths
            requestAnimationFrame(() => {
                const fillLeft = row.querySelector('.bar-fill.left');
                const fillRight = row.querySelector('.bar-fill.right');

                const ratio1 = val1 / max * 100;
                const ratio2 = val2 / max * 100;

                fillLeft.style.width = `${ratio1}%`;
                fillRight.style.width = `${ratio2}%`;
            })
        });
    }

    // --- Explore Tab Functions ---
    function initExploreTab() {
        // Check if playersData is available
        if (typeof playersData === 'undefined') {
            console.error('playersData not found. Make sure players_data.js is loaded.');
            return;
        }

        // Populate team selector
        if (exploreTeamSelect && teamNames) {
            teamNames.forEach(team => {
                exploreTeamSelect.add(new Option(team, team));
            });
        }

        // Team selection handler
        if (exploreTeamSelect) {
            exploreTeamSelect.addEventListener('change', (e) => {
                const selectedTeam = e.target.value;
                if (selectedTeam && playersData[selectedTeam]) {
                    renderPlayerGrid(playersData[selectedTeam]);
                }
            });
        }

        // Modal close handlers
        if (modalClose) {
            modalClose.addEventListener('click', closePlayerModal);
        }
        if (modalOverlay) {
            modalOverlay.addEventListener('click', closePlayerModal);
        }

        // ESC key to close modal
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && playerModal && !playerModal.classList.contains('hidden')) {
                closePlayerModal();
            }
        });
    }

    function renderPlayerGrid(players) {
        if (!playerGrid) return;

        playerGrid.innerHTML = '';
        playerGrid.classList.remove('hidden');

        players.forEach(player => {
            const card = document.createElement('div');
            card.className = 'player-card-explore';
            card.innerHTML = `
                <div class="player-card-name">${player.name}</div>
                <div class="player-card-overall">${player.overall}</div>
                <div class="player-card-stats">
                    <div class="player-card-stat">
                        <span>PAC</span>
                        <span>${player.pace}</span>
                    </div>
                    <div class="player-card-stat">
                        <span>SHO</span>
                        <span>${player.shooting}</span>
                    </div>
                    <div class="player-card-stat">
                        <span>PAS</span>
                        <span>${player.passing}</span>
                    </div>
                    <div class="player-card-stat">
                        <span>DRI</span>
                        <span>${player.dribbling}</span>
                    </div>
                    <div class="player-card-stat">
                        <span>DEF</span>
                        <span>${player.defending}</span>
                    </div>
                    <div class="player-card-stat">
                        <span>PHY</span>
                        <span>${player.physical}</span>
                    </div>
                </div>
            `;

            card.addEventListener('click', () => showPlayerModal(player));
            playerGrid.appendChild(card);
        });
    }

    function showPlayerModal(player) {
        if (!playerModal) return;

        // Populate basic info
        document.getElementById('modal-player-name').textContent = player.name;
        document.getElementById('modal-player-team').textContent = player.team;
        document.getElementById('modal-player-nationality').textContent = player.nationality;
        document.getElementById('modal-player-age').textContent = `${player.age} years`;
        document.getElementById('modal-player-overall').textContent = player.overall;

        // Populate main attributes with animated bars
        const mainAttrs = [
            { key: 'pace', label: 'Pace' },
            { key: 'shooting', label: 'Shooting' },
            { key: 'passing', label: 'Passing' },
            { key: 'dribbling', label: 'Dribbling' },
            { key: 'defending', label: 'Defending' },
            { key: 'physical', label: 'Physical' }
        ];

        mainAttrs.forEach(attr => {
            const value = player[attr.key];
            const valueEl = document.getElementById(`modal-${attr.key}`);
            const barEl = document.getElementById(`modal-${attr.key}-bar`);

            if (valueEl) valueEl.textContent = value;
            if (barEl) {
                // Reset then animate
                barEl.style.width = '0%';
                setTimeout(() => {
                    barEl.style.width = `${value}%`;
                }, 50);
            }
        });

        // Populate detailed stats
        document.getElementById('modal-height').textContent = player.height;
        document.getElementById('modal-foot').textContent = player.foot;
        document.getElementById('modal-body-type').textContent = player.bodyType;
        document.getElementById('modal-rarity').textContent = player.rarity;
        document.getElementById('modal-skills').textContent = `${player.skills}★`;
        document.getElementById('modal-weak-foot').textContent = `${player.weakFoot}★`;

        // Render radar chart
        renderRadarChart(player);

        // Show modal
        playerModal.classList.remove('hidden');
        document.body.style.overflow = 'hidden'; // Prevent background scroll
    }

    function closePlayerModal() {
        if (playerModal) {
            playerModal.classList.add('hidden');
            document.body.style.overflow = ''; // Restore scroll
        }
    }

    function renderRadarChart(player) {
        if (!radarChartCanvas) return;

        // Destroy existing chart
        if (radarChartInstance) {
            radarChartInstance.destroy();
        }

        const ctx = radarChartCanvas.getContext('2d');

        radarChartInstance = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: ['Pace', 'Shooting', 'Passing', 'Dribbling', 'Defending', 'Physical'],
                datasets: [{
                    label: player.name,
                    data: [
                        player.pace,
                        player.shooting,
                        player.passing,
                        player.dribbling,
                        player.defending,
                        player.physical
                    ],
                    backgroundColor: 'rgba(59, 130, 246, 0.2)',
                    borderColor: '#3b82f6',
                    borderWidth: 2,
                    pointBackgroundColor: '#3b82f6',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: '#3b82f6'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100,
                        min: 0,
                        ticks: {
                            stepSize: 20,
                            color: '#94a3b8',
                            backdropColor: 'transparent'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        pointLabels: {
                            color: '#f8fafc',
                            font: {
                                size: 12,
                                weight: '600'
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return `${context.label}: ${context.parsed.r}`;
                            }
                        }
                    }
                }
            }
        });
    }
});
