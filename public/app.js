// Team logos mapping
const TEAM_LOGOS = {
    'Galatasaray': '⭐',
    'Fenerbahçe': '🐤',
    'Beşiktaş': '🦅',
    'Trabzonspor': '⚡',
    'Başakşehir': '🍊',
    'Alanyaspor': '🍀',
    'Adana Demirspor': '⚔️',
    'Ankaragücü': '💛',
    'Antalyaspor': '🔴',
    'Çaykur Rizespor': '💚',
    'Eyüpspor': '🟣',
    'Fatih Karagümrük': '🔴',
    'Gaziantep FK': '🔷',
    'Göztepe': '💛',
    'Hatayspor': '🌙',
    'Kasımpaşa': '🔵',
    'Kayserispor': '🔴',
    'Konyaspor': '💚',
    'Samsunspor': '🔴',
    'Sivasspor': '❤️',
};

document.addEventListener('DOMContentLoaded', async () => {
    // --- Globals ---
    // Comparison Tab Elements
    const team1Select = document.getElementById('team1-select');
    const team2Select = document.getElementById('team2-select');
    const statsContainer = document.getElementById('stats-container');
    const team1Display = document.getElementById('team1-display');
    const team2Display = document.getElementById('team2-display');

    // Simulation Tab Elements
    const simLeagueSelect = document.getElementById('sim-league');
    const simCrossLeagueToggle = document.getElementById('sim-cross-league');
    const simTeam1LeagueSelect = document.getElementById('sim-team1-league');
    const simTeam2LeagueSelect = document.getElementById('sim-team2-league');
    const simSingleLeagueGroup = document.getElementById('sim-single-league-group');
    const simHomeLeagueGroup = document.getElementById('sim-home-league-group');
    const simAwayLeagueGroup = document.getElementById('sim-away-league-group');
    const simTeam1Select = document.getElementById('sim-team1');
    const simTeam2Select = document.getElementById('sim-team2');
    const simTeam1FormationSelect = document.getElementById('sim-team1-formation');
    const simTeam2FormationSelect = document.getElementById('sim-team2-formation');
    const team1AdjSlider = document.getElementById('team1-adjustment');
    const team2AdjSlider = document.getElementById('team2-adjustment');
    const team1AdjValue = document.getElementById('team1-adj-value');
    const team2AdjValue = document.getElementById('team2-adj-value');
    const btnRunSim = document.getElementById('btn-run-sim');
    const simResults = document.getElementById('sim-results');
    const simEasyAdjustments = document.getElementById('sim-easy-adjustments');
    const simAdvancedAdjustments = document.getElementById('sim-advanced-adjustments');
    const simModeButtons = document.querySelectorAll('.sim-mode-btn');
    const SIM_CLUSTER_SLUGS = [
        'goalkeeper-zone',
        'back-left',
        'back-right',
        'mid-def',
        'mid-att',
        'wing-left',
        'wing-right',
    ];
    const simTeam1DetailedSliders = SIM_CLUSTER_SLUGS.map(
        (slug) => document.getElementById(`sim-team1-${slug}`)
    );
    const simTeam1DetailedValues = SIM_CLUSTER_SLUGS.map(
        (slug) => document.getElementById(`sim-team1-${slug}-value`)
    );
    const simTeam2DetailedSliders = SIM_CLUSTER_SLUGS.map(
        (slug) => document.getElementById(`sim-team2-${slug}`)
    );
    const simTeam2DetailedValues = SIM_CLUSTER_SLUGS.map(
        (slug) => document.getElementById(`sim-team2-${slug}-value`)
    );

    // Drawing Board Tab Elements
    const drawingBoardTab = document.getElementById('tab-drawing-board');
    const dbLeagueSelect = document.getElementById('db-league');
    const dbTeam1Select = document.getElementById('db-team1');
    const dbTeam2Select = document.getElementById('db-team2');
    const dbTeam1Panel = document.getElementById('db-team1-panel');
    const dbTeam2Panel = document.getElementById('db-team2-panel');
    const dbTeam1Name = document.getElementById('db-team1-name');
    const dbTeam2Name = document.getElementById('db-team2-name');
    const dbTeam1Badge = document.getElementById('db-team1-badge');
    const dbTeam2Badge = document.getElementById('db-team2-badge');
    const dbTeam1FormationSelect = document.getElementById('db-team1-formation');
    const dbTeam2FormationSelect = document.getElementById('db-team2-formation');

    const dbTeam1Attack = document.getElementById('db-team1-attack');
    const dbTeam1Midfield = document.getElementById('db-team1-midfield');
    const dbTeam1Defense = document.getElementById('db-team1-defense');
    const dbTeam1Goalkeeper = document.getElementById('db-team1-goalkeeper');
    const dbTeam1AttackValue = document.getElementById('db-team1-attack-value');
    const dbTeam1MidfieldValue = document.getElementById('db-team1-midfield-value');
    const dbTeam1DefenseValue = document.getElementById('db-team1-defense-value');
    const dbTeam1GoalkeeperValue = document.getElementById('db-team1-goalkeeper-value');

    const dbTeam2Attack = document.getElementById('db-team2-attack');
    const dbTeam2Midfield = document.getElementById('db-team2-midfield');
    const dbTeam2Defense = document.getElementById('db-team2-defense');
    const dbTeam2Goalkeeper = document.getElementById('db-team2-goalkeeper');
    const dbTeam2AttackValue = document.getElementById('db-team2-attack-value');
    const dbTeam2MidfieldValue = document.getElementById('db-team2-midfield-value');
    const dbTeam2DefenseValue = document.getElementById('db-team2-defense-value');
    const dbTeam2GoalkeeperValue = document.getElementById('db-team2-goalkeeper-value');

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

    // Deep Player Analysis Tab Elements
    const playerAnalysisTab = document.getElementById('tab-player-analysis');
    const paTeamFilter = document.getElementById('pa-team-filter');
    const paPlayerA = document.getElementById('pa-player-a');
    const paEnableCompare = document.getElementById('pa-enable-compare');
    const paPlayerB = document.getElementById('pa-player-b');
    const paStatus = document.getElementById('pa-status');
    const paContent = document.getElementById('pa-content');
    const paCards = document.getElementById('pa-cards');
    const paCompare = document.getElementById('pa-compare');
    const worldCupBracketFrame = document.getElementById('world-cup-bracket-frame');
    const worldCupBracketStatus = document.getElementById('world-cup-bracket-status');

    // Tab Navigation
    const tabBtns = document.querySelectorAll('.nav-btn');
    const tabContents = document.querySelectorAll('.view-section');
    const MIN_ROUND_NUM = 1;
    const MAX_ROUND_NUM = 34;
    const roundDisplayText = document.getElementById('round-display-text');
    const prevRoundBtn = document.getElementById('prev-round');
    const nextRoundBtn = document.getElementById('next-round');
    const matchesContainer = document.getElementById('matches-container');

    let selectedTeam1 = null;
    let selectedTeam2 = null;
    let playerAnalysisData = null;
    let playerAnalysisLoaded = false;
    let lastSimTeam1 = '';
    let lastSimTeam2 = '';
    let currentRoundNum = 19;
    let recentGamesInitialized = false;
    let teamData = Array.isArray(window.teamData) ? window.teamData : [];
    let simulationLeagues = [];
    let simulationTeamsByLeague = new Map();
    let currentSimulationLeague = '';
    let currentSimulationHomeLeague = '';
    let currentSimulationAwayLeague = '';
    let simulationCrossLeagueEnabled = false;
    let simulationAdjustmentMode = 'easy';
    let drawingBoardInitialized = false;
    let worldCupBracketLoaded = false;
    let drawingBoardLeague = '';
    let drawingBoardLineupTeam1 = null;
    let drawingBoardLineupTeam2 = null;
    let drawingBoardLastTeam1 = '';
    let drawingBoardLastTeam2 = '';
    let drawingBoardSyncToken = 0;
    let formationHelpersReady = false;
    let formationHelpersLoadPromise = null;
    let pitchUpdateToken = 0;
    let selectionSyncToken = 0;
    let hmmSyncToken = 0;
    const LIQUID_SURFACE_SELECTOR = '.main-nav, .config-card, .match-card, .insights-panel, .result-card, .round-selector, .lang-btn, .analysis-panel, .team-card, .scoreline-perspective-card, .confidence-indicator';
    let liquidSurfaceEls = [];
    let liquidFrameToken = null;
    let liquidPointerX = window.innerWidth * 0.5;
    let liquidPointerY = window.innerHeight * 0.35;
    let liquidScrollY = window.scrollY || 0;
    let liquidGlassInitialized = false;
    const reduceMotionMedia = window.matchMedia('(prefers-reduced-motion: reduce)');

    const SIM_FORMATIONS = [
        '3-1-4-2', '3-2-4-1', '3-3-3-1', '3-4-1-2', '3-4-2-1', '3-4-3', '3-5-1-1', '3-5-2',
        '4-1-3-2', '4-1-4-1', '4-2-2-2', '4-2-3-1', '4-3-1-2', '4-3-3', '4-4-1-1', '4-4-2',
        '4-5-1', '5-3-2', '5-4-1'
    ];

    // --- Initialization moved to after declarations ---

    // --- Localization ---
    const translations = {
        en: {
            subtitle: "Next-Gen Football Analytics & Simulation",
            nav_analysis: "Analysis",
            nav_simulation: "Simulation",
            nav_drawing_board: "Drawing Board",
            nav_recent_games: "Upcoming Games",
            nav_player_analysis: "Player Lab",
            nav_world_cup_bracket: "World Cup Bracket",
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
            drawing_board_title: "Drawing Board",
            drawing_board_desc: "Rate each team unit with separate sliders before matchday.",
            match_setup: "Match Setup",
            label_league: "League",
            label_home_league: "Home League",
            label_away_league: "Away League",
            cross_league_toggle: "Cross-League Match",
            select_short: "Select...",
            choose_league_placeholder: "Select League",
            label_home_formation: "Home Formation",
            label_away_formation: "Away Formation",
            select_formation_short: "Formation...",
            sim_adjustment_mode: "Adjustment Mode",
            sim_mode_easy: "Easy Mode",
            sim_mode_advanced: "Advanced Mode",
            home_adj: "Home Team Adjustment",
            away_adj: "Away Team Adjustment",
            db_home_adjustments: "Home Unit Adjustments",
            db_away_adjustments: "Away Unit Adjustments",
            db_attack: "Attack",
            db_midfield: "Midfield",
            db_defense: "Defense",
            db_goalkeeper: "Goalkeeper",
            cluster_goalkeeper_zone: "Goalkeeper_Zone",
            cluster_back_left: "Back_Left",
            cluster_back_right: "Back_Right",
            cluster_mid_def: "Mid_Def",
            cluster_mid_att: "Mid_Att",
            cluster_wing_left: "Wing_Left",
            cluster_wing_right: "Wing_Right",
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
            world_cup_bracket_title: "2026 World Cup Bracket",
            world_cup_bracket_desc: "Use the full tournament predictor inside Gol Oncesi.",
            world_cup_bracket_note: "The original interactive bracket is mirrored here and loads on demand.",
            world_cup_bracket_open_full: "Open full page",
            world_cup_bracket_loading: "Loading bracket...",
            world_cup_bracket_error: "Bracket failed to load. Open the full page instead.",
            player_analysis_title: "Deep Player Analysis",
            player_analysis_desc: "Profile, season summary, and detailed statistics with instant player comparison.",
            pa_team_filter_label: "Team Filter",
            pa_team_filter_all: "All Teams",
            pa_player_a_label: "Player A",
            pa_player_b_label: "Player B",
            pa_compare_toggle_label: "Compare Mode",
            pa_choose_player: "Choose a player...",
            round_label: "Round",
            loading_matches: "Loading matches...",
            confidence_high: "High Confidence",
            confidence_medium: "Medium Confidence",
            confidence_low: "Low Confidence",
            hmm_adjustments: "HMM Adjustment"
        },
        tr: {
            subtitle: "Yeni Nesil Futbol Analizi ve Simülasyonu",
            nav_analysis: "Analiz",
            nav_simulation: "Simülasyon",
            nav_drawing_board: "Çizim Tahtası",
            nav_recent_games: "Yaklaşan Maçlar",
            nav_player_analysis: "Oyuncu Laboratuvarı",
            nav_world_cup_bracket: "Dünya Kupası Braketi",
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
            drawing_board_title: "Çizim Tahtası",
            drawing_board_desc: "Maç öncesi takımın her bölümünü ayrı kaydırıcılarla puanlayın.",
            match_setup: "Maç Kurulumu",
            label_league: "Lig",
            label_home_league: "Ev Sahibi Ligi",
            label_away_league: "Deplasman Ligi",
            cross_league_toggle: "Ligler Arası Maç",
            select_short: "Seç...",
            choose_league_placeholder: "Lig seçin...",
            label_home_formation: "Ev Sahibi Dizilişi",
            label_away_formation: "Deplasman Dizilişi",
            select_formation_short: "Diziliş...",
            sim_adjustment_mode: "Ayar Modu",
            sim_mode_easy: "Kolay Mod",
            sim_mode_advanced: "Gelişmiş Mod",
            home_adj: "Ev Sahibi Ayarı",
            away_adj: "Deplasman Ayarı",
            db_home_adjustments: "Ev Sahibi Birim Ayarları",
            db_away_adjustments: "Deplasman Birim Ayarları",
            db_attack: "Hücum",
            db_midfield: "Orta Saha",
            db_defense: "Defans",
            db_goalkeeper: "Kaleci",
            cluster_goalkeeper_zone: "Goalkeeper_Zone",
            cluster_back_left: "Back_Left",
            cluster_back_right: "Back_Right",
            cluster_mid_def: "Mid_Def",
            cluster_mid_att: "Mid_Att",
            cluster_wing_left: "Wing_Left",
            cluster_wing_right: "Wing_Right",
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
            world_cup_bracket_title: "2026 Dünya Kupası Braketi",
            world_cup_bracket_desc: "Tam turnuva tahmin aracını Gol Oncesi içinde kullanın.",
            world_cup_bracket_note: "Orijinal interaktif bracket burada aynalanır ve ihtiyaç olduğunda yüklenir.",
            world_cup_bracket_open_full: "Tam sayfa aç",
            world_cup_bracket_loading: "Bracket yükleniyor...",
            world_cup_bracket_error: "Bracket yüklenemedi. Bunun yerine tam sayfayı açın.",
            player_analysis_title: "Derin Oyuncu Analizi",
            player_analysis_desc: "Profil, sezon özeti ve detaylı istatistikleri anında oyuncu karşılaştırmasıyla inceleyin.",
            pa_team_filter_label: "Takım Filtresi",
            pa_team_filter_all: "Tüm Takımlar",
            pa_player_a_label: "Oyuncu A",
            pa_player_b_label: "Oyuncu B",
            pa_compare_toggle_label: "Karşılaştırma Modu",
            pa_choose_player: "Oyuncu seçin...",
            round_label: "Hafta",
            loading_matches: "Maçlar yükleniyor...",
            confidence_high: "Yüksek Güven",
            confidence_medium: "Orta Güven",
            confidence_low: "Düşük Güven",
            hmm_adjustments: "HMM Ayarı"
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

        updateRoundDisplay();

        if (playerAnalysisLoaded) {
            populateTeamFilter();
            populatePlayerSelectors();
            renderPlayerAnalysis();
        }
    }

    function initLiquidGlass() {
        if (liquidGlassInitialized) return;
        liquidGlassInitialized = true;

        const onPointerMove = (event) => {
            liquidPointerX = event.clientX;
            liquidPointerY = event.clientY;
            queueLiquidGlassUpdate();
        };

        const onScroll = () => {
            liquidScrollY = window.scrollY || window.pageYOffset || 0;
            queueLiquidGlassUpdate();
        };

        const onResize = () => {
            liquidPointerX = Math.min(liquidPointerX, window.innerWidth);
            liquidPointerY = Math.min(liquidPointerY, window.innerHeight);
            queueLiquidGlassUpdate();
        };

        window.addEventListener('pointermove', onPointerMove, { passive: true });
        window.addEventListener('scroll', onScroll, { passive: true });
        window.addEventListener('resize', onResize, { passive: true });

        if (typeof reduceMotionMedia.addEventListener === 'function') {
            reduceMotionMedia.addEventListener('change', queueLiquidGlassUpdate);
        } else if (typeof reduceMotionMedia.addListener === 'function') {
            reduceMotionMedia.addListener(queueLiquidGlassUpdate);
        }

        refreshLiquidGlassTargets();
    }

    function refreshLiquidGlassTargets() {
        liquidSurfaceEls = Array.from(document.querySelectorAll(LIQUID_SURFACE_SELECTOR));
        queueLiquidGlassUpdate();
    }

    function queueLiquidGlassUpdate() {
        if (liquidFrameToken) return;
        liquidFrameToken = requestAnimationFrame(updateLiquidGlassFrame);
    }

    function updateLiquidGlassFrame() {
        liquidFrameToken = null;

        const rootStyle = document.documentElement.style;
        if (reduceMotionMedia.matches) {
            rootStyle.setProperty('--bg-focus-x', '12%');
            rootStyle.setProperty('--bg-focus-y', '18%');
            rootStyle.setProperty('--bg-drift-x', '0%');
            rootStyle.setProperty('--bg-drift-y', '0%');
            rootStyle.setProperty('--bg-parallax-x', '0px');
            rootStyle.setProperty('--bg-parallax-y', '0px');
            rootStyle.setProperty('--overlay-shift-x', '0px');
            rootStyle.setProperty('--overlay-shift-y', '0px');
            rootStyle.setProperty('--overlay-shift-x-inv', '0px');
            rootStyle.setProperty('--overlay-shift-y-inv', '0px');
            return;
        }

        const viewportW = Math.max(1, window.innerWidth);
        const viewportH = Math.max(1, window.innerHeight);
        const pointerXNorm = Math.min(1, Math.max(0, liquidPointerX / viewportW));
        const pointerYNorm = Math.min(1, Math.max(0, liquidPointerY / viewportH));
        const limitedScroll = Math.max(-28, Math.min(28, liquidScrollY * 0.015));

        rootStyle.setProperty('--bg-focus-x', `${(8 + pointerXNorm * 18).toFixed(2)}%`);
        rootStyle.setProperty('--bg-focus-y', `${(10 + pointerYNorm * 22).toFixed(2)}%`);
        rootStyle.setProperty('--bg-drift-x', `${((pointerXNorm - 0.5) * 12).toFixed(2)}%`);
        rootStyle.setProperty('--bg-drift-y', `${((pointerYNorm - 0.5) * 13 + Math.sin(liquidScrollY * 0.0022) * 2).toFixed(2)}%`);
        rootStyle.setProperty('--bg-parallax-x', `${((pointerXNorm - 0.5) * -16).toFixed(2)}px`);
        rootStyle.setProperty('--bg-parallax-y', `${((pointerYNorm - 0.5) * -11 - limitedScroll).toFixed(2)}px`);
        const overlayShiftX = ((pointerXNorm - 0.5) * 20);
        const overlayShiftY = ((pointerYNorm - 0.5) * 20 + limitedScroll);
        rootStyle.setProperty('--overlay-shift-x', `${overlayShiftX.toFixed(2)}px`);
        rootStyle.setProperty('--overlay-shift-y', `${overlayShiftY.toFixed(2)}px`);
        rootStyle.setProperty('--overlay-shift-x-inv', `${(overlayShiftX * -0.65).toFixed(2)}px`);
        rootStyle.setProperty('--overlay-shift-y-inv', `${(overlayShiftY * -0.65).toFixed(2)}px`);

        liquidSurfaceEls.forEach((el) => {
            const rect = el.getBoundingClientRect();
            if (rect.width < 24 || rect.height < 24) return;
            if (rect.bottom < -140 || rect.top > viewportH + 140) return;

            const localX = Math.min(1, Math.max(0, (liquidPointerX - rect.left) / rect.width));
            const localY = Math.min(1, Math.max(0, (liquidPointerY - rect.top) / rect.height));
            const centerY = rect.top + (rect.height * 0.5);
            const depth = Math.max(0, Math.min(1, 1 - (Math.abs(centerY - (viewportH * 0.5)) / (viewportH * 0.8))));
            const wave = Math.sin((liquidScrollY + centerY) * 0.01) * 2.6;
            const shiftX = ((localX - 0.5) * 18).toFixed(2);
            const shiftY = (((localY - 0.5) * 14) + wave).toFixed(2);
            const tilt = (146 + ((localX - 0.5) * 34) - ((localY - 0.5) * 16)).toFixed(2);
            const scale = (1.03 + (depth * 0.08)).toFixed(3);
            const blur = (5 + (depth * 7)).toFixed(2);
            const glossOpacity = (0.30 + (depth * 0.34)).toFixed(3);

            el.style.setProperty('--lg-local-x', `${(localX * 100).toFixed(1)}%`);
            el.style.setProperty('--lg-local-y', `${(localY * 100).toFixed(1)}%`);
            el.style.setProperty('--lg-pointer-x', `${(100 - (localX * 100)).toFixed(1)}%`);
            el.style.setProperty('--lg-pointer-y', `${(100 - (localY * 100)).toFixed(1)}%`);
            el.style.setProperty('--lg-shift-x', `${shiftX}px`);
            el.style.setProperty('--lg-shift-y', `${shiftY}px`);
            el.style.setProperty('--lg-scale', scale);
            el.style.setProperty('--lg-blur', `${blur}px`);
            el.style.setProperty('--lg-tilt', `${tilt}deg`);
            el.style.setProperty('--lg-gloss-opacity', glossOpacity);
        });
    }

    async function loadLiveAnalysisData(forceRefresh = false) {
        try {
            const url = `/api/analysis-data?refresh=${forceRefresh ? 1 : 0}&t=${Date.now()}`;
            const response = await fetch(url, { cache: 'no-store' });
            if (!response.ok) {
                throw new Error(`analysis data request failed (${response.status})`);
            }
            const payload = await response.json();
            if (Array.isArray(payload?.teams) && payload.teams.length > 0) {
                teamData = payload.teams;
                window.teamData = payload.teams;
            }
        } catch (error) {
            console.warn('Using fallback analysis dataset from public/data.js:', error.message);
        }
    }

    // --- Initialization ---
    await loadLiveAnalysisData(true);
    if (teamData.length > 0) {
        populateAllSelectors();
        initTabs();
        initExploreTab();
        initPlayerAnalysisTab();
        initLanguage();
        await ensureSimulationSelectorsPopulated(true);
        initLiquidGlass();
    } else {
        console.error("No data found. Ensure data.js is loaded.");
        alert("Data not found. Please run the ingestion script.");
    }

    // --- Functions ---
    function buildPlaceholderOption(select, fallbackText = 'Select...') {
        const placeholder = select?.querySelector('option[value=""]');
        const option = placeholder ? placeholder.cloneNode(true) : new Option(fallbackText, '');
        option.disabled = true;
        option.selected = true;
        if (!option.value) option.value = '';
        return option;
    }

    function populateAllSelectors() {
        const teamNames = teamData.map(t => t.name).sort();

        // Helper to populate a specific select element
        const fillSelect = (select) => {
            if (!select) return;
            const placeholderOption = buildPlaceholderOption(select, 'Select...');
            select.innerHTML = '';
            select.add(placeholderOption);
            teamNames.forEach(name => {
                select.add(new Option(name, name));
            });
        };

        const fillFormationSelect = (select) => {
            if (!select) return;
            const placeholderOption = buildPlaceholderOption(select, 'Formation...');
            select.innerHTML = '';
            select.add(placeholderOption);
            SIM_FORMATIONS.forEach(formation => {
                select.add(new Option(formation, formation));
            });
        };

        fillSelect(team1Select);
        fillSelect(team2Select);
        fillFormationSelect(simTeam1FormationSelect);
        fillFormationSelect(simTeam2FormationSelect);
        fillFormationSelect(dbTeam1FormationSelect);
        fillFormationSelect(dbTeam2FormationSelect);
    }

    function getSimulationTeamMeta(leagueFolder, teamFolder) {
        const leagueTeams = simulationTeamsByLeague.get(leagueFolder) || [];
        const target = `${teamFolder || ''}`.trim();
        if (!target) return null;
        return leagueTeams.find((team) => `${team?.folder || team?.name || ''}`.trim() === target) || null;
    }

    function getTeamsForLeague(leagueFolder) {
        return simulationTeamsByLeague.has(leagueFolder)
            ? (simulationTeamsByLeague.get(leagueFolder) || [])
            : [];
    }

    function getEffectiveSimulationHomeLeague() {
        return simulationCrossLeagueEnabled ? currentSimulationHomeLeague : currentSimulationLeague;
    }

    function getEffectiveSimulationAwayLeague() {
        return simulationCrossLeagueEnabled ? currentSimulationAwayLeague : currentSimulationLeague;
    }

    function getSimulationSelectionState() {
        return {
            homeLeague: getEffectiveSimulationHomeLeague(),
            awayLeague: getEffectiveSimulationAwayLeague(),
            homeTeam: simTeam1Select?.value || '',
            awayTeam: simTeam2Select?.value || '',
        };
    }

    function fillSimulationLeagueSelect(select) {
        if (!select) return;
        const placeholderOption = buildPlaceholderOption(select, 'Select League');
        select.innerHTML = '';
        select.add(placeholderOption);
        simulationLeagues.forEach((league) => {
            select.add(new Option(league.name, league.folder));
        });
    }

    function applyCrossLeagueModeUI() {
        if (simSingleLeagueGroup) {
            simSingleLeagueGroup.classList.toggle('hidden', simulationCrossLeagueEnabled);
        }
        if (simHomeLeagueGroup) {
            simHomeLeagueGroup.classList.toggle('hidden', !simulationCrossLeagueEnabled);
        }
        if (simAwayLeagueGroup) {
            simAwayLeagueGroup.classList.toggle('hidden', !simulationCrossLeagueEnabled);
        }
        if (simLeagueSelect) {
            simLeagueSelect.disabled = simulationCrossLeagueEnabled;
        }
        if (simCrossLeagueToggle) {
            simCrossLeagueToggle.checked = simulationCrossLeagueEnabled;
        }
    }

    function populateSimulationLeagueSelects() {
        fillSimulationLeagueSelect(simLeagueSelect);
        fillSimulationLeagueSelect(simTeam1LeagueSelect);
        fillSimulationLeagueSelect(simTeam2LeagueSelect);

        if (simulationTeamsByLeague.has(currentSimulationLeague) && simLeagueSelect) {
            simLeagueSelect.value = currentSimulationLeague;
        } else {
            currentSimulationLeague = '';
        }

        if (simulationTeamsByLeague.has(currentSimulationHomeLeague) && simTeam1LeagueSelect) {
            simTeam1LeagueSelect.value = currentSimulationHomeLeague;
        } else {
            currentSimulationHomeLeague = '';
        }

        if (simulationTeamsByLeague.has(currentSimulationAwayLeague) && simTeam2LeagueSelect) {
            simTeam2LeagueSelect.value = currentSimulationAwayLeague;
        } else {
            currentSimulationAwayLeague = '';
        }

        if (!simulationCrossLeagueEnabled && currentSimulationLeague) {
            currentSimulationHomeLeague = currentSimulationLeague;
            currentSimulationAwayLeague = currentSimulationLeague;
            if (simTeam1LeagueSelect) simTeam1LeagueSelect.value = currentSimulationHomeLeague;
            if (simTeam2LeagueSelect) simTeam2LeagueSelect.value = currentSimulationAwayLeague;
        }

        applyCrossLeagueModeUI();
    }

    function populateSimulationTeamSelectors() {
        if (!simTeam1Select || !simTeam2Select) return;

        const homeLeague = getEffectiveSimulationHomeLeague();
        const awayLeague = getEffectiveSimulationAwayLeague();
        const homeTeams = getTeamsForLeague(homeLeague);
        const awayTeams = getTeamsForLeague(awayLeague);
        const previousHome = simTeam1Select.value;
        const previousAway = simTeam2Select.value;

        const fillTeamSelect = (select, teams, league) => {
            const placeholderOption = buildPlaceholderOption(select, 'Select...');
            select.innerHTML = '';
            select.add(placeholderOption);
            teams.forEach((team) => {
                const teamFolder = `${team?.folder || team?.name || ''}`.trim();
                if (!teamFolder) return;
                const teamLabel = `${team?.name || teamFolder}`.trim();
                select.add(new Option(teamLabel, teamFolder));
            });
            select.disabled = !league || teams.length === 0;
        };

        fillTeamSelect(simTeam1Select, homeTeams, homeLeague);
        fillTeamSelect(simTeam2Select, awayTeams, awayLeague);

        if (homeTeams.some(team => `${team?.folder || team?.name || ''}` === previousHome)) {
            simTeam1Select.value = previousHome;
        }
        if (awayTeams.some(team => `${team?.folder || team?.name || ''}` === previousAway)) {
            simTeam2Select.value = previousAway;
        }

        if (!homeLeague || !awayLeague) {
            applySliderValue(team1AdjSlider, team1AdjValue, 0);
            applySliderValue(team2AdjSlider, team2AdjValue, 0);
            if (typeof hidePitchView === 'function') hidePitchView();
            lastSimTeam1 = '';
            lastSimTeam2 = '';
        }
    }

    async function loadSimulationOptions(forceRefresh = false) {
        const query = forceRefresh ? `?t=${Date.now()}` : '';
        const response = await fetch(`/api/simulation-options${query}`);
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`simulation options request failed (${response.status}): ${errorText}`);
        }

        const payload = await response.json();
        const leagues = Array.isArray(payload?.leagues) ? payload.leagues : [];
        simulationLeagues = leagues.map((league) => ({
            name: `${league?.name || league?.folder || ''}`.trim(),
            folder: `${league?.folder || league?.name || ''}`.trim(),
            teams: Array.isArray(league?.teams) ? league.teams : [],
        })).filter(league => league.name && league.folder);

        simulationTeamsByLeague = new Map(
            simulationLeagues.map(league => [league.folder, league.teams])
        );
    }

    async function ensureSimulationSelectorsPopulated(forceRefresh = false) {
        if (!simLeagueSelect || !simTeam1Select || !simTeam2Select) return;
        const hasLeagueOptions = simulationLeagues.length > 0 && simLeagueSelect.options.length > 1;
        if (!forceRefresh && hasLeagueOptions) return;

        try {
            await loadSimulationOptions(forceRefresh);
        } catch (error) {
            console.warn('Using fallback simulation league options:', error.message);
            simulationLeagues = [{
                name: 'Turkish Super League',
                folder: 'Turkish Super League',
                teams: teamData.map(team => ({
                    name: team.name,
                    folder: team.name,
                })),
            }];
            simulationTeamsByLeague = new Map([
                ['Turkish Super League', simulationLeagues[0].teams]
            ]);
        }

        const defaultLeague = simulationLeagues[0]?.folder || '';
        if (!currentSimulationLeague) currentSimulationLeague = defaultLeague;
        if (!currentSimulationHomeLeague) currentSimulationHomeLeague = currentSimulationLeague || defaultLeague;
        if (!currentSimulationAwayLeague) currentSimulationAwayLeague = currentSimulationLeague || defaultLeague;
        simulationCrossLeagueEnabled = Boolean(simCrossLeagueToggle?.checked);
        if (!simulationCrossLeagueEnabled) {
            currentSimulationHomeLeague = currentSimulationLeague;
            currentSimulationAwayLeague = currentSimulationLeague;
        }
        populateSimulationLeagueSelects();
        populateSimulationTeamSelectors();
    }

    function clearDrawingBoardPanel(panelEl, nameEl, badgeEl, playersGroupId, fallbackBadge = '🏟️') {
        if (panelEl) panelEl.classList.add('hidden');
        if (nameEl) nameEl.textContent = '-';
        if (badgeEl) badgeEl.textContent = fallbackBadge;
        const playersEl = document.getElementById(playersGroupId);
        if (playersEl) playersEl.innerHTML = '';
    }

    function renderDrawingBoardPanel(panelEl, nameEl, badgeEl, playersGroupId, teamData, side = 'home') {
        if (!teamData) {
            clearDrawingBoardPanel(
                panelEl,
                nameEl,
                badgeEl,
                playersGroupId,
                side === 'home' ? '🏠' : '✈️'
            );
            return;
        }

        if (panelEl) panelEl.classList.remove('hidden');
        if (nameEl) nameEl.textContent = teamData.name || '-';
        if (badgeEl) {
            badgeEl.innerHTML = `<img src="/logos/${teamData.name}.png" alt="${teamData.name}" class="pitch-team-logo" onerror="this.style.display='none'">`;
        }

        const formation = getSafeFormation(teamData.formation);
        const positions = typeof getFormationPositions === 'function' ? getFormationPositions(formation) : [];
        if (typeof renderTeamPlayers === 'function' && positions.length > 0) {
            renderTeamPlayers(
                playersGroupId,
                positions,
                Array.isArray(teamData.players) ? teamData.players : [],
                side,
                side === 'home' ? '#3b82f6' : '#f43f5e'
            );
        }
    }

    function populateDrawingBoardLeagueSelect() {
        if (!dbLeagueSelect) return;

        fillSimulationLeagueSelect(dbLeagueSelect);
        const preferredLeague = drawingBoardLeague || currentSimulationLeague || simulationLeagues[0]?.folder || '';
        if (simulationTeamsByLeague.has(preferredLeague)) {
            drawingBoardLeague = preferredLeague;
            dbLeagueSelect.value = preferredLeague;
        } else {
            drawingBoardLeague = '';
        }
    }

    function populateDrawingBoardTeamSelects() {
        if (!dbTeam1Select || !dbTeam2Select) return;
        const teams = getTeamsForLeague(drawingBoardLeague);
        const prevTeam1 = dbTeam1Select.value;
        const prevTeam2 = dbTeam2Select.value;

        const fillTeamSelect = (select) => {
            const placeholderOption = buildPlaceholderOption(select, 'Select...');
            select.innerHTML = '';
            select.add(placeholderOption);
            teams.forEach((team) => {
                const teamFolder = `${team?.folder || team?.name || ''}`.trim();
                if (!teamFolder) return;
                const teamLabel = `${team?.name || teamFolder}`.trim();
                select.add(new Option(teamLabel, teamFolder));
            });
            select.disabled = !drawingBoardLeague || teams.length === 0;
        };

        fillTeamSelect(dbTeam1Select);
        fillTeamSelect(dbTeam2Select);

        if (teams.some(team => `${team?.folder || team?.name || ''}` === prevTeam1)) {
            dbTeam1Select.value = prevTeam1;
        } else {
            drawingBoardLineupTeam1 = null;
            drawingBoardLastTeam1 = '';
        }

        if (teams.some(team => `${team?.folder || team?.name || ''}` === prevTeam2)) {
            dbTeam2Select.value = prevTeam2;
        } else {
            drawingBoardLineupTeam2 = null;
            drawingBoardLastTeam2 = '';
        }
    }

    function renderDrawingBoardFromCache() {
        if (dbTeam1FormationSelect && drawingBoardLineupTeam1) {
            drawingBoardLineupTeam1.formation = getSafeFormation(dbTeam1FormationSelect.value || drawingBoardLineupTeam1.formation);
            dbTeam1FormationSelect.value = drawingBoardLineupTeam1.formation;
        }
        if (dbTeam2FormationSelect && drawingBoardLineupTeam2) {
            drawingBoardLineupTeam2.formation = getSafeFormation(dbTeam2FormationSelect.value || drawingBoardLineupTeam2.formation);
            dbTeam2FormationSelect.value = drawingBoardLineupTeam2.formation;
        }

        renderDrawingBoardPanel(dbTeam1Panel, dbTeam1Name, dbTeam1Badge, 'db-team1-players', drawingBoardLineupTeam1, 'home');
        renderDrawingBoardPanel(dbTeam2Panel, dbTeam2Name, dbTeam2Badge, 'db-team2-players', drawingBoardLineupTeam2, 'away');
    }

    async function syncDrawingBoardPitches() {
        if (!dbLeagueSelect || !dbTeam1Select || !dbTeam2Select) return;

        const canRenderPitch = await ensureFormationHelpers();
        if (!canRenderPitch) return;

        const league = drawingBoardLeague;
        const team1 = dbTeam1Select.value || '';
        const team2 = dbTeam2Select.value || '';
        const token = ++drawingBoardSyncToken;

        if (!league) {
            drawingBoardLineupTeam1 = null;
            drawingBoardLineupTeam2 = null;
            renderDrawingBoardFromCache();
            return;
        }

        const team1Meta = getSimulationTeamMeta(league, team1);
        const team2Meta = getSimulationTeamMeta(league, team2);

        const [team1Data, team2Data] = await Promise.all([
            team1
                ? getTeamLatestLineup(team1, league, team1Meta?.lineup_csv_path || '').catch((error) => {
                    console.error('Drawing Board team 1 lineup error:', error);
                    return null;
                })
                : Promise.resolve(null),
            team2
                ? getTeamLatestLineup(team2, league, team2Meta?.lineup_csv_path || '').catch((error) => {
                    console.error('Drawing Board team 2 lineup error:', error);
                    return null;
                })
                : Promise.resolve(null),
        ]);

        const stillLatest =
            token === drawingBoardSyncToken &&
            drawingBoardLeague === league &&
            (dbTeam1Select?.value || '') === team1 &&
            (dbTeam2Select?.value || '') === team2;
        if (!stillLatest) return;

        drawingBoardLineupTeam1 = team1Data;
        drawingBoardLineupTeam2 = team2Data;

        if (drawingBoardLineupTeam1) {
            if (team1 !== drawingBoardLastTeam1 || !dbTeam1FormationSelect?.value) {
                applyDefaultFormation(dbTeam1FormationSelect, drawingBoardLineupTeam1.formation);
            }
            drawingBoardLineupTeam1.formation = getSafeFormation(dbTeam1FormationSelect?.value || drawingBoardLineupTeam1.formation);
        }

        if (drawingBoardLineupTeam2) {
            if (team2 !== drawingBoardLastTeam2 || !dbTeam2FormationSelect?.value) {
                applyDefaultFormation(dbTeam2FormationSelect, drawingBoardLineupTeam2.formation);
            }
            drawingBoardLineupTeam2.formation = getSafeFormation(dbTeam2FormationSelect?.value || drawingBoardLineupTeam2.formation);
        }

        drawingBoardLastTeam1 = team1;
        drawingBoardLastTeam2 = team2;
        renderDrawingBoardFromCache();
    }

    function wireDrawingBoardSlider(slider, valueEl) {
        if (!slider || !valueEl) return;
        applySliderValue(slider, valueEl, slider.value);
        slider.addEventListener('input', (e) => {
            applySliderValue(slider, valueEl, e.target.value);
        });
    }

    function initDrawingBoardTab() {
        if (!drawingBoardTab) return;

        if (!drawingBoardInitialized) {
            if (dbLeagueSelect) {
                dbLeagueSelect.addEventListener('change', async (e) => {
                    drawingBoardLeague = `${e.target?.value || ''}`.trim();
                    populateDrawingBoardTeamSelects();
                    await syncDrawingBoardPitches();
                });
            }

            if (dbTeam1Select) {
                dbTeam1Select.addEventListener('change', async () => {
                    await syncDrawingBoardPitches();
                });
            }

            if (dbTeam2Select) {
                dbTeam2Select.addEventListener('change', async () => {
                    await syncDrawingBoardPitches();
                });
            }

            if (dbTeam1FormationSelect) {
                dbTeam1FormationSelect.addEventListener('change', renderDrawingBoardFromCache);
            }
            if (dbTeam2FormationSelect) {
                dbTeam2FormationSelect.addEventListener('change', renderDrawingBoardFromCache);
            }

            wireDrawingBoardSlider(dbTeam1Attack, dbTeam1AttackValue);
            wireDrawingBoardSlider(dbTeam1Midfield, dbTeam1MidfieldValue);
            wireDrawingBoardSlider(dbTeam1Defense, dbTeam1DefenseValue);
            wireDrawingBoardSlider(dbTeam1Goalkeeper, dbTeam1GoalkeeperValue);
            wireDrawingBoardSlider(dbTeam2Attack, dbTeam2AttackValue);
            wireDrawingBoardSlider(dbTeam2Midfield, dbTeam2MidfieldValue);
            wireDrawingBoardSlider(dbTeam2Defense, dbTeam2DefenseValue);
            wireDrawingBoardSlider(dbTeam2Goalkeeper, dbTeam2GoalkeeperValue);

            drawingBoardInitialized = true;
        }

        tabBtns.forEach((btn) => {
            if (btn.getAttribute('data-tab') === 'tab-drawing-board') {
                btn.addEventListener('click', async () => {
                    await ensureSimulationSelectorsPopulated(false);
                    drawingBoardLeague = drawingBoardLeague || currentSimulationLeague || simulationLeagues[0]?.folder || '';
                    populateDrawingBoardLeagueSelect();
                    populateDrawingBoardTeamSelects();
                    await syncDrawingBoardPitches();
                });
            }
        });
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

                if (targetId === 'tab-world-cup-bracket') {
                    ensureWorldCupBracketLoaded();
                }

                queueLiquidGlassUpdate();
            });
        });
    }

    function ensureWorldCupBracketLoaded() {
        if (!worldCupBracketFrame || !worldCupBracketStatus || worldCupBracketLoaded) {
            return;
        }

        const src = worldCupBracketFrame.dataset.src;
        if (!src) {
            return;
        }

        worldCupBracketLoaded = true;
        worldCupBracketStatus.classList.remove('hidden');

        worldCupBracketFrame.addEventListener('load', () => {
            worldCupBracketStatus.classList.add('hidden');
        }, { once: true });

        worldCupBracketFrame.addEventListener('error', () => {
            worldCupBracketStatus.textContent = translations[currentLang]?.world_cup_bracket_error || 'Bracket failed to load. Open the full page instead.';
            worldCupBracketStatus.classList.remove('hidden');
        }, { once: true });

        worldCupBracketFrame.src = src;
    }

    // --- Event Listeners (Comparison) ---
    team1Select.addEventListener('change', async (e) => {
        await loadLiveAnalysisData(true);
        selectedTeam1 = teamData.find(t => t.name === e.target.value);
        if (selectedTeam2?.name) {
            selectedTeam2 = teamData.find(t => t.name === selectedTeam2.name) || selectedTeam2;
        }
        updateComparisonInterface();
    });

    team2Select.addEventListener('change', async (e) => {
        await loadLiveAnalysisData(true);
        selectedTeam2 = teamData.find(t => t.name === e.target.value);
        if (selectedTeam1?.name) {
            selectedTeam1 = teamData.find(t => t.name === selectedTeam1.name) || selectedTeam1;
        }
        updateComparisonInterface();
    });

    // --- Slider Event Listeners ---

    function formatSliderAdjustment(value) {
        const num = Number(value);
        if (!Number.isFinite(num)) return '0';
        const rounded = Math.round(num * 10) / 10;
        const formatted = Number.isInteger(rounded) ? `${rounded}` : rounded.toFixed(1);
        return rounded > 0 ? `+${formatted}` : formatted;
    }

    function clampSliderValue(slider, value) {
        const num = Number(value);
        const min = Number(slider?.min ?? -10);
        const max = Number(slider?.max ?? 10);
        if (!Number.isFinite(num)) return 0;
        return Math.min(max, Math.max(min, num));
    }

    function applySliderValue(slider, valueLabel, value) {
        if (!slider || !valueLabel) return;
        const clamped = clampSliderValue(slider, value);
        slider.value = String(clamped);
        valueLabel.textContent = formatSliderAdjustment(clamped);
    }

    function getNumericSliderValue(slider) {
        const value = Number(slider?.value ?? 0);
        return Number.isFinite(value) ? value : 0;
    }

    function applyDetailedAdjustmentValues(homeValue, awayValue) {
        simTeam1DetailedSliders.forEach((slider, index) => {
            applySliderValue(slider, simTeam1DetailedValues[index], homeValue);
        });
        simTeam2DetailedSliders.forEach((slider, index) => {
            applySliderValue(slider, simTeam2DetailedValues[index], awayValue);
        });
    }

    function getDetailedTeamAverage(sliders) {
        const values = sliders.map(getNumericSliderValue);
        if (values.length === 0) return 0;
        const total = values.reduce((sum, value) => sum + value, 0);
        return Number((total / values.length).toFixed(3));
    }

    function getSimulationAdjustmentValues() {
        if (simulationAdjustmentMode === 'advanced') {
            return {
                team1: getDetailedTeamAverage(simTeam1DetailedSliders),
                team2: getDetailedTeamAverage(simTeam2DetailedSliders),
            };
        }
        return {
            team1: getNumericSliderValue(team1AdjSlider),
            team2: getNumericSliderValue(team2AdjSlider),
        };
    }

    function areDetailedSlidersPristine() {
        return [...simTeam1DetailedSliders, ...simTeam2DetailedSliders]
            .every((slider) => getNumericSliderValue(slider) === 0);
    }

    function applySimulationModeUI() {
        if (simEasyAdjustments) {
            simEasyAdjustments.classList.toggle('hidden', simulationAdjustmentMode !== 'easy');
        }
        if (simAdvancedAdjustments) {
            simAdvancedAdjustments.classList.toggle('hidden', simulationAdjustmentMode !== 'advanced');
        }
        simModeButtons.forEach((button) => {
            const isActive = button.getAttribute('data-sim-mode') === simulationAdjustmentMode;
            button.classList.toggle('active', isActive);
            button.setAttribute('aria-pressed', isActive ? 'true' : 'false');
        });
    }

    function setSimulationAdjustmentMode(mode, { syncFromEasy = true } = {}) {
        const nextMode = mode === 'advanced' ? 'advanced' : 'easy';
        const previousMode = simulationAdjustmentMode;
        simulationAdjustmentMode = nextMode;

        if (
            nextMode === 'advanced' &&
            previousMode !== 'advanced' &&
            syncFromEasy &&
            areDetailedSlidersPristine()
        ) {
            applyDetailedAdjustmentValues(
                getNumericSliderValue(team1AdjSlider),
                getNumericSliderValue(team2AdjSlider)
            );
        }

        applySimulationModeUI();
    }

    function wireDetailedSlider(slider, valueEl) {
        if (!slider || !valueEl) return;
        applySliderValue(slider, valueEl, slider.value);
        slider.addEventListener('input', (e) => {
            applySliderValue(slider, valueEl, e.target.value);
        });
    }

    async function fetchPairHmmAdjustments(homeTeam, awayTeam, league) {
        const home = `${homeTeam || ''}`.trim();
        const away = `${awayTeam || ''}`.trim();
        if (!home && !away) {
            return { homeAdjustment: 0, awayAdjustment: 0 };
        }

        const params = new URLSearchParams();
        if (home) params.set('home_team', home);
        if (away) params.set('away_team', away);
        if (league) params.set('league', league);

        const response = await fetch(`/api/hmm-adjustments?${params.toString()}`);
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HMM adjustments fetch failed (${response.status}): ${errorText}`);
        }

        const payload = await response.json();
        const homeAdj = Number(payload?.home_hmm_adjustment);
        const awayAdj = Number(payload?.away_hmm_adjustment);
        return {
            homeAdjustment: Number.isFinite(homeAdj) ? homeAdj : 0,
            awayAdjustment: Number.isFinite(awayAdj) ? awayAdj : 0,
        };
    }

    async function fetchSingleHmmAdjustment(team, league) {
        const selectedTeam = `${team || ''}`.trim();
        const selectedLeague = `${league || ''}`.trim();
        if (!selectedTeam || !selectedLeague) return 0;

        const params = new URLSearchParams();
        params.set('team', selectedTeam);
        params.set('league', selectedLeague);
        const response = await fetch(`/api/hmm-adjustment?${params.toString()}`);
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HMM adjustment fetch failed (${response.status}): ${errorText}`);
        }
        const payload = await response.json();
        const adjustment = Number(payload?.hmm_adjustment);
        return Number.isFinite(adjustment) ? adjustment : 0;
    }

    async function updateSlidersFromHmm(homeTeam, awayTeam, homeLeague, awayLeague) {
        const token = ++hmmSyncToken;
        const selectedHomeTeam = `${homeTeam || ''}`.trim();
        const selectedAwayTeam = `${awayTeam || ''}`.trim();
        const selectedHomeLeague = `${homeLeague || ''}`.trim();
        const selectedAwayLeague = `${awayLeague || ''}`.trim();

        try {
            let homeAdjustment = 0;
            let awayAdjustment = 0;

            if (selectedHomeLeague && selectedHomeLeague === selectedAwayLeague) {
                const adjustments = await fetchPairHmmAdjustments(
                    selectedHomeTeam,
                    selectedAwayTeam,
                    selectedHomeLeague
                );
                homeAdjustment = selectedHomeTeam ? adjustments.homeAdjustment : 0;
                awayAdjustment = selectedAwayTeam ? adjustments.awayAdjustment : 0;
            } else {
                const [homeValue, awayValue] = await Promise.all([
                    fetchSingleHmmAdjustment(selectedHomeTeam, selectedHomeLeague),
                    fetchSingleHmmAdjustment(selectedAwayTeam, selectedAwayLeague),
                ]);
                homeAdjustment = selectedHomeTeam ? homeValue : 0;
                awayAdjustment = selectedAwayTeam ? awayValue : 0;
            }

            const stillLatest =
                token === hmmSyncToken &&
                (simTeam1Select?.value || '') === selectedHomeTeam &&
                (simTeam2Select?.value || '') === selectedAwayTeam &&
                getEffectiveSimulationHomeLeague() === selectedHomeLeague &&
                getEffectiveSimulationAwayLeague() === selectedAwayLeague;
            if (!stillLatest) return;

            applySliderValue(team1AdjSlider, team1AdjValue, homeAdjustment);
            applySliderValue(team2AdjSlider, team2AdjValue, awayAdjustment);
            if (simulationAdjustmentMode === 'advanced') {
                applyDetailedAdjustmentValues(homeAdjustment, awayAdjustment);
            }
        } catch (error) {
            console.warn(`Failed to load HMM adjustments for ${selectedHomeTeam} vs ${selectedAwayTeam}:`, error.message);
            const stillLatest =
                token === hmmSyncToken &&
                (simTeam1Select?.value || '') === selectedHomeTeam &&
                (simTeam2Select?.value || '') === selectedAwayTeam &&
                getEffectiveSimulationHomeLeague() === selectedHomeLeague &&
                getEffectiveSimulationAwayLeague() === selectedAwayLeague;
            if (!stillLatest) return;

            applySliderValue(team1AdjSlider, team1AdjValue, 0);
            applySliderValue(team2AdjSlider, team2AdjValue, 0);
            if (simulationAdjustmentMode === 'advanced') {
                applyDetailedAdjustmentValues(0, 0);
            }
        }
    }

    async function ensureFormationHelpers() {
        const helpersPresent = typeof getTeamLatestLineup === 'function' && typeof renderPitchView === 'function';
        if (helpersPresent) {
            formationHelpersReady = true;
            return true;
        }
        if (formationHelpersReady) return true;
        if (!formationHelpersLoadPromise) {
            formationHelpersLoadPromise = new Promise((resolve) => {
                const script = document.createElement('script');
                script.src = 'formation.js?v=8';
                script.async = true;
                script.onload = () => resolve(true);
                script.onerror = () => resolve(false);
                document.head.appendChild(script);
            });
        }

        const loaded = await formationHelpersLoadPromise;
        formationHelpersLoadPromise = null;
        formationHelpersReady = loaded &&
            typeof getTeamLatestLineup === 'function' &&
            typeof renderPitchView === 'function';
        if (!formationHelpersReady) {
            console.warn('Formation helpers are unavailable. Pitch visualization disabled.');
        }
        return formationHelpersReady;
    }

    if (team1AdjSlider && team1AdjValue) {
        applySliderValue(team1AdjSlider, team1AdjValue, team1AdjSlider.value);
        team1AdjSlider.addEventListener('input', (e) => {
            applySliderValue(team1AdjSlider, team1AdjValue, e.target.value);
        });
    }

    if (team2AdjSlider && team2AdjValue) {
        applySliderValue(team2AdjSlider, team2AdjValue, team2AdjSlider.value);
        team2AdjSlider.addEventListener('input', (e) => {
            applySliderValue(team2AdjSlider, team2AdjValue, e.target.value);
        });
    }

    simTeam1DetailedSliders.forEach((slider, index) => {
        wireDetailedSlider(slider, simTeam1DetailedValues[index]);
    });
    simTeam2DetailedSliders.forEach((slider, index) => {
        wireDetailedSlider(slider, simTeam2DetailedValues[index]);
    });

    simModeButtons.forEach((button) => {
        button.addEventListener('click', () => {
            const selectedMode = button.getAttribute('data-sim-mode') || 'easy';
            setSimulationAdjustmentMode(selectedMode);
        });
    });
    setSimulationAdjustmentMode('easy', { syncFromEasy: false });

    // --- Pitch Visualization (Formation) ---
    function getSafeFormation(formation, fallback = '4-2-3-1') {
        if (!formation || typeof formation !== 'string') return fallback;
        const normalized = formation.trim();
        return SIM_FORMATIONS.includes(normalized) ? normalized : fallback;
    }

    function applyDefaultFormation(selectElement, formation) {
        if (!selectElement) return;
        const safeFormation = getSafeFormation(formation);
        const optionExists = Array.from(selectElement.options).some(opt => opt.value === safeFormation);
        if (optionExists) {
            selectElement.value = safeFormation;
        }
    }

    async function updatePitchVisualization() {
        const canRenderPitch = await ensureFormationHelpers();
        if (!canRenderPitch) return;

        const token = ++pitchUpdateToken;
        const selectedHomeLeague = getEffectiveSimulationHomeLeague();
        const selectedAwayLeague = getEffectiveSimulationAwayLeague();
        const selectedHomeTeam = simTeam1Select?.value || '';
        const selectedAwayTeam = simTeam2Select?.value || '';
        const homeTeamMeta = getSimulationTeamMeta(selectedHomeLeague, selectedHomeTeam);
        const awayTeamMeta = getSimulationTeamMeta(selectedAwayLeague, selectedAwayTeam);
        if (!selectedHomeLeague && !selectedAwayLeague) {
            if (typeof hidePitchView === 'function') hidePitchView();
            return;
        }

        // Fetch both teams in parallel and discard stale completions.
        const [homeResult, awayResult] = await Promise.all([
            selectedHomeTeam && selectedHomeLeague
                ? getTeamLatestLineup(selectedHomeTeam, selectedHomeLeague, homeTeamMeta?.lineup_csv_path || '').catch((error) => {
                    console.error('Error loading team 1:', error);
                    return null;
                })
                : Promise.resolve(null),
            selectedAwayTeam && selectedAwayLeague
                ? getTeamLatestLineup(selectedAwayTeam, selectedAwayLeague, awayTeamMeta?.lineup_csv_path || '').catch((error) => {
                    console.error('Error loading team 2:', error);
                    return null;
                })
                : Promise.resolve(null),
        ]);

        const stillLatest =
            token === pitchUpdateToken &&
            getEffectiveSimulationHomeLeague() === selectedHomeLeague &&
            getEffectiveSimulationAwayLeague() === selectedAwayLeague &&
            (simTeam1Select?.value || '') === selectedHomeTeam &&
            (simTeam2Select?.value || '') === selectedAwayTeam;
        if (!stillLatest) return;

        const team1Data = homeResult;
        const team2Data = awayResult;

        if (team1Data) {
            if (selectedHomeTeam !== lastSimTeam1 || !simTeam1FormationSelect?.value) {
                applyDefaultFormation(simTeam1FormationSelect, team1Data.formation);
            }
            team1Data.formation = getSafeFormation(simTeam1FormationSelect?.value || team1Data.formation);
        }

        if (team2Data) {
            if (selectedAwayTeam !== lastSimTeam2 || !simTeam2FormationSelect?.value) {
                applyDefaultFormation(simTeam2FormationSelect, team2Data.formation);
            }
            team2Data.formation = getSafeFormation(simTeam2FormationSelect?.value || team2Data.formation);
        }

        lastSimTeam1 = selectedHomeTeam;
        lastSimTeam2 = selectedAwayTeam;
        renderPitchView(team1Data, team2Data);
    }

    async function syncSimulationSelectionEffects(force = false) {
        const { homeLeague, awayLeague, homeTeam, awayTeam } = getSimulationSelectionState();
        const token = ++selectionSyncToken;

        if (!homeLeague && !awayLeague) {
            applySliderValue(team1AdjSlider, team1AdjValue, 0);
            applySliderValue(team2AdjSlider, team2AdjValue, 0);
            applyDetailedAdjustmentValues(0, 0);
            if (typeof hidePitchView === 'function') hidePitchView();
            return;
        }

        await Promise.allSettled([
            updatePitchVisualization(),
            updateSlidersFromHmm(homeTeam, awayTeam, homeLeague, awayLeague),
        ]);

        if (token !== selectionSyncToken) return;
    }

    if (simLeagueSelect) {
        simLeagueSelect.addEventListener('change', async (e) => {
            currentSimulationLeague = `${e.target?.value || ''}`.trim();
            if (!simulationCrossLeagueEnabled) {
                currentSimulationHomeLeague = currentSimulationLeague;
                currentSimulationAwayLeague = currentSimulationLeague;
            }
            populateSimulationTeamSelectors();
            await syncSimulationSelectionEffects(true);
        });
    }

    if (simCrossLeagueToggle) {
        simCrossLeagueToggle.addEventListener('change', async (e) => {
            simulationCrossLeagueEnabled = Boolean(e.target?.checked);
            if (simulationCrossLeagueEnabled) {
                const fallbackLeague = currentSimulationLeague || simulationLeagues[0]?.folder || '';
                currentSimulationHomeLeague = currentSimulationHomeLeague || simTeam1LeagueSelect?.value || fallbackLeague;
                currentSimulationAwayLeague = currentSimulationAwayLeague || simTeam2LeagueSelect?.value || fallbackLeague;
                if (simTeam1LeagueSelect && currentSimulationHomeLeague) simTeam1LeagueSelect.value = currentSimulationHomeLeague;
                if (simTeam2LeagueSelect && currentSimulationAwayLeague) simTeam2LeagueSelect.value = currentSimulationAwayLeague;
            } else {
                const singleLeague = `${currentSimulationHomeLeague || currentSimulationAwayLeague || simLeagueSelect?.value || currentSimulationLeague || simulationLeagues[0]?.folder || ''}`.trim();
                currentSimulationLeague = singleLeague;
                currentSimulationHomeLeague = singleLeague;
                currentSimulationAwayLeague = singleLeague;
                if (simLeagueSelect && singleLeague) simLeagueSelect.value = singleLeague;
            }
            applyCrossLeagueModeUI();
            populateSimulationTeamSelectors();
            await syncSimulationSelectionEffects(true);
        });
    }

    if (simTeam1LeagueSelect) {
        simTeam1LeagueSelect.addEventListener('change', async (e) => {
            currentSimulationHomeLeague = `${e.target?.value || ''}`.trim();
            if (!simulationCrossLeagueEnabled) {
                currentSimulationLeague = currentSimulationHomeLeague;
                currentSimulationAwayLeague = currentSimulationHomeLeague;
                if (simLeagueSelect) simLeagueSelect.value = currentSimulationLeague;
            }
            populateSimulationTeamSelectors();
            await syncSimulationSelectionEffects(true);
        });
    }

    if (simTeam2LeagueSelect) {
        simTeam2LeagueSelect.addEventListener('change', async (e) => {
            currentSimulationAwayLeague = `${e.target?.value || ''}`.trim();
            if (!simulationCrossLeagueEnabled) {
                currentSimulationLeague = currentSimulationAwayLeague;
                currentSimulationHomeLeague = currentSimulationAwayLeague;
                if (simLeagueSelect) simLeagueSelect.value = currentSimulationLeague;
            }
            populateSimulationTeamSelectors();
            await syncSimulationSelectionEffects(true);
        });
    }

    // Add change listeners to sim team selects
    if (simTeam1Select) {
        simTeam1Select.addEventListener('change', () => syncSimulationSelectionEffects(false));
    }
    if (simTeam2Select) {
        simTeam2Select.addEventListener('change', () => syncSimulationSelectionEffects(false));
    }
    if (simTeam1FormationSelect) {
        simTeam1FormationSelect.addEventListener('change', updatePitchVisualization);
    }
    if (simTeam2FormationSelect) {
        simTeam2FormationSelect.addEventListener('change', updatePitchVisualization);
    }

    tabBtns.forEach(btn => {
        if (btn.getAttribute('data-tab') === 'tab-simulation') {
            btn.addEventListener('click', async () => {
                await ensureSimulationSelectorsPopulated(false);
                await syncSimulationSelectionEffects(true);
            });
        }
    });

    // --- Event Listeners (Simulation) ---
    if (btnRunSim) {
        btnRunSim.addEventListener('click', async () => {
            const selectedHomeLeague = getEffectiveSimulationHomeLeague();
            const selectedAwayLeague = getEffectiveSimulationAwayLeague();
            const selectedLeague = selectedHomeLeague || selectedAwayLeague || currentSimulationLeague || simLeagueSelect?.value || '';
            const t1 = simTeam1Select.value;
            const t2 = simTeam2Select.value;
            // Combined script doesn't need type

            if (!selectedHomeLeague || !selectedAwayLeague) {
                alert("Please select league(s) first.");
                return;
            }

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
                const adjustmentValues = getSimulationAdjustmentValues();
                const team1Adj = adjustmentValues.team1;
                const team2Adj = adjustmentValues.team2;
                const team1Formation = getSafeFormation(simTeam1FormationSelect?.value || '');
                const team2Formation = getSafeFormation(simTeam2FormationSelect?.value || '');

                const response = await fetch('/api/simulate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        league: selectedLeague,
                        home_league: selectedHomeLeague,
                        away_league: selectedAwayLeague,
                        team1: t1,
                        team2: t2,
                        team1_formation: team1Formation,
                        team2_formation: team2Formation,
                        team1_adj: team1Adj,
                        team2_adj: team2Adj,
                        simulation_count: 60,
                        include_heatmaps: false,
                        include_images: false,
                        include_markov: false
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

                // Build scoreline panel with both perspectives.
                const top5HomePerspective = data.top5_scores_home_perspective || data.top5_scores || [];
                const top5AwayPerspective = data.top5_scores_away_perspective || [];
                const scorelinesPanelHtml = buildDualScorelinesPanel(
                    top5HomePerspective,
                    top5AwayPerspective,
                    t1,
                    t2
                );

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

                    const buildStateProfiles = (team) => renderStateProfilesList(team);

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

                // Build Heatmaps HTML
                let heatmapsHtml = '';
                const playerHeatmapUrl = data.player_heatmap_url || data.heatmaps?.player;
                const mainClusterHeatmapUrl = data.main_cluster_heatmap_url || data.heatmaps?.main_clusters;
                const stripClusterHeatmapUrl = data.strip_cluster_heatmap_url || data.heatmaps?.strip_clusters;
                if (playerHeatmapUrl || mainClusterHeatmapUrl || stripClusterHeatmapUrl) {
                    const cards = [];
                    if (playerHeatmapUrl) {
                        cards.push(`
                            <div class="heatmap-card">
                                <div class="heatmap-title">Player Ratings</div>
                                <img src="${playerHeatmapUrl}" alt="Player rating heatmap" class="heatmap-img">
                            </div>
                        `);
                    }
                    if (mainClusterHeatmapUrl) {
                        cards.push(`
                            <div class="heatmap-card">
                                <div class="heatmap-title">Main Clusters</div>
                                <img src="${mainClusterHeatmapUrl}" alt="Main cluster heatmap" class="heatmap-img">
                            </div>
                        `);
                    }
                    if (stripClusterHeatmapUrl) {
                        cards.push(`
                            <div class="heatmap-card">
                                <div class="heatmap-title">Strip Clusters</div>
                                <img src="${stripClusterHeatmapUrl}" alt="Strip cluster heatmap" class="heatmap-img">
                            </div>
                        `);
                    }
                    heatmapsHtml = `
                        <div class="insights-panel">
                            <h4><span class="icon">🗺️</span> Tactical Heatmaps</h4>
                            <div class="heatmaps-grid">
                                ${cards.join('')}
                            </div>
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
                            ${scorelinesPanelHtml}

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

                            ${heatmapsHtml}

                            <div class="sim-meta">
                                <div class="sim-meta-item">
                                    <span class="meta-label">Simulations</span>
                                    <span class="meta-value">${data.simulated_matches?.toLocaleString() || '450+'}</span>
                                </div>
                                ${data.adjustments ? `
                                <div class="sim-meta-item">
                                    <span class="meta-label">${t1} Adj.</span>
                                    <span class="meta-value">${formatSliderAdjustment(data.adjustments.team1)}%</span>
                                </div>
                                <div class="sim-meta-item">
                                    <span class="meta-label">${t2} Adj.</span>
                                    <span class="meta-value">${formatSliderAdjustment(data.adjustments.team2)}%</span>
                                </div>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                `;
                refreshLiquidGlassTargets();

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
                refreshLiquidGlassTargets();
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
            'Goals Scored': [...teamData].sort((a, b) => b.stats.avg_goals_scored - a.stats.avg_goals_scored).map(t => t.name),
            'Goals Conceded': [...teamData].sort((a, b) => a.stats.avg_goals_conceded - b.stats.avg_goals_conceded).map(t => t.name),
            'Win Rate': [...teamData].sort((a, b) => b.stats.win_rate - a.stats.win_rate).map(t => t.name),
            'Possession': [...teamData].sort((a, b) => b.stats.avg_possession - a.stats.avg_possession).map(t => t.name)
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

    // --- Deep Player Analysis Tab ---
    const playerLabChartInstances = new Map();

    const snapshotMetricConfigs = [
        { label: 'Form', source: 'summary', key: 'Rating' },
        { label: 'Scoring', source: 'detailed', key: 'Goals per game' },
        { label: 'Shooting', source: 'detailed', key: 'Shots on target per game' },
        { label: 'Creation', source: 'detailed', key: 'Key passes' },
        { label: 'Ball Wins', source: 'detailed', key: 'Interceptions' },
        { label: 'Discipline', source: 'detailed', key: 'Fouls per game', lowerIsBetter: true }
    ];

    const outputMetricConfigs = [
        { label: 'Goals', source: 'summary', key: 'Goals' },
        { label: 'Assists', source: 'summary', key: 'Assists' },
        { label: 'Apps', source: 'summary', key: 'Appearances' },
        { label: 'Minutes/90', source: 'summary', key: 'MinutesPlayed', transform: (v) => v / 90 },
        { label: 'xG', source: 'detailed', key: 'Expected goals (xG)' },
        { label: 'xA', source: 'detailed', key: 'Expected assists (xA)' }
    ];

    function initPlayerAnalysisTab() {
        if (!playerAnalysisTab) return;

        const playerAnalysisBtn = document.querySelector('.nav-btn[data-tab="tab-player-analysis"]');
        if (playerAnalysisBtn) {
            playerAnalysisBtn.addEventListener('click', async () => {
                if (!playerAnalysisLoaded) {
                    await loadPlayerAnalysisData();
                } else {
                    renderPlayerAnalysis();
                }
            });
        }

        if (paTeamFilter) {
            paTeamFilter.addEventListener('change', () => {
                populatePlayerSelectors();
                renderPlayerAnalysis();
            });
        }

        if (paPlayerA) {
            paPlayerA.addEventListener('change', () => {
                renderPlayerAnalysis();
            });
        }

        if (paEnableCompare) {
            paEnableCompare.addEventListener('change', () => {
                if (paPlayerB) {
                    paPlayerB.disabled = !paEnableCompare.checked;
                    if (!paEnableCompare.checked) {
                        paPlayerB.value = '';
                    }
                }
                renderPlayerAnalysis();
            });
        }

        if (paPlayerB) {
            paPlayerB.addEventListener('change', () => {
                renderPlayerAnalysis();
            });
        }
    }

    async function loadPlayerAnalysisData() {
        if (!paStatus) return;

        setPlayerAnalysisStatus('Loading player analysis data...');

        try {
            const response = await fetch('/api/player-analysis?limit=2');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            playerAnalysisData = await response.json();
            playerAnalysisLoaded = true;

            populateTeamFilter();
            populatePlayerSelectors();

            const playersCount = playerAnalysisData?.playerCount || 0;
            const teamsCount = playerAnalysisData?.teamCount || 0;
            setPlayerAnalysisStatus(`Loaded ${playersCount} players from ${teamsCount} teams. Select Player A to begin.`);

            if (paPlayerA && paPlayerA.options.length > 1) {
                paPlayerA.selectedIndex = 1;
                renderPlayerAnalysis();
            }
        } catch (error) {
            console.error('Failed to load player analysis:', error);
            setPlayerAnalysisStatus(`Failed to load player data: ${error.message}`, 'error');
        }
    }

    function setPlayerAnalysisStatus(message, type = 'info') {
        if (!paStatus) return;
        paStatus.textContent = message;
        paStatus.classList.remove('error');
        if (type === 'error') {
            paStatus.classList.add('error');
        }
    }

    function populateTeamFilter() {
        if (!paTeamFilter || !playerAnalysisData) return;

        const previous = paTeamFilter.value || 'all';
        paTeamFilter.innerHTML = '';

        const allOpt = new Option(translations[currentLang].pa_team_filter_all || 'All Teams', 'all');
        paTeamFilter.add(allOpt);

        (playerAnalysisData.teams || []).forEach(team => {
            const count = team.playerCount || 0;
            paTeamFilter.add(new Option(`${team.name} (${count})`, team.name));
        });

        const values = Array.from(paTeamFilter.options).map(opt => opt.value);
        paTeamFilter.value = values.includes(previous) ? previous : 'all';
    }

    function getFilteredPlayers() {
        if (!playerAnalysisData || !Array.isArray(playerAnalysisData.players)) return [];
        const selectedTeam = paTeamFilter?.value || 'all';
        const allPlayers = playerAnalysisData.players;

        if (selectedTeam === 'all') {
            return allPlayers;
        }
        return allPlayers.filter(player => player.team === selectedTeam);
    }

    function populatePlayerSelectors() {
        if (!paPlayerA || !paPlayerB) return;

        const players = getFilteredPlayers();
        const previousA = paPlayerA.value;
        const previousB = paPlayerB.value;

        paPlayerA.innerHTML = '';
        paPlayerB.innerHTML = '';

        const placeholder = translations[currentLang].pa_choose_player || 'Choose a player...';
        paPlayerA.add(new Option(placeholder, ''));
        paPlayerB.add(new Option(placeholder, ''));

        players.forEach(player => {
            const label = `${player.name} (${player.team})`;
            paPlayerA.add(new Option(label, player.id));
            paPlayerB.add(new Option(label, player.id));
        });

        paPlayerA.value = players.some(player => player.id === previousA) ? previousA : '';
        paPlayerB.value = players.some(player => player.id === previousB) ? previousB : '';
    }

    function getPlayerById(playerId) {
        if (!playerId || !playerAnalysisData || !Array.isArray(playerAnalysisData.players)) return null;
        return playerAnalysisData.players.find(player => player.id === playerId) || null;
    }

    function renderPlayerAnalysis() {
        if (!paContent || !paCards || !paCompare) return;
        destroyPlayerLabCharts();

        const playerA = getPlayerById(paPlayerA?.value);
        const compareEnabled = Boolean(paEnableCompare?.checked);
        const playerB = compareEnabled ? getPlayerById(paPlayerB?.value) : null;

        if (!playerA) {
            paContent.classList.add('hidden');
            setPlayerAnalysisStatus('Select Player A to view full profile, season summary, and detailed stats.');
            return;
        }

        paContent.classList.remove('hidden');
        const cardA = renderPlayerCard(playerA, 'A');
        const cardB = playerB ? renderPlayerCard(playerB, 'B') : '';
        paCards.classList.toggle('single', !playerB);
        paCards.innerHTML = cardA + cardB;
        renderPlayerCardCharts(playerA, 'A');
        if (playerB) {
            renderPlayerCardCharts(playerB, 'B');
        }

        if (compareEnabled && playerB) {
            paCompare.classList.remove('hidden');
            paCompare.innerHTML = renderComparisonPanel(playerA, playerB);
            renderComparisonCharts(playerA, playerB);
            setPlayerAnalysisStatus(`Comparing ${playerA.name} vs ${playerB.name}`);
        } else if (compareEnabled && !playerB) {
            paCompare.classList.add('hidden');
            paCompare.innerHTML = '';
            setPlayerAnalysisStatus(`Viewing ${playerA.name}. Select Player B to compare.`);
        } else {
            paCompare.classList.add('hidden');
            paCompare.innerHTML = '';
            setPlayerAnalysisStatus(`Viewing ${playerA.name}`);
        }
    }

    function renderPlayerCard(player, slotLabel) {
        const profile = player.profile || {};
        const summaryMetrics = player.seasonSummary?.metrics || {};
        const detailedMetrics = player.detailedStats?.metrics || {};
        const profileRow = [
            { label: 'Age', value: profile.Age },
            { label: 'Date of Birth', value: formatDateOfBirth(profile.DateOfBirth) },
            { label: 'Height', value: profile.Height_cm ? `${profile.Height_cm} cm` : null },
            { label: 'Preferred Foot', value: profile.PreferredFoot },
            { label: 'Shirt', value: profile.ShirtNumber },
            { label: 'Nationality', value: profile.Nationality }
        ];

        const kpis = [
            { label: 'Rating', value: summaryMetrics.Rating },
            { label: 'Goals', value: summaryMetrics.Goals },
            { label: 'Assists', value: summaryMetrics.Assists },
            { label: 'Apps', value: summaryMetrics.Appearances },
            { label: 'Minutes', value: summaryMetrics.MinutesPlayed }
        ];

        const kpiHtml = kpis.map(kpi => `
            <div class="pa-kpi">
                <span class="pa-kpi-label">${kpi.label}</span>
                <span class="pa-kpi-value">${formatValue(kpi.value)}</span>
            </div>
        `).join('');

        return `
            <article class="pa-player-card">
                <div class="pa-card-header">
                    <div>
                        <div class="pa-slot">Player ${slotLabel}</div>
                        <h3>${player.name}</h3>
                        <p class="pa-subtitle">${player.team}</p>
                    </div>
                    <div class="pa-chip">${formatValue(profile.Position) || '-'}</div>
                </div>

                <div class="pa-profile-row">
                    ${profileRow.map(item => `
                        <div class="pa-profile-pill">
                            <span class="pa-profile-label">${item.label}</span>
                            <span class="pa-profile-value">${formatValue(item.value)}</span>
                        </div>
                    `).join('')}
                </div>

                <div class="pa-position-strip">
                    <div class="pa-position-pitch">
                        ${renderPositionPitch(profile.Position)}
                    </div>
                </div>

                <div class="pa-kpi-strip">
                    ${kpiHtml}
                </div>

                <div class="pa-chart-grid">
                    <div class="pa-chart-card">
                        <h4>Rating Trend</h4>
                        <div class="pa-chart-wrap">
                            <canvas id="pa-trend-${slotLabel}"></canvas>
                        </div>
                    </div>
                    <div class="pa-chart-card">
                        <h4>Team Relative Snapshot</h4>
                        <div class="pa-chart-wrap">
                            <canvas id="pa-snapshot-${slotLabel}"></canvas>
                        </div>
                    </div>
                    <div class="pa-chart-card pa-chart-card-wide">
                        <h4>Season Output</h4>
                        <div class="pa-chart-wrap">
                            <canvas id="pa-output-${slotLabel}"></canvas>
                        </div>
                    </div>
                </div>

                <details class="pa-raw-details">
                    <summary>View Raw Data</summary>
                    <div class="pa-raw-grid">
                        <div class="pa-section">
                            <h4>Profile</h4>
                            ${renderKeyValueGrid({
            Age: profile.Age,
            DateOfBirth: profile.DateOfBirth,
            Height: profile.Height_cm ? `${profile.Height_cm} cm` : null,
            PreferredFoot: profile.PreferredFoot,
            Position: profile.Position,
            ShirtNumber: profile.ShirtNumber,
            Nationality: profile.Nationality
        })}
                        </div>

                        <div class="pa-section">
                            <h4>Season Summary</h4>
                            ${renderKeyValueGrid(summaryMetrics)}
                        </div>

                        <div class="pa-section">
                            <h4>Detailed Statistics</h4>
                            ${renderKeyValueGrid(detailedMetrics)}
                        </div>
                    </div>
                </details>
            </article>
        `;
    }

    function renderKeyValueGrid(metricsObj) {
        const entries = Object.entries(metricsObj || {})
            .filter(([, value]) => value !== null && value !== undefined && value !== '');

        if (!entries.length) {
            return '<p class="pa-empty">No data available.</p>';
        }

        const html = entries.map(([key, value]) => `
            <div class="pa-kv-item">
                <span class="pa-kv-key">${prettifyMetricKey(key)}</span>
                <span class="pa-kv-value">${formatValue(value)}</span>
            </div>
        `).join('');

        return `<div class="pa-kv-grid">${html}</div>`;
    }

    function renderComparisonPanel(playerA, playerB) {
        const callouts = buildComparisonCallouts(playerA, playerB).map(item => `
            <div class="pa-callout">
                <span class="pa-callout-metric">${item.metric}</span>
                <span class="pa-callout-winner">${item.winner}</span>
                <span class="pa-callout-values">${item.left} vs ${item.right}</span>
            </div>
        `).join('');

        return `
            <div class="pa-compare-panel">
                <h3>Head-to-Head Snapshot</h3>
                <p class="pa-subtitle">${playerA.name} vs ${playerB.name}</p>
                <div class="pa-callout-grid">${callouts || '<p class="pa-empty">No comparable callouts available.</p>'}</div>
                <div class="pa-compare-chart-grid">
                    <div class="pa-chart-card">
                        <h4>Relative Performance Radar</h4>
                        <div class="pa-chart-wrap">
                            <canvas id="pa-compare-radar"></canvas>
                        </div>
                    </div>
                    <div class="pa-chart-card">
                        <h4>Output Comparison</h4>
                        <div class="pa-chart-wrap">
                            <canvas id="pa-compare-output"></canvas>
                        </div>
                    </div>
                </div>
                <div class="pa-chart-card pa-chart-card-wide">
                    <h4>Monthly Rating Trend</h4>
                    <div class="pa-chart-wrap">
                        <canvas id="pa-compare-trend"></canvas>
                    </div>
                </div>
            </div>
        `;
    }

    function renderPlayerCardCharts(player, slotLabel) {
        renderPlayerTrendChart(player, `pa-trend-${slotLabel}`);
        renderPlayerSnapshotChart(player, `pa-snapshot-${slotLabel}`);
        renderPlayerOutputChart(player, `pa-output-${slotLabel}`);
    }

    function renderComparisonCharts(playerA, playerB) {
        renderCompareRadarChart(playerA, playerB, 'pa-compare-radar');
        renderCompareOutputChart(playerA, playerB, 'pa-compare-output');
        renderCompareTrendChart(playerA, playerB, 'pa-compare-trend');
    }

    function renderPlayerTrendChart(player, canvasId) {
        const series = getMonthlyRatingSeries(player);
        if (!series.labels.length) return;

        const overall = getMetricByConfig(player, { source: 'summary', key: 'Rating' });
        const datasets = [{
            label: `${player.name} Rating`,
            data: series.values,
            borderColor: '#38bdf8',
            backgroundColor: 'rgba(56, 189, 248, 0.2)',
            pointBackgroundColor: '#bae6fd',
            fill: true,
            tension: 0.35
        }];

        if (overall !== null) {
            datasets.push({
                label: 'Season Avg',
                data: series.values.map(() => overall),
                borderColor: 'rgba(248, 250, 252, 0.55)',
                borderDash: [6, 5],
                pointRadius: 0,
                fill: false,
                tension: 0
            });
        }

        createPlayerLabChart(canvasId, {
            type: 'line',
            data: {
                labels: series.labels,
                datasets: datasets
            },
            options: getPlayerLabChartOptions({
                yMin: 5,
                yMax: 10,
                showLegend: true
            })
        });
    }

    function renderPlayerSnapshotChart(player, canvasId) {
        const snapshot = buildSnapshotScores(player);
        if (!snapshot.labels.length) return;

        createPlayerLabChart(canvasId, {
            type: 'radar',
            data: {
                labels: snapshot.labels,
                datasets: [{
                    label: `${player.name} (Team Percentile)`,
                    data: snapshot.values,
                    backgroundColor: 'rgba(34, 211, 238, 0.22)',
                    borderColor: '#22d3ee',
                    pointBackgroundColor: '#67e8f9',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { color: '#e2e8f0' }
                    }
                },
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100,
                        grid: { color: 'rgba(148, 163, 184, 0.22)' },
                        angleLines: { color: 'rgba(148, 163, 184, 0.22)' },
                        pointLabels: { color: '#cbd5e1', font: { size: 11 } },
                        ticks: { color: '#94a3b8', backdropColor: 'transparent', stepSize: 20 }
                    }
                }
            }
        });
    }

    function renderPlayerOutputChart(player, canvasId) {
        const output = getOutputValues(player);
        if (!output.labels.length) return;

        createPlayerLabChart(canvasId, {
            type: 'bar',
            data: {
                labels: output.labels,
                datasets: [{
                    label: player.name,
                    data: output.values,
                    borderRadius: 8,
                    backgroundColor: [
                        '#22d3ee',
                        '#38bdf8',
                        '#0ea5e9',
                        '#3b82f6',
                        '#60a5fa',
                        '#93c5fd'
                    ]
                }]
            },
            options: getPlayerLabChartOptions({
                yMin: 0,
                showLegend: false
            })
        });
    }

    function renderCompareRadarChart(playerA, playerB, canvasId) {
        const a = buildSnapshotScores(playerA);
        const b = buildSnapshotScores(playerB);
        if (!a.labels.length || !b.labels.length) return;

        createPlayerLabChart(canvasId, {
            type: 'radar',
            data: {
                labels: a.labels,
                datasets: [
                    {
                        label: playerA.name,
                        data: a.values,
                        backgroundColor: 'rgba(56, 189, 248, 0.2)',
                        borderColor: '#38bdf8',
                        pointBackgroundColor: '#38bdf8',
                        borderWidth: 2
                    },
                    {
                        label: playerB.name,
                        data: b.values,
                        backgroundColor: 'rgba(244, 114, 182, 0.2)',
                        borderColor: '#f472b6',
                        pointBackgroundColor: '#f472b6',
                        borderWidth: 2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: '#e2e8f0' } }
                },
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100,
                        grid: { color: 'rgba(148, 163, 184, 0.22)' },
                        angleLines: { color: 'rgba(148, 163, 184, 0.22)' },
                        pointLabels: { color: '#cbd5e1', font: { size: 11 } },
                        ticks: { color: '#94a3b8', backdropColor: 'transparent', stepSize: 20 }
                    }
                }
            }
        });
    }

    function renderCompareOutputChart(playerA, playerB, canvasId) {
        const a = getOutputValues(playerA);
        const b = getOutputValues(playerB);
        if (!a.labels.length || !b.labels.length) return;

        createPlayerLabChart(canvasId, {
            type: 'bar',
            data: {
                labels: a.labels,
                datasets: [
                    {
                        label: playerA.name,
                        data: a.values,
                        backgroundColor: 'rgba(56, 189, 248, 0.78)',
                        borderRadius: 8
                    },
                    {
                        label: playerB.name,
                        data: b.values,
                        backgroundColor: 'rgba(244, 114, 182, 0.75)',
                        borderRadius: 8
                    }
                ]
            },
            options: getPlayerLabChartOptions({
                yMin: 0,
                showLegend: true
            })
        });
    }

    function renderCompareTrendChart(playerA, playerB, canvasId) {
        const a = getMonthlyRatingSeries(playerA);
        const b = getMonthlyRatingSeries(playerB);
        const labels = Array.from(new Set([...a.labels, ...b.labels])).sort();
        if (!labels.length) return;

        const toSeries = (series) => {
            const map = Object.fromEntries(series.labels.map((label, idx) => [label, series.values[idx]]));
            return labels.map(label => map[label] ?? null);
        };

        createPlayerLabChart(canvasId, {
            type: 'line',
            data: {
                labels: labels.map(formatMonthLabel),
                datasets: [
                    {
                        label: playerA.name,
                        data: toSeries(a),
                        borderColor: '#38bdf8',
                        backgroundColor: 'rgba(56, 189, 248, 0.15)',
                        pointBackgroundColor: '#bae6fd',
                        fill: false,
                        spanGaps: true,
                        tension: 0.3
                    },
                    {
                        label: playerB.name,
                        data: toSeries(b),
                        borderColor: '#f472b6',
                        backgroundColor: 'rgba(244, 114, 182, 0.15)',
                        pointBackgroundColor: '#fbcfe8',
                        fill: false,
                        spanGaps: true,
                        tension: 0.3
                    }
                ]
            },
            options: getPlayerLabChartOptions({
                yMin: 5,
                yMax: 10,
                showLegend: true
            })
        });
    }

    function createPlayerLabChart(canvasId, config) {
        const canvas = document.getElementById(canvasId);
        if (!canvas || typeof Chart === 'undefined') return;

        if (playerLabChartInstances.has(canvasId)) {
            playerLabChartInstances.get(canvasId).destroy();
            playerLabChartInstances.delete(canvasId);
        }

        const chart = new Chart(canvas, config);
        playerLabChartInstances.set(canvasId, chart);
    }

    function destroyPlayerLabCharts() {
        playerLabChartInstances.forEach(chart => chart.destroy());
        playerLabChartInstances.clear();
    }

    function getPlayerLabChartOptions({ yMin = undefined, yMax = undefined, showLegend = false }) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: showLegend,
                    labels: { color: '#e2e8f0' }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleColor: '#f8fafc',
                    bodyColor: '#cbd5e1',
                    borderColor: 'rgba(148, 163, 184, 0.3)',
                    borderWidth: 1
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(148, 163, 184, 0.12)' },
                    ticks: { color: '#cbd5e1' }
                },
                y: {
                    min: yMin,
                    max: yMax,
                    grid: { color: 'rgba(148, 163, 184, 0.12)' },
                    ticks: { color: '#cbd5e1' }
                }
            }
        };
    }

    function buildSnapshotScores(player) {
        const labels = [];
        const values = [];
        const peers = (playerAnalysisData?.players || []).filter(p => p.team === player.team);

        snapshotMetricConfigs.forEach(metric => {
            const ownValue = getMetricByConfig(player, metric);
            if (ownValue === null) return;

            const peerValues = peers
                .map(peer => getMetricByConfig(peer, metric))
                .filter(v => v !== null);

            let percentile = 50;
            if (peerValues.length) {
                const betterOrEqual = peerValues.filter(v => metric.lowerIsBetter ? v >= ownValue : v <= ownValue).length;
                percentile = Math.round((betterOrEqual / peerValues.length) * 100);
            }

            labels.push(metric.label);
            values.push(percentile);
        });

        return { labels, values };
    }

    function getOutputValues(player) {
        const labels = [];
        const values = [];

        outputMetricConfigs.forEach(metric => {
            let value = getMetricByConfig(player, metric);
            if (value === null) return;
            if (typeof metric.transform === 'function') {
                value = metric.transform(value);
            }
            if (!Number.isFinite(value)) return;

            labels.push(metric.label);
            values.push(Number(value.toFixed(2)));
        });

        return { labels, values };
    }

    function getMonthlyRatingSeries(player) {
        const monthly = player.seasonSummary?.monthlyRatings || {};
        const entries = Object.entries(monthly)
            .filter(([key, value]) => /^\d{4}-\d{2}$/.test(key) && toComparableNumber(value) !== null)
            .sort((a, b) => a[0].localeCompare(b[0]));

        return {
            labels: entries.map(([key]) => formatMonthLabel(key)),
            values: entries.map(([, value]) => toComparableNumber(value))
        };
    }

    function buildComparisonCallouts(playerA, playerB) {
        const calloutMetrics = [
            { metric: 'Rating', source: 'summary', key: 'Rating' },
            { metric: 'Goals', source: 'summary', key: 'Goals' },
            { metric: 'Assists', source: 'summary', key: 'Assists' },
            { metric: 'xG', source: 'detailed', key: 'Expected goals (xG)' }
        ];

        return calloutMetrics.map(metric => {
            const left = getMetricByConfig(playerA, metric);
            const right = getMetricByConfig(playerB, metric);
            if (left === null && right === null) return null;

            let winner = 'Even';
            if ((left ?? -Infinity) > (right ?? -Infinity)) winner = playerA.name;
            if ((right ?? -Infinity) > (left ?? -Infinity)) winner = playerB.name;

            return {
                metric: metric.metric,
                winner: winner,
                left: formatValue(left),
                right: formatValue(right)
            };
        }).filter(Boolean);
    }

    function getMetricByConfig(player, metric) {
        const source = metric.source === 'summary'
            ? (player.seasonSummary?.metrics || {})
            : (player.detailedStats?.metrics || {});
        const raw = source[metric.key];

        if (raw === null || raw === undefined || raw === '') return null;
        return toComparableNumber(raw, Boolean(metric.preferPercent));
    }

    function formatValue(value) {
        if (value === null || value === undefined || value === '') return '-';
        if (typeof value === 'number') {
            return Number.isInteger(value) ? `${value}` : value.toFixed(2).replace(/\.00$/, '');
        }
        return `${value}`;
    }

    function toComparableNumber(value, preferPercent = false) {
        if (value === null || value === undefined || value === '') return null;
        if (typeof value === 'number') return Number.isFinite(value) ? value : null;

        const str = `${value}`.replace(',', '.').trim();
        if (!str) return null;

        if (preferPercent) {
            const pct = extractPercentNumber(str);
            if (pct !== null) return pct;
        }

        const ratioMatch = str.match(/(-?\d+(?:\.\d+)?)\s*\/\s*(-?\d+(?:\.\d+)?)/);
        if (ratioMatch) {
            const numerator = parseFloat(ratioMatch[1]);
            const denominator = parseFloat(ratioMatch[2]);
            if (Number.isFinite(numerator) && Number.isFinite(denominator) && denominator !== 0) {
                return numerator / denominator;
            }
        }

        const numMatch = str.match(/-?\d+(?:\.\d+)?/);
        if (!numMatch) return null;

        const parsed = parseFloat(numMatch[0]);
        return Number.isFinite(parsed) ? parsed : null;
    }

    function extractPercentNumber(value) {
        const str = `${value}`;
        const match = str.match(/(-?\d+(?:\.\d+)?)\s*%/);
        if (!match) return null;
        const parsed = parseFloat(match[1]);
        return Number.isFinite(parsed) ? parsed : null;
    }

    function prettifyMetricKey(key) {
        if (!key) return '';
        return key
            .replace(/_/g, ' ')
            .replace(/\bcm\b/gi, 'cm')
            .trim();
    }

    function formatMonthLabel(key) {
        if (key === 'Last12Months') return 'Last 12M';
        return key;
    }

    function formatDateOfBirth(value) {
        if (!value) return null;
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return value;
        return date.toLocaleDateString('en-GB', {
            day: '2-digit',
            month: 'long',
            year: 'numeric'
        });
    }

    function renderPositionPitch(positionRaw) {
        const active = parsePositionTokens(positionRaw);
        const spots = [
            { key: 'st', label: 'ST' },
            { key: 'rw', label: 'RW' },
            { key: 'lw', label: 'LW' },
            { key: 'am', label: 'AM' },
            { key: 'cm', label: 'CM' },
            { key: 'dm', label: 'DM' },
            { key: 'rb', label: 'RB' },
            { key: 'cb', label: 'CB' },
            { key: 'lb', label: 'LB' },
            { key: 'gk', label: 'GK' }
        ];

        return `
            <div class="mini-pitch">
                <div class="mini-pitch-lines"></div>
                ${spots.map(spot => `
                    <div class="mini-pos mini-pos-${spot.key} ${active.has(spot.key) ? 'active' : ''}">${spot.label}</div>
                `).join('')}
            </div>
        `;
    }

    function parsePositionTokens(positionRaw) {
        const set = new Set();
        const raw = `${positionRaw || ''}`
            .toUpperCase()
            .replace(/\./g, '')
            .split(/[,/|]/)
            .map(token => token.trim())
            .filter(Boolean);

        raw.forEach(token => {
            if (['ST', 'CF', 'F', 'FW'].includes(token)) set.add('st');
            if (['RW', 'RM', 'RF'].includes(token)) set.add('rw');
            if (['LW', 'LM', 'LF'].includes(token)) set.add('lw');
            if (['AM', 'CAM', 'OMF', 'SS'].includes(token)) set.add('am');
            if (['CM', 'M', 'MC'].includes(token)) set.add('cm');
            if (['DM', 'CDM'].includes(token)) set.add('dm');
            if (['RB', 'RWB'].includes(token)) set.add('rb');
            if (['LB', 'LWB'].includes(token)) set.add('lb');
            if (['CB', 'SW', 'D'].includes(token)) set.add('cb');
            if (['GK'].includes(token)) set.add('gk');
        });

        if (!set.size) {
            set.add('cm');
        }
        return set;
    }

    // --- Upcoming Games Tab ---
    function updateRoundDisplay() {
        if (!roundDisplayText) return;
        roundDisplayText.textContent = `${translations[currentLang].round_label} ${currentRoundNum}`;
    }

    // Initialize Upcoming Games when tab is clicked
    tabBtns.forEach(btn => {
        if (btn.getAttribute('data-tab') === 'tab-recent-games') {
            btn.addEventListener('click', () => {
                if (!recentGamesInitialized) {
                    initRecentGamesTab();
                }
            });
        }
    });

    async function initRecentGamesTab() {
        try {
            // Load default/current round directly from API.
            await loadRoundMatches();

            // Set up round navigation
            prevRoundBtn.addEventListener('click', () => {
                if (currentRoundNum > MIN_ROUND_NUM) {
                    currentRoundNum--;
                    loadRoundMatches(currentRoundNum);
                }
            });

            nextRoundBtn.addEventListener('click', () => {
                if (currentRoundNum < MAX_ROUND_NUM) {
                    currentRoundNum++;
                    loadRoundMatches(currentRoundNum);
                }
            });

            recentGamesInitialized = true;

        } catch (error) {
            console.error('Error initializing Upcoming Games:', error);
            matchesContainer.innerHTML = `<div class="error">Error loading data: ${error.message}</div>`;
        }
    }

    async function loadRoundMatches(roundNum = null) {
        try {
            matchesContainer.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Loading matches...</p></div>';

            const requestUrl = Number.isInteger(roundNum)
                ? `/api/recent-games?round=${roundNum}`
                : '/api/recent-games';
            const response = await fetch(requestUrl);
            const data = await response.json();

            currentRoundNum = Math.min(
                MAX_ROUND_NUM,
                Math.max(MIN_ROUND_NUM, Number(data.round) || Number(roundNum) || MIN_ROUND_NUM)
            );
            updateRoundDisplay();
            renderMatches(data.matches);

        } catch (error) {
            console.error('Error loading matches:', error);
            matchesContainer.innerHTML = `<div class="error">Error: ${error.message}</div>`;
        }
    }

    function renderMatches(matches) {
        if (!matches || matches.length === 0) {
            matchesContainer.innerHTML = '<div class="no-matches">No matches found for this round.</div>';
            refreshLiquidGlassTargets();
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
        refreshLiquidGlassTargets();
    }

    function encodeAssetUrl(url) {
        if (!url || typeof url !== 'string') return '';
        const qIndex = url.indexOf('?');
        const pathPart = qIndex >= 0 ? url.slice(0, qIndex) : url;
        const queryPart = qIndex >= 0 ? url.slice(qIndex) : '';
        try {
            return encodeURI(pathPart) + queryPart;
        } catch (error) {
            return url;
        }
    }

    function formatSignedPercent(value) {
        const num = Number(value);
        if (!Number.isFinite(num)) return '0.0%';
        return `${num >= 0 ? '+' : ''}${num.toFixed(1)}%`;
    }

    function sanitizeScoreLabel(scoreText) {
        const score = `${scoreText || ''}`.trim();
        const match = score.match(/^(\d+)\s*-\s*(\d+)$/);
        if (!match) return '0-0';
        return `${match[1]}-${match[2]}`;
    }

    function renderScorelineRows(scores) {
        if (!Array.isArray(scores) || scores.length === 0) {
            return '<div class="scoreline-empty">No scoreline distribution available.</div>';
        }

        return scores.map(s => `
            <div class="scoreline-row">
                <span class="scoreline-label">${sanitizeScoreLabel(s?.score)}</span>
                <div class="scoreline-bar-wrapper">
                    <div class="scoreline-bar" style="width: ${Number.isFinite(Number(s?.percentage)) ? Number(s.percentage) : 0}%">
                        <span class="scoreline-pct">${Number.isFinite(Number(s?.percentage)) ? Number(s.percentage).toFixed(1) : '0.0'}%</span>
                    </div>
                </div>
            </div>
        `).join('');
    }

    function buildDualScorelinesPanel(homeScoresRaw, awayScoresRaw, homeTeamName, awayTeamName) {
        const homeScores = Array.isArray(homeScoresRaw) ? homeScoresRaw : [];
        if (homeScores.length === 0) return '';

        const awayScores = Array.isArray(awayScoresRaw) ? awayScoresRaw : [];

        return `
            <div class="insights-panel">
                <h4><span class="icon">📊</span> Most Likely Scorelines</h4>
                <div class="scoreline-perspective-grid">
                    <div class="scoreline-perspective-card">
                        <div class="scoreline-perspective-title">${homeTeamName} Perspective</div>
                        <div class="score-probabilities">
                            ${renderScorelineRows(homeScores)}
                        </div>
                    </div>
                    <div class="scoreline-perspective-card">
                        <div class="scoreline-perspective-title">${awayTeamName} Perspective</div>
                        <div class="score-probabilities">
                            ${renderScorelineRows(awayScores)}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    function toStateProfiles(rawProfiles) {
        if (Array.isArray(rawProfiles)) return rawProfiles;
        if (rawProfiles && typeof rawProfiles === 'object') {
            return Object.values(rawProfiles).filter(Boolean);
        }
        return [];
    }

    function toPercent(value) {
        const num = Number(value);
        return Number.isFinite(num) ? num.toFixed(1) : '0.0';
    }

    function renderStateProfilesList(team) {
        const profiles = toStateProfiles(team?.state_profiles);
        if (profiles.length === 0) {
            return `
                <div class="state-profile-empty">
                    No state-level breakdown available for this team in the current round data.
                </div>
            `;
        }

        return profiles.map(state => `
            <div class="state-profile-card">
                <div class="state-header">
                    <span class="state-label">${state?.label || 'State'}</span>
                    <span class="state-matches">${Number.isFinite(Number(state?.count)) ? Number(state.count) : 0} matches</span>
                </div>
                <div class="state-probs">
                    <div class="state-prob win">
                        <span class="prob-bar" style="width: ${toPercent(state?.win_prob)}%"></span>
                        <span class="prob-text">W ${toPercent(state?.win_prob)}%</span>
                    </div>
                    <div class="state-prob draw">
                        <span class="prob-bar" style="width: ${toPercent(state?.draw_prob)}%"></span>
                        <span class="prob-text">D ${toPercent(state?.draw_prob)}%</span>
                    </div>
                    <div class="state-prob loss">
                        <span class="prob-bar" style="width: ${toPercent(state?.loss_prob)}%"></span>
                        <span class="prob-text">L ${toPercent(state?.loss_prob)}%</span>
                    </div>
                </div>
            </div>
        `).join('');
    }

    function normalizeTeamKey(value) {
        return `${value || ''}`
            .trim()
            .toLowerCase()
            .replace(/ı/g, 'i')
            .replace(/İ/g, 'i')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .replace(/[^a-z0-9]/g, '');
    }

    function findTeamSnapshot(teamName) {
        if (!Array.isArray(teamData) || teamData.length === 0) return null;
        const targetKey = normalizeTeamKey(teamName);
        if (!targetKey) return null;

        const exact = teamData.find(team => normalizeTeamKey(team?.name) === targetKey);
        if (exact) return exact;

        return teamData.find(team => {
            const teamKey = normalizeTeamKey(team?.name);
            if (!teamKey) return false;
            return (
                teamKey.includes(targetKey) ||
                targetKey.includes(teamKey) ||
                teamKey.replace(/(fk|jk)$/, '') === targetKey.replace(/(fk|jk)$/, '')
            );
        }) || null;
    }

    function pointsFromResult(result) {
        const value = `${result || ''}`.trim().toUpperCase();
        if (value === 'W') return 3;
        if (value === 'D') return 1;
        return 0;
    }

    function getRecentFormPoints(teamSnapshot, windowSize = 5) {
        const history = Array.isArray(teamSnapshot?.match_history) ? teamSnapshot.match_history : [];
        if (history.length === 0) return null;
        const recent = history.slice(0, windowSize);
        const points = recent.reduce((sum, row) => sum + pointsFromResult(row?.result), 0);
        return {
            points,
            matches: recent.length,
            maxPoints: recent.length * 3,
        };
    }

    function formatPercent(value, decimals = 1) {
        const num = Number(value);
        if (!Number.isFinite(num)) return null;
        return `${(num * 100).toFixed(decimals)}%`;
    }

    function formatDecimal(value, decimals = 2) {
        const num = Number(value);
        if (!Number.isFinite(num)) return null;
        return num.toFixed(decimals);
    }

    function buildConfidenceDataEvidence(match, pred) {
        const homeSnapshot = findTeamSnapshot(match.home_team);
        const awaySnapshot = findTeamSnapshot(match.away_team);
        const evidenceParts = [];

        if (homeSnapshot?.stats && awaySnapshot?.stats) {
            const homeStats = homeSnapshot.stats;
            const awayStats = awaySnapshot.stats;
            const sampleSize = Math.min(
                Number(homeStats.total_games) || 0,
                Number(awayStats.total_games) || 0
            );
            const homeWinRate = formatPercent(homeStats.win_rate);
            const awayWinRate = formatPercent(awayStats.win_rate);
            const homeScored = formatDecimal(homeStats.avg_goals_scored);
            const homeConceded = formatDecimal(homeStats.avg_goals_conceded);
            const awayScored = formatDecimal(awayStats.avg_goals_scored);
            const awayConceded = formatDecimal(awayStats.avg_goals_conceded);

            if (sampleSize > 0 && homeWinRate && awayWinRate && homeScored && awayScored && homeConceded && awayConceded) {
                evidenceParts.push(
                    `Season dataset (${sampleSize} matches): ${match.home_team} win rate ${homeWinRate}, ${homeScored} scored / ${homeConceded} conceded per match; ${match.away_team} win rate ${awayWinRate}, ${awayScored} scored / ${awayConceded} conceded.`
                );
            }
        }

        const homeRecent = getRecentFormPoints(homeSnapshot, 5);
        const awayRecent = getRecentFormPoints(awaySnapshot, 5);
        if (homeRecent && awayRecent) {
            evidenceParts.push(
                `Recent form (last ${homeRecent.matches}): ${match.home_team} ${homeRecent.points}/${homeRecent.maxPoints} points, ${match.away_team} ${awayRecent.points}/${awayRecent.maxPoints}.`
            );
        }

        const homeXg = formatDecimal(pred?.expected_goals?.home);
        const awayXg = formatDecimal(pred?.expected_goals?.away);
        if (homeXg && awayXg) {
            evidenceParts.push(`Model xG projection: ${match.home_team} ${homeXg} vs ${match.away_team} ${awayXg}.`);
        }

        const homeRating = formatDecimal(pred?.avg_ratings?.team1, 2);
        const awayRating = formatDecimal(pred?.avg_ratings?.team2, 2);
        if (homeRating && awayRating) {
            evidenceParts.push(`Projected lineup ratings: ${homeRating} vs ${awayRating}.`);
        }

        if (evidenceParts.length === 0) return '';
        return evidenceParts.slice(0, 3).join(' ');
    }

    function renderTeamLogo(teamName, logoUrl) {
        const fallbackIcon = TEAM_LOGOS[teamName] || '⚽';
        if (!logoUrl) {
            return `<span class="team-logo-fallback visible" aria-hidden="true">${fallbackIcon}</span>`;
        }

        const safeUrl = encodeAssetUrl(logoUrl);
        return `
            <span class="team-logo-wrap">
                <img src="${safeUrl}" alt="${teamName} Logo" class="team-logo" loading="lazy"
                     onerror="this.style.display='none'; this.nextElementSibling.style.display='inline-flex';">
                <span class="team-logo-fallback" style="display:none;" aria-hidden="true">${fallbackIcon}</span>
            </span>
        `;
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
        const hmmAdjustments = pred.adjustments;
        const hasHmmAdjustments = Boolean(hmmAdjustments && hmmAdjustments.hmm_applied);
        const hmmAdjustmentsHtml = hasHmmAdjustments ? `
            <div class="hmm-adjust-summary">
                <div class="hmm-adjust-label">${translations[currentLang].hmm_adjustments}</div>
                <div class="hmm-adjust-values">
                    <span>${match.home_team}: <strong>${formatSignedPercent(hmmAdjustments.hmm_team1)}</strong></span>
                    <span>${match.away_team}: <strong>${formatSignedPercent(hmmAdjustments.hmm_team2)}</strong></span>
                </div>
            </div>
        ` : '';

        // Build clearer confidence metrics for explanation
        const homeWinProb = Number(pred.probabilities?.home_win) || 0;
        const drawProb = Number(pred.probabilities?.draw) || 0;
        const awayWinProb = Number(pred.probabilities?.away_win) || 0;
        const outcomes = [
            { key: 'home_win', label: `${match.home_team} win`, value: homeWinProb },
            { key: 'draw', label: 'draw', value: drawProb },
            { key: 'away_win', label: `${match.away_team} win`, value: awayWinProb },
        ];
        const sortedOutcomes = [...outcomes].sort((a, b) => b.value - a.value);
        const favorite = sortedOutcomes[0] || { key: 'draw', label: 'draw', value: 0 };
        const runnerUp = sortedOutcomes[1] || { key: 'draw', label: 'draw', value: 0 };

        const favoriteChance = Math.max(0, favorite.value);
        const leadGap = Math.max(0, favorite.value - runnerUp.value);
        const probsNormalized = outcomes
            .map(o => Math.max(0, o.value) / 100)
            .filter(v => v > 0);
        const entropy = probsNormalized.reduce((sum, p) => sum - (p * Math.log(p)), 0);
        const maxEntropy = Math.log(3);
        const clarityScore = Math.max(0, Math.min(100, (1 - (entropy / maxEntropy)) * 100));

        const favoriteOutcomeText = favorite.key === 'draw'
            ? 'a draw'
            : (favorite.key === 'home_win' ? `${match.home_team} to win` : `${match.away_team} to win`);

        const getMetricStatus = (metric, value) => {
            if (metric === 'favorite') {
                if (value >= 58) return 'good';
                if (value >= 45) return 'ok';
                return 'warn';
            }
            if (metric === 'lead') {
                if (value >= 18) return 'good';
                if (value >= 10) return 'ok';
                return 'warn';
            }
            if (metric === 'clarity') {
                if (value >= 45) return 'good';
                if (value >= 28) return 'ok';
                return 'warn';
            }
            return 'ok';
        };

        const confidenceIndicators = [
            {
                label: 'Favorite Chance',
                value: `${favoriteChance.toFixed(1)}%`,
                status: getMetricStatus('favorite', favoriteChance),
                help: `Chance of the most likely result (${favorite.label}). Higher means a clearer favorite.`
            },
            {
                label: 'Lead over 2nd Option',
                value: `+${leadGap.toFixed(1)} pts`,
                status: getMetricStatus('lead', leadGap),
                help: 'Difference between the top result and the second most likely result. Bigger gap means less uncertainty.'
            },
            {
                label: 'Clarity Score',
                value: `${clarityScore.toFixed(0)}/100`,
                status: getMetricStatus('clarity', clarityScore),
                help: 'How concentrated the three probabilities are. 100 = one clear direction, 0 = outcomes are almost evenly split.'
            },
        ];

        const confidenceExplanations = {
            high: {
                icon: '🟢',
                title: 'High Confidence Prediction',
                reason: `The model sees a <strong>clear direction</strong>: <strong>${favoriteOutcomeText}</strong>. The top outcome is ${favoriteChance.toFixed(1)}%, with a ${leadGap.toFixed(1)} point lead over the next option.`
            },
            medium: {
                icon: '🟡',
                title: 'Medium Confidence Prediction',
                reason: `The model has a <strong>preferred outcome</strong> (${favoriteOutcomeText}), but alternative outcomes are still realistic. The lead over the second option is ${leadGap.toFixed(1)} points.`
            },
            low: {
                icon: '🔴',
                title: 'Low Confidence Prediction',
                reason: `This match is <strong>hard to separate</strong>. The top outcome (${favoriteOutcomeText}) is only ${favoriteChance.toFixed(1)}%, and probabilities are relatively close.`
            }
        };

        const currentConfidence = confidenceExplanations[confClass] || confidenceExplanations.medium;
        const confidenceEvidence = buildConfidenceDataEvidence(match, pred);
        const confidenceHtml = `
            <div class="confidence-explanation-panel">
                <div class="confidence-header">
                    <span class="confidence-icon">${currentConfidence.icon}</span>
                    <h4>${currentConfidence.title}</h4>
                </div>
                <p class="confidence-reason">${currentConfidence.reason}</p>
                ${confidenceEvidence ? `<p class="confidence-evidence">${confidenceEvidence}</p>` : ''}
                <div class="confidence-indicators">
                    ${confidenceIndicators.map(ind => `
                        <div class="confidence-indicator">
                            <div class="indicator-header">
                                <span class="indicator-label">${ind.label}</span>
                                <span class="indicator-help-wrap">
                                    <button type="button" class="indicator-help" aria-label="What does ${ind.label} mean?">?</button>
                                    <span class="indicator-tooltip">${ind.help}</span>
                                </span>
                            </div>
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
        scorelinesHtml = buildDualScorelinesPanel(
            pred.top5_scores_home_perspective || pred.top5_scores || [],
            pred.top5_scores_away_perspective || [],
            match.home_team,
            match.away_team
        );

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

            const buildStateProfiles = (team) => renderStateProfilesList(team);

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

        // Build heatmaps HTML
        let heatmapsHtml = '';
        const playerHeatmapUrl = pred.player_heatmap_url || pred.heatmaps?.player;
        const mainClusterHeatmapUrl = pred.main_cluster_heatmap_url || pred.heatmaps?.main_clusters;
        const stripClusterHeatmapUrl = pred.strip_cluster_heatmap_url || pred.heatmaps?.strip_clusters;
        if (playerHeatmapUrl || mainClusterHeatmapUrl || stripClusterHeatmapUrl) {
            const cards = [];
            if (playerHeatmapUrl) {
                cards.push(`
                    <div class="heatmap-card">
                        <div class="heatmap-title">Player Ratings</div>
                        <img src="${playerHeatmapUrl}" alt="Player rating heatmap" class="heatmap-img">
                    </div>
                `);
            }
            if (mainClusterHeatmapUrl) {
                cards.push(`
                    <div class="heatmap-card">
                        <div class="heatmap-title">Main Clusters</div>
                        <img src="${mainClusterHeatmapUrl}" alt="Main cluster heatmap" class="heatmap-img">
                    </div>
                `);
            }
            if (stripClusterHeatmapUrl) {
                cards.push(`
                    <div class="heatmap-card">
                        <div class="heatmap-title">Strip Clusters</div>
                        <img src="${stripClusterHeatmapUrl}" alt="Strip cluster heatmap" class="heatmap-img">
                    </div>
                `);
            }
            heatmapsHtml = `
                <div class="insights-panel">
                    <h4><span class="icon">🗺️</span> Tactical Heatmaps</h4>
                    <div class="heatmaps-grid">
                        ${cards.join('')}
                    </div>
                </div>
            `;
        }

        return `
            <div class="match-card" data-match-id="${match.match_id}">
                <div class="match-header">
                    <div class="team home">
                        <span class="team-name">${match.home_team}</span>
                        ${renderTeamLogo(match.home_team, pred.team1_logo_url)}
                    </div>
                    <div class="match-center">
                        <div class="predicted-score">${pred.predicted_score}</div>
                        <div class="match-time">${match.time}</div>
                        <div class="confidence-badge ${confClass}">${confLabel}</div>
                    </div>
                    <div class="team away">
                        ${renderTeamLogo(match.away_team, pred.team2_logo_url)}
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
                ${hmmAdjustmentsHtml}

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
                        ${heatmapsHtml}
                    </div>
                </div>
            </div>
        `;
    }
});
