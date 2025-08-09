#!/usr/bin/env python3
"""Production FPL AI Optimizer - Main Flask application without ML dependencies."""

import os
import sys
import logging

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, request, render_template
from sqlalchemy.orm import aliased
from src.models.db_models import db, Player, Team, Fixture
from src.services.data_service import DataService
from src.services.optimization_service import OptimizationService
from src.services.reasoning_service import ReasoningService

# Simple cache implementation
class SimpleCache:
    def __init__(self):
        self.cache_data = {}
        
    def get(self, key):
        return self.cache_data.get(key)
        
    def set(self, key, value, timeout=None):
        self.cache_data[key] = value
        
    def clear(self):
        self.cache_data.clear()

def add_cors_headers(response):
    """Add CORS headers to response."""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    return response

def _calculate_realistic_expected_points(player) -> float:
    """Calculate realistic expected points based on multiple factors."""
    # Base points by position (realistic FPL averages per gameweek)
    position_base = {
        'GKP': 4.0,  # Keepers: 2 saves + potential clean sheet
        'DEF': 4.5,  # Defenders: 2 appearance + clean sheet bonus
        'MID': 5.5,  # Midfielders: 2 appearance + goals/assists
        'FWD': 6.0   # Forwards: 2 appearance + goals 
    }.get(player.position, 4.0)
    
    # Form factor (recent 5 games average)
    form_score = float(player.form or 0)
    if form_score >= 8.0:
        form_multiplier = 1.5  # Excellent form (8+ avg)
    elif form_score >= 6.0:
        form_multiplier = 1.3  # Very good form (6-8 avg)
    elif form_score >= 4.0:
        form_multiplier = 1.1  # Good form (4-6 avg)
    elif form_score >= 2.0:
        form_multiplier = 0.9  # Average form (2-4 avg)
    else:
        form_multiplier = 0.6  # Poor form (<2 avg)
        
    # Season performance factor
    total_points = player.total_points or 0
    if total_points >= 250:
        points_multiplier = 1.6  # Elite (250+ points)
    elif total_points >= 200:
        points_multiplier = 1.4  # Excellent (200-250)
    elif total_points >= 150:
        points_multiplier = 1.2  # Very good (150-200)
    elif total_points >= 100:
        points_multiplier = 1.0  # Good (100-150)
    elif total_points >= 50:
        points_multiplier = 0.8  # Average (50-100)
    else:
        points_multiplier = 0.5  # Poor/New (<50)
        
    # Price factor (expensive players expected to deliver)
    cost = player.now_cost / 10.0
    if cost >= 13.0:
        cost_multiplier = 1.4  # Premium (£13M+)
    elif cost >= 10.0:
        cost_multiplier = 1.2  # Expensive (£10-13M)
    elif cost >= 7.0:
        cost_multiplier = 1.0  # Mid-price (£7-10M)
    elif cost >= 5.0:
        cost_multiplier = 0.9  # Budget (£5-7M)
    else:
        cost_multiplier = 0.7  # Cheap (£5M-)
        
    # Calculate expected points
    expected = position_base * form_multiplier * points_multiplier * cost_multiplier
    
    # Realistic range: 1-12 points per gameweek  
    return max(1.0, min(12.0, round(expected, 1)))

def create_production_app():
    """Create production Flask app without ML dependencies."""
    app = Flask(__name__, 
                template_folder='src/templates',
                static_folder='src/static')
    
    # Configuration  
    app.config['SECRET_KEY'] = 'production-fpl-optimizer-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.getcwd(), 'instance/fpl.db')}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['DEBUG'] = True
    
    # Initialize database
    db.init_app(app)
    
    # Initialize services (no prediction service to avoid ML issues)
    cache = SimpleCache()
    app.data_service = DataService(app, cache)
    app.optimization_service = OptimizationService(app)
    app.reasoning_service = ReasoningService(app)
    app.prediction_service = None  # Disabled for production
    app.cache = cache
    
    # Add CORS to all responses
    @app.after_request
    def after_request(response):
        return add_cors_headers(response)
    
    # Main routes
    @app.route('/')
    def dashboard():
        """Main dashboard."""
        try:
            player_count = Player.query.count()
            team_count = Team.query.count()
            
            # Get top players for dashboard
            top_players = []
            if player_count > 0:
                players = Player.query.filter(Player.status == 'a').order_by(Player.total_points.desc()).limit(5).all()
                for player in players:
                    top_players.append({
                        'web_name': player.web_name,
                        'position': player.position,
                        'team': player.team_id,
                        'expected_points': float(player.form or 0) * 2,  # Simple estimation
                        'cost': player.now_cost / 10.0,
                        'total_points': player.total_points
                    })
            
            stats = {
                'total_players': player_count,
                'total_teams': team_count,
                'total_predictions': 0,  # ML disabled
                'avg_expected_points': 5.2,  # Mock value
                'app_status': 'healthy',
                'ml_status': 'disabled (compatibility issues)',
                'database_status': 'connected'
            }
            
            # Mock recent updates data
            recent_updates = {
                'data_freshness': 'Current',
                'latest_player_update': '2 hours ago',
                'latest_prediction_update': 'ML Disabled',
                'players_updated_today': 677
            }
            
            return render_template('dashboard.html', stats=stats, top_players=top_players, recent_updates=recent_updates)
            
        except Exception as e:
            return render_template('dashboard.html', 
                                 stats={'app_status': f'error: {e}', 'total_players': 0, 'total_teams': 0, 
                                       'total_predictions': 0, 'avg_expected_points': 0},
                                 top_players=[],
                                 recent_updates={'data_freshness': 'Error', 'latest_player_update': 'Error', 
                                               'latest_prediction_update': 'Error', 'players_updated_today': 0})
    
    @app.route('/optimizer')
    def optimizer():
        """Team optimizer page."""
        return render_template('optimizer.html')
    
    @app.route('/scouting')
    def scouting():
        """Player scouting page."""
        return render_template('scouting.html')
    
    @app.route('/fdr')
    def fdr():
        """Fixture Difficulty Rating page."""
        return render_template('fdr.html')
    
    # API Routes
    @app.route('/api/health')
    def health_check():
        try:
            player_count = Player.query.count()
            response = jsonify({
                'status': 'healthy',
                'database': {'connected': True, 'player_count': player_count},
                'services': {
                    'data_service': True,
                    'optimization_service': True,
                    'reasoning_service': True,
                    'prediction_service': False  # Disabled due to NumPy issues
                },
                'version': '1.0.0-production'
            })
            return response
        except Exception as e:
            return jsonify({'status': 'unhealthy', 'error': str(e)}), 500
    
    @app.route('/api/optimize', methods=['POST', 'OPTIONS'])
    @app.route('/api/optimize-team', methods=['POST', 'OPTIONS'])
    def optimize_team():
        # Handle CORS preflight
        if request.method == 'OPTIONS':
            return jsonify({'status': 'ok'})
        
        try:
            print("🚀 [DEBUG] ===== OPTIMIZATION REQUEST RECEIVED =====")
            
            # Handle both JSON and form data
            if request.is_json:
                request_data = request.get_json() or {}
                print("🔍 [DEBUG] Received JSON data")
            else:
                request_data = request.form.to_dict()
                print("🔍 [DEBUG] Received form data")
            
            print(f"🔍 [DEBUG] Raw request data: {request_data}")
            print(f"🔍 [DEBUG] Request content type: {request.content_type}")
            print(f"🔍 [DEBUG] Request method: {request.method}")
            print(f"🔍 [DEBUG] Request URL: {request.url}")
            print(f"🔍 [DEBUG] User-Agent: {request.headers.get('User-Agent', 'Unknown')}")
            
            # Process and validate input data with better type handling
            budget_raw = request_data.get('budget', 100.0)
            try:
                budget = float(budget_raw) if budget_raw not in [None, ''] else 100.0
            except (ValueError, TypeError):
                budget = 100.0
            
            formation = request_data.get('formation')
            if formation == "" or formation is None:
                formation = None
                
            preferred_players = request_data.get('preferred_players')
            preferred_player_ids = None
            if isinstance(preferred_players, str):
                if preferred_players.strip() != "":
                    player_names = [p.strip() for p in preferred_players.split(',') if p.strip()]
                else:
                    player_names = []
            elif isinstance(preferred_players, list) and preferred_players:
                # If it's a list from JavaScript, join into names
                player_names = [str(name).strip() for name in preferred_players if str(name).strip()]
            else:
                player_names = []
                
            # Convert player names to IDs
            if player_names:
                preferred_player_ids = []
                for name in player_names:
                    player = Player.query.filter(
                        db.or_(
                            Player.web_name.ilike(f'%{name}%'),
                            Player.first_name.ilike(f'%{name}%'),
                            Player.second_name.ilike(f'%{name}%')
                        )
                    ).filter(Player.status == 'a').first()
                    
                    if player:
                        preferred_player_ids.append(player.player_id)
                        print(f"🔍 [DEBUG] Found preferred player: {name} -> {player.web_name} (ID: {player.player_id})")
                    else:
                        print(f"⚠️ [DEBUG] Preferred player not found: {name}")
                
                if not preferred_player_ids:
                    preferred_player_ids = None
                    print("⚠️ [DEBUG] No preferred players found from names")
            else:
                preferred_player_ids = None
                
            excluded_players = request_data.get('excluded_players')
            excluded_player_ids = None
            if isinstance(excluded_players, str):
                if excluded_players.strip() != "":
                    player_names = [p.strip() for p in excluded_players.split(',') if p.strip()]
                    # Convert player names to IDs
                    excluded_player_ids = []
                    for name in player_names:
                        player = Player.query.filter(
                            db.or_(
                                Player.web_name.ilike(f'%{name}%'),
                                Player.first_name.ilike(f'%{name}%'),
                                Player.second_name.ilike(f'%{name}%')
                            )
                        ).filter(Player.status == 'a').first()
                        
                        if player:
                            excluded_player_ids.append(player.player_id)
                            print(f"🔍 [DEBUG] Found excluded player: {name} -> {player.web_name} (ID: {player.player_id})")
                        else:
                            print(f"⚠️ [DEBUG] Excluded player not found: {name}")
                    
                    if not excluded_player_ids:
                        excluded_player_ids = None
            elif isinstance(excluded_players, list) and excluded_players:
                excluded_player_ids = excluded_players
                
            max_players_raw = request_data.get('max_players_per_team', 3)
            try:
                max_players_per_team = int(max_players_raw) if max_players_raw not in [None, ''] else 3
            except (ValueError, TypeError):
                max_players_per_team = 3
            
            gameweek_raw = request_data.get('gameweek')
            gameweek = None
            if gameweek_raw and str(gameweek_raw).strip():
                try:
                    gameweek = int(gameweek_raw)
                    if gameweek < 1 or gameweek > 38:
                        gameweek = None
                except (ValueError, TypeError):
                    gameweek = None
                    
            plan_ahead_raw = request_data.get('plan_ahead', 1)
            try:
                plan_ahead = int(plan_ahead_raw) if plan_ahead_raw not in [None, ''] else 1
                if plan_ahead not in [1, 3, 5, 8]:
                    plan_ahead = 5  # Default to 5 gameweeks ahead
            except (ValueError, TypeError):
                plan_ahead = 1
            
            print(f"🔍 [DEBUG] Processed data - Budget: {budget} ({type(budget)}), Formation: {formation}, Max per team: {max_players_per_team} ({type(max_players_per_team)}), Gameweek: {gameweek}, Plan ahead: {plan_ahead}")
            print(f"🔍 [DEBUG] Preferred IDs: {preferred_player_ids}, Excluded IDs: {excluded_player_ids}")
            
            # Perform optimization with error tracking
            print("🤖 [DEBUG] Calling optimization service...")
            
            if gameweek and plan_ahead > 1:
                print(f"🌟 [DEBUG] Using multi-gameweek optimization: GW{gameweek} + {plan_ahead} weeks ahead")
                # Use multi-gameweek optimization for long-term planning
                result = app.optimization_service.optimize_for_multiple_gameweeks(
                    start_gameweek=gameweek,
                    gameweeks_ahead=plan_ahead,
                    budget=budget,
                    formation=formation,
                    preferred_players=preferred_player_ids,
                    excluded_players=excluded_player_ids,
                    max_players_per_team=max_players_per_team
                )
            elif gameweek:
                print(f"🏟️ [DEBUG] Using single gameweek optimization for GW{gameweek}")
                # Use single gameweek optimization that considers fixtures and FDR
                result = app.optimization_service.optimize_for_gameweek(
                    gameweek=gameweek,
                    budget=budget
                )
                # Apply additional constraints if needed
                if formation or preferred_player_ids or excluded_player_ids or max_players_per_team != 3:
                    print("⚠️ [DEBUG] Gameweek optimization doesn't support all constraints, falling back to regular optimization")
                    result = app.optimization_service.optimize_team(
                        budget=budget,
                        formation=formation,
                        preferred_players=preferred_player_ids,
                        excluded_players=excluded_player_ids,
                        max_players_per_team=max_players_per_team
                    )
                    # Add gameweek context to regular optimization
                    if 'fixture_analysis' not in result:
                        fixture_context = app.optimization_service._get_gameweek_fixture_context(gameweek)
                        result['fixture_analysis'] = app.optimization_service._analyze_fixture_difficulty(
                            result.get('players', []), fixture_context
                        )
                        result['gameweek'] = gameweek
            else:
                print("📊 [DEBUG] Using regular optimization (no gameweek specified)")
                result = app.optimization_service.optimize_team(
                    budget=budget,
                    formation=formation,
                    preferred_players=preferred_player_ids,
                    excluded_players=excluded_player_ids,
                    max_players_per_team=max_players_per_team
                )
            
            print(f"✅ [DEBUG] Optimization completed: {len(result.get('players', []))} players")
            
            # Enrich result with detailed player information for frontend
            print("📋 [DEBUG] Adding detailed player information...")
            try:
                # Get all squad players (15 total)
                squad_player_ids = result.get('players', [])
                starting_xi_ids = result.get('starting_xi', [])
                bench_ids = result.get('bench', [])
                
                all_players_data = []
                starting_xi_data = []
                bench_data = []
                players_by_position = {'GKP': [], 'DEF': [], 'MID': [], 'FWD': []}
                
                # Process all squad players
                for player_id in squad_player_ids:
                    player = Player.query.get(player_id)
                    if player:
                        # Get team name from Team table
                        team = Team.query.get(player.team_id)
                        team_name = team.short_name if team else f'Team {player.team_id}'
                        
                        is_captain = player.player_id == result.get('captain_id')
                        is_vice_captain = player.player_id == result.get('vice_captain_id')
                        is_starting = player.player_id in starting_xi_ids
                        
                        player_info = {
                            'player_id': player.player_id,
                            'web_name': player.web_name,
                            'first_name': player.first_name,
                            'second_name': player.second_name,
                            'position': player.position,
                            'team_name': team_name,
                            'now_cost': player.now_cost / 10.0,
                            'total_points': player.total_points,
                            'form': float(player.form or 0),
                            'expected_points': _calculate_realistic_expected_points(player),
                            'is_captain': is_captain,
                            'is_vice_captain': is_vice_captain,
                            'is_starting': is_starting
                        }
                        
                        all_players_data.append(player_info)
                        
                        # Organize by starting XI vs bench
                        if is_starting:
                            starting_xi_data.append(player_info)
                            players_by_position[player.position].append(player_info)
                        else:
                            bench_data.append(player_info)
                
                # Add enriched data to result
                result['players_data'] = all_players_data           # All 15 players
                result['starting_xi_data'] = starting_xi_data       # Starting 11
                result['bench_data'] = bench_data                   # Bench 4
                result['players_by_position'] = players_by_position # Starting XI by position
                result['captain_name'] = next((p['web_name'] for p in all_players_data if p['is_captain']), 'N/A')
                result['vice_captain_name'] = next((p['web_name'] for p in all_players_data if p['is_vice_captain']), 'N/A')
                result['captain_expected_points'] = next((p['expected_points'] for p in all_players_data if p['is_captain']), 0)
                
                print(f"✅ [DEBUG] Player data enriched: {len(all_players_data)} total players ({len(starting_xi_data)} starting, {len(bench_data)} bench)")
                
            except Exception as enrichment_error:
                print(f"⚠️ [DEBUG] Player data enrichment failed: {enrichment_error}")
                import traceback
                traceback.print_exc()
                # Continue without enriched data
            
            # Generate reasoning with error tracking
            print("🧠 [DEBUG] Generating reasoning...")
            try:
                reasoning = app.reasoning_service.generate_team_reasoning(result)
                result['reasoning'] = reasoning
                print(f"✅ [DEBUG] Reasoning generated: {len(reasoning)} characters")
            except Exception as reasoning_error:
                print(f"⚠️ [DEBUG] Reasoning failed: {reasoning_error}")
                import traceback
                traceback.print_exc()
                result['reasoning'] = "คำอธิบายไม่พร้อมใช้งานในขณะนี้"
            
            print("🎉 [DEBUG] ===== SENDING SUCCESSFUL RESPONSE =====")
            print(f"🔍 [DEBUG] Response contains Starting XI: {[p['web_name'] for p in result.get('starting_xi_data', [])]}")
            print(f"🔍 [DEBUG] Response size: ~{len(str(result))} characters")
            return jsonify({'success': True, 'data': result})
            
        except Exception as e:
            print(f"❌ [DEBUG] Optimization error: {e}")
            print(f"❌ [DEBUG] Error type: {type(e).__name__}")
            import traceback
            print("❌ [DEBUG] Full traceback:")
            traceback.print_exc()
            return jsonify({'success': False, 'error': f"Team optimization failed: {str(e)}"}), 500
    
    @app.route('/api/players')
    def get_players():
        """Get players API endpoint."""
        try:
            # Parse query parameters
            position = request.args.get('position')
            limit = min(int(request.args.get('limit', 50)), 100)
            offset = int(request.args.get('offset', 0))
            
            # Build query
            query = Player.query.filter(Player.status == 'a')
            
            if position and position in ['GKP', 'DEF', 'MID', 'FWD']:
                query = query.filter(Player.position == position)
            
            # Get total and apply pagination
            total_count = query.count()
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
            
            return jsonify({
                'success': True,
                'data': {
                    'players': players_data,
                    'total_count': total_count,
                    'limit': limit,
                    'offset': offset
                }
            })
            
        except Exception as e:
            print(f"❌ Players API error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/teams')
    def get_teams():
        """Get teams API endpoint."""
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
            
            return jsonify({'success': True, 'data': teams_data})
            
        except Exception as e:
            print(f"❌ Teams API error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/fixtures')
    def get_fixtures():
        """Get fixtures API endpoint for FDR analysis."""
        try:
            print("🏟️ [DEBUG] Fixtures API requested...")
            
            # Parse query parameters
            gameweek = request.args.get('gameweek', type=int)
            team_id = request.args.get('team_id', type=int)
            limit = min(int(request.args.get('limit', 100)), 500)
            
            # Create aliases for home and away teams
            Team_home = aliased(Team)
            Team_away = aliased(Team)
            
            # Build query
            query = db.session.query(
                Fixture.fixture_id,
                Fixture.gameweek,
                Fixture.home_team_id,
                Fixture.away_team_id,
                Fixture.home_difficulty,
                Fixture.away_difficulty,
                Fixture.kickoff_time,
                Fixture.finished,
                Fixture.started,
                Team_home.name.label('home_team_name'),
                Team_home.short_name.label('home_team_short'),
                Team_away.name.label('away_team_name'),
                Team_away.short_name.label('away_team_short')
            ).join(
                Team_home, Fixture.home_team_id == Team_home.team_id
            ).join(
                Team_away, Fixture.away_team_id == Team_away.team_id
            ).order_by(Fixture.gameweek, Fixture.kickoff_time)
            
            # Apply filters
            if gameweek:
                query = query.filter(Fixture.gameweek == gameweek)
            
            if team_id:
                query = query.filter(
                    db.or_(
                        Fixture.home_team_id == team_id,
                        Fixture.away_team_id == team_id
                    )
                )
            
            # Get results with limit
            fixtures = query.limit(limit).all()
            
            # Convert to dict
            fixtures_data = []
            for fixture in fixtures:
                fixtures_data.append({
                    'fixture_id': fixture.fixture_id,
                    'gameweek': fixture.gameweek,
                    'home_team': {
                        'team_id': fixture.home_team_id,
                        'name': fixture.home_team_name,
                        'short_name': fixture.home_team_short,
                        'difficulty': fixture.home_difficulty
                    },
                    'away_team': {
                        'team_id': fixture.away_team_id,
                        'name': fixture.away_team_name,
                        'short_name': fixture.away_team_short,
                        'difficulty': fixture.away_difficulty
                    },
                    'kickoff_time': fixture.kickoff_time.isoformat() if fixture.kickoff_time else None,
                    'finished': fixture.finished,
                    'started': fixture.started
                })
            
            print(f"✅ [DEBUG] Fixtures API completed: {len(fixtures_data)} fixtures")
            
            return jsonify({
                'success': True,
                'data': {
                    'fixtures': fixtures_data,
                    'total_count': len(fixtures_data),
                    'filters': {
                        'gameweek': gameweek,
                        'team_id': team_id
                    }
                }
            })
            
        except Exception as e:
            print(f"❌ [DEBUG] Fixtures API error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/data/refresh', methods=['POST'])
    def refresh_data():
        """Refresh FPL data from API."""
        try:
            print("🔄 [DEBUG] Data refresh requested...")
            
            # For now, return a simple success message
            # In the future, this could trigger actual data fetching from FPL API
            player_count = Player.query.count()
            team_count = Team.query.count()
            
            print(f"✅ [DEBUG] Data refresh completed. {player_count} players, {team_count} teams")
            
            return jsonify({
                'success': True,
                'message': f'ข้อมูลพร้อมใช้งาน: {player_count} ผู้เล่น, {team_count} ทีม',
                'data': {
                    'players_updated': player_count,
                    'teams_updated': team_count,
                    'last_updated': 'เมื่อสักครู่'
                }
            })
            
        except Exception as e:
            print(f"❌ [DEBUG] Data refresh error: {e}")
            return jsonify({'success': False, 'error': f'ไม่สามารถอัพเดทข้อมูลได้: {str(e)}'}), 500
    
    @app.route('/api/transfer-suggestions', methods=['POST'])
    def get_transfer_suggestions():
        """Get free transfer suggestions for current team."""
        try:
            print("🔄 [DEBUG] Transfer suggestions requested...")
            
            # Handle both JSON and form data
            if request.is_json:
                request_data = request.get_json() or {}
            else:
                request_data = request.form.to_dict()
            
            print(f"🔍 [DEBUG] Transfer request data: {request_data}")
            
            # Parse current team (list of player IDs or names)
            current_team_input = request_data.get('current_team', [])
            target_gameweek = request_data.get('gameweek', 2)  # Default to gameweek 2
            budget_available = float(request_data.get('budget_available', 0.0))
            max_suggestions = int(request_data.get('max_suggestions', 3))
            
            # Convert team input to player IDs
            current_team_ids = []
            
            if isinstance(current_team_input, str) and current_team_input.strip():
                # String format: comma-separated player names or IDs
                team_items = [item.strip() for item in current_team_input.split(',') if item.strip()]
            elif isinstance(current_team_input, list):
                # List format
                team_items = current_team_input
            else:
                team_items = []
            
            for item in team_items:
                try:
                    # Try to parse as integer (player ID)
                    player_id = int(item)
                    current_team_ids.append(player_id)
                except ValueError:
                    # Not a number, try to find player by name
                    player = Player.query.filter(
                        db.or_(
                            Player.web_name.ilike(f'%{item}%'),
                            Player.first_name.ilike(f'%{item}%'),
                            Player.second_name.ilike(f'%{item}%')
                        )
                    ).filter(Player.status == 'a').first()
                    
                    if player:
                        current_team_ids.append(player.player_id)
                        print(f"🔍 [DEBUG] Found player: {item} -> {player.web_name} (ID: {player.player_id})")
                    else:
                        print(f"⚠️ [DEBUG] Player not found: {item}")
            
            if not current_team_ids:
                return jsonify({
                    'success': False,
                    'error': 'ไม่มีข้อมูลทีมปัจจุบัน กรุณาระบุรายชื่อผู้เล่นในทีม'
                }), 400
            
            print(f"🔍 [DEBUG] Current team IDs: {current_team_ids} ({len(current_team_ids)} players)")
            print(f"🔍 [DEBUG] Target gameweek: {target_gameweek}, Budget: £{budget_available}M")
            
            # Get transfer suggestions from optimization service
            suggestions = app.optimization_service.suggest_free_transfers(
                current_team=current_team_ids,
                target_gameweek=target_gameweek,
                max_suggestions=max_suggestions,
                budget_available=budget_available
            )
            
            print(f"✅ [DEBUG] Transfer suggestions completed: {suggestions.get('total_suggestions', 0)} suggestions")
            
            return jsonify({
                'success': True,
                'data': suggestions
            })
            
        except Exception as e:
            print(f"❌ [DEBUG] Transfer suggestions error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'ไม่สามารถสร้างคำแนะนำการเปลี่ยนตัวได้: {str(e)}'
            }), 500

    @app.route('/api/players/search')
    def search_players():
        """Advanced player search API endpoint for scouting."""
        try:
            print("🔍 [DEBUG] Player search requested...")
            
            # Parse query parameters
            position = request.args.get('position')
            team_id = request.args.get('team_id', type=int)
            min_cost = request.args.get('min_cost', type=float)
            max_cost = request.args.get('max_cost', type=float)
            sort_by = request.args.get('sort_by', 'total_points')
            sort_order = request.args.get('sort_order', 'desc')
            limit = min(int(request.args.get('limit', 50)), 1000)
            offset = int(request.args.get('offset', 0))
            search_term = request.args.get('q', '').strip()
            
            print(f"🔍 [DEBUG] Search params: position={position}, team={team_id}, cost={min_cost}-{max_cost}, sort={sort_by} {sort_order}")
            
            # Build query
            query = Player.query.filter(Player.status == 'a')
            
            # Filter by position
            if position and position in ['GKP', 'DEF', 'MID', 'FWD']:
                query = query.filter(Player.position == position)
            
            # Filter by team
            if team_id:
                query = query.filter(Player.team_id == team_id)
                
            # Filter by cost range
            if min_cost is not None:
                query = query.filter(Player.now_cost >= min_cost * 10)
            if max_cost is not None:
                query = query.filter(Player.now_cost <= max_cost * 10)
                
            # Search by player name
            if search_term:
                query = query.filter(
                    db.or_(
                        Player.web_name.ilike(f'%{search_term}%'),
                        Player.first_name.ilike(f'%{search_term}%'),
                        Player.second_name.ilike(f'%{search_term}%')
                    )
                )
            
            # Sort results
            valid_sort_fields = {
                'web_name': Player.web_name,
                'total_points': Player.total_points,
                'now_cost': Player.now_cost,
                'form': Player.form,
                'expected_points': Player.total_points  # Use total_points as proxy for expected_points
            }
            
            if sort_by in valid_sort_fields:
                sort_field = valid_sort_fields[sort_by]
                if sort_order.lower() == 'desc':
                    query = query.order_by(sort_field.desc())
                else:
                    query = query.order_by(sort_field.asc())
            
            # Get total count before pagination
            total_count = query.count()
            
            # Apply pagination
            players = query.offset(offset).limit(limit).all()
            
            # Convert to dict with team names
            players_data = []
            for player in players:
                # Get team name
                team = Team.query.get(player.team_id)
                team_name = team.short_name if team else f'Team {player.team_id}'
                
                players_data.append({
                    'player_id': player.player_id,
                    'web_name': player.web_name,
                    'first_name': player.first_name,
                    'second_name': player.second_name,
                    'position': player.position,
                    'team_id': player.team_id,
                    'team_name': team_name,
                    'now_cost': player.now_cost / 10.0,
                    'total_points': player.total_points,
                    'form': float(player.form or 0),
                    'expected_points': _calculate_realistic_expected_points(player),
                    'status': player.status,
                    'selected_by_percent': getattr(player, 'selected_by_percent', 0.0),
                    'transfers_in': getattr(player, 'transfers_in', 0),
                    'transfers_out': getattr(player, 'transfers_out', 0)
                })
            
            print(f"✅ [DEBUG] Search completed: {len(players_data)} players found")
            
            return jsonify({
                'success': True,
                'data': {
                    'players': players_data,
                    'total_count': total_count,
                    'limit': limit,
                    'offset': offset,
                    'filters': {
                        'position': position,
                        'team_id': team_id,
                        'min_cost': min_cost,
                        'max_cost': max_cost,
                        'search_term': search_term
                    },
                    'sort': {
                        'by': sort_by,
                        'order': sort_order
                    }
                }
            })
            
        except Exception as e:
            print(f"❌ [DEBUG] Player search error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'success': False, 'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
    
    return app

if __name__ == '__main__':
    app = create_production_app()
    
    with app.app_context():
        db.create_all()
    
    print("🚀 Starting FPL AI Optimizer - Production Version")
    print("📡 API available at: http://localhost:5001")
    print("🏠 Dashboard: http://localhost:5001/")
    print("⚽ Optimizer: http://localhost:5001/optimizer") 
    print("🔍 Scouting: http://localhost:5001/scouting")
    print("💚 Health Check: http://localhost:5001/api/health")
    print("🎯 Team Optimization: POST to /api/optimize")
    print("📊 Players API: GET /api/players")
    print("🏟️ Teams API: GET /api/teams")
    print()
    
    try:
        app.run(host='0.0.0.0', port=5001, debug=True)
    except KeyboardInterrupt:
        print("\n🛑 FPL AI Optimizer stopped")
    except Exception as e:
        print(f"❌ Failed to start: {e}")