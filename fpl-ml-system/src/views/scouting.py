"""Scouting and statistics views for FPL AI Optimizer."""

import logging
from typing import Dict, Any, List, Optional

from flask import Blueprint, render_template, request, jsonify, current_app
from sqlalchemy import or_, and_, func
from pydantic import ValidationError

from ..models.data_models import PlayerSearchRequest, PlayerSearchResponse, APIResponse
from ..models.db_models import db, Player, Team, PlayerPrediction, Fixture, PlayerPastStats


logger = logging.getLogger(__name__)

scouting_bp = Blueprint('scouting', __name__)


@scouting_bp.route('/')
def index():
    """Scouting and statistics main page."""
    try:
        # Get teams for filter dropdown
        teams = Team.query.order_by(Team.name).all()
        
        # Get position statistics
        position_stats = get_position_statistics()
        
        # Get price ranges
        price_ranges = get_price_ranges()
        
        return render_template('scouting.html',
                             teams=teams,
                             position_stats=position_stats,
                             price_ranges=price_ranges)
        
    except Exception as e:
        logger.error(f"Error loading scouting page: {e}")
        return render_template('scouting.html',
                             teams=[],
                             position_stats={},
                             price_ranges={})


@scouting_bp.route('/search', methods=['GET', 'POST'])
def search_players():
    """Search players with filters."""
    try:
        # Handle both GET and POST requests
        if request.method == 'POST':
            request_data = request.get_json() or {}
        else:
            request_data = request.args.to_dict()
        
        # Parse and validate search parameters
        try:
            search_request = PlayerSearchRequest(**request_data)
        except ValidationError as e:
            return jsonify({
                'success': False,
                'error': 'Invalid search parameters',
                'details': e.errors()
            }), 400
        
        # Perform search
        search_result = perform_player_search(search_request)
        
        # Return results
        if request.method == 'POST':
            return jsonify({
                'success': True,
                'data': search_result.dict()
            })
        else:
            return render_template('scouting_results.html',
                                 search_result=search_result,
                                 search_params=search_request)
        
    except Exception as e:
        logger.error(f"Player search error: {e}")
        error_response = {
            'success': False,
            'error': 'Search failed. Please try again.'
        }
        
        if request.method == 'POST':
            return jsonify(error_response), 500
        else:
            return render_template('scouting_results.html',
                                 search_result=None,
                                 error=error_response['error'])


@scouting_bp.route('/player/<int:player_id>')
def player_detail(player_id: int):
    """Get detailed player information."""
    try:
        player_info = get_detailed_player_info(player_id)
        
        if not player_info:
            return jsonify({
                'success': False,
                'error': 'Player not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': player_info
        })
        
    except Exception as e:
        logger.error(f"Error getting player {player_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get player information'
        }), 500


@scouting_bp.route('/compare', methods=['POST'])
def compare_players():
    """Compare multiple players side by side."""
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        player_ids = request_data.get('player_ids', [])
        if not player_ids or len(player_ids) < 2:
            return jsonify({'error': 'At least 2 players required for comparison'}), 400
        
        if len(player_ids) > 6:
            return jsonify({'error': 'Maximum 6 players can be compared'}), 400
        
        # Get comparison data
        comparison_data = get_player_comparison(player_ids)
        
        return jsonify({
            'success': True,
            'data': comparison_data
        })
        
    except Exception as e:
        logger.error(f"Player comparison error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to compare players'
        }), 500


@scouting_bp.route('/stats/position/<position>')
def position_stats(position: str):
    """Get statistics for a specific position."""
    try:
        if position not in ['GKP', 'DEF', 'MID', 'FWD']:
            return jsonify({'error': 'Invalid position'}), 400
        
        stats = get_detailed_position_stats(position)
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting {position} stats: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get {position} statistics'
        }), 500


@scouting_bp.route('/trends')
def player_trends():
    """Get trending players based on recent performance."""
    try:
        # Get different types of trending players
        trends = {
            'form_risers': get_form_trending_players(direction='up'),
            'form_fallers': get_form_trending_players(direction='down'),
            'price_risers': get_price_trending_players(direction='up'),
            'price_fallers': get_price_trending_players(direction='down'),
            'transfer_targets': get_transfer_trending_players()
        }
        
        return jsonify({
            'success': True,
            'data': trends
        })
        
    except Exception as e:
        logger.error(f"Error getting trends: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get trending data'
        }), 500


def perform_player_search(search_request: PlayerSearchRequest) -> PlayerSearchResponse:
    """Perform player search with filters."""
    try:
        # Base query
        query = db.session.query(
            Player.player_id,
            Player.web_name,
            Player.first_name,
            Player.second_name,
            Player.position,
            Player.now_cost,
            Player.total_points,
            Player.form,
            Player.points_per_game,
            Player.expected_goals,
            Player.expected_assists,
            Player.status,
            Player.minutes,
            Team.name.label('team_name'),
            Team.short_name.label('team_short'),
            PlayerPrediction.expected_points
        ).join(
            Team, Player.team_id == Team.team_id
        ).join(
            PlayerPrediction, Player.player_id == PlayerPrediction.player_id,
            isouter=True
        ).filter(
            Player.status == 'a'  # Available players only
        )
        
        # Apply filters
        if search_request.name:
            # Use indexed web_name search for performance
            query = query.filter(
                Player.web_name.ilike(f'%{search_request.name}%')
            )
        
        if search_request.position:
            query = query.filter(Player.position == search_request.position)
        
        if search_request.team_id:
            query = query.filter(Player.team_id == search_request.team_id)
        
        if search_request.min_cost:
            query = query.filter(Player.now_cost >= search_request.min_cost * 10)
        
        if search_request.max_cost:
            query = query.filter(Player.now_cost <= search_request.max_cost * 10)
        
        if search_request.min_points:
            query = query.filter(Player.total_points >= search_request.min_points)
        
        # Apply sorting
        if search_request.sort_by == 'expected_points':
            if search_request.sort_order == 'desc':
                query = query.order_by(PlayerPrediction.expected_points.desc().nullslast())
            else:
                query = query.order_by(PlayerPrediction.expected_points.asc().nullsfirst())
        elif search_request.sort_by == 'form':
            if search_request.sort_order == 'desc':
                query = query.order_by(Player.form.desc().nullslast())
            else:
                query = query.order_by(Player.form.asc().nullsfirst())
        elif search_request.sort_by == 'total_points':
            if search_request.sort_order == 'desc':
                query = query.order_by(Player.total_points.desc())
            else:
                query = query.order_by(Player.total_points.asc())
        elif search_request.sort_by == 'now_cost':
            if search_request.sort_order == 'desc':
                query = query.order_by(Player.now_cost.desc())
            else:
                query = query.order_by(Player.now_cost.asc())
        elif search_request.sort_by == 'web_name':
            if search_request.sort_order == 'desc':
                query = query.order_by(Player.web_name.desc())
            else:
                query = query.order_by(Player.web_name.asc())
        
        # Get total count before limit
        total_count = query.count()
        
        # Apply limit
        query = query.limit(search_request.limit)
        
        # Execute query
        results = query.all()
        
        # Convert to PlayerStats objects
        from ..models.data_models import PlayerStats
        players = []
        
        for row in results:
            try:
                player_stats = PlayerStats(
                    player_id=row.player_id,
                    web_name=row.web_name,
                    position=row.position,
                    team_id=row.team_name,  # Using team name for display
                    now_cost=row.now_cost / 10.0,
                    expected_points=float(row.expected_points or 0),
                    form=float(row.form or 0),
                    total_points=row.total_points,
                    points_per_game=float(row.points_per_game or 0),
                    expected_goals=float(row.expected_goals or 0),
                    expected_assists=float(row.expected_assists or 0),
                    minutes=row.minutes or 0
                )
                players.append(player_stats)
            except Exception as e:
                logger.warning(f"Error converting player {row.player_id}: {e}")
                continue
        
        return PlayerSearchResponse(
            players=players,
            total_count=total_count,
            search_params=search_request
        )
        
    except Exception as e:
        logger.error(f"Error performing player search: {e}")
        return PlayerSearchResponse(
            players=[],
            total_count=0,
            search_params=search_request
        )


def get_detailed_player_info(player_id: int) -> Optional[Dict[str, Any]]:
    """Get detailed information for a specific player."""
    try:
        # Basic player info
        player_query = db.session.query(
            Player,
            Team.name.label('team_name'),
            Team.short_name.label('team_short'),
            PlayerPrediction.expected_points,
            PlayerPrediction.expected_minutes,
            PlayerPrediction.expected_goals,
            PlayerPrediction.expected_assists,
            PlayerPrediction.confidence_score
        ).join(
            Team, Player.team_id == Team.team_id
        ).join(
            PlayerPrediction, Player.player_id == PlayerPrediction.player_id,
            isouter=True
        ).filter(
            Player.player_id == player_id
        ).first()
        
        if not player_query:
            return None
        
        player = player_query[0]
        
        # Recent performance stats
        recent_stats = get_player_recent_performance(player_id, games=5)
        
        # Fixture difficulty
        upcoming_fixtures = get_player_upcoming_fixtures(player_id, count=5)
        
        # Value metrics
        value_metrics = calculate_player_value_metrics(player)
        
        return {
            'basic_info': {
                'player_id': player.player_id,
                'web_name': player.web_name,
                'full_name': f"{player.first_name} {player.second_name}",
                'position': player.position,
                'team_name': player_query.team_name,
                'team_short': player_query.team_short,
                'status': player.status,
                'cost': player.now_cost / 10.0
            },
            'performance': {
                'total_points': player.total_points,
                'form': float(player.form or 0),
                'points_per_game': float(player.points_per_game or 0),
                'minutes': player.minutes or 0,
                'starts': player.starts or 0,
                'expected_goals': float(player.expected_goals or 0),
                'expected_assists': float(player.expected_assists or 0)
            },
            'predictions': {
                'expected_points': float(player_query.expected_points or 0),
                'expected_minutes': float(player_query.expected_minutes or 0),
                'expected_goals': float(player_query.expected_goals or 0),
                'expected_assists': float(player_query.expected_assists or 0),
                'confidence_score': float(player_query.confidence_score or 0)
            },
            'recent_stats': recent_stats,
            'upcoming_fixtures': upcoming_fixtures,
            'value_metrics': value_metrics
        }
        
    except Exception as e:
        logger.error(f"Error getting detailed info for player {player_id}: {e}")
        return None


def get_player_comparison(player_ids: List[int]) -> Dict[str, Any]:
    """Compare multiple players across key metrics."""
    try:
        comparison_data = {
            'players': [],
            'metrics': [
                'cost', 'total_points', 'form', 'expected_points',
                'points_per_game', 'expected_goals', 'expected_assists', 'minutes'
            ]
        }
        
        for player_id in player_ids:
            player_info = get_detailed_player_info(player_id)
            if player_info:
                comparison_data['players'].append(player_info)
        
        # Calculate comparative rankings
        if len(comparison_data['players']) >= 2:
            comparison_data['rankings'] = calculate_comparison_rankings(comparison_data['players'])
        
        return comparison_data
        
    except Exception as e:
        logger.error(f"Error comparing players: {e}")
        return {'players': [], 'metrics': []}


def get_position_statistics() -> Dict[str, Any]:
    """Get statistics by position."""
    try:
        stats = {}
        
        for position in ['GKP', 'DEF', 'MID', 'FWD']:
            position_query = db.session.query(
                func.count(Player.player_id).label('count'),
                func.avg(Player.now_cost).label('avg_cost'),
                func.avg(Player.total_points).label('avg_points'),
                func.avg(Player.form).label('avg_form'),
                func.max(Player.total_points).label('max_points'),
                func.min(Player.now_cost).label('min_cost'),
                func.max(Player.now_cost).label('max_cost')
            ).filter(
                Player.position == position,
                Player.status == 'a'
            ).first()
            
            if position_query:
                stats[position] = {
                    'count': position_query.count,
                    'avg_cost': round(position_query.avg_cost / 10.0, 1) if position_query.avg_cost else 0,
                    'avg_points': round(position_query.avg_points, 1) if position_query.avg_points else 0,
                    'avg_form': round(position_query.avg_form, 1) if position_query.avg_form else 0,
                    'max_points': position_query.max_points or 0,
                    'min_cost': round(position_query.min_cost / 10.0, 1) if position_query.min_cost else 0,
                    'max_cost': round(position_query.max_cost / 10.0, 1) if position_query.max_cost else 0
                }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting position statistics: {e}")
        return {}


def get_price_ranges() -> Dict[str, float]:
    """Get price ranges for filters."""
    try:
        price_query = db.session.query(
            func.min(Player.now_cost).label('min_price'),
            func.max(Player.now_cost).label('max_price')
        ).filter(Player.status == 'a').first()
        
        if price_query:
            return {
                'min': round(price_query.min_price / 10.0, 1),
                'max': round(price_query.max_price / 10.0, 1)
            }
        
        return {'min': 3.9, 'max': 15.0}  # Default ranges
        
    except Exception as e:
        logger.error(f"Error getting price ranges: {e}")
        return {'min': 3.9, 'max': 15.0}


def get_player_recent_performance(player_id: int, games: int = 5) -> List[Dict]:
    """Get recent performance stats for player."""
    try:
        recent_stats = db.session.query(
            PlayerPastStats.total_points,
            PlayerPastStats.minutes,
            PlayerPastStats.goals_scored,
            PlayerPastStats.assists,
            PlayerPastStats.clean_sheets,
            PlayerPastStats.was_home,
            Fixture.gameweek
        ).join(
            Fixture, PlayerPastStats.fixture_id == Fixture.fixture_id
        ).filter(
            PlayerPastStats.player_id == player_id
        ).order_by(
            Fixture.gameweek.desc()
        ).limit(games).all()
        
        return [
            {
                'gameweek': stat.gameweek,
                'points': stat.total_points,
                'minutes': stat.minutes,
                'goals': stat.goals_scored,
                'assists': stat.assists,
                'clean_sheet': stat.clean_sheets > 0,
                'home': stat.was_home
            }
            for stat in recent_stats
        ]
        
    except Exception as e:
        logger.error(f"Error getting recent performance for player {player_id}: {e}")
        return []


def get_player_upcoming_fixtures(player_id: int, count: int = 5) -> List[Dict]:
    """Get upcoming fixtures for player."""
    try:
        player = Player.query.get(player_id)
        if not player:
            return []
        
        upcoming = db.session.query(
            Fixture.gameweek,
            Fixture.kickoff_time,
            Fixture.home_team_id,
            Fixture.away_team_id,
            Fixture.home_difficulty,
            Fixture.away_difficulty,
            Team.name.label('opponent_name'),
            Team.short_name.label('opponent_short')
        ).join(
            Team,
            or_(
                and_(Fixture.home_team_id == player.team_id, Team.team_id == Fixture.away_team_id),
                and_(Fixture.away_team_id == player.team_id, Team.team_id == Fixture.home_team_id)
            )
        ).filter(
            or_(
                Fixture.home_team_id == player.team_id,
                Fixture.away_team_id == player.team_id
            ),
            Fixture.finished == False
        ).order_by(
            Fixture.kickoff_time.asc().nullslast(),
            Fixture.gameweek.asc()
        ).limit(count).all()
        
        fixtures = []
        for fixture in upcoming:
            is_home = fixture.home_team_id == player.team_id
            difficulty = fixture.home_difficulty if is_home else fixture.away_difficulty
            
            fixtures.append({
                'gameweek': fixture.gameweek,
                'opponent': fixture.opponent_name,
                'opponent_short': fixture.opponent_short,
                'is_home': is_home,
                'difficulty': difficulty or 3,
                'kickoff': fixture.kickoff_time.strftime('%Y-%m-%d %H:%M') if fixture.kickoff_time else 'TBD'
            })
        
        return fixtures
        
    except Exception as e:
        logger.error(f"Error getting upcoming fixtures for player {player_id}: {e}")
        return []


def calculate_player_value_metrics(player: Player) -> Dict[str, float]:
    """Calculate value metrics for a player."""
    try:
        cost = player.now_cost / 10.0
        
        metrics = {
            'points_per_million': (player.total_points / cost) if cost > 0 else 0,
            'form_per_million': (float(player.form or 0) / cost) if cost > 0 else 0,
            'minutes_per_million': ((player.minutes or 0) / cost) if cost > 0 else 0
        }
        
        # Round to 2 decimal places
        return {k: round(v, 2) for k, v in metrics.items()}
        
    except Exception as e:
        logger.error(f"Error calculating value metrics: {e}")
        return {'points_per_million': 0, 'form_per_million': 0, 'minutes_per_million': 0}


def get_form_trending_players(direction: str, limit: int = 10) -> List[Dict]:
    """Get players trending up or down in form."""
    try:
        order_func = Player.form.desc() if direction == 'up' else Player.form.asc()
        
        trending = db.session.query(
            Player.player_id,
            Player.web_name,
            Player.position,
            Player.form,
            Team.short_name
        ).join(
            Team, Player.team_id == Team.team_id
        ).filter(
            Player.status == 'a',
            Player.form.isnot(None)
        ).order_by(
            order_func
        ).limit(limit).all()
        
        return [
            {
                'player_id': player.player_id,
                'name': player.web_name,
                'position': player.position,
                'team': player.short_name,
                'form': float(player.form)
            }
            for player in trending
        ]
        
    except Exception as e:
        logger.error(f"Error getting form trending players: {e}")
        return []


def get_price_trending_players(direction: str, limit: int = 10) -> List[Dict]:
    """Get players with highest/lowest prices."""
    try:
        order_func = Player.now_cost.desc() if direction == 'up' else Player.now_cost.asc()
        
        trending = db.session.query(
            Player.player_id,
            Player.web_name,
            Player.position,
            Player.now_cost,
            Team.short_name
        ).join(
            Team, Player.team_id == Team.team_id
        ).filter(
            Player.status == 'a'
        ).order_by(
            order_func
        ).limit(limit).all()
        
        return [
            {
                'player_id': player.player_id,
                'name': player.web_name,
                'position': player.position,
                'team': player.short_name,
                'cost': player.now_cost / 10.0
            }
            for player in trending
        ]
        
    except Exception as e:
        logger.error(f"Error getting price trending players: {e}")
        return []


def get_transfer_trending_players(limit: int = 10) -> List[Dict]:
    """Get players that are good transfer targets."""
    try:
        # This is a simplified version - in reality you'd track transfer data
        # For now, we'll use expected points as a proxy
        trending = db.session.query(
            Player.player_id,
            Player.web_name,
            Player.position,
            Player.now_cost,
            PlayerPrediction.expected_points,
            Team.short_name
        ).join(
            Team, Player.team_id == Team.team_id
        ).join(
            PlayerPrediction, Player.player_id == PlayerPrediction.player_id
        ).filter(
            Player.status == 'a',
            PlayerPrediction.expected_points.isnot(None)
        ).order_by(
            PlayerPrediction.expected_points.desc()
        ).limit(limit).all()
        
        return [
            {
                'player_id': player.player_id,
                'name': player.web_name,
                'position': player.position,
                'team': player.short_name,
                'cost': player.now_cost / 10.0,
                'expected_points': float(player.expected_points)
            }
            for player in trending
        ]
        
    except Exception as e:
        logger.error(f"Error getting transfer trending players: {e}")
        return []


def calculate_comparison_rankings(players: List[Dict]) -> Dict[str, List[int]]:
    """Calculate rankings for player comparison."""
    try:
        metrics = ['cost', 'total_points', 'form', 'expected_points']
        rankings = {}
        
        for metric in metrics:
            # Extract values for this metric
            values = []
            for i, player in enumerate(players):
                if metric in ['cost']:
                    value = player['basic_info'].get(metric, 0)
                elif metric in ['total_points', 'form']:
                    value = player['performance'].get(metric, 0)
                elif metric in ['expected_points']:
                    value = player['predictions'].get(metric, 0)
                else:
                    value = 0
                
                values.append((value, i))
            
            # Sort and create rankings (higher is better except for cost)
            reverse = metric != 'cost'
            values.sort(key=lambda x: x[0], reverse=reverse)
            
            # Create ranking list
            ranking = [0] * len(players)
            for rank, (_, player_idx) in enumerate(values):
                ranking[player_idx] = rank + 1
            
            rankings[metric] = ranking
        
        return rankings
        
    except Exception as e:
        logger.error(f"Error calculating comparison rankings: {e}")
        return {}