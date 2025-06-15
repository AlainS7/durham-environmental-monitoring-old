# Architecture Overview

This document provides a comprehensive overview of the Hot Durham Environmental Monitoring System architecture, including its components, data flow, and design principles.

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Hot Durham System Architecture                │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   Data Sources   │    │  Data Collection │    │   Data Storage   │
│                  │    │                  │    │                  │
│ • Weather API    │───▶│ • Async Fetchers │───▶│ • SQLite/MySQL   │
│ • TSI Sensors    │    │ • Rate Limiting  │    │ • Google Sheets  │
│ • Custom APIs    │    │ • Error Handling │    │ • File Storage   │
│ • Manual Input   │    │ • Validation     │    │ • Cache Layer    │
└──────────────────┘    └──────────────────┘    └──────────────────┘
         │                        │                        │
         │                        ▼                        │
         │              ┌──────────────────┐               │
         │              │  Data Processing │               │
         │              │                  │               │
         │              │ • Data Cleaning  │               │
         │              │ • Aggregation    │               │
         │              │ • ML Analysis    │               │
         │              │ • Anomaly Det.   │               │
         │              └──────────────────┘               │
         │                        │                        │
         │                        ▼                        │
         │              ┌──────────────────┐               │
         └─────────────▶│   API Gateway    │◀──────────────┘
                        │                  │
                        │ • REST API       │
                        │ • Authentication │
                        │ • Rate Limiting  │
                        │ • Documentation  │
                        └──────────────────┘
                                 │
                                 ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  Web Dashboard   │    │   Reporting      │    │   Monitoring     │
│                  │    │                  │    │                  │
│ • Real-time UI   │    │ • Scheduled      │    │ • Health Checks  │
│ • Interactive    │    │ • PDF Reports    │    │ • Alerts         │
│ • Visualizations │    │ • Email Alerts   │    │ • Performance    │
│ • Mobile Resp.   │    │ • Export Tools   │    │ • Logging        │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

## Core Components

### 1. Data Collection Layer

**Purpose**: Responsible for gathering data from various external sources.

**Components**:
- **Weather Underground Client** (`src/data_collection/weather_underground.py`)
  - Asynchronous API calls
  - Rate limiting and retry logic
  - Data validation and normalization

- **TSI Sensor Interface** (`src/data_collection/tsi_interface.py`)
  - Direct sensor communication
  - Real-time data streaming
  - Error detection and recovery

- **Google Sheets Connector** (`src/data_collection/sheets_connector.py`)
  - Bidirectional data sync
  - Batch operations for efficiency
  - Conflict resolution

**Key Features**:
- Fault-tolerant design with retry mechanisms
- Asynchronous processing for performance
- Configurable collection intervals
- Data validation at ingestion point

### 2. Data Processing Engine

**Purpose**: Transforms raw data into actionable insights.

**Components**:
- **Data Validator** (`src/validation/data_validator.py`)
  - Schema validation
  - Range checking
  - Anomaly detection

- **ML Analysis Module** (`src/ml/analysis.py`)
  - Predictive modeling
  - Trend analysis
  - Pattern recognition

- **Data Aggregator** (`src/core/aggregator.py`)
  - Time-series aggregation
  - Statistical calculations
  - Data summarization

### 3. Storage Layer

**Purpose**: Persistent and efficient data storage with multiple backends.

**Storage Options**:
- **Primary Database** (SQLite/MySQL)
  - Structured data storage
  - ACID compliance
  - Query optimization

- **Google Sheets** (Secondary/Backup)
  - Human-readable format
  - Collaborative access
  - Real-time sharing

- **File System** (Raw data/logs)
  - Backup storage
  - Large file handling
  - Archive management

### 4. API Gateway

**Purpose**: Provides secure, standardized access to system functionality.

**Features**:
- RESTful API design
- JWT authentication
- Rate limiting
- API versioning
- Comprehensive documentation

**Endpoints**:
```
GET    /api/v1/sensors          - List all sensors
GET    /api/v1/sensors/{id}     - Get sensor details
GET    /api/v1/data/latest      - Latest readings
GET    /api/v1/data/historical  - Historical data
POST   /api/v1/data/export      - Export data
GET    /api/v1/health           - System health
```

### 5. User Interface Layer

**Purpose**: Web-based interface for system interaction and visualization.

**Components**:
- **Dashboard** (`src/gui/dashboard.py`)
  - Real-time data display
  - Interactive charts
  - Customizable widgets

- **Admin Panel** (`src/gui/admin.py`)
  - System configuration
  - User management
  - Maintenance tools

**Technologies**:
- Streamlit for rapid prototyping
- Plotly for interactive visualizations
- Responsive design for mobile devices

## Design Principles

### 1. Modularity
- Loosely coupled components
- Clear interface boundaries
- Easy component replacement
- Independent testing

### 2. Scalability
- Horizontal scaling support
- Efficient resource utilization
- Load balancing capabilities
- Performance monitoring

### 3. Reliability
- Fault tolerance
- Automatic recovery
- Data integrity
- Comprehensive logging

### 4. Security
- Input validation
- Authentication/authorization
- Secure API endpoints
- Data encryption

### 5. Maintainability
- Clean code architecture
- Comprehensive documentation
- Automated testing
- Version control

## Data Flow

### 1. Collection Flow
```
External APIs → Async Collectors → Validators → Database
     ↓
Rate Limiters → Error Handlers → Transformers → Cache
```

### 2. Processing Flow
```
Raw Data → Cleaning → Validation → Analysis → Storage
    ↓
Anomaly Detection → ML Models → Alerts → Notifications
```

### 3. Serving Flow
```
User Request → API Gateway → Authentication → Database Query
     ↓
Data Processing → Response Formatting → Caching → Response
```

## Technology Stack

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI / Flask
- **Database**: SQLite (dev), MySQL (prod)
- **Async**: asyncio, aiohttp
- **ML**: scikit-learn, pandas

### Frontend
- **Framework**: Streamlit
- **Visualization**: Plotly, Matplotlib
- **Styling**: CSS3, Bootstrap

### Infrastructure
- **Containerization**: Docker
- **Process Management**: systemd
- **Monitoring**: Custom health checks
- **Logging**: Python logging module

### External Services
- **Weather Underground API**
- **Google Sheets API**
- **TSI Sensor Network**

## Performance Characteristics

### Throughput
- **Data Collection**: 100+ requests/minute
- **API Responses**: <200ms average
- **Database Queries**: <50ms typical

### Scalability Limits
- **Concurrent Users**: 50+ simultaneous
- **Data Points**: 1M+ historical records
- **Sensors**: 100+ active monitoring points

### Resource Usage
- **Memory**: 256MB-1GB typical
- **CPU**: 10-30% on modest hardware
- **Storage**: 10GB+ for historical data

## Security Architecture

### Authentication
- JWT token-based authentication
- Role-based access control
- Session management

### Data Protection
- Input sanitization
- SQL injection prevention
- XSS protection
- HTTPS enforcement

### API Security
- Rate limiting
- Request validation
- Error message sanitization
- Audit logging

## Deployment Architecture

### Development
```
Local Machine → SQLite → File Storage → Debug Mode
```

### Production
```
Server/Container → MySQL → Distributed Storage → Production Mode
    ↓
Load Balancer → Multiple Instances → Shared Database
```

### Monitoring
```
Health Checks → Performance Metrics → Alert System → Notifications
```

## Future Enhancements

### Planned Improvements
1. **Microservices Architecture** - Break into smaller services
2. **Real-time Streaming** - WebSocket support for live updates
3. **Advanced ML** - More sophisticated predictive models
4. **Mobile App** - Native mobile application
5. **Cloud Deployment** - AWS/GCP deployment options

### Scalability Roadmap
1. **Database Sharding** - Horizontal database scaling
2. **Caching Layer** - Redis for improved performance
3. **Message Queue** - Asynchronous task processing
4. **CDN Integration** - Static asset delivery
5. **Auto-scaling** - Dynamic resource allocation

---

*This architecture document is maintained by the development team and updated as the system evolves.*
