const express = require('express');
const fetch = require('node-fetch');
const fs = require('fs');
const path = require('path');
const app = express();
const PORT = 3000;

const wu_key = JSON.parse(fs.readFileSync('./wu_api_key.json')).test_api_key;
const tsi_creds = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../tsi_creds.json')));

async function getTSIToken() {
  const resp = await fetch('https://api-prd.tsilink.com/api/v3/external/oauth/client_credential/accesstoken?grant_type=client_credentials', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: `client_id=${tsi_creds.key}&client_secret=${tsi_creds.secret}`
  });
  const data = await resp.json();
  return data.access_token;
}

app.use(express.static('../frontend'));

app.get('/api/wu/:stationId', async (req, res) => {
  const stationId = req.params.stationId;
  const url = `https://api.weather.com/v2/pws/observations/current?stationId=${stationId}&format=json&units=m&apiKey=${wu_key}`;
  
  try {
    const response = await fetch(url);
    const json = await response.json();
    const obs = json.observations[0];

    res.json({
      temp: obs.metric.temp,
      humidity: obs.humidity,
      wind: obs.metric.windSpeed
    });
  } catch (e) {
    res.status(500).json({ error: "Failed to fetch data" });
  }
});

app.get('/api/tsi/devices', async (req, res) => {
  try {
    const token = await getTSIToken();
    const resp = await fetch('https://api-prd.tsilink.com/api/v3/external/devices', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const devices = await resp.json();
    res.json(devices);
  } catch (e) {
    res.status(500).json({ error: 'Failed to fetch TSI devices' });
  }
});

app.get('/api/tsi/:deviceId', async (req, res) => {
  const deviceId = req.params.deviceId;
  try {
    const token = await getTSIToken();
    // Get last 24h data (or latest)
    const now = new Date();
    const start = new Date(now.getTime() - 24*60*60*1000).toISOString();
    const end = now.toISOString();
    const url = `https://api-prd.tsilink.com/api/v3/external/telemetry?start_date=${start}&end_date=${end}&device_id=${deviceId}`;
    const resp = await fetch(url, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await resp.json();
    // Return the latest record if available
    if (Array.isArray(data) && data.length > 0) {
      res.json(data[data.length - 1]);
    } else {
      res.status(404).json({ error: 'No data found for device' });
    }
  } catch (e) {
    res.status(500).json({ error: 'Failed to fetch TSI data' });
  }
});

app.listen(PORT, () => {
  console.log(`API proxy running at http://localhost:${PORT}`);
});

// Do the same with one drive (teams folder)
// (manual is easy, but try automatic)
// weekly file of data
// (check data weekly to see if it is working well)
//dont need to download daily but would be good to check daily
// maybe cn
// can make map to make sure its not weird
// can join TSI with hotdurham gmail
// dashboard with sensors

//in future: maps available for the public (run online)





// maybe also add 45 days

