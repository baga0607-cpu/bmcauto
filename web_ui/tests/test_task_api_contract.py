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
                lock_session.add(Task(environment_config='{"host":"https://example.invalid","username":"test","password":"test"}', id="active",plan_id="plan_guard",name="Active",execution_active=True)); lock_session.commit()
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

















    def test_task_testcase_patch_route_exists(self):
        routes = {str(rule) for rule in app.url_map.iter_rules()}

        self.assertIn("/api/task_testcases/<task_id>/<tc_id>", routes)



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










    def test_task_testcase_model_uses_task_id_attribute(self):
        self.assertTrue(hasattr(TaskTestCase, "task_id"))
        self.assertFalse(hasattr(TaskTestCase, "build_id"))
        self.assertEqual(TaskTestCase.__table__.columns["task_id"].name, "task_id")

    def test_backend_queries_task_testcases_by_task_id(self):
        engine=create_engine('sqlite:///:memory:'); Base.metadata.create_all(engine)
        Session=sessionmaker(bind=engine)
        with Session() as session:
            session.add_all([Project(id='p',name='P'),ProjectPlan(id='plan',project_id='p',name='Plan')]);session.commit()
            session.add_all([Task(environment_config='{"host":"https://example.invalid","username":"test","password":"test"}', id='one',plan_id='plan',name='One'),Task(environment_config='{"host":"https://example.invalid","username":"test","password":"test"}', id='two',plan_id='plan',name='Two'),TestCase(system_id='tc',plan_id='plan',display_name='Case',script_path='case')]);session.commit()
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
            task = Task(environment_config='{"host":"https://example.invalid","username":"test","password":"test"}', id="task_1", plan_id="plan_1", name="Task 1")
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





if __name__ == "__main__":
    unittest.main()
