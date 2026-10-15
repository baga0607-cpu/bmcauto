import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker


WEB_UI_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = WEB_UI_DIR.parent

sys.path.insert(0, str(WEB_UI_DIR))

import app as app_module
from app import app
from models import Base, Category, Project, ProjectPlan, PlanSubfolder, Task, TaskTestCase, TestCase


class TaskApiContractTest(unittest.TestCase):
    def test_testcase_normalized_name_is_unique_per_plan(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            project = Project(id="proj_unique", name="Unique Project")
            plan = ProjectPlan(id="plan_unique", project_id=project.id, name="Unique Plan")
            session.add_all([
                project,
                plan,
                TestCase(system_id="tc_one", family_id="f1", display_name="Straße V2", plan_id=plan.id, script_path="one"),
            ])
            session.commit()
            session.add(TestCase(system_id="tc_two", family_id="f2", display_name="  STRASSE V2  ", plan_id=plan.id, script_path="two"))
            with self.assertRaises(IntegrityError):
                session.commit()
        finally:
            session.rollback()
            session.close()
            engine.dispose()

    def test_fresh_golden_plan_publish_can_be_forked(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        session.add_all([
            Project(id="source_project", name="Source Project"),
            ProjectPlan(id="source_plan", project_id="source_project", name="Source Plan"),
            Project(id="target_project", name="Target Project"),
            ProjectPlan(id="target_plan", project_id="target_project", name="Target Plan"),
            Category(id="cat", name="Custom"),
            TestCase(system_id="source_tc", family_id="family", display_name="Fresh Publish", plan_id="source_plan", category_id="cat", script_path="testcase_database.scripts.source_tc"),
        ])
        session.commit()
        session.close()
        with tempfile.TemporaryDirectory() as main_program:
            source_dir = Path(main_program) / "testcase_database" / "scripts" / "source_tc"
            source_dir.mkdir(parents=True)
            (source_dir / "__testcase__.py").write_text("STEPS = []\n", encoding="utf-8")
            with patch.object(app_module, "DbSession", Session), patch.object(app_module, "MAIN_PROGRAM_DIR", main_program):
                client = app.test_client()
                published = client.post("/api/push_to_golden", json={"system_id": "source_tc"})
                forked = client.post("/api/fork_tc", json={"project": "Target Project", "plan_id": "target_plan", "category": "Custom", "testcase": "Fresh Publish"})
            self.assertEqual(published.status_code, 200, published.get_json())
            self.assertEqual(forked.status_code, 200, forked.get_json())
        engine.dispose()

    def test_import_tc_rolls_back_records_and_both_dirs_on_golden_clone_failure(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        session.add_all([Project(id="p", name="P"), ProjectPlan(id="plan", project_id="p", name="Plan")])
        session.commit(); session.close()
        with tempfile.TemporaryDirectory() as main_program:
            real_clone = app_module._clone_testcase_record
            def fail_after_clone(*args, **kwargs):
                real_clone(*args, **kwargs)
                raise RuntimeError("forced golden failure")
            with patch.object(app_module, "DbSession", Session), patch.object(app_module, "MAIN_PROGRAM_DIR", main_program), patch.object(app_module, "_clone_testcase_record", side_effect=fail_after_clone):
                response = app.test_client().post("/api/import_tc", json={"plan_id": "plan", "project": "P", "category": "Custom", "tc_name": "Atomic", "steps": [], "push_to_golden": True})
            self.assertEqual(response.status_code, 500)
            verify = Session()
            self.assertEqual(verify.query(TestCase).count(), 0)
            verify.close()
            scripts = Path(main_program) / "testcase_database" / "scripts"
            self.assertFalse(scripts.exists() and any(scripts.iterdir()))
        engine.dispose()

    def test_fork_tc_cleans_dirs_on_copy_and_commit_failure(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        session.add_all([Project(id="g", name="Golden_Project"), ProjectPlan(id="plan_golden", project_id="g", name="plan_golden"), Project(id="t", name="Target"), ProjectPlan(id="target", project_id="t", name="Target"), Category(id="cat_fork", name="Custom"), TestCase(system_id="gold", family_id="fam", display_name="Fork Me", plan_id="plan_golden", category_id="cat_fork", script_path="testcase_database.scripts.gold")])
        session.commit(); session.close()
        with tempfile.TemporaryDirectory() as main_program:
            source_dir = Path(main_program) / "testcase_database" / "scripts" / "gold"
            source_dir.mkdir(parents=True); (source_dir / "__testcase__.py").write_text("STEPS=[]", encoding="utf-8")
            with patch.object(app_module, "DbSession", Session), patch.object(app_module, "MAIN_PROGRAM_DIR", main_program), patch("shutil.copy2", side_effect=OSError("copy failed")):
                response = app.test_client().post("/api/fork_tc", json={"plan_id":"target", "category":"Custom", "testcase":"Fork Me"})
            self.assertEqual(response.status_code, 500)
            dirs = [p.name for p in (Path(main_program) / "testcase_database" / "scripts").iterdir()]
            self.assertEqual(dirs, ["gold"])
            with patch.object(app_module, "DbSession", Session), patch.object(app_module, "MAIN_PROGRAM_DIR", main_program), patch.object(Session.class_, "commit", side_effect=RuntimeError("commit failed")):
                response = app.test_client().post("/api/fork_tc", json={"plan_id":"target", "category":"Custom", "testcase":"Fork Me"})
            self.assertEqual(response.status_code, 500)
            dirs = [p.name for p in (Path(main_program) / "testcase_database" / "scripts").iterdir()]
            self.assertEqual(dirs, ["gold"])
        engine.dispose()

    def test_frontend_uses_backend_name_key_and_library_failure_retry_contract(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIn("candidate?.name_key", html)
        self.assertIn("full?.name_key", html)
        self.assertIn("${tc.id}", html)
        self.assertIn("libraryLoadError", html)
        self.assertIn("Unable to load Golden Plan library", html)
        self.assertIn("Retry", html)
        self.assertIn("if (!r.ok) throw new Error", html)
        self.assertIn(
            'onclick="renderLibrary().then(renderPlanLibraryDrawer)">Retry',
            html,
        )

    def test_import_overwrite_restores_script_when_commit_fails(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        session.add_all([
            Project(id="overwrite_project", name="Overwrite Project"),
            ProjectPlan(id="overwrite_plan", project_id="overwrite_project", name="Overwrite Plan"),
            Category(id="overwrite_category", name="Custom"),
            TestCase(system_id="overwrite_tc", family_id="overwrite_family", display_name="Original Name", plan_id="overwrite_plan", category_id="overwrite_category", script_path="testcase_database.scripts.overwrite_tc"),
        ])
        session.commit(); session.close()
        with tempfile.TemporaryDirectory() as main_program:
            script_dir = Path(main_program) / "testcase_database" / "scripts" / "overwrite_tc"
            script_dir.mkdir(parents=True)
            script_file = script_dir / "__testcase__.py"
            original_bytes = b"# original bytes\r\nSTEPS = []\r\n"
            script_file.write_bytes(original_bytes)
            with patch.object(app_module, "DbSession", Session), patch.object(app_module, "MAIN_PROGRAM_DIR", main_program), patch.object(Session.class_, "commit", side_effect=RuntimeError("forced commit failure")):
                response = app.test_client().post("/api/import_tc", json={"plan_id":"overwrite_plan", "project":"Overwrite Project", "category":"Custom", "tc_name":"Changed Name", "overwrite":True, "original_id":"overwrite_tc", "steps":[{"module_path":"changed"}]})
            self.assertEqual(response.status_code, 500)
            self.assertEqual(script_file.read_bytes(), original_bytes)
            verify = Session()
            self.assertEqual(verify.query(TestCase).filter_by(system_id="overwrite_tc").one().display_name, "Original Name")
            verify.close()
        engine.dispose()

    def test_fresh_workspace_bootstraps_current_database_schema(self):
        with tempfile.TemporaryDirectory() as workspace:
            env = os.environ.copy()
            env["BMC_WEB_UI_WORKSPACE_DIR"] = workspace
            env["PYTHONPATH"] = os.pathsep.join(
                (str(WEB_UI_DIR), str(REPO_ROOT / "main_program"))
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    (
                        "from app import app; "
                        "response = app.test_client().get('/api/projects'); "
                        "print(response.status_code); "
                        "print(response.get_data(as_text=True)); "
                        "raise SystemExit(0 if response.status_code == 200 else 1)"
                    ),
                ],
                cwd=WEB_UI_DIR,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            database_path = Path(workspace) / "testcase_meta.db"
            self.assertTrue(
                database_path.is_file(),
                "app ignored BMC_WEB_UI_WORKSPACE_DIR and did not create a fresh database",
            )
            with closing(sqlite3.connect(database_path)) as connection:
                project_columns = {
                    row[1]
                    for row in connection.execute("PRAGMA table_info(projects)")
                }

        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        self.assertIn("200", result.stdout)
        self.assertEqual(project_columns, {"id", "name"})

    def test_fork_tc_blocks_only_normalized_exact_version_duplicates(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            golden_project = Project(id="proj_golden", name="Golden_Project")
            target_project = Project(id="proj_target", name="Target_Project")
            golden_plan = ProjectPlan(
                id="plan_golden",
                project_id=golden_project.id,
                name="Golden Plan",
            )
            target_plan = ProjectPlan(
                id="plan_target",
                project_id=target_project.id,
                name="Target Plan",
            )
            category = Category(id="cat_chassis", name="Resource_Chassis")
            golden_v2 = TestCase(
                system_id="golden_v2",
                family_id="family_led",
                display_name="Indicator_LED_Control_V2",
                plan_id=golden_plan.id,
                category_id=category.id,
                script_path="testcase_database.scripts.golden_v2",
            )
            golden_v3 = TestCase(
                system_id="golden_v3",
                family_id="family_led",
                display_name="Indicator_LED_Control_V3",
                plan_id=golden_plan.id,
                category_id=category.id,
                script_path="testcase_database.scripts.golden_v3",
            )
            existing_v2 = TestCase(
                system_id="target_v2",
                family_id="family_led",
                display_name="  indicator_led_control_v2  ",
                plan_id=target_plan.id,
                category_id=category.id,
                script_path="testcase_database.scripts.target_v2",
            )
            session.add_all(
                [
                    golden_project,
                    target_project,
                    golden_plan,
                    target_plan,
                    category,
                    golden_v2,
                    golden_v3,
                    existing_v2,
                ]
            )
            session.commit()
        finally:
            session.close()

        with tempfile.TemporaryDirectory() as main_program:
            scripts_root = (
                Path(main_program) / "testcase_database" / "scripts"
            )
            for script_id in ("golden_v2", "golden_v3"):
                script_dir = scripts_root / script_id
                script_dir.mkdir(parents=True)
                (script_dir / "__testcase__.py").write_text(
                    "STEPS = []\n",
                    encoding="utf-8",
                )

            with (
                patch.object(app_module, "DbSession", Session),
                patch.object(app_module, "MAIN_PROGRAM_DIR", main_program),
            ):
                client = app.test_client()
                duplicate = client.post(
                    "/api/fork_tc",
                    json={
                        "project": "Target_Project",
                        "plan_id": "plan_target",
                        "category": "Resource_Chassis",
                        "testcase": "Indicator_LED_Control_V2",
                    },
                )
                other_version = client.post(
                    "/api/fork_tc",
                    json={
                        "project": "Target_Project",
                        "plan_id": "plan_target",
                        "category": "Resource_Chassis",
                        "testcase": "Indicator_LED_Control_V3",
                    },
                )

        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(duplicate.get_json()["reason"], "same_name")
        self.assertEqual(other_version.status_code, 200)
        self.assertEqual(other_version.get_json()["family_id"], "family_led")

        verify = Session()
        try:
            versions = {
                tc.display_name: tc.family_id
                for tc in verify.query(TestCase)
                .filter_by(plan_id="plan_target")
                .all()
            }
        finally:
            verify.close()
            engine.dispose()

        self.assertEqual(
            versions,
            {
                "  indicator_led_control_v2  ": "family_led",
                "Indicator_LED_Control_V3": "family_led",
            },
        )

    def test_push_to_golden_blocks_only_normalized_exact_version_duplicates(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            golden_project = Project(id="proj_golden", name="Golden_Project")
            target_project = Project(id="proj_target", name="Target_Project")
            golden_plan = ProjectPlan(
                id="plan_golden",
                project_id=golden_project.id,
                name="plan_golden",
            )
            target_plan = ProjectPlan(
                id="plan_target",
                project_id=target_project.id,
                name="Target Plan",
            )
            category = Category(id="cat_chassis", name="Resource_Chassis")
            golden_v2 = TestCase(
                system_id="golden_v2",
                family_id="family_led",
                display_name="Indicator_LED_Control_V2",
                plan_id=golden_plan.id,
                category_id=category.id,
                script_path="testcase_database.scripts.golden_v2",
            )
            target_v2 = TestCase(
                system_id="target_v2",
                family_id="family_led",
                display_name=" indicator_led_control_v2 ",
                plan_id=target_plan.id,
                category_id=category.id,
                script_path="testcase_database.scripts.target_v2",
            )
            target_v3 = TestCase(
                system_id="target_v3",
                family_id="family_led",
                display_name="Indicator_LED_Control_V3",
                plan_id=target_plan.id,
                category_id=category.id,
                script_path="testcase_database.scripts.target_v3",
            )
            session.add_all(
                [
                    golden_project,
                    target_project,
                    golden_plan,
                    target_plan,
                    category,
                    golden_v2,
                    target_v2,
                    target_v3,
                ]
            )
            session.commit()
        finally:
            session.close()

        with tempfile.TemporaryDirectory() as main_program:
            scripts_root = Path(main_program) / "testcase_database" / "scripts"
            for script_id in ("target_v2", "target_v3"):
                script_dir = scripts_root / script_id
                script_dir.mkdir(parents=True)
                (script_dir / "__testcase__.py").write_text(
                    "STEPS = []\n",
                    encoding="utf-8",
                )

            with (
                patch.object(app_module, "DbSession", Session),
                patch.object(app_module, "MAIN_PROGRAM_DIR", main_program),
            ):
                client = app.test_client()
                duplicate = client.post(
                    "/api/push_to_golden", json={"system_id": "target_v2"}
                )
                other_version = client.post(
                    "/api/push_to_golden", json={"system_id": "target_v3"}
                )

        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(duplicate.get_json()["reason"], "same_name")
        self.assertEqual(other_version.status_code, 200)

        verify = Session()
        try:
            versions = {
                tc.display_name: tc.family_id
                for tc in verify.query(TestCase)
                .filter_by(plan_id="plan_golden")
                .all()
            }
        finally:
            verify.close()
            engine.dispose()

        self.assertEqual(
            versions,
            {
                "Indicator_LED_Control_V2": "family_led",
                "Indicator_LED_Control_V3": "family_led",
            },
        )

    def test_import_tc_syncs_version_to_golden(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            target_project = Project(id="proj_target", name="Target_Project")
            target_plan = ProjectPlan(
                id="plan_target",
                project_id=target_project.id,
                name="Target Plan",
            )
            category = Category(id="cat_chassis", name="Resource_Chassis")
            session.add_all([target_project, target_plan, category])
            session.commit()
        finally:
            session.close()

        with tempfile.TemporaryDirectory() as main_program:
            with (
                patch.object(app_module, "DbSession", Session),
                patch.object(app_module, "MAIN_PROGRAM_DIR", main_program),
            ):
                response = app.test_client().post(
                    "/api/import_tc",
                    json={
                        "project": "Target_Project",
                        "plan_id": "plan_target",
                        "category": "Resource_Chassis",
                        "tc_name": "Indicator_LED_Control_V3",
                        "family_id": "family_led",
                        "steps": [],
                        "push_to_golden": True,
                    },
                )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["golden_sync"], "added")
        self.assertIsNotNone(payload["golden_id"])

        verify = Session()
        try:
            golden_plan = (
                verify.query(ProjectPlan)
                .join(Project)
                .filter(Project.name == "Golden_Project")
                .filter(ProjectPlan.name == "plan_golden")
                .one()
            )
            target_tc = verify.query(TestCase).filter_by(plan_id="plan_target").one()
            golden_tc = verify.query(TestCase).filter_by(plan_id=golden_plan.id).one()
        finally:
            verify.close()
            engine.dispose()

        self.assertEqual(target_tc.display_name, "Indicator_LED_Control_V3")
        self.assertEqual(golden_tc.display_name, "Indicator_LED_Control_V3")
        self.assertEqual(target_tc.family_id, "family_led")
        self.assertEqual(golden_tc.family_id, "family_led")
        self.assertEqual(golden_tc.system_id, payload["golden_id"])

    def test_import_tc_syncs_version_to_golden_skips_normalized_duplicate(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            golden_project = Project(id="proj_golden", name="Golden_Project")
            target_project = Project(id="proj_target", name="Target_Project")
            golden_plan = ProjectPlan(
                id="plan_golden",
                project_id=golden_project.id,
                name="plan_golden",
            )
            target_plan = ProjectPlan(
                id="plan_target",
                project_id=target_project.id,
                name="Target Plan",
            )
            category = Category(id="cat_chassis", name="Resource_Chassis")
            golden_tc = TestCase(
                system_id="golden_v3",
                family_id="family_led",
                display_name="  indicator_led_control_v3  ",
                plan_id=golden_plan.id,
                category_id=category.id,
                script_path="testcase_database.scripts.golden_v3",
            )
            session.add_all(
                [
                    golden_project,
                    target_project,
                    golden_plan,
                    target_plan,
                    category,
                    golden_tc,
                ]
            )
            session.commit()
        finally:
            session.close()

        with tempfile.TemporaryDirectory() as main_program:
            with (
                patch.object(app_module, "DbSession", Session),
                patch.object(app_module, "MAIN_PROGRAM_DIR", main_program),
            ):
                response = app.test_client().post(
                    "/api/import_tc",
                    json={
                        "project": "Target_Project",
                        "plan_id": "plan_target",
                        "category": "Resource_Chassis",
                        "tc_name": "Indicator_LED_Control_V3",
                        "family_id": "family_led",
                        "steps": [],
                        "push_to_golden": True,
                    },
                )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["golden_sync"], "skipped")
        self.assertIsNone(payload["golden_id"])

        verify = Session()
        try:
            target_tc = verify.query(TestCase).filter_by(plan_id="plan_target").one()
            golden_versions = (
                verify.query(TestCase).filter_by(plan_id="plan_golden").all()
            )
        finally:
            verify.close()
            engine.dispose()

        self.assertEqual(target_tc.display_name, "Indicator_LED_Control_V3")
        self.assertEqual(target_tc.family_id, "family_led")
        self.assertEqual(len(golden_versions), 1)
        self.assertEqual(golden_versions[0].system_id, "golden_v3")

    def test_import_tc_cleans_script_dirs_when_source_validation_fails(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            target_project = Project(id="proj_target", name="Target_Project")
            target_plan = ProjectPlan(
                id="plan_target",
                project_id=target_project.id,
                name="Target Plan",
            )
            category = Category(id="cat_chassis", name="Resource_Chassis")
            source_without_script = TestCase(
                system_id="source_without_script",
                family_id="family_led",
                display_name="Source Without Script",
                plan_id=target_plan.id,
                category_id=category.id,
                script_path="testcase_database.scripts.source_without_script",
            )
            session.add_all(
                [target_project, target_plan, category, source_without_script]
            )
            session.commit()
        finally:
            session.close()

        with tempfile.TemporaryDirectory() as main_program:
            scripts_root = (
                Path(main_program) / "testcase_database" / "scripts"
            )
            with (
                patch.object(app_module, "DbSession", Session),
                patch.object(app_module, "MAIN_PROGRAM_DIR", main_program),
            ):
                client = app.test_client()
                for source_id in ("unknown_source", "source_without_script"):
                    response = client.post(
                        "/api/import_tc",
                        json={
                            "project": "Target_Project",
                            "plan_id": "plan_target",
                            "category": "Resource_Chassis",
                            "tc_name": "Indicator_LED_Control_V3",
                            "system_id": source_id,
                        },
                    )
                    self.assertEqual(response.status_code, 404)
                    self.assertFalse(
                        scripts_root.exists() and any(scripts_root.iterdir())
                    )

        engine.dispose()

    def test_classic_library_uses_exact_version_partial_success(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(
            encoding="utf-8"
        )

        self.assertIn("function normalizeTestCaseName", html)
        self.assertIn("function findExactPlanNameConflict", html)
        self.assertIn("function formatLibraryBatchSummary", html)
        self.assertIn("same version already in plan", html)
        self.assertIn("result.skipped", html)
        self.assertIn("result.failed", html)
        self.assertNotIn("family branches already exist", html)
        self.assertNotIn("Batch add cancelled", html)

    def test_golden_membership_uses_normalized_names_and_save_feedback(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(
            encoding="utf-8"
        )

        membership_start = html.index("function getGoldenPlanMembership(tc)")
        membership_end = html.index("function renderPlanDetailCaseActions", membership_start)
        membership_block = html[membership_start:membership_end]
        self.assertIn("getTestCaseNameKey(candidate)", membership_block)
        self.assertIn("getTestCaseNameKey(tc)", membership_block)
        self.assertNotIn("candidate.family_id === tc.family_id", membership_block)

        classic_start = html.index("let goldenOptionHtml = '';")
        classic_end = html.index("let isMissing =", classic_start)
        classic_block = html[classic_start:classic_end]
        self.assertIn("const alreadyInGolden = getGoldenPlanMembership(tc);", classic_block)
        self.assertNotIn("t.family_id === tc.family_id", classic_block)

        inline_start = html.index("async function saveInlineEdit(")
        inline_end = html.index("//  EMBEDDED TEST CASE BUILDER", inline_start)
        embedded_start = html.index("async function _ebuilderSubmit(")
        embedded_end = html.index("function ebuilderAutoBumpVersionName", embedded_start)
        for save_block in (
            html[inline_start:inline_end],
            html[embedded_start:embedded_end],
        ):
            self.assertIn("resJson.golden_sync", save_block)

        embedded_block = html[embedded_start:embedded_end]
        self.assertIn("msg += `\\n\\n${goldenSyncMessage}`;", embedded_block)

        self.assertIn("Golden Plan: version published.", html)
        self.assertIn(
            "Golden Plan: skipped because the same version already exists.",
            html,
        )

    def test_plan_library_supports_folder_filters_and_persistent_selection(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(
            encoding="utf-8"
        )

        for marker in (
            "Add from Golden Plan",
            "Import Test Case",
            "plan-library-folder-tree",
            "function getPlanLibraryFolderModel",
            "function getVisiblePlanLibraryItems",
            "function setPlanLibraryFolderFilter",
            "function toggleVisiblePlanLibrarySelection",
            "Select all in this folder",
            "test cases selected",
            "Clear selection",
            "Add Selected (",
        ):
            self.assertIn(marker, html)

        self.assertIn("custom_subfolder", html)
        self.assertIn("findExactPlanNameConflict(plan, tc)", html)
        self.assertIn("librarySelectionMessage", html)

    def test_plan_all_cases_hierarchy_and_compact_search_contract(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(
            encoding="utf-8"
        )

        for marker in (
            "plan-custom-child-groups",
            "plan-folder-guide",
            "function clearPlanDetailSearch",
            "Search test cases in this plan",
            "plan-search-icon",
            "plan-search-clear",
        ):
            self.assertIn(marker, html)

        self.assertIn(
            "if (clearButton) clearButton.hidden = true;",
            html,
        )
        self.assertIn(
            ".plan-scope-search-wrap .plan-scope-search",
            html,
        )
        self.assertIn("padding-left:42px", html)
        self.assertNotIn(
            "Drag folders on the left; drag test cases in the list.",
            html,
        )

    def test_plan_testcase_reorder_persists_positions(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            project = Project(id="proj_reorder", name="Reorder Project")
            plan = ProjectPlan(id="plan_reorder", project_id=project.id, name="Reorder Plan")
            cases = [
                TestCase(
                    system_id=f"tc_{index}",
                    family_id=f"family_{index}",
                    display_name=f"Case {index}",
                    plan_id=plan.id,
                    script_path=f"case_{index}.py",
                    position=index,
                )
                for index in range(3)
            ]
            session.add_all([project, plan, *cases])
            session.commit()
            from plan_state import resolve_folder, assign_folder
            folder=resolve_folder(session,plan.id,{"folder_path":"Custom"})
            for tc in session.query(TestCase).filter_by(plan_id=plan.id): assign_folder(session,tc,folder)
            session.commit()
        finally:
            session.close()

        with patch.object(app_module, "DbSession", Session):
            response = app.test_client().post(
                "/api/plans/plan_reorder/testcases/reorder",
                json={"folder_path":"Custom", "order": ["tc_2", "tc_1", "tc_0"]},
            )

        self.assertEqual(response.status_code, 200)
        verify = Session()
        try:
            ordered = (
                verify.query(TestCase)
                .filter_by(plan_id="plan_reorder")
                .order_by(TestCase.position)
                .all()
            )
            self.assertEqual([tc.system_id for tc in ordered], ["tc_2", "tc_1", "tc_0"])
            self.assertEqual([tc.position for tc in ordered], [0, 1, 2])
        finally:
            verify.close()

    def test_plan_testcase_reorder_rejects_invalid_input(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            project = Project(id="proj_validation", name="Validation Project")
            plan = ProjectPlan(id="plan_validation", project_id=project.id, name="Validation Plan")
            testcase = TestCase(
                system_id="tc_validation",
                family_id="family_validation",
                display_name="Validation Case",
                plan_id=plan.id,
                script_path="validation.py",
            )
            session.add_all([project, plan, testcase])
            session.commit()
            from plan_state import resolve_folder, assign_folder
            folder=resolve_folder(session,plan.id,{"folder_path":"Custom"})
            for tc in session.query(TestCase).filter_by(plan_id=plan.id): assign_folder(session,tc,folder)
            session.commit()
        finally:
            session.close()

        with patch.object(app_module, "DbSession", Session):
            client = app.test_client()
            malformed = client.post(
                "/api/plans/plan_validation/testcases/reorder",
                json={"folder_path":"Custom", "order": "tc_validation"},
            )
            duplicate = client.post(
                "/api/plans/plan_validation/testcases/reorder",
                json={"folder_path":"Custom", "order": ["tc_validation", "tc_validation"]},
            )
            incomplete = client.post(
                "/api/plans/plan_validation/testcases/reorder",
                json={"folder_path":"Custom", "order": ["foreign_tc"]},
            )
            missing = client.post(
                "/api/plans/missing_plan/testcases/reorder",
                json={"folder_path":"Custom", "order": []},
            )

        self.assertEqual(malformed.status_code, 400)
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(incomplete.status_code, 400)
        self.assertEqual(missing.status_code, 404)

    def test_frontend_persists_plan_testcase_order(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIn("async function persistCurrentEntityOrder(entity)", html)
        self.assertIn("`${API}/plans/${currentPlanId}/testcases/reorder`", html)
        self.assertIn("await persistCurrentEntityOrder(entity);", html)
        self.assertIn("const orderSnapshot = entity.testcases.slice();", html)
        self.assertIn("entity.testcases = orderSnapshot;", html)

    def test_plan_batch_move_updates_category_and_custom_folder_transactionally(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        session.add_all([
            Project(id="proj_move", name="Move Project"),
            ProjectPlan(id="plan_move", project_id="proj_move", name="Move Plan"),
            Category(id="cat_chassis", name="Resource_Chassis"),
            Category(id="cat_custom", name="Custom"),
            PlanSubfolder(id="folder_ibm", plan_id="plan_move", subfolder_name="IBM"),
            TestCase(system_id="tc_move", family_id="family_move", display_name="Move Me", plan_id="plan_move", category_id="cat_chassis", script_path="move.py"),
            TestCase(system_id="tc_skip", family_id="family_skip", display_name="Already There", plan_id="plan_move", category_id="cat_custom", subfolder_id="folder_ibm", script_path="skip.py"),
        ])
        session.commit()
        session.close()

        with patch.object(app_module, "DbSession", Session):
            response = app.test_client().post(
                "/api/plans/plan_move/testcases/move",
                json={"testcase_ids": ["tc_move", "tc_skip"], "target_key": "custom:IBM"},
            )

        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()['moved'],2)
        self.assertTrue(response.get_json()['folder_id'])
        verify = Session()
        moved = verify.query(TestCase).filter_by(system_id="tc_move").one()
        skipped = verify.query(TestCase).filter_by(system_id="tc_skip").one()
        self.assertEqual(moved.category_id, "cat_custom")
        self.assertEqual(moved.folder_obj.path, "Custom/IBM")
        self.assertEqual(moved.folder_id, skipped.folder_id)
        self.assertTrue(moved.selected)
        self.assertTrue(skipped.selected)
        verify.close()
        engine.dispose()

    def test_plan_batch_move_rejects_missing_members_without_partial_updates(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        session.add_all([
            Project(id="proj_atomic", name="Atomic Project"),
            ProjectPlan(id="plan_atomic", project_id="proj_atomic", name="Atomic Plan"),
            ProjectPlan(id="plan_other", project_id="proj_atomic", name="Other Plan"),
            Category(id="cat_source", name="Source"),
            Category(id="cat_target", name="Target"),
            TestCase(system_id="tc_valid", family_id="family_valid", display_name="Valid", plan_id="plan_atomic", category_id="cat_source", script_path="valid.py"),
            TestCase(system_id="tc_foreign", family_id="family_foreign", display_name="Foreign", plan_id="plan_other", category_id="cat_source", script_path="foreign.py"),
        ])
        session.commit()
        session.close()

        with patch.object(app_module, "DbSession", Session):
            response = app.test_client().post(
                "/api/plans/plan_atomic/testcases/move",
                json={"testcase_ids": ["tc_valid", "tc_foreign"], "target_key": "category:Target"},
            )

        self.assertEqual(response.status_code, 400, response.get_json())
        verify = Session()
        self.assertEqual(
            verify.query(TestCase).filter_by(system_id="tc_valid").one().category_id,
            "cat_source",
        )
        verify.close()
        engine.dispose()

    def test_plan_batch_move_validates_request_destination_and_project_lock(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        session.add_all([
            Project(id="proj_guard", name="Guard Project"),
            ProjectPlan(id="plan_guard", project_id="proj_guard", name="Guard Plan"),
            Category(id="cat_guard", name="Guard"),
            TestCase(system_id="tc_guard", family_id="family_guard", display_name="Guarded", plan_id="plan_guard", category_id="cat_guard", script_path="guard.py"),
        ])
        session.commit()
        session.close()

        with patch.object(app_module, "DbSession", Session):
            client = app.test_client()
            malformed = client.post(
                "/api/plans/plan_guard/testcases/move",
                json={"testcase_ids": "tc_guard", "target_key": "category:Guard"},
            )
            duplicate = client.post(
                "/api/plans/plan_guard/testcases/move",
                json={"testcase_ids": ["tc_guard", "tc_guard"], "target_key": "category:Guard"},
            )
            missing_folder = client.post(
                "/api/plans/plan_guard/testcases/move",
                json={"testcase_ids": ["tc_guard"], "folder_id": "missing"},
            )
            with Session() as lock_session:
                lock_session.add(Task(id="active",plan_id="plan_guard",name="Active",execution_active=True)); lock_session.commit()
            try:
                locked = client.post(
                    "/api/plans/plan_guard/testcases/move",
                    json={"testcase_ids": ["tc_guard"], "target_key": "category:Guard"},
                )
            finally:
                with Session() as lock_session:
                    lock_session.get(Task,"active").execution_active=False; lock_session.commit()

        self.assertEqual(malformed.status_code, 400)
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(missing_folder.status_code, 404)
        self.assertEqual(locked.status_code, 409)
        engine.dispose()

    def test_rename_plan_keeps_plan_detail_open(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
        start = html.index("async function renamePlan(pid)")
        end = html.index("async function deletePlan", start)
        block = html[start:end]

        self.assertNotIn("currentPlanId = newName.trim();", block)
        self.assertNotIn("selectPlan(currentPlanId, true);", block)
        self.assertIn("const sourceView = currentViewId;", block)
        self.assertIn("currentPlanId = pid;", block)
        self.assertIn("if (sourceView === 'plan-detail')", block)
        self.assertIn("renderPlanDetail();", block)
        self.assertNotIn("planDetailState.activePlanId = null;", block)

    def test_golden_plan_publish_uses_backend_contract(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
        start = html.index("async function addSingleTcToGolden(realIdx)")
        end = html.index("let dragSrcIdx", start)
        block = html[start:end]

        self.assertIn("body: JSON.stringify({ system_id: tcMeta.id })", block)
        self.assertIn("const payload = await res.json().catch(() => ({}));", block)
        self.assertIn("payload.error || `HTTP ${res.status}`", block)
        self.assertIn(
            "await Promise.all([reloadProjects(), refreshAllTestcases()]);",
            block,
        )
        self.assertIn("renderPlanDetail();", block)

    def test_plan_folder_grid_and_full_sidebar_collapse_contract(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn(
            ".plan-tree-node { display:grid; grid-template-columns:18px minmax(0,1fr) 28px minmax(54px,auto);",
            html,
        )
        self.assertIn(".plan-tree-name { min-width:0; overflow-wrap:anywhere;", html)
        self.assertIn('class="plan-tree-icon"', html)
        self.assertIn('class="plan-tree-name"', html)
        self.assertIn('class="plan-tree-end"', html)
        self.assertIn(
            "body.app-nav-collapsed .app-sidebar {\n      width: 0;\n      border-right: 0;\n      overflow: hidden;",
            html,
        )
        self.assertNotIn(
            "body.app-nav-collapsed .app-sidebar {\n      width: 72px;",
            html,
        )

    def test_plan_folder_panel_has_shared_resizable_width_and_independent_scroll(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn("const PLAN_FOLDER_WIDTH_KEY = 'testPlanWorkspace.navigatorWidth'", html)
        self.assertIn('class="plan-folder-resize-handle"', html)
        self.assertIn("startPlanFolderResize(event)", html)
        self.assertIn("localStorage.setItem(PLAN_FOLDER_WIDTH_KEY", html)
        self.assertIn(".plan-folder-tree { position:sticky;", html)
        self.assertIn("display:flex; flex-direction:column", html)
        self.assertIn(".plan-tree-list { min-height:0; overflow-y:auto;", html)

    def test_plan_pointer_drag_rows_replace_native_testcase_drag_handlers(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
        start = html.index("function renderPlanDetailRows(cases)")
        end = html.index("function togglePlanDetailGroup", start)
        rows = html[start:end]

        self.assertIn('data-plan-tc-index="${tc.realIdx}"', rows)
        self.assertIn(
            'onpointerdown="startPlanTcPointerDrag(event, ${tc.realIdx})"',
            rows,
        )
        for native_handler in (
            'draggable="true"',
            "ondragstart",
            "ondragend",
            "ondragover",
            "ondrop",
        ):
            self.assertNotIn(native_handler, rows)

    def test_plan_pointer_drag_uses_hit_testing_wheel_and_folder_data_keys(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn("document.elementFromPoint(clientX, clientY)", html)
        self.assertIn("PlanWorkspaceInteractions.classifyPointerDropTarget(element)", html)
        self.assertIn("function handlePlanPointerDragWheel(event)", html)
        self.assertIn(
            "document.addEventListener('wheel', handlePlanPointerDragWheel, { passive: false, capture: true })",
            html,
        )
        self.assertIn('data-plan-drop-key="${escapeHtml(folder.key)}"', html)
        self.assertIn('data-plan-drop-key="${escapeHtml(folder.key)}"', html)
        self.assertIn('data-plan-drop-key="${escapeHtml(group.key)}"', html)

    def test_plan_pointer_drag_cancels_on_escape_blur_and_pointercancel(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn("function cancelPlanTcPointerDrag()", html)
        self.assertIn(
            "document.addEventListener('pointercancel', handlePlanTcPointerCancel)",
            html,
        )
        self.assertIn("if (event.key === 'Escape') cancelPlanTcPointerDrag();", html)
        self.assertIn("window.addEventListener('blur', cancelPlanTcPointerDrag)", html)
        self.assertIn("planTcPointerDrag.preview?.remove()", html)
        self.assertIn("planTcPointerDrag.sourceElement?.classList.remove", html)
        self.assertIn("planDragScrollController?.stop()", html)

    def test_plan_pointer_drag_cancels_before_view_change(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
        start = html.index("function showView(viewId, options = {})")
        end = html.index("function stateFromLocation", start)
        show_view = html[start:end]

        self.assertIn("cancelPlanTcPointerDrag();", show_view)
        self.assertLess(
            show_view.index("cancelPlanTcPointerDrag();"),
            show_view.index("currentViewId = viewId;"),
        )

    def test_plan_tree_drag_feedback_is_neutral_and_has_no_destination_label(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
        drag_start = html.index("function dragTcStart(event, idx)")
        drag_end = html.index("async function persistCurrentEntityOrder", drag_start)
        tree_start = html.index("function renderPlanFolderTree(plan)")
        tree_end = html.index("function getGoldenPlanMembership", tree_start)
        tree = html[tree_start:tree_end]

        self.assertIn(".plan-tree-node.tc-drop-target", html)
        self.assertIn(".plan-tree-node.folder-drop-target", html)
        self.assertNotIn(".plan-tree-drop-label", html)
        self.assertNotIn("Move to ${", html)
        self.assertIn("background:#374151", html)
        self.assertNotIn(".plan-tree-node.tc-drop-target { background:rgba(99, 102, 241", html)
        self.assertIn("showPlanTreeDropFeedback(this", html)
        self.assertIn("clearPlanTreeDropFeedbackOnLeave(event)", html)
        self.assertIn("clearAllPlanTreeDropFeedback()", html[drag_start:drag_end])

        for handler in ("ondragenter", "ondragover", "ondragleave", "ondrop"):
            self.assertGreaterEqual(tree.count(handler), 1)
        self.assertGreaterEqual(
            tree.count('draggable="${!locked}" ondragstart="startPlanFolderDrag'),
            1,
        )

    def test_plan_tree_drag_feedback_rejects_invalid_folder_targets_and_nested_leaves(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
        feedback_start = html.index("function isPlanFolderDropTargetCompatible")
        feedback_end = html.index("function handlePlanTreeDrop", feedback_start)
        feedback = html[feedback_start:feedback_end]
        tree_start = html.index("function renderPlanFolderTree(plan)")
        tree_end = html.index("function getGoldenPlanMembership", tree_start)
        tree = html[tree_start:tree_end]

        self.assertIn("sourceKey === targetKey", feedback)
        self.assertIn("`folder:${f.id}`===sourceKey", feedback)
        self.assertIn("`folder:${f.id}`===targetKey", feedback)
        self.assertIn(
            "!isPlanFolderDropTargetCompatible(planFolderDragKey, targetKey)",
            feedback,
        )
        self.assertIn("event.currentTarget?.contains(event.relatedTarget)", feedback)
        self.assertIn("clearPlanTreeDropFeedbackOnLeave(event)", tree)

    def test_plan_tree_dragover_accepts_only_valid_drop_targets(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
        tree_start = html.index("function renderPlanFolderTree(plan)")
        tree_end = html.index("function getGoldenPlanMembership", tree_start)
        tree = html[tree_start:tree_end]
        handler_start = html.index("function handlePlanTreeDragOver(event, target, targetKey)")
        handler_end = html.index("function handlePlanTreeDrop", handler_start)
        handler = html[handler_start:handler_end]

        self.assertNotIn("ondragover=\"event.preventDefault();", tree)
        self.assertGreaterEqual(
            tree.count("ondragover=\"handlePlanTreeDragOver(event, this,"),
            1,
        )
        feedback_gate = handler.index(
            "if (!showPlanTreeDropFeedback(target, targetKey)) return;"
        )
        prevent_default = handler.index("event.preventDefault();")
        self.assertLess(feedback_gate, prevent_default)

    def test_plan_tree_drag_feedback_serializes_quote_bearing_folder_keys(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
        tree_start = html.index("function renderPlanFolderTree(plan)")
        tree_end = html.index("function getGoldenPlanMembership", tree_start)
        tree = html[tree_start:tree_end]
        drag_start = html.index("function dragTcStart(event, idx)")
        drag_end = html.index("async function persistCurrentEntityOrder", drag_start)

        self.assertIn("function planTreeHandlerKey(key)", html)
        self.assertIn("return escapeHtml(JSON.stringify(key));", html)
        self.assertIn("planTreeHandlerKey(folder.key)", tree)
        self.assertIn("planTreeHandlerKey(folder.key)", tree)
        self.assertNotIn("'custom:${escapeHtml(folder.name)}'", tree)
        self.assertIn("dragSrcIdx = null;", html[drag_start:drag_end])

    def test_middle_plan_group_quote_bearing_key_has_compilable_handlers(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
        render_start = html.index("function renderPlanCaseGroupSection(group")
        render_end = html.index("function renderPlanAllCaseHierarchy", render_start)
        render = html[render_start:render_end]

        self.assertIn(
            'onclick="togglePlanDetailGroup(${planTreeHandlerKey(group.key)})"',
            render,
        )
        self.assertIn(
            'data-plan-drop-key="${escapeHtml(group.key)}"',
            render,
        )
        for native_handler in ("ondragenter", "ondragover", "ondragleave", "ondrop"):
            self.assertNotIn(native_handler, render)
        self.assertNotIn("'${escapeHtml(group.key)}'", render)

    def test_all_folders_use_stable_exclusive_direct_membership(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
        start = html.index("function getPlanFolderModel(plan)")
        end = html.index("function setPlanDetailFolderFilter", start)
        block = html[start:end]
        self.assertIn('String(tc.folder_id)===String(folder.id)', block)
        self.assertIn('plan.folders || []', block)
        self.assertNotIn('custom_subfolder', block)
        self.assertNotIn('category_order', block)

    def test_plan_detail_has_plan_wide_testcase_search(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn("searchQuery: ''", html)
        self.assertIn("function setPlanDetailSearchQuery(value)", html)
        self.assertIn("function getPlanSearchResults(plan, query)", html)
        self.assertIn(
            "Search test cases in this plan",
            html,
        )
        self.assertIn("plan-search-results", html)
        self.assertIn("No test cases match this search.", html)

    def test_plan_search_updates_results_without_replacing_search_input(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
        start = html.index("function setPlanDetailSearchQuery(value)")
        end = html.index("function getPlanSearchResults", start)
        block = html[start:end]

        self.assertIn(
            "casePane.outerHTML = renderPlanFolderTree(plan);",
            block,
        )
        self.assertNotIn("renderPlanDetail();", block)

    def test_plan_group_headers_are_pointer_folder_targets_when_empty(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn(
            'data-plan-drop-key="${escapeHtml(group.key)}"',
            html,
        )
        self.assertIn(
            "async function commitPlanTcPointerFolderDrop(identity)",
            html,
        )
        start = html.index("async function commitPlanTcPointerFolderDrop")
        end = html.index("async function finishPlanTcPointerDrag", start)
        block = html[start:end]
        self.assertIn("runPlanPointerFolderCommit(", block)
        self.assertIn("getPlanPointerCommitDependencies()", block)

    def test_plan_detail_row_menu_and_batch_move_dialog_contract(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
        actions_start = html.index("function renderPlanDetailCaseActions")
        actions_end = html.index("function renderPlanRowActionsPortal(plan)", actions_start)
        actions = html[actions_start:actions_end]
        self.assertIn("function renderPlanRowActionsPortal(plan)", html)
        portal_start = html.index("function renderPlanRowActionsPortal(plan)")
        portal_end = html.index("function renderPlanDetailRows", portal_start)
        portal = html[portal_start:portal_end]
        drop_start = html.index("async function dropPlanTcIntoFolder")
        drop_end = html.index("function dropPlanDetailTc", drop_start)
        drop = html[drop_start:drop_end]

        self.assertIn("actionMenuRealIdx", html)
        self.assertIn("moveDialog", html)
        self.assertIn("In Golden Plan", actions)
        self.assertIn("&#8942;", actions)
        self.assertNotIn("plan-row-menu", actions)
        self.assertIn("Move selected", portal)
        self.assertIn("openPlanTcEditor(${realIdx})", portal)
        self.assertIn("deleteTC(${realIdx})", portal)
        self.assertIn("${renderPlanRowActionsPortal(plan)}", html)
        self.assertIn('id="plan-move-dialog"', html)
        self.assertIn("Search folders", html)
        self.assertIn("submitPlanTestCaseMove()", html)
        self.assertIn("/testcases/move`", html)
        self.assertNotIn("`${API}/move_tc`", drop)

    def test_plan_workspace_interaction_asset_uses_the_flask_static_root(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
        with closing(app.test_client().get("/plan_workspace_interactions.js")) as response:
            self.assertEqual(response.status_code, 200)
        self.assertIn('src="/plan_workspace_interactions.js"', html)
        self.assertNotIn('src="/static/plan_workspace_interactions.js"', html)

    def test_plan_row_actions_float_outside_table_overflow(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
        table_wrap_start = html.index(".plan-detail-table-wrap {")
        table_wrap_end = html.index("}", table_wrap_start)
        table_wrap = html[table_wrap_start:table_wrap_end]

        self.assertIn(".plan-row-menu { position:fixed;", html)
        self.assertIn("overflow:visible;", table_wrap)
        self.assertIn(".plan-case-group .tc-table { table-layout:fixed; width:100%; }", html)
        self.assertIn("actionMenuPosition", html)
        self.assertIn("event.currentTarget.getBoundingClientRect()", html)
        self.assertIn("PlanWorkspaceInteractions.getFloatingMenuPosition(", html)
        self.assertIn("window.addEventListener('blur', closePlanRowActions)", html)

    def test_plan_pointer_drag_wheel_uses_capture_and_group_headers_have_neutral_feedback(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn("document.addEventListener('wheel', handlePlanPointerDragWheel, { passive: false, capture: true })", html)
        self.assertIn("document.removeEventListener('wheel', handlePlanPointerDragWheel, true)", html)
        self.assertIn(".plan-case-group-header.tc-drop-target { background:#374151;", html)
        self.assertIn('data-plan-drop-key="${escapeHtml(group.key)}"', html)

    def test_left_plan_tree_routes_testcases_through_generalized_drop_handler(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
        start = html.index("function handlePlanTreeDrop(event, targetKey)")
        end = html.index("function closePlanAddMenu()", start)
        handler = html[start:end]

        self.assertIn("dropPlanTcIntoFolder(event, targetKey)", handler)
        self.assertNotIn("dropTcInCustom", handler)
        self.assertNotIn("dropPlanDetailTc", handler)
        self.assertIn("movePlanFolder(planFolderDragKey, targetKey,", handler)

        tree_start = html.index("function renderPlanFolderTree(plan)")
        tree_end = html.index("function renderPlanCaseGroups(plan)", tree_start)
        tree = html[tree_start:tree_end]
        self.assertIn(
            "ondrop=\"handlePlanTreeDrop(event,${planTreeHandlerKey(folder.key)})\"",
            tree,
        )
        self.assertIn(
            "ondrop=\"handlePlanTreeDrop(event,${planTreeHandlerKey(folder.key)})\"",
            tree,
        )

    def test_plan_ordering_model_contract(self):
        self.assertTrue(hasattr(ProjectPlan, "category_order"))
        self.assertTrue(hasattr(PlanSubfolder, "position"))
        self.assertTrue(hasattr(TestCase, "position"))

    def test_plan_patch_accepts_ordering_contract(self):
        source = (WEB_UI_DIR / "app.py").read_text(encoding="utf-8")
        patch_start = source.index("def patch_plan(plan_id):")
        patch_end = source.index("# API CRUD", patch_start)
        block = source[patch_start:patch_end]
        self.assertIn('if "category_order" in data:', block)
        self.assertIn("folder.position = idx", block)

    def test_plan_detail_workspace_parity_contract(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
        for signature in (
            "const planDetailState =",
            "function renameCurrentPlan()",
            "function getPlanFolderModel(plan)",
            "function renderPlanFolderTree(plan)",
            "function renderPlanCaseGroups(plan)",
            "function movePlanFolder(sourceKey,targetKey,",
            "function dropPlanDetailTc(event, target)",
            "function handlePlanTreeDrop(event, targetKey)",
            "function openPlanLibraryDrawer()",
            "function closePlanLibraryDrawer()",
            "function renderPlanLibraryDrawer()",
            "function addSelectedPlanLibraryCases()",
            "function getGoldenPlanMembership(tc)",
            "function renderPlanDetailCaseActions(realIdx, tc)",
        ):
            self.assertIn(signature, html)
        self.assertIn('id="plan-library-drawer"', html)
        self.assertIn("plan-detail-grid plan-workspace-grid", html)
        self.assertIn(".plan-workspace-grid { grid-template-columns:1fr; }", html)
        self.assertIn("All Test Cases", html)
        self.assertNotIn("Native categories cannot be renamed", html)
        self.assertIn("Rename folder", html)
        detail_start = html.index("function renderPlanDetail()")
        detail_end = html.index("async function openPlanDetail", detail_start)
        detail = html[detail_start:detail_end]
        for copy in (
            "Generate Summary Report",
            "Export Selected",
            "Import Test Case",
            "+ Add Test Case",
        ):
            self.assertIn(copy, detail)
        self.assertNotIn("Delete Plan", detail)
        self.assertNotIn("+ Create Task", detail)
        self.assertIn(
            "result.added > 0 && result.skipped === 0 && result.failed === 0",
            html,
        )

    def test_plan_detail_actions_stay_on_one_line(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn(
            ".plan-case-group .plan-case-actions { text-align:right; white-space:nowrap; }",
            html,
        )
        self.assertIn(
            ".plan-case-actions-inline { display:inline-flex; align-items:center; justify-content:flex-end; gap:6px; white-space:nowrap; }",
            html,
        )
        self.assertIn(
            ".plan-case-group .plan-case-actions-col { width:220px; text-align:right; }",
            html,
        )
        self.assertIn(
            ".plan-case-actions .plan-golden-action { white-space:nowrap; flex:0 0 auto; }",
            html,
        )
        self.assertIn(
            ".plan-row-actions { position:relative; display:inline-flex; flex:0 0 28px; width:28px; align-items:center; justify-content:flex-end; }",
            html,
        )
        self.assertIn('class="btn-text plan-golden-action"', html)
        self.assertIn('class="plan-case-actions-inline"', html)

    def test_plan_library_results_use_aligned_columns(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")

        for class_name in (
            "plan-library-table-head",
            "plan-library-result-row",
            "plan-library-result-name",
            "plan-library-result-folder",
            "plan-library-result-status",
        ):
            self.assertIn(class_name, html)
        self.assertIn("grid-template-columns:28px minmax(180px,1.4fr) minmax(150px,1fr) 112px", html)
        self.assertIn("<span>Test Case</span><span>Folder</span><span>Status</span>", html)
        self.assertIn('title="${escapeHtml(tc.tc_name)}"', html)
        self.assertIn("const folderPath = getPlanLibraryItemPath(tc);", html)
        self.assertIn('title="${escapeHtml(folderPath)}"', html)

    def test_classic_view_switches_renderer_context_before_render(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
        start = html.index("function openClassicPlanView()")
        end = html.index("function openPlanTcEditor", start)
        block = html[start:end]
        self.assertIn("showView('plan-detail')", block)
        self.assertNotIn("Classic View", html)

    def test_projects_exposes_tasks_without_builds_alias(self):
        client = app.test_client()
        response = client.get("/api/projects")

        self.assertEqual(response.status_code, 200)
        projects = response.get_json().get("projects", [])
        self.assertGreaterEqual(len(projects), 1)

        plans = [plan for project in projects for plan in project.get("plans", [])]
        self.assertGreaterEqual(len(plans), 1)

        for plan in plans:
            self.assertIn("tasks", plan)
            self.assertNotIn("builds", plan)

    def test_frontend_has_task_navigation_state_alias(self):
        html_path = os.path.join(str(WEB_UI_DIR), "static", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn("let currentTaskId = null;", html)
        self.assertIn("function setCurrentTaskId(taskId)", html)
        self.assertIn("function getCurrentTaskId()", html)

    def test_frontend_prefers_task_named_entrypoints(self):
        html_path = os.path.join(str(WEB_UI_DIR), "static", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn("async function selectTask(planId, taskId)", html)
        self.assertIn("async function openTaskDetail(planId, taskId)", html)
        self.assertIn("async function newTask()", html)
        self.assertIn("function downloadTaskPDFReport(taskId)", html)
        self.assertIn("return newTask();", html)
        self.assertNotIn("function selectBuild", html)
        self.assertNotIn("function openBuildDetail", html)
        self.assertNotIn("function downloadBuildPDFReport", html)

    def test_frontend_uses_task_local_variable_names_for_task_contexts(self):
        html_path = os.path.join(str(WEB_UI_DIR), "static", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn("let isTask = false;", html)
        self.assertIn("Current Task Summary Reports:", html)
        self.assertIn("function downloadTaskPDFReport(taskId)", html)
        self.assertNotIn("let isBuild", html)
        self.assertNotIn("const isBuild", html)
        self.assertNotIn("function renderInlineSteps(isBuild)", html)
        self.assertNotIn("lastBuild", html)
        self.assertNotIn("downloadBuildPDFReport", html)

    def test_frontend_prefers_task_named_detail_helpers(self):
        html_path = os.path.join(str(WEB_UI_DIR), "static", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn("function renderTaskDetailRows(task)", html)
        self.assertIn("saveTaskResults(entity);", html)
        self.assertNotIn("function renderBuildDetail", html)
        self.assertNotIn("function renderBuildDetailRows", html)
        self.assertNotIn("function openExecutionFromBuildDetail", html)
        self.assertNotIn("function saveBuildResults", html)
        self.assertNotIn("function loadBuildResults", html)

    def test_frontend_prefers_task_named_execution_helpers(self):
        html_path = os.path.join(str(WEB_UI_DIR), "static", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn("let taskLogBuffer = [];", html)
        self.assertIn("let taskApiLogBuffer = [];", html)
        self.assertIn("function getTaskSetup(task)", html)
        self.assertIn("async function updateTaskSetupField(field, value)", html)
        self.assertNotIn("function getBuildSetup", html)
        self.assertNotIn("function updateBuildSetupField", html)

    def test_frontend_uses_current_task_id_without_build_alias_state(self):
        html_path = os.path.join(str(WEB_UI_DIR), "static", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn("let currentTaskId = null;", html)
        self.assertIn("function getCurrentTaskId()", html)
        self.assertNotIn("currentBuildId", html)
        self.assertNotIn("nav_build_id", html)
        self.assertNotIn("params.get('build_id')", html)
        self.assertNotIn('"build-detail"', html)

    def test_frontend_init_reports_real_project_load_errors(self):
        html_path = os.path.join(str(WEB_UI_DIR), "static", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn("if (!r.ok) throw new Error(`GET /api/projects failed: ${r.status}`);", html)
        self.assertIn('console.error("Unable to load project data", e);', html)
        self.assertIn("${e.message || e}", html)

    def test_frontend_defines_normalize_view_id_for_init_navigation(self):
        html_path = os.path.join(str(WEB_UI_DIR), "static", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn("function normalizeViewId(viewId)", html)
        self.assertIn("'dashboard'", html)
        self.assertIn("'workspace'", html)
        self.assertIn("'plan-detail'", html)
        self.assertIn("'task-detail'", html)
        self.assertIn("'execution-detail'", html)
        self.assertIn("return allowedViews.has(normalized) ? normalized : 'dashboard';", html)

    def test_frontend_restore_navigation_guards_missing_plan_before_task_lookup(self):
        html_path = os.path.join(str(WEB_UI_DIR), "static", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        restore_start = html.index("function restoreNavigationState(state)")
        restore_end = html.index("function renderProjectSelect()", restore_start)
        restore_block = html[restore_start:restore_end]

        self.assertIn("const activePlan = proj.plans.find", restore_block)
        self.assertIn("const task = activePlan ? getPlanTasks(activePlan).find", restore_block)
        self.assertNotIn("const task = getPlanTasks(plan).find", restore_block)

    def test_frontend_removes_task_detail_build_compat_wrappers(self):
        html_path = os.path.join(str(WEB_UI_DIR), "static", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn("function getCurrentTaskContext()", html)
        self.assertIn("function resolveTaskTestCases(task)", html)
        self.assertIn("function renderTaskInfoForm(task)", html)
        self.assertIn("function renderTaskTargetSettingsForm(task)", html)
        self.assertIn("function renderTaskSummaryStrip(task)", html)
        self.assertIn("function renderPlanTaskSummary(plan)", html)
        self.assertIn("function renderCompactTaskStatus(task", html)
        self.assertNotIn("function getCurrentBuildContext", html)
        self.assertNotIn("function resolveBuildTestCases", html)
        self.assertNotIn("function renderBuildInfoForm", html)
        self.assertNotIn("function renderBuildTargetSettingsForm", html)
        self.assertNotIn("function renderBuildSummaryStrip", html)
        self.assertNotIn("function renderPlanBuildSummary", html)
        self.assertNotIn("function renderCompactBuildStatus", html)

    def test_frontend_uses_task_testcase_patch_route(self):
        html_path = os.path.join(str(WEB_UI_DIR), "static", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn("/task_testcases/${taskId}/${tc.id}", html)
        self.assertNotIn("/build_testcases/", html)

    def test_task_testcase_patch_route_exists(self):
        routes = {str(rule) for rule in app.url_map.iter_rules()}

        self.assertIn("/api/task_testcases/<task_id>/<tc_id>", routes)

    def test_frontend_prefers_task_detail_view_ids(self):
        html_path = os.path.join(str(WEB_UI_DIR), "static", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn('id="view-task-detail"', html)
        self.assertIn("init-view-task-detail", html)
        self.assertIn("'task-detail'", html)
        self.assertIn("function renderTaskDetail()", html)
        self.assertNotIn("function renderBuildDetail()", html)
        self.assertNotIn("return renderBuildDetail();", html)

    def test_frontend_prefers_task_setup_css_classes(self):
        html_path = os.path.join(str(WEB_UI_DIR), "static", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn("task-setup-grid", html)
        self.assertIn("task-setup-input", html)
        self.assertIn("task-summary-strip", html)
        self.assertNotIn("build-setup-", html)
        self.assertNotIn("build-summary-strip", html)

    def test_report_generator_prefers_task_named_entrypoint(self):
        report_path = os.path.join(str(WEB_UI_DIR), "report_generator.py")
        with open(report_path, "r", encoding="utf-8") as f:
            source = f.read()

        self.assertIn("def generate_task_pdf_report(task_id, output_path, db_path=None, log_dir=None):", source)
        self.assertNotIn("def generate_pdf_report(", source)
        self.assertNotIn("build_id, output_path", source)
        self.assertIn("Task :", source)
        self.assertIn("Task Name", source)
        self.assertIn("Firmware / Task Label", source)
        self.assertNotIn("Firmware / Build Label", source)
        self.assertIn("task_table = 'tasks'", source)
        self.assertIn("task_tc_table = 'task_testcases'", source)
        self.assertIn("task_fk_col = 'task_id'", source)
        self.assertNotIn("else 'builds'", source)
        self.assertNotIn("else 'build_testcases'", source)
        self.assertNotIn("else 'build_id'", source)
        self.assertIn("task_name = task['name'] or 'Unnamed_Task'", source)
        self.assertIn("'task_name': task_name", source)
        self.assertNotIn("_report_meta.get('build_name'", source)
        self.assertNotIn("'build_name':", source)

    def test_task_report_route_uses_task_named_report_generator(self):
        app_path = os.path.join(str(WEB_UI_DIR), "app.py")
        with open(app_path, "r", encoding="utf-8") as f:
            source = f.read()

        self.assertIn("from report_generator import generate_task_pdf_report", source)
        self.assertIn("generate_task_pdf_report(task_id, out_path, db_path=DB_PATH)", source)

    def test_app_no_longer_contains_legacy_build_schema_migration(self):
        app_path = os.path.join(str(WEB_UI_DIR), "app.py")
        with open(app_path, "r", encoding="utf-8") as f:
            source = f.read()

        self.assertNotIn('"builds"', source)
        self.assertNotIn('"build_testcases"', source)
        self.assertNotIn('"build_id"', source)
        self.assertNotIn("ALTER TABLE builds", source)
        self.assertNotIn("ALTER TABLE build_testcases", source)
        self.assertNotIn("RENAME COLUMN build_id", source)

    def test_new_result_payload_uses_task_keys_only(self):
        html_path = os.path.join(str(WEB_UI_DIR), "static", "index.html")
        app_path = os.path.join(str(WEB_UI_DIR), "app.py")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        with open(app_path, "r", encoding="utf-8") as f:
            source = f.read()

        save_start = html.index("async function saveTaskResults(entity)")
        save_end = html.index("async function loadTaskResults(entity)", save_start)
        save_block = html[save_start:save_end]

        annotate_start = html.index("async function changeTcStatus")
        annotate_end = html.index("async function toggleAll", annotate_start)
        annotate_block = html[annotate_start:annotate_end]

        result_block = (WEB_UI_DIR / "plan_state.py").read_text(encoding="utf-8")

        self.assertIn("/tasks/${entity.id}/summary", save_block)
        self.assertIn("execution_token:token", save_block)
        self.assertNotIn("testcases:", save_block)
        self.assertNotIn("build_id:", save_block)
        self.assertNotIn("build_name:", save_block)
        self.assertNotIn("build_id:", annotate_block)
        self.assertNotIn("build_id: taskId", html)
        self.assertNotIn("build_name: build.name", html)
        self.assertNotIn('"build_id":   task_id', result_block)
        self.assertNotIn('"build_name": task_name', result_block)

    def test_legacy_build_api_routes_are_removed(self):
        routes = {str(rule) for rule in app.url_map.iter_rules()}

        self.assertNotIn("/api/builds", routes)
        self.assertNotIn("/api/builds/<build_id>", routes)
        self.assertNotIn("/api/builds/<build_id>/testcases", routes)
        self.assertNotIn("/api/builds/<build_id>/report", routes)
        self.assertNotIn("/api/builds/<build_id>/testcases/import", routes)
        self.assertNotIn("/api/builds/<build_id>/testcases/reorder", routes)
        self.assertNotIn("/api/build_tc/annotate", routes)
        self.assertNotIn("/api/results/<build_id>", routes)

    def test_frontend_reads_task_results_route(self):
        html_path = os.path.join(str(WEB_UI_DIR), "static", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn("/tasks/${task.id}/summary", html)
        self.assertIn("/tasks/${entity.id}/results", html)
        self.assertNotIn("data.found", html)
        self.assertNotIn("/results/${task.id}", html)
        self.assertNotIn("/results/${build.id}", html)
        self.assertNotIn("/results/${taskId}", html)

    def test_backend_request_contract_requires_task_keys(self):
        client=app.test_client()
        for endpoint in ('/api/results/save','/api/task_tc/annotate'):
            response=client.post(endpoint,json={'build_id':'legacy','testcases':[]})
            self.assertIn(response.status_code,(400,404))
        source=(WEB_UI_DIR/'plan_state.py').read_text(encoding='utf-8')
        self.assertNotIn("data.get('build_id')",source)
        self.assertNotIn("data.get('build_name')",source)

    def test_save_projects_import_uses_tasks_without_builds_fallback(self):
        source=(WEB_UI_DIR/'plan_state.py').read_text(encoding='utf-8')
        self.assertIn("plan_data.get('tasks',[])",source)
        self.assertNotIn("plan_data.get('builds'",source)
        self.assertNotIn('BuildTestCase',source)

    def test_frontend_primary_workspace_flow_uses_task_names(self):
        html_path = os.path.join(str(WEB_UI_DIR), "static", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn('data-project-tab="tasks"', html)
        self.assertIn("renderProjectWorkspace('tasks')", html)
        self.assertIn("function openDashboardTask(projectId, planId, taskId)", html)
        self.assertIn("async function renameTask(planId, taskId)", html)
        self.assertIn("async function deleteTask(planId, taskId)", html)

        self.assertNotIn('data-project-tab="builds"', html)
        self.assertNotIn("renderProjectWorkspace('builds')", html)
        self.assertNotIn("function openDashboardBuild", html)
        self.assertNotIn("function selectBuild", html)
        self.assertNotIn("async function newBuild", html)
        self.assertNotIn("async function renameBuild", html)
        self.assertNotIn("async function deleteBuild", html)
        self.assertNotIn("window.openDashboardBuild", html)

    def test_frontend_stops_writing_plan_builds_alias(self):
        html_path = os.path.join(str(WEB_UI_DIR), "static", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertNotIn("if (Array.isArray(plan.builds)) return plan.builds;", html)
        self.assertIn("plan.tasks = tasks;", html)
        self.assertNotIn("plan.builds = tasks;", html)
        self.assertNotIn("plan.builds = remainingTasks;", html)
        self.assertNotIn("builds: []", html)

    def test_frontend_visible_dashboard_copy_uses_task_terms(self):
        html_path = os.path.join(str(WEB_UI_DIR), "static", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertNotIn("build cases", html)
        self.assertNotIn("Latest build test cases", html)
        self.assertNotIn("0 total build cases", html)
        self.assertIn("task cases executed", html)
        self.assertIn("Latest task test cases grouped by status", html)

    def test_frontend_dashboard_workspace_model_uses_task_terms(self):
        html_path = os.path.join(str(WEB_UI_DIR), "static", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        dashboard_start = html.index("function buildDashboardModel()")
        dashboard_end = html.index("function renderWorkspaceRows", dashboard_start)
        dashboard_block = html[dashboard_start:dashboard_end]

        self.assertIn("taskCount: 0", dashboard_block)
        self.assertIn("taskCaseCount: 0", dashboard_block)
        self.assertIn("model.taskCount", dashboard_block)
        self.assertIn("projectHealth.taskCount", dashboard_block)
        self.assertIn("return { plans, tasks, latest", dashboard_block)
        self.assertNotIn("buildCount", dashboard_block)
        self.assertNotIn("buildCaseCount", dashboard_block)
        self.assertNotIn("stats.builds", dashboard_block)
        self.assertNotIn("item.build", dashboard_block)
        self.assertNotIn("projectHealth.build", dashboard_block)

    def test_frontend_task_selection_uses_task_terms(self):
        html_path = os.path.join(str(WEB_UI_DIR), "static", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        select_start = html.index("async function selectTask(planId, taskId)")
        select_end = html.index("function getCurrentEntity()", select_start)
        select_block = html[select_start:select_end]

        self.assertIn("const task = getPlanTasks(plan).find", select_block)
        self.assertIn("loadTaskResults(task)", select_block)
        self.assertNotIn("const build =", select_block)
        self.assertNotIn("entering the build", select_block)
        self.assertNotIn("switching to Build", select_block)

        rename_start = html.index("async function renameTask(planId, taskId)")
        rename_end = html.index("async function deleteTask", rename_start)
        rename_block = html[rename_start:rename_end]
        self.assertIn("const task = getPlanTasks(plan).find", rename_block)
        self.assertNotIn("const build =", rename_block)
        self.assertNotIn("build.name", rename_block)

    def test_frontend_plan_summary_uses_task_terms(self):
        html_path = os.path.join(str(WEB_UI_DIR), "static", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        detail_start = html.index("function renderPlanDetail()")
        detail_end = html.index("async function openPlanDetail", detail_start)
        detail_block = html[detail_start:detail_end]
        strip_start = html.index("function renderPlanSummaryStrip(plan)")
        strip_end = html.index("function renderCompactTaskStatus", strip_start)
        strip_block = html[strip_start:strip_end]

        self.assertIn("const tasks = getPlanTasks(plan)", detail_block)
        self.assertIn("const latestTask = tasks.length", detail_block)
        self.assertNotIn("const builds", detail_block)
        self.assertNotIn("latestBuild", detail_block)
        self.assertIn("const tasks = getPlanTasks(plan)", strip_block)
        self.assertIn("const latestTask = tasks.length", strip_block)
        self.assertNotIn("const builds", strip_block)
        self.assertNotIn("latestBuild", strip_block)

    def test_frontend_task_import_and_config_use_task_terms(self):
        html_path = os.path.join(str(WEB_UI_DIR), "static", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        import_start = html.index("function openAddFromPlanModal()")
        import_end = html.index("//", html.index("async function importTC", import_start))
        import_block = html[import_start:import_end]
        config_start = html.index("function openEnvConfigModal()")
        config_end = html.index("function closeModal", config_start)
        config_block = html[config_start:config_end]

        self.assertIn("const task = getPlanTasks(plan).find", import_block)
        self.assertIn("const taskIds = new Set(task.testcases.map", import_block)
        self.assertIn("const members=new Map(task.testcases.map", import_block)
        self.assertIn("testcases:[...members.values()]", import_block)
        self.assertNotIn("const build =", import_block)
        self.assertNotIn("build.testcases", import_block)
        self.assertNotIn("Build", import_block)
        self.assertIn("const task = getPlanTasks(plan).find", config_block)
        self.assertIn("task.environment_config", config_block)
        self.assertNotIn("const build =", config_block)
        self.assertNotIn("build.environment_config", config_block)

    def test_frontend_custom_folder_sync_uses_task_terms(self):
        html_path = os.path.join(str(WEB_UI_DIR), "static", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        drag_start = html.index("function dropTc")
        drag_end = html.index("async function batchDeleteTC", drag_start)
        drag_block = html[drag_start:drag_end]

        self.assertIn("getPlanTasks(plan).forEach(task =>", drag_block)
        self.assertIn("const taskTc = task.testcases.find", drag_block)
        self.assertNotIn("forEach(build =>", drag_block)
        self.assertNotIn("buildTc", drag_block)
        self.assertNotIn("all Builds", drag_block)
        self.assertNotIn("Build view", drag_block)

    def test_frontend_reconnect_flow_uses_task_terms(self):
        html_path = os.path.join(str(WEB_UI_DIR), "static", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        reconnect_start = html.index("function reconnectLogStream(sessionId)")
        reconnect_end = html.index("function applyReadOnlyLockIfLocked", reconnect_start)
        reconnect_block = html[reconnect_start:reconnect_end]

        self.assertIn("const taskId=getCurrentTaskId()", reconnect_block)
        self.assertNotIn("/task_tc/annotate", reconnect_block)
        self.assertNotIn("saveTaskResults", reconnect_block)
        self.assertIn("loadTaskResults(getCurrentEntity())", reconnect_block)
        self.assertNotIn("const build =", reconnect_block)
        self.assertNotIn("if (build", reconnect_block)
        self.assertNotIn("build.testcases", reconnect_block)
        self.assertNotIn("build.name", reconnect_block)

    def test_task_testcase_model_uses_task_id_attribute(self):
        self.assertTrue(hasattr(TaskTestCase, "task_id"))
        self.assertFalse(hasattr(TaskTestCase, "build_id"))
        self.assertEqual(TaskTestCase.__table__.columns["task_id"].name, "task_id")

    def test_backend_queries_task_testcases_by_task_id(self):
        engine=create_engine('sqlite:///:memory:'); Base.metadata.create_all(engine)
        Session=sessionmaker(bind=engine)
        with Session() as session:
            session.add_all([Project(id='p',name='P'),ProjectPlan(id='plan',project_id='p',name='Plan')]);session.commit()
            session.add_all([Task(id='one',plan_id='plan',name='One'),Task(id='two',plan_id='plan',name='Two'),TestCase(system_id='tc',plan_id='plan',display_name='Case',script_path='case')]);session.commit()
        with patch.object(app_module,'DbSession',Session):
            response=app.test_client().post('/api/tasks/one/testcases/import',json={'testcases':[{'id':'tc'}]})
            self.assertEqual(response.status_code,200)
            self.assertEqual(len(app.test_client().get('/api/tasks/one/summary').get_json()['testcases']),1)
            self.assertEqual(app.test_client().get('/api/tasks/two/summary').get_json()['testcases'],[])
        engine.dispose()

    def test_task_relationships_use_task_names_without_legacy_aliases(self):
        self.assertTrue(hasattr(ProjectPlan, "tasks"))
        self.assertFalse(hasattr(ProjectPlan, "builds"))
        self.assertTrue(hasattr(PlanSubfolder, "task_testcases"))
        self.assertFalse(hasattr(PlanSubfolder, "build_testcases"))
        self.assertTrue(hasattr(Task, "task_testcases"))
        self.assertFalse(hasattr(Task, "build_testcases"))
        self.assertIn("task_obj", TaskTestCase.__mapper__.relationships.keys())
        self.assertFalse(hasattr(TaskTestCase, "build_obj"))

        models_path = os.path.join(str(WEB_UI_DIR), "models.py")
        with open(models_path, "r", encoding="utf-8") as f:
            source = f.read()

        self.assertNotIn("Build = Task", source)
        self.assertNotIn("BuildTestCase = TaskTestCase", source)

    def test_task_testcase_task_id_round_trip(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            project = Project(id="proj_1", name="Project 1")
            plan = ProjectPlan(id="plan_1", project_id="proj_1", name="Plan 1")
            task = Task(id="task_1", plan_id="plan_1", name="Task 1")
            testcase = TestCase(
                system_id="tc_1",
                family_id="fam_1",
                display_name="Case 1",
                plan_id="plan_1",
                script_path="case_1.py",
            )
            task_tc = TaskTestCase(task_id="task_1", testcase_id="tc_1")
            session.add_all([project, plan, task, testcase, task_tc])
            session.commit()

            loaded = session.query(TaskTestCase).filter_by(task_id="task_1").one()

            self.assertEqual(loaded.task_id, "task_1")
            self.assertEqual(loaded.task_obj.name, "Task 1")
        finally:
            session.close()

    def test_workspace_database_uses_task_tables(self):
        db_path = os.path.join(str(WEB_UI_DIR), "workspace", "testcase_meta.db")
        conn = sqlite3.connect(db_path)
        try:
            tables = {
                row[0]
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            task_tc_cols = {
                row[1]
                for row in conn.execute("PRAGMA table_info(task_testcases)")
            }

            self.assertIn("tasks", tables)
            self.assertIn("task_testcases", tables)
            self.assertNotIn("builds", tables)
            self.assertNotIn("build_testcases", tables)
            self.assertIn("task_id", task_tc_cols)
            self.assertNotIn("build_id", task_tc_cols)
        finally:
            conn.close()

    def test_task_execution_has_current_state_without_attempt_storage(self):
        self.assertNotIn('task_execution_attempts', Base.metadata.tables)
        self.assertIn('execution_active', Task.__table__.columns)
        self.assertIn('result_json', TaskTestCase.__table__.columns)
        routes={rule.rule for rule in app.url_map.iter_rules()}
        self.assertNotIn('/api/task_attempts/start',routes)
        self.assertIn('/api/tasks/<task_id>/execution/start',routes)
        self.assertIn('/api/tasks/<task_id>/summary',routes)

    def test_toolbar_project_selection_rerenders_visible_combobox(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
        choose_start = html.index("function chooseProjectFromToolbar(pid, event)")
        choose_end = html.index("document.addEventListener('click'", choose_start)
        choose_project = html[choose_start:choose_end]
        change_start = html.index("async function changeProject(pid)")
        change_end = html.index("function switchSidebarTab(tab)", change_start)
        change_project = html[change_start:change_end]

        self.assertIn("currentProjId = null", change_project)
        self.assertIn("renderProjectSelect()", change_project)
        self.assertIn("currentProjId = proj ? proj.id : null", change_project)
        self.assertIn("renderProjectSelect()", choose_project)
        self.assertEqual(html.count("btn.textContent ="), 1)

    def test_toolbar_project_clear_precedes_running_project_guard(self):
        html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
        change_start = html.index("async function changeProject(pid)")
        change_end = html.index("function switchSidebarTab(tab)", change_start)
        change_project = html[change_start:change_end]
        clear_guard = change_project.index("if (!pid)")
        running_guard = change_project.index("if (isRunning)")
        clear_branch = change_project[clear_guard:running_guard]

        self.assertLess(clear_guard, running_guard)
        for statement in (
            "currentProjId = null;",
            "currentPlanId = null;",
            "setCurrentTaskId(null);",
            "renderProjectSelect();",
            "showView('dashboard', { forceCurrentTab: true });",
            "return;",
        ):
            self.assertIn(statement, clear_branch)
        self.assertNotIn("window.open", clear_branch)

        show_start = html.index("function showView(viewId, options = {})")
        show_end = html.index("function stateFromLocation()", show_start)
        show_view = html[show_start:show_end]
        self.assertIn("!options.forceCurrentTab", show_view)

    def test_frontend_uses_current_execution_and_live_results(self):
        html_path = os.path.join(str(WEB_UI_DIR), "static", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn('/execution/start', html)
        self.assertIn('execution_token:', html)
        self.assertIn('sessionStorage.setItem(`task-execution:', html)
        self.assertIn('Object.assign(entity,data)', html)
        self.assertNotIn('Run History', html)
        self.assertNotIn('currentAttemptId', html)
        self.assertNotIn('task_attempts/start', html)


if __name__ == "__main__":
    unittest.main()
