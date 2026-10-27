
from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np
import io
import os

app = Flask(__name__)
CORS(app)

REQUIRED_COLUMNS = [
    "timestamp",
    "ambient_temp_c",
    "humidity_pct",
    "solar_irradiance_wm2",
]

NUMERIC_COLUMNS = [
    "ambient_temp_c",
    "humidity_pct",
    "solar_irradiance_wm2",
]


def read_telemetry(file):
    """Read, validate, and clean an uploaded telemetry CSV."""
    if not file or not file.filename:
        raise ValueError("Please select a CSV file.")

    if not file.filename.lower().endswith(".csv"):
        raise ValueError("Only CSV files are supported.")

    content = file.read()

    if not content:
        raise ValueError("The uploaded CSV is empty.")

    df = pd.read_csv(io.BytesIO(content))

    if df.empty:
        raise ValueError("The CSV contains no rows.")

    missing = [
        column for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "Missing required columns: " + ", ".join(missing)
        )

    total_rows = len(df)
    df = df[REQUIRED_COLUMNS].copy()

    df["timestamp"] = pd.to_datetime(
        df["timestamp"], errors="coerce"
    )

    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(
            df[column], errors="coerce"
        )

    # Reject impossible sensor values as invalid.
    df.loc[
        ~df["humidity_pct"].between(0, 100),
        "humidity_pct"
    ] = np.nan

    df.loc[
        df["solar_irradiance_wm2"] < 0,
        "solar_irradiance_wm2"
    ] = np.nan

    invalid_rows = int(df.isna().any(axis=1).sum())
    df = df.dropna().sort_values("timestamp")

    if df.empty:
        raise ValueError("No valid telemetry rows remain after cleaning.")

    return df, total_rows, invalid_rows


def switching_decision(demand_kw, timestamp):
    """Apply the HackSphere energy-source transition rules."""
    hour = timestamp.hour

    renewable_mode = (
        demand_kw > 160
        or 18 <= hour <= 22
    )

    return {
        "source": (
            "Renewable Storage"
            if renewable_mode
            else "Main Grid"
        ),
        "critical_overload": bool(demand_kw >= 200),
        "hour": hour,
    }


def generate_demo_forecast(latest_row):
    """
    Generate DEMO values for UI and workflow testing only.
    This is not a trained model and must not be presented
    as actual QuickML predictions.
    """
    start_time = latest_row["timestamp"] + pd.Timedelta(hours=1)

    temperature = float(latest_row["ambient_temp_c"])
    humidity = float(latest_row["humidity_pct"])
    solar = float(latest_row["solar_irradiance_wm2"])

    # Illustrative baseline derived from the latest input row.
    baseline = (
        115
        + max(temperature - 25, 0) * 1.2
        + humidity * 0.08
        - min(solar, 1000) * 0.015
    )

    results = []

    for offset in range(24):
        timestamp = start_time + pd.Timedelta(hours=offset)
        hour = timestamp.hour

        # Illustrative daily demand pattern, not model inference.
        daily_pattern = (
            18 * np.sin((hour - 7) * np.pi / 12)
            + 22 * np.exp(-((hour - 20) / 3) ** 2)
        )

        demand_kw = round(
            max(0, baseline + daily_pattern), 2
        )

        decision = switching_decision(demand_kw, timestamp)

        results.append({
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "hour": timestamp.strftime("%H:%M"),
            "predicted_demand_kw": demand_kw,
            "recommended_source": decision["source"],
            "critical_overload": decision["critical_overload"],
        })

    return results


@app.get("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "Smart Energy Forecasting API",
    })


@app.post("/api/telemetry/upload")
def upload_telemetry():
    try:
        df, total_rows, invalid_rows = read_telemetry(
            request.files.get("file")
        )

        preview_df = df.head(5).copy()
        preview_df["timestamp"] = preview_df[
            "timestamp"
        ].dt.strftime("%Y-%m-%d %H:%M:%S")

        return jsonify({
            "message": "CSV validated successfully.",
            "total_rows": total_rows,
            "valid_rows": len(df),
            "invalid_rows_removed": invalid_rows,
            "preview": preview_df.to_dict(orient="records"),
            "note": "This endpoint validates data only.",
        })

    except (ValueError, pd.errors.ParserError) as exc:
        return jsonify({"error": str(exc)}), 400

    except Exception:
        app.logger.exception("Telemetry upload failed")
        return jsonify({
            "error": "Unexpected error while processing the CSV."
        }), 500


@app.post("/api/forecast")
def forecast():
    """
    Accept telemetry CSV and return a 24-hour forecast.
    Current implementation is demo mode only.
    """
    try:
        df, total_rows, invalid_rows = read_telemetry(
            request.files.get("file")
        )

        latest_row = df.iloc[-1]
        predictions = generate_demo_forecast(latest_row)

        return jsonify({
            "status": "success",
            "forecast_mode": "DEMO_NOT_QUICKML",
            "is_real_model_prediction": False,
            "message": (
                "Demo forecast only. Real QuickML integration "
                "has not been connected."
            ),
            "input_rows": total_rows,
            "valid_rows": len(df),
            "invalid_rows_removed": invalid_rows,
            "forecast_count": len(predictions),
            "forecasts": predictions,
        })

    except (ValueError, pd.errors.ParserError) as exc:
        return jsonify({"error": str(exc)}), 400

    except Exception:
        app.logger.exception("Forecast generation failed")
        return jsonify({
            "error": "Unexpected error while generating the forecast."
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
