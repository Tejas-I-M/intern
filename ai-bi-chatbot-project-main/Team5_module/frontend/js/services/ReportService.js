import { apiClient } from "../core/ApiClient.js";
import { stateManager } from "../core/StateManager.js";

function asObject(value) {
  return value && typeof value === "object" ? value : {};
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function safeString(value, fallback = "") {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

export class ReportService {
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

  toAbsoluteUrl(path) {
    const safePath = safeString(path, "");
    if (!safePath) {
      return null;
    }

    if (/^https?:\/\//i.test(safePath) || /^data:/i.test(safePath)) {
      return safePath;
    }

    const baseUrl = safeString(this.api?.baseUrl, "http://127.0.0.1:5000");

    try {
      return new URL(safePath, `${baseUrl.replace(/\/+$/, "")}/`).toString();
    } catch (_error) {
      return null;
    }
  }

  normalizeReportEntry(entry) {
    const payload = asObject(entry);
    const reportId = safeString(payload?.report_id || payload?.reportId, null);
    const fallbackDownloadPath = reportId ? `/api/analysis/report-download/${encodeURIComponent(reportId)}/pdf` : "";

    return {
      reportId,
      fileId: safeString(payload?.file_id || payload?.fileId, null),
      datasetName: safeString(payload?.dataset_name || payload?.datasetName, "Dataset"),
      createdAt: safeString(payload?.created_at || payload?.createdAt, ""),
      previewUrl: this.toAbsoluteUrl(payload?.preview_url || payload?.previewUrl),
      downloadPdfUrl: this.toAbsoluteUrl(payload?.download_pdf_url || payload?.downloadPdfUrl || fallbackDownloadPath),
      downloadFormat: safeString(payload?.download_format || payload?.downloadFormat, "pdf")
    };
  }

  async askQuestion(fileId, question, options = {}) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return {
        success: false,
        message: "Dataset file_id is missing. Analyze a dataset first.",
        data: null
      };
    }

    const prompt = safeString(question, "");
    if (!prompt) {
      return {
        success: false,
        message: "Question cannot be empty.",
        data: null
      };
    }

    const useGemini = Boolean(options?.useGemini);

    let response = null;
    try {
      response = await this.api.post(`/api/analysis/chat/${encodeURIComponent(activeFileId)}`, {
        question: prompt,
        use_gemini: useGemini
      });
    } catch (error) {
      return {
        success: false,
        message: `Chat request failed: ${error?.message || "unknown error"}`,
        data: null
      };
    }

    if (!response?.success) {
      return {
        success: false,
        message: response?.message || "Chat request failed.",
        data: response?.data || null
      };
    }

    const payload = asObject(response?.data);

    return {
      success: true,
      message: payload?.message || response?.message || "Answer received.",
      data: {
        answer: safeString(payload?.answer, "No answer returned."),
        confidence: Number(payload?.confidence || 0),
        source: safeString(payload?.source, "unknown"),
        intent: safeString(payload?.intent, "unknown")
      }
    };
  }

  async getPredefinedQuestions() {
    let response = null;

    try {
      response = await this.api.get("/api/analysis/predefined-questions");
    } catch (error) {
      return {
        success: false,
        message: `Unable to load predefined questions: ${error?.message || "unknown error"}`,
        data: []
      };
    }

    if (!response?.success) {
      return {
        success: false,
        message: response?.message || "Unable to load predefined questions.",
        data: []
      };
    }

    const payload = asObject(response?.data);
    const questions = asArray(payload?.questions)
      .map((item) => safeString(item, ""))
      .filter(Boolean);

    return {
      success: true,
      message: payload?.message || response?.message || "Predefined questions loaded.",
      data: questions
    };
  }

  async generateReport(fileId = null, options = {}) {
    const activeFileId = this.getActiveFileId(fileId);
    if (!activeFileId) {
      return {
        success: false,
        message: "Dataset file_id is missing. Analyze dataset first.",
        data: null
      };
    }

    const selectedAdvancedModules = asArray(options?.selectedAdvancedModules)
      .map((item) => safeString(item, ""))
      .filter(Boolean);

    const requestBody = {
      include_advanced_modules: options?.includeAdvancedModules !== false,
      selected_advanced_modules: selectedAdvancedModules
    };

    let response = null;
    try {
      response = await this.api.post(`/api/analysis/generate-report/${encodeURIComponent(activeFileId)}`, requestBody);
    } catch (error) {
      return {
        success: false,
        message: `Report generation failed: ${error?.message || "unknown error"}`,
        data: null
      };
    }

    if (!response?.success) {
      return {
        success: false,
        message: response?.message || "Report generation failed.",
        data: response?.data || null
      };
    }

    const payload = asObject(response?.data);
    const normalized = this.normalizeReportEntry(payload);

    this.stateManager.updatePath("reports.latest", normalized);

    return {
      success: true,
      message: payload?.message || response?.message || "Report generated.",
      data: normalized
    };
  }

  async getReportHistory() {
    let response = null;

    try {
      response = await this.api.get("/api/analysis/reports");
    } catch (error) {
      return {
        success: false,
        message: `Unable to load report history: ${error?.message || "unknown error"}`,
        data: []
      };
    }

    if (!response?.success) {
      return {
        success: false,
        message: response?.message || "Unable to load report history.",
        data: []
      };
    }

    const payload = asObject(response?.data);
    const reports = asArray(payload?.reports).map((item) => this.normalizeReportEntry(item));

    this.stateManager.updatePath("reports.history", reports);

    return {
      success: true,
      message: payload?.message || response?.message || "Report history loaded.",
      data: reports
    };
  }
}

export const reportService = new ReportService();
