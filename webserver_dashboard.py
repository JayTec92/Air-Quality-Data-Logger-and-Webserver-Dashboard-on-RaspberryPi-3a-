import csv
import os
from collections import deque
from datetime import datetime

from flask import Flask, jsonify, send_file

LOGFILE = os.path.expanduser("~/Desktop/Sensortest/sensor_log.csv")

app = Flask(__name__)


def read_history(limit=1000000):
    """
    Liest die letzten 'limit' Zeilen aus der CSV,
    filtert fehlerhafte Einträge und gibt Listen für die Charts zurück.
    """
    if not os.path.exists(LOGFILE):
        return {
            "labels": [],
            "pm1": [],
            "pm25": [],
            "pm10": [],
            "temp": [],
            "hum": [],
        }

    rows = deque(maxlen=limit)

    with open(LOGFILE, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    labels = []
    pm1_list = []
    pm25_list = []
    pm10_list = []
    temp_list = []
    hum_list = []

    for r in rows:
        if r.get("dht_status") not in ("ok", "fallback"):
            continue
        if r.get("hm_status") not in ("ok", "fallback"):
            continue

        ts = r.get("timestamp")

        try:
            dt = datetime.fromisoformat(ts)
            label = dt.strftime("%H:%M")
        except:
            label = ts

        try:
            pm1 = float(r["pm1"])
            pm25 = float(r["pm2_5"])
            pm10 = float(r["pm10"])
            temp = float(r["temp_c"])
            hum = float(r["humidity"])
        except:
            continue

        labels.append(label)
        pm1_list.append(pm1)
        pm25_list.append(pm25)
        pm10_list.append(pm10)
        temp_list.append(temp)
        hum_list.append(hum)

    return {
        "labels": labels,
        "pm1": pm1_list,
        "pm25": pm25_list,
        "pm10": pm10_list,
        "temp": temp_list,
        "hum": hum_list,
    }


def read_latest():
    data = read_history(limit=500)
    if not data["labels"]:
        return None

    return {
        "time": data["labels"][-1],
        "pm1": data["pm1"][-1],
        "pm25": data["pm25"][-1],
        "pm10": data["pm10"][-1],
        "temp": data["temp"][-1],
        "hum": data["hum"][-1],
    }


@app.route("/api/history")
def api_history():
    return jsonify(read_history())


@app.route("/api/latest")
def api_latest():
    latest = read_latest()
    if latest is None:
        return jsonify({"error": "no data yet"}), 404
    return jsonify(latest)


@app.route("/download")
def download():
    if not os.path.exists(LOGFILE):
        return "No log file yet", 404
    return send_file(LOGFILE, mimetype="text/csv", as_attachment=True,
                     download_name="sensor_log.csv")


@app.route("/")
def index():
    return """
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <title>Luft-Sensor Dashboard</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { font-family: sans-serif; margin: 10px; background: #111; color: #eee; }
    .cards { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 15px; }
    .card {
      background: #222;
      padding: 10px 15px;
      border-radius: 8px;
      min-width: 140px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.5);
    }
    .card h3 { margin: 0 0 5px 0; font-size: 0.9rem; color: #aaa; }
    .card .value { font-size: 1.4rem; }
    canvas { background: #222; border-radius: 8px; }
    a.button {
      display: inline-block;
      margin-top: 10px;
      padding: 6px 10px;
      border-radius: 6px;
      background: #444;
      color: #eee;
      text-decoration: none;
      font-size: 0.9rem;
    }
    a.button:hover { background: #666; }
  </style>

  <!-- Chart.js & Zoom-Plugin -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js"></script>
</head>

<body>
  <h1>Luft-Sensor Dashboard</h1>

  <label for="range-select">Zeitraum: </label>
  <select id="range-select">
    <option value="all">Gesamter Zeitraum</option>
    <option value="1h">Letzte 1 Stunde</option>
    <option value="4h">Letzte 4 Stunden</option>
    <option value="1d">Letzte 24 Stunden</option>
    <option value="1w">Letzte 7 Tage</option>
    <option value="1m">Letzter Monat</option>
  </select>

  <br><br>

  <div class="cards">
    <div class="card"><h3>PM1.0</h3><div class="value" id="pm1-value">–</div></div>
    <div class="card"><h3>PM2.5</h3><div class="value" id="pm25-value">–</div></div>
    <div class="card"><h3>PM10</h3><div class="value" id="pm10-value">–</div></div>
    <div class="card"><h3>Temperatur</h3><div class="value" id="temp-value">–</div></div>
    <div class="card"><h3>Luftfeuchte</h3><div class="value" id="hum-value">–</div></div>
  </div>

  <a href="/download" class="button">CSV herunterladen</a>

  <h2>Feinstaub (PM)</h2>
  <canvas id="pm-chart"></canvas>

  <h2>Temperatur & Luftfeuchte</h2>
  <canvas id="th-chart"></canvas>

  <script>
    let pmChart = null;
    let thChart = null;

    async function fetchHistory() {
      const res = await fetch('/api/history');
      return await res.json();
    }
    async function fetchLatest() {
      const res = await fetch('/api/latest');
      return await res.json();
    }

    // ----- Filterfunktion -----
    function filterData(history, range) {
      if (range === "all") return history;
      const len = history.labels.length;
      let iMin = 0;

      switch (range) {
        case "1h": iMin = len - 60; break;
        case "4h": iMin = len - 240; break;
        case "1d": iMin = len - 1440; break;
        case "1w": iMin = len - 10080; break;
        case "1m": iMin = len - 43200; break;
      }
      if (iMin < 0) iMin = 0;

      return {
        labels: history.labels.slice(iMin),
        pm1: history.pm1.slice(iMin),
        pm25: history.pm25.slice(iMin),
        pm10: history.pm10.slice(iMin),
        temp: history.temp.slice(iMin),
        hum: history.hum.slice(iMin),
      };
    }

    // ----- Zoom-Konfiguration -----
    function zoomOptions() {
      return {
        pan: { enabled: true, mode: 'x', modifierKey: 'shift' },
        zoom: {
          wheel: { enabled: true },
          pinch: { enabled: true },
          mode: 'x',
        }
      };
    }

    function initCharts(data) {
      const ctxPm = document.getElementById('pm-chart').getContext('2d');
      const ctxTh = document.getElementById('th-chart').getContext('2d');

      pmChart = new Chart(ctxPm, {
        type: 'line',
        data: {
          labels: data.labels,
          datasets: [
            { label: 'PM1', data: data.pm1, fill: false },
            { label: 'PM2.5', data: data.pm25, fill: false },
            { label: 'PM10', data: data.pm10, fill: false },
          ]
        },
        options: {
          responsive: true,
          plugins: { zoom: zoomOptions() },
          scales: { x: { }, y: { title: { display: true, text: 'µg/m³' }} }
        }
      });

      thChart = new Chart(ctxTh, {
        type: 'line',
        data: {
          labels: data.labels,
          datasets: [
            { label: 'Temp °C', data: data.temp, fill: false },
            { label: 'Luftfeuchte %', data: data.hum, fill: false },
          ]
        },
        options: {
          responsive: true,
          plugins: { zoom: zoomOptions() },
          scales: { x: { }, y: { } }
        }
      });

      // Doppelklick → zoom reset
      document.getElementById("pm-chart").ondblclick = () => pmChart.resetZoom();
      document.getElementById("th-chart").ondblclick = () => thChart.resetZoom();
    }

    function updateCharts(data) {
      pmChart.data.labels = data.labels;
      pmChart.data.datasets[0].data = data.pm1;
      pmChart.data.datasets[1].data = data.pm25;
      pmChart.data.datasets[2].data = data.pm10;
      pmChart.update('none');

      thChart.data.labels = data.labels;
      thChart.data.datasets[0].data = data.temp;
      thChart.data.datasets[1].data = data.hum;
      thChart.update('none');
    }

    async function refresh() {
      const history = await fetchHistory();
      const range = document.getElementById("range-select").value;
      const filtered = filterData(history, range);
      updateCharts(filtered);

      const latest = await fetchLatest();
      if (!latest || latest.error) return;

      document.getElementById('pm1-value').textContent = latest.pm1.toFixed(1) + ' µg/m³';
      document.getElementById('pm25-value').textContent = latest.pm25.toFixed(1) + ' µg/m³';
      document.getElementById('pm10-value').textContent = latest.pm10.toFixed(1) + ' µg/m³';
      document.getElementById('temp-value').textContent = latest.temp.toFixed(1) + ' °C';
      document.getElementById('hum-value').textContent = latest.hum.toFixed(1) + ' %';
    }

    document.getElementById("range-select").addEventListener("change", async () => {
      const history = await fetchHistory();
      updateCharts(filterData(history, document.getElementById("range-select").value));
    });

    (async () => {
      const history = await fetchHistory();
      const range = document.getElementById("range-select").value;
      initCharts(filterData(history, range));
      await refresh();
      setInterval(refresh, 30000);
    })();
  </script>

</body>
</html>
"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
