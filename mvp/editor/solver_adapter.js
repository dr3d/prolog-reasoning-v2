import { CANVAS, cloneScene } from "./state.js";

const EPSILON = 0.01;
const MAX_ITERATIONS = 24;

function nearlyEqual(a, b) {
  return Math.abs(a - b) <= EPSILON;
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function idsFor(constraint) {
  return constraint.type === "inside" ? [constraint.a] : [constraint.a, constraint.b].filter(Boolean);
}

function makeConflict(constraint, message) {
  return {
    constraintId: constraint?.id ?? "scene",
    constraintType: constraint?.type ?? "scene",
    rectIds: idsFor(constraint ?? {}),
    message,
  };
}

function rectMap(scene) {
  return new Map(scene.rects.map((rect) => [rect.id, rect]));
}

function validateBasics(rect) {
  if (rect.width < CANVAS.minRectSize || rect.height < CANVAS.minRectSize) {
    return `Rectangle ${rect.id} is smaller than the minimum size of ${CANVAS.minRectSize}px.`;
  }
  return null;
}

function detectDirectConflict(scene) {
  const map = rectMap(scene);
  const gapBuckets = new Map();

  for (const constraint of scene.constraints) {
    if (constraint.type === "horizontal-gap") {
      const key = `${constraint.a}:${constraint.b}`;
      if (!gapBuckets.has(key)) {
        gapBuckets.set(key, []);
      }
      gapBuckets.get(key).push(constraint);
    }
  }

  for (const constraints of gapBuckets.values()) {
    const gaps = new Set(constraints.map((constraint) => Number(constraint.gap)));
    if (gaps.size > 1) {
      return makeConflict(constraints[1], `These horizontal-gap rules disagree for ${constraints[0].a} -> ${constraints[0].b}. Pick one gap value.`);
    }
  }

  for (const constraint of scene.constraints) {
    const rectA = map.get(constraint.a);
    const rectB = map.get(constraint.b);

    if (constraint.type === "inside" && rectA) {
      if (rectA.width > scene.canvas.width || rectA.height > scene.canvas.height) {
        return makeConflict(constraint, `${rectA.id} is larger than the canvas, so inside(${rectA.id}, canvas) cannot be satisfied.`);
      }
    }

    if (constraint.type === "align-left" && rectA && rectB) {
      const gapMate = scene.constraints.find((item) => item.type === "horizontal-gap" && item.a === constraint.a && item.b === constraint.b);
      if (gapMate && !nearlyEqual(rectA.width + Number(gapMate.gap), 0)) {
        return makeConflict(gapMate, `${constraint.b} cannot stay aligned left with ${constraint.a} and also keep a ${gapMate.gap}px horizontal gap.`);
      }
    }
  }

  return null;
}

function applyConstraint(constraint, map, canvas) {
  const rectA = map.get(constraint.a);
  const rectB = map.get(constraint.b);
  let changed = false;

  if (!rectA) {
    return { conflict: makeConflict(constraint, `Constraint ${constraint.id} references missing rectangle ${constraint.a}.`) };
  }

  const basicsA = validateBasics(rectA);
  if (basicsA) {
    return { conflict: makeConflict(constraint, basicsA) };
  }

  if (constraint.type === "inside") {
    if (rectA.width > canvas.width || rectA.height > canvas.height) {
      return { conflict: makeConflict(constraint, `${rectA.id} is too large for the canvas, so the inside constraint cannot be satisfied.`) };
    }
    const nextX = clamp(rectA.x, 0, canvas.width - rectA.width);
    const nextY = clamp(rectA.y, 0, canvas.height - rectA.height);
    changed = !nearlyEqual(rectA.x, nextX) || !nearlyEqual(rectA.y, nextY);
    rectA.x = nextX;
    rectA.y = nextY;
    return { changed };
  }

  if (!rectB) {
    return { conflict: makeConflict(constraint, `Constraint ${constraint.id} references missing rectangle ${constraint.b}.`) };
  }

  const basicsB = validateBasics(rectB);
  if (basicsB) {
    return { conflict: makeConflict(constraint, basicsB) };
  }

  if (constraint.type === "align-left") {
    changed = !nearlyEqual(rectB.x, rectA.x);
    rectB.x = rectA.x;
    return { changed };
  }

  if (constraint.type === "align-top") {
    changed = !nearlyEqual(rectB.y, rectA.y);
    rectB.y = rectA.y;
    return { changed };
  }

  if (constraint.type === "equal-width") {
    changed = !nearlyEqual(rectB.width, rectA.width);
    rectB.width = rectA.width;
    return { changed };
  }

  if (constraint.type === "horizontal-gap") {
    const nextX = rectA.x + rectA.width + Number(constraint.gap);
    changed = !nearlyEqual(rectB.x, nextX);
    rectB.x = nextX;
    return { changed };
  }

  return { conflict: makeConflict(constraint, `Unsupported constraint type ${constraint.type}.`) };
}

function validateScene(scene) {
  const map = rectMap(scene);
  for (const constraint of scene.constraints) {
    const rectA = map.get(constraint.a);
    const rectB = map.get(constraint.b);

    if (!rectA) {
      return makeConflict(constraint, `Constraint ${constraint.id} references missing rectangle ${constraint.a}.`);
    }

    if (constraint.type === "align-left" && (!rectB || !nearlyEqual(rectA.x, rectB.x))) {
      return makeConflict(constraint, `${constraint.b} did not end up aligned to the left edge of ${constraint.a}.`);
    }
    if (constraint.type === "align-top" && (!rectB || !nearlyEqual(rectA.y, rectB.y))) {
      return makeConflict(constraint, `${constraint.b} did not end up aligned to the top edge of ${constraint.a}.`);
    }
    if (constraint.type === "equal-width" && (!rectB || !nearlyEqual(rectA.width, rectB.width))) {
      return makeConflict(constraint, `${constraint.b} did not keep the same width as ${constraint.a}.`);
    }
    if (constraint.type === "horizontal-gap" && (!rectB || !nearlyEqual(rectB.x, rectA.x + rectA.width + Number(constraint.gap)))) {
      return makeConflict(constraint, `${constraint.b} did not keep the requested ${constraint.gap}px horizontal gap after ${constraint.a}.`);
    }
    if (constraint.type === "inside") {
      const inside = rectA.x >= 0 && rectA.y >= 0 && rectA.x + rectA.width <= scene.canvas.width + EPSILON && rectA.y + rectA.height <= scene.canvas.height + EPSILON;
      if (!inside) {
        return makeConflict(constraint, `${constraint.a} ended outside the canvas bounds.`);
      }
    }
  }
  return null;
}

export function solveScene(scene) {
  const working = cloneScene(scene);
  const directConflict = detectDirectConflict(working);
  if (directConflict) {
    return { ok: false, scene: working, conflict: directConflict, iterations: 0 };
  }

  const map = rectMap(working);
  let lastConstraint = null;

  for (let iteration = 1; iteration <= MAX_ITERATIONS; iteration += 1) {
    let changed = false;
    for (const constraint of working.constraints) {
      const result = applyConstraint(constraint, map, working.canvas);
      if (result.conflict) {
        return { ok: false, scene: working, conflict: result.conflict, iterations: iteration };
      }
      if (result.changed) {
        changed = true;
        lastConstraint = constraint;
      }
    }

    const issue = validateScene(working);
    if (!issue && !changed) {
      return { ok: true, scene: working, conflict: null, iterations: iteration };
    }
  }

  return {
    ok: false,
    scene: working,
    conflict: makeConflict(lastConstraint, "These constraints keep changing the scene in circles. Remove one of the competing rules and try again."),
    iterations: MAX_ITERATIONS,
  };
}
