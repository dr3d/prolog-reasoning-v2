import {
  CANVAS,
  LESSONS,
  buildStarterScene,
  cloneScene,
  createAppState,
  loadLessonScene,
  makeConstraint,
  makeRect,
  reseedCounters,
} from "./state.js";
import { solveScene } from "./solver_adapter.js";
import { formatConstraint, renderConstraintPanel } from "./ui_constraints.js";

const svg = document.querySelector("#editor-canvas");
const addRectButton = document.querySelector("#add-rect-button");
const deleteRectButton = document.querySelector("#delete-rect-button");
const resetSceneButton = document.querySelector("#reset-scene-button");
const constraintPanel = document.querySelector("#constraint-panel");
const conflictPanel = document.querySelector("#conflict-panel");
const lessonList = document.querySelector("#lesson-list");
const lessonDetail = document.querySelector("#lesson-detail");
const statusBanner = document.querySelector("#status-banner");
const selectedReadout = document.querySelector("#selected-readout");
const rectCountReadout = document.querySelector("#rect-count-readout");
const freedomReadout = document.querySelector("#freedom-readout");

const appState = createAppState();
let interaction = null;

function roughFreedomCount(scene) {
  return Math.max(0, scene.rects.length * 4 - scene.constraints.length);
}

function selectedRect(scene = appState.scene) {
  return scene.rects.find((rect) => rect.id === appState.selectedRectId) ?? null;
}

function setStatus(tone, title, detail) {
  appState.status = { tone, title, detail };
}

function commitScene(candidateScene, detailPrefix) {
  reseedCounters(candidateScene);
  const result = solveScene(candidateScene);
  if (result.ok) {
    appState.scene = result.scene;
    appState.lastValidScene = cloneScene(result.scene);
    appState.conflict = null;
    setStatus("info", "Solve succeeded", `${detailPrefix} Solver settled in ${result.iterations} pass${result.iterations === 1 ? "" : "es"}.`);
    const selectedStillExists = appState.scene.rects.some((rect) => rect.id === appState.selectedRectId);
    if (!selectedStillExists) {
      appState.selectedRectId = appState.scene.rects[0]?.id ?? null;
    }
  } else {
    appState.scene = cloneScene(appState.lastValidScene);
    appState.conflict = result.conflict;
    setStatus("conflict", "Conflict detected", result.conflict.message);
  }
  render();
  return result.ok;
}

function loadScene(scene, lessonId, detail) {
  appState.activeLessonId = lessonId;
  appState.selectedRectId = scene.rects[0]?.id ?? null;
  appState.scene = cloneScene(scene);
  appState.lastValidScene = cloneScene(scene);
  appState.conflict = null;
  const solved = solveScene(scene);
  if (solved.ok) {
    appState.scene = solved.scene;
    appState.lastValidScene = cloneScene(solved.scene);
    setStatus("info", "Scene loaded", detail);
  } else {
    appState.scene = cloneScene(scene);
    appState.lastValidScene = cloneScene(scene);
    appState.conflict = solved.conflict;
    setStatus("conflict", "Lesson conflict", solved.conflict.message);
  }
  render();
}

function resetToStarterScene() {
  loadScene(buildStarterScene(), LESSONS[0].id, "Starter scene loaded. Add a rule or pick a lesson to experience the editor step by step.");
}

function canvasPoint(event) {
  const bounds = svg.getBoundingClientRect();
  return {
    x: ((event.clientX - bounds.left) / bounds.width) * CANVAS.width,
    y: ((event.clientY - bounds.top) / bounds.height) * CANVAS.height,
  };
}

function buildConstraintGhost(constraint, scene) {
  if (constraint.type === "inside") {
    return "";
  }
  const rectA = scene.rects.find((rect) => rect.id === constraint.a);
  const rectB = scene.rects.find((rect) => rect.id === constraint.b);
  if (!rectA || !rectB) {
    return "";
  }
  const x1 = rectA.x + rectA.width / 2;
  const y1 = rectA.y + rectA.height / 2;
  const x2 = rectB.x + rectB.width / 2;
  const y2 = rectB.y + rectB.height / 2;
  const midX = (x1 + x2) / 2;
  const midY = (y1 + y2) / 2 - 10;
  return `
    <line class="constraint-line" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"></line>
    <text class="constraint-label" x="${midX}" y="${midY}" text-anchor="middle">${constraint.type}</text>
  `;
}

function renderCanvas() {
  const ghosts = appState.scene.constraints.map((constraint) => buildConstraintGhost(constraint, appState.scene)).join("");
  const shapes = appState.scene.rects
    .map((rect) => {
      const selected = rect.id === appState.selectedRectId ? "selected" : "";
      const handleX = rect.x + rect.width - 8;
      const handleY = rect.y + rect.height - 8;
      return `
        <g class="shape ${selected}" data-rect-id="${rect.id}">
          <rect class="body" data-role="body" data-rect-id="${rect.id}" x="${rect.x}" y="${rect.y}" width="${rect.width}" height="${rect.height}" rx="18" fill="${rect.fill}"></rect>
          <text x="${rect.x + 16}" y="${rect.y + 30}">${rect.label}</text>
          <text class="canvas-caption" x="${rect.x + 16}" y="${rect.y + 50}">${rect.id}</text>
          <rect class="resize-handle" data-role="handle" data-rect-id="${rect.id}" x="${handleX}" y="${handleY}" width="16" height="16" rx="4"></rect>
        </g>
      `;
    })
    .join("");

  svg.innerHTML = `
    <rect class="canvas-stage" x="0" y="0" width="${CANVAS.width}" height="${CANVAS.height}" rx="28"></rect>
    ${ghosts}
    ${shapes}
  `;
}

function renderLessons() {
  lessonList.innerHTML = LESSONS.map((lesson) => {
    const active = lesson.id === appState.activeLessonId ? "active" : "";
    return `
      <article class="lesson-card ${active}">
        <p class="lesson-meta">${lesson.duration}</p>
        <h3 class="lesson-title">${lesson.title}</h3>
        <p>${lesson.summary}</p>
        <button class="button button-secondary" type="button" data-load-lesson="${lesson.id}">Load Lesson</button>
      </article>
    `;
  }).join("");

  lessonList.querySelectorAll("[data-load-lesson]").forEach((button) => {
    button.addEventListener("click", () => {
      const lesson = LESSONS.find((item) => item.id === button.dataset.loadLesson);
      if (lesson) {
        loadScene(loadLessonScene(lesson.id), lesson.id, `${lesson.title} loaded. ${lesson.projectLink}`);
      }
    });
  });

  const activeLesson = LESSONS.find((lesson) => lesson.id === appState.activeLessonId) ?? LESSONS[0];
  lessonDetail.innerHTML = `
    <h3>${activeLesson.title}</h3>
    <p>${activeLesson.projectLink}</p>
    <div class="lesson-steps">
      ${activeLesson.steps.map((step, index) => `<div class="lesson-step"><strong>${index + 1}.</strong><span>${step}</span></div>`).join("")}
    </div>
  `;
}

function renderConflictPanel() {
  if (!appState.conflict) {
    conflictPanel.innerHTML = `<div class="empty-state">No current conflict. Try the "How to read a conflict" lesson if you want to see rollback in action.</div>`;
    return;
  }
  conflictPanel.innerHTML = `
    <div class="conflict-list">
      <article class="conflict-card">
        <span class="constraint-pill">${appState.conflict.constraintType}</span>
        <strong>${appState.conflict.constraintId}</strong>
        <p>${appState.conflict.message}</p>
        <p><strong>Involved:</strong> ${appState.conflict.rectIds.join(", ") || "scene"}</p>
      </article>
    </div>
  `;
}

function renderStatus() {
  statusBanner.className = `status-banner ${appState.status.tone === "conflict" ? "conflict" : ""}`;
  statusBanner.innerHTML = `<strong>${appState.status.title}</strong><p>${appState.status.detail}</p>`;
}

function renderReadouts() {
  selectedReadout.textContent = selectedRect()?.id ?? "None";
  rectCountReadout.textContent = String(appState.scene.rects.length);
  freedomReadout.textContent = String(roughFreedomCount(appState.scene));
}

function renderConstraints() {
  renderConstraintPanel({
    container: constraintPanel,
    scene: appState.scene,
    onAddConstraint: (draft) => {
      if (!draft.a) {
        return;
      }
      if (draft.type !== "inside" && (!draft.b || draft.a === draft.b)) {
        setStatus("conflict", "Constraint needs two rectangles", "Pick different A and B rectangles for pairwise rules.");
        render();
        return;
      }
      const nextScene = cloneScene(appState.scene);
      const nextConstraint = makeConstraint({
        type: draft.type,
        a: draft.a,
        b: draft.type === "inside" ? "" : draft.b,
        gap: draft.type === "horizontal-gap" ? draft.gap : 0,
      });
      nextScene.constraints.push(nextConstraint);
      commitScene(nextScene, `Added ${formatConstraint(nextConstraint)}.`);
    },
    onRemoveConstraint: (constraintId) => {
      const nextScene = cloneScene(appState.scene);
      nextScene.constraints = nextScene.constraints.filter((constraint) => constraint.id !== constraintId);
      commitScene(nextScene, `Removed ${constraintId}.`);
    },
  });
}

function render() {
  renderCanvas();
  renderLessons();
  renderConstraints();
  renderConflictPanel();
  renderStatus();
  renderReadouts();
}

function addRectangle() {
  const nextScene = cloneScene(appState.scene);
  const rect = makeRect();
  nextScene.rects.push(rect);
  appState.selectedRectId = rect.id;
  commitScene(nextScene, `Added ${rect.id}.`);
}

function deleteSelectedRectangle() {
  const rect = selectedRect();
  if (!rect) {
    return;
  }
  const nextScene = cloneScene(appState.scene);
  nextScene.rects = nextScene.rects.filter((item) => item.id !== rect.id);
  nextScene.constraints = nextScene.constraints.filter((constraint) => constraint.a !== rect.id && constraint.b !== rect.id);
  appState.selectedRectId = nextScene.rects[0]?.id ?? null;
  commitScene(nextScene, `Deleted ${rect.id} and removed dependent constraints.`);
}

function startInteraction(event, mode, rectId) {
  const point = canvasPoint(event);
  const rect = appState.scene.rects.find((item) => item.id === rectId);
  if (!rect) {
    return;
  }
  appState.selectedRectId = rectId;
  interaction = {
    mode,
    rectId,
    startPoint: point,
    baseScene: cloneScene(appState.scene),
    baseRect: { ...rect },
  };
  render();
}

function moveInteraction(event) {
  if (!interaction) {
    return;
  }
  const current = canvasPoint(event);
  const dx = current.x - interaction.startPoint.x;
  const dy = current.y - interaction.startPoint.y;
  const nextScene = cloneScene(interaction.baseScene);
  const rect = nextScene.rects.find((item) => item.id === interaction.rectId);
  if (!rect) {
    return;
  }

  if (interaction.mode === "drag") {
    rect.x = interaction.baseRect.x + dx;
    rect.y = interaction.baseRect.y + dy;
  } else {
    rect.width = Math.max(CANVAS.minRectSize, interaction.baseRect.width + dx);
    rect.height = Math.max(CANVAS.minRectSize, interaction.baseRect.height + dy);
  }

  commitScene(nextScene, interaction.mode === "drag" ? `Moved ${rect.id}.` : `Resized ${rect.id}.`);
}

function stopInteraction() {
  interaction = null;
}

svg.addEventListener("pointerdown", (event) => {
  const target = event.target.closest("[data-role]");
  if (!target) {
    appState.selectedRectId = null;
    render();
    return;
  }
  const rectId = target.dataset.rectId;
  if (target.dataset.role === "body") {
    startInteraction(event, "drag", rectId);
  } else {
    startInteraction(event, "resize", rectId);
  }
});

window.addEventListener("pointermove", (event) => {
  if (interaction) {
    moveInteraction(event);
  }
});
window.addEventListener("pointerup", stopInteraction);
window.addEventListener("keydown", (event) => {
  if (event.key === "Delete" || event.key === "Backspace") {
    deleteSelectedRectangle();
  }
});

addRectButton.addEventListener("click", addRectangle);
deleteRectButton.addEventListener("click", deleteSelectedRectangle);
resetSceneButton.addEventListener("click", resetToStarterScene);

loadScene(loadLessonScene(LESSONS[0].id), LESSONS[0].id, `${LESSONS[0].title} loaded. ${LESSONS[0].projectLink}`);
