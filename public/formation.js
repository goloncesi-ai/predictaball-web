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
function getFormationPositions(formationString) {
    const lines = parseFormation(formationString);
    const positions = [];

    // GK is always first at x=10, y=34 (center of goal area)
    positions.push({ x: 10, y: 34, role: 'GK', line: 0 });

    // Calculate positions for outfield players
    const pitchHeight = 68;
    const startX = 18; // Where defenders start
    const lineSpacing = 22; // Space between defensive lines

    lines.forEach((playersInLine, lineIndex) => {
        const xPos = startX + (lineIndex * lineSpacing);
        const ySpacing = pitchHeight / (playersInLine + 1);

        for (let i = 0; i < playersInLine; i++) {
            const yPos = ySpacing * (i + 1);
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

// Render players for one team on the pitch
function renderTeamPlayers(containerId, positions, players, side, teamColor) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Clear existing
    container.innerHTML = '';

    positions.forEach((pos, idx) => {
        if (idx >= players.length) return;

        const player = players[idx];
        const x = side === 'home' ? pos.x : (100 - pos.x); // Mirror for away team
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
    tooltip.textContent = `${player.name || 'Unknown'}\nRating: ${player.rating ? player.rating.toFixed(2) : 'N/A'}`;
    playerNode.appendChild(tooltip);
}

// Main render function
function renderPitchView(team1Data, team2Data) {
    if (!team1Data || !team2Data) {
        console.error('Missing team data');
        return;
    }

    // Show pitch container
    const pitchContainer = document.getElementById('lineup-pitch-container');
    if (pitchContainer) {
        pitchContainer.classList.remove('hidden');
    }

    // Update team info
    document.getElementById('pitch-team1-name').textContent = team1Data.name || '-';
    document.getElementById('pitch-team1-formation').textContent = team1Data.formation || '-';
    document.getElementById('pitch-team2-name').textContent = team2Data.name || '-';
    document.getElementById('pitch-team2-formation').textContent = team2Data.formation || '-';

    // Get positions for each formation
    const team1Positions = getFormationPositions(team1Data.formation);
    const team2Positions = getFormationPositions(team2Data.formation);

    // Render players
    renderTeamPlayers('team1-players', team1Positions, team1Data.players, 'home', '#3b82f6');
    renderTeamPlayers('team2-players', team2Positions, team2Data.players, 'away', '#f43f5e');
}

// Hide pitch view
function hidePitchView() {
    const pitchContainer = document.getElementById('lineup-pitch-container');
    if (pitchContainer) {
        pitchContainer.classList.add('hidden');
    }
}

// Get team lineup from CSV data
async function getTeamLatestLineup(teamName) {
    try {
        // For now, we'll need to fetch and parse CSV
        // In Phase 2, we'll pre-process this into data.js
        const csvPath = `/Data/Turkish Super League/${teamName}/mixed-seasons/${teamName}_Games_Input.csv`;
        const response = await fetch(csvPath);

        if (!response.ok) {
            throw new Error(`Failed to fetch CSV: ${response.status}`);
        }

        const csvText = await response.text();
        const lines = csvText.trim().split('\n');

        if (lines.length < 2) {
            throw new Error('CSV file is empty or invalid');
        }

        // Parse header
        const headers = lines[0].split(',');
        // Get most recent match (last line)
        const lastMatch = lines[lines.length - 1].split(',');

        // Build data object
        const data = {};
        headers.forEach((header, idx) => {
            data[header.trim()] = lastMatch[idx]?.trim();
        });

        // Determine if team is Team1 or Team2 in this match
        const isTeam1 = data.Team1 === teamName;
        const prefix = isTeam1 ? 'Team1' : 'Team2';

        // Extract formation
        const formation = data[`${prefix}Formation`] || '4-4-2';

        // Extract players (11 players)
        const players = [];
        for (let i = 1; i <= 11; i++) {
            const name = data[`${prefix}Player${i}Name`] || `Player ${i}`;
            const rating = parseFloat(data[`${prefix}Player${i}`]) || 6.0;
            players.push({ name, rating });
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
