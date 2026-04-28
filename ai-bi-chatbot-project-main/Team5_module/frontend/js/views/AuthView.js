import { authService as sharedAuthService } from "../services/AuthService.js";
import { stateManager as sharedStateManager } from "../core/StateManager.js";
import { toast as sharedToast } from "../components/Toast.js";

const MODES = {
  LOGIN: "login",
  SIGNUP: "signup"
};

function safeText(value, fallback = "") {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

export class AuthView {
  constructor(options = {}) {
    this.authService = options?.authService || sharedAuthService;
    this.stateManager = options?.stateManager || sharedStateManager;
    this.toast = options?.toast || sharedToast;
    this.router = options?.router || null;

    this.mode = MODES.LOGIN;
    this.host = null;
    this.container = null;
    this.unsubscribe = null;
    this.boundClickHandler = this.handleClick.bind(this);
    this.boundSubmitHandler = this.handleSubmit.bind(this);
  }

  mount(root) {
    if (!root) {
      return () => {};
    }

    this.host = root;
    this.host.innerHTML = this.render();

    this.container = this.host.querySelector(".auth-view");
    if (this.container) {
      this.container.addEventListener("click", this.boundClickHandler);
      this.container.addEventListener("submit", this.boundSubmitHandler);
      this.setMode(this.mode);
    }

    this.syncFromState(this.stateManager.getState());
    this.unsubscribe = this.stateManager.subscribe((nextState) => {
      this.syncFromState(nextState);
    });

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
      this.container = null;
    }

    this.host = null;
  }

  render() {
    return `
      <section class="auth-view glass-card" aria-label="Authentication">
        <div class="auth-pane auth-pane-centered">
          <h2>Welcome Back</h2>

          <div class="auth-mode-switch" role="tablist" aria-label="Auth mode">
            <button
              type="button"
              class="mode-btn is-active"
              data-auth-mode="login"
              role="tab"
              aria-selected="true"
            >Login</button>
            <button
              type="button"
              class="mode-btn"
              data-auth-mode="signup"
              role="tab"
              aria-selected="false"
            >Signup</button>
          </div>

          <p class="auth-status" data-auth-status>
            Login with your email and password.
          </p>

          <form class="auth-form" data-auth-form novalidate>
            <div class="signup-row" data-signup-fields hidden>
              <label>
                <span>First Name</span>
                <input name="firstName" type="text" autocomplete="given-name" maxlength="80">
              </label>
              <label>
                <span>Last Name</span>
                <input name="lastName" type="text" autocomplete="family-name" maxlength="80">
              </label>
            </div>

            <label>
              <span>Email</span>
              <input name="email" type="email" autocomplete="email" required>
            </label>

            <label>
              <span>Password</span>
              <div class="password-wrap">
                <input name="password" data-password-input type="password" autocomplete="current-password" minlength="6" required>
                <button type="button" class="eye-toggle" data-eye-toggle="password" aria-label="Toggle password visibility">Show</button>
              </div>
            </label>

            <label data-confirm-wrap hidden>
              <span>Confirm Password</span>
              <div class="password-wrap">
                <input name="confirmPassword" data-confirm-password-input type="password" autocomplete="new-password" minlength="6">
                <button type="button" class="eye-toggle" data-eye-toggle="confirm" aria-label="Toggle confirm password visibility">Show</button>
              </div>
            </label>

            <button type="submit" class="auth-submit" data-auth-submit>
              Continue
            </button>
          </form>
        </div>
      </section>
    `;
  }

  handleClick(event) {
    const modeTrigger = event?.target?.closest?.("[data-auth-mode]");
    if (!modeTrigger) {
      const eyeToggle = event?.target?.closest?.("[data-eye-toggle]");
      if (!eyeToggle) {
        return;
      }

      const targetType = eyeToggle.getAttribute("data-eye-toggle");
      if (targetType === "confirm") {
        this.togglePasswordVisibility("[data-confirm-password-input]", eyeToggle);
      } else {
        this.togglePasswordVisibility("[data-password-input]", eyeToggle);
      }
      return;
    }

    const nextMode = modeTrigger.getAttribute("data-auth-mode") === MODES.SIGNUP ? MODES.SIGNUP : MODES.LOGIN;
    this.setMode(nextMode);
  }

  async handleSubmit(event) {
    const form = event?.target?.closest?.("[data-auth-form]");
    if (!form) {
      return;
    }

    event.preventDefault();

    const submitButton = form.querySelector("[data-auth-submit]");
    if (submitButton) {
      submitButton.disabled = true;
      submitButton.textContent = "Processing...";
    }

    const formData = typeof FormData !== "undefined" ? new FormData(form) : null;
    const email = safeText(formData?.get("email"));
    const password = safeText(formData?.get("password"));
    const confirmPassword = safeText(formData?.get("confirmPassword"));
    const firstName = safeText(formData?.get("firstName"));
    const lastName = safeText(formData?.get("lastName"));

    let result = { success: false, message: "Unknown error.", user: null };

    try {
      if (!email || !password) {
        result = {
          success: false,
          message: "Email and password are required.",
          user: null
        };
      } else if (this.mode === MODES.SIGNUP) {
        if (!firstName || !lastName) {
          result = {
            success: false,
            message: "First name and last name are required for signup.",
            user: null
          };
        } else if (password !== confirmPassword) {
          result = {
            success: false,
            message: "Password and confirm password must match.",
            user: null
          };
        } else {
          result = await this.authService.signup({
            firstName,
            lastName,
            email,
            password
          });
        }
      } else {
        result = await this.authService.login({
          email,
          password
        });
      }
    } catch (error) {
      result = {
        success: false,
        message: `Auth request failed: ${error?.message || "unknown error"}`,
        user: null
      };
    }

    if (result?.success) {
      this.toast.show(result?.message || "Authenticated.", { type: "success", duration: 1800 });

      if (this.mode === MODES.SIGNUP) {
        this.renderStatus("Signup successful. Please login using your email and password.", "success");
        form.reset();
        this.setMode(MODES.LOGIN);
      } else {
        this.renderStatus(`Welcome ${result?.user?.fullName || result?.user?.email || "User"}.`, "success");

        if (this.router && typeof this.router.navigate === "function") {
          if (typeof window !== "undefined") {
            window.setTimeout(() => {
              this.router.navigate("/upload");
            }, 220);
          } else {
            this.router.navigate("/upload");
          }
        }

        form.reset();
      }
    } else {
      this.toast.show(result?.message || "Authentication failed.", { type: "error", duration: 3200 });
      this.renderStatus(result?.message || "Authentication failed.", "error");
    }

    if (submitButton) {
      submitButton.disabled = false;
      submitButton.textContent = this.mode === MODES.SIGNUP ? "Create Account" : "Continue";
    }
  }

  setMode(nextMode) {
    this.mode = nextMode === MODES.SIGNUP ? MODES.SIGNUP : MODES.LOGIN;

    const signupFields = this.container?.querySelector?.("[data-signup-fields]");
    const confirmWrap = this.container?.querySelector?.("[data-confirm-wrap]");
    const buttons = this.container?.querySelectorAll?.("[data-auth-mode]");
    const submitButton = this.container?.querySelector?.("[data-auth-submit]");
    const firstNameInput = this.container?.querySelector?.('input[name="firstName"]');
    const lastNameInput = this.container?.querySelector?.('input[name="lastName"]');
    const passwordInput = this.container?.querySelector?.("[data-password-input]");
    const confirmInput = this.container?.querySelector?.("[data-confirm-password-input]");

    if (signupFields) {
      signupFields.hidden = this.mode !== MODES.SIGNUP;
    }

    if (confirmWrap) {
      confirmWrap.hidden = this.mode !== MODES.SIGNUP;
    }

    if (buttons?.forEach) {
      buttons.forEach((button) => {
        const buttonMode = button?.getAttribute?.("data-auth-mode") || MODES.LOGIN;
        const isActive = buttonMode === this.mode;
        button.classList.toggle("is-active", isActive);
        button.setAttribute("aria-selected", String(isActive));
      });
    }

    if (submitButton) {
      submitButton.textContent = this.mode === MODES.SIGNUP ? "Create Account" : "Continue";
    }

    if (firstNameInput) {
      firstNameInput.required = this.mode === MODES.SIGNUP;
      firstNameInput.disabled = this.mode !== MODES.SIGNUP;
    }

    if (lastNameInput) {
      lastNameInput.required = this.mode === MODES.SIGNUP;
      lastNameInput.disabled = this.mode !== MODES.SIGNUP;
    }

    if (confirmInput) {
      confirmInput.required = this.mode === MODES.SIGNUP;
      confirmInput.disabled = this.mode !== MODES.SIGNUP;
    }

    if (passwordInput) {
      passwordInput.autocomplete = this.mode === MODES.SIGNUP ? "new-password" : "current-password";
    }

    const message =
      this.mode === MODES.SIGNUP
        ? "Create your account. Confirm password is required."
        : "Login with your email and password.";

    if (passwordInput) {
      passwordInput.value = "";
      passwordInput.type = "password";
    }
    if (confirmInput) {
      confirmInput.value = "";
      confirmInput.type = "password";
    }

    const toggleButtons = this.container?.querySelectorAll?.("[data-eye-toggle]");
    if (toggleButtons?.forEach) {
      toggleButtons.forEach((button) => {
        button.textContent = "Show";
      });
    }

    this.renderStatus(message, "info");
  }

  syncFromState(nextState) {
    const isAuthenticated = Boolean(nextState?.auth?.isAuthenticated);
    const user = nextState?.auth?.user || null;

    if (isAuthenticated && user) {
      this.renderStatus(`Authenticated as ${user?.fullName || user?.email || "user"}.`, "success");
    }
  }

  renderStatus(message, variant = "info") {
    const statusEl = this.container?.querySelector?.("[data-auth-status]");
    if (!statusEl) {
      return;
    }

    statusEl.textContent = safeText(message, "Ready.");
    statusEl.setAttribute("data-variant", variant);
  }

  togglePasswordVisibility(selector, toggleButton) {
    const input = this.container?.querySelector?.(selector);
    if (!input || !toggleButton) {
      return;
    }

    const show = input.type === "password";
    input.type = show ? "text" : "password";
    toggleButton.textContent = show ? "Hide" : "Show";
  }
}
