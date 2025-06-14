# Public Dashboard Deployment Guide

## 🌍 Hot Durham Public Dashboard

The Public Dashboard provides Durham residents with easy access to real-time air quality and weather data through a user-friendly web interface.

---

## 🚀 Quick Start

### 1. Start the Public Dashboard
```bash
cd "/Users/alainsoto/IdeaProjects/Hot Durham"
python src/visualization/public_dashboard.py
```

### 2. Access the Dashboard
- **Public Interface:** http://localhost:5001
- **Health Check:** http://localhost:5001/health

### 3. For Production Deployment
```bash
# Run on specific host/port
python src/visualization/public_dashboard.py --host 0.0.0.0 --port 8080

# Run without debug mode for production
python src/visualization/public_dashboard.py --host 0.0.0.0 --port 8080 --no-debug
```

---

## 📊 Available Features

### Main Dashboard
- **Real-time AQI Display** - Current overall air quality index for Durham
- **Health Recommendations** - Personalized advice based on current conditions
- **Sensor Grid** - Current readings from all monitoring locations
- **Interactive Map** - Click markers to see detailed sensor information
- **24-Hour Trends** - Historical data visualization

### Mobile-Friendly Design
- Responsive layout works on phones, tablets, and desktops
- Touch-friendly interface
- Optimized for readability on small screens

---

## 🔗 API Endpoints

All endpoints return JSON data and include proper error handling:

### Public Data APIs
```bash
# Get all sensor locations
curl http://localhost:5001/api/public/sensors

# Get current air quality readings
curl http://localhost:5001/api/public/air-quality

# Get current weather data
curl http://localhost:5001/api/public/weather

# Get health index and recommendations
curl http://localhost:5001/api/public/health-index

# Get 24-hour trend data
curl http://localhost:5001/api/public/trends

# System health check
curl http://localhost:5001/health
```

### Example Response (Health Index)
```json
{
    "overall_aqi": 52,
    "status": "Good",
    "color": "#4CAF50",
    "message": "Air quality is good. Perfect day for outdoor activities!",
    "recommendations": [
        "Great conditions for outdoor exercise",
        "Windows can be opened for fresh air",
        "No health precautions needed for general population"
    ],
    "last_updated": "2025-05-27T18:57:14.983589"
}
```

---

## 🔧 Configuration

### Environment Setup
The dashboard automatically handles missing credentials by providing demo data:

- **With Credentials:** Uses real API data from TSI and Weather Underground
- **Without Credentials:** Displays mock data for demonstration purposes

### Data Caching
- **Cache Duration:** 5 minutes (configurable)
- **Purpose:** Reduces API calls and improves performance
- **Automatic Refresh:** Data updates every 5 minutes

---

## 🛡️ Security & Privacy

### Public Safety Measures
- **Anonymized Locations:** Sensor coordinates are generalized
- **No Sensitive Data:** Only public air quality metrics exposed
- **Error Handling:** Graceful degradation when services unavailable

### Data Sources
- **Air Quality:** TSI sensor network (anonymized)
- **Weather:** Weather Underground stations
- **Health Index:** Calculated from EPA AQI standards

---

## 📱 User Experience

### What Residents See
1. **Current Conditions** - Easy-to-read AQI display with color coding
2. **Health Guidance** - Clear recommendations for outdoor activities
3. **Local Data** - Readings from multiple Durham neighborhoods
4. **Trends** - 24-hour charts showing air quality changes
5. **Educational Content** - Information about air quality metrics

### Accessibility Features
- **Color-blind Friendly** - Uses patterns and text in addition to colors
- **Screen Reader Compatible** - Proper ARIA labels and semantic HTML
- **Keyboard Navigation** - All features accessible without mouse
- **High Contrast** - Readable text and clear visual hierarchy

---

## 🔍 Monitoring

### Health Check
```bash
curl http://localhost:5001/health
```

Expected response:
```json
{
    "status": "healthy",
    "timestamp": "2025-05-27T18:56:51.934798",
    "version": "2.0.0"
}
```

### Error Monitoring
- **API Failures:** Automatically switch to cached or mock data
- **Service Downtime:** Display user-friendly error messages
- **Performance:** Monitor response times and cache hit rates

---

## 🌟 Key Benefits for Durham Residents

### Real-Time Information
- **Current Conditions** - Always up-to-date air quality data
- **Local Focus** - Data specific to Durham neighborhoods
- **Health Context** - Practical advice for daily activities

### Easy Access
- **No App Required** - Works in any web browser
- **Mobile Optimized** - Perfect for checking on-the-go
- **Fast Loading** - Optimized for quick access

### Educational Value
- **AQI Explanation** - Learn what air quality numbers mean
- **Health Impact** - Understand how air quality affects you
- **Environmental Awareness** - Track local environmental conditions

---

## 🛠️ Technical Details

### Technology Stack
- **Backend:** Python Flask
- **Frontend:** Bootstrap 5, Chart.js, Leaflet maps
- **Data:** Real-time APIs with caching
- **Maps:** OpenStreetMap tiles

### Performance Optimizations
- **Data Caching** - 5-minute cache reduces API calls
- **Lazy Loading** - Charts load only when needed
- **Compression** - Efficient data transfer
- **CDN Resources** - Fast loading of external libraries

---

## 📞 Support

### For Technical Issues
- Check the health endpoint: http://localhost:5001/health
- Review logs for error messages
- Verify internet connectivity for API access

### For Data Questions
- All air quality data follows EPA AQI standards
- Weather data sourced from Weather Underground
- Sensor locations are anonymized for privacy

---

**The Public Dashboard is now ready to serve Durham residents with real-time environmental data!**

*Last Updated: May 27, 2025*
