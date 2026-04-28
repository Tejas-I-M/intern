import { stateManager as sharedStateManager } from "../core/StateManager.js";

const FEATURES = [
  {
    title: "Dataset Upload",
    body: "Bring CSV, Excel, JSON, or parquet files into the analytics flow."
  },
  {
    title: "Smart Column Mapping",
    body: "Review detected fields before the system prepares your analysis."
  },
  {
    title: "KPI Dashboard",
    body: "Explore revenue, customer, and product performance in one workspace."
  },
  {
    title: "Advanced Analytics",
    body: "Run forecasting, churn, segmentation, cohort, and geographic insights."
  },
  {
    title: "AI Chat Assistant",
    body: "Ask business questions in plain language after analysis is complete."
  },
  {
    title: "Report Generation",
    body: "Create downloadable summaries for sharing insights with your team."
  }
];

const STEPS = [
  {
    title: "Sign in securely",
    body: "Create an account or login so your workspace can be prepared."
  },
  {
    title: "Upload your dataset",
    body: "Choose a supported business dataset and give it an optional name."
  },
  {
    title: "Confirm mapping",
    body: "Check the preview and verify important columns like date and amount."
  },
  {
    title: "Run analysis",
    body: "Start the analytics engine after upload and mapping are ready."
  },
  {
    title: "Explore insights",
    body: "Use dashboards, advanced modules, chat, and reports to understand results."
  }
];

export class LandingView {
  constructor(options = {}) {
    this.router = options?.router || null;
    this.stateManager = options?.stateManager || sharedStateManager;
    this.host = null;
    this.container = null;
    this.scrollButtons = [];
    this.boundClickHandler = this.handleClick.bind(this);
    this.boundScrollHandler = this.handleScrollClick.bind(this);
  }

  mount(root) {
    if (!root) {
      return () => {};
    }

    this.host = root;
    this.host.innerHTML = this.render();
    this.container = this.host.querySelector(".landing-view");

    if (this.container) {
      this.container.addEventListener("click", this.boundClickHandler);
      this.scrollButtons = Array.from(this.container.querySelectorAll("[data-scroll-target]"));
      this.scrollButtons.forEach((button) => {
        button.addEventListener("click", this.boundScrollHandler);
      });
    }

    return () => this.unmount();
  }

  unmount() {
    if (this.container) {
      this.container.removeEventListener("click", this.boundClickHandler);
      this.scrollButtons.forEach((button) => {
        button.removeEventListener("click", this.boundScrollHandler);
      });
      this.scrollButtons = [];
      this.container = null;
    }

    this.host = null;
  }

  render() {
    return `
      <section class="landing-view" aria-label="Nexus AI Analytics landing page">
        <div class="landing-hero">
          <div class="landing-copy">
            <p class="landing-kicker">Business intelligence with AI guidance</p>
            <h2>Nexus AI Analytics Platform</h2>
            <p class="landing-lead">
              Upload your dataset, map the important columns, run analytics, and turn results into dashboards, chat answers, and reports.
            </p>

            <div class="landing-actions" aria-label="Landing actions">
              <button type="button" class="auth-submit" data-route="${this.getPrimaryRoute()}">
                Get Started
              </button>
              <button type="button" class="ghost-btn" data-scroll-target="landing-features">
                View Features
              </button>
            </div>
          </div>

          <aside class="landing-preview glass-card" aria-label="Analytics preview">
            <div class="preview-topline" aria-label="Live analytics loading">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <div class="preview-products">
              <h3>Top performing products:</h3>
              <div class="preview-chart" aria-hidden="true">
                <span style="height: 92%"></span>
                <span style="height: 82%"></span>
                <span style="height: 72%"></span>
                <span style="height: 64%"></span>
                <span style="height: 56%"></span>
                <span style="height: 48%"></span>
              </div>
            </div>
          </aside>
        </div>

        <section id="landing-features" class="landing-section" aria-labelledby="features-title">
          <div class="landing-section-head">
            <p class="landing-kicker">Features</p>
            <h2 id="features-title">What the platform helps you do</h2>
          </div>

          <div class="feature-grid">
            ${FEATURES.map((feature, index) => `
              <article class="feature-card glass-card">
                <span class="feature-number">${String(index + 1).padStart(2, "0")}</span>
                <h3>${feature.title}</h3>
                <p>${feature.body}</p>
              </article>
            `).join("")}
          </div>
        </section>

        <section class="landing-section how-section" aria-labelledby="steps-title">
          <div class="landing-section-head">
            <p class="landing-kicker">How to use</p>
            <h2 id="steps-title">Analyze only after signing in and uploading</h2>
          </div>

          <div class="steps-list">
            ${STEPS.map((step, index) => `
              <article class="step-row">
                <span>${index + 1}</span>
                <div>
                  <h3>${step.title}</h3>
                  <p>${step.body}</p>
                </div>
              </article>
            `).join("")}
          </div>
        </section>

        <section class="landing-cta glass-card" aria-label="Start using Nexus AI Analytics">
          <div>
            <p class="landing-kicker">Ready when your data is</p>
            <h2>Start with login, then upload before analysis.</h2>
          </div>
          <button type="button" class="auth-submit" data-route="${this.getPrimaryRoute()}">
            Continue
          </button>
        </section>
      </section>
    `;
  }

  getPrimaryRoute() {
    const isAuthenticated = Boolean(this.stateManager.get("auth.isAuthenticated", false));
    return isAuthenticated ? "/upload" : "/auth";
  }

  scrollToTarget(targetId) {
    const target = targetId ? this.container?.querySelector?.(`#${targetId}`) : null;
    if (!target || typeof window === "undefined") {
      return;
    }

    const scrollContainer = this.host || document.scrollingElement || document.documentElement;

    const calculateTop = () => {
      const containerRect = scrollContainer.getBoundingClientRect?.() || { top: 0 };
      return Math.max(
        0,
        target.getBoundingClientRect().top -
          containerRect.top +
          Number(scrollContainer.scrollTop || 0) -
          14
      );
    };

    const scrollNow = (behavior = "smooth") => {
      const top = calculateTop();
      if (typeof scrollContainer.scrollTo === "function") {
        scrollContainer.scrollTo({ top, left: 0, behavior });
      } else {
        scrollContainer.scrollTop = top;
        scrollContainer.scrollLeft = 0;
      }
    };

    scrollNow("smooth");

    window.setTimeout(() => {
      const containerRect = scrollContainer.getBoundingClientRect?.() || { top: 0 };
      const targetGap = Math.abs(target.getBoundingClientRect().top - containerRect.top - 14);
      if (targetGap > 24) {
        scrollNow("auto");
      }
    }, 280);
  }

  handleScrollClick(event) {
    event?.preventDefault?.();
    event?.stopPropagation?.();
    const scrollTrigger = event?.currentTarget;
    const targetId = scrollTrigger?.getAttribute?.("data-scroll-target");
    this.scrollToTarget(targetId);
  }

  handleClick(event) {
    const routeTrigger = event?.target?.closest?.("[data-route]");
    if (routeTrigger) {
      const targetRoute = routeTrigger.getAttribute("data-route") || "/auth";
      if (this.router && typeof this.router.navigate === "function") {
        this.router.navigate(targetRoute);
      }
      return;
    }

    const scrollTrigger = event?.target?.closest?.("[data-scroll-target]");
    if (!scrollTrigger) {
      return;
    }

    event?.preventDefault?.();
    this.scrollToTarget(scrollTrigger.getAttribute("data-scroll-target"));
  }
}
