class TestResult:
    test_script_path: str
    tests_generated: int
    tests_passed: int
    tests_failed: int
    test_logs: List[str]
    issues_found: List[str]