"""Pydantic data models for FPL AI Optimizer validation and serialization."""

from datetime import datetime
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator


class PlayerStats(BaseModel):
    """Player statistics data model."""
    
    player_id: int
    web_name: str
    position: str = Field(..., pattern=r'^(GKP|DEF|MID|FWD)$')
    team_id: int
    now_cost: float = Field(..., gt=0, description="Player cost in millions")
    expected_points: float = Field(..., ge=0)
    form: float = Field(..., ge=0)
    total_points: int = Field(..., ge=0)
    points_per_game: float = Field(..., ge=0)
    
    # Optional performance metrics
    expected_goals: Optional[float] = Field(None, ge=0)
    expected_assists: Optional[float] = Field(None, ge=0)
    minutes: Optional[int] = Field(None, ge=0)
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class TeamData(BaseModel):
    """Team information data model."""
    
    team_id: int
    name: str
    short_name: str = Field(..., max_length=3)
    strength_overall_home: Optional[int] = Field(None, ge=1, le=5)
    strength_overall_away: Optional[int] = Field(None, ge=1, le=5)
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class OptimizedTeam(BaseModel):
    """Optimized team selection result."""
    
    players: List[int] = Field(..., min_items=15, max_items=15)
    captain_id: int
    vice_captain_id: int
    total_cost: float = Field(..., le=100.0)
    expected_points: float = Field(..., gt=0)
    reasoning: str = Field(..., min_length=10)
    
    # Formation breakdown
    formation: Dict[str, int] = Field(
        default={'GKP': 2, 'DEF': 5, 'MID': 5, 'FWD': 3}
    )
    
    @validator('captain_id')
    def captain_must_be_in_players(cls, v, values):
        """Validate captain is in the selected players."""
        if 'players' in values and v not in values['players']:
            raise ValueError('Captain must be one of the selected players')
        return v
    
    @validator('vice_captain_id')
    def vice_captain_must_be_in_players(cls, v, values):
        """Validate vice captain is in the selected players."""
        if 'players' in values and v not in values['players']:
            raise ValueError('Vice captain must be one of the selected players')
        return v
    
    @validator('vice_captain_id')
    def vice_captain_different_from_captain(cls, v, values):
        """Validate vice captain is different from captain."""
        if 'captain_id' in values and v == values['captain_id']:
            raise ValueError('Vice captain must be different from captain')
        return v


class TransferSuggestion(BaseModel):
    """Transfer recommendation data model."""
    
    player_out: PlayerStats
    player_in: PlayerStats
    cost_change: float  # Positive means more expensive
    expected_points_gain: float
    reasoning: str = Field(..., min_length=10)
    confidence_score: float = Field(..., ge=0, le=1)
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class CaptainSuggestion(BaseModel):
    """Captain recommendation data model."""
    
    captain: PlayerStats
    vice_captain: PlayerStats
    expected_points_captain: float = Field(..., gt=0)
    expected_points_vice: float = Field(..., gt=0)
    reasoning: str = Field(..., min_length=10)
    confidence_score: float = Field(..., ge=0, le=1)
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class OptimizationRequest(BaseModel):
    """Request parameters for team optimization."""
    
    budget: float = Field(default=100.0, ge=50.0, le=100.0)
    formation: Optional[str] = Field(None, pattern=r'^\d-\d-\d$')  # e.g., "3-5-2"
    preferred_players: Optional[List[int]] = Field(None, max_items=15)
    excluded_players: Optional[List[int]] = Field(None, max_items=100)
    max_players_per_team: int = Field(default=3, ge=1, le=5)
    include_reasoning: bool = Field(default=True)
    
    @validator('formation')
    def validate_formation(cls, v):
        """Validate formation adds up to 10 outfield players."""
        if v is not None:
            parts = v.split('-')
            if len(parts) != 3:
                raise ValueError('Formation must be in format "DEF-MID-FWD"')
            total = sum(int(x) for x in parts)
            if total != 10:
                raise ValueError('Formation must add up to 10 outfield players')
        return v


class PlayerSearchRequest(BaseModel):
    """Request parameters for player search."""
    
    name: Optional[str] = Field(None, max_length=50)
    position: Optional[str] = Field(None, pattern=r'^(GKP|DEF|MID|FWD)$')
    team_id: Optional[int] = Field(None, ge=1)
    min_cost: Optional[float] = Field(None, ge=0)
    max_cost: Optional[float] = Field(None, le=20.0)
    min_points: Optional[int] = Field(None, ge=0)
    sort_by: str = Field(default='expected_points', pattern=r'^(expected_points|form|total_points|now_cost|web_name)$')
    sort_order: str = Field(default='desc', pattern=r'^(asc|desc)$')
    limit: int = Field(default=20, ge=1, le=100)


class PlayerSearchResponse(BaseModel):
    """Response model for player search."""
    
    players: List[PlayerStats]
    total_count: int
    search_params: PlayerSearchRequest
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class FixtureData(BaseModel):
    """Fixture information data model."""
    
    fixture_id: int
    gameweek: int = Field(..., ge=1, le=38)
    home_team_id: int
    away_team_id: int
    home_difficulty: Optional[int] = Field(None, ge=1, le=5)
    away_difficulty: Optional[int] = Field(None, ge=1, le=5)
    kickoff_time: Optional[datetime] = None
    finished: bool = Field(default=False)
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class PlayerPredictionData(BaseModel):
    """Player prediction data model."""
    
    player_id: int
    expected_points: float = Field(..., ge=0)
    expected_minutes: Optional[float] = Field(None, ge=0, le=90)
    expected_goals: Optional[float] = Field(None, ge=0)
    expected_assists: Optional[float] = Field(None, ge=0)
    confidence_score: Optional[float] = Field(None, ge=0, le=1)
    model_version: Optional[str] = None
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class APIResponse(BaseModel):
    """Standard API response format."""
    
    success: bool
    data: Optional[Union[Dict, List, str, int, float]] = None
    message: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ValidationErrorResponse(BaseModel):
    """Validation error response format."""
    
    success: bool = Field(default=False)
    error: str = Field(default="Validation error")
    details: Dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }