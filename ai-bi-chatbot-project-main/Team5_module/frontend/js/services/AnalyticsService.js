import { apiClient } from "../core/ApiClient.js";
import { stateManager } from "../core/StateManager.js";

function safeObject(value) {
  return value && typeof value === "object" ? value : {};
}

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function toQueryString(params = {}) {
  const entries = Object.entries(params).filter(([, value]) => {
    return value !== undefined && value !== null && value !== "";
  });

  if (!entries.length) {
    return "";
  }

  const search = new URLSearchParams();
  for (const [key, value] of entries) {
    search.append(key, String(value));
  }

  const query = search.toString();
  return query ? `?${query}` : "";
}

function sleep(ms) {
  return new Promise((resolve) => {
    if (typeof window !== "undefined") {
      window.setTimeout(resolve, ms);
      return;
    }
    setTimeout(resolve, ms);
  });
}

export class AnalyticsService {
  constructor(options = {}) {
    this.api = options?.apiClient || apiClient;
    this.stateManager = options?.stateManager || stateManager;
  }

  getActiveFileId(fallbackFileId = null) {
    if (fallbackFileId) {
      return fallbackFileId;
    }

    return this.stateManager.get("dataset.fileId", null);
  }

  async requestAnalysis(path, options = {}) {
    const method = String(options?.method || "GET").toUpperCase();
    const body = options?.body;

    let response = null;
    try {
      if (method === "POST") {
        response = await this.api.post(path, body || {});
      } else {
        response = await this.api.get(path);
      }
    } catch (error) {
      return {
        success: false,
        message: `${method} ${path} failed: ${error?.message || "unknown error"}`,
        data: null
      };
    }

    if (!response?.success) {
      return {
        success: false,
        message: response?.message || `${method} ${path} failed.`,
        data: response?.data || null,
        status: response?.status || 0
      };
    }

    return {
      success: true,
      message: response?.message || "Request completed.",
      data: response?.data || {},
      status: response?.status || 200
    };
  }

  async analyzeDataset(fileId = null) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return {
        success: false,
        message: "Dataset file_id is missing. Upload first.",
        data: null
      };
    }

    const response = await this.requestAnalysis(`/api/analysis/analyze/${encodeURIComponent(activeFileId)}`, {
      method: "POST",
      body: {}
    });

    if (!response?.success) {
      return {
        success: false,
        message: response?.message || "Analysis failed.",
        data: response?.data || null
      };
    }

    const payload = safeObject(response?.data);
    const capabilities = safeObject(payload?.capabilities);

    this.stateManager.updatePath("dataset.fileId", activeFileId);
    this.stateManager.updatePath("dataset.capabilities", capabilities);
    this.stateManager.updatePath("dataset.analysisPlan", payload?.analysis_plan || []);
    this.stateManager.updatePath("dataset.mappedColumns", payload?.mapped_columns || {});
    this.stateManager.updatePath("dataset.sourceColumns", payload?.source_columns || []);
    this.stateManager.updatePath("dataset.analysisMode", payload?.analysis_mode || "unknown");
    this.stateManager.markAnalysisComplete(true);

    return {
      success: true,
      message: payload?.message || response?.message || "Analysis completed.",
      data: payload
    };
  }

  async analyzeDatasetAsync(fileId = null, options = {}) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return {
        success: false,
        message: "Dataset file_id is missing. Upload first.",
        data: null
      };
    }

    const body = {
      timeout_seconds: options?.timeoutSeconds,
      max_retries: options?.maxRetries
    };

    return this.requestAnalysis(`/api/analysis/analyze-async/${encodeURIComponent(activeFileId)}`, {
      method: "POST",
      body
    });
  }

  async getAnalysisJob(jobId) {
    const safeJobId = String(jobId || "").trim();
    if (!safeJobId) {
      return {
        success: false,
        message: "job_id is required.",
        data: null
      };
    }

    return this.requestAnalysis(`/api/analysis/jobs/${encodeURIComponent(safeJobId)}`);
  }

  async waitForAnalysisJob(jobId, options = {}) {
    const pollIntervalMs = Math.max(500, Number(options?.pollIntervalMs || 1500));
    const maxPolls = Math.max(5, Number(options?.maxPolls || 120));

    for (let index = 0; index < maxPolls; index += 1) {
      const statusResult = await this.getAnalysisJob(jobId);
      if (!statusResult?.success) {
        return statusResult;
      }

      const job = safeObject(statusResult?.data?.job);
      const status = String(job?.status || "").toLowerCase();

      if (status === "completed") {
        const resultPayload = safeObject(job?.result);
        if (Object.keys(resultPayload).length) {
          this.stateManager.updatePath("dataset.capabilities", safeObject(resultPayload?.capabilities));
          this.stateManager.updatePath("dataset.analysisPlan", resultPayload?.analysis_plan || []);
          this.stateManager.updatePath("dataset.analysisMode", resultPayload?.analysis_mode || "async");
          this.stateManager.markAnalysisComplete(true);
        }

        return {
          success: true,
          message: "Async analysis completed.",
          data: {
            job,
            result: resultPayload
          }
        };
      }

      if (status === "failed") {
        return {
          success: false,
          message: job?.error || "Async analysis failed.",
          data: { job }
        };
      }

      await sleep(pollIntervalMs);
    }

    return {
      success: false,
      message: "Async analysis timed out while waiting for job completion.",
      data: null
    };
  }

  async getDashboardData(fileId = null) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return {
        success: false,
        message: "Dataset file_id is missing.",
        data: null
      };
    }

    const response = await this.requestAnalysis(`/api/analysis/dashboard-data/${encodeURIComponent(activeFileId)}`);

    if (!response?.success) {
      return {
        success: false,
        message: response?.message || "Dashboard data unavailable.",
        data: response?.data || null
      };
    }

    const payload = safeObject(response?.data);
    const dashboardData = safeObject(payload?.data);

    const capabilities = safeObject(dashboardData?.capabilities);
    if (Object.keys(capabilities).length > 0) {
      this.stateManager.updatePath("dataset.capabilities", capabilities);
    }

    return {
      success: true,
      message: payload?.message || response?.message || "Dashboard data ready.",
      data: dashboardData
    };
  }

  async getTeam4Visualization(fileId = null) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return {
        success: false,
        message: "Dataset file_id is missing.",
        data: null
      };
    }

    const response = await this.requestAnalysis(`/api/analysis/team4-visualization/${encodeURIComponent(activeFileId)}`);

    if (!response?.success) {
      return {
        success: false,
        message: response?.message || "Team4 visualization unavailable.",
        data: response?.data || null
      };
    }

    const payload = safeObject(response?.data);

    return {
      success: true,
      message: payload?.message || response?.message || "Team4 visualization ready.",
      data: payload?.team4_visualization || {}
    };
  }

  async getDatasetProfile(fileId = null) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    return this.requestAnalysis(`/api/analysis/profile/${encodeURIComponent(activeFileId)}`);
  }

  async getRecentAnalyses() {
    return this.requestAnalysis("/api/analysis/recent-analyses");
  }

  async getSuggestedQuestions(fileId = null) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    return this.requestAnalysis(`/api/analysis/suggested-questions/${encodeURIComponent(activeFileId)}`);
  }

  async getInsights(fileId = null) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    return this.requestAnalysis(`/api/analysis/insights/${encodeURIComponent(activeFileId)}`);
  }

  async getFullReport(fileId = null) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    return this.requestAnalysis(`/api/analysis/full-report/${encodeURIComponent(activeFileId)}`);
  }

  async getNlpStatus() {
    return this.requestAnalysis("/api/analysis/nlp-status");
  }

  async getMetrics(fileId = null, timeRange = "all") {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    const safeRange = String(timeRange || "all").trim() || "all";
    return this.requestAnalysis(`/api/analysis/metrics/${encodeURIComponent(activeFileId)}/${encodeURIComponent(safeRange)}`);
  }

  async getCapabilities(fileId = null) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    return this.requestAnalysis(`/api/analysis/capabilities/${encodeURIComponent(activeFileId)}`);
  }

  async getCohortAnalysis(fileId = null) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    return this.requestAnalysis(`/api/analysis/cohort-analysis/${encodeURIComponent(activeFileId)}`);
  }

  async getGeographicAnalysis(fileId = null) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    return this.requestAnalysis(`/api/analysis/geographic-analysis/${encodeURIComponent(activeFileId)}`);
  }

  async getTimeseriesAnalysis(fileId = null, params = {}) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    const query = toQueryString({ period: params?.period });
    return this.requestAnalysis(`/api/analysis/timeseries-analysis/${encodeURIComponent(activeFileId)}${query}`);
  }

  async getChurnPrediction(fileId = null, params = {}) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    const query = toQueryString({ days_threshold: params?.daysThreshold });
    return this.requestAnalysis(`/api/analysis/churn-prediction/${encodeURIComponent(activeFileId)}${query}`);
  }

  async getSalesForecast(fileId = null, params = {}) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    const query = toQueryString({ periods: params?.periods });
    return this.requestAnalysis(`/api/analysis/sales-forecast/${encodeURIComponent(activeFileId)}${query}`);
  }

  async getProductAffinity(fileId = null, params = {}) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    const query = toQueryString({
      min_support: params?.minSupport,
      min_confidence: params?.minConfidence
    });
    return this.requestAnalysis(`/api/analysis/product-affinity/${encodeURIComponent(activeFileId)}${query}`);
  }

  async exportAnalysis(fileId = null, format = "pdf") {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    return this.requestAnalysis(`/api/analysis/export/${encodeURIComponent(activeFileId)}/${encodeURIComponent(format)}`);
  }

  async getExportStatus(fileId = null, exportId = null) {
    const activeFileId = this.getActiveFileId(fileId);
    const safeExportId = String(exportId || "").trim();
    if (!activeFileId || !safeExportId) {
      return { success: false, message: "file_id and export_id are required.", data: null };
    }
    return this.requestAnalysis(`/api/analysis/export-status/${encodeURIComponent(activeFileId)}/${encodeURIComponent(safeExportId)}`);
  }

  async filterByCategory(fileId = null, category = "") {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    const query = toQueryString({ category });
    return this.requestAnalysis(`/api/analysis/filter/category/${encodeURIComponent(activeFileId)}${query}`);
  }

  async filterBySegment(fileId = null, segment = "") {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    const query = toQueryString({ segment });
    return this.requestAnalysis(`/api/analysis/filter/segment/${encodeURIComponent(activeFileId)}${query}`);
  }

  async filterTransactions(fileId = null, params = {}) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    const query = toQueryString({
      category: params?.category,
      customer_id: params?.customerId,
      date_start: params?.dateStart,
      date_end: params?.dateEnd,
      limit: params?.limit
    });
    return this.requestAnalysis(`/api/analysis/filter/transactions/${encodeURIComponent(activeFileId)}${query}`);
  }

  async getAvailableFilterValues(fileId = null) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    return this.requestAnalysis(`/api/analysis/filter/available-values/${encodeURIComponent(activeFileId)}`);
  }

  async getClv(fileId = null) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    return this.requestAnalysis(`/api/analysis/clv/${encodeURIComponent(activeFileId)}`);
  }

  async getTopClv(fileId = null, limit = 10) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    return this.requestAnalysis(`/api/analysis/clv/${encodeURIComponent(activeFileId)}/top/${encodeURIComponent(limit)}`);
  }

  async getClvBySegment(fileId = null, segmentName = "high-value") {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    return this.requestAnalysis(`/api/analysis/clv/${encodeURIComponent(activeFileId)}/segment/${encodeURIComponent(segmentName)}`);
  }

  async getRepeatPurchase(fileId = null) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    return this.requestAnalysis(`/api/analysis/repeat-purchase/${encodeURIComponent(activeFileId)}`);
  }

  async getRepeatPurchaseCohort(fileId = null) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    return this.requestAnalysis(`/api/analysis/repeat-purchase/${encodeURIComponent(activeFileId)}/cohort`);
  }

  async getHealthScore(fileId = null) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    return this.requestAnalysis(`/api/analysis/health-score/${encodeURIComponent(activeFileId)}`);
  }

  async getHealthScoreSummary(fileId = null) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    return this.requestAnalysis(`/api/analysis/health-score/${encodeURIComponent(activeFileId)}/summary`);
  }

  async getHealthScoreByStatus(fileId = null, statusType = "excellent") {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    return this.requestAnalysis(`/api/analysis/health-score/${encodeURIComponent(activeFileId)}/status/${encodeURIComponent(statusType)}`);
  }

  async getAnomalies(fileId = null, params = {}) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    const query = toQueryString({ sensitivity: params?.sensitivity });
    return this.requestAnalysis(`/api/analysis/anomalies/${encodeURIComponent(activeFileId)}${query}`);
  }

  async getProductPerformance(fileId = null) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    return this.requestAnalysis(`/api/analysis/product-performance/${encodeURIComponent(activeFileId)}`);
  }

  async getProductPerformanceByCategory(fileId = null, category = "Star") {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    return this.requestAnalysis(`/api/analysis/product-performance/${encodeURIComponent(activeFileId)}/category/${encodeURIComponent(category)}`);
  }

  async getPromotionalImpact(fileId = null) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return { success: false, message: "Dataset file_id is missing.", data: null };
    }
    return this.requestAnalysis(`/api/analysis/promotional-impact/${encodeURIComponent(activeFileId)}`);
  }

  async loadAdvancedBundle(fileId = null) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return {
        success: false,
        message: "Dataset file_id is missing.",
        data: {}
      };
    }

    const requests = {
      capabilities: () => this.getCapabilities(activeFileId),
      insights: () => this.getInsights(activeFileId),
      recentAnalyses: () => this.getRecentAnalyses(),
      cohort: () => this.getCohortAnalysis(activeFileId),
      geographic: () => this.getGeographicAnalysis(activeFileId),
      timeseries: () => this.getTimeseriesAnalysis(activeFileId),
      churn: () => this.getChurnPrediction(activeFileId),
      forecast: () => this.getSalesForecast(activeFileId),
      affinity: () => this.getProductAffinity(activeFileId),
      clv: () => this.getClv(activeFileId),
      repeatPurchase: () => this.getRepeatPurchase(activeFileId),
      healthScore: () => this.getHealthScore(activeFileId),
      anomalies: () => this.getAnomalies(activeFileId),
      productPerformance: () => this.getProductPerformance(activeFileId),
      promotionalImpact: () => this.getPromotionalImpact(activeFileId),
      availableFilters: () => this.getAvailableFilterValues(activeFileId)
    };

    const entries = Object.entries(requests);
    const settled = await Promise.all(
      entries.map(async ([key, fn]) => {
        const result = await fn();
        return [key, result];
      })
    );

    const bundle = {};
    let successCount = 0;

    for (const [key, result] of settled) {
      bundle[key] = result;
      if (result?.success) {
        successCount += 1;
      }
    }

    const overallSuccess = successCount > 0;
    return {
      success: overallSuccess,
      message: overallSuccess
        ? "Advanced modules loaded successfully."
        : "Advanced modules failed to load.",
      data: bundle,
      meta: {
        successCount,
        totalCount: entries.length,
        failedCount: entries.length - successCount,
        keys: entries.map(([key]) => key),
        successfulKeys: entries
          .map(([key]) => key)
          .filter((key) => bundle[key]?.success),
        failedKeys: entries
          .map(([key]) => key)
          .filter((key) => !bundle[key]?.success)
      }
    };
  }

  async loadDashboardBundle(fileId = null) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return {
        success: false,
        message: "Dataset file_id is missing.",
        data: {
          dashboard: {},
          team4: {}
        }
      };
    }

    const dashboardResult = await this.getDashboardData(activeFileId);
    const team4Result = await this.getTeam4Visualization(activeFileId);
    const capabilityResult = await this.getCapabilities(activeFileId);
    const insightResult = await this.getInsights(activeFileId);

    if (!dashboardResult?.success && !team4Result?.success && !capabilityResult?.success && !insightResult?.success) {
      return {
        success: false,
        message:
          dashboardResult?.message ||
          team4Result?.message ||
          capabilityResult?.message ||
          insightResult?.message ||
          "Unable to load dashboard bundle.",
        data: {
          dashboard: dashboardResult?.data || {},
          team4: team4Result?.data || {},
          capabilities: capabilityResult?.data || {},
          insights: insightResult?.data || {}
        }
      };
    }

    const capabilitiesPayload = safeObject(capabilityResult?.data);
    const capabilities = safeObject(capabilitiesPayload?.capabilities);
    const analysisPlan = capabilitiesPayload?.analysis_plan || [];

    if (Object.keys(capabilities).length > 0) {
      this.stateManager.updatePath("dataset.capabilities", capabilities);
    }
    const hasAnalysisPlan = Array.isArray(analysisPlan)
      ? analysisPlan.length > 0
      : Object.keys(safeObject(analysisPlan)).length > 0;
    if (hasAnalysisPlan) {
      this.stateManager.updatePath("dataset.analysisPlan", analysisPlan);
    }

    return {
      success: true,
      message: "Dashboard bundle loaded.",
      data: {
        dashboard: dashboardResult?.data || {},
        team4: team4Result?.data || {},
        capabilities: capabilityResult?.data || {},
        insights: insightResult?.data || {}
      }
    };
  }
}

export const analyticsService = new AnalyticsService();
