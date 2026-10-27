import os
import requests
import logging
from flask import Flask, request, jsonify, make_response

# Initialize Flask App
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_access_token():
    response = requests.post(
        "https://accounts.zoho.in/oauth/v2/token",
        data={
            "refresh_token": os.environ["ZOHO_REFRESH_TOKEN"],
            "client_id": os.environ["ZOHO_CLIENT_ID"],
            "client_secret": os.environ["ZOHO_CLIENT_SECRET"],
            "grant_type": "refresh_token",
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def predict_with_quickml(row):
    QUICKML_URL = "https://api.catalyst.zoho.in/quickml/v1/project/91968000000013050/endpoints/predict"
    
    headers = {
        "X-QUICKML-ENDPOINT-KEY": os.environ["QUICKML_ENDPOINT_KEY"],
        "Authorization": f"Zoho-oauthtoken {get_access_token()}",
        "CATALYST-ORG": "60093101864",
        "Environment": "Development",
        "Content-Type": "application/json",
    }

    payload = {
        "data": {
            "timestamp": row["timestamp"],
            "ambient_temp_c": float(row["ambient_temp_c"]),
            "humidity_pct": float(row["humidity_pct"]),
            "solar_irradiance_wm2": float(row["solar_irradiance_wm2"]),
        }
    }

    response = requests.post(QUICKML_URL, headers=headers, json=payload, timeout=25)
    response.raise_for_status()

    result = response.json().get("result")
    if not result:
        raise ValueError("QuickML returned an empty prediction.")

    prediction = result[0]
    if isinstance(prediction, dict):
        prediction = prediction.get("prediction")

    return float(prediction)


# (Step 4 Code): The Grid Transition Logic
def process_forecast(prediction, timestamp_str):
    demand = float(prediction)
    
    # Extract hour from "YYYY-MM-DD HH:MM:SS"
    hour = int(timestamp_str.split(" ")[1].split(":")[0])
    
    # Grid transition logic
    use_renewable_storage = (demand > 160) or (18 <= hour <= 22)
    critical_overload = demand >= 200
    
    return {
        "forecast_kw": round(demand, 2),
        "grid_source": "Renewable Storage" if use_renewable_storage else "Main Grid",
        "critical_overload": critical_overload
    }


# ==========================================
# ROUTES
# ==========================================

# (Step 3 Code): The Safe Diagnostic Route
@app.route('/diagnostic', methods=['GET', 'POST'])
def diagnostic():
    required_keys = [
        "QUICKML_ENDPOINT_KEY", 
        "ZOHO_CLIENT_ID", 
        "ZOHO_CLIENT_SECRET", 
        "ZOHO_REFRESH_TOKEN"
    ]
    
    missing_keys = [key for key in required_keys if key not in os.environ]
    
    return make_response(jsonify({
        "status": "diagnostic",
        "missing_variables": missing_keys,
        "is_quickml_key_present": "QUICKML_ENDPOINT_KEY" in os.environ
    }), 200)


# The Actual Prediction Route
@app.route('/quickml-test', methods=['POST'])
def quickml_test():
    try:
        # 1. Get data from the POST request body
        req_data = request.get_json()
        row = req_data.get("data", {})
        
        # 2. Call the QuickML API
        raw_prediction = predict_with_quickml(row)
        
        # 3. Apply the project requirements (Step 4 logic)
        final_result = process_forecast(raw_prediction, row["timestamp"])
        
        # 4. Return the formatted response to your frontend
        return make_response(jsonify({
            "status": "success",
            "data": final_result
        }), 200)
        
    except (KeyError, TypeError, ValueError) as exc:
        logger.exception("Prediction error: %s", exc)
        return make_response(jsonify({
            "status": "error",
            "error_type": type(exc).__name__,
            "error_detail": str(exc),
        }), 400)
    except Exception as e:
        logger.exception("Unexpected error: %s", e)
        return make_response(jsonify({
            "status": "error",
            "error_type": type(e).__name__,
            "error_detail": str(e),
        }), 500)