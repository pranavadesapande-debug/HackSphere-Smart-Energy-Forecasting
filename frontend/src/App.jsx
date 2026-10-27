
import { useState } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Area,
  Line,
} from "recharts";
import "./App.css";

const API_URL = "http://127.0.0.1:5000";

function getRecommendedSource(demand, hour) {
  return demand > 160 || (hour >= 18 && hour <= 22)
    ? "Renewable Storage"
    : "Main Grid";
}

function App() {
  const [demand, setDemand] = useState(145);
  const [selectedHour, setSelectedHour] = useState("12:00");
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [forecasting, setForecasting] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [forecastResult, setForecastResult] = useState(null);
  const [error, setError] = useState("");

  const hour = Number(selectedHour.slice(0, 2));
  const recommendedSource = getRecommendedSource(demand, hour);
  const critical = demand >= 200;

  async function sendFile(endpoint) {
    if (!file) {
      setError("Please select a CSV file first.");
      return null;
    }

    if (!file.name.toLowerCase().endsWith(".csv")) {
      setError("Please select a CSV file.");
      return null;
    }

    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_URL}${endpoint}`, {
      method: "POST",
      body: formData,
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || "The request failed.");
    }

    return result;
  }

  async function handleValidate(event) {
    event.preventDefault();
    setError("");
    setUploadResult(null);

    setUploading(true);

    try {
      const result = await sendFile("/api/telemetry/upload");
      if (result) setUploadResult(result);
    } catch (err) {
      setError(
        `${err.message} Check that the Flask backend is running on port 5000.`
      );
    } finally {
      setUploading(false);
    }
  }

  async function handleForecast() {
    setError("");
    setForecastResult(null);
    setForecasting(true);

    try {
      const result = await sendFile("/api/forecast");
      if (!result) return;

      if (!Array.isArray(result.forecasts) || result.forecasts.length !== 24) {
        throw new Error("The backend did not return exactly 24 forecast entries.");
      }

      setForecastResult(result);
    } catch (err) {
      setError(
        `${err.message} Check the Flask terminal for details.`
      );
    } finally {
      setForecasting(false);
    }
  }

  const chartData = forecastResult
    ? forecastResult.forecasts.map((item) => ({
        hour: item.hour,
        demand: Number(item.predicted_demand_kw),
      }))
    : [];

  return (
    <main className="dashboard">
      <header className="topbar">
        <div>
          <p className="eyebrow">HACKSPHERE 3.0</p>
          <h1>Smart Energy Microgrid</h1>
          <p className="subtitle">
            Energy demand forecasting and source management
          </p>
        </div>
        <span className="live-badge">● System Online</span>
      </header>

      <section className="summary-grid">
        <article className="panel">
          <p className="label">Current Demo Demand</p>
          <h2>{demand} <small>kW</small></h2>
          <p>Use the simulator below to test the rules.</p>
        </article>

        <article className="panel">
          <p className="label">Recommended Source</p>
          <h2>{recommendedSource}</h2>
          <p>
            {hour >= 18 && hour <= 22
              ? "Evening time rule is active"
              : "Based on demand threshold"}
          </p>
        </article>

        <article className="panel">
          <p className="label">System Alert</p>
          <h2 className={critical ? "danger" : ""}>
            {critical ? "Critical Overload" : "Normal"}
          </h2>
          <p>
            {critical
              ? "Demand is at least 200 kW"
              : "No critical overload"}
          </p>
        </article>
      </section>

      <section className="panel controls">
        <h2>Demand Simulator</h2>
        <p>Adjust the sample demand and hour to test switching rules.</p>

        <label htmlFor="demand">Demand: {demand} kW</label>
        <input
          id="demand"
          type="range"
          min="50"
          max="250"
          value={demand}
          onChange={(event) => setDemand(Number(event.target.value))}
        />

        <div className="range-labels">
          <span>50 kW</span>
          <span>250 kW</span>
        </div>

        <label htmlFor="forecast-hour">Hour for switching-rule test</label>
        <select
          id="forecast-hour"
          className="hour-select"
          value={selectedHour}
          onChange={(event) => setSelectedHour(event.target.value)}
        >
          {Array.from({ length: 24 }, (_, h) => {
            const value = `${String(h).padStart(2, "0")}:00`;
            return <option key={value} value={value}>{value}</option>;
          })}
        </select>

        <div className="rule">
          <strong>Switching rules:</strong> Demand above 160 kW or time
          between 18:00–22:00 inclusive selects Renewable Storage.
          Demand at or above 200 kW triggers a critical alert independently.
        </div>
      </section>

      <section className="panel">
        <h2>Upload Energy Telemetry</h2>
        <p>
          Select a CSV containing timestamp, temperature, humidity, and solar
          irradiance data.
        </p>

        <form onSubmit={handleValidate} className="upload-form">
          <input
            type="file"
            accept=".csv,text/csv"
            className="file-input"
            onChange={(event) => {
              setFile(event.target.files?.[0] || null);
              setUploadResult(null);
              setForecastResult(null);
              setError("");
            }}
          />

          <button className="upload-button" type="submit" disabled={uploading}>
            {uploading ? "Validating..." : "Validate CSV"}
          </button>

          <button
            className="upload-button"
            type="button"
            onClick={handleForecast}
            disabled={forecasting || uploading || !file}
          >
            {forecasting ? "Generating..." : "Generate 24-Hour Forecast"}
          </button>
        </form>

        {file && <p className="file-name">Selected: {file.name}</p>}

        {error && (
          <div className="message error-message" role="alert">
            {error}
          </div>
        )}

        {uploadResult && (
          <div className="message success-message" role="status">
            <h3>CSV validation successful</h3>
            <p>Total rows: {uploadResult.total_rows}</p>
            <p>Valid rows: {uploadResult.valid_rows}</p>
            <p>Invalid rows removed: {uploadResult.invalid_rows_removed}</p>

            {uploadResult.preview?.length > 0 && (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Timestamp</th>
                      <th>Temp (°C)</th>
                      <th>Humidity (%)</th>
                      <th>Solar (W/m²)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {uploadResult.preview.map((row, index) => (
                      <tr key={`${row.timestamp}-${index}`}>
                        <td>{row.timestamp}</td>
                        <td>{row.ambient_temp_c}</td>
                        <td>{row.humidity_pct}</td>
                        <td>{row.solar_irradiance_wm2}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {forecastResult && (
          <div className="message success-message" role="status">
            <h3>24-hour forecast generated</h3>
            <p>
              Mode: <strong>{forecastResult.forecast_mode}</strong>
            </p>
            <p>
              {forecastResult.is_real_model_prediction
                ? "Generated by the connected model."
                : "Demo values only — Zoho QuickML is not connected yet."}
            </p>
            <p>Forecast entries: {forecastResult.forecast_count}</p>
          </div>
        )}
      </section>

      <section className="panel forecast">
        <h2>Next 24 Hours — Demand Forecast</h2>
        <p>
          {forecastResult
            ? "Values returned by the Flask forecast endpoint."
            : "Upload a CSV and generate a forecast to display the returned data."}
        </p>

        <div className="chart-container">
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart
                data={chartData}
                margin={{ top: 10, right: 12, left: 4, bottom: 10 }}
              >
                <defs>
                  <linearGradient id="demandFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#60a5fa" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#60a5fa" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#293a54" strokeDasharray="4 4" />
                <XAxis
                  dataKey="hour"
                  tick={{ fill: "#a9bdd7", fontSize: 11 }}
                  axisLine={{ stroke: "#40516b" }}
                  tickLine={false}
                  interval={3}
                />
                <YAxis
                  unit=" kW"
                  tick={{ fill: "#a9bdd7", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  width={65}
                />
                <Tooltip
                  contentStyle={{
                    background: "#131d30",
                    border: "1px solid #40516b",
                    borderRadius: 8,
                    color: "#f8fafc",
                  }}
                  formatter={(value) => [`${value} kW`, "Demand"]}
                />
                <Area
                  type="monotone"
                  dataKey="demand"
                  stroke="none"
                  fill="url(#demandFill)"
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="demand"
                  stroke="#60a5fa"
                  strokeWidth={3}
                  dot={false}
                  isAnimationActive={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          ) : (
            <div className="chart-empty">
              Your 24 hourly forecast will appear here.
            </div>
          )}
        </div>
      </section>

      {forecastResult && (
        <section className="panel">
          <h2>Hourly Energy Decisions</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Demand (kW)</th>
                  <th>Recommended Source</th>
                  <th>Critical Alert</th>
                </tr>
              </thead>
              <tbody>
                {forecastResult.forecasts.map((item) => (
                  <tr key={item.timestamp}>
                    <td>{item.timestamp}</td>
                    <td>{item.predicted_demand_kw}</td>
                    <td>{item.recommended_source}</td>
                    <td>{item.critical_overload ? "YES" : "No"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <footer>
        HackSphere 3.0 · Local prototype · Real QuickML integration pending
      </footer>
    </main>
  );
}

export default App;
