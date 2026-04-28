import { dataService as sharedDataService } from "../services/DataService.js";
import { stateManager as sharedStateManager } from "../core/StateManager.js";
import { toast as sharedToast } from "../components/Toast.js";
import { Sidebar } from "../components/Sidebar.js";

const CANONICAL_FIELDS = ["Date", "Total Amount", "Customer ID", "Product Category"];
const AUTO_DETECT_VALUE = "__auto_detect_all_columns__";

function formatBytes(bytes) {
  const size = Number(bytes || 0);
  if (!size || size < 0) {
    return "0 KB";
  }

  const units = ["B", "KB", "MB", "GB"];
  let value = size;
  let index = 0;

  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }

  return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function sanitizeText(value, fallback = "") {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function truncateLabel(value, maxLength = 42) {
  const safe = String(value ?? "");
  if (safe.length <= maxLength) {
    return safe;
  }
  return `${safe.slice(0, Math.max(0, maxLength - 3))}...`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export class UploadView {
  constructor(options = {}) {
    this.router = options?.router || null;
    this.dataService = options?.dataService || sharedDataService;
    this.stateManager = options?.stateManager || sharedStateManager;
    this.toast = options?.toast || sharedToast;

    this.host = null;
    this.container = null;
    this.sidebar = null;
    this.selectedFile = null;
    this.unsubscribe = null;

    this.isBusy = false;
    this.preview = null;
    this.mappingSuggestions = {};
    this.mappingModel = {};
    this.sourceColumns = [];
    this.previewLoadInFlight = null;

    this.boundClickHandler = this.handleClick.bind(this);
    this.boundChangeHandler = this.handleChange.bind(this);
    this.boundSubmitHandler = this.handleSubmit.bind(this);
    this.boundDragOverHandler = this.handleDragOver.bind(this);
    this.boundDragLeaveHandler = this.handleDragLeave.bind(this);
    this.boundDropHandler = this.handleDrop.bind(this);
  }

  mount(root) {
    if (!root) {
      return () => {};
    }

    this.host = root;
    this.host.innerHTML = this.render();
    this.container = this.host.querySelector(".upload-view");

    const sidebarHost = this.host.querySelector("[data-sidebar-mount]");
    this.sidebar = new Sidebar({
      router: this.router,
      stateManager: this.stateManager,
      toast: this.toast
    });

    if (sidebarHost) {
      this.sidebar.mount(sidebarHost);
    }

    if (this.container) {
      this.container.addEventListener("click", this.boundClickHandler);
      this.container.addEventListener("change", this.boundChangeHandler);
      this.container.addEventListener("submit", this.boundSubmitHandler);
      this.container.addEventListener("dragover", this.boundDragOverHandler);
      this.container.addEventListener("dragleave", this.boundDragLeaveHandler);
      this.container.addEventListener("drop", this.boundDropHandler);
    }

    this.syncState(this.stateManager.getState());
    this.unsubscribe = this.stateManager.subscribe((nextState) => {
      this.syncState(nextState);
    });

    const existingFileId = this.stateManager.get("dataset.fileId", null);
    if (existingFileId) {
      this.loadPreviewAndMapping(existingFileId);
    }

    return () => this.unmount();
  }

  unmount() {
    if (typeof this.unsubscribe === "function") {
      this.unsubscribe();
      this.unsubscribe = null;
    }

    if (this.container) {
      this.container.removeEventListener("click", this.boundClickHandler);
      this.container.removeEventListener("change", this.boundChangeHandler);
      this.container.removeEventListener("submit", this.boundSubmitHandler);
      this.container.removeEventListener("dragover", this.boundDragOverHandler);
      this.container.removeEventListener("dragleave", this.boundDragLeaveHandler);
      this.container.removeEventListener("drop", this.boundDropHandler);
      this.container = null;
    }

    if (this.sidebar) {
      this.sidebar.unmount();
      this.sidebar = null;
    }

    this.selectedFile = null;
    this.host = null;
  }

  render() {
    return `
      <section class="upload-view app-grid" aria-label="Dataset upload and mapping">
        <div data-sidebar-mount class="sidebar-slot"></div>

        <article class="upload-main glass-card">
          <header class="upload-head">
            <h2>Upload Dataset</h2>
            <p>Upload, preview, adjust mapping, then run analysis.</p>
          </header>

          <p class="upload-status" data-upload-status data-variant="info">
            Sign in, upload your file, and prepare mapping.
          </p>

          <section class="drop-zone" data-drop-zone>
            <input
              id="dataset-file-input"
              data-file-input
              type="file"
              accept=".csv,.xlsx,.xls,.json,.parquet"
              hidden
            >

            <p class="drop-title">Drag and drop dataset here</p>
            <p class="drop-sub">or</p>
            <button type="button" class="ghost-btn" data-upload-pick>Choose File</button>
            <p class="drop-file" data-file-name>No file selected</p>
          </section>

          <form class="upload-form" data-upload-form novalidate>
            <label>
              <span>Dataset Name (optional)</span>
              <input
                name="datasetName"
                type="text"
                maxlength="120"
                placeholder="Retail Q1"
              >
            </label>

            <div class="upload-actions">
              <button type="submit" class="auth-submit" data-upload-submit>
                Upload Dataset
              </button>
              <button type="button" class="ghost-btn" data-clear-file>
                Clear Selection
              </button>
            </div>
          </form>

          <section class="mapping-block" data-mapping-block hidden>
            <div class="mapping-head">
              <h3>Preview + Mapping</h3>
              <p>Verify columns before analysis.</p>
            </div>

            <div class="preview-table-wrap" data-preview-table></div>

            <div class="mapping-grid" data-mapping-grid></div>

            <div class="mapping-actions">
              <button type="button" class="ghost-btn" data-apply-mapping>Apply Mapping</button>
              <button type="button" class="auth-submit" data-start-analysis>Analyze Dataset</button>
            </div>
          </section>

          <button type="button" class="inline-link" data-go-auth hidden>
            Go to Login
          </button>
        </article>
      </section>
    `;
  }

  handleClick(event) {
    const pickFileButton = event?.target?.closest?.("[data-upload-pick]");
    if (pickFileButton) {
      const input = this.container?.querySelector?.("[data-file-input]");
      if (input && !input.disabled) {
        input.click();
      }
      return;
    }

    const clearButton = event?.target?.closest?.("[data-clear-file]");
    if (clearButton) {
      this.clearSelection();
      return;
    }

    const authButton = event?.target?.closest?.("[data-go-auth]");
    if (authButton && this.router && typeof this.router.navigate === "function") {
      this.router.navigate("/auth");
      return;
    }

    const applyMappingButton = event?.target?.closest?.("[data-apply-mapping]");
    if (applyMappingButton) {
      this.applyMapping();
      return;
    }

    const analyzeButton = event?.target?.closest?.("[data-start-analysis]");
    if (analyzeButton) {
      this.startAnalysisFlow();
    }
  }

  handleChange(event) {
    const fileInput = event?.target?.closest?.("[data-file-input]");
    if (fileInput) {
      const nextFile = fileInput?.files?.[0] || null;
      if (nextFile) {
        this.setSelectedFile(nextFile);
      }
      return;
    }

    const mappingSelect = event?.target?.closest?.("[data-map-role]");
    if (mappingSelect) {
      const role = mappingSelect.getAttribute("data-map-role") || "";
      const sourceCol = sanitizeText(mappingSelect.value, "");
      if (role) {
        this.mappingModel[role] = sourceCol || AUTO_DETECT_VALUE;
      }
    }
  }

  async handleSubmit(event) {
    const form = event?.target?.closest?.("[data-upload-form]");
    if (!form) {
      return;
    }

    event.preventDefault();

    const isAuthenticated = Boolean(this.stateManager.get("auth.isAuthenticated", false));
    if (!isAuthenticated) {
      this.renderStatus("Please login first before uploading.", "error");
      this.toast.show("Authentication required before upload.", { type: "error" });
      const authBtn = this.container?.querySelector?.("[data-go-auth]");
      if (authBtn) {
        authBtn.hidden = false;
      }
      return;
    }

    if (!this.selectedFile) {
      this.renderStatus("Please choose a dataset file.", "error");
      this.toast.show("No file selected.", { type: "error" });
      return;
    }

    this.setBusy(true, "Uploading...");

    const formData = typeof FormData !== "undefined" ? new FormData(form) : null;
    const datasetName = sanitizeText(formData?.get("datasetName"));

    let result = { success: false, message: "Upload failed.", fileId: null };

    try {
      result = await this.dataService.uploadDataset(this.selectedFile, { datasetName });
    } catch (error) {
      result = {
        success: false,
        message: `Upload failed: ${error?.message || "unknown error"}`,
        fileId: null
      };
    }

    if (result?.success) {
      this.preview = result?.preview || null;
      this.sourceColumns = this.stateManager.get("dataset.sourceColumns", []);
      this.renderStatus("Dataset uploaded. Loading preview and mapping suggestions...", "success");
      this.toast.show("Upload complete.", { type: "success", duration: 1600 });

      await this.loadPreviewAndMapping(result.fileId);

      form.reset();
      this.selectedFile = null;
      this.updateSelectedFileLabel();
    } else {
      this.renderStatus(result?.message || "Upload failed.", "error");
      this.toast.show(result?.message || "Upload failed.", { type: "error", duration: 3000 });
    }

    this.setBusy(false);
  }

  handleDragOver(event) {
    const dropZone = event?.target?.closest?.("[data-drop-zone]");
    if (!dropZone) {
      return;
    }

    event.preventDefault();
    dropZone.classList.add("is-dragging");
  }

  handleDragLeave(event) {
    const dropZone = event?.target?.closest?.("[data-drop-zone]");
    if (!dropZone) {
      return;
    }

    const relatedTarget = event?.relatedTarget;
    if (relatedTarget && dropZone.contains(relatedTarget)) {
      return;
    }

    dropZone.classList.remove("is-dragging");
  }

  handleDrop(event) {
    const dropZone = event?.target?.closest?.("[data-drop-zone]");
    if (!dropZone) {
      return;
    }

    event.preventDefault();
    dropZone.classList.remove("is-dragging");

    const droppedFile = event?.dataTransfer?.files?.[0] || null;
    if (!droppedFile) {
      this.toast.show("Dropped data did not contain a file.", { type: "error" });
      return;
    }

    this.setSelectedFile(droppedFile);
  }

  setSelectedFile(file) {
    const validation = this.dataService.validateUploadFile(file);
    if (!validation?.valid) {
      this.toast.show(validation?.message || "Invalid file.", { type: "error" });
      this.renderStatus(validation?.message || "Invalid file.", "error");
      this.clearSelection();
      return;
    }

    this.selectedFile = file;
    this.updateSelectedFileLabel();
    this.renderStatus("File selected. Click upload.", "info");
  }

  clearSelection() {
    this.selectedFile = null;

    const fileInput = this.container?.querySelector?.("[data-file-input]");
    if (fileInput) {
      fileInput.value = "";
    }

    this.updateSelectedFileLabel();
    this.renderStatus("Selection cleared.", "info");
  }

  updateSelectedFileLabel() {
    const label = this.container?.querySelector?.("[data-file-name]");
    if (!label) {
      return;
    }

    if (!this.selectedFile) {
      label.textContent = "No file selected";
      return;
    }

    label.textContent = `${this.selectedFile?.name || "dataset"} (${formatBytes(this.selectedFile?.size)})`;
  }

  async loadPreviewAndMapping(fileId) {
    const activeFileId = sanitizeText(fileId || this.stateManager.get("dataset.fileId", ""), "");
    if (!activeFileId) {
      return;
    }

    if (this.previewLoadInFlight === activeFileId) {
      return;
    }

    this.previewLoadInFlight = activeFileId;

    this.setBusy(true, "Loading preview...");

    try {
      const [previewResult, mappingResult] = await Promise.all([
        this.dataService.getDatasetPreview(activeFileId, 8),
        this.dataService.getMappingSuggestions(activeFileId)
      ]);

      if (previewResult?.success) {
        this.preview = previewResult?.data?.preview || this.preview;
      }

      if (mappingResult?.success) {
        this.mappingSuggestions = mappingResult?.data?.suggestions || {};
        this.sourceColumns =
          mappingResult?.data?.source_columns ||
          this.preview?.columns ||
          this.stateManager.get("dataset.sourceColumns", []);

        const mapped = mappingResult?.data?.mapped_columns || this.stateManager.get("dataset.mappedColumns", {});
        this.mappingModel = { ...mapped };
      }

      this.renderPreviewTable();
      this.renderMappingGrid();

      const mappingBlock = this.container?.querySelector?.("[data-mapping-block]");
      if (mappingBlock) {
        mappingBlock.hidden = false;
      }

      this.renderStatus("Preview and mapping are ready.", "success");
    } catch (error) {
      this.renderStatus(`Unable to load preview/mapping: ${error?.message || "unknown error"}`, "error");
    } finally {
      if (this.previewLoadInFlight === activeFileId) {
        this.previewLoadInFlight = null;
      }
      this.setBusy(false);
    }
  }

  renderPreviewTable() {
    const holder = this.container?.querySelector?.("[data-preview-table]");
    if (!holder) {
      return;
    }

    const rows = Array.isArray(this.preview?.rows) ? this.preview.rows : [];
    const columns = Array.isArray(this.preview?.columns) ? this.preview.columns : [];

    if (!rows.length || !columns.length) {
      holder.innerHTML = '<p class="table-empty">Preview unavailable.</p>';
      return;
    }

    const head = columns.map((col) => `<th>${escapeHtml(col)}</th>`).join("");

    const body = rows
      .map((row) => {
        const cols = columns
          .map((col) => `<td>${escapeHtml(row?.[col] ?? "")}</td>`)
          .join("");
        return `<tr>${cols}</tr>`;
      })
      .join("");

    holder.innerHTML = `
      <table class="preview-table">
        <thead><tr>${head}</tr></thead>
        <tbody>${body}</tbody>
      </table>
    `;
  }

  renderMappingGrid() {
    const holder = this.container?.querySelector?.("[data-mapping-grid]");
    if (!holder) {
      return;
    }

    if (!this.sourceColumns.length) {
      holder.innerHTML = '<p class="table-empty">No source columns available for mapping.</p>';
      return;
    }

    const rows = CANONICAL_FIELDS.map((role) => {
      const suggested = Array.isArray(this.mappingSuggestions?.[role]) ? this.mappingSuggestions[role] : [];
      const currentValue = sanitizeText(this.mappingModel?.[role], "");
      const autoSelected = !currentValue || currentValue === AUTO_DETECT_VALUE ? "selected" : "";
      const options = this.sourceColumns.map((sourceColumn) => {
        const selected = currentValue === sourceColumn ? "selected" : "";
        const hit = suggested.find((item) => item?.column === sourceColumn);
        const confidence = hit ? ` | ${Number(hit?.confidence_pct || 0).toFixed(0)}%` : "";
        const optionLabel = `${truncateLabel(sourceColumn)}${confidence}`;
        return `<option value="${escapeHtml(sourceColumn)}" ${selected}>${escapeHtml(optionLabel)}</option>`;
      }).join("");

      return `
        <label class="map-row">
          <span>${escapeHtml(role)}</span>
          <select data-map-role="${escapeHtml(role)}">
            <option value="${AUTO_DETECT_VALUE}" ${autoSelected}>Auto-detect (consider all columns)</option>
            ${options}
          </select>
        </label>
      `;
    }).join("");

    holder.innerHTML = rows;
  }

  async applyMapping() {
    const fileId = sanitizeText(this.stateManager.get("dataset.fileId", ""), "");
    if (!fileId) {
      this.toast.show("Upload a dataset first.", { type: "error" });
      return;
    }

    const requiredRoles = ["Date", "Total Amount"];
    const resolvedMapping = {};

    CANONICAL_FIELDS.forEach((role) => {
      const selected = sanitizeText(this.mappingModel?.[role], "");

      if (selected && selected !== AUTO_DETECT_VALUE) {
        resolvedMapping[role] = selected;
        return;
      }

      if (!requiredRoles.includes(role)) {
        return;
      }

      const currentMapped = sanitizeText(this.stateManager.get(`dataset.mappedColumns.${role}`, ""), "");
      if (currentMapped) {
        resolvedMapping[role] = currentMapped;
        return;
      }

      const suggestions = Array.isArray(this.mappingSuggestions?.[role]) ? this.mappingSuggestions[role] : [];
      const bestSuggestion = sanitizeText(suggestions?.[0]?.column, "");
      if (bestSuggestion) {
        resolvedMapping[role] = bestSuggestion;
      }
    });

    const requiredMissing = requiredRoles.filter((item) => !sanitizeText(resolvedMapping?.[item], ""));
    if (requiredMissing.length) {
      this.toast.show(`Please map required fields: ${requiredMissing.join(", ")}`, { type: "error" });
      return;
    }

    const cleanedMapping = Object.entries(resolvedMapping).reduce((acc, [key, value]) => {
      const normalized = sanitizeText(value, "");
      if (normalized) {
        acc[key] = normalized;
      }
      return acc;
    }, {});

    this.setBusy(true, "Applying mapping...");

    const result = await this.dataService.applyMapping(fileId, cleanedMapping);

    if (result?.success) {
      this.toast.show("Mapping applied.", { type: "success", duration: 1500 });
      this.renderStatus("Mapping updated. You can now analyze.", "success");
      await this.loadPreviewAndMapping(fileId);
    } else {
      this.toast.show(result?.message || "Mapping update failed.", { type: "error" });
      this.renderStatus(result?.message || "Mapping update failed.", "error");
    }

    this.setBusy(false);
  }

  startAnalysisFlow() {
    const fileId = sanitizeText(this.stateManager.get("dataset.fileId", ""), "");
    if (!fileId) {
      this.toast.show("Upload dataset first.", { type: "error" });
      return;
    }

    this.stateManager.updatePath("ui.pendingAnalyze", true);
    this.renderStatus("Analyzing dataset...", "info");

    if (this.router && typeof this.router.navigate === "function") {
      this.router.navigate("/dashboard");
    }
  }

  syncState(state) {
    const isAuthenticated = Boolean(state?.auth?.isAuthenticated);
    const goAuthButton = this.container?.querySelector?.("[data-go-auth]");
    const fileInput = this.container?.querySelector?.("[data-file-input]");
    const submitButton = this.container?.querySelector?.("[data-upload-submit]");

    if (goAuthButton) {
      goAuthButton.hidden = isAuthenticated;
    }

    if (fileInput) {
      fileInput.disabled = !isAuthenticated || this.isBusy;
    }

    if (submitButton) {
      submitButton.disabled = !isAuthenticated || this.isBusy;
    }

    if (!isAuthenticated) {
      this.renderStatus("Please login to unlock upload.", "error");
      return;
    }

    const fileId = state?.dataset?.fileId || null;
    if (fileId && !this.preview && this.previewLoadInFlight !== fileId) {
      this.renderStatus("Dataset detected. Loading preview...", "info");
      this.loadPreviewAndMapping(fileId);
    }
  }

  setBusy(isBusy, label = "Uploading...") {
    this.isBusy = Boolean(isBusy);

    const isAuthenticated = Boolean(this.stateManager.get("auth.isAuthenticated", false));
    const fileInput = this.container?.querySelector?.("[data-file-input]");
    const pickButton = this.container?.querySelector?.("[data-upload-pick]");
    const uploadButton = this.container?.querySelector?.("[data-upload-submit]");
    const applyButton = this.container?.querySelector?.("[data-apply-mapping]");
    const analyzeButton = this.container?.querySelector?.("[data-start-analysis]");

    if (fileInput) {
      fileInput.disabled = !isAuthenticated || this.isBusy;
    }

    if (pickButton) {
      pickButton.disabled = !isAuthenticated || this.isBusy;
    }

    if (uploadButton) {
      uploadButton.disabled = !isAuthenticated || this.isBusy;
      uploadButton.textContent = this.isBusy ? label : "Upload Dataset";
    }

    if (applyButton) {
      applyButton.disabled = this.isBusy;
    }

    if (analyzeButton) {
      analyzeButton.disabled = this.isBusy;
    }
  }

  renderStatus(message, variant = "info") {
    const status = this.container?.querySelector?.("[data-upload-status]");
    if (!status) {
      return;
    }

    status.textContent = sanitizeText(message, "Ready.");
    status.setAttribute("data-variant", variant);
  }
}
