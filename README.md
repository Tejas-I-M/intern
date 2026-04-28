# Team5 Module README

This document is for teammates. It explains the Team5 module in simple words.

## What This Module Does

Team5 is the full app layer for:

1. User login and session handling.
2. CSV/tabular upload and smart column mapping.
3. Core business analytics (KPIs, trends, segments, categories).
4. Advanced analytics modules (cohort, churn, forecast, CLV, etc.).
5. NLP chat Q&A over the uploaded dataset.
6. Report generation (HTML, Markdown, downloadable PDF).

## Project Parts

- `backend/`: Flask API and analytics/report logic.
- `frontend/`: Browser UI (vanilla JS).
- `data/`: Sample datasets.
- `models/`: ML model files used by backend (`*.pkl`).

## Quick Start

## 1) Run backend

```powershell
cd Team5_module/backend
python -m pip install -r requirements.txt
python app.py
```

Backend defaults to `http://127.0.0.1:5000`.

Run the main backend entry file directly from project root:

```powershell
cd ai-bi-chatbot-project-main
python Team5_module/backend/app.py
```

This starts the backend on port `5000` by default (or `SERVER_PORT` if you set it).

Port notes:

- Backend API default port: `5000`.
- Frontend static server (from command below): `3000`.
- If `5000` is already used, backend auto-picks the next free port and prints it in terminal as `Server URL`.

Force a custom backend port (PowerShell):

```powershell
$env:SERVER_PORT="5050"
python app.py
```

## 2) Run frontend

Open a new terminal:

```powershell
cd Team5_module/frontend
python -m http.server 3000
```

Open: `http://127.0.0.1:3000`

## 3) Health check

Open: `http://127.0.0.1:5000/api/health`

## Main User Flow

1. Sign up / login.
2. Upload a CSV file.
3. Check preview + mapping suggestions.
4. Run analysis.
5. Ask chat questions.
6. Generate report.
7. Preview report and download PDF.

## Most Important Files (Backend)

- `backend/app.py`
  : Flask app entry point, CORS, blueprint registration, cleanup worker.

- `backend/config.py`
  : Environment/config defaults (ports, CORS, model paths, cleanup).

- `backend/api/auth_routes.py`
  : Signup, login, logout, profile APIs.

- `backend/api/analysis_routes.py`
  : Upload, analyze, advanced modules, chat, report, export, history APIs.

- `backend/services/data_processor.py`
  : Data loading, schema mapping, validation, capability detection, optional ML model inference helpers.

- `backend/services/real_analytics_service.py`
  : Main analytics algorithms used by APIs (core + advanced modules).

- `backend/services/unified_nlp_analytics.py`
  : NLP intent pipeline (Team2 + analytics engine + optional Gemini).

- `backend/services/report_generator.py`
  : Markdown/HTML report generation and PDF export (WeasyPrint + ReportLab fallback).

- `backend/services/team4_visualization_adapter.py`
  : Team4 chart/insight bridge for visualization payload.

- `backend/auth/auth_handler.py`
  : Persistent user account and report metadata storage in JSON.

## Most Important Files (Frontend)

- `frontend/index.html`
  : Main UI shell.

- `frontend/js/app.js`
  : Route registration and app bootstrap.

- `frontend/js/core/ApiClient.js`
  : Base API URL and request wrapper.

- `frontend/js/services/*.js`
  : Auth/data/analytics/report API adapters.

## Where Data Is Stored

Runtime memory (clears on backend restart):

- Uploaded dataframes: `user_datasets` (in `analysis_routes.py`).
- Analysis results: `user_analyses`.
- Chat histories: `chat_histories`.
- Async jobs: `analysis_jobs`.

Persistent JSON/files on disk:

- Users + report metadata: `backend/credentials_of_users.json`.
- Recent analysis snapshots: `backend/recent_analyses.json`.
- Uploaded files: `backend/uploads/`.
- Generated reports: `backend/reports/` (`.md`, `.html`, `.pdf`).

## Report Notes

- Report preview uses saved HTML.
- PDF download tries WeasyPrint first.
- If WeasyPrint native libs are missing, backend automatically falls back to ReportLab.
- Advanced Summary now appears in both preview HTML and fallback PDF.

## Useful Commands

Run backend tests:

```powershell
cd Team5_module/backend
python -m pytest tests -q
```

Run only report tests:

```powershell
cd Team5_module/backend
python -m pytest tests/test_report_advanced_summary.py tests/test_report_history.py -q
```

## Troubleshooting

- If APIs seem stale, kill old backend processes and run one fresh `python app.py`.
- If browser shows auth/CORS issues, verify `CORS_ALLOWED_ORIGINS` in `backend/.env`.
- If PDF generation shows WeasyPrint native-lib warning, fallback PDF still works.
