const fs = require('fs');
const acorn = require('acorn');

const dashCode = fs.readFileSync('c:/Users/Tejas/Desktop/team9/ai-bi-chatbot-project-main/Team5_module/frontend/js/views/DashboardView.js', 'utf8');

const newRender = `render() {
    return \`
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
            <!-- user asked: when i click load advanced modules it should directly automatically take me to the advanced summary page without me clicking -->
            <!-- We will auto load if on this page, but we keep the button if they want to reload -->
            <button type="button" class="ghost-btn" data-load-advanced>Reload Modules</button>
            <button type="button" class="ghost-btn" data-go-report>Go to Report</button>
          </div>

          <section class="dashboard-sections" data-dashboard-sections>
            <article class="dash-card dash-card-wide">
              <p class="table-empty" data-advanced-summary>
                Fetching modules...
              </p>
              <div class="advanced-modules" data-advanced-modules></div>
              <div class="module-output" data-advanced-output>
                <p class="table-empty">No module selected.</p>
              </div>
            </article>
          </section>
        </article>
      </section>
    \`;
  }`;

const ast = acorn.parse(dashCode, {sourceType: 'module', ecmaVersion: 'latest', ranges: true});
const exportDecl = ast.body.find(n => n.type === 'ExportNamedDeclaration' && n.declaration.id.name === 'DashboardView');
const classBody = exportDecl.declaration.body.body;

const renderMethod = classBody.find(m => m.key.name === 'render');

let advancedCode = dashCode.slice(0, renderMethod.range[0]) + newRender + dashCode.slice(renderMethod.range[1]);

// Replace class definition
advancedCode = advancedCode.replace(/class DashboardView\b/, 'class AdvancedView');

// Also, the user wants the advanced page to auto-load modules the moment it opens
// Let's modify the tryAutoload method of AdvancedView
advancedCode = advancedCode.replace(
  /tryAutoload\(\) \{[\s\S]*?\}\n/,
  `tryAutoload() {
    const fileId = this.stateManager.get("dataset.fileId", null);
    if (!fileId) return;

    // Call load advanced modules directly if we have a file ID
    this.loadAdvancedModules();
  }\n`
);

fs.writeFileSync('c:/Users/Tejas/Desktop/team9/ai-bi-chatbot-project-main/Team5_module/frontend/js/views/AdvancedView.js', advancedCode);
console.log("AdvancedView replaced successfully.");
