#!/usr/bin/env python3
"""
Build script for Free Chess Stats Database
Processes CSV and JSON data files to generate JavaScript data files for the static website.

Usage:
    python build_site.py

This will read from:
    - ../Stats/player_stats.csv
    - ../Stats/aggregated_game_data.csv
    - ../PGNs/*.json

And generate:
    - data/players.js
    - data/tournaments.js
    - data/tpr_year.js
"""

import os
import sys
import json
import csv
from pathlib import Path
from collections import defaultdict
import math

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_OUTPUT_DIR = SCRIPT_DIR / "data"

# Stats directory (now inside Free_Chess_Stats_Database)
STATS_DIR = SCRIPT_DIR / "Stats"

# Time control directories
TIME_CONTROLS = ["classical", "rapid", "blitz"]
CLASSICAL_DIR = STATS_DIR / "Classical"
RAPID_DIR = STATS_DIR / "Rapid"
BLITZ_DIR = STATS_DIR / "Blitz"

# Import EPR calculator for TPR calculations
sys.path.insert(0, str(PROJECT_ROOT))
try:
    from epr_calculator import optimize_w, calculate_EPR, adjust_mn
except ImportError:
    print("Warning: Could not import epr_calculator. TPR calculations may be limited.")
    optimize_w = None
    calculate_EPR = None
    adjust_mn = None


def find_csv_files(directory, pattern):
    """Find CSV files matching a pattern (e.g., 'player_stats') recursively in directory."""
    matches = []
    if not directory.exists():
        return matches
    
    # Search recursively for CSV files containing the pattern in their name
    for csv_file in directory.rglob("*.csv"):
        if pattern.lower() in csv_file.stem.lower():
            matches.append(csv_file)
    
    return matches


def load_player_stats():
    """Load player statistics from all player_stats*.csv files in Classical subfolders."""
    # Find all player_stats CSV files recursively in Classical directory
    csv_files = find_csv_files(CLASSICAL_DIR, "player_stats")
    
    if not csv_files:
        print(f"Warning: No player_stats*.csv files found in {CLASSICAL_DIR}")
        return []
    
    print(f"Found {len(csv_files)} player_stats files to merge")
    
    # Aggregate players by name
    player_data = {}
    
    for csv_path in csv_files:
        print(f"  Loading: {csv_path.name}")
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        name = row.get('Player', '')
                        if not name:
                            continue
                        
                        # If player already exists, merge stats (sum games, weighted average TPR, etc.)
                        if name in player_data:
                            existing = player_data[name]
                            new_games = safe_int(row.get('total_game_count', 0))
                            
                            # Update game counts
                            existing['games'] += new_games
                            existing['whiteGames'] += safe_int(row.get('White_games', 0))
                            existing['blackGames'] += safe_int(row.get('Black_games', 0))
                            existing['points'] += safe_float(row.get('Points', 0))
                            existing['whitePoints'] += safe_float(row.get('white_result_sum', 0))
                            existing['blackPoints'] += safe_float(row.get('black_result_sum', 0))
                            
                            # Keep highest Elo
                            existing['elo'] = max(existing['elo'], safe_float(row.get('Elo', 0)))
                        else:
                            player_data[name] = {
                                'name': name,
                                'elo': safe_float(row.get('Elo', 0)),
                                'tpr': safe_float(row.get('TPR', 0)),
                                'whiteTpr': safe_float(row.get('white_tpr', 0)),
                                'blackTpr': safe_float(row.get('black_tpr', 0)),
                                'games': safe_int(row.get('total_game_count', 0)),
                                'points': safe_float(row.get('Points', 0)),
                                'avgGi': safe_float(row.get('avg_gi', 0)),
                                'avgMissedPoints': safe_float(row.get('avg_missed_points', 0)),
                                'avgAcpl': safe_float(row.get('avg_acpl', 0)),
                                'whiteGames': safe_int(row.get('White_games', 0)),
                                'blackGames': safe_int(row.get('Black_games', 0)),
                                'whitePoints': safe_float(row.get('white_result_sum', 0)),
                                'blackPoints': safe_float(row.get('black_result_sum', 0)),
                                'avgGiWhite': safe_float(row.get('avg_gi_white', 0)),
                                'avgGiBlack': safe_float(row.get('avg_gi_black', 0)),
                                'avgMpWhite': safe_float(row.get('avg_missed_points_white', 0)),
                                'avgMpBlack': safe_float(row.get('avg_missed_points_black', 0)),
                                'giMedian': safe_float(row.get('gi_median', 0)),
                                'giStd': safe_float(row.get('gi_std', 0)),
                            }
                    except Exception as e:
                        print(f"Warning: Error processing player row: {e}")
                        continue
        except Exception as e:
            print(f"Warning: Error reading {csv_path}: {e}")
            continue
    
    players = list(player_data.values())
    print(f"Loaded {len(players)} unique players from {len(csv_files)} files")
    return players


def load_game_data():
    """Load aggregated game data from CSV (Classical only)."""
    csv_path = CLASSICAL_DIR / "aggregated_game_data.csv"
    if not csv_path.exists():
        print(f"Warning: {csv_path} not found")
        return []
    
    games = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                game = {
                    'white': row.get('White', ''),
                    'black': row.get('Black', ''),
                    'event': row.get('Event', ''),
                    'site': row.get('Site', ''),
                    'round': row.get('Round', ''),
                    'date': row.get('Date', ''),
                    'whiteElo': safe_int(row.get('WhiteElo', 0)),
                    'blackElo': safe_int(row.get('BlackElo', 0)),
                    'whiteResult': safe_float(row.get('WhiteResult', 0)),
                    'blackResult': safe_float(row.get('BlackResult', 0)),
                    'whiteGi': safe_float(row.get('white_gi', 0)),
                    'blackGi': safe_float(row.get('black_gi', 0)),
                }
                games.append(game)
            except Exception as e:
                continue
    
    print(f"Loaded {len(games)} games from aggregated_game_data.csv")
    return games


def calculate_tournament_summary_stats(player_stats_list, games_list):
    """Calculate summary statistics for a tournament (Mean, Median, Std Dev, Min, Max)."""
    import statistics
    
    def calc_stats(values):
        """Calculate stats for a list of values."""
        if not values:
            return {'mean': 0, 'median': 0, 'std': 0, 'min': 0, 'max': 0}
        # Filter only None values - zeros are valid data points
        values = [v for v in values if v is not None]
        if not values:
            return {'mean': 0, 'median': 0, 'std': 0, 'min': 0, 'max': 0}
        
        mean = sum(values) / len(values)
        median = statistics.median(values)
        std = statistics.stdev(values) if len(values) > 1 else 0
        min_val = min(values)
        max_val = max(values)
        
        return {
            'mean': round(mean, 2),
            'median': round(median, 2),
            'std': round(std, 2),
            'min': round(min_val, 2),
            'max': round(max_val, 2)
        }
    
    # Collect values from player stats
    gi_values = [p.get('avgGi', 0) for p in player_stats_list if p.get('avgGi')]
    mp_values = [p.get('avgMp', 0) for p in player_stats_list if p.get('avgMp')]
    elo_values = [p.get('elo', 0) for p in player_stats_list if p.get('elo')]
    tpr_values = [p.get('tpr', 0) for p in player_stats_list if p.get('tpr')]
    
    # Collect GI values from games (white and black separately for more detail)
    white_gi = [g.get('whiteGi', 0) for g in games_list if g.get('whiteGi')]
    black_gi = [g.get('blackGi', 0) for g in games_list if g.get('blackGi')]
    white_mp = [g.get('whiteMp', 0) for g in games_list if g.get('whiteMp')]
    black_mp = [g.get('blackMp', 0) for g in games_list if g.get('blackMp')]
    
    # Combine white and black for overall stats
    all_gi = white_gi + black_gi
    all_mp = white_mp + black_mp
    
    summary_stats = {
        'totalGames': len(games_list),
        'totalPlayers': len(player_stats_list),
        'avgGi': calc_stats(gi_values if gi_values else all_gi),
        'avgMissedPoints': calc_stats(mp_values if mp_values else all_mp),
        'avgGiWhite': calc_stats(white_gi),
        'avgGiBlack': calc_stats(black_gi),
        'avgMpWhite': calc_stats(white_mp),
        'avgMpBlack': calc_stats(black_mp),
        'elo': calc_stats(elo_values),
        'tpr': calc_stats(tpr_values)
    }
    
    return summary_stats


def is_round_pairing(event_str):
    """
    Check if an Event string looks like a round pairing rather than a tournament name.
    
    Patterns detected:
    - "Round X: Player1 - Player2" (English)
    - "Game X: Player1 - Player2" (Match games)
    - "Round of 32 | Game 1: ..." (Knockout rounds)
    - "Quarter-Finals | Game 1: ..." (Knockout stages)
    - "Ottavo turno: Player1 - Player2" (Italian - ordinal + turno)
    - "Tiebreak: Player1 - Player2"
    - Other patterns with colon followed by player names
    """
    import re
    
    if not event_str:
        return False
    
    # Pattern 1: English round format "Round X: ..." or "Classical Round X: ..." etc.
    if re.match(r'^(Classical\s+|Rapid\s+|Blitz\s+)?Round\s+\d+\s*:', event_str, re.IGNORECASE):
        return True
    
    # Pattern 2: Game format "Game X: ..."
    if re.match(r'^Game\s+\d+\s*:', event_str, re.IGNORECASE):
        return True
    
    # Pattern 3: Knockout rounds "Round of X | Game Y: ..."
    if re.match(r'^Round\s+of\s+\d+\s*\|', event_str, re.IGNORECASE):
        return True
    
    # Pattern 4: Knockout stages (Quarter-Finals, Semi-Finals, Finals, etc.)
    knockout_stages = [
        r'^Quarter-Finals?\s*\|',
        r'^Semi-Finals?\s*\|',
        r'^Finals?\s*\|',
        r'^3rd\s+Place\s*\|',
        r'^Bronze\s+Medal\s*\|',
    ]
    for pattern in knockout_stages:
        if re.match(pattern, event_str, re.IGNORECASE):
            return True
    
    # Pattern 5: Tiebreak games
    if re.match(r'^Tiebreak\s*:', event_str, re.IGNORECASE):
        return True
    if '| Tiebreak:' in event_str or '|Tiebreak:' in event_str:
        return True
    
    # Pattern 6: Italian ordinal + "turno" (e.g., "Ottavo turno:", "Primo turno:")
    italian_ordinals = [
        'primo', 'secondo', 'terzo', 'quarto', 'quinto', 
        'sesto', 'settimo', 'ottavo', 'nono', 'decimo',
        'undicesimo', 'dodicesimo', 'tredicesimo'
    ]
    for ordinal in italian_ordinals:
        if re.match(rf'^{ordinal}\s+turno\s*:', event_str, re.IGNORECASE):
            return True
    
    # Pattern 7: German/French/Spanish round patterns
    other_round_patterns = [
        r'^Runde\s+\d+\s*:',      # German
        r'^Tour\s+\d+\s*:',       # French
        r'^Ronda\s+\d+\s*:',      # Spanish
        r'^Partida\s+\d+\s*:',    # Portuguese
    ]
    for pattern in other_round_patterns:
        if re.match(pattern, event_str, re.IGNORECASE):
            return True
    
    # Pattern 8: Heuristic - if it looks like "Last, First - Last, First" (player vs player)
    # This is a common format for head-to-head match events
    if re.match(r'^[A-Z][a-z]+,\s+[A-Z][a-z]+\s+-\s+[A-Z][a-z]+,\s+[A-Z][a-z]+$', event_str):
        return True
    
    return False


def extract_tournament_from_url(site_url):
    """
    Extract tournament name from a Lichess broadcast URL.
    
    Examples:
    - "https://lichess.org/broadcast/aeroflot-open-2025/round-1/..."
      -> "Aeroflot Open 2025"
    - "https://lichess.org/broadcast/fide-grand-swiss-2025--open/..."
      -> "FIDE Grand Swiss 2025 Open"
    - "https://lichess.org/broadcast/27-festival-internazionale-di-scacchi-citta-di-trieste/..."
      -> "27 Festival Internazionale Di Scacchi Citta Di Trieste"
    """
    import re
    
    if not site_url:
        return None
    
    slug = None
    
    # Try to extract the tournament slug from Lichess broadcast URL
    # Format: https://lichess.org/broadcast/TOURNAMENT-SLUG/round-X/...
    match = re.search(r'/broadcast/([^/]+)/', site_url)
    if match:
        slug = match.group(1)
    else:
        # Try direct tournament URL format: https://lichess.org/TOURNAMENT-SLUG/GAME-ID/...
        # Match pattern: lichess.org/some-tournament-name-2025/gameId
        match = re.search(r'lichess\.org/([a-z0-9-]+(?:-\d{4})?)/[a-zA-Z0-9]+', site_url)
        if match:
            potential_slug = match.group(1)
            # Filter out game IDs (typically 8 chars) and common non-tournament paths
            excluded = ['game', 'study', 'editor', 'analysis', 'training', 'learn', 'tv', 'api']
            if len(potential_slug) > 10 and potential_slug not in excluded:
                slug = potential_slug
    
    if not slug:
        return None
    
    # Convert slug to title
    # Replace -- with special marker, then process
    slug = slug.replace('--', '|||')  # Preserve double dashes as separators
    
    # Split by single dash
    words = slug.split('-')
    
    formatted_words = []
    for word in words:
        # Restore double-dash words (they become separate logical parts)
        word = word.replace('|||', ' ')
        
        if not word:
            continue
        
        # Handle special acronyms
        acronyms = ['fide', 'usa', 'us', 'gm', 'im', 'fm', 'wgm', 'wim']
        if word.lower() in acronyms:
            formatted_words.append(word.upper())
        # Numbers stay as-is
        elif word.isdigit():
            formatted_words.append(word)
        # Short words (2-3 chars) that aren't common words get uppercased
        elif len(word) <= 2 and word.lower() not in ['di', 'de', 'la', 'le', 'a', 'e', 'i', 'o', 'u']:
            formatted_words.append(word.upper())
        else:
            formatted_words.append(word.capitalize())
    
    return ' '.join(formatted_words) if formatted_words else None


def load_tournament_data():
    """Load tournament data from aggregated_game_data*.csv files in subfolders.
    
    Games are grouped by tournament name. Tournament names are extracted:
    1. From Site URL if Event looks like a round pairing (e.g., "Round 1: Player1 - Player2")
    2. From Event column if it looks like a proper tournament name
    3. From folder name as fallback
    """
    tournaments = {}
    
    # Map directory to time control
    time_control_dirs = {
        'classical': CLASSICAL_DIR,
        'rapid': RAPID_DIR,
        'blitz': BLITZ_DIR
    }
    
    for time_control, stats_dir in time_control_dirs.items():
        if not stats_dir.exists():
            print(f"Note: {stats_dir} not found, skipping {time_control}")
            continue
        
        # Find all aggregated_game_data CSV files recursively
        csv_files = find_csv_files(stats_dir, "aggregated_game_data")
        print(f"Found {len(csv_files)} aggregated_game_data files in {time_control.capitalize()} directory")
        
        for csv_path in csv_files:
            try:
                folder_name = csv_path.parent.name  # Fallback tournament name
                
                # First pass: Read all rows and group by tournament
                # Key: tournament_name -> list of game rows
                tournament_games = defaultdict(list)
                
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        event = row.get('Event', '')
                        site = row.get('Site', '')
                        
                        # Determine tournament name for this row
                        if event and is_round_pairing(event):
                            # Event is a round pairing - extract from Site URL
                            tournament_name = extract_tournament_from_url(site)
                            if not tournament_name:
                                tournament_name = format_tournament_name(folder_name)  # Fallback with formatting
                        elif event:
                            # Event looks like a proper tournament name
                            tournament_name = event
                        else:
                            tournament_name = format_tournament_name(folder_name)
                        
                        tournament_games[tournament_name].append(row)
                
                print(f"  Found {len(tournament_games)} unique tournaments in {csv_path.name}")
                
                # Second pass: Process each tournament group
                for tournament_name, rows in tournament_games.items():
                    # Infer time control from tournament name ONLY if unambiguous
                    # If name contains BOTH "blitz" and "rapid", use directory-based time control
                    actual_time_control = time_control  # Default to directory
                    name_lower = tournament_name.lower()
                    has_blitz = 'blitz' in name_lower
                    has_rapid = 'rapid' in name_lower
                    
                    # Only override if exactly one time control keyword is found
                    if has_blitz and not has_rapid:
                        actual_time_control = 'blitz'
                    elif has_rapid and not has_blitz:
                        actual_time_control = 'rapid'
                    # If both or neither keyword found, keep directory-based time control
                    
                    # Create tournament ID from name
                    tournament_id = tournament_name.lower().replace(' ', '-').replace('_', '-')
                    # Add time control suffix to avoid collisions
                    full_tournament_id = f"{tournament_id}-{actual_time_control}"
                    
                    games_list = []
                    player_stats = defaultdict(lambda: {
                        'games': 0, 'score': 0, 'elo': 0, 'gi_sum': 0, 'mp_sum': 0,
                        'opp_elo_sum': 0, 'wins': 0, 'draws': 0, 'losses': 0,
                        # White/Black specific tracking
                        'white_games': 0, 'black_games': 0,
                        'white_gi_sum': 0, 'black_gi_sum': 0,
                        'white_mp_sum': 0, 'black_mp_sum': 0
                    })
                    
                    total_moves = 0
                    first_date = None
                    first_site = None
                    
                    for row in rows:
                        white = row.get('White', '')
                        black = row.get('Black', '')
                        white_result = safe_float(row.get('WhiteResult', 0))
                        black_result = safe_float(row.get('BlackResult', 0))
                        white_elo = safe_int(row.get('WhiteElo', 0))
                        black_elo = safe_int(row.get('BlackElo', 0))
                        white_gi = safe_float(row.get('white_gi', 0))
                        black_gi = safe_float(row.get('black_gi', 0))
                        white_mp = safe_float(row.get('white_missed_points', 0))
                        black_mp = safe_float(row.get('black_missed_points', 0))
                        round_num = row.get('Round', '')
                        white_moves = safe_int(row.get('white_move_number', 0))
                        black_moves = safe_int(row.get('black_move_number', 0))
                        total_moves += white_moves + black_moves
                        
                        if not first_site:
                            first_site = row.get('Site', '')
                        if not first_date:
                            first_date = row.get('Date', '')
                        
                        # Result string
                        if white_result == 1:
                            result = "1-0"
                        elif black_result == 1:
                            result = "0-1"
                        else:
                            result = "½-½"
                        
                        games_list.append({
                            'white': white,
                            'black': black,
                            'whiteElo': white_elo,
                            'blackElo': black_elo,
                            'whiteGi': white_gi,
                            'blackGi': black_gi,
                            'whiteMp': white_mp,
                            'blackMp': black_mp,
                            'result': result,
                            'round': round_num,
                            'date': first_date
                        })
                        
                        # Update player stats
                        if white:
                            player_stats[white]['games'] += 1
                            player_stats[white]['score'] += white_result
                            player_stats[white]['elo'] = max(player_stats[white]['elo'], white_elo)
                            player_stats[white]['gi_sum'] += white_gi
                            player_stats[white]['mp_sum'] += white_mp
                            player_stats[white]['opp_elo_sum'] += black_elo
                            # White-specific stats
                            player_stats[white]['white_games'] += 1
                            player_stats[white]['white_gi_sum'] += white_gi
                            player_stats[white]['white_mp_sum'] += white_mp
                            if white_result == 1.0:
                                player_stats[white]['wins'] += 1
                            elif white_result == 0.5:
                                player_stats[white]['draws'] += 1
                            else:
                                player_stats[white]['losses'] += 1
                        
                        if black:
                            player_stats[black]['games'] += 1
                            player_stats[black]['score'] += black_result
                            player_stats[black]['elo'] = max(player_stats[black]['elo'], black_elo)
                            player_stats[black]['gi_sum'] += black_gi
                            player_stats[black]['mp_sum'] += black_mp
                            player_stats[black]['opp_elo_sum'] += white_elo
                            # Black-specific stats
                            player_stats[black]['black_games'] += 1
                            player_stats[black]['black_gi_sum'] += black_gi
                            player_stats[black]['black_mp_sum'] += black_mp
                            if black_result == 1.0:
                                player_stats[black]['wins'] += 1
                            elif black_result == 0.5:
                                player_stats[black]['draws'] += 1
                            else:
                                player_stats[black]['losses'] += 1
                    
                    # Calculate TPR for each player
                    player_stats_list = []
                    for name, stats in player_stats.items():
                        if stats['games'] > 0:
                            avg_opp_elo = stats['opp_elo_sum'] / stats['games']
                            avg_gi = stats['gi_sum'] / stats['games']
                            avg_mp = stats['mp_sum'] / stats['games']
                            
                            # Calculate white/black specific averages
                            white_games = stats['white_games']
                            black_games = stats['black_games']
                            avg_gi_white = stats['white_gi_sum'] / white_games if white_games > 0 else 0
                            avg_gi_black = stats['black_gi_sum'] / black_games if black_games > 0 else 0
                            avg_mp_white = stats['white_mp_sum'] / white_games if white_games > 0 else 0
                            avg_mp_black = stats['black_mp_sum'] / black_games if black_games > 0 else 0
                            
                            # Calculate TPR
                            tpr = 0
                            if optimize_w and calculate_EPR and adjust_mn:
                                try:
                                    m, n = adjust_mn(stats['score'], stats['games'])
                                    w_star = optimize_w(m, n, 0.75)
                                    tpr = calculate_EPR(w_star, avg_opp_elo)
                                except:
                                    tpr = avg_opp_elo  # Fallback
                            else:
                                # Simple TPR approximation with CPR for perfect/zero scores
                                m, n = stats['score'], stats['games']
                                if m == 0 or m == n:
                                    tpr = avg_opp_elo - ((n + 1) / n) * 400 * math.log10((n + 0.5 - m) / (m + 0.5))
                                else:
                                    tpr = avg_opp_elo + 400 * math.log10(m / (n - m))
                            
                            player_stats_list.append({
                                'name': name,
                                'games': stats['games'],
                                'score': stats['score'],
                                'elo': stats['elo'],
                                'avgGi': avg_gi,
                                'avgMp': avg_mp,
                                'tpr': tpr,
                                'wins': stats['wins'],
                                'draws': stats['draws'],
                                'losses': stats['losses'],
                                # White/Black specific stats
                                'whiteGames': white_games,
                                'blackGames': black_games,
                                'avgGiWhite': avg_gi_white,
                                'avgGiBlack': avg_gi_black,
                                'avgMpWhite': avg_mp_white,
                                'avgMpBlack': avg_mp_black
                            })
                    
                    # Sort by score
                    player_stats_list.sort(key=lambda x: (-x['score'], -x['tpr']))
                    
                    # Calculate summary statistics
                    summary_stats = calculate_tournament_summary_stats(player_stats_list, games_list)
                    
                    # Calculate rounds as max games played by any player
                    max_games = max((stats['games'] for stats in player_stats.values()), default=0)
                    
                    tournaments[full_tournament_id] = {
                        'id': full_tournament_id,
                        'name': tournament_name,
                        'date': first_date,
                        'games': len(games_list),
                        'totalMoves': total_moves,
                        'players': len(player_stats),
                        'rounds': max_games,
                        'playerStats': player_stats_list,
                        'gamesList': games_list,
                        'timeControl': actual_time_control,
                        'summaryStats': summary_stats
                    }
                    
                    print(f"    - {tournament_name}: {len(games_list)} games, {len(player_stats)} players")
                
            except Exception as e:
                print(f"Warning: Error processing {csv_path.name}: {e}")
                import traceback
                traceback.print_exc()
                continue
    
    print(f"Processed {len(tournaments)} total tournaments")
    return tournaments


def generate_tpr_year_data(tournaments):
    """Generate TPR by year data from tournament data."""
    tpr_year = []
    
    for tournament_id, tournament in tournaments.items():
        # Extract year from date or tournament name
        year = None
        if tournament.get('date'):
            try:
                year = int(tournament['date'].split('.')[0])
            except:
                pass
        
        if not year:
            # Try to extract from tournament name/id
            for part in tournament_id.split('-'):
                if part.isdigit() and len(part) == 4:
                    year = int(part)
                    break
        
        if not year:
            year = 2025  # Default
        
        for player in tournament.get('playerStats', []):
            if player['games'] >= 3 and player.get('tpr'):
                tpr_year.append({
                    'player': player['name'],
                    'tournament': tournament['name'],
                    'tournamentId': tournament_id,
                    'year': year,
                    'tpr': player['tpr'],
                    'games': player['games'],
                    'score': player['score'],
                    'timeControl': tournament.get('timeControl', 'classical')
                })
    
    # Sort by TPR descending
    tpr_year.sort(key=lambda x: -x['tpr'])
    
    return tpr_year


def generate_yearly_tpr_data(tournaments):
    """Generate yearly aggregate TPR data - TPR from all games played in a year per player, separated by time control."""
    from collections import defaultdict
    
    # Aggregate player data by year and time control
    # Key: (year, timeControl) -> player_name -> stats
    yearly_player_data = defaultdict(lambda: defaultdict(lambda: {
        'games': 0, 'score': 0, 'opp_elo_sum': 0, 'tournaments': set()
    }))
    
    for tournament_id, tournament in tournaments.items():
        # Extract year
        year = None
        if tournament.get('date'):
            try:
                year = int(tournament['date'].split('.')[0])
            except:
                pass
        
        if not year:
            for part in tournament_id.split('-'):
                if part.isdigit() and len(part) == 4:
                    year = int(part)
                    break
        
        if not year:
            year = 2025
        
        time_control = tournament.get('timeControl', 'classical')
        
        # Aggregate each player's data for this year
        for player in tournament.get('playerStats', []):
            name = player['name']
            games = player['games']
            score = player['score']
            
            # Calculate avg opponent elo for this tournament
            # We stored opp_elo_sum in player stats, so avg * games = sum
            # But we only have tpr and games, so we need to estimate
            # Use games list data instead
            pass
        
        # Use games list for more accurate data
        for game in tournament.get('gamesList', []):
            white = game.get('white', '')
            black = game.get('black', '')
            white_elo = game.get('whiteElo', 0)
            black_elo = game.get('blackElo', 0)
            
            # Determine result
            result_str = game.get('result', '')
            if result_str == '1-0':
                white_result, black_result = 1, 0
            elif result_str == '0-1':
                white_result, black_result = 0, 1
            else:
                white_result, black_result = 0.5, 0.5
            
            # Key is (year, timeControl)
            key = (year, time_control)
            
            if white and black_elo > 0:
                yearly_player_data[key][white]['games'] += 1
                yearly_player_data[key][white]['score'] += white_result
                yearly_player_data[key][white]['opp_elo_sum'] += black_elo
                yearly_player_data[key][white]['tournaments'].add(tournament_id)
            
            if black and white_elo > 0:
                yearly_player_data[key][black]['games'] += 1
                yearly_player_data[key][black]['score'] += black_result
                yearly_player_data[key][black]['opp_elo_sum'] += white_elo
                yearly_player_data[key][black]['tournaments'].add(tournament_id)
    
    # Calculate TPR for each player/year/timeControl combination
    yearly_tpr = []
    
    for (year, time_control), players in yearly_player_data.items():
        for player_name, data in players.items():
            if data['games'] >= 5:  # Minimum games filter
                avg_opp_elo = data['opp_elo_sum'] / data['games']
                
                # Calculate TPR
                tpr = 0
                if optimize_w and calculate_EPR and adjust_mn:
                    try:
                        m, n = adjust_mn(data['score'], data['games'])
                        w_star = optimize_w(m, n, 0.75)
                        tpr = calculate_EPR(w_star, avg_opp_elo)
                    except:
                        tpr = avg_opp_elo
                else:
                    # Simple TPR approximation with CPR for perfect/zero scores
                    m, n = data['score'], data['games']
                    if m == 0 or m == n:
                        # Use CPR formula for perfect/zero scores
                        tpr = avg_opp_elo - ((n + 1) / n) * 400 * math.log10((n + 0.5 - m) / (m + 0.5))
                    else:
                        tpr = avg_opp_elo + 400 * math.log10(m / (n - m))
                
                yearly_tpr.append({
                    'player': player_name,
                    'year': year,
                    'tpr': tpr,
                    'games': data['games'],
                    'score': data['score'],
                    'tournaments': len(data['tournaments']),
                    'timeControl': time_control
                })
    
    # Sort by TPR descending
    yearly_tpr.sort(key=lambda x: -x['tpr'])
    
    return yearly_tpr


def normalize_player_name(name):
    """Convert 'Last, First' format to 'First Last' format."""
    if name and ', ' in name:
        parts = name.split(', ')
        if len(parts) == 2:
            return parts[1] + ' ' + parts[0]
    return name


def build_player_tournaments(tournaments):
    """Build a mapping of player names to their tournament participation."""
    from collections import defaultdict
    
    player_tournaments = defaultdict(list)
    
    for tournament_id, tournament in tournaments.items():
        tournament_name = tournament.get('name', '')
        tournament_date = tournament.get('date', '')
        time_control = tournament.get('timeControl', 'classical')  # NEW: Get time control
        
        # Extract year from date, tournament name, or default to current year
        import re
        from datetime import datetime
        year = None
        # Try to get year from date (format: YYYY.MM.DD)
        if tournament_date and len(tournament_date) >= 4 and not tournament_date.startswith('????'):
            year = int(tournament_date[:4])
        # Try to get year from tournament name (e.g., "Norway Chess 2025")
        if not year:
            year_match = re.search(r'\b(20\d{2})\b', tournament_name)
            if year_match:
                year = int(year_match.group(1))
        # Default to current year if no year found
        if not year:
            year = datetime.now().year
        
        # Get all players from this tournament
        for player_stat in tournament.get('playerStats', []):
            player_name = player_stat['name']
            
            # Add tournament info to this player's list
            player_tournaments[player_name].append({
                'id': tournament_id,
                'name': tournament_name,
                'date': tournament_date,
                'year': year,
                'games': player_stat['games'],
                'score': player_stat['score'],
                'elo': player_stat.get('elo'),  # Include player's Elo for this tournament
                'tpr': round(player_stat['tpr']) if player_stat.get('tpr') else None,
                'avgGi': player_stat.get('avgGi'),
                'avgMp': player_stat.get('avgMp'),
                'timeControl': time_control,
                'wins': player_stat.get('wins', 0),
                'draws': player_stat.get('draws', 0),
                'losses': player_stat.get('losses', 0)
            })
    
    # Sort each player's tournaments by date (newest first)
    for player_name in player_tournaments:
        player_tournaments[player_name].sort(
            key=lambda x: x.get('date', ''), 
            reverse=True
        )
    
    return dict(player_tournaments)


def format_tournament_name(filename):
    """Convert filename to readable tournament name."""
    name = filename.replace('-', ' ').replace('_', ' ')
    # Capitalize words
    words = name.split()
    formatted = []
    for word in words:
        if word.isdigit():
            formatted.append(word)
        elif len(word) <= 3:
            formatted.append(word.upper())
        else:
            formatted.append(word.capitalize())
    return ' '.join(formatted)


def safe_float(value):
    """Safely convert value to float."""
    try:
        return float(value) if value and value != '' else 0
    except (ValueError, TypeError):
        return 0


def safe_int(value):
    """Safely convert value to int."""
    try:
        return int(float(value)) if value and value != '' else 0
    except (ValueError, TypeError):
        return 0


def write_js_data(filename, var_name, data):
    """Write data as JavaScript variable to file."""
    output_path = DATA_OUTPUT_DIR / filename
    
    # Ensure directory exists
    DATA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Write JavaScript file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"// Auto-generated by build_site.py\n")
        f.write(f"const {var_name} = ")
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write(";\n")
    
    print(f"Generated {output_path}")


def main():
    """Main build function."""
    print("=" * 50)
    print("Building Free Chess Stats Database")
    print("=" * 50)
    
    # Load data
    players = load_player_stats()
    tournaments = load_tournament_data()
    
    # Build player tournament participation data
    player_tournaments = build_player_tournaments(tournaments)
    
    # Add tournament participation to player data
    for player in players:
        player_name = player['name']
        # Also try normalized name for matching
        player['tournaments'] = player_tournaments.get(player_name, [])
        
        # If no match, try to find with normalized name
        if not player['tournaments']:
            # Try matching with "First Last" vs "Last, First" variations
            for key in player_tournaments:
                # Normalize both and compare
                if normalize_player_name(key) == player_name or key == player_name:
                    player['tournaments'] = player_tournaments[key]
                    break
        
        # Recalculate weighted averages from tournament data
        if player['tournaments']:
            total_games = 0
            gi_weighted_sum = 0
            mp_weighted_sum = 0
            for t in player['tournaments']:
                games = t.get('games', 0)
                total_games += games
                if t.get('avgGi') is not None:
                    gi_weighted_sum += t['avgGi'] * games
                if t.get('avgMp') is not None:
                    mp_weighted_sum += t['avgMp'] * games
            
            if total_games > 0:
                player['avgGi'] = gi_weighted_sum / total_games
                player['avgMissedPoints'] = mp_weighted_sum / total_games
                player['games'] = total_games
                # Recalculate total points from tournaments
                player['points'] = sum(t.get('score', 0) for t in player['tournaments'])
    
    # Generate TPR data (per-tournament performances)
    tpr_year = generate_tpr_year_data(tournaments)
    
    # Generate yearly aggregate TPR data (all games in a year)
    yearly_tpr = generate_yearly_tpr_data(tournaments)
    
    # Convert tournaments dict to list for JS
    tournaments_list = list(tournaments.values())
    # Sort by number of games (most games first)
    tournaments_list.sort(key=lambda x: -x['games'])
    
    # Write JavaScript data files
    write_js_data('players.js', 'playersData', players)
    write_js_data('tournaments.js', 'tournamentsData', tournaments_list)
    write_js_data('tpr_year.js', 'tprYearData', tpr_year)
    write_js_data('yearly_tpr.js', 'yearlyTprData', yearly_tpr)
    
    print("=" * 50)
    print("Build complete!")
    print(f"  Players: {len(players)}")
    print(f"  Tournaments: {len(tournaments_list)}")
    print(f"  Best performances: {len(tpr_year)}")
    print(f"  Yearly TPR entries: {len(yearly_tpr)}")
    print("=" * 50)


if __name__ == "__main__":
    main()
