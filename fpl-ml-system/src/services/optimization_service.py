"""Optimization service using PuLP for FPL team selection and transfers."""

import logging
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime

from pulp import LpMaximize, LpProblem, LpVariable, lpSum, LpStatus, value
from flask import current_app

from ..models.db_models import db, Player, Team, PlayerPrediction
from ..models.data_models import OptimizedTeam, TransferSuggestion


logger = logging.getLogger(__name__)


class OptimizationService:
    """Service for team optimization using linear programming."""
    
    def __init__(self, app=None):
        """Initialize optimization service."""
        self.app = app
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the optimization service with Flask app."""
        self.app = app
    
    def optimize_team(self, 
                     budget: float = 100.0,
                     formation: Optional[str] = None,
                     preferred_players: Optional[List[int]] = None,
                     excluded_players: Optional[List[int]] = None,
                     max_players_per_team: int = 3,
                     existing_team: Optional[List[int]] = None,
                     transfer_limit: int = 1) -> Dict:
        """
        Optimize FPL team selection using linear programming.
        
        Args:
            budget: Total budget in millions (default: 100.0)
            formation: Formation string like "3-5-2" (optional)
            preferred_players: List of player IDs to prioritize
            excluded_players: List of player IDs to exclude
            max_players_per_team: Maximum players from same team
            existing_team: Current team for transfer optimization
            transfer_limit: Maximum number of transfers allowed
            
        Returns:
            Dict with optimized team and metadata
        """
        logger.info(f"Starting team optimization with budget £{budget}M")
        
        try:
            # Get player predictions and data
            player_data = self._get_player_data_for_optimization(excluded_players)
            
            if not player_data:
                raise ValueError("No player data available for optimization")
            
            # Create optimization problem
            prob = LpProblem("FPL_Team_Optimization", LpMaximize)
            
            # Extract player info
            player_ids = list(player_data.keys())
            player_predictions = {pid: data['expected_points'] for pid, data in player_data.items()}
            player_costs = {pid: data['cost'] for pid, data in player_data.items()}
            player_positions = {pid: data['position'] for pid, data in player_data.items()}
            player_teams = {pid: data['team_id'] for pid, data in player_data.items()}
            
            # Decision variables - binary selection for each player
            players_selected = LpVariable.dicts("player", player_ids, cat='Binary')
            
            # Objective function: Maximize expected points
            prob += lpSum([
                player_predictions[pid] * players_selected[pid] 
                for pid in player_ids
            ])
            
            # Budget constraint
            prob += lpSum([
                player_costs[pid] * players_selected[pid] 
                for pid in player_ids
            ]) <= budget
            
            # Formation constraints
            formation_constraints = self._get_formation_constraints(formation)
            
            for position, count in formation_constraints.items():
                position_players = [pid for pid, pos in player_positions.items() if pos == position]
                prob += lpSum([
                    players_selected[pid] for pid in position_players
                ]) == count
            
            # Team constraint (max players per team)
            team_ids = set(player_teams.values())
            for team_id in team_ids:
                team_players = [pid for pid, tid in player_teams.items() if tid == team_id]
                prob += lpSum([
                    players_selected[pid] for pid in team_players
                ]) <= max_players_per_team
            
            # Preferred players constraint (hard constraint - must include)
            if preferred_players:
                logger.info(f"Adding preferred players constraint: {preferred_players}")
                for pid in preferred_players:
                    if pid in players_selected:
                        # Force selection of preferred players
                        prob += players_selected[pid] == 1
                        logger.info(f"Forced selection of preferred player ID: {pid}")
            
            # Transfer constraints if optimizing existing team
            if existing_team and transfer_limit > 0:
                # Transfer variables
                transfers_out = LpVariable.dicts("transfer_out", existing_team, cat='Binary')
                
                # Link transfers to player selection
                for pid in existing_team:
                    if pid in players_selected:
                        # If player was in team but not selected, it's a transfer out
                        prob += transfers_out[pid] >= 1 - players_selected[pid]
                        prob += transfers_out[pid] <= 1 - players_selected[pid]
                
                # Transfer limit constraint
                prob += lpSum([transfers_out[pid] for pid in existing_team]) <= transfer_limit
            
            # Solve the optimization problem
            prob.solve()
            
            # Check if solution is optimal
            if LpStatus[prob.status] != 'Optimal':
                logger.warning(f"Optimization status: {LpStatus[prob.status]}")
                if LpStatus[prob.status] == 'Infeasible':
                    raise ValueError("No feasible solution found with given constraints")
            
            # Extract solution
            selected_players = [
                pid for pid in player_ids 
                if players_selected[pid].value() == 1
            ]
            
            # Always expect 15 players (full FPL squad)
            if len(selected_players) != 15:
                raise ValueError(f"Invalid team size: {len(selected_players)} players selected (expected 15)")
            
            # Calculate team statistics
            total_cost = sum(player_costs[pid] for pid in selected_players)
            expected_points = sum(player_predictions[pid] for pid in selected_players)
            
            # Select Starting XI from the 15-player squad based on formation
            starting_xi = self._select_starting_xi(
                selected_players, formation, player_predictions, player_positions, preferred_players
            )
            
            # Select captain and vice-captain from Starting XI (highest expected points)
            captain_candidates = sorted(
                starting_xi,
                key=lambda pid: player_predictions[pid],
                reverse=True
            )
            captain_id = captain_candidates[0]
            vice_captain_id = captain_candidates[1]
            
            # Calculate starting XI expected points (this is what matters for scoring)
            starting_xi_points = sum(player_predictions[pid] for pid in starting_xi)
            
            # Get bench players (squad - starting XI)
            bench_players = [pid for pid in selected_players if pid not in starting_xi]
            
            # Validate formation for starting XI
            actual_formation = self._validate_team_formation(starting_xi, player_positions)
            
            result = {
                'players': selected_players,  # Full 15-player squad
                'starting_xi': starting_xi,   # 11 best players in formation
                'bench': bench_players,       # 4 substitute players  
                'captain_id': captain_id,
                'vice_captain_id': vice_captain_id,
                'total_cost': round(total_cost, 1),
                'expected_points': round(starting_xi_points, 2),  # Only starting XI counts for points
                'squad_expected_points': round(expected_points, 2),  # Total squad potential
                'formation': actual_formation,
                'budget_remaining': round(budget - total_cost, 1),
                'optimization_status': LpStatus[prob.status],
                'solver_time': getattr(prob, 'solutionTime', 0),
                'objective_value': value(prob.objective)
            }
            
            # Add transfer information if applicable
            if existing_team:
                transfers_in = [pid for pid in selected_players if pid not in existing_team]
                transfers_out = [pid for pid in existing_team if pid not in selected_players]
                
                result.update({
                    'transfers_in': transfers_in,
                    'transfers_out': transfers_out,
                    'transfer_count': len(transfers_out)
                })
            
            logger.info(f"Optimization completed: {len(selected_players)} players, "
                       f"£{total_cost:.1f}M, {expected_points:.2f} points")
            
            return result
            
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            raise
    
    def _get_player_data_for_optimization(self, excluded_players: Optional[List[int]] = None) -> Dict:
        """Get player data needed for optimization."""
        query = db.session.query(
            Player.player_id,
            Player.web_name,
            Player.position,
            Player.now_cost,
            Player.team_id,
            Player.status,
            PlayerPrediction.expected_points
        ).join(
            PlayerPrediction, 
            Player.player_id == PlayerPrediction.player_id,
            isouter=True
        ).filter(
            Player.status == 'a'  # Available players only
        )
        
        # Exclude specific players if requested
        if excluded_players:
            query = query.filter(~Player.player_id.in_(excluded_players))
        
        results = query.all()
        
        player_data = {}
        for row in results:
            # Use predicted points or fallback to form-based estimate
            expected_points = row.expected_points
            if expected_points is None:
                # Fallback: estimate based on total points and cost
                expected_points = self._estimate_expected_points(row)
            
            player_data[row.player_id] = {
                'web_name': row.web_name,
                'position': row.position,
                'cost': row.now_cost / 10.0,  # Convert from tenths to millions
                'team_id': row.team_id,
                'expected_points': expected_points,
                'status': row.status
            }
        
        logger.info(f"Retrieved data for {len(player_data)} players")
        return player_data
    
    def _estimate_expected_points(self, player_row) -> float:
        """Estimate expected points when prediction is not available using realistic FPL scoring."""
        from ..models.db_models import Player
        
        # Get the actual player object to access form and total_points
        player = Player.query.get(player_row.player_id)
        if not player:
            return 2.0
            
        # Base points by position (realistic FPL averages)
        position_base = {
            'GKP': 4.0,  # Keepers get clean sheet points
            'DEF': 4.5,  # Defenders get clean sheet + attacking returns  
            'MID': 5.5,  # Midfielders get goals/assists
            'FWD': 6.0   # Forwards get most goals
        }.get(player.position, 4.0)
        
        # Form factor (recent performance)
        form_score = float(player.form or 0)
        if form_score > 7.0:
            form_multiplier = 1.4  # Excellent form
        elif form_score > 5.0:
            form_multiplier = 1.2  # Good form  
        elif form_score > 3.0:
            form_multiplier = 1.0  # Average form
        else:
            form_multiplier = 0.7  # Poor form
            
        # Total points factor (season performance)
        total_points = player.total_points or 0
        if total_points > 200:
            points_multiplier = 1.5  # Elite performers
        elif total_points > 150:
            points_multiplier = 1.3  # Very good
        elif total_points > 100:
            points_multiplier = 1.1  # Good
        elif total_points > 50:
            points_multiplier = 0.9  # Average
        else:
            points_multiplier = 0.6  # Poor/new players
            
        # Cost factor (expensive players should deliver more)
        cost = player.now_cost / 10.0  # Convert to millions
        if cost >= 12.0:
            cost_multiplier = 1.3  # Premium players
        elif cost >= 8.0:
            cost_multiplier = 1.1  # Mid-price
        elif cost >= 5.0:
            cost_multiplier = 1.0  # Budget
        else:
            cost_multiplier = 0.8  # Cheap players
            
        # Calculate final expected points
        expected = position_base * form_multiplier * points_multiplier * cost_multiplier
        
        # Ensure reasonable range (1-15 points per gameweek)
        return max(1.0, min(15.0, round(expected, 1)))
    
    def _select_starting_xi(self, squad_players: List[int], formation: Optional[str], 
                           player_predictions: Dict[int, float], 
                           player_positions: Dict[int, str], 
                           preferred_players: Optional[List[int]] = None) -> List[int]:
        """Select the best 11 players from 15-player squad based on formation."""
        
        # Parse formation or use default
        if formation:
            try:
                parts = formation.split('-')
                if len(parts) == 3:
                    formation_needs = {
                        'GKP': 1,
                        'DEF': int(parts[0]),
                        'MID': int(parts[1]),
                        'FWD': int(parts[2])
                    }
                else:
                    raise ValueError("Invalid formation")
            except (ValueError, IndexError):
                logger.warning(f"Invalid formation {formation}, using 3-4-3")
                formation_needs = {'GKP': 1, 'DEF': 3, 'MID': 4, 'FWD': 3}
        else:
            formation_needs = {'GKP': 1, 'DEF': 3, 'MID': 4, 'FWD': 3}  # Default 3-4-3
        
        # Group players by position
        players_by_position = {'GKP': [], 'DEF': [], 'MID': [], 'FWD': []}
        for player_id in squad_players:
            position = player_positions[player_id]
            players_by_position[position].append(player_id)
        
        # Sort each position by expected points, but prioritize preferred players
        for position in players_by_position:
            def sort_key(pid):
                base_score = player_predictions[pid]
                # Add huge bonus to preferred players to ensure they're selected first
                if preferred_players and pid in preferred_players:
                    return base_score + 100.0  # Very high bonus
                return base_score
                
            players_by_position[position].sort(
                key=sort_key, 
                reverse=True
            )
        
        # Select best players for each position according to formation
        starting_xi = []
        for position, needed_count in formation_needs.items():
            available_players = players_by_position[position]
            if len(available_players) < needed_count:
                raise ValueError(f"Not enough {position} players in squad: need {needed_count}, have {len(available_players)}")
            
            # Take the best players for this position
            selected = available_players[:needed_count]
            starting_xi.extend(selected)
        
        return starting_xi
    
    def _get_formation_constraints(self, formation: Optional[str] = None) -> Dict[str, int]:
        """Get formation constraints for optimization."""
        # Always use full squad constraints (15 players total) - FPL rules
        # 2 GKP, 5 DEF, 5 MID, 3 FWD = 15 players total
        return current_app.config.get('FORMATION_CONSTRAINTS', {
            'GKP': 2,
            'DEF': 5,
            'MID': 5,
            'FWD': 3
        })
    
    def _validate_team_formation(self, selected_players: List[int], 
                                player_positions: Dict[int, str]) -> Dict[str, int]:
        """Validate and return actual team formation."""
        formation_count = {'GKP': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
        
        for player_id in selected_players:
            position = player_positions.get(player_id, 'UNK')
            if position in formation_count:
                formation_count[position] += 1
        
        return formation_count
    
    def suggest_transfers(self, 
                         current_team: List[int],
                         budget_available: float = 0.0,
                         transfer_limit: int = 1,
                         min_improvement: float = 0.1) -> List[TransferSuggestion]:
        """
        Suggest optimal transfers for current team.
        
        Args:
            current_team: Current 15 player IDs
            budget_available: Extra budget available for transfers
            transfer_limit: Maximum number of transfers
            min_improvement: Minimum expected points improvement
            
        Returns:
            List of transfer suggestions
        """
        logger.info(f"Analyzing transfer suggestions for team of {len(current_team)} players")
        
        try:
            # Get current team data
            current_data = self._get_player_data_for_optimization()
            current_predictions = {
                pid: current_data[pid]['expected_points'] 
                for pid in current_team if pid in current_data
            }
            current_costs = {
                pid: current_data[pid]['cost'] 
                for pid in current_team if pid in current_data
            }
            current_positions = {
                pid: current_data[pid]['position'] 
                for pid in current_team if pid in current_data
            }
            
            # Calculate current team value
            current_value = sum(current_costs[pid] for pid in current_team if pid in current_costs)
            available_budget = current_value + budget_available
            
            suggestions = []
            
            # Analyze each position for potential improvements
            for position in ['GKP', 'DEF', 'MID', 'FWD']:
                position_players = [
                    pid for pid in current_team 
                    if current_positions.get(pid) == position
                ]
                
                for current_player_id in position_players:
                    if current_player_id not in current_predictions:
                        continue
                    
                    current_points = current_predictions[current_player_id]
                    current_cost = current_costs[current_player_id]
                    
                    # Find better alternatives
                    alternatives = self._find_position_alternatives(
                        position, current_cost, available_budget, 
                        excluded_players=[current_player_id] + [pid for pid in current_team if pid != current_player_id]
                    )
                    
                    for alt_player_id, alt_data in alternatives.items():
                        expected_improvement = alt_data['expected_points'] - current_points
                        cost_change = alt_data['cost'] - current_cost
                        
                        if (expected_improvement >= min_improvement and 
                            cost_change <= budget_available):
                            
                            # Create transfer suggestion
                            current_player = Player.query.get(current_player_id)
                            alt_player = Player.query.get(alt_player_id)
                            
                            if current_player and alt_player:
                                suggestion = TransferSuggestion(
                                    player_out=self._player_to_stats(current_player, current_points),
                                    player_in=self._player_to_stats(alt_player, alt_data['expected_points']),
                                    cost_change=cost_change,
                                    expected_points_gain=expected_improvement,
                                    reasoning="",  # Will be filled by reasoning service
                                    confidence_score=min(1.0, expected_improvement / 5.0)
                                )
                                suggestions.append(suggestion)
            
            # Sort by expected points gain
            suggestions.sort(key=lambda x: x.expected_points_gain, reverse=True)
            
            # Limit to top suggestions
            suggestions = suggestions[:transfer_limit * 3]  # Show multiple options per transfer slot
            
            logger.info(f"Generated {len(suggestions)} transfer suggestions")
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating transfer suggestions: {e}")
            return []
    
    def _find_position_alternatives(self, position: str, current_cost: float, 
                                  max_budget: float, excluded_players: List[int]) -> Dict:
        """Find alternative players for a given position."""
        query = db.session.query(
            Player.player_id,
            Player.web_name,
            Player.now_cost,
            PlayerPrediction.expected_points
        ).join(
            PlayerPrediction, Player.player_id == PlayerPrediction.player_id
        ).filter(
            Player.position == position,
            Player.status == 'a',
            ~Player.player_id.in_(excluded_players),
            Player.now_cost / 10.0 <= max_budget
        ).order_by(
            PlayerPrediction.expected_points.desc()
        ).limit(10)  # Top 10 alternatives
        
        alternatives = {}
        for row in query.all():
            alternatives[row.player_id] = {
                'web_name': row.web_name,
                'cost': row.now_cost / 10.0,
                'expected_points': row.expected_points or 0
            }
        
        return alternatives
    
    def _player_to_stats(self, player: Player, expected_points: float):
        """Convert Player model to PlayerStats for Pydantic model."""
        from ..models.data_models import PlayerStats
        
        return PlayerStats(
            player_id=player.player_id,
            web_name=player.web_name,
            position=player.position,
            team_id=player.team_id,
            now_cost=player.now_cost / 10.0,
            expected_points=expected_points,
            form=float(player.form or 0),
            total_points=player.total_points,
            points_per_game=float(player.points_per_game or 0)
        )
    
    def suggest_captain(self, team_players: List[int], 
                       fixture_context: Optional[Dict] = None) -> Dict:
        """
        Suggest captain and vice-captain from team players.
        
        Args:
            team_players: List of 15 player IDs in the team
            fixture_context: Optional fixture information for each player
            
        Returns:
            Dict with captain and vice-captain suggestions
        """
        logger.info(f"Analyzing captain suggestions for {len(team_players)} players")
        
        try:
            # Get player predictions
            player_predictions = {}
            
            query = db.session.query(
                Player.player_id,
                Player.web_name,
                Player.position,
                PlayerPrediction.expected_points
            ).join(
                PlayerPrediction, Player.player_id == PlayerPrediction.player_id
            ).filter(
                Player.player_id.in_(team_players)
            )
            
            for row in query.all():
                base_points = row.expected_points or 0
                
                # Apply fixture context if available
                if fixture_context and row.player_id in fixture_context:
                    context = fixture_context[row.player_id]
                    # Adjust for home/away and fixture difficulty
                    if context.get('is_home', True):
                        base_points *= 1.05  # Small home advantage
                    
                    fixture_difficulty = context.get('fixture_difficulty', 3)
                    difficulty_multiplier = 1 + (3 - fixture_difficulty) * 0.1  # Easier = higher multiplier
                    base_points *= difficulty_multiplier
                
                player_predictions[row.player_id] = {
                    'web_name': row.web_name,
                    'position': row.position,
                    'expected_points': base_points,
                    'captain_points': base_points * 2,  # Captain gets double points
                    'vice_captain_points': base_points  # Vice gets single (if captain doesn't play)
                }
            
            if not player_predictions:
                raise ValueError("No player predictions found for captain selection")
            
            # Sort by captain potential (double points)
            sorted_players = sorted(
                player_predictions.items(),
                key=lambda x: x[1]['captain_points'],
                reverse=True
            )
            
            captain_id, captain_data = sorted_players[0]
            vice_captain_id, vice_data = sorted_players[1] if len(sorted_players) > 1 else sorted_players[0]
            
            result = {
                'captain_id': captain_id,
                'captain_name': captain_data['web_name'],
                'captain_expected_points': round(captain_data['captain_points'], 2),
                'vice_captain_id': vice_captain_id,
                'vice_captain_name': vice_data['web_name'],
                'vice_captain_expected_points': round(vice_data['expected_points'], 2),
                'total_expected_captain_points': round(
                    captain_data['captain_points'] + vice_data['expected_points'], 2
                )
            }
            
            logger.info(f"Captain suggestion: {captain_data['web_name']} "
                       f"({captain_data['captain_points']:.2f} pts)")
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating captain suggestions: {e}")
            return {}
    
    def optimize_for_gameweek(self, gameweek: int, 
                            existing_team: Optional[List[int]] = None,
                            free_transfers: int = 1,
                            budget: float = 100.0) -> Dict:
        """
        Optimize team specifically for a gameweek.
        
        Args:
            gameweek: Target gameweek number
            existing_team: Current team if optimizing transfers
            free_transfers: Number of free transfers available
            budget: Available budget
            
        Returns:
            Gameweek-specific optimization result
        """
        logger.info(f"Optimizing team for gameweek {gameweek}")
        
        try:
            # Get fixture context for the gameweek
            fixture_context = self._get_gameweek_fixture_context(gameweek)
            
            # If we have an existing team, optimize transfers
            if existing_team:
                result = self.optimize_team(
                    budget=budget,
                    existing_team=existing_team,
                    transfer_limit=free_transfers
                )
            else:
                # Fresh team optimization
                result = self.optimize_team(budget=budget)
            
            # Add gameweek-specific captain suggestion
            if result.get('players'):
                captain_suggestion = self.suggest_captain(
                    result['players'], 
                    fixture_context
                )
                result.update(captain_suggestion)
            
            # Add fixture difficulty analysis
            result['gameweek'] = gameweek
            result['fixture_analysis'] = self._analyze_fixture_difficulty(
                result.get('players', []), fixture_context
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Gameweek optimization failed: {e}")
            raise
    
    def _get_gameweek_fixture_context(self, gameweek: int) -> Dict:
        """Get fixture context for players in a specific gameweek."""
        from ..models.db_models import Fixture
        
        fixtures = Fixture.query.filter_by(gameweek=gameweek).all()
        context = {}
        
        for fixture in fixtures:
            # Home team context
            home_players = Player.query.filter_by(team_id=fixture.home_team_id).all()
            for player in home_players:
                context[player.player_id] = {
                    'fixture_id': fixture.fixture_id,
                    'is_home': True,
                    'fixture_difficulty': fixture.home_difficulty or 3,
                    'opponent_team_id': fixture.away_team_id
                }
            
            # Away team context
            away_players = Player.query.filter_by(team_id=fixture.away_team_id).all()
            for player in away_players:
                context[player.player_id] = {
                    'fixture_id': fixture.fixture_id,
                    'is_home': False,
                    'fixture_difficulty': fixture.away_difficulty or 3,
                    'opponent_team_id': fixture.home_team_id
                }
        
        return context
    
    def optimize_for_multiple_gameweeks(self, 
                                      start_gameweek: int,
                                      gameweeks_ahead: int = 5,
                                      budget: float = 100.0,
                                      existing_team: Optional[List[int]] = None,
                                      formation: Optional[str] = None,
                                      preferred_players: Optional[List[int]] = None,
                                      excluded_players: Optional[List[int]] = None,
                                      max_players_per_team: int = 3) -> Dict:
        """
        Optimize team considering multiple gameweeks ahead for long-term planning.
        
        Args:
            start_gameweek: Starting gameweek number
            gameweeks_ahead: Number of gameweeks to look ahead (3, 5, 8)
            budget: Available budget
            existing_team: Current team if optimizing transfers  
            formation: Target formation
            preferred_players: Players to prioritize
            excluded_players: Players to exclude
            max_players_per_team: Max players per team
            
        Returns:
            Optimization result with multi-gameweek fixture analysis
        """
        logger.info(f"Multi-gameweek optimization: GW{start_gameweek} + {gameweeks_ahead} weeks ahead")
        
        try:
            # Get fixture contexts for multiple gameweeks
            multi_fixture_contexts = {}
            gameweek_range = list(range(start_gameweek, min(start_gameweek + gameweeks_ahead + 1, 39)))
            
            for gw in gameweek_range:
                multi_fixture_contexts[gw] = self._get_gameweek_fixture_context(gw)
            
            # Get enhanced player data with multi-gameweek scoring
            player_data = self._get_multi_gameweek_player_data(
                multi_fixture_contexts, excluded_players
            )
            
            if not player_data:
                raise ValueError("No player data available for multi-gameweek optimization")
                
            # Create optimization problem  
            prob = LpProblem("FPL_Multi_Gameweek_Optimization", LpMaximize)
            
            # Extract player info
            player_ids = list(player_data.keys())
            player_predictions = {pid: data['multi_gameweek_score'] for pid, data in player_data.items()}
            player_costs = {pid: data['cost'] for pid, data in player_data.items()}
            player_positions = {pid: data['position'] for pid, data in player_data.items()}
            player_teams = {pid: data['team_id'] for pid, data in player_data.items()}
            
            # Decision variables
            players_selected = LpVariable.dicts("player", player_ids, cat='Binary')
            
            # Objective function: Maximize multi-gameweek expected points
            prob += lpSum([
                player_predictions[pid] * players_selected[pid] 
                for pid in player_ids
            ])
            
            # Standard FPL constraints
            prob += lpSum([player_costs[pid] * players_selected[pid] for pid in player_ids]) <= budget
            
            # Formation constraints
            formation_constraints = self._get_formation_constraints(formation)
            for position, count in formation_constraints.items():
                position_players = [pid for pid, pos in player_positions.items() if pos == position]
                prob += lpSum([players_selected[pid] for pid in position_players]) == count
                
            # Team constraint
            team_ids = set(player_teams.values())
            for team_id in team_ids:
                team_players = [pid for pid, tid in player_teams.items() if tid == team_id]
                prob += lpSum([players_selected[pid] for pid in team_players]) <= max_players_per_team
                
            # Preferred players constraint
            if preferred_players:
                for pid in preferred_players:
                    if pid in players_selected:
                        prob += players_selected[pid] == 1
                        
            # Solve optimization
            prob.solve()
            
            if LpStatus[prob.status] != 'Optimal':
                if LpStatus[prob.status] == 'Infeasible':
                    raise ValueError("No feasible solution for multi-gameweek optimization")
                    
            # Extract solution
            selected_players = [pid for pid in player_ids if players_selected[pid].value() == 1]
            
            if len(selected_players) != 15:
                raise ValueError(f"Invalid team size: {len(selected_players)} players selected")
                
            # Calculate costs and points
            total_cost = sum(player_costs[pid] for pid in selected_players)
            multi_gw_points = sum(player_predictions[pid] for pid in selected_players)
            
            # Select Starting XI using single gameweek logic for current week
            current_gw_context = multi_fixture_contexts.get(start_gameweek, {})
            starting_xi = self._select_starting_xi(
                selected_players, formation, 
                {pid: player_data[pid]['current_gameweek_score'] for pid in selected_players},
                player_positions, preferred_players
            )
            
            # Captain selection for current gameweek
            captain_candidates = sorted(
                starting_xi,
                key=lambda pid: player_data[pid]['current_gameweek_score'],
                reverse=True
            )
            captain_id = captain_candidates[0]
            vice_captain_id = captain_candidates[1] if len(captain_candidates) > 1 else captain_candidates[0]
            
            # Calculate current gameweek points (for display)
            current_gw_points = sum(player_data[pid]['current_gameweek_score'] for pid in starting_xi)
            bench_players = [pid for pid in selected_players if pid not in starting_xi]
            
            # Multi-gameweek fixture analysis
            multi_fixture_analysis = self._analyze_multi_gameweek_fixtures(
                selected_players, multi_fixture_contexts, gameweek_range
            )
            
            result = {
                'players': selected_players,
                'starting_xi': starting_xi,
                'bench': bench_players,
                'captain_id': captain_id,
                'vice_captain_id': vice_captain_id,
                'total_cost': round(total_cost, 1),
                'expected_points': round(current_gw_points, 2),  # Current gameweek for display
                'multi_gameweek_points': round(multi_gw_points, 2),  # Total across all gameweeks
                'formation': self._validate_team_formation(starting_xi, player_positions),
                'budget_remaining': round(budget - total_cost, 1),
                'optimization_status': LpStatus[prob.status],
                'gameweek_range': gameweek_range,
                'gameweeks_ahead': gameweeks_ahead,
                'multi_gameweek_analysis': multi_fixture_analysis
            }
            
            logger.info(f"Multi-gameweek optimization completed: {len(selected_players)} players, "
                       f"Current GW: {current_gw_points:.1f} pts, Multi-GW: {multi_gw_points:.1f} pts")
            
            return result
            
        except Exception as e:
            logger.error(f"Multi-gameweek optimization failed: {e}")
            raise

    def suggest_free_transfers(self, 
                              current_team: List[int],
                              target_gameweek: int,
                              max_suggestions: int = 3,
                              budget_available: float = 0.0) -> Dict:
        """
        Suggest free transfers for the current team based on form, fixtures, and value.
        
        Args:
            current_team: List of current player IDs
            target_gameweek: Gameweek to optimize for
            max_suggestions: Maximum number of transfer suggestions
            budget_available: Available budget for transfers (ITB money)
        
        Returns:
            Dict with transfer suggestions and reasoning
        """
        logger.info(f"Generating free transfer suggestions for GW{target_gameweek}")
        
        try:
            # Get current team player data
            current_players_data = {}
            for player_id in current_team:
                player = Player.query.get(player_id)
                if player:
                    current_players_data[player_id] = {
                        'id': player.player_id,
                        'name': player.web_name,
                        'position': player.position,
                        'team_id': player.team_id,
                        'cost': player.now_cost / 10.0,
                        'form': float(player.form or 0),
                        'total_points': player.total_points,
                        'expected_points': self._calculate_player_expected_points(player, target_gameweek)
                    }
            
            # Get fixture context for target gameweek
            fixture_context = self._get_gameweek_fixture_context(target_gameweek)
            
            # Analyze current team weaknesses
            transfer_suggestions = []
            
            # Group players by position for targeted analysis
            positions = ['GKP', 'DEF', 'MID', 'FWD']
            
            for position in positions:
                position_players = [
                    pid for pid, data in current_players_data.items() 
                    if data['position'] == position
                ]
                
                if not position_players:
                    continue
                
                # Find the weakest player in this position based on multiple factors
                weak_candidates = self._identify_weak_players(
                    position_players, current_players_data, fixture_context, target_gameweek
                )
                
                # Find the best replacement options
                for weak_player_id in weak_candidates[:2]:  # Top 2 weakest in each position
                    weak_player = current_players_data[weak_player_id]
                    
                    # Find better alternatives
                    alternatives = self._find_transfer_alternatives(
                        weak_player, fixture_context, target_gameweek, budget_available
                    )
                    
                    for alternative in alternatives[:1]:  # Top alternative per weak player
                        transfer_value = self._calculate_transfer_value(weak_player, alternative, fixture_context)
                        
                        if transfer_value['improvement_score'] > 0.5:  # Only suggest if significant improvement
                            suggestion = {
                                'transfer_out': {
                                    'id': weak_player['id'],
                                    'name': weak_player['name'],
                                    'position': weak_player['position'],
                                    'cost': weak_player['cost'],
                                    'form': weak_player['form'],
                                    'expected_points': weak_player['expected_points'],
                                    'weakness_reasons': transfer_value['out_reasons']
                                },
                                'transfer_in': {
                                    'id': alternative['id'],
                                    'name': alternative['name'], 
                                    'position': alternative['position'],
                                    'cost': alternative['cost'],
                                    'form': alternative['form'],
                                    'expected_points': alternative['expected_points'],
                                    'strength_reasons': transfer_value['in_reasons']
                                },
                                'cost_difference': alternative['cost'] - weak_player['cost'],
                                'points_improvement': alternative['expected_points'] - weak_player['expected_points'],
                                'improvement_score': transfer_value['improvement_score'],
                                'priority': self._calculate_transfer_priority(transfer_value),
                                'reasoning': transfer_value['reasoning']
                            }
                            
                            transfer_suggestions.append(suggestion)
            
            # Sort suggestions by improvement score and priority
            transfer_suggestions.sort(key=lambda x: (x['priority'], x['improvement_score']), reverse=True)
            
            # Limit to max_suggestions
            final_suggestions = transfer_suggestions[:max_suggestions]
            
            # Generate overall reasoning
            overall_reasoning = self._generate_transfer_reasoning(final_suggestions, target_gameweek, fixture_context)
            
            result = {
                'gameweek': target_gameweek,
                'suggestions': final_suggestions,
                'total_suggestions': len(final_suggestions),
                'reasoning': overall_reasoning,
                'fixture_context': {
                    'gameweek': target_gameweek,
                    'total_fixtures': len(fixture_context),
                    'average_difficulty': sum(f.get('difficulty', 3) for f in fixture_context.values()) / len(fixture_context) if fixture_context else 3
                }
            }
            
            logger.info(f"Generated {len(final_suggestions)} transfer suggestions for GW{target_gameweek}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating transfer suggestions: {e}")
            return {
                'gameweek': target_gameweek,
                'suggestions': [],
                'total_suggestions': 0,
                'reasoning': f"ไม่สามารถสร้างคำแนะนำการเปลี่ยนตัวได้: {str(e)}",
                'error': str(e)
            }

    def _identify_weak_players(self, player_ids: List[int], players_data: Dict, 
                             fixture_context: Dict, gameweek: int) -> List[int]:
        """Identify weak players based on form, fixtures, and value."""
        weak_scores = {}
        
        for player_id in player_ids:
            player = players_data[player_id]
            weakness_score = 0
            
            # Poor form (0-3 points)
            if player['form'] < 3.0:
                weakness_score += 2
            elif player['form'] < 4.0:
                weakness_score += 1
                
            # Bad fixture (difficulty > 3)
            team_fixture = fixture_context.get(player['team_id'], {})
            if team_fixture.get('difficulty', 3) > 3:
                weakness_score += 1
                
            # Low expected points
            if player['expected_points'] < 4.0:
                weakness_score += 1
                
            # Price vs performance ratio
            if player['cost'] > 0:
                value_ratio = player['expected_points'] / player['cost']
                if value_ratio < 0.5:  # Less than 0.5 points per million
                    weakness_score += 1
            
            weak_scores[player_id] = weakness_score
        
        # Return players sorted by weakness score (highest first)
        return sorted(weak_scores.keys(), key=lambda pid: weak_scores[pid], reverse=True)

    def _find_transfer_alternatives(self, weak_player: Dict, fixture_context: Dict, 
                                  gameweek: int, budget_available: float) -> List[Dict]:
        """Find better alternatives for a weak player."""
        max_cost = weak_player['cost'] + budget_available
        
        # Query available players in same position
        alternatives_query = Player.query.filter(
            Player.position == weak_player['position'],
            Player.status == 'a',
            Player.now_cost <= max_cost * 10,  # Convert to FPL price format
            Player.player_id != weak_player['id']
        ).order_by(Player.form.desc(), Player.total_points.desc()).limit(20)
        
        alternatives = []
        for player in alternatives_query.all():
            # Get team fixture info
            team_fixture = fixture_context.get(player.team_id, {})
            fixture_difficulty = team_fixture.get('difficulty', 3)
            
            expected_points = self._calculate_player_expected_points(player, gameweek)
            
            # Only consider players with better prospects
            if (expected_points > weak_player['expected_points'] * 1.1 or  # 10% better expected points
                (player.form > weak_player['form'] + 1.0 and fixture_difficulty <= 3)):  # Much better form + decent fixture
                
                alternatives.append({
                    'id': player.player_id,
                    'name': player.web_name,
                    'position': player.position,
                    'team_id': player.team_id,
                    'cost': player.now_cost / 10.0,
                    'form': float(player.form or 0),
                    'total_points': player.total_points,
                    'expected_points': expected_points,
                    'fixture_difficulty': fixture_difficulty,
                    'is_home': team_fixture.get('is_home', False)
                })
        
        # Sort by expected points and form
        alternatives.sort(key=lambda x: (x['expected_points'], x['form']), reverse=True)
        
        return alternatives[:5]  # Top 5 alternatives

    def _calculate_transfer_value(self, out_player: Dict, in_player: Dict, 
                                fixture_context: Dict) -> Dict:
        """Calculate the value of a potential transfer."""
        
        # Points improvement
        points_diff = in_player['expected_points'] - out_player['expected_points']
        
        # Form improvement  
        form_diff = in_player['form'] - out_player['form']
        
        # Fixture improvement
        out_fixture = fixture_context.get(out_player['team_id'], {})
        in_fixture = fixture_context.get(in_player['team_id'], {})
        fixture_diff = out_fixture.get('difficulty', 3) - in_fixture.get('difficulty', 3)
        
        # Cost efficiency
        cost_diff = in_player['cost'] - out_player['cost']
        
        # Calculate improvement score (0-5 scale)
        improvement_score = 0
        
        # Points improvement (max 2 points)
        improvement_score += min(2, max(0, points_diff / 2))
        
        # Form improvement (max 1.5 points) 
        improvement_score += min(1.5, max(0, form_diff / 3))
        
        # Fixture improvement (max 1 point)
        improvement_score += min(1, max(0, fixture_diff / 2))
        
        # Cost efficiency bonus (max 0.5 points)
        if cost_diff <= 0:  # Cheaper or same price
            improvement_score += 0.5
        elif cost_diff <= 1.0:  # Up to 1M more expensive
            improvement_score += 0.2
        
        # Generate reasoning
        out_reasons = []
        if out_player['form'] < 3:
            out_reasons.append(f"ฟอร์มไม่ดี ({out_player['form']:.1f})")
        if out_fixture.get('difficulty', 3) > 3:
            out_reasons.append("ตารางแข่งขันยาก")
        if out_player['expected_points'] < 4:
            out_reasons.append("คะแนนคาดหวังต่ำ")
            
        in_reasons = []
        if form_diff > 1:
            in_reasons.append(f"ฟอร์มดีกว่า ({in_player['form']:.1f})")
        if fixture_diff > 0:
            in_reasons.append("ตารางแข่งขันง่ายกว่า")
        if points_diff > 1:
            in_reasons.append(f"คะแนนคาดหวังสูงกว่า ({points_diff:.1f})")
        if cost_diff <= 0:
            in_reasons.append("ราคาถูกกว่าหรือเท่ากัน")
            
        reasoning = f"เปลี่ยน {out_player['name']} เป็น {in_player['name']} "
        if points_diff > 0:
            reasoning += f"เพิ่มคะแนนคาดหวัง {points_diff:.1f} "
        if form_diff > 1:
            reasoning += f"ฟอร์มดีขึ้น {form_diff:.1f} "
        if cost_diff != 0:
            if cost_diff > 0:
                reasoning += f"ใช้เงินเพิ่ม £{cost_diff:.1f}M"
            else:
                reasoning += f"ประหยัด £{abs(cost_diff):.1f}M"
        
        return {
            'improvement_score': improvement_score,
            'points_improvement': points_diff,
            'form_improvement': form_diff,
            'fixture_improvement': fixture_diff,
            'cost_efficiency': -cost_diff,  # Negative cost is better
            'out_reasons': out_reasons,
            'in_reasons': in_reasons,
            'reasoning': reasoning
        }

    def _calculate_transfer_priority(self, transfer_value: Dict) -> int:
        """Calculate transfer priority (1-5, 5 being highest priority)."""
        score = transfer_value['improvement_score']
        
        if score >= 4:
            return 5  # Must have
        elif score >= 3:
            return 4  # Highly recommended
        elif score >= 2:
            return 3  # Good option
        elif score >= 1:
            return 2  # Consider
        else:
            return 1  # Low priority

    def _generate_transfer_reasoning(self, suggestions: List[Dict], gameweek: int, 
                                   fixture_context: Dict) -> str:
        """Generate overall reasoning for transfer suggestions."""
        if not suggestions:
            return f"ไม่มีการเปลี่ยนตัวที่แนะนำสำหรับเกมวีคที่ {gameweek} ทีมปัจจุบันมีความเหมาะสมแล้ว"
        
        reasoning = f"🔄 คำแนะนำการเปลี่ยนตัวสำหรับเกมวีคที่ {gameweek}:\n\n"
        
        for i, suggestion in enumerate(suggestions, 1):
            priority_text = {5: "จำเป็นมาก", 4: "แนะนำสูง", 3: "ตัวเลือกดี", 2: "พิจารณา", 1: "ไม่จำเป็น"}
            
            reasoning += f"{i}. {suggestion['reasoning']} "
            reasoning += f"(ความสำคัญ: {priority_text.get(suggestion['priority'], 'ปกติ')})\n"
            
            if suggestion['cost_difference'] > 0:
                reasoning += f"   💰 ต้องใช้เงินเพิ่ม £{suggestion['cost_difference']:.1f}M\n"
            elif suggestion['cost_difference'] < 0:
                reasoning += f"   💚 ประหยัดเงิน £{abs(suggestion['cost_difference']):.1f}M\n"
            
            reasoning += "\n"
        
        reasoning += "💡 คำแนะนำ: ควรพิจารณาตารางแข่งขันในสัปดาห์ถัดไปด้วย และอย่าลืมเช็ค injury news ก่อนทำการเปลี่ยนตัว"
        
        return reasoning

    def _calculate_player_expected_points(self, player, gameweek: int) -> float:
        """Calculate expected points for a player in specific gameweek."""
        # Base calculation similar to production_app.py
        position_base = {
            'GKP': 4.0, 'DEF': 4.5, 'MID': 5.5, 'FWD': 6.0
        }.get(player.position, 4.0)
        
        # Form factor
        form_score = float(player.form or 0)
        if form_score >= 8.0:
            form_multiplier = 1.5
        elif form_score >= 6.0:
            form_multiplier = 1.3
        elif form_score >= 4.0:
            form_multiplier = 1.1
        elif form_score >= 2.0:
            form_multiplier = 0.9
        else:
            form_multiplier = 0.6
            
        # Season performance factor
        total_points = player.total_points or 0
        if total_points >= 250:
            points_multiplier = 1.6
        elif total_points >= 200:
            points_multiplier = 1.4
        elif total_points >= 150:
            points_multiplier = 1.2
        elif total_points >= 100:
            points_multiplier = 1.0
        elif total_points >= 50:
            points_multiplier = 0.8
        else:
            points_multiplier = 0.5
            
        # Price factor
        cost = player.now_cost / 10.0
        if cost >= 13.0:
            cost_multiplier = 1.4
        elif cost >= 10.0:
            cost_multiplier = 1.2
        elif cost >= 7.0:
            cost_multiplier = 1.0
        elif cost >= 5.0:
            cost_multiplier = 0.9
        else:
            cost_multiplier = 0.7
            
        expected = position_base * form_multiplier * points_multiplier * cost_multiplier
        return max(1.0, min(12.0, round(expected, 1)))

    def _get_multi_gameweek_player_data(self, multi_fixture_contexts: Dict[int, Dict], 
                                      excluded_players: Optional[List[int]] = None) -> Dict:
        """Get player data with enhanced scoring across multiple gameweeks."""
        # Get base player data
        player_data = self._get_player_data_for_optimization(excluded_players)
        
        # Enhance with multi-gameweek fixture analysis
        for player_id, data in player_data.items():
            base_points = data['expected_points']
            current_gameweek_score = base_points
            multi_gameweek_score = 0
            
            # Calculate points for each gameweek considering fixtures
            for gw, fixture_context in multi_fixture_contexts.items():
                if player_id in fixture_context:
                    context = fixture_context[player_id]
                    gw_score = base_points
                    
                    # Apply home advantage
                    if context.get('is_home', True):
                        gw_score *= 1.05
                        
                    # Apply fixture difficulty multiplier
                    difficulty = context.get('fixture_difficulty', 3)
                    difficulty_multiplier = 1 + (3 - difficulty) * 0.1  # Easier = higher points
                    gw_score *= difficulty_multiplier
                    
                    # Weight current gameweek more heavily
                    if list(multi_fixture_contexts.keys())[0] == gw:  # First gameweek
                        current_gameweek_score = gw_score
                        multi_gameweek_score += gw_score * 1.5  # Current GW weighted more
                    else:
                        # Future gameweeks weighted less due to uncertainty
                        future_weight = 1.0 - (gw - list(multi_fixture_contexts.keys())[0]) * 0.1
                        multi_gameweek_score += gw_score * max(0.5, future_weight)
                else:
                    # No fixture = no points for this gameweek
                    if list(multi_fixture_contexts.keys())[0] == gw:
                        current_gameweek_score = 0
                        
            data['current_gameweek_score'] = current_gameweek_score
            data['multi_gameweek_score'] = multi_gameweek_score
            
        return player_data
        
    def _analyze_multi_gameweek_fixtures(self, player_ids: List[int], 
                                       multi_fixture_contexts: Dict[int, Dict],
                                       gameweek_range: List[int]) -> Dict:
        """Analyze fixture difficulty across multiple gameweeks."""
        analysis = {
            'gameweek_range': f"GW{gameweek_range[0]}-{gameweek_range[-1]}",
            'total_gameweeks': len(gameweek_range),
            'gameweek_breakdown': {}
        }
        
        total_fixtures = 0
        total_difficulty = 0
        total_home = 0
        total_easy = 0
        total_hard = 0
        
        for gw in gameweek_range:
            fixture_context = multi_fixture_contexts.get(gw, {})
            gw_difficulties = []
            gw_home = 0
            
            for player_id in player_ids:
                if player_id in fixture_context:
                    context = fixture_context[player_id]
                    difficulty = context.get('fixture_difficulty', 3)
                    gw_difficulties.append(difficulty)
                    total_difficulty += difficulty
                    total_fixtures += 1
                    
                    if context.get('is_home'):
                        gw_home += 1
                        total_home += 1
                        
                    if difficulty <= 2:
                        total_easy += 1
                    elif difficulty >= 4:
                        total_hard += 1
                        
            if gw_difficulties:
                analysis['gameweek_breakdown'][f'gw_{gw}'] = {
                    'avg_difficulty': round(sum(gw_difficulties) / len(gw_difficulties), 2),
                    'home_players': gw_home,
                    'fixtures_count': len(gw_difficulties)
                }
                
        if total_fixtures > 0:
            analysis.update({
                'overall_avg_difficulty': round(total_difficulty / total_fixtures, 2),
                'total_fixtures': total_fixtures,
                'total_home_fixtures': total_home,
                'total_easy_fixtures': total_easy,
                'total_hard_fixtures': total_hard,
                'fixture_quality_score': round((total_easy * 2 + total_hard * -1) / total_fixtures, 2)
            })
            
        return analysis
    
    def _analyze_fixture_difficulty(self, player_ids: List[int], 
                                  fixture_context: Dict) -> Dict:
        """Analyze fixture difficulty for selected players."""
        if not player_ids or not fixture_context:
            return {}
        
        difficulties = []
        home_count = 0
        
        for player_id in player_ids:
            if player_id in fixture_context:
                context = fixture_context[player_id]
                difficulties.append(context['fixture_difficulty'])
                if context['is_home']:
                    home_count += 1
        
        if difficulties:
            avg_difficulty = sum(difficulties) / len(difficulties)
            return {
                'average_fixture_difficulty': round(avg_difficulty, 2),
                'home_players': home_count,
                'away_players': len(difficulties) - home_count,
                'easy_fixtures': sum(1 for d in difficulties if d <= 2),
                'hard_fixtures': sum(1 for d in difficulties if d >= 4)
            }
        
        return {}