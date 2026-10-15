import ast
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WEB_UI_DIR = REPO_ROOT / "web_ui"


class TestLayoutTest(unittest.TestCase):
    def test_indicator_led_verify_step_is_versioned(self):
        repo_root = Path(__file__).resolve().parents[2]
        verify_step = (
            "main_program/testcase_database/steps/"
            "Resource_Chassis/Indicator_LED_Control/verify_led.py"
        )
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", verify_step],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(
            tracked.returncode,
            0,
            f"{verify_step} must be tracked by git: {tracked.stderr}",
        )

    def test_active_tests_use_component_owned_paths(self):
        expected = (
            WEB_UI_DIR / "tests" / "test_task_api_contract.py",
            WEB_UI_DIR / "tests" / "test_db_lifecycle.py",
            REPO_ROOT / "main_program" / "tests" / "test_console_helper.py",
        )
        for path in expected:
            with self.subTest(path=path):
                self.assertTrue(path.is_file(), f"missing target test: {path}")

        obsolete = (
            WEB_UI_DIR / "task_api_contract_check.py",
            WEB_UI_DIR / "tests" / "integration",
            REPO_ROOT / "Test_development_scripts",
        )
        for path in obsolete:
            with self.subTest(path=path):
                self.assertFalse(path.exists(), f"obsolete path remains: {path}")

    def test_lifecycle_runner_has_main_guard(self):
        runner = (
            WEB_UI_DIR / "tests" / "test_db_lifecycle.py"
        )
        tree = ast.parse(runner.read_text(encoding="utf-8"), filename=str(runner))

        guarded_main_call = False
        for node in tree.body:
            if not isinstance(node, ast.If):
                continue
            if not (
                isinstance(node.test, ast.Compare)
                and isinstance(node.test.left, ast.Name)
                and node.test.left.id == "__name__"
            ):
                continue
            guarded_main_call = any(
                isinstance(descendant, ast.Call)
                and isinstance(descendant.func, ast.Name)
                and descendant.func.id == "main"
                for descendant in ast.walk(node)
            )

        self.assertTrue(
            guarded_main_call,
            "manual lifecycle runner must call main() only under __main__ guard",
        )

    def test_lifecycle_runner_has_no_bypass_to_development_server(self):
        runner = WEB_UI_DIR / "tests" / "test_db_lifecycle.py"
        source = runner.read_text(encoding="utf-8")
        self.assertEqual(source.count("http://127.0.0.1:5000/api"), 1)
        self.assertIn("BASE = API", source)
        self.assertIn("_assert_isolated_worker_configuration()", source)


if __name__ == "__main__":
    unittest.main()
