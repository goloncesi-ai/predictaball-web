/**
 * Formation Pitch Visualization
 * Handles parsing formations and rendering players on pitch
 */

// Parse formation string like "4-3-3" into array [4, 3, 3]
function parseFormation(formationString) {
    if (!formationString || typeof formationString !== 'string') {
        return [4, 4, 2]; // Default formation
    }
    return formationString.split('-').map(num => parseInt(num, 10)).filter(n => !isNaN(n));
}

// Calculate positions for all players in a formation
// Vertical pitch: 68 wide x 100 tall
// Orientation: GK at bottom (y=90), strikers at top (y=10)
// Formation order: DEF-MID-FWD (e.g., "4-4-2" = 4 defenders, 4 mids, 2 forwards)
function getFormationPositions(formationString) {
    const lines = parseFormation(formationString);
    const positions = [];

    // GK at bottom: y=90, x=34 (center)
    positions.push({ x: 34, y: 90, role: 'GK', line: 0 });

    // Calculate spacing to use full pitch
    const pitchWidth = 68;
    const pitchHeight = 100;
    const usableHeight = 75; // From y=10 (top) to y=85 (just above GK)
    const topY = 12; // Start forwards near top
    const bottomY = 85; // End defenders just above GK

    // Calculate Y positions for each line
    const lineSpacing = lines.length > 1 ? (bottomY - topY) / (lines.length - 1) : 0;

    // REVERSE iteration: first line (defenders) should be at BOTTOM
    lines.forEach((playersInLine, lineIndex) => {
        // Reverse index: 0 becomes last, last becomes 0
        const reversedIndex = lines.length - 1 - lineIndex;
        // Y position: forwards at top (low Y), defenders at bottom (high Y)
        const yPos = topY + (reversedIndex * lineSpacing);
        const xSpacing = pitchWidth / (playersInLine + 1);

        for (let i = 0; i < playersInLine; i++) {
            const xPos = xSpacing * (i + 1);
            const role = lineIndex === 0 ? 'DEF' :
                lineIndex === lines.length - 1 ? 'FWD' : 'MID';

            positions.push({
                x: xPos,
                y: yPos,
                role: role,
                line: lineIndex + 1
            });
        }
    });

    return positions;
}

// Render players for one team on their own vertical pitch
function renderTeamPlayers(containerId, positions, players, side, teamColor) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Clear existing
    container.innerHTML = '';

    positions.forEach((pos, idx) => {
        if (idx >= players.length) return;

        const player = players[idx];
        // No mirroring needed - each team has their own pitch
        const x = pos.x;
        const y = pos.y;

        // Create player node group
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.classList.add('player-node');
        g.setAttribute('data-player-index', idx);
        g.setAttribute('data-player-name', player.name || '-');
        g.setAttribute('data-player-rating', player.rating || '-');

        // Circle
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', x);
        circle.setAttribute('cy', y);
        circle.setAttribute('r', '2.8');
        circle.classList.add('player-circle');

        // Rating/Number
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', x);
        text.setAttribute('y', y);
        text.classList.add('player-number');
        const rating = player.rating ? (Math.round(player.rating * 10) / 10).toFixed(1) : '-';
        text.textContent = rating;

        // Player last name (below circle)
        const name = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        name.setAttribute('x', x);
        name.setAttribute('y', y + 4.5);
        name.classList.add('player-name');
        const lastName = player.name ? player.name.split(' ').slice(-1)[0] : '-';
        name.textContent = lastName.length > 10 ? lastName.substring(0, 10) : lastName;

        g.appendChild(circle);
        g.appendChild(text);
        g.appendChild(name);
        container.appendChild(g);

        // Add hover tooltip
        addPlayerTooltip(g, player);
    });
}

// Add tooltip on player hover
function addPlayerTooltip(playerNode, player) {
    const tooltip = document.createElement('title');
    let text = `${player.name || 'Unknown'}`;

    if (player.stats && player.stats.hasStats) {
        // Show detailed stats if available
        text += `\nRating: ${player.stats.rating ? parseFloat(player.stats.rating).toFixed(1) : 'N/A'}`;
        text += `\nGoals: ${player.stats.goals}`;
        text += `\nAssists: ${player.stats.assists}`;
        text += `\nApps: ${player.stats.appearances}`;
    } else {
        // Fallback to simple rating
        text += `\nRating: ${player.rating ? parseFloat(player.rating).toFixed(1) : 'N/A'}`;
    }

    tooltip.textContent = text;
    playerNode.appendChild(tooltip);
}

// Main render function - shows pitches individually per team
function renderPitchView(team1Data, team2Data) {
    const pitch1Wrapper = document.getElementById('pitch-team1-wrapper');
    const pitch2Wrapper = document.getElementById('pitch-team2-wrapper');

    // Team 1 (Home) - show if data available
    if (team1Data && team1Data.formation) {
        if (pitch1Wrapper) pitch1Wrapper.classList.remove('hidden');

        // Update team info with logo image (same as Analysis tab)
        const badgeElem = document.querySelector('#pitch-team1-wrapper .team-badge');
        if (badgeElem) {
            badgeElem.innerHTML = `<img src="/logos/${team1Data.name}.png" alt="${team1Data.name}" class="pitch-team-logo" onerror="this.style.display='none'">`;
        }

        document.getElementById('pitch-team1-name').textContent = team1Data.name || '-';
        const homeFormationSelect = document.getElementById('sim-team1-formation');
        if (homeFormationSelect && team1Data.formation) {
            homeFormationSelect.value = team1Data.formation;
        }

        // Get positions and render
        const team1Positions = getFormationPositions(team1Data.formation);
        renderTeamPlayers('team1-players', team1Positions, team1Data.players, 'home', '#3b82f6');
    } else {
        if (pitch1Wrapper) pitch1Wrapper.classList.add('hidden');
    }

    // Team 2 (Away) - show if data available
    if (team2Data && team2Data.formation) {
        if (pitch2Wrapper) pitch2Wrapper.classList.remove('hidden');

        // Update team info with logo image (same as Analysis tab)
        const badgeElem = document.querySelector('#pitch-team2-wrapper .team-badge');
        if (badgeElem) {
            badgeElem.innerHTML = `<img src="/logos/${team2Data.name}.png" alt="${team2Data.name}" class="pitch-team-logo" onerror="this.style.display='none'">`;
        }

        document.getElementById('pitch-team2-name').textContent = team2Data.name || '-';
        const awayFormationSelect = document.getElementById('sim-team2-formation');
        if (awayFormationSelect && team2Data.formation) {
            awayFormationSelect.value = team2Data.formation;
        }

        // Get positions and render
        const team2Positions = getFormationPositions(team2Data.formation);
        renderTeamPlayers('team2-players', team2Positions, team2Data.players, 'away', '#f43f5e');
    } else {
        if (pitch2Wrapper) pitch2Wrapper.classList.add('hidden');
    }
}

// Hide pitch view
function hidePitchView() {
    const pitch1Wrapper = document.getElementById('pitch-team1-wrapper');
    const pitch2Wrapper = document.getElementById('pitch-team2-wrapper');
    if (pitch1Wrapper) pitch1Wrapper.classList.add('hidden');
    if (pitch2Wrapper) pitch2Wrapper.classList.add('hidden');
}

// Cache for player stats
const PLAYER_STATS_DB = {};

async function fetchTeamPlayerStats(teamName) {
    if (PLAYER_STATS_DB[teamName]) return PLAYER_STATS_DB[teamName];

    try {
        // Normalize name to match python script: remove accents, spaces, lowercase
        // e.g. "Fenerbahçe" -> "fenerbahce", "Galatasaray" -> "galatasaray"
        const cleanName = teamName.normalize("NFD").replace(/[\u0300-\u036f]/g, "")
            .toLowerCase().replace(/ /g, "").replace(/-/g, "");

        console.log(`[Stats] Fetching DB for ${teamName} -> /data/players/${cleanName}.json`);
        const response = await fetch(`/data/players/${cleanName}.json?v=2`);

        if (!response.ok) {
            console.warn(`No stats DB found for ${teamName} (checked /data/players/${cleanName}.json)`);
            return null;
        }

        const data = await response.json();

        // Create a map by player name for easy lookup
        const statsMap = {};
        if (data.players) {
            data.players.forEach(p => {
                // Key by normalized name for robust matching
                // e.g. "İsmail Yüksek" -> "ismail yuksek"
                const normName = normalizeName(p.name);
                statsMap[normName] = p;

                // Also add last name as fallback key
                const parts = normName.split(' ');
                if (parts.length > 1) {
                    const lastName = parts[parts.length - 1];
                    // Only map if unique, otherwise conflict risk
                    if (!statsMap[lastName]) statsMap[lastName] = p;
                }
            });
        }

        PLAYER_STATS_DB[teamName] = statsMap;
        return statsMap;
    } catch (e) {
        console.warn(`Could not load stats for ${teamName}:`, e);
        return null;
    }
}

// Get team lineup from CSV data
function encodePathSegment(value) {
    return encodeURIComponent(`${value || ''}`);
}

async function getTeamLatestLineup(teamName, leagueName = 'Turkish Super League', explicitCsvPath = '') {
    try {
        // 1. Start fetching stats in parallel
        const statsPromise = fetchTeamPlayerStats(teamName);

        // 2. Fetch and parse CSV
        const defaultCsvPath = `/Data/${encodePathSegment(leagueName)}/${encodePathSegment(teamName)}/mixed-seasons/${encodePathSegment(`${teamName}_Games_Input.csv`)}`;
        const csvPath = explicitCsvPath || defaultCsvPath;
        const response = await fetch(encodeURI(csvPath));

        if (!response.ok) {
            throw new Error(`Failed to fetch CSV: ${response.status}`);
        }

        const csvText = await response.text();
        const lines = csvText
            .split(/\r?\n/)
            .map(line => line.trim())
            .filter(line => line.length > 0);

        if (lines.length < 2) {
            throw new Error('CSV file is empty or invalid');
        }

        // Parse header
        const headers = lines[0].split(',');
        // Newest match is stored on first data row (line right after header)
        const latestMatch = lines[1].split(',');

        // Build data object
        const data = {};
        headers.forEach((header, idx) => {
            data[header.trim()] = latestMatch[idx]?.trim();
        });

        // Determine if team is Team1 or Team2 in this match
        const isTeam1 = data.Team1 === teamName;
        const prefix = isTeam1 ? 'Team1' : 'Team2';

        // Extract formation
        const formation = data[`${prefix}Formation`] || '4-4-2';

        // Wait for stats to load
        const statsMap = await statsPromise;
        const normalizedStatsMap = {}; // Not used but good for debug if we wanted
        // Actually fetchTeamPlayerStats returns a normalized map already?
        // Wait, my previous code in fetchTeamPlayerStats was constructing a map keyed by normalized name.
        // Let's verify that fetchTeamPlayerStats DOES that.
        // It does: `const normName = normalizeName(p.name); statsMap[normName] = p;`

        // Extract players (11 players)
        const players = [];
        for (let i = 1; i <= 11; i++) {
            const rawName = data[`${prefix}Player${i}Name`] || `Player ${i}`;
            let rating = parseFloat(data[`${prefix}Player${i}`]) || 6.0;
            let fullStats = null;

            // Try to find in stats DB
            if (statsMap) {
                // Normalize CSV name: "İsmail Yüksek" -> "ismail yuksek"
                const normName = normalizeName(rawName);

                // 1. Try exact normalized match
                let match = statsMap[normName];

                // 2. Try partial match (normalized last name)
                if (!match) {
                    const parts = normName.split(' ');
                    const lastName = parts[parts.length - 1];
                    match = statsMap[lastName];
                }

                if (match) {
                    // Only use stats rating if valid (>0), otherwise fallback to CSV rating
                    // But if stats are 0 (like now), we prioritize CSV.
                    // This fixes the "0.0 rating" issue.
                    if (match.stats && match.stats.rating && match.stats.rating > 0) {
                        rating = match.stats.rating;
                    }
                    fullStats = match.stats;
                }
            }

            players.push({
                name: rawName,
                rating: rating,
                stats: fullStats // Attach full stats for tooltip
            });
        }

        return {
            name: teamName,
            formation,
            players
        };
    } catch (error) {
        console.error(`Error loading lineup for ${teamName}:`, error);
        // Return default fallback
        return {
            name: teamName,
            formation: '4-4-2',
            players: Array.from({ length: 11 }, (_, i) => ({
                name: `Player ${i + 1}`,
                rating: 6.5
            }))
        };
    }
}

// Helper: Normalize name for matching (removes accents, case, spaces)
function normalizeName(str) {
    if (!str) return "";
    return str.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}

// Export functions (if using modules, otherwise they're global)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        parseFormation,
        getFormationPositions,
        renderTeamPlayers,
        renderPitchView,
        hidePitchView,
        getTeamLatestLineup
    };
}
