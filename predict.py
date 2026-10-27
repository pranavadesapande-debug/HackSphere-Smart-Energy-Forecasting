
import os
import numpy as np
import pandas as pd
import requests

QUICKML_ENDPOINT_URL = os.getenv("QUICKML_ENDPOINT_URL", "").strip()


def predict(input_df: pd.DataFrame) -> np.ndarray:
    required = [
        "timestamp",
        "ambient_temp_c",
        "humidity_pct",
        "solar_irradiance_wm2",
    ]

    missing = [c for c in required if c not in input_df.columns]
    if missing:
        raise ValueError(f"Missing input columns: {missing}")

    if input_df.empty:
        return np.array([], dtype=float)

    if not QUICKML_ENDPOINT_URL:
        raise RuntimeError("Set QUICKML_ENDPOINT_URL before running.")

    endpoint_key = os.getenv("QUICKML_ENDPOINT_KEY", "").strip()
    access_token = os.getenv("ZOHO_ACCESS_TOKEN", "").strip()
    catalyst_org = os.getenv("CATALYST_ORG", "").strip()
    environment = os.getenv("QUICKML_ENVIRONMENT", "Development").strip()

    if not all([endpoint_key, access_token, catalyst_org]):
        raise RuntimeError(
            "Set QUICKML_ENDPOINT_KEY, ZOHO_ACCESS_TOKEN, "
            "and CATALYST_ORG environment variables."
        )

    headers = {
        "X-QUICKML-ENDPOINT-KEY": endpoint_key,
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "CATALYST-ORG": catalyst_org,
        "Environment": environment,
        "Content-Type": "application/json",
    }

    predictions = []

    with requests.Session() as session:
        for index, row in input_df[required].iterrows():
            record = row.to_dict()

            # Convert pandas timestamps to the format used in
            # the QuickML sample request.
            record["timestamp"] = str(
                pd.to_datetime(record["timestamp"]).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )

            response = session.post(
                QUICKML_ENDPOINT_URL,
                headers=headers,
                json={"data": record},
                timeout=90,
            )

            
            if not response.ok:
                 print("HTTP status:", response.status_code)
                 print("Zoho error response:", response.text[:2000])
                 raise RuntimeError("QuickML request failed.")


            body = response.json()

            # Support the response shapes shown/documented by
            # the endpoint, without inventing a prediction.
            values = body.get("result", body.get("predictions"))

            if isinstance(values, (int, float)):
                values = [values]

            if not isinstance(values, list) or len(values) != 1:
                raise RuntimeError(
                    f"Unexpected QuickML response on row {index}: "
                    f"{body}"
                )

            predictions.append(float(values[0]))

    return np.asarray(predictions, dtype=float)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="sample_test_input.csv")
    parser.add_argument("--output", default="predictions.csv")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    preds = predict(df)

    if len(preds) != len(df):
        raise RuntimeError("Prediction count does not match input rows.")

    output = pd.DataFrame({
        "timestamp": df["timestamp"],
        "prediction": preds,
    })
    output.to_csv(args.output, index=False)

    print(f"Saved {len(preds)} real QuickML predictions to {args.output}")
    print(output.head())
