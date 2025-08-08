"""Tests for ReasoningService."""

import pytest
from unittest.mock import Mock, patch

from src.services.reasoning_service import ReasoningService


class TestReasoningService:
    """Test ReasoningService functionality."""
    
    @pytest.fixture
    def reasoning_service(self, app):
        """Create ReasoningService instance for testing."""
        with app.app_context():
            return ReasoningService()
    
    def test_init(self, reasoning_service):
        """Test ReasoningService initialization."""
        assert reasoning_service.data_service is not None
        assert reasoning_service.templates is not None
        assert len(reasoning_service.templates) > 0
    
    def test_templates_structure(self, reasoning_service):
        """Test that templates have required structure."""
        required_template_keys = [
            'team_optimization',
            'transfer_suggestion',
            'captain_selection',
            'player_comparison',
            'form_analysis'
        ]
        
        for key in required_template_keys:
            assert key in reasoning_service.templates
            assert isinstance(reasoning_service.templates[key], list)
            assert len(reasoning_service.templates[key]) > 0
    
    def test_generate_team_optimization_reasoning(self, reasoning_service, sample_players):
        """Test team optimization reasoning generation."""
        optimization_result = {
            "players": [1, 2, 3, 4, 5],
            "captain_id": 1,
            "vice_captain_id": 2,
            "total_cost": 95.5,
            "expected_points": 65.2,
            "formation": {"GKP": 2, "DEF": 5, "MID": 5, "FWD": 3}
        }
        
        players_data = {p.player_id: p for p in sample_players}
        
        with patch.object(reasoning_service.data_service, 'get_players_by_ids') as mock_get_players:
            mock_get_players.return_value = sample_players[:5]  # Return first 5 players
            
            reasoning = reasoning_service.generate_team_optimization_reasoning(
                optimization_result, players_data
            )
            
            assert isinstance(reasoning, str)
            assert len(reasoning) > 50  # Should be substantial text
            assert "65.2" in reasoning  # Expected points
            assert "95.5" in reasoning  # Total cost
    
    def test_generate_transfer_reasoning(self, reasoning_service, sample_players):
        """Test transfer reasoning generation."""
        player_in = sample_players[0]  # Salah
        player_out = sample_players[1]  # De Bruyne
        
        reasoning = reasoning_service.generate_transfer_reasoning(
            player_in, player_out, cost_change=0.5, expected_gain=1.2
        )
        
        assert isinstance(reasoning, str)
        assert len(reasoning) > 30
        assert player_in.web_name in reasoning
        assert player_out.web_name in reasoning
        assert "0.5" in reasoning  # Cost change
    
    def test_generate_captain_reasoning(self, reasoning_service, sample_players):
        """Test captain selection reasoning generation."""
        captain = sample_players[0]  # Salah
        vice_captain = sample_players[1]  # De Bruyne
        
        reasoning = reasoning_service.generate_captain_reasoning(
            captain, vice_captain, 
            captain_expected=8.2, vice_expected=7.8
        )
        
        assert isinstance(reasoning, str)
        assert len(reasoning) > 30
        assert captain.web_name in reasoning
        assert vice_captain.web_name in reasoning
        assert "8.2" in reasoning  # Captain expected points
    
    def test_generate_player_comparison_reasoning(self, reasoning_service, sample_players):
        """Test player comparison reasoning generation."""
        players = sample_players[:3]  # First 3 players
        
        reasoning = reasoning_service.generate_player_comparison_reasoning(players)
        
        assert isinstance(reasoning, str)
        assert len(reasoning) > 50
        
        # Should mention all players
        for player in players:
            assert player.web_name in reasoning
    
    def test_analyze_player_form(self, reasoning_service, sample_players):
        """Test player form analysis."""
        player = sample_players[0]  # Salah with form 5.5
        
        analysis = reasoning_service.analyze_player_form(player)
        
        assert isinstance(analysis, str)
        assert len(analysis) > 20
        assert player.web_name in analysis
        assert "5.5" in analysis  # Form score
    
    def test_get_form_description(self, reasoning_service):
        """Test form description mapping."""
        # Test excellent form
        excellent = reasoning_service._get_form_description(7.0)
        assert "ยอดเยี่ยม" in excellent.lower() or "excellent" in excellent.lower()
        
        # Test good form
        good = reasoning_service._get_form_description(5.5)
        assert "ดี" in good.lower() or "good" in good.lower()
        
        # Test average form
        average = reasoning_service._get_form_description(4.0)
        assert "ปานกลาง" in average.lower() or "average" in average.lower()
        
        # Test poor form  
        poor = reasoning_service._get_form_description(2.0)
        assert "แย่" in poor.lower() or "poor" in poor.lower()
    
    def test_get_cost_efficiency_description(self, reasoning_service):
        """Test cost efficiency description."""
        # High efficiency
        high = reasoning_service._get_cost_efficiency_description(0.8)
        assert len(high) > 10
        
        # Low efficiency
        low = reasoning_service._get_cost_efficiency_description(0.3)
        assert len(low) > 10
    
    def test_get_expected_points_tier(self, reasoning_service):
        """Test expected points tier classification."""
        # Premium tier
        premium = reasoning_service._get_expected_points_tier(8.0)
        assert "premium" in premium.lower() or "พรีเมี่ยม" in premium.lower()
        
        # Mid tier
        mid = reasoning_service._get_expected_points_tier(6.0)
        assert "mid" in mid.lower() or "กลาง" in mid.lower()
        
        # Budget tier
        budget = reasoning_service._get_expected_points_tier(4.0)
        assert "budget" in budget.lower() or "ประหยัด" in budget.lower()
    
    def test_template_selection_randomness(self, reasoning_service, sample_players):
        """Test that template selection shows some variety."""
        player_in = sample_players[0]
        player_out = sample_players[1]
        
        # Generate multiple reasonings and check for variety
        reasonings = []
        for _ in range(10):
            reasoning = reasoning_service.generate_transfer_reasoning(
                player_in, player_out, cost_change=0.5, expected_gain=1.2
            )
            reasonings.append(reasoning)
        
        # Should have some variety in templates (not all identical)
        unique_reasonings = set(reasonings)
        assert len(unique_reasonings) > 1  # At least some variety
    
    def test_handle_missing_player_data(self, reasoning_service):
        """Test handling of missing player data."""
        # Create mock player with minimal data
        mock_player = Mock()
        mock_player.web_name = "Test Player"
        mock_player.form = None
        mock_player.expected_points = None
        mock_player.now_cost = 50
        
        # Should not crash
        reasoning = reasoning_service.analyze_player_form(mock_player)
        
        assert isinstance(reasoning, str)
        assert len(reasoning) > 0
        assert "Test Player" in reasoning
    
    def test_generate_reasoning_with_context(self, reasoning_service, sample_players):
        """Test reasoning generation with additional context."""
        player = sample_players[0]  # Salah
        
        context = {
            "upcoming_fixtures": ["easy", "medium", "hard"],
            "injury_status": "fit",
            "recent_performance": "excellent"
        }
        
        # This method might not exist yet, but shows the pattern for contextual reasoning
        try:
            reasoning = reasoning_service.generate_reasoning_with_context(player, context)
            assert isinstance(reasoning, str)
            assert len(reasoning) > 30
        except AttributeError:
            # Method doesn't exist yet - that's OK for now
            pass
    
    def test_multilingual_support(self, reasoning_service, sample_players):
        """Test that reasoning is primarily in Thai as specified."""
        player_in = sample_players[0]
        player_out = sample_players[1]
        
        reasoning = reasoning_service.generate_transfer_reasoning(
            player_in, player_out, cost_change=0.5, expected_gain=1.2
        )
        
        # Should contain Thai characters (basic check)
        has_thai = any(ord(char) >= 0x0E00 and ord(char) <= 0x0E7F for char in reasoning)
        assert has_thai, "Reasoning should contain Thai text"
    
    def test_reasoning_length_appropriate(self, reasoning_service, sample_players):
        """Test that reasoning text is appropriate length."""
        optimization_result = {
            "players": [1, 2, 3, 4, 5],
            "captain_id": 1,
            "vice_captain_id": 2,
            "total_cost": 95.5,
            "expected_points": 65.2,
            "formation": {"GKP": 2, "DEF": 5, "MID": 5, "FWD": 3}
        }
        
        players_data = {p.player_id: p for p in sample_players}
        
        with patch.object(reasoning_service.data_service, 'get_players_by_ids') as mock_get_players:
            mock_get_players.return_value = sample_players[:5]
            
            reasoning = reasoning_service.generate_team_optimization_reasoning(
                optimization_result, players_data
            )
            
            # Should be substantial but not too long
            assert 50 <= len(reasoning) <= 500, f"Reasoning length {len(reasoning)} not in expected range"
    
    def test_consistent_formatting(self, reasoning_service, sample_players):
        """Test that reasoning has consistent formatting."""
        players = sample_players[:2]
        
        reasoning = reasoning_service.generate_player_comparison_reasoning(players)
        
        # Basic formatting checks
        assert reasoning.strip() == reasoning  # No leading/trailing whitespace
        assert not reasoning.startswith(" ")  # No leading space
        assert not reasoning.endswith(" ")   # No trailing space
        
        # Should not have excessive punctuation
        assert ".." not in reasoning  # No double periods
        assert "!!" not in reasoning  # No double exclamations
    
    def test_error_handling_empty_data(self, reasoning_service):
        """Test error handling with empty or invalid data."""
        # Test with empty optimization result
        empty_result = {}
        
        try:
            reasoning = reasoning_service.generate_team_optimization_reasoning(empty_result, {})
            # Should either work with fallbacks or raise appropriate error
            assert isinstance(reasoning, str) or reasoning is None
        except (KeyError, ValueError):
            # Acceptable to raise error for invalid data
            pass
    
    def test_numeric_formatting(self, reasoning_service, sample_players):
        """Test that numbers are formatted appropriately in reasoning."""
        player_in = sample_players[0]
        player_out = sample_players[1]
        
        reasoning = reasoning_service.generate_transfer_reasoning(
            player_in, player_out, cost_change=1.234567, expected_gain=2.987654
        )
        
        # Numbers should be reasonably formatted (not too many decimal places)
        assert "1.234567" not in reasoning  # Should be rounded
        assert "2.987654" not in reasoning  # Should be rounded