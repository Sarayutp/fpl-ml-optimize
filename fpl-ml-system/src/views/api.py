"""REST API views for FPL AI Optimizer."""

import logging
from datetime import datetime
from typing import Dict, Any

from flask import Blueprint, jsonify, request, current_app
from pydantic import ValidationError

from ..models.data_models import APIResponse, ValidationErrorResponse
from ..models.db_models import Player, Team, PlayerPrediction


logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__)


@api_bp.route('/health')
def health_check():
    """Health check endpoint."""
    try:
        # Check database connection
        player_count = Player.query.count()
        
        # Check services
        services_status = {
            'data_service': hasattr(current_app, 'data_service'),
            'prediction_service': hasattr(current_app, 'prediction_service'),
            'optimization_service': hasattr(current_app, 'optimization_service'),
            'reasoning_service': hasattr(current_app, 'reasoning_service')
        }
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'database': {
                'connected': True,
                'player_count': player_count
            },
            'services': services_status
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 500


@api_bp.route('/players')
def get_players():
    """Get players with optional filtering."""
    try:
        # Parse query parameters
        position = request.args.get('position')
        team_id = request.args.get('team_id', type=int)
        status = request.args.get('status', 'a')  # Default to available
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Validate limit
        if limit > 100:
            limit = 100
        
        # Build query
        query = Player.query.filter(Player.status == status)
        
        if position:
            if position not in ['GKP', 'DEF', 'MID', 'FWD']:
                return jsonify(ValidationErrorResponse(
                    error="Invalid position. Must be GKP, DEF, MID, or FWD"
                ).dict()), 400
            query = query.filter(Player.position == position)
        
        if team_id:
            query = query.filter(Player.team_id == team_id)
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination and execute
        players = query.offset(offset).limit(limit).all()
        
        # Convert to dict
        players_data = []
        for player in players:
            players_data.append({
                'player_id': player.player_id,
                'web_name': player.web_name,
                'first_name': player.first_name,
                'second_name': player.second_name,
                'position': player.position,
                'team_id': player.team_id,
                'now_cost': player.now_cost / 10.0,
                'total_points': player.total_points,
                'form': float(player.form or 0),
                'status': player.status
            })
        
        return jsonify(APIResponse(
            success=True,
            data={
                'players': players_data,
                'total_count': total_count,
                'limit': limit,
                'offset': offset
            }
        ).dict())
        
    except Exception as e:
        logger.error(f"Error getting players: {e}")
        return jsonify(APIResponse(
            success=False,
            error="Failed to retrieve players"
        ).dict()), 500


@api_bp.route('/players/<int:player_id>')
def get_player(player_id: int):
    """Get specific player information."""
    try:
        player = Player.query.get(player_id)
        if not player:
            return jsonify(APIResponse(
                success=False,
                error="Player not found"
            ).dict()), 404
        
        # Get team info
        team = Team.query.get(player.team_id)
        
        # Get prediction info
        prediction = PlayerPrediction.query.filter_by(
            player_id=player_id,
            fixture_id=None  # General prediction
        ).first()
        
        player_data = {
            'player_id': player.player_id,
            'web_name': player.web_name,
            'full_name': f"{player.first_name} {player.second_name}",
            'position': player.position,
            'team': {
                'team_id': team.team_id if team else None,
                'name': team.name if team else None,
                'short_name': team.short_name if team else None
            },
            'stats': {
                'now_cost': player.now_cost / 10.0,
                'total_points': player.total_points,
                'form': float(player.form or 0),
                'points_per_game': float(player.points_per_game or 0),
                'minutes': player.minutes or 0,
                'expected_goals': float(player.expected_goals or 0),
                'expected_assists': float(player.expected_assists or 0),
                'status': player.status
            },
            'prediction': {
                'expected_points': float(prediction.expected_points) if prediction else None,
                'confidence': float(prediction.confidence_score) if prediction and prediction.confidence_score else None,
                'last_updated': prediction.last_updated.isoformat() if prediction and prediction.last_updated else None
            }
        }
        
        return jsonify(APIResponse(
            success=True,
            data=player_data
        ).dict())
        
    except Exception as e:
        logger.error(f"Error getting player {player_id}: {e}")
        return jsonify(APIResponse(
            success=False,
            error="Failed to retrieve player information"
        ).dict()), 500


@api_bp.route('/teams')
def get_teams():
    """Get all teams."""
    try:
        teams = Team.query.order_by(Team.name).all()
        
        teams_data = []
        for team in teams:
            teams_data.append({
                'team_id': team.team_id,
                'name': team.name,
                'short_name': team.short_name,
                'strength_overall_home': team.strength_overall_home,
                'strength_overall_away': team.strength_overall_away
            })
        
        return jsonify(APIResponse(
            success=True,
            data=teams_data
        ).dict())
        
    except Exception as e:
        logger.error(f"Error getting teams: {e}")
        return jsonify(APIResponse(
            success=False,
            error="Failed to retrieve teams"
        ).dict()), 500


@api_bp.route('/predictions')
def get_predictions():
    """Get player predictions."""
    try:
        # Parse parameters
        player_id = request.args.get('player_id', type=int)
        position = request.args.get('position')
        limit = request.args.get('limit', 50, type=int)
        
        # Build query
        query = PlayerPrediction.query.join(Player)
        
        if player_id:
            query = query.filter(PlayerPrediction.player_id == player_id)
        
        if position:
            if position not in ['GKP', 'DEF', 'MID', 'FWD']:
                return jsonify(ValidationErrorResponse(
                    error="Invalid position"
                ).dict()), 400
            query = query.filter(Player.position == position)
        
        # Order by expected points
        query = query.order_by(PlayerPrediction.expected_points.desc())
        
        # Apply limit
        predictions = query.limit(limit).all()
        
        predictions_data = []
        for pred in predictions:
            predictions_data.append({
                'player_id': pred.player_id,
                'web_name': pred.player.web_name,
                'position': pred.player.position,
                'expected_points': float(pred.expected_points),
                'expected_minutes': float(pred.expected_minutes) if pred.expected_minutes else None,
                'confidence_score': float(pred.confidence_score) if pred.confidence_score else None,
                'model_version': pred.model_version,
                'last_updated': pred.last_updated.isoformat() if pred.last_updated else None
            })
        
        return jsonify(APIResponse(
            success=True,
            data=predictions_data
        ).dict())
        
    except Exception as e:
        logger.error(f"Error getting predictions: {e}")
        return jsonify(APIResponse(
            success=False,
            error="Failed to retrieve predictions"
        ).dict()), 500


@api_bp.route('/optimize', methods=['POST', 'OPTIONS'])
@api_bp.route('/optimize-team', methods=['POST', 'OPTIONS'])  
def optimize_team():
    """Optimize team selection."""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
        
    try:
        logger.info("Team optimization API called")
        
        # Get request data
        request_data = request.get_json()
        if not request_data:
            logger.error("No JSON data provided")
            return jsonify(ValidationErrorResponse(
                error="No JSON data provided"
            ).dict()), 400
        
        logger.info(f"Request data: {request_data}")
        
        # Check if services exist
        if not hasattr(current_app, 'optimization_service'):
            logger.error("optimization_service not found in app context")
            return jsonify(APIResponse(
                success=False,
                error="Optimization service not available"
            ).dict()), 500
            
        if not hasattr(current_app, 'reasoning_service'):
            logger.error("reasoning_service not found in app context")
            return jsonify(APIResponse(
                success=False,
                error="Reasoning service not available"
            ).dict()), 500
        
        # Get services
        optimization_service = current_app.optimization_service
        reasoning_service = current_app.reasoning_service
        
        logger.info("Starting team optimization...")
        
        # Perform optimization
        result = optimization_service.optimize_team(
            budget=request_data.get('budget', 100.0),
            formation=request_data.get('formation'),
            preferred_players=request_data.get('preferred_players'),
            excluded_players=request_data.get('excluded_players'),
            max_players_per_team=request_data.get('max_players_per_team', 3)
        )
        
        logger.info("Optimization completed, generating reasoning...")
        
        # Generate simple reasoning to avoid recursion
        try:
            reasoning = reasoning_service.generate_team_reasoning(result)
            result['reasoning'] = reasoning
        except Exception as reasoning_error:
            logger.warning(f"Reasoning generation failed: {reasoning_error}")
            # Provide fallback reasoning
            total_cost = result.get('total_cost', 0)
            expected_points = result.get('expected_points', 0)
            result['reasoning'] = f"ทีมที่แนะนำใช้งบ £{total_cost:.1f}M คาดหวัง {expected_points:.1f} แต้ม ได้รับการปรับให้เหมาะสมแล้วด้วย AI"
        
        logger.info("Team optimization API completed successfully")
        
        response = jsonify(APIResponse(
            success=True,
            data=result
        ).dict())
        
        # Add CORS headers
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        
        return response
        
    except Exception as e:
        logger.error(f"Team optimization API error: {e}", exc_info=True)
        response = jsonify(APIResponse(
            success=False,
            error=f"Team optimization failed: {str(e)}"
        ).dict())
        
        # Add CORS headers to error response too
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        
        return response, 500


@api_bp.route('/suggest-captain', methods=['POST'])
def suggest_captain():
    """Suggest captain for team."""
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify(ValidationErrorResponse(
                error="No JSON data provided"
            ).dict()), 400
        
        team_players = request_data.get('team_players', [])
        if not team_players:
            return jsonify(ValidationErrorResponse(
                error="Team players list is required"
            ).dict()), 400
        
        # Get services
        optimization_service = current_app.optimization_service
        reasoning_service = current_app.reasoning_service
        
        # Get suggestion
        suggestion = optimization_service.suggest_captain(
            team_players=team_players,
            fixture_context=request_data.get('fixture_context')
        )
        
        # Add reasoning
        reasoning = reasoning_service.generate_captain_reasoning(
            suggestion,
            request_data.get('fixture_context')
        )
        suggestion['reasoning'] = reasoning
        
        return jsonify(APIResponse(
            success=True,
            data=suggestion
        ).dict())
        
    except Exception as e:
        logger.error(f"Captain suggestion API error: {e}")
        return jsonify(APIResponse(
            success=False,
            error="Captain suggestion failed"
        ).dict()), 500


@api_bp.route('/data/refresh', methods=['POST'])
def refresh_data():
    """Refresh data from FPL API."""
    try:
        if not current_app.config.get('ALLOW_DATA_REFRESH', True):
            return jsonify(APIResponse(
                success=False,
                error="Data refresh not allowed in this environment"
            ).dict()), 403
        
        data_service = current_app.data_service
        stats = data_service.update_database_from_api()
        
        return jsonify(APIResponse(
            success=True,
            data={
                'refresh_completed': True,
                'stats': stats,
                'timestamp': datetime.now().isoformat()
            }
        ).dict())
        
    except Exception as e:
        logger.error(f"Data refresh API error: {e}")
        return jsonify(APIResponse(
            success=False,
            error="Data refresh failed"
        ).dict()), 500


@api_bp.route('/stats/overview')
def stats_overview():
    """Get system overview statistics."""
    try:
        from ..views.dashboard import get_dashboard_stats
        
        stats = get_dashboard_stats()
        
        return jsonify(APIResponse(
            success=True,
            data=stats
        ).dict())
        
    except Exception as e:
        logger.error(f"Stats overview API error: {e}")
        return jsonify(APIResponse(
            success=False,
            error="Failed to get statistics"
        ).dict()), 500


# Error handlers for API blueprint
@api_bp.errorhandler(404)
def api_not_found(error):
    """API 404 handler."""
    return jsonify(APIResponse(
        success=False,
        error="API endpoint not found"
    ).dict()), 404


@api_bp.errorhandler(405)
def api_method_not_allowed(error):
    """API 405 handler."""
    return jsonify(APIResponse(
        success=False,
        error="Method not allowed for this endpoint"
    ).dict()), 405


@api_bp.errorhandler(500)
def api_internal_error(error):
    """API 500 handler."""
    logger.error(f"API internal error: {error}")
    return jsonify(APIResponse(
        success=False,
        error="Internal server error"
    ).dict()), 500