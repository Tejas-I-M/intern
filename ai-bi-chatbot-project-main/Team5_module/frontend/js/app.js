import { Router } from "./core/Router.js?v=2";
import { stateManager } from "./core/StateManager.js";
import { Toast, toast as sharedToast } from "./components/Toast.js";
import { authService } from "./services/AuthService.js";
import { AuthView } from "./views/AuthView.js";
import { LandingView } from "./views/LandingView.js?v=6";
import { UploadView } from "./views/UploadView.js?v=2";
import { DashboardView } from "./views/DashboardView.js?v=4";
import { AdvancedView } from "./views/AdvancedView.js?v=2";
import { ChatView } from "./views/ChatView.js?v=3";
import { ReportView } from "./views/ReportView.js?v=3";

const toast = sharedToast || new Toast();
const router = new Router({ rootSelector: "#app-root", toastInstance: toast });

function syncThemeToggleLabel(theme) {
  const themeToggle = document.getElementById("theme-toggle");
  const themeControl = themeToggle?.closest?.(".theme-toggle");
  if (!themeToggle || !themeControl) {
    return;
  }

  const isNight = theme === "cyber-dark";
  themeControl.title = isNight ? "Switch to day mode" : "Switch to night mode";
  themeToggle.setAttribute("aria-label", isNight ? "Switch to day mode" : "Switch to night mode");
}

function initThemeToggle() {
  const rawTheme = stateManager.get("ui.theme", "holo-light");
  const currentTheme = rawTheme === "cyber-dark" ? "cyber-dark" : "holo-light";

  if (rawTheme !== currentTheme) {
    stateManager.updatePath("ui.theme", currentTheme);
  }

  if (document?.body) {
    document.body.setAttribute("data-theme", currentTheme);
  }

  const themeToggle = document.getElementById("theme-toggle");
  if (!themeToggle) {
    return;
  }

  themeToggle.checked = currentTheme === "cyber-dark";
  syncThemeToggleLabel(currentTheme);

  setTimeout(() => {
    const restoredTheme = stateManager.get("ui.theme", "holo-light") === "cyber-dark" ? "cyber-dark" : "holo-light";
    themeToggle.checked = restoredTheme === "cyber-dark";
    syncThemeToggleLabel(restoredTheme);
  }, 50);

  themeToggle.addEventListener("change", (event) => {
    if (typeof event.isTrusted === "boolean" && !event.isTrusted) {
      return;
    }

    const cyberEnabled = Boolean(event?.target?.checked);
    const nextTheme = cyberEnabled ? "cyber-dark" : "holo-light";

    document?.body?.setAttribute("data-theme", nextTheme);
    stateManager.updatePath("ui.theme", nextTheme);
    syncThemeToggleLabel(nextTheme);

    toast.show(`${cyberEnabled ? "Night" : "Day"} mode enabled.`, {
      type: "info",
      duration: 1800
    });
  });
}

function renderSessionPill(state) {
  const pill = document.getElementById("session-pill");
  if (!pill) {
    return;
  }

  const isAuthenticated = Boolean(state?.auth?.isAuthenticated);
  const fullName = state?.auth?.user?.fullName;
  const email = state?.auth?.user?.email;

  if (!isAuthenticated) {
    pill.textContent = "";
    pill.hidden = true;
    return;
  }

  pill.hidden = false;
  pill.textContent = fullName || email || "Signed in";
}

function initSessionPill() {
  renderSessionPill(stateManager.getState());
  stateManager.subscribe((nextState) => {
    renderSessionPill(nextState);
  });
}

function syncRouteChrome(state) {
  const path = state?.routing?.currentPath || "/";
  const homeButton = document.getElementById("home-nav-btn");

  if (document?.body) {
    document.body.setAttribute("data-route", path);
  }

  if (homeButton) {
    homeButton.hidden = path !== "/auth";
  }
}

function initRouteChrome() {
  syncRouteChrome(stateManager.getState());
  stateManager.subscribe((nextState) => {
    syncRouteChrome(nextState);
  });
}

function initHomeButton() {
  const homeButton = document.getElementById("home-nav-btn");
  if (!homeButton) {
    return;
  }

  homeButton.addEventListener("click", () => {
    router.navigate("/");
  });
}

function registerRoutes() {
  router.register("/", ({ router: activeRouter, state }) => {
    return new LandingView({
      stateManager,
      router: activeRouter
    });
  });

  router.register("/auth", ({ router: activeRouter }) => {
    return new AuthView({
      authService,
      stateManager,
      router: activeRouter,
      toast
    });
  });

  router.register("/upload", ({ router: activeRouter }) => {
    return new UploadView({
      stateManager,
      router: activeRouter,
      toast
    });
  });

  router.register("/dashboard", ({ router: activeRouter }) => {
    return new DashboardView({
      stateManager,
      router: activeRouter,
      toast
    });
  });

  router.register("/advanced", ({ router: activeRouter }) => {
    return new AdvancedView({
      stateManager,
      router: activeRouter,
      toast
    });
  });

  router.register("/chat", ({ router: activeRouter }) => {
    return new ChatView({
      stateManager,
      router: activeRouter,
      toast
    });
  });

  router.register("/reports", ({ router: activeRouter }) => {
    return new ReportView({
      stateManager,
      router: activeRouter,
      toast
    });
  });
}

async function bootstrap() {
  initThemeToggle();
  initSessionPill();
  initRouteChrome();
  initHomeButton();
  registerRoutes();

  const rememberedSession =
    typeof window !== "undefined" && window.sessionStorage
      ? window.sessionStorage.getItem("nexus-authenticated") === "1"
      : false;

  if (rememberedSession) {
    const profile = await authService.getProfile();
    if (!profile?.success) {
      stateManager.clearAuthSession();
      if (typeof window !== "undefined" && window.sessionStorage) {
        window.sessionStorage.removeItem("nexus-authenticated");
      }
    }
  }

  router.init();
}

if (typeof window !== "undefined" && typeof document !== "undefined") {
  bootstrap();
}
