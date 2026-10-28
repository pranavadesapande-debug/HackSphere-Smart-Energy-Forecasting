# HackSphere 3.0 – Smart Energy Microgrid & Demand Forecasting Engine

## Overview
A web-based energy management dashboard for demand forecasting, grid-source selection, and overload monitoring.

## Live Demo
https://slate-deploy-edkhhlxq.onslate.in/

## GitHub Repository
https://github.com/pranavadesapande-debug/HackSphere-Smart-Energy-Forecasting

## Features
- React + Vite dashboard
- Flask backend API
- CSV telemetry upload and validation
- 24-hour forecast workflow
- Grid switching based on demand and time
- Critical overload alert at 200 kW or above
- Zoho Catalyst Slate deployment
- QuickML model prepared for integration

## Grid Switching Rules
- Demand above 160 kW OR hour from 18:00 to 22:00: Renewable Storage
- Otherwise: Main Grid
- Demand at or above 200 kW: Critical Overload alert

## Technology Stack
- Frontend: React, Vite
- Backend: Python, Flask
- ML: Zoho Catalyst QuickML
- Hosting: Zoho Catalyst Slate

## Run Locally
### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Backend
Install backend dependencies, then run:
```bash
python backend/app.py
```

## Forecast Status
The dashboard currently supports demo-mode forecasts. Real QuickML prediction integration and end-to-end backend connectivity require final verification.

## Security
Do not commit API keys, OAuth tokens, or environment files. Configure credentials securely in the deployment environment.