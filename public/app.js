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

    // --- Initialization moved to after declarations ---

    // --- Localization ---
    const translations = {
        en: {
            subtitle: "Next-Gen Football Analytics & Simulation",
            nav_analysis: "Analysis",
            nav_simulation: "Simulation",
            nav_recent_games: "Recent Games",
            nav_scout: "Scout",
            nav_explore: "Explore",
            analysis_title: "Pre-Match Analysis",
            analysis_desc: "Compare team statistics head-to-head before the whistle blows.",
            label_home_team: "Home Team",
            label_away_team: "Away Team",
            select_placeholder: "Select Team",
            h2h_title: "Head-to-Head Record",
            goals_trend_title: "Goal Scoring Trend (Last 15 Matches)",
            radar_title: "Team Comparison Radar",
            recent_form_title: "Recent Form (Last 10 Matches)",
            recent_matches_title: "Recent Matches",
            rankings_title: "Metric Rankings",
            sim_title: "AI Match Engine",
            sim_desc: "Run 1000+ Monte Carlo simulations to predict the outcome.",
            match_setup: "Match Setup",
            select_short: "Select...",
            home_adj: "Home Team Adjustment",
            away_adj: "Away Team Adjustment",
            btn_run_sim: "Run Prediction",
            loader_title: "Analyzing Match...",
            loader_subtitle: "Running 10,000 simulations with AI predictions",
            scout_title: "Player Scout",
            scout_desc: "Deep dive into individual player ratings and performance history.",
            search_placeholder: "Search for a player (e.g. Icardi)...",
            matches: "Matches",
            avg_rating: "Avg Rating",
            explore_title: "Player Explorer",
            explore_desc: "Browse Turkish Super League players by team and view detailed statistics.",
            label_select_team: "Select Team",
            choose_team_placeholder: "Choose a team...",
            main_attributes: "Main Attributes",
            attr_pace: "Pace",
            attr_shooting: "Shooting",
            attr_passing: "Passing",
            attr_dribbling: "Dribbling",
            attr_defending: "Defending",
            attr_physical: "Physical",
            physical_info: "Physical Info",
            height: "Height",
            foot: "Foot",
            body_type: "Body Type",
            card_info: "Card Info",
            rarity: "Rarity",
            skills: "Skills",
            weak_foot: "Weak Foot",
            radar_title: "Performance Radar",
            recent_games_title: "Weekly Predictions",
            recent_games_desc: "AI-powered predictions for upcoming Turkish Super League matches.",
            round_label: "Round",
            loading_matches: "Loading matches...",
            confidence_high: "High Confidence",
            confidence_medium: "Medium Confidence",
            confidence_low: "Low Confidence"
        },
        tr: {
            subtitle: "Yeni Nesil Futbol Analizi ve Simülasyonu",
            nav_analysis: "Analiz",
            nav_simulation: "Simülasyon",
            nav_recent_games: "Son Maçlar",
            nav_scout: "Gözlemci",
            nav_explore: "Keşfet",
            analysis_title: "Maç Öncesi Analiz",
            analysis_desc: "Takım istatistiklerini maçtan önce karşılaştırın.",
            label_home_team: "Ev Sahibi",
            label_away_team: "Deplasman",
            select_placeholder: "Takım Seçin",
            h2h_title: "Aradaki Maçlar",
            goals_trend_title: "Gol Trendi (Son 15 Maç)",
            radar_title: "Takım Karşılaştırma Radarı",
            recent_form_title: "Son Form (Son 10 Maç)",
            recent_matches_title: "Son Maçlar",
            rankings_title: "Sıralamalar",
            sim_title: "Yapay Zeka Maç Motoru",
            sim_desc: "Maç sonucunu tahmin etmek için 1000+ Monte Carlo simülasyonu çalıştırın.",
            match_setup: "Maç Kurulumu",
            select_short: "Seç...",
            home_adj: "Ev Sahibi Ayarı",
            away_adj: "Deplasman Ayarı",
            btn_run_sim: "Tahmin Yürüt",
            loader_title: "Maç Analiz Ediliyor...",
            loader_subtitle: "10.000 simülasyon yapay zeka tahminleri ile çalışıyor",
            scout_title: "Oyuncu Gözlemcisi",
            scout_desc: "Oyuncu reytinglerine ve performans geçmişine derinlemesine bakın.",
            search_placeholder: "Oyuncu ara (örn. Icardi)...",
            matches: "Maçlar",
            avg_rating: "Ort. Reyting",
            explore_title: "Oyuncu Keşfi",
            explore_desc: "Süper Lig oyuncularını takıma göre inceleyin.",
            label_select_team: "Takım Seç",
            choose_team_placeholder: "Bir takım seçin...",
            main_attributes: "Ana Özellikler",
            attr_pace: "Hız",
            attr_shooting: "Şut",
            attr_passing: "Pas",
            attr_dribbling: "Top Sürme",
            attr_defending: "Defans",
            attr_physical: "Fizik",
            physical_info: "Fiziksel Bilgi",
            height: "Boy",
            foot: "Ayak",
            body_type: "Vücut Tipi",
            card_info: "Kart Bilgisi",
            rarity: "Nadirlik",
            skills: "Yetenek",
            weak_foot: "Zayıf Ayak",
            radar_title: "Performans Radarı",
            recent_games_title: "Haftalık Tahminler",
            recent_games_desc: "Süper Lig maçları için yapay zeka destekli tahminler.",
            round_label: "Hafta",
            loading_matches: "Maçlar yükleniyor...",
            confidence_high: "Yüksek Güven",
            confidence_medium: "Orta Güven",
            confidence_low: "Düşük Güven"
        }
    };

    let currentLang = localStorage.getItem('goloncesi_lang') || 'tr';

    function initLanguage() {
        const langBtn = document.getElementById('lang-btn');
        const langMenu = document.querySelector('.lang-menu');
        const langOptions = document.querySelectorAll('.lang-option');

        // Initial update
        updateLanguage(currentLang);

        // Toggle menu on button click
        if (langBtn && langMenu) {
            langBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                langMenu.classList.toggle('show');
            });

            // Close menu when clicking outside
            document.addEventListener('click', (e) => {
                if (!langBtn.contains(e.target) && !langMenu.contains(e.target)) {
                    langMenu.classList.remove('show');
                }
            });
        }

        // Handle language option clicks
        langOptions.forEach(opt => {
            opt.addEventListener('click', () => {
                const lang = opt.getAttribute('data-lang');
                updateLanguage(lang);
                // Close menu after selection
                if (langMenu) {
                    langMenu.classList.remove('show');
                }
            });
        });
    }

    function updateLanguage(lang) {
        currentLang = lang;
        localStorage.setItem('goloncesi_lang', lang);

        // Update Text Content
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            if (translations[lang][key]) {
                el.textContent = translations[lang][key];
            }
        });

        // Update Placeholders
        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            if (translations[lang][key]) {
                el.placeholder = translations[lang][key];
            }
        });

        // Update Dropdown UI
        const flag = lang === 'en' ? '🇬🇧' : '🇹🇷';
        const code = lang === 'en' ? 'EN' : 'TR';
        const langBtn = document.getElementById('lang-btn');
        if (langBtn) {
            langBtn.innerHTML = `<span class="flag-icon">${flag}</span> <span class="lang-code">${code}</span>`;
        }

        // Update Menu Active State
        document.querySelectorAll('.lang-option').forEach(opt => {
            opt.classList.toggle('active', opt.getAttribute('data-lang') === lang);
        });
    }

    // --- Initialization ---
    if (typeof teamData !== 'undefined' && teamData.length > 0) {
        populateAllSelectors();
        initTabs();
        initExploreTab();
        initLanguage();
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

    // --- Pitch Visualization (Formation) ---
    async function updatePitchVisualization() {
        const t1 = simTeam1Select?.value;
        const t2 = simTeam2Select?.value;

        if (!t1 || !t2) {
            // Hide pitch if one or both teams not selected
            if (typeof hidePitchView === 'function') {
                hidePitchView();
            }
            return;
        }

        try {
            // Fetch lineup data for both teams
            const team1Data = await getTeamLatestLineup(t1);
            const team2Data = await getTeamLatestLineup(t2);

            // Render pitch
            if (typeof renderPitchView === 'function') {
                renderPitchView(team1Data, team2Data);
            }
        } catch (error) {
            console.error('Error updating pitch visualization:', error);
        }
    }

    // Add change listeners to sim team selects
    if (simTeam1Select) {
        simTeam1Select.addEventListener('change', updatePitchVisualization);
    }
    if (simTeam2Select) {
        simTeam2Select.addEventListener('change', updatePitchVisualization);
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
            simResults.classList.add('hidden');

            // Show loader with animation
            const loader = document.getElementById('sim-loader');
            const progressFill = document.querySelector('.progress-fill');
            const progressGlow = document.querySelector('.progress-glow');
            const progressPct = document.querySelector('.progress-percentage');
            const progressStatus = document.querySelector('.progress-status');

            loader.classList.remove('hidden');

            // Define progress stages with milestones and status messages
            const stages = [
                { target: 37, message: 'Loading team data...', speed: 150 },
                { target: 68, message: 'Running Markov chain analysis...', speed: 200 },
                { target: 82, message: 'Simulating match outcomes...', speed: 250 },
                { target: 94, message: 'Generating predictions...', speed: 300 }
            ];

            let progress = 0;
            let currentStage = 0;

            const progressInterval = setInterval(() => {
                if (currentStage >= stages.length) {
                    clearInterval(progressInterval);
                    return;
                }

                const stage = stages[currentStage];
                const increment = (stage.target - progress) / 20; // Gradual approach to target

                progress += Math.max(0.5, increment);

                if (progress >= stage.target) {
                    progress = stage.target;
                    currentStage++;
                    if (currentStage < stages.length) {
                        progressStatus.textContent = stages[currentStage].message;
                    }
                }

                progressFill.style.width = `${progress}%`;
                progressGlow.style.width = `${progress}%`;
                progressPct.textContent = `${Math.round(progress)}%`;
            }, stages[currentStage]?.speed || 150);

            // Set initial status
            progressStatus.textContent = stages[0].message;

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

                // Build Top 5 Scores HTML
                let top5Html = '';
                if (data.top5_scores && data.top5_scores.length > 0) {
                    top5Html = data.top5_scores.map(s => `
                        <div class="scoreline-row">
                            <span class="scoreline-label">${s.score}</span>
                            <div class="scoreline-bar-wrapper">
                                <div class="scoreline-bar" style="width: ${s.percentage}%">
                                    <span class="scoreline-pct">${s.percentage}%</span>
                                </div>
                            </div>
                        </div>
                    `).join('');
                }

                // Build Form Indicators HTML
                let formHtml = '';
                let stateProfilesHtml = '';
                if (data.markov_form) {
                    const m1 = data.markov_form.team1;
                    const m2 = data.markov_form.team2;
                    const getFormClass = (label) => {
                        if (label.includes('Hot')) return 'hot';
                        if (label.includes('Cold')) return 'cold';
                        return 'neutral';
                    };

                    // Build state profiles for each team
                    const buildStateProfiles = (team) => {
                        if (!team.state_profiles || team.state_profiles.length === 0) return '';
                        return team.state_profiles.map(state => `
                            <div class="state-profile-card">
                                <div class="state-header">
                                    <span class="state-label">${state.label}</span>
                                    <span class="state-matches">${state.count} matches</span>
                                </div>
                                <div class="state-probs">
                                    <div class="state-prob win">
                                        <span class="prob-bar" style="width: ${state.win_prob}%"></span>
                                        <span class="prob-text">W ${state.win_prob}%</span>
                                    </div>
                                    <div class="state-prob draw">
                                        <span class="prob-bar" style="width: ${state.draw_prob}%"></span>
                                        <span class="prob-text">D ${state.draw_prob}%</span>
                                    </div>
                                    <div class="state-prob loss">
                                        <span class="prob-bar" style="width: ${state.loss_prob}%"></span>
                                        <span class="prob-text">L ${state.loss_prob}%</span>
                                    </div>
                                </div>
                            </div>
                        `).join('');
                    };

                    formHtml = `
                        <div class="form-team">
                            <div class="form-team-name">${m1.name}</div>
                            <div class="form-badge ${getFormClass(m1.form_label)}">${m1.form_label}</div>
                            <div class="form-probs">
                                <div class="form-prob-item">
                                    <span class="prob-label">Win</span>
                                    <span class="prob-value">${m1.next_win_prob}%</span>
                                </div>
                                <div class="form-prob-item">
                                    <span class="prob-label">Draw</span>
                                    <span class="prob-value">${m1.next_draw_prob}%</span>
                                </div>
                                <div class="form-prob-item">
                                    <span class="prob-label">Loss</span>
                                    <span class="prob-value">${m1.next_loss_prob}%</span>
                                </div>
                            </div>
                            <div class="form-meta">
                                <span>${m1.matches_analyzed} matches • ${m1.hidden_states} states</span>
                            </div>
                        </div>
                        <div class="form-team">
                            <div class="form-team-name">${m2.name}</div>
                            <div class="form-badge ${getFormClass(m2.form_label)}">${m2.form_label}</div>
                            <div class="form-probs">
                                <div class="form-prob-item">
                                    <span class="prob-label">Win</span>
                                    <span class="prob-value">${m2.next_win_prob}%</span>
                                </div>
                                <div class="form-prob-item">
                                    <span class="prob-label">Draw</span>
                                    <span class="prob-value">${m2.next_draw_prob}%</span>
                                </div>
                                <div class="form-prob-item">
                                    <span class="prob-label">Loss</span>
                                    <span class="prob-value">${m2.next_loss_prob}%</span>
                                </div>
                            </div>
                            <div class="form-meta">
                                <span>${m2.matches_analyzed} matches • ${m2.hidden_states} states</span>
                            </div>
                        </div>
                    `;

                    // Build detailed state profiles section
                    stateProfilesHtml = `
                        <div class="state-profiles-grid">
                            <div class="team-states">
                                <h5>${m1.name} Form States</h5>
                                <div class="states-list">
                                    ${buildStateProfiles(m1)}
                                </div>
                            </div>
                            <div class="team-states">
                                <h5>${m2.name} Form States</h5>
                                <div class="states-list">
                                    ${buildStateProfiles(m2)}
                                </div>
                            </div>
                        </div>
                    `;
                }

                // Build Ratings Comparison HTML
                let ratingsHtml = '';
                if (data.avg_ratings) {
                    const maxRating = 10;
                    const r1 = data.avg_ratings.team1;
                    const r2 = data.avg_ratings.team2;
                    ratingsHtml = `
                        <div class="rating-row">
                            <span class="rating-team-name">${t1}</span>
                            <div class="rating-bar-wrapper">
                                <div class="rating-bar team1" style="width: ${(r1 / maxRating) * 100}%"></div>
                            </div>
                            <span class="rating-value team1">${r1}</span>
                        </div>
                        <div class="rating-row">
                            <span class="rating-team-name">${t2}</span>
                            <div class="rating-bar-wrapper">
                                <div class="rating-bar team2" style="width: ${(r2 / maxRating) * 100}%"></div>
                            </div>
                            <span class="rating-value team2">${r2}</span>
                        </div>
                    `;
                }

                // Render Results with Enhanced Insights
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
                            <h3>Match Prediction</h3>
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
                                Predicted Score: <span class="score-val">${data.predicted_score}</span>
                                <div style="font-size: 0.8em; margin-top: 5px; color: #aaa;">
                                    Expected Goals: ${data.exp_home_goals} - ${data.exp_away_goals}
                                </div>
                            </div>
                        </div>

                        <!-- Enhanced Insights Section -->
                        <div class="insights-container">
                            ${top5Html ? `
                            <div class="insights-panel">
                                <h4><span class="icon">📊</span> Most Likely Scorelines</h4>
                                <div class="score-probabilities">
                                    ${top5Html}
                                </div>
                            </div>
                            ` : ''}

                            ${formHtml ? `
                            <div class="insights-panel">
                                <h4><span class="icon">🔥</span> Current Form (Markov Analysis)</h4>
                                <div class="form-indicators">
                                    ${formHtml}
                                </div>
                            </div>
                            ` : ''}

                            ${stateProfilesHtml ? `
                            <div class="insights-panel">
                                <h4><span class="icon">🧠</span> HMM State Breakdown</h4>
                                <p class="panel-subtitle">Historical form states detected by the Hidden Markov Model</p>
                                ${stateProfilesHtml}
                            </div>
                            ` : ''}

                            ${ratingsHtml ? `
                            <div class="insights-panel">
                                <h4><span class="icon">⭐</span> Average Player Ratings</h4>
                                <div class="ratings-comparison">
                                    ${ratingsHtml}
                                </div>
                            </div>
                            ` : ''}

                            <div class="sim-meta">
                                <div class="sim-meta-item">
                                    <span class="meta-label">Simulations</span>
                                    <span class="meta-value">${data.simulated_matches?.toLocaleString() || '450+'}</span>
                                </div>
                                ${data.adjustments ? `
                                <div class="sim-meta-item">
                                    <span class="meta-label">${t1} Adj.</span>
                                    <span class="meta-value">${data.adjustments.team1 >= 0 ? '+' : ''}${data.adjustments.team1}%</span>
                                </div>
                                <div class="sim-meta-item">
                                    <span class="meta-label">${t2} Adj.</span>
                                    <span class="meta-value">${data.adjustments.team2 >= 0 ? '+' : ''}${data.adjustments.team2}%</span>
                                </div>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                `;

                // Complete the progress animation
                clearInterval(progressInterval);
                progressStatus.textContent = 'Complete!';
                progressFill.style.width = '100%';
                progressGlow.style.width = '100%';
                progressPct.textContent = '100%';

                // Brief delay to show 100%, then hide loader and show results
                setTimeout(() => {
                    loader.classList.add('hidden');
                    simResults.classList.remove('hidden');
                }, 400);

            } catch (error) {
                console.error(error);

                // Complete progress and hide loader on error too
                clearInterval(progressInterval);
                loader.classList.add('hidden');

                simResults.innerHTML = `<div class="error">Error: ${error.message}. Is server.py running?</div>`;
                simResults.classList.remove('hidden');
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
            ? ratings.map(r => r.rating).reverse()
            : ratings.slice().reverse();

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
    // Chart instances for Analysis tab (prefixed with analysis_ to avoid conflicts)
    let analysisGoalsChartInstance = null;
    let analysisRadarChartInstance = null;
    const analysisCharts = document.getElementById('analysis-charts');
    const analysisGoalsCanvas = document.getElementById('goalsChart');
    const analysisRadarCanvas = document.getElementById('radarChart');

    function updateComparisonInterface() {
        // Update Headers
        if (selectedTeam1) {
            team1Display.innerHTML = `
                <img src="/logos/${selectedTeam1.name}.png" alt="${selectedTeam1.name} Logo" class="team-logo" onerror="this.style.display='none'">
                <h2>${selectedTeam1.name}</h2>
            `;
        }
        if (selectedTeam2) {
            team2Display.innerHTML = `
                <img src="/logos/${selectedTeam2.name}.png" alt="${selectedTeam2.name} Logo" class="team-logo" onerror="this.style.display='none'">
                <h2>${selectedTeam2.name}</h2>
            `;
        }

        // Render Stats if both selected
        if (selectedTeam1 && selectedTeam2) {
            renderComparison(selectedTeam1, selectedTeam2, statsContainer);
            statsContainer.classList.remove('hidden');

            // Render enhanced analysis
            if (analysisCharts) {
                analysisCharts.classList.remove('hidden');
                renderGoalsChart(selectedTeam1, selectedTeam2);
                renderTeamRadarChart(selectedTeam1, selectedTeam2);
                renderHeadToHead(selectedTeam1, selectedTeam2);
                renderFormDisplay(selectedTeam1, selectedTeam2);
                renderMatchHistory(selectedTeam1, selectedTeam2);
                renderRankings(selectedTeam1, selectedTeam2);
            }
        } else {
            statsContainer.classList.add('hidden');
            if (analysisCharts) analysisCharts.classList.add('hidden');
        }
    }

    function renderGoalsChart(t1, t2) {
        if (!analysisGoalsCanvas) return;
        if (analysisGoalsChartInstance) analysisGoalsChartInstance.destroy();

        // Data comes in newest-first order. Reverse for time-series charts.
        const h1 = (t1.match_history || []).slice().reverse();
        const h2 = (t2.match_history || []).slice().reverse();
        const len = Math.max(h1.length, h2.length, 1);
        const labels = Array.from({ length: len }, (_, i) => `M${i + 1}`);

        analysisGoalsChartInstance = new Chart(analysisGoalsCanvas, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: `${t1.name} Goals`,
                        data: h1.map(m => m.goals_for),
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: `${t2.name} Goals`,
                        data: h2.map(m => m.goals_for),
                        borderColor: '#f43f5e',
                        backgroundColor: 'rgba(244, 63, 94, 0.1)',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { intersect: false, mode: 'index' },
                scales: {
                    y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#ccc' } },
                    x: { grid: { display: false }, ticks: { color: '#ccc' } }
                },
                plugins: { legend: { labels: { color: '#fff' } } }
            }
        });
    }

    function renderTeamRadarChart(t1, t2) {
        if (!analysisRadarCanvas) return;
        if (analysisRadarChartInstance) analysisRadarChartInstance.destroy();

        // Robust normalize function
        const normalize = (val, max) => {
            if (val === undefined || val === null || isNaN(val)) return 0;
            return Math.min(100, (val / max) * 100);
        };

        // Helper to get stats safely
        const getStats = (team) => team.stats || {};
        const s1 = getStats(t1);
        const s2 = getStats(t2);

        const data1 = [
            normalize(s1.win_rate, 1),
            normalize(s1.avg_goals_scored, 3),
            100 - normalize(s1.avg_goals_conceded, 3),
            normalize(s1.avg_shots, 20),
            normalize(s1.avg_possession, 1),
            normalize(s1.avg_corners, 8)
        ];

        const data2 = [
            normalize(s2.win_rate, 1),
            normalize(s2.avg_goals_scored, 3),
            100 - normalize(s2.avg_goals_conceded, 3),
            normalize(s2.avg_shots, 20),
            normalize(s2.avg_possession, 1),
            normalize(s2.avg_corners, 8)
        ];

        analysisRadarChartInstance = new Chart(analysisRadarCanvas, {
            type: 'radar',
            data: {
                labels: ['Win Rate', 'Goals Scored', 'Goals Conceded', 'Shots', 'Possession', 'Corners'],
                datasets: [
                    {
                        label: t1.name,
                        data: data1,
                        backgroundColor: 'rgba(59, 130, 246, 0.2)',
                        borderColor: '#3b82f6',
                        borderWidth: 2,
                        pointBackgroundColor: '#3b82f6'
                    },
                    {
                        label: t2.name,
                        data: data2,
                        backgroundColor: 'rgba(244, 63, 94, 0.2)',
                        borderColor: '#f43f5e',
                        borderWidth: 2,
                        pointBackgroundColor: '#f43f5e'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100,
                        grid: { color: 'rgba(255,255,255,0.1)' },
                        pointLabels: { color: '#fff', font: { size: 11 } },
                        ticks: { display: false }
                    }
                },
                plugins: { legend: { labels: { color: '#fff' } } }
            }
        });
    }

    function renderHeadToHead(t1, t2) {
        const container = document.getElementById('h2h-content');
        if (!container) return;

        const h2h1 = t1.head_to_head?.[t2.name];
        const h2h2 = t2.head_to_head?.[t1.name];

        if (!h2h1 && !h2h2) {
            container.innerHTML = '<p class="no-data">No head-to-head data available</p>';
            return;
        }

        const record = h2h1 || { wins: 0, draws: 0, losses: 0, goals_for: 0, goals_against: 0 };
        const total = record.wins + record.draws + record.losses;

        container.innerHTML = `
            <div class="h2h-stats">
                <div class="h2h-team">
                    <span class="team-name">${t1.name}</span>
                    <span class="h2h-wins">${record.wins} wins</span>
                </div>
                <div class="h2h-center">
                    <div class="h2h-draws">${record.draws} draws</div>
                    <div class="h2h-matches">${total} matches</div>
                </div>
                <div class="h2h-team">
                    <span class="team-name">${t2.name}</span>
                    <span class="h2h-wins">${record.losses} wins</span>
                </div>
            </div>
            <div class="h2h-goals">
                <span>Goals: ${record.goals_for} - ${record.goals_against}</span>
            </div>
        `;
    }

    function renderFormDisplay(t1, t2) {
        const container = document.getElementById('form-display');
        if (!container) return;

        const buildFormRow = (team) => {
            // Take first 10 (newest) and reverse for past-to-present visual order
            const history = (team.match_history || []).slice(0, 10).reverse();
            const formIcons = history.map(m => {
                if (m.result === 'W') return '<span class="form-icon win">W</span>';
                if (m.result === 'D') return '<span class="form-icon draw">D</span>';
                return '<span class="form-icon loss">L</span>';
            }).join('');
            return `
                <div class="form-row">
                    <span class="form-team-label">${team.name}</span>
                    <div class="form-icons">${formIcons || 'No data'}</div>
                </div>
            `;
        };

        container.innerHTML = buildFormRow(t1) + buildFormRow(t2);
    }

    function renderMatchHistory(t1, t2) {
        const container = document.getElementById('match-history');
        if (!container) return;

        const buildTable = (team) => {
            // First 8 matches are the newest. Keep that order for table.
            const history = (team.match_history || []).slice(0, 8);
            if (history.length === 0) return `<p>${team.name}: No match data</p>`;

            const rows = history.map(m => `
                <tr class="result-${m.result.toLowerCase()}">
                    <td>${m.home_away}</td>
                    <td>${m.opponent}</td>
                    <td>${m.goals_for} - ${m.goals_against}</td>
                    <td>${m.possession}%</td>
                    <td>${m.shots}</td>
                </tr>
            `).join('');

            return `
                <div class="history-table-wrapper">
                    <h5>${team.name}</h5>
                    <table class="history-table">
                        <thead><tr><th>H/A</th><th>Opponent</th><th>Score</th><th>Poss</th><th>Shots</th></tr></thead>
                        <tbody>${rows}</tbody>
                    </table>
                </div>
            `;
        };

        container.innerHTML = `<div class="history-grid">${buildTable(t1)}${buildTable(t2)}</div>`;
    }

    function renderRankings(t1, t2) {
        const container = document.getElementById('rankings-display');
        if (!container) return;

        // Calculate rankings among all teams
        const rankings = {
            'Goals Scored': teamData.sort((a, b) => b.stats.avg_goals_scored - a.stats.avg_goals_scored).map(t => t.name),
            'Goals Conceded': teamData.sort((a, b) => a.stats.avg_goals_conceded - b.stats.avg_goals_conceded).map(t => t.name),
            'Win Rate': teamData.sort((a, b) => b.stats.win_rate - a.stats.win_rate).map(t => t.name),
            'Possession': teamData.sort((a, b) => b.stats.avg_possession - a.stats.avg_possession).map(t => t.name)
        };

        const html = Object.entries(rankings).map(([metric, order]) => {
            const rank1 = order.indexOf(t1.name) + 1;
            const rank2 = order.indexOf(t2.name) + 1;
            return `
                <div class="ranking-item">
                    <span class="ranking-metric">${metric}</span>
                    <div class="ranking-values">
                        <span class="rank team1">#${rank1}</span>
                        <span class="rank team2">#${rank2}</span>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = `
            <div class="ranking-header">
                <span></span>
                <span class="team1-label">${t1.name}</span>
                <span class="team2-label">${t2.name}</span>
            </div>
            ${html}
        `;
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
        renderPlayerRadarChart(player);

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

    function renderPlayerRadarChart(player) {
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

    // --- Recent Games Tab ---
    let currentRoundNum = 19;
    const recentGamesTab = document.getElementById('tab-recent-games');
    const roundDropdown = document.getElementById('round-dropdown');
    const prevRoundBtn = document.getElementById('prev-round');
    const nextRoundBtn = document.getElementById('next-round');
    const matchesContainer = document.getElementById('matches-container');

    // Initialize Recent Games when tab is clicked
    tabBtns.forEach(btn => {
        if (btn.getAttribute('data-tab') === 'tab-recent-games') {
            btn.addEventListener('click', () => {
                if (!roundDropdown.options.length) {
                    initRecentGamesTab();
                }
            });
        }
    });

    async function initRecentGamesTab() {
        try {
            // Fetch current round
            const roundResponse = await fetch('/api/current-round');
            const roundData = await roundResponse.json();
            currentRoundNum = roundData.current_round;

            // Populate round dropdown (1-34)
            for (let i = 1; i <= 34; i++) {
                const option = new Option(`${translations[currentLang].round_label} ${i}`, i);
                roundDropdown.add(option);
            }
            roundDropdown.value = currentRoundNum;

            // Load matches for current round
            await loadRoundMatches(currentRoundNum);

            // Set up round navigation
            roundDropdown.addEventListener('change', (e) => {
                loadRoundMatches(parseInt(e.target.value));
            });

            prevRoundBtn.addEventListener('click', () => {
                if (currentRoundNum > 1) {
                    currentRoundNum--;
                    roundDropdown.value = currentRoundNum;
                    loadRoundMatches(currentRoundNum);
                }
            });

            nextRoundBtn.addEventListener('click', () => {
                if (currentRoundNum < 34) {
                    currentRoundNum++;
                    roundDropdown.value = currentRoundNum;
                    loadRoundMatches(currentRoundNum);
                }
            });

        } catch (error) {
            console.error('Error initializing Recent Games:', error);
            matchesContainer.innerHTML = `<div class="error">Error loading data: ${error.message}</div>`;
        }
    }

    async function loadRoundMatches(roundNum) {
        try {
            matchesContainer.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Loading matches...</p></div>';

            const response = await fetch(`/api/recent-games?round=${roundNum}`);
            const data = await response.json();

            currentRoundNum = roundNum;
            renderMatches(data.matches);

        } catch (error) {
            console.error('Error loading matches:', error);
            matchesContainer.innerHTML = `<div class="error">Error: ${error.message}</div>`;
        }
    }

    function renderMatches(matches) {
        if (!matches || matches.length === 0) {
            matchesContainer.innerHTML = '<div class="no-matches">No matches found for this round.</div>';
            return;
        }

        // Group matches by date
        const grouped = {};
        matches.forEach(match => {
            const date = match.date;
            if (!grouped[date]) grouped[date] = [];
            grouped[date].push(match);
        });

        let html = '';
        Object.keys(grouped).sort().forEach(date => {
            const dateObj = new Date(date + 'T12:00:00');
            const dateStr = dateObj.toLocaleDateString(currentLang === 'tr' ? 'tr-TR' : 'en-US', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });

            html += `<div class="date-group"><h3 class="date-header">${dateStr}</h3>`;

            grouped[date].forEach(match => {
                html += renderMatchCard(match);
            });

            html += '</div>';
        });

        matchesContainer.innerHTML = html;

        // Attach expand/collapse listeners
        document.querySelectorAll('.match-card').forEach(card => {
            const expandBtn = card.querySelector('.expand-btn');
            if (expandBtn) {
                expandBtn.addEventListener('click', () => {
                    card.classList.toggle('expanded');
                    const details = card.querySelector('.match-details');
                    if (card.classList.contains('expanded')) {
                        details.style.maxHeight = details.scrollHeight + 'px';
                        expandBtn.textContent = '▲';
                    } else {
                        details.style.maxHeight = '0';
                        expandBtn.textContent = '▼';
                    }
                });
            }
        });
    }

    function renderMatchCard(match) {
        const pred = match.prediction;
        if (!pred) {
            return `
                <div class="match-card no-prediction">
                    <div class="match-header">
                        <div class="team home">${match.home_team}</div>
                        <div class="match-center">
                            <div class="match-time">${match.time}</div>
                            <div class="no-pred-label">No prediction yet</div>
                        </div>
                        <div class="team away">${match.away_team}</div>
                    </div>
                </div>
            `;
        }

        const confClass = pred.confidence;
        const confLabel = translations[currentLang][`confidence_${pred.confidence}`] || pred.confidence;

        // Calculate confidence metrics for explanation
        const maxProb = Math.max(pred.probabilities.home_win, pred.probabilities.draw, pred.probabilities.away_win);
        const minProb = Math.min(pred.probabilities.home_win, pred.probabilities.draw, pred.probabilities.away_win);
        const spread = maxProb - minProb;

        // Build confidence explanation HTML
        const confidenceExplanations = {
            high: {
                icon: '🟢',
                title: 'High Confidence Prediction',
                reason: `Our model shows a <strong>clear favorite</strong> with ${maxProb.toFixed(1)}% probability and a significant ${spread.toFixed(1)}% spread between outcomes. This indicates strong predictive signals from our analysis.`,
                indicators: [
                    { label: 'Max Probability', value: `${maxProb.toFixed(1)}%`, status: maxProb >= 60 ? 'good' : 'ok' },
                    { label: 'Outcome Spread', value: `${spread.toFixed(1)}%`, status: spread >= 40 ? 'good' : 'ok' },
                    { label: 'Model Agreement', value: 'Strong', status: 'good' }
                ]
            },
            medium: {
                icon: '🟡',
                title: 'Medium Confidence Prediction',
                reason: `Our model identifies a <strong>moderate favorite</strong> with ${maxProb.toFixed(1)}% probability. While the prediction is reliable, there's more uncertainty compared to high confidence matches.`,
                indicators: [
                    { label: 'Max Probability', value: `${maxProb.toFixed(1)}%`, status: maxProb >= 45 ? 'ok' : 'warn' },
                    { label: 'Outcome Spread', value: `${spread.toFixed(1)}%`, status: spread >= 25 ? 'ok' : 'warn' },
                    { label: 'Model Agreement', value: 'Moderate', status: 'ok' }
                ]
            },
            low: {
                icon: '🔴',
                title: 'Low Confidence Prediction',
                reason: `This is a <strong>highly competitive match</strong> with close probabilities (max: ${maxProb.toFixed(1)}%, spread: ${spread.toFixed(1)}%). Multiple outcomes are nearly equally likely, making this prediction less certain.`,
                indicators: [
                    { label: 'Max Probability', value: `${maxProb.toFixed(1)}%`, status: 'warn' },
                    { label: 'Outcome Spread', value: `${spread.toFixed(1)}%`, status: 'warn' },
                    { label: 'Model Agreement', value: 'Uncertain', status: 'warn' }
                ]
            }
        };

        const currentConfidence = confidenceExplanations[confClass];
        const confidenceHtml = `
            <div class="confidence-explanation-panel">
                <div class="confidence-header">
                    <span class="confidence-icon">${currentConfidence.icon}</span>
                    <h4>${currentConfidence.title}</h4>
                </div>
                <p class="confidence-reason">${currentConfidence.reason}</p>
                <div class="confidence-indicators">
                    ${currentConfidence.indicators.map(ind => `
                        <div class="confidence-indicator">
                            <span class="indicator-label">${ind.label}</span>
                            <div class="indicator-value-wrapper">
                                <span class="indicator-value ${ind.status}">${ind.value}</span>
                                <div class="indicator-status ${ind.status}">
                                    ${ind.status === 'good' ? '✓' : ind.status === 'ok' ? '○' : '!'}
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;


        // Build scorelines HTML
        let scorelinesHtml = '';
        if (pred.top5_scores && pred.top5_scores.length > 0) {
            scorelinesHtml = `
                <div class="insights-panel">
                    <h4><span class="icon">📊</span> Most Likely Scorelines</h4>
                    <div class="score-probabilities">
                        ${pred.top5_scores.map(s => `
                            <div class="scoreline-row">
                                <span class="scoreline-label">${s.score}</span>
                                <div class="scoreline-bar-wrapper">
                                    <div class="scoreline-bar" style="width: ${s.percentage}%">
                                        <span class="scoreline-pct">${s.percentage}%</span>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        // Build Markov form HTML
        let formHtml = '';
        if (pred.markov_form) {
            const m1 = pred.markov_form.team1;
            const m2 = pred.markov_form.team2;
            const getFormClass = (label) => {
                if (label.includes('Hot')) return 'hot';
                if (label.includes('Cold')) return 'cold';
                return 'neutral';
            };

            formHtml = `
                <div class="insights-panel">
                    <h4><span class="icon">🔥</span> Current Form (Markov Analysis)</h4>
                    <div class="form-indicators">
                        <div class="form-team">
                            <div class="form-team-name">${m1.name}</div>
                            <div class="form-badge ${getFormClass(m1.form_label)}">${m1.form_label}</div>
                            <div class="form-probs">
                                <div class="form-prob-item">
                                    <span class="prob-label">Win</span>
                                    <span class="prob-value">${m1.next_win_prob}%</span>
                                </div>
                                <div class="form-prob-item">
                                    <span class="prob-label">Draw</span>
                                    <span class="prob-value">${m1.next_draw_prob}%</span>
                                </div>
                                <div class="form-prob-item">
                                    <span class="prob-label">Loss</span>
                                    <span class="prob-value">${m1.next_loss_prob}%</span>
                                </div>
                            </div>
                            <div class="form-meta">
                                <span>${m1.matches_analyzed} matches • ${m1.hidden_states} states</span>
                            </div>
                        </div>
                        <div class="form-team">
                            <div class="form-team-name">${m2.name}</div>
                            <div class="form-badge ${getFormClass(m2.form_label)}">${m2.form_label}</div>
                            <div class="form-probs">
                                <div class="form-prob-item">
                                    <span class="prob-label">Win</span>
                                    <span class="prob-value">${m2.next_win_prob}%</span>
                                </div>
                                <div class="form-prob-item">
                                    <span class="prob-label">Draw</span>
                                    <span class="prob-value">${m2.next_draw_prob}%</span>
                                </div>
                                <div class="form-prob-item">
                                    <span class="prob-label">Loss</span>
                                    <span class="prob-value">${m2.next_loss_prob}%</span>
                                </div>
                            </div>
                            <div class="form-meta">
                                <span>${m2.matches_analyzed} matches • ${m2.hidden_states} states</span>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }

        // Build HMM state profiles HTML
        let stateProfilesHtml = '';
        if (pred.markov_form) {
            const m1 = pred.markov_form.team1;
            const m2 = pred.markov_form.team2;

            const buildStateProfiles = (team) => {
                if (!team.state_profiles || team.state_profiles.length === 0) return '';
                return team.state_profiles.map(state => `
                    <div class="state-profile-card">
                        <div class="state-header">
                            <span class="state-label">${state.label}</span>
                            <span class="state-matches">${state.count} matches</span>
                        </div>
                        <div class="state-probs">
                            <div class="state-prob win">
                                <span class="prob-bar" style="width: ${state.win_prob}%"></span>
                                <span class="prob-text">W ${state.win_prob}%</span>
                            </div>
                            <div class="state-prob draw">
                                <span class="prob-bar" style="width: ${state.draw_prob}%"></span>
                                <span class="prob-text">D ${state.draw_prob}%</span>
                            </div>
                            <div class="state-prob loss">
                                <span class="prob-bar" style="width: ${state.loss_prob}%"></span>
                                <span class="prob-text">L ${state.loss_prob}%</span>
                            </div>
                        </div>
                    </div>
                `).join('');
            };

            stateProfilesHtml = `
                <div class="insights-panel">
                    <h4><span class="icon">🧠</span> HMM State Breakdown</h4>
                    <p class="panel-subtitle">Historical form states detected by the Hidden Markov Model</p>
                    <div class="state-profiles-grid">
                        <div class="team-states">
                            <h5>${m1.name} Form States</h5>
                            <div class="states-list">
                                ${buildStateProfiles(m1)}
                            </div>
                        </div>
                        <div class="team-states">
                            <h5>${m2.name} Form States</h5>
                            <div class="states-list">
                                ${buildStateProfiles(m2)}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }

        // Build ratings HTML
        let ratingsHtml = '';
        if (pred.avg_ratings) {
            const maxRating = 10;
            const r1 = pred.avg_ratings.team1;
            const r2 = pred.avg_ratings.team2;
            ratingsHtml = `
                <div class="insights-panel">
                    <h4><span class="icon">⭐</span> Average Player Ratings</h4>
                    <div class="ratings-comparison">
                        <div class="rating-row">
                            <span class="rating-team-name">${match.home_team}</span>
                            <div class="rating-bar-wrapper">
                                <div class="rating-bar team1" style="width: ${(r1 / maxRating) * 100}%"></div>
                            </div>
                            <span class="rating-value team1">${r1}</span>
                        </div>
                        <div class="rating-row">
                            <span class="rating-team-name">${match.away_team}</span>
                            <div class="rating-bar-wrapper">
                                <div class="rating-bar team2" style="width: ${(r2 / maxRating) * 100}%"></div>
                            </div>
                            <span class="rating-value team2">${r2}</span>
                        </div>
                    </div>
                </div>
            `;
        }

        return `
            <div class="match-card" data-match-id="${match.match_id}">
                <div class="match-header">
                    <div class="team home">
                        <span class="team-name">${match.home_team}</span>
                        ${pred.team1_logo_url ? `<img src="${pred.team1_logo_url}" alt="${match.home_team} Logo" class="team-logo">` : ''}
                    </div>
                    <div class="match-center">
                        <div class="predicted-score">${pred.predicted_score}</div>
                        <div class="match-time">${match.time}</div>
                        <div class="confidence-badge ${confClass}">${confLabel}</div>
                    </div>
                    <div class="team away">
                        ${pred.team2_logo_url ? `<img src="${pred.team2_logo_url}" alt="${match.away_team} Logo" class="team-logo">` : ''}
                        <span class="team-name">${match.away_team}</span>
                    </div>
                    <button class="expand-btn">▼</button>
                </div>

                <div class="probabilities-bar">
                    <div class="prob home" style="width: ${pred.probabilities.home_win}%" title="Home Win: ${pred.probabilities.home_win}%">
                        ${pred.probabilities.home_win}%
                    </div>
                    <div class="prob draw" style="width: ${pred.probabilities.draw}%" title="Draw: ${pred.probabilities.draw}%">
                        ${pred.probabilities.draw}%
                    </div>
                    <div class="prob away" style="width: ${pred.probabilities.away_win}%" title="Away Win: ${pred.probabilities.away_win}%">
                        ${pred.probabilities.away_win}%
                    </div>
                </div>

                <div class="match-details">
                    ${confidenceHtml}
                    
                    <div class="details-grid">
                        <div class="detail-item">
                            <label>Expected Goals</label>
                            <div class="xg-display">
                                <span class="xg home">${pred.expected_goals.home.toFixed(2)}</span>
                                <span class="xg-separator">-</span>
                                <span class="xg away">${pred.expected_goals.away.toFixed(2)}</span>
                            </div>
                        </div>
                    </div>

                    <!-- Enhanced Insights Section -->
                    <div class="insights-container">
                        ${scorelinesHtml}
                        ${formHtml}
                        ${stateProfilesHtml}
                        ${ratingsHtml}
                    </div>
                </div>
            </div>
        `;
    }
});
