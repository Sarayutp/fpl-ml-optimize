"""Team optimizer views for FPL AI Optimizer."""

import logging
import time
from datetime import datetime
from typing import Dict, Any, List

from flask import Blueprint, render_template, request, jsonify, current_app
from pydantic import ValidationError

from ..models.data_models import OptimizationRequest, APIResponse, ValidationErrorResponse
from ..models.db_models import Player, Team


logger = logging.getLogger(__name__)

optimizer_bp = Blueprint('optimizer', __name__)


@optimizer_bp.route('/')
def index():
    """Team optimizer page."""
    try:
        # Get available teams for filters
        teams = Team.query.order_by(Team.name).all()
        
        # Get player count by position for UI
        position_counts = get_position_counts()
        
        return render_template('optimizer.html',
                             teams=teams,
                             position_counts=position_counts)
        
    except Exception as e:
        logger.error(f"Error loading optimizer page: {e}")
        return render_template('optimizer.html',
                             teams=[],
                             position_counts={})


@optimizer_bp.route('/optimize', methods=['POST'])
def optimize_team():
    """Optimize FPL team based on constraints."""
    start_time = time.time()
    
    try:
        # Parse and validate request
        request_data = request.get_json()
        if not request_data:
            return jsonify(ValidationErrorResponse(
                error="No JSON data provided"
            ).dict()), 400
        
        try:
            optimization_request = OptimizationRequest(**request_data)
        except ValidationError as e:
            return jsonify(ValidationErrorResponse(
                error="Invalid request parameters",
                details=e.errors()
            ).dict()), 400
        
        # Perform optimization
        optimization_service = current_app.optimization_service
        reasoning_service = current_app.reasoning_service
        
        result = optimization_service.optimize_team(
            budget=optimization_request.budget,
            formation=optimization_request.formation,
            preferred_players=optimization_request.preferred_players,
            excluded_players=optimization_request.excluded_players,
            max_players_per_team=optimization_request.max_players_per_team
        )
        
        # Generate reasoning if requested
        reasoning = ""
        if optimization_request.include_reasoning:
            reasoning = reasoning_service.generate_team_reasoning(result)
        
        # Get player details for the result
        player_details = get_players_details(result['players'])
        
        # Prepare response
        response_data = {
            'optimization_result': result,
            'reasoning': reasoning,
            'player_details': player_details,
            'request_params': optimization_request.dict(),
            'processing_time': round(time.time() - start_time, 2)
        }
        
        return jsonify(APIResponse(
            success=True,
            data=response_data
        ).dict())
        
    except ValueError as e:
        logger.error(f"Optimization validation error: {e}")
        return jsonify(APIResponse(
            success=False,
            error=str(e)
        ).dict()), 400
        
    except Exception as e:
        logger.error(f"Optimization error: {e}")
        return jsonify(APIResponse(
            success=False,
            error="Optimization failed. Please try again."
        ).dict()), 500


@optimizer_bp.route('/suggest-transfers', methods=['POST'])
def suggest_transfers():
    """Suggest optimal transfers for current team."""
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate required parameters
        current_team = request_data.get('current_team', [])
        if not current_team or len(current_team) != 15:
            return jsonify({'error': 'Current team must contain exactly 15 players'}), 400
        
        # Optional parameters
        budget_available = request_data.get('budget_available', 0.0)
        transfer_limit = request_data.get('transfer_limit', 1)
        min_improvement = request_data.get('min_improvement', 0.1)
        
        # Get transfer suggestions
        optimization_service = current_app.optimization_service
        reasoning_service = current_app.reasoning_service
        
        suggestions = optimization_service.suggest_transfers(
            current_team=current_team,
            budget_available=budget_available,
            transfer_limit=transfer_limit,
            min_improvement=min_improvement
        )
        
        # Add reasoning to each suggestion
        for suggestion in suggestions:
            suggestion.reasoning = reasoning_service.generate_transfer_reasoning(suggestion)
        
        # Convert to dict for JSON response
        suggestions_data = [suggestion.dict() for suggestion in suggestions]
        
        return jsonify({
            'success': True,
            'data': suggestions_data,
            'count': len(suggestions_data)
        })
        
    except Exception as e:
        logger.error(f"Transfer suggestion error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to generate transfer suggestions'
        }), 500


@optimizer_bp.route('/suggest-captain', methods=['POST'])
def suggest_captain():
    """Suggest captain and vice-captain for team."""
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate required parameters
        team_players = request_data.get('team_players', [])
        if not team_players or len(team_players) != 15:
            return jsonify({'error': 'Team must contain exactly 15 players'}), 400
        
        # Optional fixture context
        fixture_context = request_data.get('fixture_context', {})
        
        # Get captain suggestion
        optimization_service = current_app.optimization_service
        reasoning_service = current_app.reasoning_service
        
        suggestion = optimization_service.suggest_captain(
            team_players=team_players,
            fixture_context=fixture_context
        )
        
        # Add reasoning
        reasoning = reasoning_service.generate_captain_reasoning(suggestion, fixture_context)
        suggestion['reasoning'] = reasoning
        
        return jsonify({
            'success': True,
            'data': suggestion
        })
        
    except Exception as e:
        logger.error(f"Captain suggestion error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to generate captain suggestion'
        }), 500


@optimizer_bp.route('/gameweek-optimize', methods=['POST'])
def optimize_gameweek():
    """Optimize team for specific gameweek."""
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Required parameters
        gameweek = request_data.get('gameweek')
        if not gameweek or not isinstance(gameweek, int) or gameweek < 1 or gameweek > 38:
            return jsonify({'error': 'Valid gameweek (1-38) is required'}), 400
        
        # Optional parameters
        existing_team = request_data.get('existing_team', [])
        free_transfers = request_data.get('free_transfers', 1)
        budget = request_data.get('budget', 100.0)
        
        # Perform gameweek optimization
        optimization_service = current_app.optimization_service
        reasoning_service = current_app.reasoning_service
        
        result = optimization_service.optimize_for_gameweek(
            gameweek=gameweek,
            existing_team=existing_team if existing_team else None,
            free_transfers=free_transfers,
            budget=budget
        )
        
        # Generate comprehensive reasoning
        analysis = reasoning_service.generate_comprehensive_analysis(result)
        
        # Get player details
        if result.get('players'):
            player_details = get_players_details(result['players'])
            result['player_details'] = player_details
        
        result['analysis'] = analysis
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"Gameweek optimization error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to optimize for gameweek'
        }), 500


@optimizer_bp.route('/validate-team', methods=['POST'])
def validate_team():
    """Validate team composition and constraints."""
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        player_ids = request_data.get('players', [])
        if not player_ids:
            return jsonify({'error': 'Player list is required'}), 400
        
        validation_result = validate_team_composition(player_ids)
        
        return jsonify({
            'success': True,
            'data': validation_result
        })
        
    except Exception as e:
        logger.error(f"Team validation error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to validate team'
        }), 500


def get_players_details(player_ids: List[int]) -> List[Dict[str, Any]]:
    """Get detailed information for list of players."""
    try:
        if not player_ids:
            return []
        
        query = current_app.db.session.query(
            Player.player_id,
            Player.web_name,
            Player.first_name,
            Player.second_name,
            Player.position,
            Player.now_cost,
            Player.total_points,
            Player.form,
            Player.expected_goals,
            Player.expected_assists,
            Player.status,
            Team.name.label('team_name'),
            Team.short_name.label('team_short')
        ).join(
            Team, Player.team_id == Team.team_id
        ).filter(
            Player.player_id.in_(player_ids)
        )
        
        players = []
        for row in query.all():
            players.append({
                'player_id': row.player_id,
                'web_name': row.web_name,
                'full_name': f"{row.first_name} {row.second_name}",
                'position': row.position,
                'team_name': row.team_name,
                'team_short': row.team_short,
                'cost': row.now_cost / 10.0,
                'total_points': row.total_points,
                'form': float(row.form or 0),
                'expected_goals': float(row.expected_goals or 0),
                'expected_assists': float(row.expected_assists or 0),
                'status': row.status,
                'is_available': row.status == 'a'
            })
        
        # Sort by position and then by cost descending
        position_order = {'GKP': 0, 'DEF': 1, 'MID': 2, 'FWD': 3}
        players.sort(key=lambda x: (position_order.get(x['position'], 4), -x['cost']))
        
        return players
        
    except Exception as e:
        logger.error(f"Error getting player details: {e}")
        return []


def validate_team_composition(player_ids: List[int]) -> Dict[str, Any]:
    """Validate team composition against FPL rules."""
    try:
        if len(player_ids) != 15:
            return {
                'is_valid': False,
                'errors': [f'Team must have exactly 15 players, got {len(player_ids)}']
            }
        
        # Get player information
        players = Player.query.filter(Player.player_id.in_(player_ids)).all()
        
        if len(players) != len(player_ids):
            return {
                'is_valid': False,
                'errors': ['Some players not found in database']
            }
        
        errors = []
        warnings = []
        
        # Check position constraints
        position_counts = {}
        total_cost = 0
        team_counts = {}
        unavailable_players = []
        
        for player in players:
            # Count positions
            position_counts[player.position] = position_counts.get(player.position, 0) + 1
            
            # Calculate total cost
            total_cost += player.now_cost / 10.0
            
            # Count players per team
            team_counts[player.team_id] = team_counts.get(player.team_id, 0) + 1
            
            # Check availability
            if player.status != 'a':
                unavailable_players.append(player.web_name)
        
        # Validate formation constraints
        required_positions = {'GKP': 2, 'DEF': 5, 'MID': 5, 'FWD': 3}
        for position, required in required_positions.items():
            actual = position_counts.get(position, 0)
            if actual != required:
                errors.append(f'Invalid {position} count: need {required}, got {actual}')
        
        # Validate budget constraint
        if total_cost > 100.0:
            errors.append(f'Team cost £{total_cost:.1f}M exceeds budget of £100.0M')
        
        # Validate team constraints (max 3 per team)
        for team_id, count in team_counts.items():
            if count > 3:
                team = Team.query.get(team_id)
                team_name = team.name if team else f'Team {team_id}'
                errors.append(f'Too many players from {team_name}: {count} (max 3)')
        
        # Check player availability
        if unavailable_players:
            warnings.append(f'Unavailable players: {", ".join(unavailable_players)}')
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'stats': {
                'total_cost': round(total_cost, 1),
                'budget_remaining': round(100.0 - total_cost, 1),
                'position_counts': position_counts,
                'team_distribution': len(team_counts),
                'unavailable_count': len(unavailable_players)
            }
        }
        
    except Exception as e:
        logger.error(f"Error validating team: {e}")
        return {
            'is_valid': False,
            'errors': ['Validation failed due to system error']
        }


def get_position_counts() -> Dict[str, int]:
    """Get count of available players by position."""
    try:
        query = current_app.db.session.query(
            Player.position,
            current_app.db.func.count(Player.player_id).label('count')
        ).filter(
            Player.status == 'a'
        ).group_by(
            Player.position
        )
        
        counts = {}
        for row in query.all():
            counts[row.position] = row.count
        
        return counts
        
    except Exception as e:
        logger.error(f"Error getting position counts: {e}")
        return {'GKP': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}