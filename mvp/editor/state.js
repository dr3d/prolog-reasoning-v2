export const CANVAS = {
  width: 960,
  height: 600,
  minRectSize: 48,
};

const COLORS = ["#efc46a", "#d1a25c", "#a7c89c", "#8bbcc4", "#d59f8b", "#cdb7dd"];
let rectCounter = 0;
let constraintCounter = 0;

export function cloneScene(scene) {
  return JSON.parse(JSON.stringify(scene));
}

export function makeRect(overrides = {}) {
  rectCounter += 1;
  const index = rectCounter;
  return {
    id: overrides.id ?? `rect_${index}`,
    label: overrides.label ?? `Rect ${index}`,
    x: overrides.x ?? 72 + ((index - 1) % 4) * 160,
    y: overrides.y ?? 72 + Math.floor((index - 1) / 4) * 110,
    width: overrides.width ?? 150,
    height: overrides.height ?? 96,
    fill: overrides.fill ?? COLORS[(index - 1) % COLORS.length],
  };
}

export function makeConstraint(overrides = {}) {
  constraintCounter += 1;
  return {
    id: overrides.id ?? `constraint_${constraintCounter}`,
    type: overrides.type ?? "align-left",
    a: overrides.a ?? "",
    b: overrides.b ?? "",
    gap: overrides.gap ?? 24,
  };
}

function buildScene(rects, constraints = []) {
  return {
    canvas: { ...CANVAS },
    rects,
    constraints,
  };
}

export function reseedCounters(scene) {
  const rectNumbers = scene.rects
    .map((rect) => Number.parseInt(String(rect.id).split("_").pop(), 10))
    .filter((value) => Number.isFinite(value));
  const constraintNumbers = scene.constraints
    .map((constraint) => Number.parseInt(String(constraint.id).split("_").pop(), 10))
    .filter((value) => Number.isFinite(value));
  rectCounter = rectNumbers.length ? Math.max(...rectNumbers) : scene.rects.length;
  constraintCounter = constraintNumbers.length ? Math.max(...constraintNumbers) : scene.constraints.length;
}

export function buildStarterScene() {
  const scene = buildScene(
    [
      makeRect({ id: "rect_1", label: "Header", x: 96, y: 120, width: 170, height: 92 }),
      makeRect({ id: "rect_2", label: "Body", x: 336, y: 184, width: 150, height: 92 }),
      makeRect({ id: "rect_3", label: "Aside", x: 584, y: 248, width: 150, height: 92 }),
    ],
    []
  );
  reseedCounters(scene);
  return scene;
}

function lessonScene(id) {
  const scenes = {
    why_constraints: buildScene(
      [
        makeRect({ id: "card_a", label: "Card A", x: 110, y: 146, width: 180, height: 96, fill: "#efc46a" }),
        makeRect({ id: "card_b", label: "Card B", x: 390, y: 266, width: 150, height: 96, fill: "#8bbcc4" }),
      ],
      [makeConstraint({ id: "constraint_1", type: "align-left", a: "card_a", b: "card_b" })]
    ),
    editor_loop: buildScene(
      [
        makeRect({ id: "story_a", label: "Story A", x: 92, y: 150, width: 160, height: 100, fill: "#efc46a" }),
        makeRect({ id: "story_b", label: "Story B", x: 320, y: 212, width: 120, height: 100, fill: "#d59f8b" }),
        makeRect({ id: "story_c", label: "Story C", x: 548, y: 274, width: 120, height: 100, fill: "#a7c89c" }),
      ],
      [
        makeConstraint({ id: "constraint_1", type: "equal-width", a: "story_a", b: "story_b" }),
        makeConstraint({ id: "constraint_2", type: "equal-width", a: "story_b", b: "story_c" }),
        makeConstraint({ id: "constraint_3", type: "horizontal-gap", a: "story_a", b: "story_b", gap: 34 }),
        makeConstraint({ id: "constraint_4", type: "horizontal-gap", a: "story_b", b: "story_c", gap: 34 }),
      ]
    ),
    nesy_role: buildScene(
      [
        makeRect({ id: "intent_box", label: "Intent", x: 112, y: 128, width: 170, height: 102, fill: "#d59f8b" }),
        makeRect({ id: "solver_box", label: "Truth", x: 360, y: 128, width: 170, height: 102, fill: "#8bbcc4" }),
        makeRect({ id: "explain_box", label: "Explain", x: 608, y: 128, width: 170, height: 102, fill: "#a7c89c" }),
      ],
      [
        makeConstraint({ id: "constraint_1", type: "align-top", a: "intent_box", b: "solver_box" }),
        makeConstraint({ id: "constraint_2", type: "align-top", a: "solver_box", b: "explain_box" }),
        makeConstraint({ id: "constraint_3", type: "horizontal-gap", a: "intent_box", b: "solver_box", gap: 78 }),
        makeConstraint({ id: "constraint_4", type: "horizontal-gap", a: "solver_box", b: "explain_box", gap: 78 }),
      ]
    ),
    conflict_reading: buildScene(
      [
        makeRect({ id: "rule_a", label: "Rule A", x: 120, y: 220, width: 180, height: 104, fill: "#efc46a" }),
        makeRect({ id: "rule_b", label: "Rule B", x: 392, y: 220, width: 180, height: 104, fill: "#d59f8b" }),
      ],
      [
        makeConstraint({ id: "constraint_1", type: "align-left", a: "rule_a", b: "rule_b" }),
        makeConstraint({ id: "constraint_2", type: "horizontal-gap", a: "rule_a", b: "rule_b", gap: 36 }),
      ]
    ),
  };

  const scene = scenes[id] ?? buildStarterScene();
  reseedCounters(scene);
  return scene;
}

export const LESSONS = [
  {
    id: "why_constraints",
    title: "Why constraints?",
    duration: "2 min",
    summary: "A single relationship should survive movement. Drag Card A and Card B keeps the same left edge.",
    projectLink: "This is the low-friction doorway into the whole project: explicit structure beats manual repair.",
    steps: [
      "Select Card A and drag it around the canvas.",
      "Watch Card B update because the relationship is the thing that matters, not the last pixel position.",
      "Remove the align-left constraint to feel the difference.",
    ],
  },
  {
    id: "editor_loop",
    title: "How this editor thinks",
    duration: "3 min",
    summary: "The editor clones state, applies deterministic rules, then either commits or rolls back.",
    projectLink: "This mirrors the repo's propagation mindset: a repeatable solve loop with no silent failures.",
    steps: [
      "Drag Story A or resize it from the lower-right handle.",
      "The equal-width and horizontal-gap rules propagate across the row.",
      "Notice that the result is stable because the rule order is fixed and the allowed actions are small.",
    ],
  },
  {
    id: "nesy_role",
    title: "What NeSy is doing here",
    duration: "2 min",
    summary: "The solver owns truth. A future LLM layer would translate intent or explain outcomes, not edit geometry directly.",
    projectLink: "That is the neuro-symbolic contract in this repo: deterministic structure underneath, language on top.",
    steps: [
      "Drag the Intent rectangle and watch the truth and explanation boxes follow.",
      "Imagine a language model creating these structured constraints instead of moving boxes freehand.",
      "The structure stays inspectable because every change still becomes a validated operation.",
    ],
  },
  {
    id: "conflict_reading",
    title: "How to read a conflict",
    duration: "2 min",
    summary: "A conflict means two requested truths cannot both hold. The app names the fight and keeps the last valid scene.",
    projectLink: "That same idea powers the broader project: failure should teach, not mystify.",
    steps: [
      "This scene is intentionally contradictory: Rule B cannot share Rule A's left edge and also keep a positive gap.",
      "Notice the conflict card naming the offending rule and shapes.",
      "Remove one rule to get back to a valid layout.",
    ],
  },
];

export function loadLessonScene(lessonId) {
  return lessonScene(lessonId);
}

export function createAppState() {
  const scene = buildStarterScene();
  return {
    scene,
    lastValidScene: cloneScene(scene),
    selectedRectId: scene.rects[0]?.id ?? null,
    activeLessonId: LESSONS[0].id,
    conflict: null,
    status: {
      tone: "info",
      title: "Starter scene ready",
      detail: "Add rules, drag a rectangle, or load a lesson to see the deterministic solve loop in action.",
    },
  };
}
