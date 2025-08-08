"""Data service for FPL API integration and data management."""

import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from flask import current_app

from ..models.db_models import db, Team, Player, Fixture, PlayerPastStats


logger = logging.getLogger(__name__)


class FPLAPIError(Exception):
    """Custom exception for FPL API errors."""
    pass


class DataService:
    """Service for fetching and managing FPL data."""
    
    def __init__(self, app=None, cache=None):
        """Initialize data service."""
        self.app = app
        self.cache = cache
        self.session = None
        
        if app is not None:
            self.init_app(app, cache)
    
    def init_app(self, app, cache=None):
        """Initialize the data service with Flask app."""
        self.app = app
        self.cache = cache  # Use passed cache directly
        
        # Configure requests session with retry logic
        self.session = requests.Session()
        # Configure retry strategy with compatibility check
        try:
            # Try new parameter name first (urllib3 >= 1.26.0)
            retry_strategy = Retry(
                total=3,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "OPTIONS"],
                backoff_factor=1
            )
        except TypeError:
            # Fallback to old parameter name (urllib3 < 1.26.0)
            retry_strategy = Retry(
                total=3,
                status_forcelist=[429, 500, 502, 503, 504],
                method_whitelist=["HEAD", "GET", "OPTIONS"],
                backoff_factor=1
            )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default timeout
        self.session.timeout = app.config.get('API_TIMEOUT', 30)
    
    def _get_from_cache_or_api(self, cache_key: str, api_endpoint: str, timeout: int = 3600) -> Dict:
        """Get data from cache or API with fallback."""
        if self.cache:
            # Try to get from cache first
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                logger.info(f"Retrieved {cache_key} from cache")
                return cached_data
        
        # Fetch from API
        logger.info(f"Fetching {cache_key} from API: {api_endpoint}")
        data = self._fetch_from_api(api_endpoint)
        
        # Cache the result
        if self.cache and data:
            self.cache.set(cache_key, data, timeout=timeout)
            logger.info(f"Cached {cache_key} for {timeout} seconds")
        
        return data
    
    def _fetch_from_api(self, endpoint: str) -> Dict:
        """Fetch data from FPL API with error handling."""
        try:
            base_url = current_app.config.get('FPL_API_BASE_URL', 'https://fantasy.premierleague.com/api/')
            url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            
            logger.debug(f"Fetching data from: {url}")
            
            # Add delay to respect rate limits
            time.sleep(0.1)  # 100ms delay between requests
            
            response = self.session.get(url, timeout=current_app.config.get('API_TIMEOUT', 30))
            
            # Check for rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                
                # Retry once after waiting
                response = self.session.get(url, timeout=current_app.config.get('API_TIMEOUT', 30))
            
            if response.status_code != 200:
                raise FPLAPIError(f"FPL API returned {response.status_code}: {response.text}")
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching from {endpoint}: {e}")
            raise FPLAPIError(f"Failed to fetch data from FPL API: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching from {endpoint}: {e}")
            raise FPLAPIError(f"Unexpected error: {e}")
    
    def get_bootstrap_static(self) -> Dict:
        """Get FPL bootstrap-static data (players, teams, fixtures)."""
        cache_timeout = current_app.config.get('FPL_CACHE_TIMEOUT', 3600)
        return self._get_from_cache_or_api(
            cache_key='fpl_bootstrap_static',
            api_endpoint='bootstrap-static/',
            timeout=cache_timeout
        )
    
    def get_player_data(self) -> List[Dict]:
        """Fetch and transform player data from FPL API."""
        bootstrap_data = self.get_bootstrap_static()
        raw_players = bootstrap_data.get('elements', [])
        
        return self._transform_player_data(raw_players)
    
    def get_team_data(self) -> List[Dict]:
        """Fetch and transform team data from FPL API."""
        bootstrap_data = self.get_bootstrap_static()
        raw_teams = bootstrap_data.get('teams', [])
        
        return self._transform_team_data(raw_teams)
    
    def get_fixture_data(self) -> List[Dict]:
        """Fetch and transform fixture data from FPL API."""
        cache_timeout = current_app.config.get('FPL_CACHE_TIMEOUT', 900)  # 15 minutes
        fixture_data = self._get_from_cache_or_api(
            cache_key='fpl_fixtures',
            api_endpoint='fixtures/',
            timeout=cache_timeout
        )
        
        return self._transform_fixture_data(fixture_data)
    
    def get_player_detailed_stats(self, player_id: int) -> Dict:
        """Get detailed stats for a specific player."""
        cache_key = f'player_stats_{player_id}'
        cache_timeout = current_app.config.get('FPL_CACHE_TIMEOUT', 1800)  # 30 minutes
        
        return self._get_from_cache_or_api(
            cache_key=cache_key,
            api_endpoint=f'element-summary/{player_id}/',
            timeout=cache_timeout
        )
    
    def _transform_player_data(self, raw_players: List[Dict]) -> List[Dict]:
        """Transform FPL API player format to internal format."""
        transformed_players = []
        
        for player in raw_players:
            try:
                transformed = {
                    'player_id': player['id'],
                    'web_name': player['web_name'],
                    'first_name': player.get('first_name', ''),
                    'second_name': player.get('second_name', ''),
                    'team_id': player['team'],
                    'position': self._get_position_name(player['element_type']),
                    'now_cost': player['now_cost'],
                    
                    # Performance metrics
                    'expected_goals': float(player.get('expected_goals', '0') or 0),
                    'expected_assists': float(player.get('expected_assists', '0') or 0),
                    'expected_goal_involvements': float(player.get('expected_goal_involvements', '0') or 0),
                    'form': float(player.get('form', '0') or 0),
                    'points_per_game': float(player.get('points_per_game', '0') or 0),
                    'total_points': int(player.get('total_points', 0)),
                    
                    # Playing time
                    'minutes': int(player.get('minutes', 0)),
                    'starts': int(player.get('starts', 0)),
                    
                    # Status
                    'status': player.get('status', 'a'),
                    'chance_of_playing_this_round': player.get('chance_of_playing_this_round'),
                    'chance_of_playing_next_round': player.get('chance_of_playing_next_round'),
                }
                
                transformed_players.append(transformed)
                
            except (ValueError, KeyError, TypeError) as e:
                logger.warning(f"Error transforming player {player.get('id', 'unknown')}: {e}")
                continue
        
        logger.info(f"Transformed {len(transformed_players)} players")
        return transformed_players
    
    def _transform_team_data(self, raw_teams: List[Dict]) -> List[Dict]:
        """Transform FPL API team format to internal format."""
        transformed_teams = []
        
        for team in raw_teams:
            try:
                transformed = {
                    'team_id': team['id'],
                    'name': team['name'],
                    'short_name': team['short_name'],
                    'strength_overall_home': team.get('strength_overall_home'),
                    'strength_overall_away': team.get('strength_overall_away'),
                }
                
                transformed_teams.append(transformed)
                
            except (KeyError, TypeError) as e:
                logger.warning(f"Error transforming team {team.get('id', 'unknown')}: {e}")
                continue
        
        logger.info(f"Transformed {len(transformed_teams)} teams")
        return transformed_teams
    
    def _transform_fixture_data(self, raw_fixtures: List[Dict]) -> List[Dict]:
        """Transform FPL API fixture format to internal format."""
        transformed_fixtures = []
        
        for fixture in raw_fixtures:
            try:
                # Parse kickoff time
                kickoff_time = None
                if fixture.get('kickoff_time'):
                    try:
                        kickoff_time = datetime.fromisoformat(
                            fixture['kickoff_time'].replace('Z', '+00:00')
                        )
                    except ValueError:
                        pass
                
                transformed = {
                    'fixture_id': fixture['id'],
                    'gameweek': fixture.get('event'),
                    'home_team_id': fixture['team_h'],
                    'away_team_id': fixture['team_a'],
                    'home_difficulty': fixture.get('team_h_difficulty'),
                    'away_difficulty': fixture.get('team_a_difficulty'),
                    'kickoff_time': kickoff_time,
                    'finished': fixture.get('finished', False),
                    'started': fixture.get('started', False),
                }
                
                transformed_fixtures.append(transformed)
                
            except (KeyError, TypeError) as e:
                logger.warning(f"Error transforming fixture {fixture.get('id', 'unknown')}: {e}")
                continue
        
        logger.info(f"Transformed {len(transformed_fixtures)} fixtures")
        return transformed_fixtures
    
    def _get_position_name(self, element_type: int) -> str:
        """Convert FPL element_type to position name."""
        position_map = {
            1: 'GKP',  # Goalkeeper
            2: 'DEF',  # Defender
            3: 'MID',  # Midfielder
            4: 'FWD'   # Forward
        }
        return position_map.get(element_type, 'UNK')
    
    def update_database_from_api(self) -> Dict[str, int]:
        """Update database with latest data from FPL API."""
        logger.info("Starting database update from FPL API...")
        
        stats = {
            'teams_updated': 0,
            'players_updated': 0,
            'fixtures_updated': 0,
            'errors': 0
        }
        
        try:
            # Update teams
            team_data = self.get_team_data()
            stats['teams_updated'] = self._update_teams(team_data)
            
            # Update players
            player_data = self.get_player_data()
            stats['players_updated'] = self._update_players(player_data)
            
            # Update fixtures
            fixture_data = self.get_fixture_data()
            stats['fixtures_updated'] = self._update_fixtures(fixture_data)
            
            db.session.commit()
            logger.info(f"Database update completed: {stats}")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Database update failed: {e}")
            stats['errors'] = 1
            raise
        
        return stats
    
    def _update_teams(self, team_data: List[Dict]) -> int:
        """Update teams in database."""
        updated_count = 0
        
        for team_info in team_data:
            team = Team.query.filter_by(team_id=team_info['team_id']).first()
            
            if team:
                # Update existing team
                for key, value in team_info.items():
                    if hasattr(team, key):
                        setattr(team, key, value)
                team.updated_at = datetime.utcnow()
            else:
                # Create new team
                team = Team(**team_info)
                db.session.add(team)
            
            updated_count += 1
        
        return updated_count
    
    def _update_players(self, player_data: List[Dict]) -> int:
        """Update players in database."""
        updated_count = 0
        
        for player_info in player_data:
            player = Player.query.filter_by(player_id=player_info['player_id']).first()
            
            if player:
                # Update existing player
                for key, value in player_info.items():
                    if hasattr(player, key):
                        setattr(player, key, value)
                player.updated_at = datetime.utcnow()
            else:
                # Create new player
                player = Player(**player_info)
                db.session.add(player)
            
            updated_count += 1
        
        return updated_count
    
    def _update_fixtures(self, fixture_data: List[Dict]) -> int:
        """Update fixtures in database."""
        updated_count = 0
        
        for fixture_info in fixture_data:
            fixture = Fixture.query.filter_by(fixture_id=fixture_info['fixture_id']).first()
            
            if fixture:
                # Update existing fixture
                for key, value in fixture_info.items():
                    if hasattr(fixture, key):
                        setattr(fixture, key, value)
                fixture.updated_at = datetime.utcnow()
            else:
                # Create new fixture
                fixture = Fixture(**fixture_info)
                db.session.add(fixture)
            
            updated_count += 1
        
        return updated_count
    
    def search_players(self, name: Optional[str] = None, position: Optional[str] = None,
                      team_id: Optional[int] = None, limit: int = 20) -> List[Player]:
        """Search players with filters."""
        query = Player.query
        
        if name:
            # Use index on web_name for efficient search
            query = query.filter(Player.web_name.ilike(f'%{name}%'))
        
        if position:
            query = query.filter(Player.position == position)
        
        if team_id:
            query = query.filter(Player.team_id == team_id)
        
        # Order by expected points (assuming we have this field)
        query = query.order_by(Player.total_points.desc())
        
        return query.limit(limit).all()
    
    def get_player_by_id(self, player_id: int) -> Optional[Player]:
        """Get player by ID."""
        return Player.query.filter_by(player_id=player_id).first()
    
    def get_team_by_id(self, team_id: int) -> Optional[Team]:
        """Get team by ID."""
        return Team.query.filter_by(team_id=team_id).first()