# User Guide

This guide explains how to use the Hot Durham Environmental Monitoring System dashboard and features.

## 🌐 Accessing the System

### Web Dashboard
- **URL**: `https://your-domain.com` (or `http://localhost:5000` for development)
- **Browser Requirements**: Modern browser (Chrome, Firefox, Safari, Edge)
- **Mobile Support**: Responsive design works on tablets and phones

### Authentication
- **Public Access**: Basic dashboard and data visualization
- **Admin Access**: Full system configuration and management
- **API Access**: Programmatic access with API keys

## 🏠 Dashboard Overview

### Main Dashboard

The main dashboard provides a comprehensive view of environmental data:

**Key Sections:**
- **Current Conditions** - Real-time weather and sensor data
- **Historical Trends** - Charts showing data over time
- **Alerts & Notifications** - System alerts and anomaly detection
- **System Status** - Health of sensors and data sources
- **Quick Actions** - Common tasks and exports

### Navigation Menu

- **🏠 Home** - Main dashboard
- **📊 Analytics** - Detailed data analysis
- **📈 Reports** - Generated reports and exports
- **⚙️ Settings** - System configuration (admin only)
- **📚 Help** - Documentation and support

## 📊 Data Visualization

### Current Conditions Widget

**Real-time Data Display:**
- Temperature (°F/°C)
- Humidity (%)
- Pressure (inHg/hPa)
- Wind Speed & Direction
- Precipitation
- Air Quality Index

**Features:**
- Auto-refresh every 5 minutes
- Units toggle (Imperial/Metric)
- Color-coded alerts for extreme values
- Timestamp of last update

### Historical Charts

**Available Chart Types:**
- **Line Charts** - Temperature, humidity trends
- **Bar Charts** - Precipitation, wind data
- **Heat Maps** - Data density over time
- **Scatter Plots** - Correlation analysis

**Interactive Features:**
- Zoom and pan
- Data point tooltips
- Legend toggle
- Export chart as PNG/PDF

**Time Ranges:**
- Last 24 hours
- Last 7 days
- Last 30 days
- Custom date range
- Year-over-year comparison

### Data Filtering

**Filter Options:**
- **Date Range** - Select specific time periods
- **Sensor Type** - Temperature, humidity, weather
- **Location** - Filter by geographic area
- **Data Quality** - Show only validated data

**Quick Filters:**
- Today's data
- This week
- This month
- Anomalies only
- Complete data only

## 🔔 Alerts and Notifications

### Alert Types

**Automatic Alerts:**
- **Temperature Extremes** - Above/below thresholds
- **Humidity Anomalies** - Unusual humidity levels
- **Sensor Failures** - Equipment malfunction
- **Data Gaps** - Missing data periods
- **System Errors** - Application issues

**Custom Alerts:**
- User-defined thresholds
- Specific sensor monitoring
- Time-based alerts
- Combination conditions

### Alert Management

**Alert Dashboard:**
- View active alerts
- Alert history
- Acknowledge alerts
- Set alert preferences

**Notification Methods:**
- Dashboard notifications
- Email alerts (if configured)
- SMS notifications (if configured)
- API webhooks

## 📈 Reports and Analytics

### Pre-built Reports

**Daily Summary:**
- 24-hour temperature range
- Average humidity
- Precipitation total
- Wind summary
- Notable events

**Weekly Report:**
- 7-day trends
- Comparison to previous week
- Anomaly summary
- Data quality metrics

**Monthly Analysis:**
- Monthly averages
- Extreme events
- Seasonal patterns
- Historical comparison

### Custom Reports

**Report Builder:**
1. Select data sources
2. Choose date range
3. Pick metrics to include
4. Set output format
5. Generate report

**Export Formats:**
- PDF report
- Excel spreadsheet
- CSV data
- JSON format
- Images (PNG/SVG)

### Analytics Features

**Trend Analysis:**
- Moving averages
- Seasonal decomposition
- Correlation analysis
- Regression modeling

**Anomaly Detection:**
- Statistical outliers
- Machine learning detection
- Threshold exceedances
- Pattern recognition

## 🛠️ System Configuration

### User Preferences

**Display Settings:**
- Temperature units (°F/°C)
- Pressure units (inHg/hPa)
- Time zone
- Theme (light/dark)
- Refresh intervals

**Dashboard Layout:**
- Widget arrangement
- Chart preferences
- Default time ranges
- Data display options

### Data Sources

**Weather APIs:**
- Weather Underground
- OpenWeatherMap
- Custom weather stations

**Sensor Networks:**
- TSI temperature sensors
- Humidity sensors
- Custom monitoring equipment

**Data Storage:**
- Google Sheets integration
- Database storage
- File exports

## 📱 Mobile Usage

### Mobile Dashboard

**Optimized Features:**
- Touch-friendly interface
- Simplified navigation
- Key metrics focus
- Quick data access

**Mobile-Specific:**
- Swipe gestures
- Tap to zoom
- Portrait/landscape support
- Offline data viewing

### Mobile Alerts

- Push notifications
- Location-based alerts
- Emergency notifications
- Data summaries

## 🔧 Troubleshooting

### Common Issues

**Dashboard Not Loading:**
1. Check internet connection
2. Clear browser cache
3. Try different browser
4. Check system status

**Data Not Updating:**
1. Verify data sources are active
2. Check alert notifications
3. Review system logs
4. Contact administrator

**Chart Display Issues:**
1. Refresh the page
2. Check browser compatibility
3. Disable ad blockers
4. Try different time range

### Performance Tips

**Faster Loading:**
- Use shorter time ranges
- Limit number of sensors
- Close unused browser tabs
- Use wired internet connection

**Better Experience:**
- Use latest browser version
- Enable JavaScript
- Allow location access
- Bookmark frequently used views

## 🎯 Best Practices

### Data Interpretation

**Understanding Readings:**
- Check data timestamps
- Verify sensor locations
- Consider weather conditions
- Review data quality indicators

**Trend Analysis:**
- Use appropriate time ranges
- Consider seasonal patterns
- Account for local factors
- Compare multiple metrics

### Efficient Usage

**Dashboard Navigation:**
- Use bookmarks for frequent views
- Set up custom dashboards
- Configure alert preferences
- Learn keyboard shortcuts

**Data Export:**
- Export only needed data
- Use appropriate formats
- Schedule regular exports
- Organize exported files

## ❓ Frequently Asked Questions

### General Usage

**Q: How often is data updated?**
A: Real-time data updates every 1-5 minutes, depending on the sensor type.

**Q: Can I view historical data?**
A: Yes, historical data is available from the system's start date with various time range options.

**Q: Is the system accessible on mobile devices?**
A: Yes, the dashboard is fully responsive and optimized for mobile use.

### Technical Questions

**Q: What browsers are supported?**
A: Chrome, Firefox, Safari, and Edge (latest versions recommended).

**Q: Can I export data for analysis?**
A: Yes, data can be exported in CSV, JSON, Excel, and PDF formats.

**Q: How do I set up custom alerts?**
A: Use the Settings menu to configure alert thresholds and notification preferences.

### Data Questions

**Q: What if I see gaps in the data?**
A: Data gaps may occur due to sensor maintenance, network issues, or API limitations. Check the system status for more information.

**Q: How accurate are the readings?**
A: Accuracy depends on sensor type and calibration. Most temperature sensors are accurate to ±0.5°C.

**Q: Can I compare data from different time periods?**
A: Yes, use the comparison features in the Analytics section to compare different time periods.

## 📞 Getting Help

### Self-Service Resources
- **User Guide** - This document
- **FAQ** - Common questions and answers
- **Video Tutorials** - Step-by-step guides
- **System Status** - Current system health

### Contact Support
- **Email**: support@hotdurham.org
- **Issue Tracker**: GitHub issues
- **Community Forum**: User discussions
- **Documentation**: Complete system documentation

### Training Resources
- **Quick Start Guide** - Get started quickly
- **Advanced Features** - Power user guide
- **API Documentation** - Programmatic access
- **Best Practices** - Optimization tips

---

*This user guide covers the most common features and use cases. For advanced configuration and development information, see the complete documentation wiki.*

*Last updated: June 15, 2025*
