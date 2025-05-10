const express = require('express');
const fetch = require('node-fetch');
const fs = require('fs');
const app = express();
const PORT = 3000;

const wu_key = JSON.parse(fs.readFileSync('./wu_api_key.json')).test_api_key;

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

app.listen(PORT, () => {
  console.log(`API proxy running at http://localhost:${PORT}`);
});
