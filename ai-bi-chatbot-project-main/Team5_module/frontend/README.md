# Team5 Frontend README

This README documents the Team5 frontend SPA and how it connects to the Team5 backend.

## 1) Frontend Overview

Frontend stack:

- Vanilla JavaScript modules
- HTML + CSS
- Chart.js for chart rendering
- Browser fetch API with cookie-based sessions

The frontend consumes Team5 backend APIs for:

1. Authentication
2. File upload and mapping
3. Analysis dashboard
4. Team4 visualization payload display
5. NLP chat
6. Report generation and download

## 2) Frontend Directory Map

```text
Team5_module/
   frontend/
      index.html
      README.md
      css/
         variables.css
         global.css
         components.css
      js/
         app.js
         core/
            Router.js
            StateManager.js
            ApiClient.js
            AntiGravityEngine.js
         services/
            AuthService.js
            DataService.js
            AnalyticsService.js
            ReportService.js
         views/
            AuthView.js
            UploadView.js
            DashboardView.js
            ChatView.js
            ReportView.js
         components/
            Toast.js
            Sidebar.js
         effects/
            AntiGravity.js
```

## 3) Frontend Flow

High-level route flow in js/app.js:

1. /auth -> login/signup
2. /upload -> upload dataset and mapping
3. /dashboard -> KPIs and analysis results
4. /chat -> natural language Q/A
5. /reports -> generate and download report

State is handled by core/StateManager.js.
Routing is handled by core/Router.js.
API calls are centralized in core/ApiClient.js and service modules.

## 4) Backend URL Binding

Default backend base URL is defined in:

- js/core/ApiClient.js

Default behavior:

- Uses current browser hostname with port 5000
- Example: http://127.0.0.1:5000

If backend runs on another port, update ApiClient.js or set matching server port.

## 5) How To Run Frontend and Backend Together

Run these from project root: ai-bi-chatbot-project-main

### 5.1 Start backend

```powershell
cd Team5_module/backend
python -m pip install -r requirements.txt
python app.py
```

### 5.2 Start frontend

Open a second terminal:

```powershell
cd Team5_module/frontend
python -m http.server 3000
```

### 5.3 Open website

Open this URL in browser:

- http://127.0.0.1:3000

Backend API should be reachable at:

- http://127.0.0.1:5000

Health endpoint:

- http://127.0.0.1:5000/api/health

## 6) Frontend to Backend API Mapping

AuthService.js:

- POST /api/auth/signup
- POST /api/auth/login
- POST /api/auth/logout
- GET /api/auth/profile

DataService.js:

- POST /api/analysis/upload
- GET /api/analysis/preview/<file_id>
- GET /api/analysis/mapping-suggestions/<file_id>
- POST /api/analysis/remap/<file_id>

AnalyticsService.js:

- POST /api/analysis/analyze/<file_id>
- GET /api/analysis/dashboard-data/<file_id>
- GET /api/analysis/team4-visualization/<file_id>

ReportService.js:

- POST /api/analysis/chat/<file_id>
- GET /api/analysis/predefined-questions
- POST /api/analysis/generate-report/<file_id>
- GET /api/analysis/reports
- GET /api/analysis/report-preview/<report_id>
- GET /api/analysis/report-download/<report_id>/pdf

## 7) Required Changes On Another Computer

Before running on a different machine, verify:

1. Team5_module/backend/.env
   - SERVER_PORT and CORS_ALLOWED_ORIGINS
2. Team5_module/frontend/js/core/ApiClient.js
   - backend port if not 5000
3. Ensure browser opens frontend URL on 3000 and backend is alive on configured API port

## 8) Related Docs

1. Team5 backend guide: ../README.md
2. Project root guide: ../../README.md
3. Team5 runtime flow: ../../TEAM5_MODULE_RUNTIME_FLOW.md
