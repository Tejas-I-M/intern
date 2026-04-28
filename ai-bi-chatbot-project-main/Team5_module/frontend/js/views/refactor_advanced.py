import re

with open('c:/Users/Tejas/Desktop/team9/ai-bi-chatbot-project-main/Team5_module/frontend/js/views/DashboardView.js', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('DashboardView', 'AdvancedView')

new_render = '''render() {
    return \
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
    \;
  }

  setBusy('''

content = re.sub(r'render\(\) \{.*?\n  setBusy\(', new_render, content, flags=re.DOTALL)

with open('c:/Users/Tejas/Desktop/team9/ai-bi-chatbot-project-main/Team5_module/frontend/js/views/AdvancedView.js', 'w', encoding='utf-8') as f:
    f.write(content)
