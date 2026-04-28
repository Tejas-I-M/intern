import { Toast } from "../components/Toast.js";

const DEFAULT_BASE_URL = "http://127.0.0.1:5000";

function resolveDefaultBaseUrl() {
  if (typeof window === "undefined") {
    return DEFAULT_BASE_URL;
  }

  const host = String(window.location?.hostname || "127.0.0.1").trim();
  const backendHost = host || "127.0.0.1";
  return `http://${backendHost}:5000`;
}

export class ApiClient {
  constructor(options = {}) {
    this.baseUrl = String(options?.baseUrl || resolveDefaultBaseUrl()).replace(/\/+$/, "");
    this.toast = options?.toastInstance || new Toast();
  }

  buildUrl(path = "/") {
    const normalizedPath = String(path || "/").startsWith("/") ? String(path || "/") : `/${path}`;
    return `${this.baseUrl}${normalizedPath}`;
  }

  shouldSuppressErrorToast(message = "", options = {}) {
    if (Boolean(options?.suppressErrorToast)) {
      return true;
    }

    const text = String(message || "").toLowerCase();
    if (!text) {
      return false;
    }

    // Missing-data module responses should be handled by in-view fallback cards, not global red toasts.
    return (
      text.includes("required columns") ||
      text.includes("column not found") ||
      text.includes("columns not found") ||
      text.includes("no data available") ||
      text.includes("required fields")
    );
  }

  async request(path, options = {}) {
    const method = String(options?.method || "GET").toUpperCase();
    const url = this.buildUrl(path);

    if (typeof fetch !== "function") {
      const message = "Fetch API is not available in this environment.";
      this.toast.show(message, { type: "error" });
      return { success: false, status: 0, message, data: null };
    }

    const headers = new Headers(options?.headers || {});
    let requestBody = options?.body;

    const hasFormData = typeof FormData !== "undefined";
    const hasBlob = typeof Blob !== "undefined";
    const isFormData = hasFormData && requestBody instanceof FormData;
    const isBlob = hasBlob && requestBody instanceof Blob;
    const isSearchParams = requestBody instanceof URLSearchParams;
    const isPlainObject =
      requestBody !== null &&
      typeof requestBody === "object" &&
      !isFormData &&
      !isBlob &&
      !isSearchParams;

    if (isPlainObject) {
      requestBody = JSON.stringify(requestBody);
      if (!headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
      }
    }

    if (!headers.has("Accept")) {
      headers.set("Accept", "application/json");
    }

    const requestOptions = {
      ...options,
      method,
      headers,
      body: requestBody,
      credentials: "include"
    };

    try {
      const response = await fetch(url, requestOptions);
      const payload = await this.parseResponse(response);

      if (!response?.ok) {
        const message =
          payload?.message ||
          payload?.error ||
          `Request failed with status ${response?.status || "unknown"}.`;
        if (!this.shouldSuppressErrorToast(message, options)) {
          this.toast.show(message, { type: "error" });
        }

        return {
          success: false,
          status: response?.status || 0,
          message,
          data: payload
        };
      }

      return {
        success: payload?.success ?? true,
        status: response.status,
        message: payload?.message || "Request completed.",
        data: payload
      };
    } catch (error) {
      const message = `Network error: ${error?.message || "Unable to reach backend."}`;
      this.toast.show(message, { type: "error" });

      return {
        success: false,
        status: 0,
        message,
        data: null,
        error
      };
    }
  }

  async parseResponse(response) {
    if (!response) {
      return null;
    }

    const contentType = response?.headers?.get?.("content-type") || "";

    try {
      if (contentType.includes("application/json")) {
        const rawText = await response.text();
        if (!rawText) {
          return {};
        }

        try {
          return JSON.parse(rawText);
        } catch (_jsonError) {
          const sanitized = String(rawText)
            .replace(/\bNaN\b/g, "null")
            .replace(/\b-Infinity\b/g, "null")
            .replace(/\bInfinity\b/g, "null");

          try {
            return JSON.parse(sanitized);
          } catch (_parseError) {
            return {
              message: "Failed to parse server response.",
              raw: rawText || null,
              error: "parse_error"
            };
          }
        }
      }

      const rawText = await response.text();
      return {
        message: rawText || "Non-JSON response received.",
        raw: rawText
      };
    } catch (error) {
      return {
        message: "Failed to parse server response.",
        raw: null,
        error: error?.message || "parse_error"
      };
    }
  }

  async get(path, options = {}) {
    return this.request(path, { ...options, method: "GET" });
  }

  async post(path, body, options = {}) {
    return this.request(path, { ...options, method: "POST", body });
  }

  async put(path, body, options = {}) {
    return this.request(path, { ...options, method: "PUT", body });
  }

  async patch(path, body, options = {}) {
    return this.request(path, { ...options, method: "PATCH", body });
  }

  async delete(path, options = {}) {
    return this.request(path, { ...options, method: "DELETE" });
  }
}

export const apiClient = new ApiClient();
