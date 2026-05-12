# Nexus AI Analytics Platform - Complete Project Documentation

**Project Name:** Nexus AI Analytics Platform (Team5 Module)  
**Version:** Final Complete Documentation  
**Purpose:** End-to-end BI platform for uploading datasets, automated schema mapping, multi-dimensional analytics, NLP chat, and report generation.

---

## 📋 Quick Navigation

1. [Problem Statement](#problem-statement)
2. [Tech Stack Summary](#tech-stack-summary)
3. [User Workflow (Visual Flow)](#user-workflow)
4. [Architecture Overview](#architecture-overview)
5. [Module Definitions (12 Advanced Analytics Modules)](#module-definitions)
6. [Complete File Inventory](#complete-file-inventory)
7. [Team1, Team2, Team3, Team4 Integration](#team-integration-details)
8. [Backend API Reference](#backend-api-reference)
9. [End-to-End Data Flow](#end-to-end-data-flow)
10. [Interview Q&A Preparation](#interview-qa-preparation)

---

## Problem Statement

**Business Challenge:**  
Organizations have raw sales/customer data but struggle to convert it into actionable insights quickly. Traditional workflows require:

- Manual data cleaning (hours/days of effort)
- Manual column mapping (error-prone naming convention issues)
- Heavy analyst involvement (bottleneck for decision-making)
- Separate tools for dashboards, chat, and reporting

**Our Solution:**  
One unified, end-to-end platform that automates the entire analytics journey:

```
Login → Upload Dataset → Auto Schema Mapping →
Run Analysis → Ask Questions in Plain English →
Generate Executive Report
```

**Business Impact:**  
Turn messy tabular business data into analytics, insights, chatbot answers, and PDF reports with **zero manual preprocessing effort.**

---

## Tech Stack Summary

| Layer               | Tools                                      | Why This Choice                                                                   |
| ------------------- | ------------------------------------------ | --------------------------------------------------------------------------------- |
| **Backend API**     | Python, Flask, Flask-CORS                  | Modular API development, seamless integration with analytics/ML services          |
| **Data Processing** | pandas, NumPy, scikit-learn                | Best-in-class for tabular preprocessing, aggregation, and numeric analysis        |
| **ML Inference**    | scikit-learn, joblib                       | Lightweight and production-ready for classical ML (churn, forecast, segmentation) |
| **NLP/Chat**        | Team2 NLP modules + optional Gemini        | Deterministic pipeline with LLM fallback only for weak-confidence questions       |
| **Reporting**       | WeasyPrint + ReportLab fallback            | High-quality HTML-to-PDF with reliable fallback for environment edge cases        |
| **Frontend UI**     | Vanilla JavaScript SPA, HTML/CSS, Chart.js | Lightweight, modular, no framework overhead; responsive dashboard/chart rendering |
| **Data Storage**    | JSON files + in-memory runtime stores      | Simple, practical, and suitable for internship scope and rapid prototyping        |

---

## User Workflow

### High-Level Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    NEXUS AI ANALYTICS PLATFORM                      │
└─────────────────────────────────────────────────────────────────────┘

1. AUTHENTICATION
   └─→ Signup/Login → Secure session established

2. DATA INGESTION
   └─→ Upload CSV/XLSX/JSON → Read & Validate → Data Sanitization
       └─→ Auto Schema Mapping (candidate columns identified)
       └─→ Quality Checks (parse rates, missingness, duplicates)
       └─→ Capability Matrix (determines which modules can run)

3. ANALYSIS
   └─→ Core KPIs (Revenue, AOV, Customers, Repeat Rate)
   └─→ Dashboard Summaries (trends, categories, segments)
   └─→ Advanced Modules (12 optional: cohort, churn, forecast, CLV, etc.)
   └─→ Team4 Visualization Adapter (generates chart payloads)

4. INTERACTION
   └─→ Chat Interface → Team2 NLP Pipeline
       ├─ Intent Classification
       ├─ Entity Extraction
       ├─ Query Construction
       └─ Analytics Engine Execution + Response Generation

5. REPORTING
   └─→ Compile Analysis + Chat Context
   └─→ Generate Markdown/HTML
   └─→ Export PDF (WeasyPrint first, ReportLab fallback)
   └─→ User Downloads Report
```

---

## Architecture Overview

### System Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND TIER                            │
│  Vanilla JS SPA | Views (Auth/Upload/Dashboard/Advanced/Chat)   │
│  Services (Auth/Data/Analytics/Report) | Core (Router/State)    │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP/JSON
┌────────────────────────▼────────────────────────────────────────┐
│                      BACKEND TIER (Flask)                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ API Routes Layer (analysis_routes.py, auth_routes.py)   │   │
│  │  - /auth/* (signup, login, logout)                       │   │
│  │  - /analysis/* (upload, analyze, dashboard, chat, etc.)  │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Services Layer                                            │   │
│  │  - data_processor.py (schema mapping, cleaning, quality) │   │
│  │  - real_analytics_service.py (KPI, advanced modules)     │   │
│  │  - unified_nlp_analytics.py (Team2→Team3 pipeline)       │   │
│  │  - team4_visualization_adapter.py (chart generation)     │   │
│  │  - report_generator.py (PDF/HTML compilation)            │   │
│  │  - auth_service.py (user management)                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Data & Models                                             │   │
│  │  - forecast_model.pkl, churn_model.pkl, scaler.pkl       │   │
│  │  - column_mapper_model (schema mapping ML)                │   │
│  │  - Uploaded datasets (ephemeral, auto-cleanup @ 48h)      │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────┬───────────────┬───────────────┬────────────────────┘
             │               │               │
   ┌─────────▼────┐ ┌───────▼──────┐ ┌─────▼──────────┐
   │   Team2 NLP  │ │ Team3         │ │ Team4          │
   │   Pipeline   │ │ Analytics     │ │ Visualization  │
   │              │ │ Engine        │ │ Engine         │
   └──────────────┘ └───────────────┘ └────────────────┘
```

---

## Module Definitions

### 12 Advanced Analytics Modules (with Proper Definitions)

These modules are **capability-gated**: a module returns output only if required columns exist in the dataset.

| #   | Module                            | Definition                                                                                                                                                                                                                               | Required Columns                         | Output                                                                        |
| --- | --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- | ----------------------------------------------------------------------------- |
| 1   | **Cohort Analysis**               | Groups customers by acquisition month (cohort), then tracks their retention rate, revenue, and revenue-per-customer across subsequent months. Reveals acquisition quality and customer lifecycle patterns.                               | Date, Customer ID, Amount                | Cohort matrix (cohorts × months), retention rates, revenue per cohort         |
| 2   | **Geographic Analysis**           | Aggregates sales by region/location; computes regional revenue, market share, customer concentration, growth score, and performance tier (Top/High/Medium/Low). Identifies geographic strengths and expansion opportunities.             | Location/Region/State, Amount            | Regional summary, revenue ranking, market share %, growth score               |
| 3   | **Time-Series Analysis**          | Decomposes date-based revenue into three components: **Trend** (overall direction), **Seasonal** (recurring patterns), **Residual** (noise). Uses rolling average and seasonal pattern estimation. Reveals underlying business dynamics. | Date, Amount                             | Trend line, seasonal pattern (weekly/monthly), decomposed chart               |
| 4   | **Churn Prediction**              | RFM-based risk scoring (Recency: days since last purchase, Frequency: purchase count, Monetary: lifetime value). Assigns each customer a 0–100 risk score and labels: Critical/High/Medium/Low/Minimal.                                  | Date, Customer ID, Amount                | Risk scores per customer, churn distribution, high-risk customer list         |
| 5   | **Sales Forecast**                | Exponential smoothing with trend component projects future daily/weekly/monthly sales. Includes 95% confidence bounds to show forecast uncertainty.                                                                                      | Date, Amount                             | Forecast line, upper/lower bounds, MAPE accuracy metric                       |
| 6   | **Product Affinity**              | Market-basket association analysis: finds products frequently bought together. Reports Support (% of baskets), Confidence (likelihood of B given A), and Lift (co-occurrence boost).                                                     | Product, Amount, Date                    | Top product pairs, support/confidence/lift scores, cross-sell recommendations |
| 7   | **CLV (Customer Lifetime Value)** | Sums total lifetime revenue per customer. Segments customers into tiers (High/Medium/Low). Reports top customers, concentration (% of revenue from top 20%), and value distribution.                                                     | Customer ID, Amount                      | CLV per customer, tier distribution, top customers list, concentration %      |
| 8   | **Repeat Purchase Analysis**      | Measures repeat-buy behavior: repeat-rate (% of customers with 2+ purchases), cohorts by frequency (1x, 2x, 3–5x, 5+), average days between repeats. Indicates customer loyalty.                                                         | Date, Customer ID, Amount                | Repeat rate %, frequency distribution, average repeat cycle days              |
| 9   | **Health Score**                  | Weighted RFM health index (0–100): Recency 30%, Frequency 30%, Monetary 40%. Labels customers: Excellent/Good/Fair/Poor. Actionable for retention campaigns.                                                                             | Date, Customer ID, Amount                | Health score per customer, segment distribution, at-risk customer list        |
| 10  | **Anomaly Detection**             | Z-score–based outlier detection on transaction amounts. Flags unusual spikes/drops (sensitivity configurable). Reports anomaly rate and flagged records for fraud/error investigation.                                                   | Amount                                   | Anomaly score per transaction, anomaly rate %, flagged records                |
| 11  | **Product Performance**           | Ranks products by total sales, average order value, frequency, growth score, and assigns performance tier: Star (high sales, high growth), Workhorse (high sales, low growth), Premium (low sales, high value), Standard (rest).         | Product, Amount                          | Product ranking, tier assignment, growth trend per product                    |
| 12  | **Promotional Impact**            | Compares promotional vs non-promotional transactions to estimate lift (% revenue increase), promotional revenue share, effectiveness rating, and recommended strategy.                                                                   | Date, Amount, Is_Promo (or inferred tag) | Lift %, revenue share %, effectiveness rating, strategy recommendation        |

**Note:** Each module is computed on-demand via API endpoint; results are cached with dataset context for chat Q&A.

---

## Complete File Inventory

### Team1 Module (Data Engineering Foundation)

**Purpose:** Build, clean, and engineer base dataset; generate baseline EDA.

| File                     | Location                       | Function                                                           |
| ------------------------ | ------------------------------ | ------------------------------------------------------------------ |
| `data_cleaning.py`       | `Team1_module/scripts/`        | Removes duplicates, handles missing values, standardizes formats   |
| `data_merging.py`        | `Team1_module/scripts/`        | Joins multiple data sources (e.g., transactions + customer master) |
| `feature_engineering.py` | `Team1_module/scripts/`        | Derives features (RFM, age segments, revenue bins, cohorts)        |
| `eda_analysis.py`        | `Team1_module/scripts/`        | Exploratory analysis, summary stats, correlation, distributions    |
| `data_dictionary.py`     | `Team1_module/scripts/`        | Documents column definitions and business meanings                 |
| `run_pipeline.py`        | `Team1_module/scripts/`        | Orchestrates full pipeline: cleaning → merging → engineering → EDA |
| `master_dataset.csv`     | `Team1_module/data/processed/` | Output: cleaned, merged, engineered dataset for analytics use      |

**Integration:** Team1 dataset is indirectly used by Team3 analytics_engine via `analytics_engine/utils/data_loader.py` for reference/baseline analysis.

---

### Team2 Module (NLP Layer)

**Purpose:** Convert user questions into structured analytics queries; generate human-readable responses.

| File                    | Location               | Key Function                                                                                                                                                                                   |
| ----------------------- | ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `intent_classifier.py`  | `Team2_module/`        | Classifies user query intent (sales_query, ranking_query, comparison_query, forecast_query, hr_query). Uses TF-IDF + LogisticRegression/RandomForest. Output: intent class + confidence score. |
| `entity_extractor.py`   | `Team2_module/`        | Identifies business entities from query (e.g., "product X", "date range Y"). Uses rule-based + regex patterns. Output: entity_type + extracted_value.                                          |
| `query_builder.py`      | `Team2_module/`        | Constructs structured analytics query JSON (filter, group_by, rank, date_range). Input: intent + entities. Output: {query_type, filters, grouping, ranking}.                                   |
| `response_generator.py` | `Team2_module/`        | Formats analytics results into natural English prose. Input: query_result + insight_payload. Output: "Your top product is X, generating $Y revenue."                                           |
| `intent_model.pkl`      | `Team2_module/models/` | Trained intent classifier model (serialized).                                                                                                                                                  |
| `vectorizer.pkl`        | `Team2_module/models/` | TF-IDF vectorizer for query tokenization.                                                                                                                                                      |
| `training_data.json`    | `Team2_module/`        | Sample training data: {query_text, intent_label, entities}.                                                                                                                                    |
| `test_interactive.py`   | `Team2_module/`        | Manual test script for NLP pipeline debugging.                                                                                                                                                 |

**Integration:** Imported by `Team5_module/backend/services/unified_nlp_analytics.py`; called during `/api/analysis/chat/<file_id>` requests.

---

### Team3 Module (Analytics Engine)

**Purpose:** Execute structured analytics queries and generate insights on datasets.

**Core Directories & Files:**

#### Core Orchestration

| File                 | Location                 | Function                                                                                            |
| -------------------- | ------------------------ | --------------------------------------------------------------------------------------------------- |
| `engine.py`          | `analytics_engine/core/` | Main query processor. Validates input, routes to module analyzer, returns result + insight payload. |
| `query_validator.py` | `analytics_engine/core/` | Validates query structure and required fields before execution.                                     |

#### Processors (Query Execution)

| File                  | Location                       | Function                                            |
| --------------------- | ------------------------------ | --------------------------------------------------- |
| `filter_processor.py` | `analytics_engine/processors/` | Filters rows based on WHERE-like conditions.        |
| `group_processor.py`  | `analytics_engine/processors/` | Groups data and aggregates (SUM, AVG, COUNT, etc.). |
| `rank_processor.py`   | `analytics_engine/processors/` | Ranks groups by metric; retrieves top N.            |

#### Analytics Modules (12 Analyzers)

| Directory      | Files                                           | Function                                                                       |
| -------------- | ----------------------------------------------- | ------------------------------------------------------------------------------ |
| `cohort/`      | `cohort_analyzer.py`                            | CohortAnalyzer class with analyze() method; outputs cohort matrix.             |
| `churn/`       | `churn_analyzer.py`                             | ChurnAnalyzer with predict() method; outputs risk scores.                      |
| `forecasting/` | `forecast_engine.py`                            | ForecastAnalyzer with predict() method; outputs future sales + bounds.         |
| `geographic/`  | `geographic_analyzer.py`                        | GeographicAnalyzer with analyze() method; outputs regional metrics.            |
| `timeseries/`  | `timeseries_analyzer.py`                        | TimeseriesAnalyzer with analyze() method; outputs trend/seasonal/residual.     |
| `affinity/`    | `affinity_analyzer.py`                          | AffinityAnalyzer with analyze() method; outputs product pairs + metrics.       |
| `kpi/`         | `kpi_calculator.py`                             | KPICalculator with calculate() method; outputs revenue, AOV, repeat rate.      |
| `insights/`    | `insight_generator.py`                          | InsightGenerator with generate_insight() method; converts result to narrative. |
| `utils/`       | `data_loader.py`, `helpers.py`, `validators.py` | Utility functions: load data, error handling, field validation.                |

#### API Wrapper

| File          | Location                | Function                                                                                       |
| ------------- | ----------------------- | ---------------------------------------------------------------------------------------------- |
| `api/main.py` | `analytics_engine/api/` | Optional FastAPI wrapper. Exposes analytics_engine as standalone HTTP service (used by Team4). |

**Integration:** Imported directly by `Team5_module/backend/services/unified_nlp_analytics.py` (Team2→Team3 bridge) and indirectly called by Team4 via Team5 adapter.

---

### Team4 Module (Visualization Engine)

**Purpose:** Generate narrative insights and chart visualizations from datasets.

| File            | Location                            | Function                                                                                     |
| --------------- | ----------------------------------- | -------------------------------------------------------------------------------------------- |
| `dashboard.py`  | `Team4_module/visualization/`       | Streamlit app initialization; page structure (Upload, Dashboard, Insights, Chat tabs).       |
| `charts.py`     | `Team4_module/visualization/`       | Chart generation functions: line charts, bar charts, pie charts using Plotly.                |
| `insights.py`   | `Team4_module/visualization/`       | Generates narrative text insights (e.g., "Revenue grew 15% YoY").                            |
| `config.py`     | `Team4_module/visualization/`       | Configuration for theme, chart defaults, data schema mapping.                                |
| `nlp_bridge.py` | `Team4_module/visualization/`       | Loads Team2 NLP models, calls analytics API (/api/analysis/chat), generates Plotly response. |
| `utils/`        | `Team4_module/visualization/utils/` | Helper functions for data transformation, validation.                                        |

**Integration:** Called by `Team5_module/backend/services/team4_visualization_adapter.py`; payload embedded in `/api/analysis/dashboard` and `/api/analysis/team4-visualization` responses.

---

### Team5 Module Backend

#### Application Bootstrap

| File        | Location                | Function                                                                                                     |
| ----------- | ----------------------- | ------------------------------------------------------------------------------------------------------------ |
| `app.py`    | `Team5_module/backend/` | Flask app factory pattern. Initializes CORS, error handlers, blueprint registration, service initialization. |
| `config.py` | `Team5_module/backend/` | Configuration: database paths, upload/artifact directories, model paths, feature flags.                      |

#### API Routes

| File                     | Location                    | Endpoints                                                                                                                                                                                                                                                                                           |
| ------------------------ | --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `api/auth_routes.py`     | `Team5_module/backend/api/` | `/api/auth/signup`, `/api/auth/login`, `/api/auth/logout`, `/api/auth/profile`                                                                                                                                                                                                                      |
| `api/analysis_routes.py` | `Team5_module/backend/api/` | `/api/analysis/upload`, `/api/analysis/preview`, `/api/analysis/remap`, `/api/analysis/analyze`, `/api/analysis/dashboard`, `/api/analysis/chat`, `/api/analysis/insights`, `/api/analysis/team4-visualization`, `/api/analysis/report`, `/api/analysis/{module_name}/{file_id}` (advanced modules) |

#### Services (Business Logic)

| File                                      | Location                         | Key Functions                                                                                                                                                                  |
| ----------------------------------------- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `services/data_processor.py`              | `Team5_module/backend/services/` | `read_file()`, `sanitize_data()`, `auto_map_columns()`, `quality_checks()`, `generate_capability_matrix()`                                                                     |
| `services/real_analytics_service.py`      | `Team5_module/backend/services/` | `compute_kpis()`, `analyze_customer_cohorts()`, `analyze_geography()`, `analyze_timeseries()`, `predict_churn()`, `analyze_forecast()`, ... (all 12 advanced module analyzers) |
| `services/unified_nlp_analytics.py`       | `Team5_module/backend/services/` | `process_nlp_query()` - Team2 intent/entity → Team3 engine → response.                                                                                                         |
| `services/team4_visualization_adapter.py` | `Team5_module/backend/services/` | `map_to_team4_schema()`, `generate_team4_visualization()` - calls Team4 functions.                                                                                             |
| `services/report_generator.py`            | `Team5_module/backend/services/` | `generate_markdown()`, `generate_html()`, `export_pdf()` (WeasyPrint first, ReportLab fallback).                                                                               |
| `services/auth_service.py`                | `Team5_module/backend/services/` | `signup()`, `login()`, `verify_token()`, `get_user()`.                                                                                                                         |
| `services/chatbot_service.py`             | `Team5_module/backend/services/` | Legacy/stub; unified NLP now in `unified_nlp_analytics.py`.                                                                                                                    |

#### Models (Serialized ML Artifacts)

| File                      | Location               | Purpose                                                    |
| ------------------------- | ---------------------- | ---------------------------------------------------------- |
| `forecast_model.pkl`      | `Team5_module/models/` | Trained exponential smoothing model for sales forecasting. |
| `churn_model.pkl`         | `Team5_module/models/` | Trained RFM-based churn risk model.                        |
| `segmentation_model.pkl`  | `Team5_module/models/` | Trained customer segmentation model (optional).            |
| `column_mapper_model.pkl` | `Team5_module/models/` | ML-based schema mapping model.                             |
| `scaler.pkl`              | `Team5_module/models/` | Fitted scaler for feature normalization.                   |

#### Utilities & Middleware

| File                            | Location                           | Function                                          |
| ------------------------------- | ---------------------------------- | ------------------------------------------------- |
| `utils/auth_utils.py`           | `Team5_module/backend/utils/`      | Token generation, verification, password hashing. |
| `utils/file_utils.py`           | `Team5_module/backend/utils/`      | File path management, cleanup, validation.        |
| `middleware/cors_middleware.py` | `Team5_module/backend/middleware/` | CORS header configuration.                        |
| `middleware/error_handler.py`   | `Team5_module/backend/middleware/` | Global error handling, exception formatting.      |

#### Database & Storage

| Directory    | Purpose                                                                             |
| ------------ | ----------------------------------------------------------------------------------- |
| `uploads/`   | Ephemeral storage for uploaded CSV/Excel files; auto-cleaned after 48h.             |
| `artifacts/` | Temporary processed data, report outputs (JSON, HTML, PDF); auto-cleaned after 48h. |
| `users/`     | User data (optional JSON storage) or external DB if configured.                     |

---

### Team5 Module Frontend

**Framework:** Vanilla JavaScript SPA (Single Page Application); no build tool required.

#### Views (Page Components)

| File               | Location                          | Route        | Function                                                         |
| ------------------ | --------------------------------- | ------------ | ---------------------------------------------------------------- |
| `AuthView.js`      | `Team5_module/frontend/js/views/` | `/auth`      | Signup/login forms, session management.                          |
| `UploadView.js`    | `Team5_module/frontend/js/views/` | `/upload`    | File upload, preview, column mapping UI.                         |
| `DashboardView.js` | `Team5_module/frontend/js/views/` | `/dashboard` | KPI cards, trends chart, segment summary, module loader buttons. |
| `AdvancedView.js`  | `Team5_module/frontend/js/views/` | `/advanced`  | Displays results from 12 advanced modules in card/table format.  |
| `ChatView.js`      | `Team5_module/frontend/js/views/` | `/chat`      | Chat interface, message history, query input, response display.  |
| `ReportView.js`    | `Team5_module/frontend/js/views/` | `/reports`   | Report history, preview, download/PDF export.                    |

#### Services (API Communication & Business Logic)

| File                  | Location                             | Function                                                                                                  |
| --------------------- | ------------------------------------ | --------------------------------------------------------------------------------------------------------- |
| `AuthService.js`      | `Team5_module/frontend/js/services/` | `signup()`, `login()`, `logout()`, `isAuthenticated()`, `getProfile()`.                                   |
| `DataService.js`      | `Team5_module/frontend/js/services/` | `uploadFile()`, `previewUpload()`, `getMappingSuggestions()`, `submitMapping()`.                          |
| `AnalyticsService.js` | `Team5_module/frontend/js/services/` | `runAnalysis()`, `getDashboard()`, `getModuleResult()`, `getAllModuleResults()`, `getCapabilityMatrix()`. |
| `ReportService.js`    | `Team5_module/frontend/js/services/` | `generateReport()`, `getReportHistory()`, `downloadPDF()`.                                                |
| `ChatService.js`      | `Team5_module/frontend/js/services/` | `sendQuery()`, `getChatHistory()`.                                                                        |

#### Core Framework

| File                   | Location                         | Function                                                                      |
| ---------------------- | -------------------------------- | ----------------------------------------------------------------------------- |
| `Router.js`            | `Team5_module/frontend/js/core/` | Client-side routing: maps URL hash (#/dashboard) to view component.           |
| `StateManager.js`      | `Team5_module/frontend/js/core/` | Global state store: current user, active dataset, analysis results, UI flags. |
| `ApiClient.js`         | `Team5_module/frontend/js/core/` | Base HTTP client: handles requests, auth headers, error responses.            |
| `AntiGravityEngine.js` | `Team5_module/frontend/js/core/` | Singleton event bus for inter-component communication.                        |

#### Components (Reusable UI Elements)

| File           | Location                               | Function                                      |
| -------------- | -------------------------------------- | --------------------------------------------- |
| `Toast.js`     | `Team5_module/frontend/js/components/` | Notification popup (success, error, warning). |
| `Sidebar.js`   | `Team5_module/frontend/js/components/` | Navigation menu, user info, logout button.    |
| `Modal.js`     | `Team5_module/frontend/js/components/` | Reusable modal dialog.                        |
| `DataTable.js` | `Team5_module/frontend/js/components/` | Sortable, paginated table display.            |

#### Application Bootstrap

| File         | Location                    | Function                                                                |
| ------------ | --------------------------- | ----------------------------------------------------------------------- |
| `app.js`     | `Team5_module/frontend/js/` | Entry point: initializes Router, StateManager, loads views, starts app. |
| `index.html` | `Team5_module/frontend/`    | HTML skeleton; mounts app.js.                                           |

#### Styling

| File         | Location                     | Scope                                         |
| ------------ | ---------------------------- | --------------------------------------------- |
| `styles.css` | `Team5_module/frontend/css/` | Global theme, layout, responsive breakpoints. |
| `theme.css`  | `Team5_module/frontend/css/` | Color scheme, typography, component styles.   |

---

### Analytics Engine Detailed Structure

```
analytics_engine/
├── core/
│   ├── engine.py              # Query orchestrator (process_query, generate_insight)
│   ├── query_validator.py     # Input validation
│   └── constants.py           # Canonical module names, field mappings
├── processors/
│   ├── filter_processor.py    # WHERE-like filtering
│   ├── group_processor.py     # GROUP BY aggregation
│   ├── rank_processor.py      # ORDER BY + LIMIT ranking
│   └── join_processor.py      # Multi-table joins (optional)
├── cohort/
│   └── cohort_analyzer.py     # CohortAnalyzer.analyze() → cohort retention matrix
├── churn/
│   └── churn_analyzer.py      # ChurnAnalyzer.predict() → risk scores
├── forecasting/
│   └── forecast_engine.py     # ForecastAnalyzer.predict() → future sales + bounds
├── geographic/
│   └── geographic_analyzer.py # GeographicAnalyzer.analyze() → regional metrics
├── timeseries/
│   └── timeseries_analyzer.py # TimeseriesAnalyzer.analyze() → trend/seasonal/residual
├── affinity/
│   └── affinity_analyzer.py   # AffinityAnalyzer.analyze() → product pairs + support/confidence/lift
├── kpi/
│   └── kpi_calculator.py      # KPICalculator.calculate() → revenue, AOV, repeat_rate
├── insights/
│   └── insight_generator.py   # InsightGenerator.generate_insight() → narrative text
├── utils/
│   ├── data_loader.py         # Load CSV/Parquet into DataFrame
│   ├── helpers.py             # Common math functions
│   ├── validators.py          # Field existence/type checks
│   └── constants.py           # Shared constants
├── models/ (optional)
│   └── feature_metadata.json  # Feature definitions for advanced modules
└── api/
    └── main.py                # FastAPI wrapper (optional; allows analytics_engine as standalone service)
```

---

## Team Integration Details

### Team1 → Team5 Integration

**Data Foundation:**

- Team1 builds base dataset (`Team1_module/data/processed/master_dataset.csv`) with cleaning, merging, feature engineering.
- Team5 uploads user datasets independently; optionally uses Team1 dataset as reference for baseline comparisons.
- **Integration Path:** `analytics_engine/utils/data_loader.py` can load both Team1 processed data and user uploads.

### Team2 → Team3 → Team5 Integration

**NLP Chat Pipeline:**

```
User asks question in chat → Team2 Intent Classifier (identify intent)
  ↓
Team2 Entity Extractor (extract entities: product, date range, etc.)
  ↓
Team2 Query Builder (construct structured query JSON)
  ↓
Team3 Analytics Engine (execute query on dataset, return result + insight)
  ↓
Team2 Response Generator (format result into natural English)
  ↓
User receives answer in chat interface
```

**File:** `Team5_module/backend/services/unified_nlp_analytics.py`  
**Endpoint:** `/api/analysis/chat/<file_id>`

**Fallback Logic:**

1. **Deterministic Priority:** Always try to answer from Team2+Team3 first.
2. **Confidence Check:** If intent/entity extraction confidence < threshold, escalate.
3. **Gemini Fallback (Optional):** For custom/complex questions outside deterministic scope, call Gemini API.
4. **Graceful Degrade:** If both fail, return "I couldn't understand. Please try rephrasing."

### Team4 → Team5 Integration

**Visualization Pipeline:**

```
User dataset uploaded and analyzed → Team5 data_processor generates schema
  ↓
Team5 team4_visualization_adapter maps schema to Team4 format
  ↓
Team4 charts.py generates Plotly chart JSON (line, bar, pie, etc.)
  ↓
Team4 insights.py generates narrative insight text
  ↓
Team5 embeds payload in /api/analysis/dashboard response
  ↓
Team5 report_generator.py includes Team4 charts in PDF report
  ↓
User sees charts in dashboard and report
```

**Files:**

- `Team5_module/backend/services/team4_visualization_adapter.py` (schema mapping)
- `Team5_module/backend/services/report_generator.py` (chart embedding)
- `Team4_module/visualization/charts.py`, `Team4_module/visualization/insights.py` (chart generation)

**Endpoints:**

- `/api/analysis/dashboard/<file_id>` (includes Team4 payload)
- `/api/analysis/team4-visualization/<file_id>` (direct Team4 output)

### Team3 Analytics Engine Integration

**Canonical Modules (12):**
Each module is a Python class with `analyze()` or `predict()` method:

```
cohort-analysis        → CohortAnalyzer.analyze()
geographic-analysis    → GeographicAnalyzer.analyze()
timeseries-analysis    → TimeseriesAnalyzer.analyze()
churn-prediction       → ChurnAnalyzer.predict()
sales-forecast         → ForecastAnalyzer.predict()
product-affinity       → AffinityAnalyzer.analyze()
clv                    → CLVAnalyzer.analyze()
repeat-purchase        → RepeatPurchaseAnalyzer.analyze()
health-score           → HealthScoreAnalyzer.analyze()
anomalies              → AnomalyDetector.analyze()
product-performance    → ProductPerformanceAnalyzer.analyze()
promotional-impact     → PromotionalImpactAnalyzer.analyze()
```

**Integration in Team5:**

- `Team5_module/backend/api/analysis_routes.py` has endpoint for each module: `/api/analysis/{module_name}/{file_id}`
- Route calls `real_analytics_service.py` function → calls corresponding analytics_engine analyzer → returns structured result.
- Results cached in memory with dataset context for chat Q&A.

---

## Backend API Reference

### Authentication Endpoints

```
POST /api/auth/signup
Body: { "email": "user@example.com", "password": "pass123" }
Response: { "user_id": "...", "token": "..." }

POST /api/auth/login
Body: { "email": "user@example.com", "password": "pass123" }
Response: { "user_id": "...", "token": "..." }

POST /api/auth/logout
Headers: { "Authorization": "Bearer <token>" }
Response: { "status": "logged_out" }

GET /api/auth/profile
Headers: { "Authorization": "Bearer <token>" }
Response: { "user_id": "...", "email": "..." }
```

### Analysis Endpoints (Data Upload & Processing)

```
POST /api/analysis/upload
Body: FormData { "file": <csv/xlsx/json/parquet> }
Response: { "file_id": "...", "row_count": 1000, "column_names": [...] }

POST /api/analysis/preview/<file_id>
Response: { "columns": [...], "sample_rows": [...], "quality_report": {...} }

POST /api/analysis/remap/<file_id>
Body: { "mapping": { "old_col_name": "canonical_field" } }
Response: { "status": "remapped", "new_columns": [...] }

POST /api/analysis/analyze/<file_id>
Response: {
  "kpis": { "revenue": ..., "aov": ... },
  "capability_matrix": { "cohort": true, "churn": true, ... },
  "trends": [...],
  "segments": [...]
}
```

### Dashboard & Visualization

```
GET /api/analysis/dashboard/<file_id>
Response: {
  "kpis": {...},
  "charts": [...],
  "team4_payload": {...}  # Includes Team4 visualization data
}

GET /api/analysis/team4-visualization/<file_id>
Response: {
  "charts": [...],
  "insights": [...]
}
```

### Chat Endpoint

```
POST /api/analysis/chat/<file_id>
Body: { "query": "What are my top 3 products?" }
Response: {
  "answer": "Your top 3 products are...",
  "supporting_data": {...},
  "confidence": 0.95
}
```

### Advanced Module Endpoints (Capability-Gated)

```
GET /api/analysis/cohort-analysis/<file_id>
GET /api/analysis/geographic-analysis/<file_id>
GET /api/analysis/timeseries-analysis/<file_id>
GET /api/analysis/churn-prediction/<file_id>
GET /api/analysis/sales-forecast/<file_id>
GET /api/analysis/product-affinity/<file_id>
GET /api/analysis/clv/<file_id>
GET /api/analysis/repeat-purchase/<file_id>
GET /api/analysis/health-score/<file_id>
GET /api/analysis/anomalies/<file_id>
GET /api/analysis/product-performance/<file_id>
GET /api/analysis/promotional-impact/<file_id>

Response: { "status": "success", "data": {...}, "metadata": {...} }
```

### Report Generation

```
POST /api/analysis/report/<file_id>
Body: { "include_modules": ["cohort", "churn", "forecast"] }
Response: { "report_id": "...", "preview_html": "...", "status": "ready" }

GET /api/analysis/report/<file_id>/download
Response: PDF binary file
```

### System Health

```
GET /api/health
Response: { "status": "healthy", "services": {...} }
```

---

## End-to-End Data Flow

### User Journey: Upload → Analysis → Chat → Report

```
1. USER LOGS IN
   ↓ Frontend: AuthView.js calls AuthService.login()
   ↓ Backend: /api/auth/login validates credentials, returns JWT token
   ↓ Frontend: StateManager stores token, user redirected to /upload

2. USER UPLOADS FILE
   ↓ Frontend: UploadView.js calls DataService.uploadFile(csv)
   ↓ Backend: /api/analysis/upload receives file, stores in uploads/ dir
   ↓ Backend: data_processor.py reads file, sanitizes data
   ↓ Response: file_id, row_count, column_names, quality_report
   ↓ Frontend: Displays preview and mapping suggestions

3. USER CONFIRMS MAPPING
   ↓ Frontend: UploadView.js calls DataService.submitMapping()
   ↓ Backend: /api/analysis/remap/<file_id> applies column mapping
   ↓ Response: mapped column schema
   ↓ Frontend: Redirects to /dashboard

4. SYSTEM RUNS ANALYSIS
   ↓ Frontend: DashboardView.js calls AnalyticsService.runAnalysis()
   ↓ Backend: /api/analysis/analyze/<file_id> orchestrates:
      - real_analytics_service.compute_kpis() → {revenue, AOV, customers, repeat_rate}
      - real_analytics_service.analyze_trends() → trend line
      - real_analytics_service.analyze_segments() → customer segments
      - team4_visualization_adapter.generate_team4_visualization() → chart payloads
      - Capability matrix: which advanced modules can run?
   ↓ Backend: Results cached in memory
   ↓ Response: KPIs, trends, segments, Team4 payload, capability_matrix
   ↓ Frontend: DashboardView.js renders KPI cards, charts, module buttons

5. USER CLICKS ADVANCED MODULE
   ↓ Frontend: DashboardView.js calls AnalyticsService.getModuleResult('cohort')
   ↓ Backend: /api/analysis/cohort-analysis/<file_id>
      - Calls real_analytics_service.analyze_customer_cohorts()
      - Which calls analytics_engine.cohort.CohortAnalyzer.analyze()
      - Returns cohort matrix + insights
   ↓ Response: module result data
   ↓ Frontend: AdvancedView.js renders module-specific UI (table, chart)

6. USER ASKS QUESTION IN CHAT
   ↓ Frontend: ChatView.js calls ChatService.sendQuery('What are my top products?')
   ↓ Backend: /api/analysis/chat/<file_id>
      - unified_nlp_analytics.process_nlp_query():
         a) Team2 intent_classifier.py → intent = "ranking_query"
         b) Team2 entity_extractor.py → entity = "products"
         c) Team2 query_builder.py → query = {type: "rank", group_by: "Product", metric: "sales"}
         d) Team3 analytics_engine.core.engine.process_query() → executes on dataset
         e) analytics_engine.insights.insight_generator.generate_insight() → result
         f) Team2 response_generator.py → "Your top product is X, generating $Y revenue."
   ↓ Optional: If confidence low, escalate to Gemini API
   ↓ Response: answer + supporting_data + confidence
   ↓ Frontend: ChatView.js displays answer and logs message

7. USER GENERATES REPORT
   ↓ Frontend: ReportView.js calls ReportService.generateReport()
   ↓ Backend: /api/analysis/report/<file_id>
      - report_generator.py compiles:
         a) Analysis results (KPIs, trends, segments)
         b) Team4 charts (embedded as images)
         c) Selected advanced module results
         d) Chat Q&A highlights
      - Generates Markdown → HTML → PDF (WeasyPrint first, ReportLab fallback)
      - Stores in artifacts/ dir (auto-cleaned after 48h)
   ↓ Response: report_id, preview_html, download_url
   ↓ Frontend: ReportView.js shows preview, download button

8. USER DOWNLOADS REPORT
   ↓ Frontend: ReportView.js calls ReportService.downloadPDF()
   ↓ Backend: /api/analysis/report/<file_id>/download
      - Serves PDF file as binary response
   ↓ Browser: Saves PDF to user's Downloads folder

9. DATA CLEANUP (Background Worker)
   ↓ Backend: Scheduled job runs every hour
      - Deletes uploads/ files older than 48h
      - Deletes artifacts/ files older than 48h
      - Clears in-memory caches if dataset inactive
```

---

## Interview Q&A Preparation

### A) Project Fundamentals

**Q: What is your project in one line?**  
A: An end-to-end AI analytics platform that automates the entire journey from uploading messy business data to generating insights, answering questions via chat, and exporting executive reports.

**Q: What problem does it solve?**  
A: It eliminates manual data cleaning, column mapping, and report preparation—tasks that normally consume days of analyst effort. Users upload a CSV, the system auto-maps columns, runs analytics, enables chat Q&A, and generates PDF reports.

**Q: Who is the target user?**  
A: Business analysts, managers, and executives who need quick insights from data but may not have technical/coding skills.

**Q: What makes it unique?**  
A: Four design principles set it apart:

1. **Capability-Aware Analytics:** Modules only run when required columns exist; never fails silently.
2. **Auto Schema Mapping:** Intelligent column naming—handles variations like "sales_amount" vs "revenue" vs "total."
3. **Deterministic-First Chat:** Answers grounded in dataset values; LLM only escalated if confidence is weak.
4. **Complete End-to-End Product:** Not just models; includes auth, UI, API, report generation, and PDF export.

**Q: Why build end-to-end instead of just model code?**  
A: Real-world impact requires more than notebooks. Building UI, APIs, and reports shows product thinking and makes the project immediately useful for stakeholders.

### B) Architecture & Tech Stack

**Q: Why Flask instead of FastAPI or Django?**  
A: Flask gave me the right balance: lightweight, quick to build modular APIs, and easy integration with pandas/scikit-learn services. Django would have been overkill; FastAPI would have added complexity I didn't need for this scope.

**Q: How is the system architectured?**  
A: Three tiers:

- **Frontend:** Vanilla JS SPA with client-side routing, state management, and service-based API calls.
- **Backend:** Flask API with clear separation: route handlers → service layer → analytics engine → data layer.
- **Analytics Engine:** Modular Python package with 12 analyzers (cohort, churn, forecast, etc.) that can run standalone or be called from Flask.

**Q: How do the 5 teams integrate?**  
A:

- **Team1 (Data Engineering):** Provides baseline dataset; indirectly used for reference analytics.
- **Team2 (NLP):** Integrated via `unified_nlp_analytics.py`; intent/entity extraction → query construction → response generation.
- **Team3 (Analytics Engine):** Core query processor; 12 analyzers execute structured queries on datasets.
- **Team4 (Visualization):** Generates chart payloads; embedded in dashboard and report outputs via `team4_visualization_adapter.py`.
- **Team5 (My Module):** Orchestration layer; ties all teams together with unified API, frontend UI, and end-to-end flow.

### C) 12 Advanced Modules

**Q: What are the 12 advanced analytics modules?**  
A:

1. **Cohort Analysis** – Track customer retention by acquisition month.
2. **Geographic Analysis** – Analyze regional revenue and growth.
3. **Time-Series Analysis** – Decompose sales into trend, seasonal, residual.
4. **Churn Prediction** – RFM-based risk scoring (0–100).
5. **Sales Forecast** – Exponential smoothing with confidence bounds.
6. **Product Affinity** – Market-basket analysis (support, confidence, lift).
7. **CLV** – Customer lifetime value + tier segmentation.
8. **Repeat Purchase** – Retention rate and purchase frequency cohorts.
9. **Health Score** – Weighted RFM index (0–100) for customer health.
10. **Anomaly Detection** – Z-score outlier flagging.
11. **Product Performance** – Product ranking by sales, AOV, growth.
12. **Promotional Impact** – Lift estimation and promo effectiveness.

**Q: How are these modules capability-gated?**  
A: Each module specifies required columns (e.g., Churn needs Date, Customer ID, Amount). Before running analysis, I compute a capability matrix: if a module's required fields are missing, it's disabled and returns a "not applicable" message instead of failing.

### D) NLP & Chat

**Q: How does the chat feature work?**  
A: Pipeline: User query → Team2 intent classifier (identify intent) → entity extractor (extract entities) → query builder (construct structured query) → Team3 analytics engine (execute on dataset) → insight generator (convert result to insight) → response generator (format as English prose) → send to user.

**Q: Why is deterministic prioritized over LLM?**  
A: Deterministic answers grounded in actual dataset values are more trustworthy for business decisions. LLM (Gemini) is fallback only: if intent/entity confidence is weak or query is outside deterministic scope, we escalate.

**Q: What happens if a question can't be answered?**  
A: Graceful degrade: confidence check fails → optional Gemini escalation → if still fails, return "I couldn't understand your question. Try rephrasing or ask about revenue, products, or customer segments."

### E) Data Flow & Integration

**Q: What happens when a user uploads a file?**  
A: Read file (CSV/Excel/JSON/Parquet) → sanitize (remove noise, handle missing values) → auto-detect column types → suggest canonical schema mapping (e.g., "sales_amount" → "Total Amount") → run quality checks (parse rates, duplicates) → generate capability matrix (which modules can run) → return preview + diagnostics.

**Q: How is schema mapping done?**  
A: Three-step approach: (1) Exact alias matching (e.g., "Amount" or "Revenue" → "Total Amount"), (2) Fuzzy string similarity, (3) ML-based role prediction (model trained on historical mappings). User can accept suggestions or manually remap.

**Q: How are results cached?**  
A: Analysis results (KPIs, module outputs) are cached in memory with the file_id as key. Chat uses this cache to answer follow-up questions without re-computing. Cache expires when file is deleted or after inactivity timeout.

### F) Report Generation

**Q: How is the PDF report generated?**  
A: Compile analysis results → render Markdown → convert to HTML → attempt PDF export with WeasyPrint (high quality, but may fail if native deps missing) → fallback to ReportLab (always works, lower quality) → serve binary to browser.

**Q: What data goes into the report?**  
A: KPIs, dashboard charts, selected advanced module results (user chooses which), chat Q&A highlights, insights narrative, and Team4 chart embeddings.

### G) Challenges & Solutions

**Q: What was the hardest technical challenge?**  
A: **Challenge:** Deterministic NLP for diverse query types without LLM dependency.
**Solution:** Trained Team2 intent/entity models on domain-specific queries, then built query_builder.py to translate entities into structured analytics queries. Added confidence thresholds and optional Gemini escalation for low-confidence cases.

**Q: How did you handle column mapping ambiguity?**  
A: Multi-level approach: (1) Config file with known aliases, (2) fuzzy string matching, (3) ML-based prediction trained on past mappings. Show confidence scores to users; let them override if suggestions are wrong.

**Q: How do you ensure compatibility with varied datasets?**  
A: Fallback-heavy design: safe file parsing (try each format), flexible schema (optional columns), capability gating (disable modules if columns missing), and gradual error messages (never crash; instead, return "this analysis not available for your data").

---

## Demo Run Commands

### Backend Setup & Run

```powershell
cd Team5_module\backend
python -m pip install -r requirements.txt
python app.py
# Backend runs on http://localhost:5000
# Health check: curl http://localhost:5000/api/health
```

### Frontend Setup & Run

```powershell
cd Team5_module\frontend
python -m http.server 3000
# Or: npx http-server -p 3000
# Frontend runs on http://localhost:3000
```

### Test Endpoints (after both are running)

```powershell
# Health check
curl http://localhost:5000/api/health

# Signup
curl -X POST http://localhost:5000/api/auth/signup `
  -H "Content-Type: application/json" `
  -d '{"email":"test@example.com","password":"pass123"}'

# Upload file
$token = "<JWT_TOKEN_FROM_LOGIN>"
curl -X POST http://localhost:5000/api/analysis/upload `
  -H "Authorization: Bearer $token" `
  -F "file=@path/to/data.csv"

# Run analysis
curl http://localhost:5000/api/analysis/analyze/<FILE_ID> `
  -H "Authorization: Bearer $token"
```

---

## Glossary & Key Definitions

| Term                  | Definition                                                                                 |
| --------------------- | ------------------------------------------------------------------------------------------ |
| **Capability Matrix** | Dict showing which advanced modules can run (true/false) based on available columns.       |
| **Cohort**            | Group of customers acquired in the same time period (month/quarter).                       |
| **Churn Risk**        | Probability customer will not purchase again; scored 0–100.                                |
| **CLV**               | Customer Lifetime Value: total revenue generated by a customer over their lifetime.        |
| **RFM**               | Recency (days since last purchase), Frequency (purchase count), Monetary (lifetime value). |
| **Support**           | % of transactions containing both product A and product B (affinity metric).               |
| **Confidence**        | If customer bought A, probability they also bought B (affinity metric).                    |
| **Lift**              | How much more likely co-purchase is vs random chance (affinity metric).                    |
| **Anomaly**           | Transaction flagged as unusual (outlier) via Z-score thresholding.                         |
| **Health Score**      | Weighted RFM index (0–100) indicating customer quality/risk.                               |
| **Forecast**          | Predicted future sales with upper/lower 95% confidence bounds.                             |
| **Trend**             | Overall direction of sales (up/down) over time.                                            |
| **Seasonality**       | Recurring patterns (weekly/monthly/yearly) in sales.                                       |

---

## Project Statistics

- **Lines of Code:** ~5,000+ (Python backend + frontend)
- **API Endpoints:** 20+
- **Advanced Modules:** 12
- **Team Integration Points:** 5
- **Supported File Formats:** 5 (CSV, XLSX, XLS, JSON, Parquet)
- **Frontend Views:** 6
- **Backend Services:** 7
- **ML Models:** 5 (serialized .pkl files)

---

## Next Steps for Development

1. **Scale to Larger Datasets:** Implement async job queues (Celery) for long-running analyses.
2. **Database Integration:** Replace JSON storage with PostgreSQL for multi-tenant data isolation.
3. **Advanced NLP:** Fine-tune LLM integration for better complex-query handling.
4. **Real-Time Collaboration:** WebSocket support for multi-user editing of mapping/analysis.
5. **Mobile App:** React Native version for on-the-go analytics access.

---

**Document Version:** 2.0 (Complete with file paths, definitions, team integration)  
**Last Updated:** 2024  
**Author:** Team5 Module  
**Contact:** For questions on architecture, integration, or specific modules, refer to codebase comments and inline docstrings.
