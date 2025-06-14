# Hot Durham Port Management System

## Overview
The Hot Durham system now includes a comprehensive port management system that provides clean service isolation, conflict resolution, and automated startup/shutdown procedures.

## Port Configuration

| Service | Port | Description |
|---------|------|-------------|
| Public Dashboard | 5001 | Public-facing environmental data dashboard |
| API Server | 5002 | RESTful API for data access |
| Live Sensor Map | 5003 | Interactive sensor map visualization |
| Predictive API | 5004 | Machine learning predictions and analytics |
| Streamlit GUI | 8502 | Administrative interface and data management |

## Key Features

### 1. Port Manager Utility (`./ports`)
- **Status Monitoring**: Real-time port usage and service health
- **Service Management**: Start/stop specific services or all services
- **Conflict Resolution**: Detect and resolve port conflicts
- **Force Termination**: SIGKILL option for stubborn processes
- **ZSH Compatibility**: Works with both bash and zsh shells

### 2. Enhanced Quick Start Script
- **Pre-startup Cleanup**: Automatically kills conflicting processes
- **Port Validation**: Verifies service binding before proceeding
- **Enhanced Error Handling**: Better error messages and recovery
- **Process Verification**: Confirms services are actually running
- **Integrated Management**: Uses port manager for all operations

### 3. Service Application Updates
All service applications now accept standardized command-line arguments:
- `--host`: Host to bind to (default varies by service)
- `--port`: Port to bind to (default as configured)
- `--debug`: Enable debug mode

## Usage

### Quick Start Commands
```bash
# Start all services
./scripts/deployment/quick_start.sh start

# Check service status
./scripts/deployment/quick_start.sh status

# Stop all services
./scripts/deployment/quick_start.sh stop

# Restart all services
./scripts/deployment/quick_start.sh restart

# Show help
./scripts/deployment/quick_start.sh help
```

### Port Manager Commands
```bash
# Show port status
./ports status

# Stop all services
./ports kill-all

# Stop specific service
./ports kill-service public_dashboard

# Force stop all services
./ports kill-all --force

# Check for conflicts
./ports check-conflicts
```

### Individual Service Startup
```bash
# Public Dashboard
python3 src/visualization/public_dashboard.py --port 5001 --debug

# API Server
python3 src/api/public_api.py --port 5002

# Live Sensor Map
python3 src/visualization/live_sensor_map.py --port 5003

# Predictive API
python3 src/ml/predictive_api.py serve --port 5004

# Streamlit GUI
streamlit run src/gui/enhanced_streamlit_gui.py --server.port 8502
```

## Technical Implementation

### Port Detection Logic
- Uses `lsof` for reliable port status checking
- Handles both IPv4 and IPv6 bindings
- Distinguishes between Hot Durham processes and external conflicts

### Process Management
- Graceful shutdown with SIGTERM
- Force termination with SIGKILL for stubborn processes
- PID file tracking for process lifecycle management
- Automatic cleanup of stale PID files

### Error Handling
- Port conflict detection and resolution
- Service startup verification
- Comprehensive logging and status reporting
- Fallback mechanisms for missing dependencies

### ZSH Compatibility
- Uses simple variables instead of associative arrays
- Compatible with both bash and zsh shells
- Proper error handling for shell differences

## Service Health Monitoring

### Status Indicators
- ✅ **ACTIVE**: Service running and port bound
- ❌ **FREE**: Port available, service not running
- ⚠️ **CONFLICT**: Port in use by external process

### Health Check Endpoints
- Public Dashboard: `http://localhost:5001/health`
- API Server: `http://localhost:5002/api/health`
- Live Sensor Map: `http://localhost:5003/api/health`
- Predictive API: `http://localhost:5004/api/v1/status`

## Logging and Debugging

### Log File Locations
- **Output Logs**: `logs/{service_name}_output.log`
- **PID Files**: `logs/{service_name}_pid.txt`
- **Port Manager Logs**: Integrated with service logs

### Debugging Commands
```bash
# View recent logs
./scripts/deployment/quick_start.sh logs

# Check specific service log
tail -f logs/Public_Dashboard_output.log

# Verify port usage
lsof -i :5001
```

## Best Practices

### Development Workflow
1. Always use `./scripts/deployment/quick_start.sh start` for development
2. Check status with `./ports status` before starting
3. Use `restart` command after code changes
4. Monitor logs for startup issues

### Production Deployment
1. Use environment-specific port configurations
2. Implement proper service monitoring
3. Set up log rotation for output files
4. Use systemd or similar for service management

### Troubleshooting
1. Check port conflicts with `./ports check-conflicts`
2. Review service logs for startup errors
3. Verify Python dependencies are installed
4. Ensure proper file permissions on scripts

## Future Enhancements

### Planned Features
- Service discovery and registration
- Load balancing for multiple instances
- Health check monitoring and alerts
- Integration with container orchestration
- Automated dependency management

### Configuration Management
- Environment-specific port mappings
- Service-specific configuration files
- Dynamic port allocation
- SSL/TLS termination support

---

**Last Updated**: June 13, 2025  
**Version**: 2.0.0  
**Author**: Hot Durham Development Team
