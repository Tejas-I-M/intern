import { apiClient } from "../core/ApiClient.js";
import { stateManager } from "../core/StateManager.js";

const MAX_UPLOAD_BYTES = 30 * 1024 * 1024;
const SUPPORTED_EXTENSIONS = [".csv", ".xlsx", ".xls", ".json", ".parquet"];

function normalizeName(value) {
  return typeof value === "string" ? value.trim() : "";
}

function getExtension(fileName) {
  const safe = normalizeName(fileName).toLowerCase();
  const index = safe.lastIndexOf(".");
  return index >= 0 ? safe.slice(index) : "";
}

export class DataService {
  constructor(options = {}) {
    this.api = options?.apiClient || apiClient;
    this.state = options?.stateManager || stateManager;
    this.maxUploadBytes = Number(options?.maxUploadBytes) > 0 ? Number(options.maxUploadBytes) : MAX_UPLOAD_BYTES;
  }

  validateUploadFile(file) {
    if (!file) {
      return { valid: false, message: "Please choose a dataset file first." };
    }

    const hasFileCtor = typeof File !== "undefined";
    if (hasFileCtor && !(file instanceof File)) {
      return { valid: false, message: "Invalid file object provided." };
    }

    const extension = getExtension(file?.name || "");
    if (!SUPPORTED_EXTENSIONS.includes(extension)) {
      return {
        valid: false,
        message: "Unsupported file type. Use csv, xlsx, xls, json, or parquet."
      };
    }

    if (Number(file?.size || 0) > this.maxUploadBytes) {
      return {
        valid: false,
        message: `File is too large. Max size is ${Math.round(this.maxUploadBytes / (1024 * 1024))}MB.`
      };
    }

    return { valid: true, message: "File ready." };
  }

  async uploadDataset(file, options = {}) {
    const validation = this.validateUploadFile(file);
    if (!validation?.valid) {
      return {
        success: false,
        message: validation?.message || "Invalid upload file.",
        fileId: null,
        capabilities: {}
      };
    }

    const formData = new FormData();
    const datasetName = normalizeName(options?.datasetName);

    formData.append("file", file, file?.name || "dataset.csv");
    if (datasetName) {
      formData.append("dataset_name", datasetName);
    }

    let response = null;
    try {
      response = await this.api.post("/api/analysis/upload", formData);
    } catch (error) {
      return {
        success: false,
        message: `Upload request failed: ${error?.message || "unknown error"}`,
        fileId: null,
        capabilities: {}
      };
    }

    if (!response?.success) {
      return {
        success: false,
        message: response?.message || "Upload failed.",
        fileId: null,
        capabilities: {}
      };
    }

    const payload = response?.data || {};
    const fileId = payload?.file_id || payload?.fileId || null;
    const capabilities = typeof payload?.capabilities === "object" && payload?.capabilities ? payload.capabilities : {};

    if (!fileId) {
      return {
        success: false,
        message: "Upload succeeded but file identifier is missing.",
        fileId: null,
        capabilities
      };
    }

    this.state.setDatasetContext(fileId, capabilities);
    this.state.updatePath("dataset.mode", payload?.mode || "unknown");
    this.state.updatePath("dataset.analysisPlan", payload?.analysis_plan || []);
    this.state.updatePath("dataset.mappedColumns", payload?.mapped_columns || {});
    this.state.updatePath("dataset.preview", payload?.preview || []);

    return {
      success: true,
      message: payload?.message || "Dataset uploaded successfully.",
      fileId,
      capabilities,
      mode: payload?.mode || "unknown",
      analysisPlan: payload?.analysis_plan || [],
      preview: payload?.preview || []
    };
  }

  async getDatasetPreview(fileId, rows = 10) {
    const activeFileId = normalizeName(fileId);
    if (!activeFileId) {
      return {
        success: false,
        message: "file_id is required for preview.",
        data: null
      };
    }

    const safeRows = Math.max(1, Math.min(Number(rows) || 10, 50));

    const response = await this.api.get(
      `/api/analysis/preview/${encodeURIComponent(activeFileId)}?rows=${safeRows}`
    );

    if (!response?.success) {
      return {
        success: false,
        message: response?.message || "Unable to load dataset preview.",
        data: null
      };
    }

    return {
      success: true,
      message: response?.message || "Preview loaded.",
      data: response?.data || {}
    };
  }

  async getMappingSuggestions(fileId) {
    const activeFileId = normalizeName(fileId);
    if (!activeFileId) {
      return {
        success: false,
        message: "file_id is required for mapping suggestions.",
        data: {}
      };
    }

    const response = await this.api.get(
      `/api/analysis/mapping-suggestions/${encodeURIComponent(activeFileId)}`
    );

    if (!response?.success) {
      return {
        success: false,
        message: response?.message || "Unable to load mapping suggestions.",
        data: {}
      };
    }

    return {
      success: true,
      message: response?.message || "Mapping suggestions loaded.",
      data: response?.data || {}
    };
  }

  async applyMapping(fileId, mapping = {}) {
    const activeFileId = normalizeName(fileId);
    if (!activeFileId) {
      return {
        success: false,
        message: "file_id is required for remapping.",
        data: null
      };
    }

    if (!mapping || typeof mapping !== "object") {
      return {
        success: false,
        message: "A valid mapping object is required.",
        data: null
      };
    }

    const response = await this.api.post(
      `/api/analysis/remap/${encodeURIComponent(activeFileId)}`,
      { mapping }
    );

    if (!response?.success) {
      return {
        success: false,
        message: response?.message || "Mapping update failed.",
        data: response?.data || null
      };
    }

    const payload = response?.data || {};
    this.state.updatePath("dataset.mappedColumns", payload?.mapped_columns || {});
    this.state.updatePath("dataset.capabilities", payload?.capabilities || {});
    this.state.updatePath("dataset.analysisPlan", payload?.analysis_plan || {});
    this.state.markAnalysisComplete(false);

    return {
      success: true,
      message: payload?.message || "Mapping updated.",
      data: payload
    };
  }
}

export const dataService = new DataService();
