# FPL AI Optimizer 🏆⚽

An intelligent Fantasy Premier League team optimizer that uses machine learning predictions and mathematical optimization to suggest optimal team selections, transfers, and captain choices with Thai-language reasoning explanations.

## 🌟 Features

### Core Functionality
- **Team Optimization**: AI-powered team selection using linear programming
- **Transfer Suggestions**: Smart transfer recommendations based on form and fixtures
- **Captain Selection**: Data-driven captain and vice-captain recommendations
- **Player Scouting**: Advanced player search and comparison tools
- **Thai Language Support**: Natural language explanations in Thai

### Technical Highlights
- **Machine Learning**: XGBoost models for player performance prediction
- **Mathematical Optimization**: PuLP-based linear programming for team selection
- **Real-time Data**: Integration with official FPL API
- **Intelligent Caching**: Redis-based caching for optimal performance
- **Service Architecture**: Clean separation of concerns with dedicated services

## 🏗️ Architecture

```
src/
├── models/           # Data models (SQLAlchemy & Pydantic)
├── services/         # Core business logic
│   ├── data_service.py         # FPL API integration
│   ├── prediction_service.py   # ML predictions
│   ├── optimization_service.py # Team optimization
│   └── reasoning_service.py    # Thai explanations
├── views/            # Flask blueprints (API & web routes)
├── templates/        # HTML templates with Tailwind CSS
└── static/           # Static assets
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose (recommended)
- Git

### Option 1: Docker Deployment (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd fpl-ml-system

# Copy environment template
cp .env.example .env

# Edit environment variables (optional)
nano .env

# Start the application
docker-compose up -d

# Access the application
open http://localhost:5000
```

### Option 2: Local Development

```bash
# Clone and setup virtual environment
git clone <repository-url>
cd fpl-ml-system
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env

# Initialize database
python scripts/setup_database.py

# Fetch initial FPL data
python scripts/fetch_fpl_data.py

# Train ML models
python scripts/train_models.py

# Run the application
flask run
```

## 📊 Usage Guide

### Web Interface

1. **Dashboard**: Overview of team performance and quick actions
2. **Team Optimizer**: Generate optimal 15-player squads with formation constraints
3. **Player Scouting**: Search and compare players with detailed statistics
4. **Transfer Analyzer**: Get transfer suggestions based on current team

### API Endpoints

```bash
# Health check
GET /api/health

# Get all teams
GET /api/teams

# Search players
GET /api/players/search?position=FWD&min_cost=5&max_cost=15

# Optimize team
POST /api/optimize
{
  "budget": 100.0,
  "formation": "4-4-2",
  "max_players_per_team": 3
}

# Get transfer suggestions
POST /api/optimize/transfers
{
  "current_team": [1, 2, 3, 4, 5, ...],
  "available_budget": 5.0,
  "max_transfers": 2
}

# Optimize captain selection
POST /api/optimize/captain
{
  "current_team": [1, 2, 3, 4, 5, ...]
}
```

## 🔧 Configuration

### Environment Variables

```env
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=sqlite:///data/fpl.db

# FPL API
FPL_API_BASE_URL=https://fantasy.premierleague.com/api/
CACHE_TTL=3600

# Optional: Redis for caching
REDIS_URL=redis://redis:6379/0
```

### Docker Configuration

The application includes multiple Docker Compose profiles:

```bash
# Basic deployment
docker-compose up -d

# Production deployment with Nginx & backup
docker-compose --profile production up -d

# Development with hot reload
docker-compose -f docker-compose.dev.yml up -d
```

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest

# Run specific test categories
pytest tests/test_models/          # Model tests
pytest tests/test_services/        # Service tests  
pytest tests/test_views/          # API tests

# Run with coverage report
pytest --cov=src --cov-report=html
```

## 📈 Performance & Optimization

### Caching Strategy
- **Bootstrap Data**: Cached for 1 hour (teams, players, fixtures)
- **ML Predictions**: Cached for 6 hours per gameweek
- **Database Queries**: Indexed on critical fields (player names, team IDs)

### Optimization Constraints
- Maximum 3 players per team
- Exact formation requirements (2 GKP, 3-5 DEF, 3-5 MID, 1-3 FWD)
- Budget constraints (up to £100M)
- Player availability and injury status

### Scaling Considerations
- **Horizontal Scaling**: Multiple Gunicorn workers
- **Database**: SQLite for development, PostgreSQL recommended for production
- **Caching**: Redis cluster for distributed caching
- **Load Balancing**: Nginx reverse proxy with rate limiting

## 🔒 Security

### API Security
- Rate limiting (10 req/s for API, 30 req/s for web)
- Input validation with Pydantic models
- SQL injection prevention with SQLAlchemy ORM
- XSS protection with template escaping

### Production Security
- Non-root Docker user
- Security headers (HSTS, CSP, XSS protection)
- Secret key management via environment variables
- HTTPS support with SSL certificates

## 🛠️ Development

### Project Structure
```
fpl-ml-system/
├── src/                 # Application source code
├── tests/               # Test suite
├── scripts/             # Utility scripts
├── data/                # Database and data files
├── logs/                # Application logs
├── models/              # Trained ML models
├── requirements.txt     # Python dependencies
├── Dockerfile          # Container configuration
├── docker-compose.yml  # Multi-service setup
└── README.md           # This file
```

### Code Quality
```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking (if using mypy)
mypy src/
```

### Database Management
```bash
# Create new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Reset database (development only)
python scripts/setup_database.py
```

## 📋 Data Sources

### FPL Official API
- Player statistics and prices
- Team information and fixtures
- Gameweek data and deadlines
- Historical performance data

### Machine Learning Features
- Player form (last 5 games average)
- Expected points based on underlying stats
- Fixture difficulty ratings
- Team defensive/offensive strength
- Historical goal/assist patterns

## 🤖 AI & ML Components

### Prediction Models
- **XGBoost Regressor**: Primary model for expected points prediction
- **Feature Engineering**: Form, fixtures, team strength, positional factors
- **Model Training**: Automated retraining with new gameweek data
- **Validation**: Cross-validation with historical data splits

### Optimization Engine
- **Linear Programming**: PuLP-based mathematical optimization
- **Constraints**: Formation, budget, team limits, player availability
- **Objective Function**: Maximize expected points within constraints
- **Solver**: CBC optimizer for reliable solution finding

### Reasoning Engine
- **Template-based**: Structured explanation templates in Thai
- **Context Aware**: Incorporates form, fixtures, and player attributes
- **Randomization**: Varied explanations to avoid repetition
- **Multi-factor**: Considers multiple decision factors

## 🚨 Troubleshooting

### Common Issues

**Database Connection Errors**
```bash
# Reset database
python scripts/setup_database.py
# Check file permissions
ls -la data/fpl.db
```

**FPL API Rate Limiting**
```bash
# Check cache status
curl localhost:5000/api/health
# Increase cache TTL in .env
```

**Docker Container Issues**
```bash
# View container logs
docker-compose logs fpl-optimizer
# Restart services
docker-compose restart
```

**Memory Issues During Optimization**
```bash
# Reduce worker count in Dockerfile
CMD ["gunicorn", "--workers", "2", ...]
# Increase Docker memory limits
```

### Performance Monitoring

```bash
# View application logs
docker-compose logs -f fpl-optimizer

# Monitor Redis cache
docker-compose exec redis redis-cli monitor

# Database query performance
sqlite3 data/fpl.db "EXPLAIN QUERY PLAN SELECT ..."
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`pytest`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open Pull Request

### Development Guidelines
- Follow PEP 8 code style
- Add tests for new features
- Update documentation
- Ensure Docker builds successfully
- Test with actual FPL data

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Fantasy Premier League** for providing the official API
- **Thai FPL Community** for feedback and feature suggestions
- **Open Source Libraries**: Flask, SQLAlchemy, XGBoost, PuLP, Pydantic
- **Frontend**: Tailwind CSS, Chart.js for beautiful and responsive UI

## 📧 Support

For support, feature requests, or bug reports:
- Open an issue on GitHub
- Check the troubleshooting section
- Review the API documentation
- Check logs for error details

---

**Built with ❤️ for the Thai FPL community** 🇹🇭⚽