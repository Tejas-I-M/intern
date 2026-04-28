const fs = require('fs');
const file = 'c:/Users/Tejas/Desktop/team9/ai-bi-chatbot-project-main/Team5_module/frontend/js/views/AdvancedView.js';
let content = fs.readFileSync(file, 'utf8');

content = content.replace(/DashboardView/g, 'AdvancedView');
content = content.replace(/import \{ Sidebar \} from "\.\.\/components\/Sidebar\.js";/, 'import { Sidebar } from "../components/Sidebar.js";\ntype AdvancedViewProps = { stateManager: any; router: any; toast: any; };');

const newRender = \ender() {
    return \\\
      <section class="dashboard-view dashboard-grid" aria-label="Advanced Analytics">
        <div data-sidebar-mount class="sidebar-slot"></div>

        <article class="dashboard-main glass-card">
          <header class="dashboard-head">
            <h2>Advanced Analytics Summary</h2>
            <p>Deep dive into cohort, health score, products, timeseries, and predictive models.</p>
          </header>

          <p class="upload-status" data-dashboard-status data-variant="info">
            Upload dataset and run analysis to view advanced modules.
          </p>

          <div class="dashboard-actions">
            <button type="button" class="ghost-btn" data-load-advanced>Load Advanced Modules</button>
            <button type="button" class="ghost-btn" data-go-report>Go to Report</button>
          </div>

          <section class="dashboard-sections" data-dashboard-sections>
            <article class="dash-card dash-card-wide">
              <p class="table-empty" data-advanced-summary>
                Click 'Load Advanced Modules' to view.
              </p>
              <div class="advanced-modules" data-advanced-modules></div>
              <div class="module-output" data-advanced-output>
                <p class="table-empty">No module selected.</p>
              </div>
            </article>
          </section>
        </article>
      </section>
    \\\;
  }\;
// replace the entire render function block
content = content.replace(/render\(\) \{[\s\S]*?\}\n\s+setBusy\(/g, newRender + '\n\n  setBusy(');

content = content.replace(/this\.updateTopProducts\(dashboardInfo\.top_products\);/g, '');
content = content.replace(/this\.updateMonthlyRevenue\(dashboardInfo\.monthly_trend\);/g, '');
content = content.replace(/this\.updateSegmentDistribution\(dashboardInfo\.segment_distribution\);/g, '');
content = content.replace(/this\.updateBasicStats\(dashboardInfo\);/g, '');

fs.writeFileSync(file, content, 'utf8');
