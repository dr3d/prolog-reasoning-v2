"""Scriptable validation for the Draw With Constraints MVP."""

from __future__ import annotations

from copy import deepcopy

CANVAS = {"width": 960, "height": 600, "min_rect_size": 48}
MAX_ITERATIONS = 24


def clone_scene(scene):
    return deepcopy(scene)


def make_conflict(constraint, message):
    return {
        "constraintId": constraint.get("id", "scene"),
        "constraintType": constraint.get("type", "scene"),
        "rectIds": [value for value in [constraint.get("a"), constraint.get("b")] if value],
        "message": message,
    }


def rect_map(scene):
    return {rect["id"]: rect for rect in scene["rects"]}


def detect_direct_conflict(scene):
    rectangles = rect_map(scene)
    gap_buckets = {}
    for constraint in scene["constraints"]:
        if constraint["type"] == "horizontal-gap":
            key = (constraint["a"], constraint["b"])
            gap_buckets.setdefault(key, []).append(constraint)

    for constraints in gap_buckets.values():
        gaps = {constraint["gap"] for constraint in constraints}
        if len(gaps) > 1:
            return make_conflict(
                constraints[1],
                f"These horizontal-gap rules disagree for {constraints[0]['a']} -> {constraints[0]['b']}. Pick one gap value.",
            )

    for constraint in scene["constraints"]:
        rect_a = rectangles.get(constraint["a"])
        rect_b = rectangles.get(constraint.get("b"))

        if constraint["type"] == "inside" and rect_a:
            if rect_a["width"] > scene["canvas"]["width"] or rect_a["height"] > scene["canvas"]["height"]:
                return make_conflict(
                    constraint,
                    f"{rect_a['id']} is larger than the canvas, so inside({rect_a['id']}, canvas) cannot be satisfied.",
                )

        if constraint["type"] == "align-left" and rect_a and rect_b:
            for other in scene["constraints"]:
                if other["type"] == "horizontal-gap" and other["a"] == constraint["a"] and other["b"] == constraint["b"]:
                    if rect_a["width"] + other["gap"] != 0:
                        return make_conflict(
                            other,
                            f"{constraint['b']} cannot stay aligned left with {constraint['a']} and also keep a {other['gap']}px horizontal gap.",
                        )
    return None


def apply_constraint(constraint, rectangles, canvas):
    rect_a = rectangles[constraint["a"]]
    rect_b = rectangles.get(constraint.get("b"))
    changed = False

    if constraint["type"] == "align-left":
        changed = rect_b["x"] != rect_a["x"]
        rect_b["x"] = rect_a["x"]
    elif constraint["type"] == "align-top":
        changed = rect_b["y"] != rect_a["y"]
        rect_b["y"] = rect_a["y"]
    elif constraint["type"] == "equal-width":
        changed = rect_b["width"] != rect_a["width"]
        rect_b["width"] = rect_a["width"]
    elif constraint["type"] == "horizontal-gap":
        next_x = rect_a["x"] + rect_a["width"] + constraint["gap"]
        changed = rect_b["x"] != next_x
        rect_b["x"] = next_x
    elif constraint["type"] == "inside":
        if rect_a["width"] > canvas["width"] or rect_a["height"] > canvas["height"]:
            return False, make_conflict(constraint, f"{rect_a['id']} is too large for the canvas, so the inside constraint cannot be satisfied.")
        next_x = min(max(rect_a["x"], 0), canvas["width"] - rect_a["width"])
        next_y = min(max(rect_a["y"], 0), canvas["height"] - rect_a["height"])
        changed = rect_a["x"] != next_x or rect_a["y"] != next_y
        rect_a["x"] = next_x
        rect_a["y"] = next_y
    else:
        return False, make_conflict(constraint, f"Unsupported constraint type {constraint['type']}.")

    return changed, None


def validate_solution(scene):
    rectangles = rect_map(scene)
    for constraint in scene["constraints"]:
        rect_a = rectangles[constraint["a"]]
        rect_b = rectangles.get(constraint.get("b"))
        if constraint["type"] == "align-left" and rect_b["x"] != rect_a["x"]:
            return make_conflict(constraint, f"{constraint['b']} did not align left with {constraint['a']}.")
        if constraint["type"] == "align-top" and rect_b["y"] != rect_a["y"]:
            return make_conflict(constraint, f"{constraint['b']} did not align top with {constraint['a']}.")
        if constraint["type"] == "equal-width" and rect_b["width"] != rect_a["width"]:
            return make_conflict(constraint, f"{constraint['b']} did not match {constraint['a']} width.")
        if constraint["type"] == "horizontal-gap" and rect_b["x"] != rect_a["x"] + rect_a["width"] + constraint["gap"]:
            return make_conflict(constraint, f"{constraint['b']} did not keep the requested gap after {constraint['a']}.")
        if constraint["type"] == "inside":
            inside = (
                rect_a["x"] >= 0
                and rect_a["y"] >= 0
                and rect_a["x"] + rect_a["width"] <= scene["canvas"]["width"]
                and rect_a["y"] + rect_a["height"] <= scene["canvas"]["height"]
            )
            if not inside:
                return make_conflict(constraint, f"{constraint['a']} ended outside the canvas bounds.")
    return None


def solve_scene(scene):
    working = clone_scene(scene)
    issue = detect_direct_conflict(working)
    if issue:
        return {"ok": False, "scene": working, "conflict": issue}

    rectangles = rect_map(working)
    for _ in range(MAX_ITERATIONS):
        changed = False
        for constraint in working["constraints"]:
            did_change, issue = apply_constraint(constraint, rectangles, working["canvas"])
            if issue:
                return {"ok": False, "scene": working, "conflict": issue}
            changed = changed or did_change
        issue = validate_solution(working)
        if not issue and not changed:
            return {"ok": True, "scene": working, "conflict": None}

    return {
        "ok": False,
        "scene": working,
        "conflict": make_conflict(working["constraints"][-1] if working["constraints"] else {"id": "scene", "type": "scene"}, "These constraints keep changing the scene in circles."),
    }


def base_rect(rect_id, x=100, y=100, width=140, height=90):
    return {"id": rect_id, "x": x, "y": y, "width": width, "height": height}


VALIDATION_CASES = [
    {
        "name": "align-left",
        "expect_ok": True,
        "scene": {
            "canvas": dict(CANVAS),
            "rects": [base_rect("a", x=120), base_rect("b", x=420)],
            "constraints": [{"id": "c1", "type": "align-left", "a": "a", "b": "b", "gap": 0}],
        },
        "check": lambda solved: solved["scene"]["rects"][1]["x"] == solved["scene"]["rects"][0]["x"],
    },
    {
        "name": "align-top",
        "expect_ok": True,
        "scene": {
            "canvas": dict(CANVAS),
            "rects": [base_rect("a", y=90), base_rect("b", y=280)],
            "constraints": [{"id": "c1", "type": "align-top", "a": "a", "b": "b", "gap": 0}],
        },
        "check": lambda solved: solved["scene"]["rects"][1]["y"] == solved["scene"]["rects"][0]["y"],
    },
    {
        "name": "equal-width",
        "expect_ok": True,
        "scene": {
            "canvas": dict(CANVAS),
            "rects": [base_rect("a", width=220), base_rect("b", width=120)],
            "constraints": [{"id": "c1", "type": "equal-width", "a": "a", "b": "b", "gap": 0}],
        },
        "check": lambda solved: solved["scene"]["rects"][1]["width"] == solved["scene"]["rects"][0]["width"],
    },
    {
        "name": "horizontal-gap",
        "expect_ok": True,
        "scene": {
            "canvas": dict(CANVAS),
            "rects": [base_rect("a", x=60, width=180), base_rect("b", x=500)],
            "constraints": [{"id": "c1", "type": "horizontal-gap", "a": "a", "b": "b", "gap": 36}],
        },
        "check": lambda solved: solved["scene"]["rects"][1]["x"] == solved["scene"]["rects"][0]["x"] + solved["scene"]["rects"][0]["width"] + 36,
    },
    {
        "name": "inside",
        "expect_ok": True,
        "scene": {
            "canvas": dict(CANVAS),
            "rects": [base_rect("a", x=900, y=560, width=120, height=80)],
            "constraints": [{"id": "c1", "type": "inside", "a": "a", "b": "", "gap": 0}],
        },
        "check": lambda solved: solved["scene"]["rects"][0]["x"] + solved["scene"]["rects"][0]["width"] <= CANVAS["width"] and solved["scene"]["rects"][0]["y"] + solved["scene"]["rects"][0]["height"] <= CANVAS["height"],
    },
    {
        "name": "conflict_align_left_vs_gap",
        "expect_ok": False,
        "scene": {
            "canvas": dict(CANVAS),
            "rects": [base_rect("a", x=100, width=180), base_rect("b", x=420)],
            "constraints": [
                {"id": "c1", "type": "align-left", "a": "a", "b": "b", "gap": 0},
                {"id": "c2", "type": "horizontal-gap", "a": "a", "b": "b", "gap": 24},
            ],
        },
        "check": lambda solved: "cannot stay aligned left" in solved["conflict"]["message"],
    },
    {
        "name": "conflict_inside_too_large",
        "expect_ok": False,
        "scene": {
            "canvas": dict(CANVAS),
            "rects": [base_rect("a", width=1100, height=120)],
            "constraints": [{"id": "c1", "type": "inside", "a": "a", "b": "", "gap": 0}],
        },
        "check": lambda solved: "canvas" in solved["conflict"]["message"],
    },
]


def run_validation_cases():
    results = []
    for case in VALIDATION_CASES:
        solved = solve_scene(case["scene"])
        if solved["ok"] != case["expect_ok"]:
            raise AssertionError(f"Unexpected success state for {case['name']}: {solved}")
        if not case["check"](solved):
            raise AssertionError(f"Validation shape failed for {case['name']}: {solved}")
        results.append({"name": case["name"], "ok": solved["ok"]})
    return results


if __name__ == "__main__":
    for result in run_validation_cases():
        print(f"[ok] {result['name']}: ok={result['ok']}")
