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

    // Tab Navigation
    const tabBtns = document.querySelectorAll('.nav-btn');
    const tabContents = document.querySelectorAll('.view-section');

    let selectedTeam1 = null;
    let selectedTeam2 = null;

    // --- Initialization ---
    if (typeof teamData !== 'undefined' && teamData.length > 0) {
        populateAllSelectors();
        initTabs();
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
                const response = await fetch('/api/simulate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ team1: t1, team2: t2 })
                });

                if (!response.ok) {
                    throw new Error("Simulation failed. Check backend console.");
                }

                const data = await response.json();

                // Render Results (Modified for Combined Output)
                simResults.innerHTML = `
                    <div class="result-card">
                        <div class="result-images-container" style="display: flex; gap: 20px; justify-content: center; flex-wrap: wrap;">
                            <div class="img-wrapper">
                                <h4>Win Probability</h4>
                                ${data.prob_image_url ? `<img src="${data.prob_image_url}" alt="Probability" class="result-img">` : ''}
                            </div>
                            <div class="img-wrapper">
                                <h4>Predicted Score</h4>
                                ${data.score_image_url ? `<img src="${data.score_image_url}" alt="Score" class="result-img">` : ''}
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
            });
        });
    }
});
