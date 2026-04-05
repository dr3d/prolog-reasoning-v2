const CONSTRAINT_TYPES = [
  { value: "align-left", label: "align-left(A, B)" },
  { value: "align-top", label: "align-top(A, B)" },
  { value: "equal-width", label: "equal-width(A, B)" },
  { value: "horizontal-gap", label: "horizontal-gap(A, B, gap)" },
  { value: "inside", label: "inside(A, canvas)" },
];

export function formatConstraint(constraint) {
  if (constraint.type === "inside") {
    return `${constraint.type}(${constraint.a}, canvas)`;
  }
  if (constraint.type === "horizontal-gap") {
    return `${constraint.type}(${constraint.a}, ${constraint.b}, ${constraint.gap})`;
  }
  return `${constraint.type}(${constraint.a}, ${constraint.b})`;
}

export function renderConstraintPanel({ container, scene, onAddConstraint, onRemoveConstraint }) {
  const rectOptions = scene.rects
    .map((rect) => `<option value="${rect.id}">${rect.label} (${rect.id})</option>`)
    .join("");

  const listMarkup = scene.constraints.length
    ? scene.constraints
        .map(
          (constraint) => `
            <article class="constraint-item">
              <div class="constraint-row">
                <span class="constraint-pill">${constraint.type}</span>
                <button class="button" type="button" data-remove-constraint="${constraint.id}">Remove</button>
              </div>
              <strong>${constraint.id}</strong>
              <p>${formatConstraint(constraint)}</p>
            </article>
          `
        )
        .join("")
    : `<div class="empty-state">No constraints yet. Add one below or load a lesson scene.</div>`;

  container.innerHTML = `
    <form class="constraint-form" id="constraint-form">
      <div class="form-grid">
        <div class="field">
          <label for="constraint-type">Type</label>
          <select id="constraint-type" name="type">
            ${CONSTRAINT_TYPES.map((type) => `<option value="${type.value}">${type.label}</option>`).join("")}
          </select>
        </div>
        <div class="field">
          <label for="constraint-a">A (source)</label>
          <select id="constraint-a" name="a" ${scene.rects.length ? "" : "disabled"}>
            ${rectOptions}
          </select>
        </div>
      </div>
      <div class="form-grid">
        <div class="field" id="constraint-b-field">
          <label for="constraint-b">B (follower)</label>
          <select id="constraint-b" name="b" ${scene.rects.length > 1 ? "" : "disabled"}>
            ${rectOptions}
          </select>
        </div>
        <div class="field" id="constraint-gap-field">
          <label for="constraint-gap">Gap</label>
          <input id="constraint-gap" name="gap" type="number" value="24">
        </div>
      </div>
      <button class="button button-primary" type="submit" ${scene.rects.length ? "" : "disabled"}>Add Constraint</button>
    </form>
    <div class="constraint-list">${listMarkup}</div>
  `;

  const form = container.querySelector("#constraint-form");
  const typeSelect = container.querySelector("#constraint-type");
  const bField = container.querySelector("#constraint-b-field");
  const gapField = container.querySelector("#constraint-gap-field");

  function syncFields() {
    const type = typeSelect.value;
    bField.style.display = type === "inside" ? "none" : "grid";
    gapField.style.display = type === "horizontal-gap" ? "grid" : "none";
  }

  syncFields();
  typeSelect.addEventListener("change", syncFields);

  form?.addEventListener("submit", (event) => {
    event.preventDefault();
    const data = new FormData(form);
    onAddConstraint({
      type: String(data.get("type")),
      a: String(data.get("a")),
      b: String(data.get("b") ?? ""),
      gap: Number(data.get("gap") ?? 0),
    });
    form.reset();
    container.querySelector("#constraint-gap").value = "24";
    syncFields();
  });

  container.querySelectorAll("[data-remove-constraint]").forEach((button) => {
    button.addEventListener("click", () => onRemoveConstraint(button.dataset.removeConstraint));
  });
}
