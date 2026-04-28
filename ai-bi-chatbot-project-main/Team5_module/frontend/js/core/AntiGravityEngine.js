import { stateManager as sharedStateManager } from "./StateManager.js";
import { toast as sharedToast } from "../components/Toast.js";

const DEFAULT_LAYER_ID = "anti-gravity-layer";
const DEFAULT_CHIP_COUNT = 14;
const CHIP_WORDS = [
  "KPI",
  "INSIGHT",
  "TREND",
  "REVENUE",
  "MARGIN",
  "GROWTH",
  "SEGMENT",
  "FORECAST",
  "CHURN",
  "COHORT",
  "LTV",
  "AOV",
  "NPS",
  "ROI"
];

function randomBetween(min, max) {
  return min + Math.random() * (max - min);
}

export class AntiGravityEngine {
  constructor(options = {}) {
    this.layerId = options?.layerId || DEFAULT_LAYER_ID;
    this.chipCount = Number(options?.chipCount) > 0 ? Number(options.chipCount) : DEFAULT_CHIP_COUNT;
    this.stateManager = options?.stateManager || sharedStateManager;
    this.toast = options?.toast || sharedToast;

    this.matterRef = null;
    this.engine = null;
    this.runner = null;
    this.layerEl = null;
    this.boundaryBodies = [];
    this.chipBodies = [];
    this.oscillation = 0;
    this.active = false;

    this.boundAfterUpdate = this.handleAfterUpdate.bind(this);
    this.boundResize = this.handleResize.bind(this);
  }

  getWindowRef() {
    if (typeof window === "undefined") {
      return null;
    }
    return window;
  }

  getDocumentRef() {
    if (typeof document === "undefined") {
      return null;
    }
    return document;
  }

  getMatterRef() {
    const win = this.getWindowRef();
    return win?.Matter || null;
  }

  ensureLayer() {
    const doc = this.getDocumentRef();
    if (!doc) {
      return null;
    }

    let layer = doc.getElementById(this.layerId);
    if (!layer) {
      layer = doc.createElement("div");
      layer.id = this.layerId;
      layer.className = "anti-gravity-layer";
      layer.setAttribute("aria-hidden", "true");
      if (doc.body) {
        doc.body.appendChild(layer);
      }
    }

    return layer;
  }

  enable() {
    if (this.active) {
      return true;
    }

    const matter = this.getMatterRef();
    if (!matter) {
      this.toast.show("Matter.js not loaded, cannot enable Anti-Gravity mode.", { type: "error" });
      return false;
    }

    const layer = this.ensureLayer();
    if (!layer) {
      this.toast.show("Anti-Gravity layer is unavailable.", { type: "error" });
      return false;
    }

    this.matterRef = matter;
    this.layerEl = layer;
    this.layerEl.innerHTML = "";
    this.layerEl.classList.add("is-enabled");

    this.engine = matter.Engine.create();
    this.engine.gravity.y = -0.22;
    this.engine.gravity.x = 0;

    this.runner = matter.Runner.create();

    this.createBounds();
    this.createChips();

    matter.Events.on(this.engine, "afterUpdate", this.boundAfterUpdate);
    matter.Runner.run(this.runner, this.engine);

    const win = this.getWindowRef();
    if (win) {
      win.addEventListener("resize", this.boundResize);
    }

    this.active = true;
    return true;
  }

  disable() {
    if (!this.active) {
      return;
    }

    const matter = this.matterRef;
    const win = this.getWindowRef();

    if (win) {
      win.removeEventListener("resize", this.boundResize);
    }

    if (matter && this.engine) {
      matter.Events.off(this.engine, "afterUpdate", this.boundAfterUpdate);
    }

    if (matter && this.runner) {
      matter.Runner.stop(this.runner);
    }

    if (matter && this.engine) {
      this.clearWorldBodies();
      matter.Engine.clear(this.engine);
    }

    if (this.layerEl) {
      this.layerEl.classList.remove("is-enabled");
      this.layerEl.innerHTML = "";
    }

    this.engine = null;
    this.runner = null;
    this.boundaryBodies = [];
    this.chipBodies = [];
    this.oscillation = 0;
    this.active = false;
    this.matterRef = null;
  }

  clearWorldBodies() {
    const matter = this.matterRef;
    if (!matter || !this.engine) {
      return;
    }

    const world = this.engine.world;

    for (const entry of this.chipBodies) {
      if (entry?.body) {
        matter.World.remove(world, entry.body);
      }
    }

    for (const boundary of this.boundaryBodies) {
      matter.World.remove(world, boundary);
    }
  }

  createBounds() {
    const matter = this.matterRef;
    const win = this.getWindowRef();
    if (!matter || !win || !this.engine) {
      return;
    }

    const width = Math.max(420, Number(win.innerWidth || 0));
    const height = Math.max(320, Number(win.innerHeight || 0));

    const world = this.engine.world;

    for (const boundary of this.boundaryBodies) {
      matter.World.remove(world, boundary);
    }

    const wallOptions = {
      isStatic: true,
      restitution: 1,
      friction: 0,
      frictionStatic: 0,
      render: { visible: false }
    };

    const top = matter.Bodies.rectangle(width / 2, -20, width + 80, 40, wallOptions);
    const bottom = matter.Bodies.rectangle(width / 2, height + 20, width + 80, 40, wallOptions);
    const left = matter.Bodies.rectangle(-20, height / 2, 40, height + 80, wallOptions);
    const right = matter.Bodies.rectangle(width + 20, height / 2, 40, height + 80, wallOptions);

    this.boundaryBodies = [top, bottom, left, right];
    matter.World.add(world, this.boundaryBodies);
  }

  createChips() {
    const matter = this.matterRef;
    const doc = this.getDocumentRef();
    const win = this.getWindowRef();

    if (!matter || !doc || !win || !this.layerEl || !this.engine) {
      return;
    }

    const world = this.engine.world;
    const width = Math.max(420, Number(win.innerWidth || 0));
    const height = Math.max(320, Number(win.innerHeight || 0));

    this.chipBodies = [];

    for (let index = 0; index < this.chipCount; index += 1) {
      const chipWidth = Math.round(randomBetween(82, 140));
      const chipHeight = Math.round(randomBetween(30, 46));
      const x = randomBetween(chipWidth, width - chipWidth);
      const y = randomBetween(height - 120, height - 30);

      const chipEl = doc.createElement("span");
      chipEl.className = "gravity-chip";
      chipEl.textContent = CHIP_WORDS[index % CHIP_WORDS.length];
      chipEl.style.width = `${chipWidth}px`;
      chipEl.style.height = `${chipHeight}px`;

      const chipBody = matter.Bodies.rectangle(x, y, chipWidth, chipHeight, {
        restitution: 0.96,
        friction: 0.0001,
        frictionStatic: 0.0001,
        frictionAir: 0.004,
        density: 0.0013,
        chamfer: { radius: 12 }
      });

      matter.Body.setVelocity(chipBody, {
        x: randomBetween(-2.6, 2.6),
        y: randomBetween(-8.2, -2.6)
      });
      matter.Body.setAngularVelocity(chipBody, randomBetween(-0.06, 0.06));

      matter.World.add(world, chipBody);
      this.layerEl.appendChild(chipEl);

      this.chipBodies.push({
        body: chipBody,
        element: chipEl,
        width: chipWidth,
        height: chipHeight
      });
    }

    this.syncChipTransforms();
  }

  handleAfterUpdate() {
    if (!this.engine) {
      return;
    }

    this.oscillation += 0.015;
    this.engine.gravity.x = Math.sin(this.oscillation) * 0.08;

    this.syncChipTransforms();
  }

  syncChipTransforms() {
    if (!this.chipBodies.length) {
      return;
    }

    for (const chip of this.chipBodies) {
      if (!chip?.body || !chip?.element) {
        continue;
      }

      const x = chip.body.position.x - chip.width / 2;
      const y = chip.body.position.y - chip.height / 2;
      chip.element.style.transform = `translate3d(${x}px, ${y}px, 0) rotate(${chip.body.angle}rad)`;
    }
  }

  handleResize() {
    if (!this.active || !this.matterRef || !this.engine) {
      return;
    }

    this.createBounds();

    const win = this.getWindowRef();
    const matter = this.matterRef;
    if (!win || !matter) {
      return;
    }

    const width = Math.max(420, Number(win.innerWidth || 0));
    const height = Math.max(320, Number(win.innerHeight || 0));

    for (const chip of this.chipBodies) {
      const body = chip?.body;
      if (!body) {
        continue;
      }

      const clampedX = Math.min(Math.max(body.position.x, chip.width / 2), width - chip.width / 2);
      const clampedY = Math.min(Math.max(body.position.y, chip.height / 2), height - chip.height / 2);

      if (clampedX !== body.position.x || clampedY !== body.position.y) {
        matter.Body.setPosition(body, { x: clampedX, y: clampedY });
      }
    }

    this.syncChipTransforms();
  }
}
