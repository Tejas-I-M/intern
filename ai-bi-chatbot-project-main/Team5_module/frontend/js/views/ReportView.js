import { reportService as sharedReportService } from "../services/ReportService.js?v=2";
import { analyticsService as sharedAnalyticsService } from "../services/AnalyticsService.js";
import { stateManager as sharedStateManager } from "../core/StateManager.js";
import { toast as sharedToast } from "../components/Toast.js";
import { Sidebar } from "../components/Sidebar.js";

function safeText(value, fallback = "") {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
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

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function asObject(value) {
  return value && typeof value === "object" ? value : {};
}

const REPORT_ADVANCED_MODULE_LABELS = {
  cohort: "Cohort Analysis",
  geographic: "Geographic Analysis",
  timeseries: "Timeseries Analysis",
  churn: "Churn Prediction",
  forecast: "Sales Forecast",
  affinity: "Product Affinity",
  clv: "Customer Lifetime Value",
  repeatPurchase: "Repeat Purchase",
  healthScore: "Health Score",
  anomalies: "Anomalies",
  productPerformance: "Product Performance",
  promotionalImpact: "Promotional Impact"
};

const REPORT_ADVANCED_DEFAULT_KEYS = Object.keys(REPORT_ADVANCED_MODULE_LABELS);

export class ReportView {
  constructor(options = {}) {
    this.router = options?.router || null;
    this.reportService = options?.reportService || sharedReportService;
    this.analyticsService = options?.analyticsService || sharedAnalyticsService;
    this.stateManager = options?.stateManager || sharedStateManager;
    this.toast = options?.toast || sharedToast;

    this.host = null;
    this.container = null;
    this.sidebar = null;
    this.unsubscribe = null;

    this.fileId = null;
    this.lastFileId = null;
    this.canGenerate = false;
    this.isBusy = false;

    this.latestReport = null;
    this.reportHistory = [];
    this.dashboardSnapshot = {};
    this.availableAdvancedModules = [];
    this.selectedAdvancedModules = [];

    this.boundClickHandler = this.handleClick.bind(this);
  }

  mount(root) {
    if (!root) {
      return () => {};
    }

    this.host = root;
    this.host.innerHTML = this.render();
    this.container = this.host.querySelector(".report-view");

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
    }

    this.unsubscribe = this.stateManager.subscribe((nextState) => {
      this.syncState(nextState);
    });

    this.syncState(this.stateManager.getState());
    this.loadHistory();
    this.loadDashboardSummary();

    return () => this.unmount();
  }

  unmount() {
    if (typeof this.unsubscribe === "function") {
      this.unsubscribe();
      this.unsubscribe = null;
    }

    if (this.container) {
      this.container.removeEventListener("click", this.boundClickHandler);
      this.container = null;
    }

    if (this.sidebar) {
      this.sidebar.unmount();
      this.sidebar = null;
    }

    this.host = null;
  }

  render() {
    return `
      <section class="report-view app-grid" aria-label="Report generation view">
        <div data-sidebar-mount class="sidebar-slot"></div>

        <article class="report-main glass-card">
          <header class="report-head">
            <h2>Report Center</h2>
            <p>Generate summary report, preview it, and download PDF.</p>
          </header>

          <p class="upload-status" data-report-status data-variant="info">
            Run analysis first to enable reports.
          </p>

          <section class="dash-card report-advanced-card">
            <h3>Advanced Summary Modules</h3>
            <p class="report-advanced-note">Choose which advanced module results appear in the report.</p>
            <div class="report-advanced-actions">
              <button type="button" class="ghost-btn" data-report-advanced-select="all">Select All</button>
              <button type="button" class="ghost-btn" data-report-advanced-select="none">Clear All</button>
            </div>
            <div class="report-advanced-options" data-report-advanced-options>
              <p class="report-history-empty">Loading module options...</p>
            </div>
          </section>

          <div class="report-actions">
            <button type="button" class="auth-submit" data-generate-report>Generate Report</button>
            <button type="button" class="ghost-btn" data-refresh-reports>Refresh History</button>
            <button type="button" class="ghost-btn" data-go-dashboard>Go Dashboard</button>
          </div>

          <section class="dash-card report-summary-card" data-report-summary>
            <h3>Summary</h3>
            <ul class="summary-list" data-report-summary-list>
              <li>Summary will appear after dashboard data is available.</li>
            </ul>
          </section>

          <section class="report-latest" data-report-latest>
            <h3>Latest Report</h3>
            <p class="report-meta" data-report-meta>No report generated yet.</p>

            <div class="report-links">
              <a class="inline-link" data-report-preview-link href="#" target="_blank" rel="noopener" hidden>Open Preview</a>
              <a class="inline-link" data-report-download-link href="#" target="_blank" rel="noopener" hidden>Download PDF</a>
            </div>

            <iframe
              data-report-preview
              class="report-preview-frame"
              title="Report preview"
              loading="lazy"
            ></iframe>
          </section>

          <section class="report-history">
            <h3>History</h3>
            <div class="history-list" data-report-history>
              <p class="report-history-empty">No reports yet.</p>
            </div>
          </section>
        </article>
      </section>
    `;
  }

  handleClick(event) {
    const generateButton = event?.target?.closest?.("[data-generate-report]");
    if (generateButton) {
      this.generateReport();
      return;
    }

    const refreshButton = event?.target?.closest?.("[data-refresh-reports]");
    if (refreshButton) {
      this.loadHistory();
      this.loadDashboardSummary();
      return;
    }

    const dashboardButton = event?.target?.closest?.("[data-go-dashboard]");
    if (dashboardButton && this.router && typeof this.router.navigate === "function") {
      this.router.navigate("/dashboard");
      return;
    }

    const historyTrigger = event?.target?.closest?.("[data-history-report-id]");
    if (historyTrigger) {
      const reportId = safeText(historyTrigger.getAttribute("data-history-report-id"), "");
      if (reportId) {
        this.loadFromHistory(reportId);
      }
      return;
    }

    const moduleToggle = event?.target?.closest?.("[data-report-advanced-module]");
    if (moduleToggle) {
      const key = safeText(moduleToggle.getAttribute("data-report-advanced-module"), "");
      const isChecked = Boolean(moduleToggle.checked);
      this.toggleAdvancedModule(key, isChecked);
      return;
    }

    const bulkToggle = event?.target?.closest?.("[data-report-advanced-select]");
    if (bulkToggle) {
      const mode = safeText(bulkToggle.getAttribute("data-report-advanced-select"), "");
      if (mode === "all") {
        this.selectedAdvancedModules = [...this.availableAdvancedModules];
        this.renderAdvancedModuleOptions();
      } else if (mode === "none") {
        this.selectedAdvancedModules = [];
        this.renderAdvancedModuleOptions();
      }
    }
  }

  async generateReport() {
    if (!this.canGenerate || !this.fileId) {
      this.toast.show("Run analysis first to generate reports.", { type: "error" });
      return;
    }

    if (this.isBusy) {
      return;
    }

    this.setBusy(true);
    this.setStatus("Generating report...", "info");

    const selectedAdvancedModules = this.getSelectedAdvancedModules();
    if (!selectedAdvancedModules.length) {
      this.setBusy(false);
      this.setStatus("Select at least one advanced module before generating report.", "error");
      this.toast.show("Select at least one advanced module before generating report.", { type: "error" });
      return;
    }

    const includeAdvancedModules = true;

    let result = { success: false, message: "Report generation failed.", data: null };

    try {
      result = await this.reportService.generateReport(this.fileId, {
        includeAdvancedModules,
        selectedAdvancedModules
      });
    } catch (error) {
      result = {
        success: false,
        message: `Report generation failed: ${error?.message || "unknown error"}`,
        data: null
      };
    }

    if (result?.success) {
      this.latestReport = result?.data || null;
      this.renderLatestReport();
      this.setStatus("Report generated successfully.", "success");
      this.toast.show("Report generated.", { type: "success", duration: 1800 });
      await this.loadHistory();
    } else {
      this.setStatus(result?.message || "Report generation failed.", "error");
      this.toast.show(result?.message || "Report generation failed.", { type: "error" });
    }

    this.setBusy(false);
  }

  async loadHistory() {
    const isAuthenticated = Boolean(this.stateManager.get("auth.isAuthenticated", false));
    if (!isAuthenticated) {
      return;
    }

    let result = { success: false, data: [], message: "Unable to load history." };

    try {
      result = await this.reportService.getReportHistory();
    } catch (error) {
      result = {
        success: false,
        data: [],
        message: `Unable to load history: ${error?.message || "unknown error"}`
      };
    }

    if (result?.success) {
      this.reportHistory = Array.isArray(result?.data) ? result.data : [];
      this.hydrateLatestReportFromHistory();
      this.renderHistory();
    } else {
      this.reportHistory = [];
      this.latestReport = null;
      this.renderLatestReport();
      this.renderHistory();
      this.setStatus(result?.message || "Unable to load report history.", "error");
    }
  }

  hydrateLatestReportFromHistory() {
    if (!this.reportHistory.length) {
      this.latestReport = null;
      this.renderLatestReport();
      return;
    }

    const currentReportId = safeText(this.latestReport?.reportId, "");
    if (currentReportId && this.reportHistory.some((item) => safeText(item?.reportId, "") === currentReportId)) {
      this.renderLatestReport();
      return;
    }

    const rememberedLatest = asObject(this.stateManager.get("reports.latest", {}));
    const rememberedReportId = safeText(rememberedLatest?.reportId, "");
    const rememberedReport = rememberedReportId
      ? this.reportHistory.find((item) => safeText(item?.reportId, "") === rememberedReportId)
      : null;

    const activeFileReport = this.fileId
      ? this.reportHistory.find((item) => safeText(item?.fileId, "") === this.fileId)
      : null;

    this.latestReport = rememberedReport || activeFileReport || this.reportHistory[0] || null;

    if (this.latestReport) {
      this.stateManager.updatePath("reports.latest", this.latestReport);
    }

    this.renderLatestReport();
  }

  async loadDashboardSummary() {
    const fileId = this.stateManager.get("dataset.fileId", null);
    const analysisComplete = Boolean(this.stateManager.get("dataset.analysisComplete", false));
    if (!fileId || !analysisComplete) {
      return;
    }

    try {
      const dashboardResult = await this.analyticsService.getDashboardData(fileId);
      if (dashboardResult?.success) {
        this.dashboardSnapshot = asObject(dashboardResult?.data);
        this.renderSummary();
      }
    } catch (_error) {
      // Keep summary block resilient.
    }
  }

  resolveAdvancedModulesForFile(fileId) {
    const safeFileId = safeText(fileId, "");
    const cacheMap = asObject(this.stateManager.get("ui.advancedSummaryCache", {}));
    const cacheEntry = asObject(cacheMap?.[safeFileId]);
    const cachedBundle = asObject(cacheEntry?.advancedBundle);
    const cachedKeys = Object.keys(cachedBundle).filter((key) => REPORT_ADVANCED_DEFAULT_KEYS.includes(key));
    return cachedKeys.length ? cachedKeys : [...REPORT_ADVANCED_DEFAULT_KEYS];
  }

  initializeAdvancedModuleOptions() {
    const options = this.resolveAdvancedModulesForFile(this.fileId);
    this.availableAdvancedModules = options;

    const selected = this.selectedAdvancedModules.filter((key) => options.includes(key));
    this.selectedAdvancedModules = selected;

    this.renderAdvancedModuleOptions();
  }

  renderAdvancedModuleOptions() {
    const holder = this.container?.querySelector?.("[data-report-advanced-options]");
    if (!holder) {
      return;
    }

    if (!this.availableAdvancedModules.length) {
      holder.innerHTML = '<p class="report-history-empty">No advanced modules available yet.</p>';
      return;
    }

    holder.innerHTML = this.availableAdvancedModules
      .map((key) => {
        const checked = this.selectedAdvancedModules.includes(key) ? "checked" : "";
        const label = REPORT_ADVANCED_MODULE_LABELS[key] || key;
        return `
          <label class="report-advanced-option">
            <input type="checkbox" data-report-advanced-module="${escapeHtml(key)}" ${checked} />
            <span>${escapeHtml(label)}</span>
          </label>
        `;
      })
      .join("");
  }

  toggleAdvancedModule(key, isChecked) {
    const safeKey = safeText(key, "");
    if (!safeKey) {
      return;
    }

    if (isChecked) {
      if (!this.selectedAdvancedModules.includes(safeKey)) {
        this.selectedAdvancedModules = [...this.selectedAdvancedModules, safeKey];
      }
      return;
    }

    this.selectedAdvancedModules = this.selectedAdvancedModules.filter((item) => item !== safeKey);
  }

  getSelectedAdvancedModules() {
    const checkboxes = asArray(
      Array.from(this.container?.querySelectorAll?.("[data-report-advanced-module]") || [])
    );

    const selected = checkboxes
      .filter((node) => Boolean(node?.checked))
      .map((node) => safeText(node?.getAttribute?.("data-report-advanced-module"), ""))
      .filter(Boolean);

    return selected;
  }

  renderSummary() {
    const holder = this.container?.querySelector?.("[data-report-summary-list]");
    if (!holder) {
      return;
    }

    const kpis = asObject(this.dashboardSnapshot?.kpis);
    const topCategories = asArray(this.dashboardSnapshot?.top_categories);

    const categoryLines = topCategories
      .slice(0, 5)
      .map((item, index) => {
        const name = safeText(item?.product_category || item?.category || item?.name, "Category");
        const amount = item?.revenue ?? item?.sales ?? item?.total ?? 0;
        return `${index + 1}. ${name}: ${formatCurrency(amount)}`;
      });

    holder.innerHTML = `
      <li><strong>Summary</strong></li>
      <li>Total Revenue: ${escapeHtml(formatCurrency(kpis?.total_revenue))}</li>
      <li>Total Orders: ${escapeHtml(String(kpis?.total_orders ?? "N/A"))}</li>
      <li>Unique Customers: ${escapeHtml(String(kpis?.unique_customers ?? "N/A"))}</li>
      <li><strong>Top Products</strong></li>
      ${categoryLines.length ? categoryLines.map((line) => `<li>${escapeHtml(line)}</li>`).join("") : "<li>No product ranking available.</li>"}
    `;
  }

  loadFromHistory(reportId) {
    const selected = this.reportHistory.find((item) => safeText(item?.reportId, "") === reportId);
    if (!selected) {
      return;
    }

    this.latestReport = selected;
    this.renderLatestReport();
    this.setStatus("Loaded report from history.", "success");
  }

  renderLatestReport() {
    const meta = this.container?.querySelector?.("[data-report-meta]");
    const previewLink = this.container?.querySelector?.("[data-report-preview-link]");
    const downloadLink = this.container?.querySelector?.("[data-report-download-link]");
    const frame = this.container?.querySelector?.("[data-report-preview]");

    if (!meta || !previewLink || !downloadLink || !frame) {
      return;
    }

    if (!this.latestReport) {
      meta.textContent = "No report generated yet.";
      previewLink.hidden = true;
      previewLink.href = "#";
      downloadLink.hidden = true;
      downloadLink.href = "#";
      frame.removeAttribute("src");
      return;
    }

    const reportId = safeText(this.latestReport?.reportId, "N/A");
    const datasetName = safeText(this.latestReport?.datasetName, "Dataset");
    const createdAt = safeText(this.latestReport?.createdAt, "recently");
    const previewUrl = safeText(this.latestReport?.previewUrl, "");
    const downloadPdfUrl = safeText(this.latestReport?.downloadPdfUrl, "");

    meta.innerHTML = `
      <strong>Report ID:</strong> ${escapeHtml(reportId)}
      <span>|</span>
      <strong>Dataset:</strong> ${escapeHtml(datasetName)}
      <span>|</span>
      <strong>Created:</strong> ${escapeHtml(createdAt)}
    `;

    if (previewUrl) {
      previewLink.hidden = false;
      previewLink.href = previewUrl;
      frame.src = previewUrl;
    } else {
      previewLink.hidden = true;
      previewLink.href = "#";
      frame.removeAttribute("src");
    }

    if (downloadPdfUrl) {
      downloadLink.hidden = false;
      downloadLink.href = downloadPdfUrl;
    } else {
      downloadLink.hidden = true;
      downloadLink.href = "#";
    }
  }

  renderHistory() {
    const holder = this.container?.querySelector?.("[data-report-history]");
    if (!holder) {
      return;
    }

    if (!this.reportHistory.length) {
      holder.innerHTML = '<p class="report-history-empty">No saved reports available.</p>';
      return;
    }

    holder.innerHTML = this.reportHistory
      .map((item) => {
        const reportId = safeText(item?.reportId, "");
        const datasetName = safeText(item?.datasetName, "Dataset");
        const createdAt = safeText(item?.createdAt, "recently");
        return `
          <button type="button" class="history-item" data-history-report-id="${escapeHtml(reportId)}">
            <strong>${escapeHtml(datasetName)}</strong>
            <span>${escapeHtml(reportId)}</span>
            <small>${escapeHtml(createdAt)}</small>
          </button>
        `;
      })
      .join("");
  }

  syncState(state) {
    const isAuthenticated = Boolean(state?.auth?.isAuthenticated);
    const fileId = state?.dataset?.fileId || null;
    const analysisComplete = Boolean(state?.dataset?.analysisComplete);

    if (this.lastFileId !== fileId) {
      this.lastFileId = fileId;
      this.fileId = fileId;
      this.initializeAdvancedModuleOptions();
    }

    this.fileId = fileId;
    this.canGenerate = isAuthenticated && Boolean(fileId) && analysisComplete;

    if (!isAuthenticated) {
      this.setStatus("Login required before report access.", "error");
      this.setActionState(false);
      return;
    }

    if (!fileId) {
      this.setStatus("Upload dataset first to enable reports.", "error");
      this.setActionState(false);
      return;
    }

    if (!analysisComplete) {
      this.setStatus("Run analytics first to generate reports.", "error");
      this.setActionState(false);
      return;
    }

    this.setStatus("Report center ready.", "success");
    this.setActionState(true);
  }

  setActionState(enabled) {
    const generateButton = this.container?.querySelector?.("[data-generate-report]");
    if (generateButton) {
      generateButton.disabled = !enabled || this.isBusy;
    }
  }

  setBusy(isBusy) {
    this.isBusy = Boolean(isBusy);

    const generateButton = this.container?.querySelector?.("[data-generate-report]");
    const refreshButton = this.container?.querySelector?.("[data-refresh-reports]");

    if (generateButton) {
      generateButton.disabled = this.isBusy || !this.canGenerate;
      generateButton.textContent = this.isBusy ? "Generating..." : "Generate Report";
    }

    if (refreshButton) {
      refreshButton.disabled = this.isBusy;
    }
  }

  setStatus(message, variant = "info") {
    const status = this.container?.querySelector?.("[data-report-status]");
    if (!status) {
      return;
    }

    status.textContent = safeText(message, "Ready.");
    status.setAttribute("data-variant", variant);
  }
}
