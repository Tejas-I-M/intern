import { analyticsService as sharedAnalyticsService } from "../services/AnalyticsService.js";
import { reportService as sharedReportService } from "../services/ReportService.js";
import { stateManager as sharedStateManager } from "../core/StateManager.js";
import { toast as sharedToast } from "../components/Toast.js";
import { Sidebar } from "../components/Sidebar.js";

function asObject(value) {
  return value && typeof value === "object" ? value : {};
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function safeText(value, fallback = "") {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function formatDataKeyLabel(key) {
  const source = String(key ?? "").trim();
  if (!source) {
    return "";
  }

  let label = source
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  // Convert numeric band keys like "3 5 purchases" into "3-5 Purchases".
  label = label.replace(/\b(\d+)\s+(\d+)\b/g, "$1-$2");
  label = label.replace(/\b10\s*plus\b/gi, "10+");

  label = label
    .split(" ")
    .map((part) => {
      if (!part) {
        return part;
      }
      if (/\d/.test(part) || part.includes("-") || part.includes("+")) {
        return part;
      }
      return part.charAt(0).toUpperCase() + part.slice(1);
    })
    .join(" ");

  return label
    .replace(/\bId\b/g, "ID")
    .replace(/\bClv\b/g, "CLV");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatCurrency(value) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) {
    return "N/A";
  }
  return amount.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 2 });
}

function formatNumber(value) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return "N/A";
  }
  return parsed.toLocaleString();
}

function firstDefined(...values) {
  for (const value of values) {
    if (value !== undefined && value !== null) {
      return value;
    }
  }
  return null;
}

const MODULE_IGNORED_KEYS = new Set([
  "success",
  "message",
  "status",
  "type",
  "file_id",
  "dataset_name",
  "source",
  "source_columns",
  "mapped_columns",
  "analysis_mode",
  "original_rowCount",
  "fallback_used",
  "columns",
  "nlp_status"
]);
const MODULE_NO_DATA_TEXT = "No data for analysis for this module in the uploaded dataset.";

function extractModulePayload(result) {
  const payload =
    result?.analysis ??
    result?.data ??
    result?.metrics ??
    result?.results ??
    result?.insights ??
    result?.cohorts ??
    result?.anomalies ??
    result?.recommendations ??
    result;

  if (payload === null || payload === undefined) {
    return {};
  }

  return payload;
}

function hasMeaningfulData(value, depth = 0) {
  if (depth > 5 || value === null || value === undefined) {
    return false;
  }

  if (typeof value === "number") {
    return Number.isFinite(value);
  }

  if (typeof value === "boolean") {
    return value;
  }

  if (typeof value === "string") {
    const text = value.trim().toLowerCase();
    if (!text || text === "n/a" || text === "na" || text === "none" || text === "null") {
      return false;
    }

    if (text === "request completed" || text === "request completed." || text === "analysis completed" || text === "analysis completed.") {
      return false;
    }

    return true;
  }

  if (Array.isArray(value)) {
    return value.some((item) => hasMeaningfulData(item, depth + 1));
  }

  if (typeof value === "object") {
    const entries = Object.entries(value).filter(([key]) => !MODULE_IGNORED_KEYS.has(key));
    if (!entries.length) {
      return false;
    }

    return entries.some(([, entryValue]) => hasMeaningfulData(entryValue, depth + 1));
  }

  return false;
}

const ADVANCED_MODULE_LABELS = {
  capabilities: "Capabilities",
  nlpStatus: "NLP Status",
  insights: "Insights",
  recentAnalyses: "Recent Analyses",
  cohort: "Cohort",
  geographic: "Geographic",
  timeseries: "Timeseries",
  churn: "Churn",
  forecast: "Forecast",
  affinity: "Product Affinity",
  clv: "CLV",
  repeatPurchase: "Repeat Purchase",
  healthScore: "Health Score",
  anomalies: "Anomalies",
  productPerformance: "Product Performance",
  promotionalImpact: "Promotional Impact",
  availableFilters: "Available Filters"
};

export class DashboardView {
  constructor(options = {}) {
    this.router = options?.router || null;
    this.analyticsService = options?.analyticsService || sharedAnalyticsService;
    this.reportService = options?.reportService || sharedReportService;
    this.stateManager = options?.stateManager || sharedStateManager;
    this.toast = options?.toast || sharedToast;

    this.host = null;
    this.container = null;
    this.sidebar = null;
    this.unsubscribe = null;

    this.fileId = null;
    this.isBusy = false;
    this.latestData = {
      dashboard: {},
      team4: {},
      capabilities: {},
      insights: {}
    };

    this.advancedBundle = {};
    this.advancedMeta = {
      successCount: 0,
      totalCount: 0,
      failedCount: 0,
      successfulKeys: [],
      failedKeys: []
    };
    this.activeAdvancedKey = "";
    this.isAdvancedLoading = false;

    this.chatMessages = [];
    this.chartInstances = [];

    this.boundClickHandler = this.handleClick.bind(this);
    this.boundSubmitHandler = this.handleSubmit.bind(this);
    this.boundWheelHandler = this.handleScrollableWheel.bind(this);
  }

  mount(root) {
    if (!root) {
      return () => {};
    }

    this.host = root;
    this.host.innerHTML = this.render();
    this.container = this.host.querySelector(".dashboard-view");

    const sidebarHost = this.host.querySelector("[data-sidebar-mount]");
    this.sidebar = new Sidebar({
      router: this.router,
      stateManager: this.stateManager,
      toast: this.toast
    });

    if (sidebarHost) {
      this.sidebar.mount(sidebarHost);
    }

    if (this.container) {
      this.container.addEventListener("click", this.boundClickHandler);
      this.container.addEventListener("submit", this.boundSubmitHandler);
      this.container.addEventListener("wheel", this.boundWheelHandler, { passive: false });
    }

    this.unsubscribe = this.stateManager.subscribe((nextState) => {
      this.syncState(nextState);
    });

    this.syncState(this.stateManager.getState());
    this.tryAutoload();

    return () => this.unmount();
  }

  unmount() {
    if (typeof this.unsubscribe === "function") {
      this.unsubscribe();
      this.unsubscribe = null;
    }

    if (this.container) {
      this.container.removeEventListener("click", this.boundClickHandler);
      this.container.removeEventListener("submit", this.boundSubmitHandler);
      this.container.removeEventListener("wheel", this.boundWheelHandler);
      this.container = null;
    }

    if (this.sidebar) {
      this.sidebar.unmount();
      this.sidebar = null;
    }

    this.destroyCharts();
    this.host = null;
  }

  render() {
    return `
      <section class="dashboard-view dashboard-grid" aria-label="Analytics dashboard">
        <div data-sidebar-mount class="sidebar-slot"></div>

        <article class="dashboard-main glass-card">
          <header class="dashboard-head">
            <h2>Analytics Dashboard</h2>
            <p>Review summary, interactive plots, and key business insights.</p>
          </header>

          <p class="upload-status" data-dashboard-status data-variant="info">
            Upload dataset and run analysis.
          </p>

          <div class="dashboard-actions">
            <button type="button" class="auth-submit" data-run-analysis>Run Analytics</button>
            <button type="button" class="ghost-btn" data-refresh-dashboard>Refresh Dashboard</button>
            <button type="button" class="ghost-btn" data-load-advanced>Load Advanced Modules</button>
            <button type="button" class="ghost-btn" data-go-report>Go to Report</button>
          </div>

          <section class="analysis-progress" data-analysis-progress hidden>
            <div class="analysis-progress-bar">
              <span data-analysis-fill style="width: 0%"></span>
            </div>
            <p data-analysis-label>Preparing analysis...</p>
          </section>

          <section class="dashboard-kpis" data-kpi-grid>
            <article class="kpi-card"><p>Total Revenue</p><strong>--</strong></article>
            <article class="kpi-card"><p>Customers</p><strong>--</strong></article>
            <article class="kpi-card"><p>Orders</p><strong>--</strong></article>
            <article class="kpi-card"><p>Avg Order Value</p><strong>--</strong></article>
          </section>

          <section class="dashboard-sections" data-dashboard-sections>
            <article class="dash-card dash-card-wide">
              <h3>Summary</h3>
              <ul class="summary-list" data-summary-list>
                <li>Run analysis to generate insights.</li>
              </ul>
            </article>

            <article class="dash-card">
              <h3>Monthly Trend</h3>
              <div class="chart-canvas-wrap">
                <canvas data-trend-chart></canvas>
              </div>
            </article>

            <article class="dash-card">
              <h3>Top Products</h3>
              <div class="chart-canvas-wrap">
                <canvas data-product-chart></canvas>
              </div>
            </article>

            <article class="dash-card dash-card-wide">
              <h3>Customer Segments</h3>
              <div class="chart-canvas-wrap chart-canvas-wrap-short">
                <canvas data-segment-chart></canvas>
              </div>
            </article>
          </section>
        </article>

        <aside class="dashboard-chat glass-card" aria-label="Dashboard chat panel">
          <header>
            <h3>Quick Chat</h3>
            <p>Ask questions against analyzed dataset.</p>
          </header>

          <section class="chat-thread dashboard-chat-thread" data-chat-thread>
            <p class="chat-empty">Run analysis and ask your first question.</p>
          </section>

          <form class="chat-form" data-chat-form novalidate>
            <label>
              <span>Question</span>
              <textarea
                rows="3"
                maxlength="1200"
                data-chat-input
                placeholder="Example: Which product line performs best?"
              ></textarea>
            </label>

            <div class="chat-actions">
              <button type="submit" class="auth-submit" data-chat-send>Ask</button>
              <button type="button" class="ghost-btn" data-open-full-chat>Open Full Chat</button>
            </div>
          </form>
        </aside>
      </section>
    `;
  }

  handleClick(event) {
    const runButton = event?.target?.closest?.("[data-run-analysis]");
    if (runButton) {
      this.runPipeline({ forceAnalysis: true });
      return;
    }

    const refreshButton = event?.target?.closest?.("[data-refresh-dashboard]");
    if (refreshButton) {
      this.refreshDashboard();
      return;
    }

    const loadAdvancedButton = event?.target?.closest?.("[data-load-advanced]");
    if (loadAdvancedButton) {
        if (this.router && typeof this.router.navigate === "function") {
          this.router.navigate("/advanced");
        } else {
          this.loadAdvancedModules();
        }
        return;
    }

    const reportButton = event?.target?.closest?.("[data-go-report]");
    if (reportButton && this.router && typeof this.router.navigate === "function") {
      this.router.navigate("/reports");
      return;
    }

    const moduleButton = event?.target?.closest?.("[data-advanced-module]");    
    if (moduleButton) {
      const key = safeText(moduleButton.getAttribute("data-advanced-module"), "");
      if (key) {
        this.selectAdvancedModule(key);
      }
      return;
    }

    const openFullChat = event?.target?.closest?.("[data-open-full-chat]");
    if (openFullChat && this.router && typeof this.router.navigate === "function") {
      this.router.navigate("/chat");
    }
  }

  handleSubmit(event) {
    const form = event?.target?.closest?.("[data-chat-form]");
    if (!form) {
      return;
    }

    event.preventDefault();

    const input = form.querySelector("[data-chat-input]");
    const question = safeText(input?.value, "");
    if (!question) {
      this.toast.show("Please enter a question.", { type: "error" });
      return;
    }

    this.askQuestion(question);
  }

  handleScrollableWheel(event) {
    const target = event?.target;
    if (!target || typeof target.closest !== "function") {
      return;
    }

    const scroller = target.closest(".preview-table-wrap-scroll, .module-preview-advanced, .module-output");
    if (!scroller || !this.container?.contains(scroller)) {
      return;
    }

    const canScrollVertically = scroller.scrollHeight > scroller.clientHeight;
    const canScrollHorizontally = scroller.scrollWidth > scroller.clientWidth;
    if (!canScrollVertically && !canScrollHorizontally) {
      return;
    }

    const deltaY = Number(event.deltaY) || 0;
    const deltaX = Number(event.deltaX) || 0;
    const horizontalDelta = deltaX || (event.shiftKey ? deltaY : 0);
    let consumed = false;

    if (canScrollVertically && deltaY !== 0) {
      const beforeTop = scroller.scrollTop;
      scroller.scrollTop = beforeTop + deltaY;
      consumed = consumed || scroller.scrollTop !== beforeTop;
    }

    if (canScrollHorizontally && horizontalDelta !== 0) {
      const beforeLeft = scroller.scrollLeft;
      scroller.scrollLeft = beforeLeft + horizontalDelta;
      consumed = consumed || scroller.scrollLeft !== beforeLeft;
    }

    if (consumed) {
      event.preventDefault();
    }
  }

  syncState(state) {
    const isAuthenticated = Boolean(state?.auth?.isAuthenticated);
    this.fileId = state?.dataset?.fileId || null;
    const analysisComplete = Boolean(state?.dataset?.analysisComplete);

    if (!isAuthenticated) {
      this.setStatus("Login required before dashboard access.", "error");
      this.setChatEnabled(false);
      return;
    }

    if (!this.fileId) {
      this.setStatus("Upload dataset first.", "error");
      this.setChatEnabled(false);
      return;
    }

    if (!analysisComplete) {
      this.setStatus("Dataset uploaded. Click Run Analytics.", "info");
      this.setChatEnabled(false);
      return;
    }

    this.setStatus("Analysis complete. Dashboard is ready.", "success");
    this.setChatEnabled(true);
  }

  async tryAutoload() {
    const isAuthenticated = Boolean(this.stateManager.get("auth.isAuthenticated", false));
    const fileId = this.stateManager.get("dataset.fileId", null);
    const pendingAnalyze = Boolean(this.stateManager.get("ui.pendingAnalyze", false));
    const analysisComplete = Boolean(this.stateManager.get("dataset.analysisComplete", false));

    if (!isAuthenticated || !fileId || this.isBusy) {
      return;
    }

    if (pendingAnalyze) {
      await this.runPipeline({ forceAnalysis: true });
      return;
    }

    if (analysisComplete) {
      await this.refreshDashboard();
    }
  }

  async runPipeline(options = {}) {
    const forceAnalysis = Boolean(options?.forceAnalysis);
    const fileId = this.fileId || this.stateManager.get("dataset.fileId", null);
    const isAuthenticated = Boolean(this.stateManager.get("auth.isAuthenticated", false));

    if (!isAuthenticated) {
      this.toast.show("Please login first.", { type: "error" });
      return;
    }

    if (!fileId) {
      this.toast.show("Upload a dataset first.", { type: "error" });
      return;
    }

    if (this.isBusy) {
      return;
    }

    this.setBusy(true);
    this.updateProgress(14, "Preparing analysis...");

    try {
      const alreadyComplete = Boolean(this.stateManager.get("dataset.analysisComplete", false));
      if (forceAnalysis || !alreadyComplete) {
        this.updateProgress(38, "Running analytics engine...");
        const analysisResult = await this.analyticsService.analyzeDataset(fileId);
        if (!analysisResult?.success) {
          this.updateProgress(52, "Retrying with async analysis fallback...");
          const asyncFallbackResult = await this.runAsyncAnalysisFallback(fileId);
          if (!asyncFallbackResult?.success) {
            this.setStatus(asyncFallbackResult?.message || analysisResult?.message || "Analysis failed.", "error");
            this.toast.show(asyncFallbackResult?.message || analysisResult?.message || "Analysis failed.", { type: "error" });
            this.updateProgress(0, "Analysis failed.", true);
            return;
          }
        }
      }

      this.updateProgress(72, "Loading dashboard data...");
      const bundle = await this.analyticsService.loadDashboardBundle(fileId);

      this.latestData = {
        dashboard: asObject(bundle?.data?.dashboard),
        team4: asObject(bundle?.data?.team4),
        capabilities: asObject(bundle?.data?.capabilities),
        insights: asObject(bundle?.data?.insights)
      };

      window.dashCacheFileId = fileId;
      window.dashCache = this.latestData;

      this.renderDashboard();
      this.stateManager.updatePath("ui.pendingAnalyze", false);
      this.updateProgress(100, "Analysis complete.");

      if (bundle?.success) {
        this.setStatus("Analysis completed and dashboard loaded.", "success");
      } else {
        this.setStatus(bundle?.message || "Dashboard loaded with partial data.", "error");
      }
    } catch (error) {
      const message = `Dashboard pipeline failed: ${error?.message || "unknown error"}`;
      this.setStatus(message, "error");
      this.toast.show(message, { type: "error" });
      this.updateProgress(0, "Pipeline failed.", true);
    } finally {
      this.setBusy(false);
    }
  }

  async refreshDashboard() {
    const fileId = this.fileId || this.stateManager.get("dataset.fileId", null);
    if (!fileId || this.isBusy) {
      return;
    }

    this.setBusy(true);
    if (!window.dashCache) { this.updateProgress(28, "Loading dashboard data..."); }

    try {
      if (window.dashCache && window.dashCacheFileId === fileId) {
        this.latestData = window.dashCache;
        this.renderDashboard();
        this.setBusy(false);
        return;
      }
      
      const bundle = await this.analyticsService.loadDashboardBundle(fileId);
      this.latestData = {
        dashboard: asObject(bundle?.data?.dashboard),
        team4: asObject(bundle?.data?.team4),
        capabilities: asObject(bundle?.data?.capabilities),
        insights: asObject(bundle?.data?.insights)
      };
      
      window.dashCacheFileId = fileId;
      window.dashCache = this.latestData;

      this.renderDashboard();
      if (!window.dashCache) { this.updateProgress(100, "Dashboard refreshed."); }

      if (bundle?.success) {
        this.setStatus("Dashboard refreshed.", "success");
      } else {
        this.setStatus(bundle?.message || "Dashboard loaded with partial data.", "error");
      }
    } catch (error) {
      this.setStatus(`Refresh failed: ${error?.message || "unknown error"}`, "error");
      this.updateProgress(0, "Refresh failed.", true);
    } finally {
      this.setBusy(false);
    }
  }

  renderDashboard() {
    const dashboard = asObject(this.latestData?.dashboard);
    const team4 = asObject(this.latestData?.team4);
    const insightPayload = asObject(this.latestData?.insights);

    this.renderKpis(asObject(dashboard?.kpis));
    this.renderSummary(dashboard, team4, insightPayload);
    this.renderCharts(dashboard);
    this.renderAdvancedSection();
  }

  renderKpis(kpis) {
    const holder = this.container?.querySelector?.("[data-kpi-grid]");
    if (!holder) {
      return;
    }

    holder.innerHTML = `
      <article class="kpi-card"><p>Total Revenue</p><strong>${formatCurrency(kpis?.total_revenue)}</strong></article>
      <article class="kpi-card"><p>Customers</p><strong>${formatNumber(kpis?.unique_customers)}</strong></article>
      <article class="kpi-card"><p>Orders</p><strong>${formatNumber(kpis?.total_orders)}</strong></article>
      <article class="kpi-card"><p>Avg Order Value</p><strong>${formatCurrency(kpis?.average_order_value)}</strong></article>
    `;
  }

  renderSummary(dashboard, team4, insightPayload = {}) {
    const summaryHolder = this.container?.querySelector?.("[data-summary-list]");
    if (!summaryHolder) {
      return;
    }

    const insights = asArray(team4?.insights).filter(Boolean);
    const nlpInsights = asArray(insightPayload?.insights).filter(Boolean);
    const categories = asArray(dashboard?.top_categories);

    const topCategoryLines = categories.slice(0, 5).map((item, index) => {
      const name = safeText(firstDefined(item?.product_category, item?.category, item?.name), "Category");
      const value = firstDefined(item?.revenue, item?.sales, item?.total, 0);
      return `${index + 1}. ${name}: ${formatCurrency(value)}`;
    });

    const summaryLines = [];
    for (const item of insights.slice(0, 5)) {
      summaryLines.push(item);
    }
    if (!summaryLines.length) {
      for (const item of nlpInsights.slice(0, 5)) {
        summaryLines.push(item);
      }
    }
    if (!summaryLines.length) {
      summaryLines.push("Insights will appear once analysis results are loaded.");
    }

    summaryHolder.innerHTML = `
      <li><strong>Summary</strong></li>
      ${summaryLines.map((line) => `<li>${escapeHtml(line)}</li>`).join("")}
      <li><strong>Top Products</strong></li>
      ${topCategoryLines.length ? topCategoryLines.map((line) => `<li>${escapeHtml(line)}</li>`).join("") : "<li>No category ranking available.</li>"}
    `;
  }

  renderCharts(dashboard) {
    const trendCanvas = this.container?.querySelector?.("[data-trend-chart]");
    const productCanvas = this.container?.querySelector?.("[data-product-chart]");
    const segmentCanvas = this.container?.querySelector?.("[data-segment-chart]");

    if (!trendCanvas || !productCanvas || !segmentCanvas) {
      return;
    }

    this.destroyCharts();

    const chartApi = typeof window !== "undefined" ? window.Chart : null;
    if (!chartApi) {
      const fallback = trendCanvas.parentElement;
      if (fallback) {
        fallback.innerHTML = "<p class=\"table-empty\">Chart library failed to load. Refresh the page.</p>";
      }
      return;
    }

    const trends = asArray(dashboard?.trends).slice(0, 12);
    const trendLabels = trends.map((item) => safeText(firstDefined(item?.period, item?.month, item?.label), "Period"));
    const trendValues = trends.map((item) => Number(firstDefined(item?.revenue, item?.value, item?.sales, 0)) || 0);

    const categories = asArray(dashboard?.top_categories).slice(0, 5);
    const categoryLabels = categories.map((item) => safeText(firstDefined(item?.product_category, item?.category, item?.name), "Category"));
    const categoryValues = categories.map((item) => Number(firstDefined(item?.revenue, item?.sales, item?.total, 0)) || 0);

    const segmentsObj = asObject(dashboard?.segments);
    const segmentEntries = Object.entries(segmentsObj).slice(0, 6);
    const segmentLabels = segmentEntries.map(([label]) => label);
    const segmentValues = segmentEntries.map(([, value]) => {
      if (typeof value === "number") {
        return value;
      }
      return Number(firstDefined(value?.count, value?.value, 0)) || 0;
    });

    const trendInstance = new chartApi(trendCanvas.getContext("2d"), {
      type: "line",
      data: {
        labels: trendLabels,
        datasets: [
          {
            label: "Revenue",
            data: trendValues,
            borderWidth: 2,
            borderColor: "#00d4c6",
            backgroundColor: "rgba(0, 212, 198, 0.16)",
            fill: true,
            tension: 0.35
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#9fb2d0" }, grid: { color: "rgba(255,255,255,0.06)" } },
          y: { ticks: { color: "#9fb2d0" }, grid: { color: "rgba(255,255,255,0.06)" } }
        }
      }
    });

    const categoryInstance = new chartApi(productCanvas.getContext("2d"), {
      type: "bar",
      data: {
        labels: categoryLabels,
        datasets: [
          {
            label: "Sales",
            data: categoryValues,
            backgroundColor: ["#3fc1ff", "#27e6a4", "#ffd166", "#ff7f7f", "#b58cff"],
            borderRadius: 8
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#9fb2d0" }, grid: { display: false } },
          y: { ticks: { color: "#9fb2d0" }, grid: { color: "rgba(255,255,255,0.06)" } }
        }
      }
    });

    const segmentInstance = new chartApi(segmentCanvas.getContext("2d"), {
      type: "doughnut",
      data: {
        labels: segmentLabels,
        datasets: [
          {
            data: segmentValues,
            backgroundColor: ["#00d4c6", "#3fc1ff", "#ffd166", "#ff9f80", "#b58cff", "#9fe870"],
            borderWidth: 1,
            borderColor: "rgba(255,255,255,0.1)"
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: { color: "#b4c2de" }
          }
        }
      }
    });

    this.chartInstances = [trendInstance, categoryInstance, segmentInstance];
  }

  renderAdvancedSection() {
    const summaryEl = this.container?.querySelector?.("[data-advanced-summary]");
    const modulesEl = this.container?.querySelector?.("[data-advanced-modules]");
    if (!summaryEl || !modulesEl) {
      return;
    }

    const total = Number(this.advancedMeta?.totalCount || 0);

    if (!total) {
      summaryEl.textContent = "Load advanced modules to connect upgraded backend endpoints.";
      modulesEl.innerHTML = "";
      this.renderAdvancedOutput();
      return;
    }

    summaryEl.textContent = "Advanced modules loaded. Showing modules with usable data only.";

    // Only include modules that succeeded and contain meaningful dataset-driven output.
    const keys = Object.keys(this.advancedBundle).filter(key => {
      const res = this.advancedBundle[key];
      if (key === "nlpStatus" || key === "capabilities" || key === "recentAnalyses") return false;
      if (!res?.success) return false;
      const dataPayload = extractModulePayload(res);
      return hasMeaningfulData(dataPayload);
    });

    if (!keys.length) {
      modulesEl.innerHTML = "";
      this.activeAdvancedKey = "";
      this.renderAdvancedOutput();
      return;
    }
    
    // Automatically select the first visible module if none is selected
    if (!this.activeAdvancedKey || !keys.includes(this.activeAdvancedKey)) {
      if (keys.length > 0) {
        this.activeAdvancedKey = keys[0];
      }
    }
    
    modulesEl.innerHTML = keys
      .map((key) => {
        const label = ADVANCED_MODULE_LABELS[key] || key;
        const active = this.activeAdvancedKey === key;
        return `
          <button
            type="button"
            class="quick-pill module-chip ${active ? "is-active" : ""}"
            data-advanced-module="${escapeHtml(key)}"
          >
            ${escapeHtml(label)}
          </button>
        `;
      })
      .join("");

    this.renderAdvancedOutput();
  }

  renderAdvancedOutput() {
    const outputEl = this.container?.querySelector?.("[data-advanced-output]");
    if (!outputEl) {
      return;
    }

    const key = this.activeAdvancedKey;
    if (!key) {
      outputEl.innerHTML = '<p class="table-empty">No advanced module has enough data for this dataset.</p>';
      return;
    }

    const result = this.advancedBundle[key];
    const label = ADVANCED_MODULE_LABELS[key] || key;

    if (!result) {
      outputEl.innerHTML = `
        <div class="module-head module-head-advanced">
          <h4 class="module-title-advanced">${escapeHtml(label)}</h4>
        </div>
        <p class="table-empty">${escapeHtml(MODULE_NO_DATA_TEXT)}</p>
      `;
      return;
    }

    const payload = this.normalizeModulePayload(key, extractModulePayload(result));
    const shouldShowNoData = !result.success || !hasMeaningfulData(payload);

    if (shouldShowNoData) {
      outputEl.innerHTML = `
        <div class="module-head module-head-advanced">
          <h4 class="module-title-advanced">${escapeHtml(label)}</h4>
        </div>
        <div class="glass-card" style="border: 1px solid rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px; background: rgba(255,255,255,0.03); margin-top: 0.45rem;">
          <p class="table-empty" style="margin: 0;">${escapeHtml(MODULE_NO_DATA_TEXT)}</p>
        </div>
      `;
      return;
    }

    const preview = this.buildModulePreview(payload, key);

    outputEl.innerHTML = `
      <div class="module-head module-head-advanced">
        <h4 class="module-title-advanced">${escapeHtml(label)}</h4>
      </div>
      <div class="module-preview glass-card module-preview-advanced">
        ${preview}
      </div>
    `;
  }

  normalizeModulePayload(moduleKey, payload) {
    const normalizedKey = safeText(moduleKey, "").toLowerCase();
    const isTimeseries = normalizedKey === "timeseries" || normalizedKey === "timeseries-analysis" || normalizedKey === "timeseriesanalysis";
    const isInsights = normalizedKey === "insights";

    const normalizeNode = (value) => {
      if (Array.isArray(value)) {
        return value.map((entry) => normalizeNode(entry));
      }

      if (!value || typeof value !== "object") {
        return value;
      }

      const normalizedObject = {};

      for (const [key, raw] of Object.entries(value)) {
        const keyLower = String(key || "").toLowerCase();

        if (isTimeseries && keyLower === "components") {
          continue;
        }

        let nextValue = normalizeNode(raw);

        if (isInsights && (keyLower === "high_risk_customers" || keyLower === "at_risk_customers") && Array.isArray(nextValue)) {
          nextValue = nextValue.slice(0, 5);
        }

        if (!isTimeseries && keyLower === "components") {
          if (Array.isArray(nextValue)) {
            nextValue = nextValue.slice(0, 5);
          } else if (nextValue && typeof nextValue === "object") {
            const compact = {};
            for (const [nestedKey, nestedVal] of Object.entries(nextValue)) {
              compact[nestedKey] = Array.isArray(nestedVal) ? nestedVal.slice(0, 5) : nestedVal;
            }
            nextValue = compact;
          }
        }

        normalizedObject[key] = nextValue;
      }

      return normalizedObject;
    };

    return normalizeNode(payload);
  }

  formatValue(val) {
    if (val === null || val === undefined) return '<span style="color: #9fb2d0;">N/A</span>';
    if (typeof val === "boolean") {
      return val ? '<span style="color: #27e6a4; font-weight: bold;">Yes</span>' : '<span style="color: #ff7f7f; font-weight: bold;">No</span>';
    }
    if (typeof val === "number") {
      if (Number.isInteger(val)) return val.toLocaleString();
      return val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
    if (typeof val === "object") {
      if (Array.isArray(val)) {
        if (val.length === 0) return '<span style="color: #9fb2d0;">Empty</span>';
        if (typeof val[0] === 'object') return this.buildTablePreview(val);
        return `<ul style="margin:0; padding-left:1.5rem; list-style: disc; columns: 1;">${val.map(v => `<li>${this.formatValue(v)}</li>`).join("")}</ul>`;
      }
      const entries = Object.entries(val);
      if (!entries.length) return '<span style="color: #9fb2d0;">Empty</span>';
      return `<div style="background: rgba(255,255,255,0.02); padding: 0.75rem; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05); display: flex; flex-direction: column; gap: 0.5rem; width: 100%;">
        ${entries.map(([k, v]) => `
          <div style="display: flex; flex-direction: row; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.03); padding-bottom: 0.25rem;">
            <strong style="color: #00d4c6; text-transform: capitalize; padding-right: 1rem; width: 40%; min-width: 120px;">${escapeHtml(formatDataKeyLabel(k))}</strong>
            <span style="width: 60%; text-align: left; word-break: break-word;">${this.formatValue(v)}</span>
          </div>`).join("")}
      </div>`;
    }
    return escapeHtml(String(val));
  }

  buildModulePreview(payload, moduleKey = "") {
    if (!payload || !Object.keys(payload).length) {
      return '<p class="table-empty">No structured preview available.</p>';
    }

    // Delete ignored keys recursively from the payload before rendering
    const cleanPayload = (obj) => {
      if (Array.isArray(obj)) return obj.map(cleanPayload).filter(v => v !== null && v !== undefined);
      if (obj !== null && typeof obj === 'object') {
        const cleaned = {};
        for (const [k, v] of Object.entries(obj)) {
          if (!MODULE_IGNORED_KEYS.has(k)) {
            // Keep actual data but strip noisy object wrappers if they match ignored names
            cleaned[k] = cleanPayload(v);
          }
        }
        return cleaned;
      }
      return obj;
    };

    const cleaned = cleanPayload(payload);

    // If cleaned payload is empty
    if (!cleaned || (typeof cleaned === 'object' && !Object.keys(cleaned).length)) {
      return '<p class="table-empty">No structured results to display.</p>';
    }

    // Try to format array of objects natively as a table
    const directArray = asArray(cleaned);
    if (directArray.length > 0 && typeof directArray[0] === 'object') {
      return this.buildTablePreview(directArray);
    }
    
    // Look for nested arrays that should be tables
    for (const [k, v] of Object.entries(cleaned)) {
      if (Array.isArray(v) && v.length > 0 && typeof v[0] === 'object') {
        // Render top-level array-of-objects as a wide table, ignore the rest if it's main
        return `
          <h5 style="color: #b4c2de; text-transform: uppercase; font-size: 0.85rem; letter-spacing: 0.05em; margin-bottom: 0.75rem;">
            ${escapeHtml(formatDataKeyLabel(k))}
          </h5>
          ${this.buildTablePreview(v)}
        `;
      }
    }

    // Single object keys - render as a horizontal property list card layout
    const kvPairs = Object.entries(cleaned)
      .map(([k, v]) => {
        return `
          <div style="background: rgba(255,255,255,0.05); border-radius: 8px; padding: 1.25rem; display: flex; flex-direction: column; justify-content: flex-start; height: 100%;">
            <h5 style="color: #b4c2de; text-transform: uppercase; font-size: 0.85rem; letter-spacing: 0.05em; margin-bottom: 0.75rem;">
              ${escapeHtml(formatDataKeyLabel(k))}
            </h5>
            <div style="flex-grow: 1;">${this.formatValue(v)}</div>
          </div>
        `;
      })
      .filter(Boolean)
      .join("");

    return `<div style="display: flex; flex-direction: row; flex-wrap: wrap; gap: 1rem;">
      <div style="display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); width: 100%;">
        ${kvPairs}
      </div>
    </div>`;
  }

  formatTableCellValue(value) {
    if (value === null || value === undefined) {
      return '<span style="color: #9fb2d0;">N/A</span>';
    }

    if (Array.isArray(value)) {
      return `<span style="color: #9fb2d0;">${value.length} item(s)</span>`;
    }

    if (typeof value === "object") {
      return `<span style="color: #9fb2d0;">${Object.keys(value).length} field(s)</span>`;
    }

    if (typeof value === "string") {
      const trimmed = value.trim();
      if (!trimmed) {
        return '<span style="color: #9fb2d0;">N/A</span>';
      }

      const looksStructured =
        (trimmed.startsWith("{") && trimmed.endsWith("}")) ||
        (trimmed.startsWith("[") && trimmed.endsWith("]"));

      if (looksStructured) {
        return '<span style="color: #9fb2d0;">Structured text omitted</span>';
      }

      const maxLen = 120;
      return escapeHtml(trimmed.length > maxLen ? `${trimmed.slice(0, maxLen)}...` : trimmed);
    }

    return this.formatValue(value);
  }

  buildTablePreview(records) {
    const rows = asArray(records).map((entry) => asObject(entry));
    if (!rows.length) {
      return '<p class="table-empty">No rows available to display.</p>';
    }

    const MAX_RENDER_ROWS = 220;
    const renderRows = rows.slice(0, MAX_RENDER_ROWS);
    const isTrimmed = rows.length > renderRows.length;

    const columns = Array.from(
      new Set(
        renderRows
          .slice(0, 120)
          .flatMap((entry) => Object.keys(entry))
      )
    );

    if (!columns.length) {
      return '<p class="table-empty">No valid table columns available.</p>';
    }

    const header = columns.map((c) => `<th style="text-align: left; padding: 0.75rem 1rem; color: var(--text-primary); font-weight: 600; font-size: 0.85rem; border-bottom: 2px solid var(--switch-border); border-right: 1px solid var(--switch-border); text-transform: uppercase; white-space: nowrap;">${escapeHtml(formatDataKeyLabel(c))}</th>`).join("");
    const body = renderRows
      .map((row) => {
        const cols = columns
          .map((column) => {
            const value = row?.[column];
            return `<td style="padding: 0.75rem 1rem; border-bottom: 1px solid var(--switch-border); border-right: 1px solid var(--switch-border); color: var(--text-secondary); font-size: 0.9rem; vertical-align: top;">${this.formatTableCellValue(value)}</td>`;
          })
          .join("");
        return `<tr>${cols}</tr>`;
      })
      .join("");

    const minTableWidth = Math.max(960, columns.length * 170);

    return `
      <div class="preview-table-wrap preview-table-wrap-scroll" style="max-height: 300px; overflow: auto; background: rgba(255,255,255,0.02); border-radius: 8px; border: 1px solid var(--card-border);">
        ${isTrimmed ? `<p class="table-empty" style="padding: 0.45rem 0.7rem 0;">Showing first ${renderRows.length} of ${rows.length} rows for smooth rendering.</p>` : ""}
        <table class="preview-table preview-table-wide" style="width: 100%; min-width: ${minTableWidth}px; border-collapse: collapse; text-align: left;">
          <thead><tr>${header}</tr></thead>
          <tbody>${body}</tbody>
        </table>
      </div>
    `;
  }

  selectAdvancedModule(key) {
    this.activeAdvancedKey = key;
    this.renderAdvancedSection();
  }

  async loadAdvancedModules() {
    const fileId = this.fileId || this.stateManager.get("dataset.fileId", null);
    if (!fileId) {
      this.toast.show("Upload and analyze a dataset first.", { type: "error" });
      return;
    }

    if (this.isAdvancedLoading || this.isBusy) {
      return;
    }

    this.isAdvancedLoading = true;
    this.setStatus("Loading advanced analytics modules...", "info");

    try {
      const result = await this.analyticsService.loadAdvancedBundle(fileId);
      this.advancedBundle = asObject(result?.data);
      this.advancedMeta = asObject(result?.meta);

      if (!this.activeAdvancedKey) {
        const firstSuccessful = asArray(this.advancedMeta?.successfulKeys)[0];
        const firstAny = Object.keys(this.advancedBundle)[0] || "";
        this.activeAdvancedKey = firstSuccessful || firstAny;
      }

      this.renderAdvancedSection();

      if (result?.success) {
        this.setStatus(result?.message || "Advanced modules loaded.", "success");
      } else {
        this.setStatus(result?.message || "Advanced modules failed.", "error");
      }
    } catch (error) {
      this.setStatus(`Advanced module loading failed: ${error?.message || "unknown error"}`, "error");
    } finally {
      this.isAdvancedLoading = false;
    }
  }

  async runAsyncAnalysisFallback(fileId) {
    const submit = await this.analyticsService.analyzeDatasetAsync(fileId, {
      timeoutSeconds: 300,
      maxRetries: 1
    });

    if (!submit?.success) {
      return {
        success: false,
        message: submit?.message || "Unable to queue async analysis."
      };
    }

    const jobId = safeText(submit?.data?.job_id, "");
    if (!jobId) {
      return {
        success: false,
        message: "Async analysis job did not return a job_id."
      };
    }

    this.updateProgress(66, "Async job queued. Waiting for completion...");

    const waitResult = await this.analyticsService.waitForAnalysisJob(jobId, {
      pollIntervalMs: 1500,
      maxPolls: 120
    });

    if (!waitResult?.success) {
      return {
        success: false,
        message: waitResult?.message || "Async analysis failed."
      };
    }

    return {
      success: true,
      message: "Async analysis completed.",
      data: waitResult?.data || {}
    };
  }

  destroyCharts() {
    if (!Array.isArray(this.chartInstances)) {
      this.chartInstances = [];
      return;
    }

    for (const instance of this.chartInstances) {
      try {
        instance?.destroy?.();
      } catch (_error) {
        // ignore chart cleanup exceptions
      }
    }

    this.chartInstances = [];
  }

  async askQuestion(question) {
    if (!this.fileId) {
      this.toast.show("Upload and analyze a dataset first.", { type: "error" });
      return;
    }

    const canAsk = Boolean(this.stateManager.get("dataset.analysisComplete", false));
    if (!canAsk) {
      this.toast.show("Run analytics before using chat.", { type: "error" });
      return;
    }

    const sendButton = this.container?.querySelector?.("[data-chat-send]");
    if (sendButton) {
      sendButton.disabled = true;
      sendButton.textContent = "Thinking...";
    }

    this.pushChatMessage("user", question);

    let result = { success: false, message: "Chat failed.", data: null };
    try {
      result = await this.reportService.askQuestion(this.fileId, question, { useGemini: false });
    } catch (error) {
      result = {
        success: false,
        message: `Chat failed: ${error?.message || "unknown error"}`,
        data: null
      };
    }

    if (result?.success) {
      this.pushChatMessage("assistant", safeText(result?.data?.answer, "No answer returned."));
    } else {
      this.pushChatMessage("system", safeText(result?.message, "Unable to fetch answer."));
      this.toast.show(result?.message || "Chat failed.", { type: "error" });
    }

    const chatInput = this.container?.querySelector?.("[data-chat-input]");
    if (chatInput) {
      chatInput.value = "";
    }

    if (sendButton) {
      sendButton.disabled = !canAsk;
      sendButton.textContent = "Ask";
    }
  }

  pushChatMessage(role, message) {
    this.chatMessages.push({ role, message: safeText(message, ""), at: new Date().toISOString() });
    this.renderChatThread();
  }

  renderChatThread() {
    const holder = this.container?.querySelector?.("[data-chat-thread]");
    if (!holder) {
      return;
    }

    if (!this.chatMessages.length) {
      holder.innerHTML = '<p class="chat-empty">Run analysis and ask your first question.</p>';
      return;
    }

    holder.innerHTML = this.chatMessages
      .map((entry) => {
        const label = entry?.role === "assistant" ? "AI" : entry?.role === "user" ? "You" : "System";
        return `
          <article class="chat-message chat-${escapeHtml(entry?.role || "system")}">
            <header>${escapeHtml(label)}</header>
            <p>${escapeHtml(entry?.message || "")}</p>
          </article>
        `;
      })
      .join("");

    holder.scrollTop = holder.scrollHeight;
  }

  setBusy(isBusy) {
    this.isBusy = Boolean(isBusy);

    const runButton = this.container?.querySelector?.("[data-run-analysis]");
    const refreshButton = this.container?.querySelector?.("[data-refresh-dashboard]");
    const loadAdvancedButton = this.container?.querySelector?.("[data-load-advanced]");

    if (runButton) {
      runButton.disabled = this.isBusy;
      runButton.textContent = this.isBusy ? "Analyzing..." : "Run Analytics";
    }

    if (refreshButton) {
      refreshButton.disabled = this.isBusy;
    }

    if (loadAdvancedButton) {
      loadAdvancedButton.disabled = this.isBusy || this.isAdvancedLoading;
      loadAdvancedButton.textContent = this.isAdvancedLoading ? "Loading Modules..." : "Load Advanced Modules";
    }
  }

  setChatEnabled(enabled) {
    const safeEnabled = Boolean(enabled);
    const input = this.container?.querySelector?.("[data-chat-input]");
    const sendButton = this.container?.querySelector?.("[data-chat-send]");

    if (input) {
      input.disabled = !safeEnabled;
    }

    if (sendButton) {
      sendButton.disabled = !safeEnabled;
    }
  }

  updateProgress(percent, label, isError = false) {
    const block = this.container?.querySelector?.("[data-analysis-progress]");
    const fill = this.container?.querySelector?.("[data-analysis-fill]");
    const text = this.container?.querySelector?.("[data-analysis-label]");

    if (!block || !fill || !text) {
      return;
    }

    if (percent <= 0 && !this.isBusy) {
      block.hidden = true;
      fill.style.width = "0%";
      text.textContent = "";
      return;
    }

    block.hidden = false;
    fill.style.width = `${Math.max(0, Math.min(100, percent))}%`;
    text.textContent = safeText(label, "Working...");

    if (isError) {
      fill.classList.add("is-error");
    } else {
      fill.classList.remove("is-error");
    }

    if (percent >= 100 && !this.isBusy) {
      if (typeof window !== "undefined") {
        window.setTimeout(() => {
          block.hidden = true;
        }, 1200);
      }
    }
  }

  setStatus(message, variant = "info") {
    const status = this.container?.querySelector?.("[data-dashboard-status]");
    if (!status) {
      return;
    }

    status.textContent = safeText(message, "Ready.");
    status.setAttribute("data-variant", variant);
  }
}

