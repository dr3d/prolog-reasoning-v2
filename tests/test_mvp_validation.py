from mvp.validate_constraints import run_validation_cases


def test_mvp_validation_cases():
    results = run_validation_cases()
    assert len(results) == 7
    assert sum(1 for result in results if result["ok"]) == 5
    assert sum(1 for result in results if not result["ok"]) == 2
