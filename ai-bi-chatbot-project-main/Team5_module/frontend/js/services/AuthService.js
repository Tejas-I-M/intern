import { apiClient } from "../core/ApiClient.js";
import { stateManager } from "../core/StateManager.js";

function normalizeString(value) {
  return typeof value === "string" ? value.trim() : "";
}

export class AuthService {
  constructor(options = {}) {
    this.api = options?.apiClient || apiClient;
    this.state = options?.stateManager || stateManager;
  }

  async signup(payload = {}) {
    const firstName = normalizeString(payload?.firstName);
    const lastName = normalizeString(payload?.lastName);
    const email = normalizeString(payload?.email).toLowerCase();
    const password = normalizeString(payload?.password);

    if (!firstName || !lastName || !email || !password) {
      return {
        success: false,
        message: "First name, last name, email, and password are required.",
        user: null
      };
    }

    const response = await this.api.post("/api/auth/signup", {
      firstName,
      lastName,
      email,
      password
    });

    if (!response?.success) {
      return {
        success: false,
        message: response?.message || "Signup failed.",
        user: null
      };
    }

    // Keep signup and login separate as requested: user signs up, then logs in.
    await this.api.post("/api/auth/logout", {});
    this.state.clearAuthSession();

    if (typeof window !== "undefined" && window.sessionStorage) {
      window.sessionStorage.removeItem("nexus-authenticated");
    }

    return {
      success: true,
      message: response?.message || "Signup completed. Please log in.",
      user: null
    };
  }

  async login(payload = {}) {
    const email = normalizeString(payload?.email).toLowerCase();
    const password = normalizeString(payload?.password);

    if (!email || !password) {
      return {
        success: false,
        message: "Email and password are required.",
        user: null
      };
    }

    const response = await this.api.post("/api/auth/login", {
      email,
      password
    });

    if (!response?.success) {
      return {
        success: false,
        message: response?.message || "Login failed.",
        user: null
      };
    }

    const user = this.extractUser(response?.data, { email });
    this.state.setAuthSession(user);

    if (typeof window !== "undefined" && window.sessionStorage) {
      window.sessionStorage.setItem("nexus-authenticated", "1");
    }

    return {
      success: true,
      message: response?.message || "Login successful.",
      user
    };
  }

  async logout() {
    const response = await this.api.post("/api/auth/logout", {});
    this.state.clearAuthSession();
    this.state.clearDatasetContext();

    if (typeof window !== "undefined" && window.sessionStorage) {
      window.sessionStorage.removeItem("nexus-authenticated");
    }

    return {
      success: response?.success ?? true,
      message: response?.message || "Logged out.",
      user: null
    };
  }

  async getProfile() {
    const response = await this.api.get("/api/auth/profile");

    if (!response?.success) {
      return {
        success: false,
        message: response?.message || "Unable to load profile.",
        user: null
      };
    }

    const user = this.extractUser(response?.data, null);
    if (user) {
      this.state.setAuthSession(user);
    }

    return {
      success: true,
      message: response?.message || "Profile loaded.",
      user
    };
  }

  extractUser(data, fallback = null) {
    const userFromResponse =
      data?.user ||
      data?.data?.user ||
      (data?.profile && typeof data.profile === "object" ? data.profile : null);

    const raw = userFromResponse || fallback;

    if (!raw || typeof raw !== "object") {
      return null;
    }

    const firstName = normalizeString(raw?.firstName || raw?.first_name);
    const lastName = normalizeString(raw?.lastName || raw?.last_name);
    const email = normalizeString(raw?.email).toLowerCase();

    return {
      firstName,
      lastName,
      fullName: normalizeString(`${firstName} ${lastName}`),
      email
    };
  }
}

export const authService = new AuthService();
