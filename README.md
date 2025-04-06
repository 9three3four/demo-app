# Trading Platform MVP

A cost-efficient and reliable trading platform built with FastAPI and Next.js.

## Features

- Real-time price feeds and order updates via WebSocket
- Secure user authentication with JWT and 2FA
- Risk management engine
- Order execution system
- Market data access
- Modern, responsive UI (to be implemented in frontend)

## Backend Architecture

- **FastAPI** for high-performance API endpoints
- **PostgreSQL** for reliable data storage
- **Redis** for caching and session management
- **WebSocket** for real-time updates
- **SQLAlchemy** for ORM
- **Pydantic** for data validation
- **JWT** for authentication

## Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL
- Redis

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd trading-platform-mvp
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r backend/requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Initialize the database:
```bash
# Make sure PostgreSQL is running
python -m backend.main
```

### Running the Application

1. Start the backend server:
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

2. Access the API documentation:
- OpenAPI (Swagger): http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Authentication
- `POST /api/v1/users/register` - Register new user
- `POST /api/v1/users/login` - User login
- `POST /api/v1/users/2fa/enable` - Enable 2FA

### Trading
- `POST /api/v1/trading/orders` - Create new order
- `GET /api/v1/trading/orders` - List user's orders
- `GET /api/v1/trading/orders/{order_id}` - Get order details
- `DELETE /api/v1/trading/orders/{order_id}` - Cancel order
- `GET /api/v1/trading/market-data/{symbol}` - Get market data

### Risk Management
- `GET /api/v1/risk/limits` - Get risk limits
- `GET /api/v1/risk/account-risk` - Get account risk metrics
- `GET /api/v1/risk/position-risk/{symbol}` - Get position risk metrics

### WebSocket
- `WSS /ws` - WebSocket endpoint for real-time updates
  - Subscribe to price feeds
  - Receive order status updates

## Security Features

- JWT authentication
- Two-factor authentication (2FA)
- Password hashing with bcrypt
- Input validation and sanitization
- Rate limiting
- CORS protection

## Error Handling

The API uses standard HTTP status codes and returns consistent error responses:

```json
{
    "detail": "Error message",
    "error_code": "ERROR_CODE",
    "timestamp": "2023-11-22T10:00:00Z"
}
```

## Monitoring

- Comprehensive logging with structured JSON format
- Request timing middleware
- Health check endpoint at `/health`

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.