# Rehearsed - Teacher Simulation Platform

An AI-powered platform for simulating classroom scenarios to help teachers practice and improve their pedagogical skills through realistic student interactions.

## 🎯 Overview

Rehearsed is a comprehensive teacher training platform that uses AI to simulate realistic classroom scenarios. Teachers can practice their instruction, classroom management, and student interaction skills in a safe, controlled environment with AI-powered student agents.

### Key Features

- **AI-Powered Student Simulation**: Realistic student personas with individual personalities and learning behaviors
- **Interactive Scenarios**: Pre-built classroom scenarios covering various teaching challenges
- **Real-time Chat Interface**: Natural conversation flow between teachers and AI students
- **Performance Analytics**: Feedback and assessment of teaching interactions
- **Admin Dashboard**: Manage scenarios, agents, and user accounts
- **Multi-environment Support**: Development, staging, and production deployments

## 🏗️ Architecture

### Backend (FastAPI + LangGraph)
- **FastAPI**: High-performance web framework with automatic API documentation
- **LangGraph**: Advanced AI workflow orchestration for conversational agents
- **PostgreSQL**: Primary database with pgvector for vector operations
- **Authentication**: JWT-based secure authentication system
- **Monitoring**: Prometheus metrics and Grafana dashboards
- **Rate Limiting**: Configurable API rate limiting

### Frontend (Angular)
- **Angular 20**: Modern TypeScript-based frontend framework
- **Angular Material**: Consistent UI components and theming
- **Responsive Design**: Works across desktop and mobile devices
- **Real-time Communication**: WebSocket support for live interactions

### Infrastructure
- **Docker**: Containerized deployment
- **Docker Compose**: Multi-service orchestration
- **Monitoring Stack**: Prometheus + Grafana + cAdvisor
- **Environment Management**: Multi-environment configuration

## 🚀 Quick Start

### Prerequisites

- **Docker & Docker Compose** (recommended for quick setup)
- **Python 3.13+** (for backend development)
- **Node.js 18+** (for frontend development)
- **PostgreSQL 16+** with pgvector extension

### Option 1: Docker Setup (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/drenfr01/rehearsed.git
   cd rehearsed
   ```

2. **Set up environment variables**
   ```bash
   cd backend
   cp .env.example .env.development
   # Edit .env.development with your configuration
   ```

3. **Start the full stack**
   ```bash
   cd backend
   make docker-compose-up ENV=development
   ```

4. **Access the application**
   - Frontend: http://localhost:4200
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Grafana Dashboard: http://localhost:3000 (admin/admin)
   - Prometheus: http://localhost:9090

### Option 2: Local Development Setup

#### Backend Setup

1. **Navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Install dependencies**
   ```bash
   make install
   ```

3. **Configure environment**
   ```bash
   make set-env ENV=development
   ```

4. **Start the development server**
   ```bash
   make dev
   ```

#### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start the development server**
   ```bash
   npm start
   ```

## 📊 Environment Configuration

The application supports multiple environments with specific configurations:

### Environment Files
- `.env.development` - Development environment
- `.env.staging` - Staging environment
- `.env.production` - Production environment
- `.env.test` - Testing environment

### Key Configuration Options

```bash
# Application
PROJECT_NAME=Rehearsed
VERSION=1.0.0
APP_ENV=development

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=rehearsed
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password

# AI/LLM Configuration
LLM_API_KEY=your_api_key
LLM_MODEL=gemini-2.5-flash
DEFAULT_LLM_TEMPERATURE=0.2

# Authentication
JWT_SECRET_KEY=your_secret_key
JWT_ALGORITHM=HS256

# Monitoring (optional)
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key
```

## 🎮 Usage

### For Teachers

1. **Login**: Access the platform with your credentials
2. **Select Scenario**: Choose from available classroom scenarios
3. **Review Objectives**: Understand the learning goals and student personas
4. **Start Simulation**: Interact with AI students in real-time
5. **Receive Feedback**: Get performance insights and improvement suggestions

### For Administrators

1. **Manage Scenarios**: Create and edit classroom scenarios
2. **Configure Agents**: Set up student personas and behaviors
3. **Monitor Usage**: Track platform usage and performance
4. **User Management**: Add/remove teachers and manage permissions

## 🔧 Development

### Backend Development

```bash
cd backend

# Install dependencies
make install

# Run development server with hot reload
make dev

# Run linting
make lint

# Format code
make format

# Run evaluations
make eval

# Run tests (when available)
make test
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm run build

# Run tests
npm test
```

### Docker Commands

```bash
cd backend

# Build Docker images
make docker-build                    # Build default image
make docker-build-env ENV=development  # Build for specific environment

# Run containers (app + db only)
make docker-run                      # Run default (development)
make docker-run-env ENV=development  # Run specific environment

# Full stack with monitoring (app + db + prometheus + grafana)
make docker-compose-up ENV=development

# View logs
make docker-logs ENV=development           # App and DB logs
make docker-compose-logs ENV=development   # All services logs

# Stop services
make docker-stop ENV=development           # Stop app + db
make docker-compose-down ENV=development   # Stop entire stack
```

## 📡 API Documentation

The API documentation is automatically generated and available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Main API Endpoints

- **Authentication**: `/api/v1/auth/*`
- **Chat/Simulation**: `/api/v1/chatbot/*`
- **Scenarios**: `/api/v1/scenario/*`
- **Administration**: `/api/v1/admin/*`

## 🗄️ Database Schema

The application uses PostgreSQL with the following main entities:

- **Users**: Teacher accounts and authentication
- **Sessions**: User sessions and authentication tokens
- **Scenarios**: Classroom simulation scenarios
- **Agents**: AI student personas
- **Agent Personalities**: Behavioral templates for students
- **Threads**: Conversation threads
- **Messages**: Individual chat messages

## 📊 Monitoring & Observability

### Metrics Collection
- **Prometheus**: System and application metrics
- **Grafana**: Visual dashboards and alerting
- **Langfuse**: LLM performance tracking
- **Structured Logging**: JSON-formatted logs for analysis

### Health Checks
- Application health: `/health`
- Database connectivity monitoring
- API response time tracking

## 🔒 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Rate Limiting**: Configurable API rate limits
- **CORS Configuration**: Proper cross-origin request handling
- **Input Validation**: Comprehensive request validation
- **Environment Separation**: Isolated configurations per environment

## 🧪 Testing

### Backend Testing
```bash
cd backend
# Run unit tests
pytest

# Run with coverage
pytest --cov=app
```

### Frontend Testing
```bash
cd frontend
# Run unit tests
npm test

# Run e2e tests
npm run e2e
```

## 🚀 Deployment

### Production Deployment

1. **Prepare environment file**
   ```bash
   cd backend
   cp .env.example .env.production
   # Configure production settings
   ```

2. **Build and deploy**
   ```bash
   make docker-build-env ENV=production
   make docker-compose-up ENV=production
   ```

3. **Monitor deployment**
   ```bash
   make docker-compose-logs ENV=production
   ```

### Staging Deployment

Similar to production but using staging configuration:
```bash
cd backend
make docker-compose-up ENV=staging
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow Python PEP 8 style guide for backend code
- Use Angular style guide for frontend code
- Write comprehensive tests for new features
- Update documentation for API changes
- Follow conventional commit message format

## 📄 License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.

## 🆘 Support & Troubleshooting

### Common Issues

**Database Connection Issues**
```bash
cd backend

# Check if PostgreSQL is running
make docker-compose-logs ENV=development

# Restart database
make docker-compose-down ENV=development
make docker-compose-up ENV=development
```

**Environment Variables Not Loading**
```bash
# Verify environment file exists
ls -la .env.development

# Check environment setting
make set-env ENV=development
```

**Port Conflicts**
- Backend: Default port 8000
- Frontend: Default port 4200
- PostgreSQL: Default port 5432
- Grafana: Default port 3000
- Prometheus: Default port 9090

### Performance Optimization

- Configure appropriate rate limits for your use case
- Adjust LLM parameters for response quality vs speed
- Monitor database performance and optimize queries
- Use caching strategies for frequently accessed data

### Getting Help

- Check the [GitHub Issues](https://github.com/drenfr01/rehearsed/issues) for known problems
- Review application logs for detailed error information
- Consult API documentation at `/docs` endpoint
- Monitor system metrics via Grafana dashboards

## 🔮 Roadmap

- Enhanced student persona customization
- Voice-based interactions
- Advanced analytics and reporting
- Integration with learning management systems
- Mobile application support
- Multi-language support

---

**Built with ❤️ for educators by the Rehearsed team**