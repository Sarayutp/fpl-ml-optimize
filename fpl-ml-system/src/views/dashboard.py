"""Dashboard views for FPL AI Optimizer."""

import logging
from datetime import datetime
from typing import Dict, Any

from flask import Blueprint, render_template, current_app, jsonify, request
from sqlalchemy import func

from ..models.db_models import db, Player, Team, PlayerPrediction, Fixture


logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
def index():
    """Main dashboard page."""
    try:
        # Get dashboard statistics
        stats = get_dashboard_stats()
        
        # Get top performers
        top_players = get_top_performers(limit=10)
        
        # Get upcoming fixtures
        upcoming_fixtures = get_upcoming_fixtures(limit=5)
        
        # Get recent updates
        recent_updates = get_recent_updates()
        
        return render_template('dashboard.html',
                             stats=stats,
                             top_players=top_players,
                             upcoming_fixtures=upcoming_fixtures,
                             recent_updates=recent_updates)
        
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        current_app.logger.error(f"Dashboard error: {e}")
        
        # Return minimal dashboard on error
        return render_template('dashboard.html',
                             stats={},
                             top_players=[],
                             upcoming_fixtures=[],
                             recent_updates={})


@dashboard_bp.route('/stats')
def dashboard_stats():
    """API endpoint for dashboard statistics."""
    try:
        stats = get_dashboard_stats()
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dashboard_bp.route('/top-players')
def top_players():
    """API endpoint for top performing players."""
    try:
        limit = request.args.get('limit', 10, type=int)
        position = request.args.get('position', None)
        
        players = get_top_performers(limit=limit, position=position)
        
        return jsonify({
            'success': True,
            'data': players
        })
    except Exception as e:
        logger.error(f"Error getting top players: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def get_dashboard_stats() -> Dict[str, Any]:
    """Get key statistics for the dashboard."""
    try:
        # Player statistics
        total_players = Player.query.filter(Player.status == 'a').count()
        
        # Team statistics
        total_teams = Team.query.count()
        
        # Predictions statistics
        total_predictions = PlayerPrediction.query.count()
        recent_predictions = PlayerPrediction.query.filter(
            PlayerPrediction.last_updated >= datetime.now().date()
        ).count()
        
        # Average expected points
        avg_expected_points = db.session.query(
            func.avg(PlayerPrediction.expected_points)
        ).scalar() or 0
        
        # Fixture statistics
        total_fixtures = Fixture.query.count()
        upcoming_fixtures = Fixture.query.filter(
            Fixture.finished == False,
            Fixture.kickoff_time >= datetime.now()
        ).count()
        
        # Price statistics
        price_stats = db.session.query(
            func.min(Player.now_cost).label('min_price'),
            func.max(Player.now_cost).label('max_price'),
            func.avg(Player.now_cost).label('avg_price')
        ).filter(Player.status == 'a').first()
        
        return {
            'total_players': total_players,
            'total_teams': total_teams,
            'total_predictions': total_predictions,
            'recent_predictions': recent_predictions,
            'avg_expected_points': round(avg_expected_points, 2),
            'total_fixtures': total_fixtures,
            'upcoming_fixtures': upcoming_fixtures,
            'min_price': (price_stats.min_price / 10.0) if price_stats.min_price else 0,
            'max_price': (price_stats.max_price / 10.0) if price_stats.max_price else 0,
            'avg_price': (price_stats.avg_price / 10.0) if price_stats.avg_price else 0,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return {}


def get_top_performers(limit: int = 10, position: str = None) -> list:
    """Get top performing players based on predictions."""
    try:
        query = db.session.query(
            Player.player_id,
            Player.web_name,
            Player.position,
            Player.now_cost,
            Player.total_points,
            Player.form,
            Team.short_name,
            PlayerPrediction.expected_points
        ).join(
            Team, Player.team_id == Team.team_id
        ).join(
            PlayerPrediction, Player.player_id == PlayerPrediction.player_id,
            isouter=True
        ).filter(
            Player.status == 'a'
        )
        
        # Filter by position if specified
        if position:
            query = query.filter(Player.position == position)
        
        # Order by expected points (with fallback to total points)
        query = query.order_by(
            PlayerPrediction.expected_points.desc().nullslast(),
            Player.total_points.desc()
        ).limit(limit)
        
        players = []
        for row in query.all():
            players.append({
                'player_id': row.player_id,
                'web_name': row.web_name,
                'position': row.position,
                'team': row.short_name,
                'cost': row.now_cost / 10.0,
                'total_points': row.total_points,
                'form': float(row.form or 0),
                'expected_points': float(row.expected_points or 0),
                'value': (row.total_points / (row.now_cost / 10.0)) if row.now_cost > 0 else 0
            })
        
        return players
        
    except Exception as e:
        logger.error(f"Error getting top performers: {e}")
        return []


def get_upcoming_fixtures(limit: int = 5) -> list:
    """Get upcoming fixtures."""
    try:
        query = db.session.query(
            Fixture.fixture_id,
            Fixture.gameweek,
            Fixture.kickoff_time,
            Fixture.home_difficulty,
            Fixture.away_difficulty,
            Team.name.label('home_team'),
            Team.short_name.label('home_short')
        ).join(
            Team, Fixture.home_team_id == Team.team_id
        ).filter(
            Fixture.finished == False,
            Fixture.kickoff_time >= datetime.now()
        ).order_by(
            Fixture.kickoff_time.asc()
        ).limit(limit)
        
        fixtures = []
        for row in query.all():
            # Get away team info
            away_team = Team.query.get(row.fixture_id)  # This would need proper join
            
            fixtures.append({
                'fixture_id': row.fixture_id,
                'gameweek': row.gameweek,
                'kickoff_time': row.kickoff_time.strftime('%Y-%m-%d %H:%M') if row.kickoff_time else 'TBD',
                'home_team': row.home_team,
                'home_short': row.home_short,
                'away_team': away_team.name if away_team else 'Unknown',
                'away_short': away_team.short_name if away_team else 'UNK',
                'home_difficulty': row.home_difficulty or 3,
                'away_difficulty': row.away_difficulty or 3
            })
        
        return fixtures
        
    except Exception as e:
        logger.error(f"Error getting upcoming fixtures: {e}")
        return []


def get_recent_updates() -> Dict[str, Any]:
    """Get information about recent data updates."""
    try:
        # Most recent player update
        latest_player_update = db.session.query(
            func.max(Player.updated_at)
        ).scalar()
        
        # Most recent prediction update
        latest_prediction_update = db.session.query(
            func.max(PlayerPrediction.last_updated)
        ).scalar()
        
        # Count of players updated today
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        players_updated_today = Player.query.filter(
            Player.updated_at >= today_start
        ).count()
        
        return {
            'latest_player_update': latest_player_update.strftime('%Y-%m-%d %H:%M:%S') if latest_player_update else 'Never',
            'latest_prediction_update': latest_prediction_update.strftime('%Y-%m-%d %H:%M:%S') if latest_prediction_update else 'Never',
            'players_updated_today': players_updated_today,
            'data_freshness': 'Current' if latest_player_update and (datetime.now() - latest_player_update).hours < 6 else 'Outdated'
        }
        
    except Exception as e:
        logger.error(f"Error getting recent updates: {e}")
        return {
            'latest_player_update': 'Unknown',
            'latest_prediction_update': 'Unknown',
            'players_updated_today': 0,
            'data_freshness': 'Unknown'
        }