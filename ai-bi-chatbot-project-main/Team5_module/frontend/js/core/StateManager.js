function safeClone(data) {
  if (typeof structuredClone === "function") {
    return structuredClone(data);
  }

  try {
    return JSON.parse(JSON.stringify(data));
  } catch (_error) {
    return data;
  }
}

function isObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function deepMerge(target, source) {
  if (!isObject(target)) {
    return safeClone(source);
  }

  if (!isObject(source)) {
    return safeClone(source);
  }

  const output = { ...target };

  Object.keys(source).forEach((key) => {
    const sourceValue = source[key];
    const targetValue = target[key];

    if (isObject(sourceValue) && isObject(targetValue)) {
      output[key] = deepMerge(targetValue, sourceValue);
      return;
    }

    output[key] = safeClone(sourceValue);
  });

  return output;
}

export class StateManager {
  static instance = null;

  static getInstance() {
    if (!StateManager.instance) {
      StateManager.instance = new StateManager();
    }
    return StateManager.instance;
  }

  constructor() {
    if (StateManager.instance) {
      return StateManager.instance;
    }

    this.listeners = new Set();
    this.state = {
      auth: {
        isAuthenticated: false,
        user: null
      },
      dataset: {
        fileId: null,
        capabilities: {},
        analysisComplete: false
      },
      ui: {
        theme: "holo-light",
        antiGravityEnabled: false,
        pendingAnalyze: false
      },
      routing: {
        currentPath: "/"
      }
    };

    StateManager.instance = this;
  }

  getState() {
    return safeClone(this.state);
  }

  get(path, fallback = null) {
    if (typeof path !== "string" || !path.trim()) {
      return this.getState();
    }

    const keys = path.split(".").filter(Boolean);
    let current = this.state;

    for (const key of keys) {
      if (!isObject(current) && !Array.isArray(current)) {
        return fallback;
      }

      if (!(key in current)) {
        return fallback;
      }

      current = current[key];
    }

    return current ?? fallback;
  }

  setState(partial) {
    if (!isObject(partial)) {
      return this.getState();
    }

    this.state = deepMerge(this.state, partial);
    this.notify();
    return this.getState();
  }

  updatePath(path, value) {
    if (typeof path !== "string" || !path.trim()) {
      return this.getState();
    }

    const keys = path.split(".").filter(Boolean);
    if (!keys.length) {
      return this.getState();
    }

    const nextState = this.getState();
    let pointer = nextState;

    for (let index = 0; index < keys.length - 1; index += 1) {
      const key = keys[index];
      if (!isObject(pointer[key])) {
        pointer[key] = {};
      }
      pointer = pointer[key];
    }

    pointer[keys[keys.length - 1]] = value;
    this.state = nextState;
    this.notify();

    return this.getState();
  }

  subscribe(listener) {
    if (typeof listener !== "function") {
      return () => {};
    }

    this.listeners.add(listener);

    return () => {
      this.listeners.delete(listener);
    };
  }

  notify() {
    const snapshot = this.getState();
    this.listeners.forEach((listener) => {
      try {
        listener(snapshot);
      } catch (error) {
        console.error("State listener error:", error?.message || error);
      }
    });
  }

  setAuthSession(user = null) {
    return this.setState({
      auth: {
        isAuthenticated: Boolean(user),
        user: user ?? null
      }
    });
  }

  clearAuthSession() {
    return this.setState({
      auth: {
        isAuthenticated: false,
        user: null
      }
    });
  }

  setDatasetContext(fileId, capabilities = {}) {
    return this.setState({
      dataset: {
        fileId: fileId || null,
        capabilities: capabilities ?? {},
        analysisComplete: false
      }
    });
  }

  markAnalysisComplete(isComplete = true) {
    return this.updatePath("dataset.analysisComplete", Boolean(isComplete));
  }

  clearDatasetContext() {
    return this.setState({
      dataset: {
        fileId: null,
        capabilities: {},
        analysisComplete: false
      }
    });
  }
}

export const stateManager = StateManager.getInstance();
