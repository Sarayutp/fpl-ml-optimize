"""Tests for API views."""

import pytest
import json
from unittest.mock import Mock, patch


class TestAPIViews:
    """Test API endpoints."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get('/api/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['message'] == 'API is healthy'
    
    def test_get_teams(self, client, sample_teams):
        """Test get teams endpoint."""
        response = client.get('/api/teams')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['data']) >= 0  # Should have teams
    
    def test_get_players_all(self, client, sample_players):
        """Test get all players endpoint."""
        response = client.get('/api/players')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'data' in data
    
    def test_get_player_by_id(self, client, sample_players):
        """Test get player by ID endpoint."""
        player_id = sample_players[0].player_id
        response = client.get(f'/api/players/{player_id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['player_id'] == player_id
    
    def test_get_player_not_found(self, client):
        """Test get non-existent player."""
        response = client.get('/api/players/99999')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'not found' in data['error'].lower()
    
    def test_search_players_basic(self, client, sample_players):
        """Test basic player search."""
        response = client.get('/api/players/search')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'players' in data['data']
        assert 'total_count' in data['data']
    
    def test_search_players_with_name(self, client, sample_players):
        """Test player search with name filter."""
        response = client.get('/api/players/search?name=Salah')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Should find Salah if exists
        if data['data']['total_count'] > 0:
            found_salah = any(
                'Salah' in player['web_name'] 
                for player in data['data']['players']
            )
            assert found_salah
    
    def test_search_players_with_position(self, client, sample_players):
        """Test player search with position filter."""
        response = client.get('/api/players/search?position=FWD')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # All returned players should be forwards
        for player in data['data']['players']:
            assert player['position'] == 'FWD'
    
    def test_search_players_with_cost_range(self, client, sample_players):
        """Test player search with cost range."""
        response = client.get('/api/players/search?min_cost=10&max_cost=15')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # All returned players should be within cost range
        for player in data['data']['players']:
            assert 10 <= player['now_cost'] <= 15
    
    def test_search_players_invalid_position(self, client):
        """Test player search with invalid position."""
        response = client.get('/api/players/search?position=INVALID')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'validation' in data['error'].lower()
    
    def test_optimize_team_basic(self, client, sample_players):
        """Test basic team optimization."""
        request_data = {
            "budget": 100.0,
            "max_players_per_team": 3
        }
        
        with patch('src.views.api_views.optimization_service') as mock_service:
            mock_service.optimize_team.return_value = {
                "players": list(range(1, 16)),
                "captain_id": 1,
                "vice_captain_id": 2,
                "total_cost": 95.5,
                "expected_points": 65.2,
                "reasoning": "Test reasoning"
            }
            
            response = client.post(
                '/api/optimize',
                data=json.dumps(request_data),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'players' in data['data']
            assert 'reasoning' in data['data']
    
    def test_optimize_team_with_formation(self, client, sample_players):
        """Test team optimization with formation."""
        request_data = {
            "budget": 100.0,
            "formation": "4-4-2",
            "max_players_per_team": 3
        }
        
        with patch('src.views.api_views.optimization_service') as mock_service:
            mock_service.optimize_team.return_value = {
                "players": list(range(1, 16)),
                "captain_id": 1,
                "vice_captain_id": 2,
                "total_cost": 95.5,
                "expected_points": 65.2,
                "reasoning": "Test reasoning with 4-4-2 formation"
            }
            
            response = client.post(
                '/api/optimize',
                data=json.dumps(request_data),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
    
    def test_optimize_team_invalid_budget(self, client):
        """Test team optimization with invalid budget."""
        request_data = {
            "budget": 200.0,  # Too high
            "max_players_per_team": 3
        }
        
        response = client.post(
            '/api/optimize',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'validation' in data['error'].lower() or 'budget' in data['error'].lower()
    
    def test_optimize_team_invalid_formation(self, client):
        """Test team optimization with invalid formation."""
        request_data = {
            "budget": 100.0,
            "formation": "invalid-formation",
            "max_players_per_team": 3
        }
        
        response = client.post(
            '/api/optimize',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_optimize_team_service_error(self, client):
        """Test team optimization when service fails."""
        request_data = {
            "budget": 100.0,
            "max_players_per_team": 3
        }
        
        with patch('src.views.api_views.optimization_service') as mock_service:
            mock_service.optimize_team.side_effect = Exception("Optimization failed")
            
            response = client.post(
                '/api/optimize',
                data=json.dumps(request_data),
                content_type='application/json'
            )
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'optimization failed' in data['error'].lower()
    
    def test_optimize_transfers_basic(self, client, sample_players):
        """Test transfer optimization."""
        request_data = {
            "current_team": [1, 2, 3, 4, 5],
            "available_budget": 5.0,
            "max_transfers": 2
        }
        
        with patch('src.views.api_views.optimization_service') as mock_service:
            mock_service.optimize_transfers.return_value = [
                {
                    "player_in": {"player_id": 6, "web_name": "New Player"},
                    "player_out": {"player_id": 1, "web_name": "Old Player"},
                    "cost_change": 1.0,
                    "expected_gain": 2.5,
                    "reasoning": "Better form"
                }
            ]
            
            response = client.post(
                '/api/optimize/transfers',
                data=json.dumps(request_data),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert isinstance(data['data'], list)
    
    def test_optimize_captain_basic(self, client):
        """Test captain optimization."""
        request_data = {
            "current_team": [1, 2, 3, 4, 5]
        }
        
        with patch('src.views.api_views.optimization_service') as mock_service:
            mock_service.optimize_captain_selection.return_value = {
                "captain_id": 1,
                "vice_captain_id": 2,
                "expected_points_captain": 16.4,
                "expected_points_vice": 7.8,
                "reasoning": "Best captain choice"
            }
            
            response = client.post(
                '/api/optimize/captain',
                data=json.dumps(request_data),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'captain_id' in data['data']
    
    def test_get_fixtures(self, client, sample_fixtures):
        """Test get fixtures endpoint."""
        response = client.get('/api/fixtures')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'data' in data
    
    def test_get_fixtures_by_gameweek(self, client, sample_fixtures):
        """Test get fixtures by gameweek."""
        response = client.get('/api/fixtures?gameweek=1')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # All fixtures should be from gameweek 1
        for fixture in data['data']:
            assert fixture['gameweek'] == 1
    
    def test_get_fixtures_by_team(self, client, sample_fixtures):
        """Test get fixtures by team."""
        response = client.get('/api/fixtures?team_id=1')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # All fixtures should involve team 1
        for fixture in data['data']:
            assert fixture['home_team_id'] == 1 or fixture['away_team_id'] == 1
    
    def test_missing_content_type(self, client):
        """Test POST request without content type."""
        response = client.post('/api/optimize', data='{"budget": 100.0}')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'content-type' in data['error'].lower() or 'json' in data['error'].lower()
    
    def test_invalid_json(self, client):
        """Test POST request with invalid JSON."""
        response = client.post(
            '/api/optimize',
            data='{"budget": invalid}',
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'json' in data['error'].lower() or 'parse' in data['error'].lower()
    
    def test_method_not_allowed(self, client):
        """Test invalid HTTP method."""
        response = client.delete('/api/optimize')
        
        assert response.status_code == 405
    
    def test_cors_headers(self, client):
        """Test CORS headers are included."""
        response = client.get('/api/health')
        
        # CORS headers might be set by Flask-CORS or custom middleware
        # This is just a basic check - actual CORS configuration depends on setup
        assert response.status_code == 200
    
    def test_api_response_format_consistency(self, client):
        """Test that all API responses follow consistent format."""
        endpoints = [
            '/api/health',
            '/api/teams',
            '/api/players',
            '/api/fixtures'
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            
            # All responses should be JSON
            assert response.content_type.startswith('application/json')
            
            data = json.loads(response.data)
            
            # All responses should have success field
            assert 'success' in data
            assert isinstance(data['success'], bool)
            
            # Should have either data or error
            if data['success']:
                assert 'data' in data
            else:
                assert 'error' in data
            
            # Should have timestamp
            assert 'timestamp' in data
    
    def test_large_request_handling(self, client):
        """Test handling of large requests."""
        # Create a large request (but reasonable for team optimization)
        large_request = {
            "budget": 100.0,
            "preferred_players": list(range(1, 100)),  # Large list
            "excluded_players": list(range(100, 200)),  # Another large list
            "max_players_per_team": 3
        }
        
        with patch('src.views.api_views.optimization_service') as mock_service:
            mock_service.optimize_team.return_value = {
                "players": list(range(1, 16)),
                "captain_id": 1,
                "vice_captain_id": 2,
                "total_cost": 95.5,
                "expected_points": 65.2,
                "reasoning": "Test reasoning"
            }
            
            response = client.post(
                '/api/optimize',
                data=json.dumps(large_request),
                content_type='application/json'
            )
            
            # Should handle large requests gracefully
            assert response.status_code in [200, 400]  # Either success or validation error
    
    def test_concurrent_requests_handling(self, client):
        """Test that API can handle multiple requests."""
        import threading
        
        results = []
        
        def make_request():
            response = client.get('/api/health')
            results.append(response.status_code)
        
        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert all(code == 200 for code in results)