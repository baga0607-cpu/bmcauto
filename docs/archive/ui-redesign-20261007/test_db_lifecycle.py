import requests, time, json, sqlite3, shutil, os
import sys
import socket
import subprocess
import unittest
import uuid
from contextlib import closing
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WEB_UI_DIR = REPO_ROOT / "web_ui"
WORKSPACE_DIR = Path(
    os.environ.get("BMC_LIFECYCLE_WORKSPACE_DIR", WEB_UI_DIR / "workspace")
).resolve()
MAIN_PROGRAM_DIR = Path(
    os.environ.get("BMC_LIFECYCLE_MAIN_PROGRAM_DIR", REPO_ROOT / "main_program")
).resolve()
SANDBOX_PARENT = WEB_UI_DIR / "tests" / "_sandboxes"

DEFAULT_API = "http://127.0.0.1:5000/api"
API = os.environ.get("BMC_LIFECYCLE_API", DEFAULT_API)
generated_tc_ids = []

def get_plan_uuid(proj_name, plan_name):
    r = requests.get(f"{API}/projects")
    try:
        return [pl["id"] for p in r.json().get("projects", []) if p["name"]==proj_name for pl in p.get("plans", []) if pl["name"]==plan_name][0]
    except Exception as e:
        raise Exception(f"Could not find UUID for {proj_name}/{plan_name}. API Response: {r.text}")



def run_tc_and_assert_pass(tc_name, steps):
    session_id = f"test_run_{int(time.time())}"
    r_run = requests.post(f"{API}/run", json={
        "session_id": session_id,
        "tc_name": tc_name,
        "steps": steps
    })
    assert r_run.status_code == 200, f"Failed to start execution: {r_run.text}"
    assert r_run.json().get("status") == "started", f"Run status is not started: {r_run.json()}"
    
    # stream SSE logs
    r_stream = requests.get(f"{API}/stream/{session_id}", stream=True)
    final_result = "pass"
    for line in r_stream.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith("data: "):
                # Safe JSON serialization avoids Windows CMD CP950 UnicodeEncodeError
                data = json.loads(line_str[6:])
                print(f"    SSE Message: {json.dumps(data)}")
                msg_type = data.get("type")
                if msg_type == "error":
                    final_result = "fail"
                elif msg_type == "step_done":
                    if data.get("result") == "FAIL":
                        final_result = "fail"
                elif msg_type == "end":
                    break
    assert final_result == "pass", f"FAIL: Test case '{tc_name}' execution failed!"
    print(f"  -> PASS: Execution of '{tc_name}' completed successfully.")



def run_v9_hardening_tests():
    global FAIL, PASS
    FAIL = 0
    PASS = 0
    import sys
    """
    test_v9_hardening.py — V9 DB Hardening 自動化測試
    ==================================================
    測試涵蓋：
      T01. GET /api/projects — 讀取現有資料，驗證結構正確
      T02. POST /api/create_project — 建立新 Project
      T03. POST /api/create_plan — 建立 Plan（取得 UUID plan_id）
      T04. 跨 Project 同名 Plan — 兩個 Project 都建立 Release_1.0，不應衝突
      T05. POST /api/rename_plan — 改名 Plan（只更新 name，UUID 不變）
      T06. POST /api/rename_project — 改名 Project（不再 delete+insert）
      T07. POST /api/delete_plan — 刪除 Plan，Cascade 清除 TC 和 Task
      T08. POST /api/delete_project — 刪除整個 Project，DB 自動 Cascade 清除所有底層資料
      T09. 舊版資料庫測試 fixture 存在
      T10. 資料型態驗證 — selected=bool, position=int
    """
    
    BASE = API
    PASS = 0
    FAIL = 0
    
    
    def ok(msg):
        global PASS
        PASS += 1
        print(f"  [PASS] {msg}")
    
    
    def fail(msg):
        global FAIL
        FAIL += 1
        print(f"  [FAIL] {msg}")
    
    
    def section(title):
        print(f"\n{'='*55}")
        print(f"  {title}")
        print('='*55)
    
    
    def get(path):
        return requests.get(f"{BASE}{path}", timeout=10)
    
    def post(path, body):
        return requests.post(f"{BASE}{path}", json=body, timeout=10)
    
    
    # ─────────────────────────────────────────────────────────────
    # T01: GET /api/projects — 讀取現有資料
    # ─────────────────────────────────────────────────────────────
    section("T01: GET /api/projects 資料結構驗證")
    r = get("/projects")
    if r.status_code == 200:
        ok(f"HTTP 200 OK")
        data = r.json()
        projects = data.get("projects", [])
        ok(f"回傳 {len(projects)} 個 Project")
        for proj in projects:
            ok(f"  Project: {proj['name']} (id={proj['id']})")
            for plan in proj.get("plans", []):
                ok(f"    Plan: {plan['name']} (id={plan['id'][:8]}...)")
                # 驗證 plan.id 不是純名稱字串（V9 應為 UUID 格式）
                plan_id = plan['id']
                is_uuid = len(plan_id) == 36 and plan_id.count('-') == 4
                if is_uuid:
                    ok(f"    plan.id 是 UUID 格式 [V9 正確]")
                else:
                    ok(f"    plan.id={plan_id} (Legacy string preserved)")
    else:
        fail(f"HTTP {r.status_code}: {r.text}")
    
    
    # ─────────────────────────────────────────────────────────────
    # T02: 建立測試 Project
    # ─────────────────────────────────────────────────────────────
    section("T02: POST /api/create_project")
    r = post("/create_project", {"project": "TestProject_V9_Alpha"})
    if r.status_code == 200 and r.json().get("status") == "ok":
        ok("建立 TestProject_V9_Alpha 成功")
    else:
        fail(f"建立失敗: {r.text}")
    
    r2 = post("/create_project", {"project": "TestProject_V9_Beta"})
    if r2.status_code == 200 and r2.json().get("status") == "ok":
        ok("建立 TestProject_V9_Beta 成功")
    else:
        fail(f"建立失敗: {r2.text}")
    
    
    # ─────────────────────────────────────────────────────────────
    # T03: 建立 Plan，取得 UUID plan_id
    # ─────────────────────────────────────────────────────────────
    section("T03: POST /api/create_plan — 取得 UUID plan_id")
    r = post("/create_plan", {"project": "TestProject_V9_Alpha", "plan_name": "Sprint_01"})
    if r.status_code == 200:
        d = r.json()
        plan_id_alpha = d.get("plan_id", "")
        is_uuid = len(plan_id_alpha) == 36 and plan_id_alpha.count('-') == 4
        if is_uuid:
            ok(f"取得 UUID plan_id: {plan_id_alpha}")
        else:
            fail(f"plan_id 不是 UUID: {plan_id_alpha}")
    else:
        fail(f"建立 Plan 失敗: {r.text}")
        plan_id_alpha = ""
    
    
    # ─────────────────────────────────────────────────────────────
    # T04: 跨 Project 同名 Plan — V9 核心修正驗證
    # ─────────────────────────────────────────────────────────────
    section("T04: 跨 Project 同名 Plan — 不應 PK 衝突")
    r_a = post("/create_plan", {"project": "TestProject_V9_Alpha", "plan_name": "Release_1.0"})
    r_b = post("/create_plan", {"project": "TestProject_V9_Beta",  "plan_name": "Release_1.0"})
    
    if r_a.status_code == 200 and r_b.status_code == 200:
        id_a = r_a.json().get("plan_id", "")
        id_b = r_b.json().get("plan_id", "")
        if id_a != id_b:
            ok(f"Alpha/Release_1.0 plan_id: {id_a}")
            ok(f"Beta/Release_1.0  plan_id: {id_b}")
            ok("兩個同名 Plan 擁有不同 UUID，PK 衝突問題已解決！[V9 核心修正]")
        else:
            fail(f"兩個同名 Plan 的 UUID 相同：{id_a}，可能有問題")
    else:
        fail(f"建立跨 Project 同名 Plan 失敗: Alpha={r_a.status_code} Beta={r_b.status_code}")
        id_a = id_b = ""
    
    
    # ─────────────────────────────────────────────────────────────
    # T05: 改名 Plan — 只更新 name，UUID 不變
    # ─────────────────────────────────────────────────────────────
    section("T05: POST /api/rename_plan — UUID 保持不變")
    if plan_id_alpha:
        r = post("/rename_plan", {
            "project": "TestProject_V9_Alpha",
            "old_name": "Sprint_01",   # 傳 UUID
            "new_name": "Sprint_01_Renamed"
        })
        if r.status_code == 200 and r.json().get("status") == "ok":
            ok("rename_plan 呼叫成功")
            # 驗證改名後 plan_id 仍是同一個 UUID
            r2 = get("/projects")
            projects2 = r2.json().get("projects", [])
            alpha = next((p for p in projects2 if p["name"] == "TestProject_V9_Alpha"), None)
            if alpha:
                renamed = next((pl for pl in alpha["plans"] if pl["id"] == plan_id_alpha), None)
                if renamed and renamed["name"] == "Sprint_01_Renamed":
                    ok(f"UUID 不變（{plan_id_alpha[:8]}...），name 已更新為 Sprint_01_Renamed [V9 架構改善]")
                elif renamed:
                    fail(f"name 未正確更新，目前為: {renamed['name']}")
                else:
                    fail(f"改名後找不到原 UUID 的 Plan（plan_id={plan_id_alpha[:8]}...）")
        else:
            fail(f"rename_plan 失敗: {r.text}")
    else:
        fail("跳過（T03 未取得 plan_id）")
    
    
    # ─────────────────────────────────────────────────────────────
    # T06: 改名 Project — 不再 delete+insert
    # ─────────────────────────────────────────────────────────────
    section("T06: POST /api/rename_project")
    r = post("/rename_project", {
        "old_name": "TestProject_V9_Beta",
        "new_name": "TestProject_V9_Beta_Renamed"
    })
    if r.status_code == 200 and r.json().get("status") == "ok":
        ok("rename_project 成功")
        # 驗證改名後 Project 存在
        r2 = get("/projects")
        projs = r2.json().get("projects", [])
        names = [p["name"] for p in projs]
        if "TestProject_V9_Beta_Renamed" in names and "TestProject_V9_Beta" not in names:
            ok("舊名稱消失，新名稱正確存在")
        else:
            fail(f"改名後 Project 列表異常: {names}")
    else:
        fail(f"rename_project 失敗: {r.text}")
    
    
    # ─────────────────────────────────────────────────────────────
    # T07: 刪除 Plan — Cascade 清除
    # ─────────────────────────────────────────────────────────────
    section("T07: POST /api/delete_plan — Cascade 清除")
    # 先取得 Release_1.0 在 Alpha 的 plan_id
    r = get("/projects")
    projs = r.json().get("projects", [])
    alpha = next((p for p in projs if p["name"] == "TestProject_V9_Alpha"), None)
    release_plan = None
    if alpha:
        release_plan = next((pl for pl in alpha["plans"] if pl["name"] == "Release_1.0"), None)
    
    if release_plan:
        r_del = post("/delete_plan", {
            "project": "TestProject_V9_Alpha",
            "plan_id": release_plan["id"]
        })
        if r_del.status_code == 200 and r_del.json().get("status") == "ok":
            ok(f"delete_plan 成功 (plan_id={release_plan['id'][:8]}...)")
            # 驗證 Plan 已消失
            r2 = get("/projects")
            projs2 = r2.json().get("projects", [])
            alpha2 = next((p for p in projs2 if p["name"] == "TestProject_V9_Alpha"), None)
            if alpha2:
                remaining = [pl["name"] for pl in alpha2["plans"]]
                if "Release_1.0" not in remaining:
                    ok("Plan 已從 DB 消失 [Cascade 正常]")
                else:
                    fail(f"Plan 未被刪除，仍在: {remaining}")
        else:
            fail(f"delete_plan 失敗: {r_del.text}")
    else:
        fail("找不到 TestProject_V9_Alpha/Release_1.0 可供刪除測試")
    
    
    # ─────────────────────────────────────────────────────────────
    # T08: 刪除 Project — DB Cascade 自動清除所有底層資料
    # ─────────────────────────────────────────────────────────────
    section("T08: POST /api/delete_project — DB Cascade 清除 [V9 核心修正]")
    r = post("/delete_project", {"project": "TestProject_V9_Alpha"})
    if r.status_code == 200 and r.json().get("status") == "ok":
        ok("delete_project 呼叫成功")
        # 驗證 Project 已消失
        r2 = get("/projects")
        projs2 = r2.json().get("projects", [])
        names2 = [p["name"] for p in projs2]
        if "TestProject_V9_Alpha" not in names2:
            ok("Project 已從 DB 消失")
            ok("底層的 Plan/Task/TC 由 DB ON DELETE CASCADE 自動清除 [不需手動逐一刪除]")
        else:
            fail(f"Project 刪除後仍存在: {names2}")
    else:
        fail(f"delete_project 失敗: {r.text}")
    
    # 同樣清理 Beta_Renamed
    post("/delete_project", {"project": "TestProject_V9_Beta_Renamed"})
    
    
    # ─────────────────────────────────────────────────────────────
    # T09: 備份檔確認
    # ─────────────────────────────────────────────────────────────
    section("T09: 備份檔確認")
    backup_path = str(WEB_UI_DIR / "tests" / "fixtures" / "testcase_meta_legacy.db")
    if os.path.exists(backup_path):
        size = os.path.getsize(backup_path)
        ok(f"舊版資料庫 fixture 存在: testcase_meta_legacy.db ({size} bytes)")
    else:
        fail("備份檔不存在！")
    
    
    # ─────────────────────────────────────────────────────────────
    # T10: 資料型態驗證（直接查資料庫）
    # ─────────────────────────────────────────────────────────────
    section("T10: 資料型態驗證 (selected=bool, position=int)")
    try:
        sys.path.insert(0, str(WEB_UI_DIR))
        from models import TestCase, TaskTestCase
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
    
        db_path = str(WORKSPACE_DIR / "testcase_meta.db")
        eng = create_engine(f"sqlite:///{db_path}")
        Sess = sessionmaker(bind=eng)
        s = Sess()
    
        tc = s.query(TestCase).first()
        if tc:
            if isinstance(tc.selected, bool):
                ok(f"testcases.selected 型態正確: bool = {tc.selected}")
            else:
                fail(f"testcases.selected 型態錯誤: {type(tc.selected).__name__} = {tc.selected}")
    
        btc = s.query(TaskTestCase).first()
        if btc:
            if isinstance(btc.position, int):
                ok(f"task_testcases.position 型態正確: int = {btc.position}")
            else:
                fail(f"task_testcases.position 型態錯誤: {type(btc.position).__name__} = {btc.position}")
            if isinstance(btc.selected, bool):
                ok(f"task_testcases.selected 型態正確: bool = {btc.selected}")
            else:
                fail(f"task_testcases.selected 型態錯誤: {type(btc.selected).__name__} = {btc.selected}")
        else:
            ok("task_testcases 無資料（正常，可略過）")
    
        s.close()
    except Exception as e:
        fail(f"型態驗證失敗: {e}")
    
    
    # ─────────────────────────────────────────────────────────────
    # 最終結果
    # ─────────────────────────────────────────────────────────────
    total = PASS + FAIL
    print(f"\n{'='*55}")
    print(f"  測試結果：{PASS}/{total} 通過，{FAIL} 失敗")
    print('='*55)
    if FAIL == 0:
        print("  [ALL PASS] V9 DB Hardening 驗證完成！")
    else:
        print(f"  [WARNING] 有 {FAIL} 項測試未通過，請確認。")
    print('='*55)
    
    assert FAIL == 0, f"V9 Hardening failed with {FAIL} errors!"
    print("\n  -> PASS: All V9 Hardening DB validations passed.\n")


def _assert_isolated_worker_configuration():
    sandbox_parent = SANDBOX_PARENT.resolve()
    if API == DEFAULT_API:
        raise RuntimeError("lifecycle worker refuses the default development API")
    for name, path in (
        ("workspace", WORKSPACE_DIR),
        ("main_program", MAIN_PROGRAM_DIR),
    ):
        try:
            path.resolve().relative_to(sandbox_parent)
        except ValueError as error:
            raise RuntimeError(
                f"lifecycle worker refuses non-sandbox {name}: {path}"
            ) from error


def main():
    _assert_isolated_worker_configuration()
    try:
        print('='*50)
        print('  Part 0: V9 Database Hardening Validation')
        print('='*50)
        run_v9_hardening_tests()
    
        print("="*50)
        print("  Part 1: Dedicated Testing Project & Plan Creation  ")
        print("="*50)
    
        # 1. Create a new project 'Project_test'
        print("\n[1] Create empty project 'Project_test'")
        r = requests.post(f"{API}/create_project", json={"project": "Project_test"})
        print(f"  Status: {r.json()}")
    
        # 2. Fetch and check it appears
        r2 = requests.get(f"{API}/projects")
        data = r2.json()
        proj_names = [p["name"] for p in data["projects"]]
        print(f"  Projects now: {proj_names}")
        assert "Project_test" in proj_names, "FAIL: Project_test not found!"
        print("  -> PASS: Project_test persisted correctly")
    
        # 3. Save a plan under it
        print("\n[2] Save Plan_test under Project_test")
        for proj in data["projects"]:
            if proj["name"] == "Project_test":
                proj["plans"] = [{"id": "Plan_test", "name": "Plan_test", "testcases": [], "tasks": [], "custom_subfolders": []}]
        r3 = requests.post(f"{API}/projects", json=data)
        print(f"  Save Plan: {r3.json()}")
    
        # 4. Re-fetch and check plan exists
        r4 = requests.get(f"{API}/projects")
        data4 = r4.json()
        for proj in data4["projects"]:
            if proj["name"] == "Project_test":
                plan_ids = [p["name"] for p in proj["plans"]]
                print(f"  Plans now: {plan_ids}")
                assert "Plan_test" in plan_ids, "FAIL: Plan_test not found!"
                print("  -> PASS: Plan_test persisted correctly")
    
    
        print("\n\n" + "="*50)
        print("  Part 2: Task & TestCase Sync Test  ")
        print("="*50)
    
        # Creating Task_test
        print("\n[1] Creating test task 'Task_test' via saveDB")
        r = requests.get(f"{API}/projects")
        data = r.json()
        for proj in data["projects"]:
            if proj["name"] == "Project_test":
                for plan in proj["plans"]:
                    if plan["name"] == "Plan_test":
                        plan["tasks"] = [{
                            "id": "Task_test",
                            "name": "Task_test",
                            "testcases": [],
                            "custom_subfolders": []
                        }]
        r2 = requests.post(f"{API}/projects", json=data)
        print(f"  Save result: {r2.json()}")
    
        # Let's import a base test case into Project_test / Plan_test first
        print("\n[2] Importing base TC 'Test_Sync_Base_TC' into Project_test/Plan_test")
        base_tc_payload = {
            "project": "Project_test",
            "plan_id": get_plan_uuid("Project_test", "Plan_test"),
            "category": "Custom",
            "tc_name": "Test_Sync_Base_TC",
            "family_id": "",
            "steps": [{"module_path": "testcase_database.steps.Basic_Function_Test.HEAD_Method_Support.head_request", "preset": ""}]
        }
        r_base = requests.post(f"{API}/import_tc", json=base_tc_payload)
        base_tc_id = r_base.json().get("id")
        generated_tc_ids.append(base_tc_id)
        print(f"  -> Imported Base TC ID: {base_tc_id}")
    
        # Now, add it to Task_test
        print("\n[3] Syncing Base TC to Task_test")
        r = requests.get(f"{API}/projects")
        data = r.json()
        for proj in data["projects"]:
            if proj["name"] == "Project_test":
                for plan in proj["plans"]:
                    if plan["name"] == "Plan_test":
                        for b in plan["tasks"]:
                            if b["id"] == "Task_test":
                                b["testcases"] = [{"id": base_tc_id, "selected": True}]
        r_sync = requests.post(f"{API}/projects", json=data)
        print(f"  Sync result: {r_sync.json()}")
    
        # Verify task sync
        print("\n[4] Verifying Task_test TestCase selection status")
        r_ver = requests.get(f"{API}/projects")
        build_tc_list = [tc for p in r_ver.json()["projects"] if p["name"]=="Project_test" for pl in p["plans"] if pl["name"] == "Plan_test" for b in pl["tasks"] if b["id"]=="Task_test" for tc in b["testcases"]]
        print(f"  Task TCs now: {build_tc_list}")
        assert len(build_tc_list) == 1 and build_tc_list[0]["id"] == base_tc_id and build_tc_list[0]["selected"] is True, "FAIL: TestCase sync failed!"
        print("  -> PASS: Task TestCase synced successfully")
    
    
        print("\n\n" + "="*50)
        print("  Part 3: Custom Subfolder & TC Movement Test  ")
        print("="*50)
    
        print("\n[1] Import Test_Custom_Movement_TC into Custom category for Project_test/Plan_test")
        import_payload = {
            "project": "Project_test",
            "plan_id": get_plan_uuid("Project_test", "Plan_test"),
            "category": "Custom",
            "tc_name": "Test_Custom_Movement_TC",
            "family_id": "",
            "steps": [{"module_path": "test", "preset": ""}]
        }
        r_imp = requests.post(f"{API}/import_tc", json=import_payload)
        new_tc_id = r_imp.json().get("id")
        generated_tc_ids.append(new_tc_id)
        print(f"  -> Imported TC ID: {new_tc_id}")
    
        print("\n[2] Create subfolder 'test01' under Plan_test")
        r = requests.get(f"{API}/projects")
        data = r.json()
        for p in data["projects"]:
            if p["name"] == "Project_test":
                for pl in p["plans"]:
                    if pl["name"] == "Plan_test":
                        if "test01" not in pl["custom_subfolders"]:
                            pl["custom_subfolders"].append("test01")
        requests.post(f"{API}/projects", json=data)
    
        print("\n[3] Link TC into Task_test")
        r = requests.get(f"{API}/projects")
        data = r.json()
        for p in data["projects"]:
            if p["name"] == "Project_test":
                for pl in p["plans"]:
                    if pl["name"] == "Plan_test":
                        for b in pl["tasks"]:
                            if b["id"] == "Task_test":
                                b["testcases"].append({
                                    "id": new_tc_id,
                                    "selected": True,
                                    "custom_subfolder": None
                                })
        requests.post(f"{API}/projects", json=data)
        
        # Verify task sync
        r = requests.get(f"{API}/projects")
        b_tc = [tc for p in r.json()["projects"] if p["name"]=="Project_test" for pl in p["plans"] if pl["name"] == "Plan_test" for b in pl["tasks"] if b["id"]=="Task_test" for tc in b["testcases"] if tc["id"]==new_tc_id][0]
        print(f"  -> Task TC custom_subfolder: {b_tc.get('custom_subfolder')}")
        assert b_tc.get('custom_subfolder') is None
    
        requests.patch(f"{API}/testcases/{new_tc_id}", json={"folder_path":"Custom/test01"}).raise_for_status()
        # Verify
        r = requests.get(f"{API}/projects")
        p_tc = [tc for p in r.json()["projects"] if p["name"]=="Project_test" for pl in p["plans"] if pl["name"] == "Plan_test" for tc in pl["testcases"] if tc["id"]==new_tc_id][0]
        b_tc = [tc for p in r.json()["projects"] if p["name"]=="Project_test" for pl in p["plans"] if pl["name"] == "Plan_test" for b in pl["tasks"] if b["id"]=="Task_test" for tc in b["testcases"] if tc["id"]==new_tc_id][0]
        print(f"  -> Plan TC subfolder: {p_tc.get('custom_subfolder')}")
        print(f"  -> Task TC subfolder: {b_tc.get('custom_subfolder')}")
        assert p_tc.get('custom_subfolder') == 'test01' and b_tc.get('custom_subfolder') == 'test01'
    
        folders = requests.get(f"{API}/plans/{get_plan_uuid('Project_test', 'Plan_test')}/folders").json()
        folder = next(f for f in folders if f["folder_path"] == "Custom/test01")
        requests.patch(f"{API}/folders/{folder['id']}", json={"name":"test02"}).raise_for_status()
        # Verify
        r = requests.get(f"{API}/projects")
        p_tc = [tc for p in r.json()["projects"] if p["name"]=="Project_test" for pl in p["plans"] if pl["name"] == "Plan_test" for tc in pl["testcases"] if tc["id"]==new_tc_id][0]
        b_tc = [tc for p in r.json()["projects"] if p["name"]=="Project_test" for pl in p["plans"] if pl["name"] == "Plan_test" for b in pl["tasks"] if b["id"]=="Task_test" for tc in b["testcases"] if tc["id"]==new_tc_id][0]
        print(f"  -> Plan TC subfolder: {p_tc.get('custom_subfolder')}")
        print(f"  -> Task TC subfolder: {b_tc.get('custom_subfolder')}")
        assert p_tc.get('custom_subfolder') == 'test02' and b_tc.get('custom_subfolder') == 'test02'
    
        requests.patch(f"{API}/testcases/{new_tc_id}", json={"folder_path":"Custom"}).raise_for_status()
        # Verify
        r = requests.get(f"{API}/projects")
        p_tc = [tc for p in r.json()["projects"] if p["name"]=="Project_test" for pl in p["plans"] if pl["name"] == "Plan_test" for tc in pl["testcases"] if tc["id"]==new_tc_id][0]
        b_tc = [tc for p in r.json()["projects"] if p["name"]=="Project_test" for pl in p["plans"] if pl["name"] == "Plan_test" for b in pl["tasks"] if b["id"]=="Task_test" for tc in b["testcases"] if tc["id"]==new_tc_id][0]
        print(f"  -> Plan TC subfolder: {p_tc.get('custom_subfolder')}")
        print(f"  -> Task TC subfolder: {b_tc.get('custom_subfolder')}")
        assert p_tc.get('custom_subfolder') is None and b_tc.get('custom_subfolder') is None
    
    
        print("\n\n" + "="*50)
        print("  Part 4: Golden Plan Warehouse Integration Test  ")
        print("="*50)
    
        print("\n[1] Dropdown direct push to Golden Plan via /api/push_to_golden")
        r = requests.get(f"{API}/projects")
        data = r.json()
        for p in data["projects"]:
            if p["name"] == "Project_test":
                for pl in p["plans"]:
                    if pl["name"] == "Plan_test":
                        for tc in pl["testcases"]:
                            if tc["id"] == new_tc_id:
                                tc["custom_subfolder"] = "folder_abc"
                        if "folder_abc" not in pl["custom_subfolders"]:
                            pl["custom_subfolders"].append("folder_abc")
        requests.post(f"{API}/projects", json=data)
        
        requests.patch(f"{API}/testcases/{new_tc_id}", json={"folder_path":"Custom/folder_abc"}).raise_for_status()
        # Trigger direct push
        r_push = requests.post(f"{API}/push_to_golden", json={"system_id": new_tc_id})
        push_res = r_push.json()
        print(f"  Push response: {push_res}")
        assert push_res.get("status") == "ok" or "Already in Golden" in push_res.get("message", "")
        if push_res.get("golden_id"):
            generated_tc_ids.append(push_res["golden_id"])
        
        # Reload and verify Golden Plan got it
        r = requests.get(f"{API}/projects")
        data = r.json()
        golden_proj = next(p for p in data["projects"] if p["name"] == "Golden_Project")
        golden_plan = next(pl for pl in golden_proj["plans"] if pl["name"] == "plan_golden")
        
        # Find Golden TC matching our family
        golden_tc = next((tc for tc in golden_plan["testcases"] if tc["family_id"] == p_tc["family_id"]), None)
        print(f"  -> Golden TC found: {golden_tc}")
        assert golden_tc is not None, "FAIL: TC was not pushed to Golden Plan!"
        assert golden_tc.get("custom_subfolder") == "folder_abc", f"FAIL: Subfolder was not carried to Golden Plan!"
        assert "folder_abc" in golden_plan["custom_subfolders"], "FAIL: Subfolder was not registered in Golden Plan custom_subfolders!"
        print("  -> PASS: Dropdown direct push and subfolder carrying verified successfully")
    
    
        print("\n\n" + "="*50)
        print("  Part 5: Plan-level TC Editing, Renaming & Synced Saving Test  ")
        print("="*50)
    
        # 1. Rename & Overwrite (直接儲存)
        # We rename Test_Custom_Movement_TC (new_tc_id) to Test_Overwritten_TC and change its steps
        print("\n[1] Test Overwrite (直接儲存) - Rename & Update Steps")
        overwrite_steps = [
            {"module_path": "testcase_database.steps.Basic_Function_Test.HEAD_Method_Support.head_request", "preset": ""},
            {"module_path": "testcase_database.steps.Basic_Function_Test.HEAD_Method_Support.verify_head_response", "preset": ""}
        ]
        overwrite_payload = {
            "project": "Project_test",
            "plan_id": get_plan_uuid("Project_test", "Plan_test"),
            "category": "Custom",
            "tc_name": "Test_Overwritten_TC",
            "family_id": p_tc["family_id"],
            "steps": overwrite_steps,
            "overwrite": True,
            "original_id": new_tc_id
        }
        r_over = requests.post(f"{API}/import_tc", json=overwrite_payload)
        print(f"  Overwrite response: {r_over.json()}")
        assert r_over.json().get("status") == "ok"
        assert r_over.json().get("id") == new_tc_id, "FAIL: Overwrite should keep the same system_id!"
        
        # Verify name and steps updated on Plan level
        r = requests.get(f"{API}/projects")
        tc_verify = next(t for p in r.json()["projects"] if p["name"]=="Project_test" for pl in p["plans"] if pl["name"] == "Plan_test" for t in pl["testcases"] if t["id"]==new_tc_id)
        print(f"  Updated TC Name: {tc_verify.get('tc_name')}")
        print(f"  Updated TC Steps: {tc_verify.get('steps')}")
        assert tc_verify.get("tc_name") == "Test_Overwritten_TC", "FAIL: Name was not updated!"
        assert len(tc_verify.get("steps", [])) == 2, "FAIL: Steps were not updated!"
        print("  -> PASS: Rename & Overwrite successfully saved and verified")
    
        # 2. Save As New Independent TC (另存新檔)
        # Simulates saving Test_Overwritten_TC as a new independent TC in 'folder_save_as' and push_to_golden=True
        print("\n[2] Test Save As (另存新檔) - Create New Family & Sync to Golden Plan")
        save_as_payload = {
            "project": "Project_test",
            "plan_id": get_plan_uuid("Project_test", "Plan_test"),
            "category": "Custom",
            "tc_name": "Test_SaveAs_Independent",
            "family_id": "", # empty means brand new bloodline
            "push_to_golden": True,
            "custom_subfolder": "folder_save_as",
            "steps": overwrite_steps
        }
        r_save = requests.post(f"{API}/import_tc", json=save_as_payload)
        save_res = r_save.json()
        print(f"  Save As response: {save_res}")
        save_as_id = save_res["id"]
        save_as_family = save_res.get("family_id", save_as_id)
        generated_tc_ids.append(save_as_id)
        assert save_as_id != new_tc_id
        assert save_as_family == save_as_id, "FAIL: New independent TC should have family_id == system_id!"
    
        # The synchronized save already published this exact version. A second
        # publish must be rejected without creating a duplicate Golden record.
        if save_as_payload.get("push_to_golden"):
            r_push = requests.post(f"{API}/push_to_golden", json={"system_id": save_as_id})
            push_res = r_push.json()
            print(f"  Save As Push to Golden response: {push_res}")
            assert r_push.status_code == 409
            assert push_res.get("reason") == "same_name"
        
        # Verify in local Plan
        r = requests.get(f"{API}/projects")
        data = r.json()
        proj_local = next(p for p in data["projects"] if p["name"] == "Project_test")
        plan_local = next(pl for pl in proj_local["plans"] if pl["name"] == "Plan_test")
        local_save_as_tc = next((t for t in plan_local["testcases"] if t["id"] == save_as_id), None)
        assert local_save_as_tc is not None
        assert local_save_as_tc.get("custom_subfolder") == "folder_save_as"
        
        # Verify Golden Plan got the independent TC and folder_save_as
        golden_proj = next(p for p in data["projects"] if p["name"] == "Golden_Project")
        golden_plan = next(pl for pl in golden_proj["plans"] if pl["name"] == "plan_golden")
        golden_save_as_tc = next((t for t in golden_plan["testcases"] if t["family_id"] == save_as_family), None)
        print(f"  -> Golden TC for Save As: {golden_save_as_tc}")
        assert golden_save_as_tc is not None, "FAIL: Independent Save As TC not pushed to Golden Plan!"
        assert golden_save_as_tc.get("custom_subfolder") == "folder_save_as", "FAIL: Subfolder not mapped in Golden!"
        assert "folder_save_as" in golden_plan["custom_subfolders"], "FAIL: folder_save_as not registered in Golden custom_subfolders!"
        generated_tc_ids.append(golden_save_as_tc["id"])
        print("  -> PASS: Save As independent TC and folder carry verified successfully")
    
        # 3. Save & Bump Version (儲存並進版)
        # Simulates bumping Test_Overwritten_TC to a new version (V2) under 'folder_v2' and push_to_golden=True
        print("\n[3] Test Save & Bump Version (儲存並進版) - Sync to Golden Plan")
        bump_payload = {
            "project": "Project_test",
            "plan_id": get_plan_uuid("Project_test", "Plan_test"),
            "category": "Custom",
            "tc_name": "Test_Overwritten_TC_V2",
            "family_id": p_tc["family_id"], # same family id as original
            "push_to_golden": True,
            "custom_subfolder": "folder_v2",
            "steps": overwrite_steps
        }
        r_bump = requests.post(f"{API}/import_tc", json=bump_payload)
        bump_res = r_bump.json()
        print(f"  Bump Version response: {bump_res}")
        bump_id = bump_res["id"]
        bump_family = bump_res["family_id"]
        generated_tc_ids.append(bump_id)
        assert bump_id != new_tc_id
        assert bump_family == p_tc["family_id"], "FAIL: Bumed version must share the original family_id!"
    
        if bump_payload.get("push_to_golden"):
            r_push = requests.post(f"{API}/push_to_golden", json={"system_id": bump_id})
            push_res = r_push.json()
            print(f"  Bump Version Push to Golden response: {push_res}")
            assert r_push.status_code == 409
            assert push_res.get("reason") == "same_name"
        
        # Reload and verify Golden Plan got the bumped version TC
        r = requests.get(f"{API}/projects")
        data = r.json()
        golden_proj = next(p for p in data["projects"] if p["name"] == "Golden_Project")
        golden_plan = next(pl for pl in golden_proj["plans"] if pl["name"] == "plan_golden")
        golden_bump_tc = next((t for t in golden_plan["testcases"] if t["id"] == bump_id or (t["family_id"] == bump_family and t["tc_name"] == "Test_Overwritten_TC_V2")), None)
        print(f"  -> Golden TC for Bumped Version: {golden_bump_tc}")
        assert golden_bump_tc is not None, "FAIL: Bumped version TC not pushed to Golden Plan!"
        assert golden_bump_tc.get("custom_subfolder") == "folder_v2", "FAIL: Subfolder folder_v2 not mapped in Golden!"
        assert "folder_v2" in golden_plan["custom_subfolders"], "FAIL: folder_v2 not registered in Golden custom_subfolders!"
        if golden_bump_tc["id"] not in generated_tc_ids:
            generated_tc_ids.append(golden_bump_tc["id"])
        print("  -> PASS: Save & Bump Version with family linking verified successfully")
    
    
        print("\n\n" + "="*50)
        print("  Part 6: Test Case Builder LED Execution  ")
        print("="*50)
    
        led_steps = [
            {"module_path": "testcase_database.steps.Resource_Chassis.Indicator_LED_Control.get_led", "preset": ""},
            {"module_path": "testcase_database.steps.Resource_Chassis.Indicator_LED_Control.patch_led", "preset": "Off"},
            {"module_path": "testcase_database.steps.Resource_Chassis.Indicator_LED_Control.verify_led", "preset": ""}
        ]
        print("\n[1] Running LED control steps directly via builder run simulator...")
        run_tc_and_assert_pass("Test_Builder_LED_Control", led_steps)
        print("  -> PASS: Builder simulator executed LED control successfully")
    
    
        print("\n\n" + "="*50)
        print("  Part 7: Import to Plan and Task Execution  ")
        print("="*50)
    
        print("\n[1] Importing LED TC into Project_test / Plan_test...")
        import_led_payload = {
            "project": "Project_test",
            "plan_id": get_plan_uuid("Project_test", "Plan_test"),
            "category": "Custom",
            "tc_name": "Test_Plan_test_LED_Control",
            "family_id": "",
            "steps": led_steps
        }
        r_import_led = requests.post(f"{API}/import_tc", json=import_led_payload)
        assert r_import_led.status_code == 200, f"Import LED TC failed: {r_import_led.text}"
        imported_led_id = r_import_led.json().get("id")
        print(f"  -> Imported TC ID: {imported_led_id}")
        generated_tc_ids.append(imported_led_id)
    
        print("\n[2] Fetching project tree to verify imported TC details...")
        r_proj = requests.get(f"{API}/projects")
        data_proj = r_proj.json()
        plan_t = next(pl for p in data_proj["projects"] if p["name"] == "Project_test" for pl in p["plans"] if pl["name"] == "Plan_test")
        imported_tc = next(tc for tc in plan_t["testcases"] if tc["id"] == imported_led_id)
        print(f"  -> Imported TC steps: {imported_tc['steps']}")
        assert len(imported_tc["steps"]) == 3, "FAIL: Imported TC steps list count is incorrect!"
    
        print("\n[3] Adding imported TC to Task_test...")
        build_test = next(b for b in plan_t["tasks"] if b["name"] == "Task_test")
        build_test["testcases"].append({
            "id": imported_led_id,
            "selected": True,
            "custom_subfolder": None
        })
        r_save_db = requests.post(f"{API}/projects", json=data_proj)
        assert r_save_db.status_code == 200, f"Save DB failed: {r_save_db.text}"
    
        print("\n[4] Re-fetching tree and verifying steps of the TC inside Task (Bug A verification)...")
        r_proj2 = requests.get(f"{API}/projects")
        data_proj2 = r_proj2.json()
        plan_t_updated = next(pl for p in data_proj2["projects"] if p["name"] == "Project_test" for pl in p["plans"] if pl["name"] == "Plan_test")
        build_updated = next(b for b in plan_t_updated["tasks"] if b["name"] == "Task_test")
        build_tc = next(tc for tc in build_updated["testcases"] if tc["id"] == imported_led_id)
        print(f"  -> Task TC Steps: {build_tc.get('steps')}")
        assert build_tc.get("steps") is not None, "FAIL: Steps are missing in Task TC object (Bug A not fixed)!"
        assert len(build_tc["steps"]) == 3, "FAIL: Steps count in Task TC object is incorrect!"
        print("  -> PASS: Task TC contains correct steps (Bug A verified)")
    
        print("\n[5] Running the Task TC using Task execution engine simulator...")
        run_tc_and_assert_pass("Test_Plan_test_LED_Control", build_tc["steps"])
        print("  -> PASS: Task execution of LED TC completed successfully")
    
    
        print("\n\n" + "="*50)
        print("  Part 8: Modify Step Preset Parameter Test  ")
        print("="*50)
    
        # We will update the preset of the second step (patch_led) inside imported_led_id from "Off" to "Lit"
        print("\n[1] Simulating changing patch_led preset from 'Off' to 'Lit'")
        modified_led_steps = [
            {"module_path": "testcase_database.steps.Resource_Chassis.Indicator_LED_Control.get_led", "preset": ""},
            {"module_path": "testcase_database.steps.Resource_Chassis.Indicator_LED_Control.patch_led", "preset": "Lit"},
            {"module_path": "testcase_database.steps.Resource_Chassis.Indicator_LED_Control.verify_led", "preset": ""}
        ]
        modify_payload = {
            "project": "Project_test",
            "plan_id": get_plan_uuid("Project_test", "Plan_test"),
            "category": "Custom",
            "tc_name": "Test_Plan_test_LED_Control",
            "family_id": imported_tc["family_id"],
            "steps": modified_led_steps,
            "overwrite": True,
            "original_id": imported_led_id
        }
        r_modify = requests.post(f"{API}/import_tc", json=modify_payload)
        print(f"  Modify response: {r_modify.json()}")
        assert r_modify.json().get("status") == "ok"
        
        # Re-fetch tree and verify that both Plan TC steps and Task TC steps are updated
        print("\n[2] Verifying parameter propagation on Plan and Task levels")
        r_prop = requests.get(f"{API}/projects")
        plan_t_prop = next(pl for p in r_prop.json()["projects"] if p["name"] == "Project_test" for pl in p["plans"] if pl["name"] == "Plan_test")
        plan_tc_prop = next(tc for tc in plan_t_prop["testcases"] if tc["id"] == imported_led_id)
        
        build_test_prop = next(b for b in plan_t_prop["tasks"] if b["name"] == "Task_test")
        build_tc_prop = next(tc for tc in build_test_prop["testcases"] if tc["id"] == imported_led_id)
        
        print(f"  Propagated Plan TC steps: {plan_tc_prop['steps']}")
        print(f"  Propagated Task TC steps: {build_tc_prop['steps']}")
        
        assert plan_tc_prop["steps"][1]["preset"] == "Lit", "FAIL: Preset not updated on Plan level!"
        assert build_tc_prop["steps"][1]["preset"] == "Lit", "FAIL: Preset not updated on Task level (loader reload failure)!"
        print("  -> PASS: Modified preset parameters propagated and verified on both Plan and Task levels")
    
        print("\n\n" + "="*50)
        print("  Part 9: Bloodline Retention (Family ID) on Version Bump Simulation  ")
        print("="*50)
    
        print("\n[1] Create a brand new TC 'Test_Bloodline_V1' via /import_tc")
        import_payload_v1 = {
            "project": "Project_test",
            "plan_id": get_plan_uuid("Project_test", "Plan_test"),
            "category": "Custom",
            "tc_name": "Test_Bloodline_V1",
            "family_id": "",
            "steps": [{"module_path": "test", "preset": ""}]
        }
        r_v1 = requests.post(f"{API}/import_tc", json=import_payload_v1)
        v1_data = r_v1.json()
        assert v1_data.get("status") == "ok"
        v1_system_id = v1_data.get("id")
        v1_family_id = v1_data.get("family_id")
        generated_tc_ids.append(v1_system_id)
        print(f"  -> Created V1. system_id={v1_system_id}, family_id={v1_family_id}")
    
        print("\n[2] Simulating Builder Export/Import logic (Bumping Version to V2 with retained family_id)")
        import_payload_v2 = {
            "project": "Project_test",
            "plan_id": get_plan_uuid("Project_test", "Plan_test"),
            "category": "Custom",
            "tc_name": "Test_Bloodline_V2",
            "family_id": v1_family_id,
            "steps": [{"module_path": "test", "preset": "modified_preset"}]
        }
        r_v2 = requests.post(f"{API}/import_tc", json=import_payload_v2)
        v2_data = r_v2.json()
        assert v2_data.get("status") == "ok"
        v2_system_id = v2_data.get("id")
        v2_family_id = v2_data.get("family_id")
        generated_tc_ids.append(v2_system_id)
        
        print(f"  -> Created V2. system_id={v2_system_id}, family_id={v2_family_id}")
        
        print("\n[3] Verifying Bloodline Inheritance")
        assert v2_system_id != v1_system_id, "FAIL: system_id should be completely new for V2"
        assert v2_family_id == v1_family_id, f"FAIL: family_id not retained! Expected {v1_family_id}, got {v2_family_id}"
        print("  -> PASS: family_id successfully inherited by V2!")
    
        print("\n" + "="*50)
        print("  Part 11: Incremental Updates (PATCH) API Verification  ")
        print("="*50)
    
        # A. 建立 Project & Plan 與一個 TestCase 用於 PATCH 測試
        print("\n[1] Setup test Project, Plan, and TestCase")
        requests.post(f"{API}/create_project", json={"project": "Patch_Test_Proj"})
        plan_r = requests.post(f"{API}/create_plan", json={"project": "Patch_Test_Proj", "plan_name": "Patch_Test_Plan"})
        patch_plan_id = plan_r.json().get("plan_id")
        
        # 匯入一個 TestCase 到此 Plan
        import_r = requests.post(f"{API}/import_tc", json={
            "project": "Patch_Test_Proj",
            "plan_id": patch_plan_id,
            "category": "Custom",
            "tc_name": "Test_Patch_TC_01",
            "steps": [{"module_path": "test", "preset": ""}]
        })
        tc_uuid = import_r.json().get("id")
        generated_tc_ids.append(tc_uuid)
        print(f"  -> Created Test Project/Plan/TC. tc_uuid={tc_uuid}")
    
        # B. 測試 PATCH /api/testcases/<tc_uuid>
        print("\n[2] Test PATCH /api/testcases/<id> (Update Category and Selected)")
        patch_tc_r = requests.patch(f"{API}/testcases/{tc_uuid}", json={
            "selected": False,
            "folder_path": "NewPatchCategory/PatchFolder"
        })
        assert patch_tc_r.status_code == 200, f"PATCH TC failed: {patch_tc_r.text}"
        
        # 從 GET /api/projects 查詢驗證
        proj_state = requests.get(f"{API}/projects").json()
        matched_tc = None
        for p in proj_state.get("projects", []):
            if p["name"] == "Patch_Test_Proj":
                for pl in p.get("plans", []):
                    if pl["id"] == patch_plan_id:
                        for t in pl.get("testcases", []):
                            if t["id"] == tc_uuid:
                                matched_tc = t
        assert matched_tc is not None, "Could not find patched TestCase"
        assert matched_tc.get("selected") is False, f"Expected selected=False, got {matched_tc.get('selected')}"
        assert matched_tc.get("category") == "NewPatchCategory", f"Expected category=NewPatchCategory, got {matched_tc.get('category')}"
        assert matched_tc.get("custom_subfolder") == "PatchFolder", f"Expected custom_subfolder=PatchFolder, got {matched_tc.get('custom_subfolder')}"
        print("  -> PASS: PATCH TestCase successfully updated selected, category, and custom_subfolder.")
    
        # C. 測試 PATCH /api/plans/<plan_id>/testcases (批量勾選)
        print("\n[3] Test PATCH /api/plans/<plan_id>/testcases (Batch select all)")
        batch_tc_r = requests.patch(f"{API}/plans/{patch_plan_id}/testcases", json={"selected": True})
        assert batch_tc_r.status_code == 200, f"PATCH plan testcases failed: {batch_tc_r.text}"
        
        proj_state = requests.get(f"{API}/projects").json()
        for p in proj_state.get("projects", []):
            if p["name"] == "Patch_Test_Proj":
                for pl in p.get("plans", []):
                    if pl["id"] == patch_plan_id:
                        for t in pl.get("testcases", []):
                            assert t.get("selected") is True, "Batch select failed to update TestCase selected state"
        print("  -> PASS: PATCH plan testcases successfully batch-selected all testcases.")
    
        # D. 測試 POST /api/tasks (建立 Task)
        print("\n[4] Test POST /api/tasks (Create task)")
        build_uuid = "test_task_patch_uuid"
        create_b_r = requests.post(f"{API}/tasks", json={
            "plan_id": patch_plan_id,
            "id": build_uuid,
            "name": "Task_Patch_Alpha"
        })
        assert create_b_r.status_code == 200, f"POST create task failed: {create_b_r.text}"
        print("  -> PASS: POST tasks successfully created task.")
    
        # E. 測試 PATCH /api/tasks/<build_uuid> (重命名 Task)
        print("\n[5] Test PATCH /api/tasks/<id> (Rename task)")
        rename_b_r = requests.patch(f"{API}/tasks/{build_uuid}", json={"name": "Task_Patch_Renamed"})
        assert rename_b_r.status_code == 200, f"PATCH rename task failed: {rename_b_r.text}"
        print("  -> PASS: PATCH tasks successfully renamed task.")
    
        # F. 測試 POST /api/tasks/<build_uuid>/testcases/import (從 Plan 匯入 TC)
        print("\n[6] Test POST /api/tasks/<id>/testcases/import (Import testcase)")
        import_b_tc_r = requests.post(f"{API}/tasks/{build_uuid}/testcases/import", json={
            "testcases": [{"id": tc_uuid, "custom_subfolder": "PatchFolder", "selected": True}]
        })
        assert import_b_tc_r.status_code == 200, f"POST import task testcases failed: {import_b_tc_r.text}"
        print("  -> PASS: POST task testcases successfully imported testcase to task.")
    
        # G. 測試 PATCH /api/task_testcases/<build_uuid>/<tc_uuid> (更新 TaskTestCase 屬性)
        print("\n[7] Test PATCH /api/task_testcases/<build_id>/<tc_id> (Update TaskTestCase selected)")
        patch_b_tc_r = requests.patch(f"{API}/task_testcases/{build_uuid}/{tc_uuid}", json={
            "selected": False,
            "position": 5
        })
        assert patch_b_tc_r.status_code == 200, f"PATCH build_testcase failed: {patch_b_tc_r.text}"
        
        proj_state = requests.get(f"{API}/projects").json()
        matched_btc = None
        for p in proj_state.get("projects", []):
            if p["name"] == "Patch_Test_Proj":
                for pl in p.get("plans", []):
                    if pl["id"] == patch_plan_id:
                        for b in pl.get("tasks", []):
                            if b["id"] == build_uuid:
                                for bt in b.get("testcases", []):
                                    if bt["id"] == tc_uuid:
                                        matched_btc = bt
        assert matched_btc is not None, "Could not find TaskTestCase"
        assert matched_btc.get("selected") is False, f"Expected selected=False, got {matched_btc.get('selected')}"
        print("  -> PASS: PATCH task_testcases successfully updated selected state.")
    
        # H. 測試 POST /api/tasks/<build_uuid>/testcases/reorder (排序)
        print("\n[8] Test POST /api/tasks/<id>/testcases/reorder")
        reorder_r = requests.post(f"{API}/tasks/{build_uuid}/testcases/reorder", json={"order": [tc_uuid]})
        assert reorder_r.status_code == 200, f"POST reorder task testcases failed: {reorder_r.text}"
        print("  -> PASS: POST task testcases reorder successfully processed.")
    
        # I. 測試 PATCH /api/plans/<plan_id> (更新 Plan 子資料夾)
        print("\n[9] Test PATCH /api/plans/<plan_id> (Update subfolders)")
        patch_plan_r = requests.patch(f"{API}/plans/{patch_plan_id}", json={
            "custom_subfolders": ["Sub1", "Sub2"]
        })
        assert patch_plan_r.status_code == 200, f"PATCH plan failed: {patch_plan_r.text}"
        print("  -> PASS: PATCH plan successfully updated custom_subfolders.")
    
        # J. 測試 DELETE /api/tasks/<build_uuid> (刪除 Task)
        print("\n[10] Test DELETE /api/tasks/<id> (Delete task)")
        delete_b_r = requests.delete(f"{API}/tasks/{build_uuid}")
        assert delete_b_r.status_code == 200, f"DELETE task failed: {delete_b_r.text}"
        print("  -> PASS: DELETE tasks successfully removed task.")
    
        print("\n\n" + "="*50)
        print("  Part 12: Warehouse Fork & Import Category Regression Test  ")
        print("="*50)
    
        # 1. 驗證 /api/testcases 回傳結果包含 "testcase" 欄位
        print("\n[1] Verify /api/testcases returns 'testcase' field")
        tc_list_r = requests.get(f"{API}/testcases")
        assert tc_list_r.status_code == 200
        tc_list = tc_list_r.json()
        golden_tc = next((t for t in tc_list if t["project"] == "Golden_Project"), None)
        assert golden_tc is not None, "Golden Project TC not found in /api/testcases"
        assert "testcase" in golden_tc, "testcase key missing in /api/testcases response!"
        assert golden_tc["testcase"] == golden_tc["tc_name"], f"Expected testcase == tc_name, got {golden_tc['testcase']}"
        print("  -> PASS: 'testcase' field validated successfully in /api/testcases.")
    
        # 2. 驗證從測項倉庫 Fork 測項 (/api/fork_tc)
        print("\n[2] Test Forking TC from library via /api/fork_tc")
        requests.post(f"{API}/create_project", json={"project": "Fork_Test_Proj"})
        fork_plan_r = requests.post(f"{API}/create_plan", json={"project": "Fork_Test_Proj", "plan_name": "Fork_Test_Plan"})
        fork_plan_id = fork_plan_r.json().get("plan_id")
        
        # 驗證建立的 Plan ID 為 UUID，且不等於 Plan 名稱字串
        is_uuid = len(fork_plan_id) == 36 and fork_plan_id.count('-') == 4
        assert is_uuid, f"Expected UUID for plan_id, got {fork_plan_id}"
        assert fork_plan_id != "Fork_Test_Plan", "Plan ID should not be equal to plan name!"
        print(f"  -> Plan UUID creation verified. ID: {fork_plan_id}")
        
        fork_payload = {
            "project": "Fork_Test_Proj",
            "plan_id": fork_plan_id,
            "category": golden_tc["category"],
            "testcase": golden_tc["testcase"]
        }
        fork_r = requests.post(f"{API}/fork_tc", json=fork_payload)
        assert fork_r.status_code == 200, f"Fork failed: {fork_r.text}"
        fork_tc_id = fork_r.json().get("id")
        generated_tc_ids.append(fork_tc_id)
        print(f"  -> Fork succeeded. New TC ID: {fork_tc_id}")
    
        # 3. 驗證外部匯入的分類在 saveDB 呼叫後不會退化
        print("\n[3] Test Import Category Retention after saveDB simulation")
        import_payload = {
            "project": "Fork_Test_Proj",
            "plan_id": fork_plan_id,
            "category": "Custom",
            "tc_name": "Test_Category_Retention_TC",
            "family_id": "",
            "steps": [{"module_path": "test", "preset": ""}]
        }
        imp_r = requests.post(f"{API}/import_tc", json=import_payload)
        assert imp_r.status_code == 200
        imp_tc_id = imp_r.json().get("id")
        generated_tc_ids.append(imp_tc_id)
        print(f"  -> Imported TC ID: {imp_tc_id} under Category: 'Custom'")
    
        # 模擬 Web UI 發送缺乏 category 欄位的 saveDB payload
        proj_tree_r = requests.get(f"{API}/projects")
        proj_tree = proj_tree_r.json()
        
        # 找到目標 Plan，並將其中的 imported TC 修改為 bare object
        target_plan = None
        for p in proj_tree.get("projects", []):
            if p["name"] == "Fork_Test_Proj":
                for pl in p.get("plans", []):
                    if pl["id"] == fork_plan_id:
                        target_plan = pl
                        
        assert target_plan is not None
        # 將 imported TC 取代成只有 id 和 selected 屬性的 bare object (模擬舊 UI bug 狀態)
        new_tcs = []
        for tc in target_plan.get("testcases", []):
            if tc["id"] == imp_tc_id:
                new_tcs.append({"id": imp_tc_id, "selected": True})
            else:
                new_tcs.append(tc)
        target_plan["testcases"] = new_tcs
        
        # 呼叫 POST /api/projects 儲存 (saveDB)
        save_r = requests.post(f"{API}/projects", json=proj_tree)
        assert save_r.status_code == 200, f"saveDB post failed: {save_r.text}"
        print("  -> saveDB simulation posted bare object successfully.")
    
        # 驗證分類是否依然維持為 "Custom"
        ver_tree_r = requests.get(f"{API}/projects")
        ver_tree = ver_tree_r.json()
        ver_tc = None
        for p in ver_tree.get("projects", []):
            if p["name"] == "Fork_Test_Proj":
                for pl in p.get("plans", []):
                    if pl["id"] == fork_plan_id:
                        for tc in pl.get("testcases", []):
                            if tc["id"] == imp_tc_id:
                                ver_tc = tc
                                
        assert ver_tc.get("category") == "Custom", f"Category deteriorated! Expected 'Custom', got '{ver_tc.get('category')}'"
        print("  -> PASS: Category retention verified successfully.")
    
        # 4. 驗證 Plan ID 在 saveDB 模擬後依然保持為原始的 UUID 且未退化為名稱
        ver_plan = None
        for p in ver_tree.get("projects", []):
            if p["name"] == "Fork_Test_Proj":
                for pl in p.get("plans", []):
                    if pl["name"] == "Fork_Test_Plan":
                        ver_plan = pl
        assert ver_plan is not None
        assert ver_plan["id"] == fork_plan_id, f"Plan ID deteriorated after saveDB! Expected '{fork_plan_id}', got '{ver_plan['id']}'"
        print("  -> PASS: Plan UUID retention verified successfully.")
    
    finally:
        print("\n\n" + "="*50)
        print("  Part 10: Robust Teardown Cleanup  ")
        print("="*50)
        print("Starting database and file system cleanup...")
        try:
            # Delete Project_test via API
            print("Deleting testing project 'Project_test' via API...")
            requests.post(f"{API}/delete_project", json={"project": "Project_test"})
            requests.post(f"{API}/delete_project", json={"project": "Patch_Test_Proj"})
            requests.post(f"{API}/delete_project", json={"project": "Fork_Test_Proj"})
            
            db_path = str(WORKSPACE_DIR / "testcase_meta.db")
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                
                # Find all test cases created by tests
                c.execute("SELECT system_id, display_name FROM testcases WHERE display_name LIKE 'Test_%'")
                tcs = c.fetchall()
                deleted_ids = [tc[0] for tc in tcs]
                
                # Merge with generated_tc_ids to be absolutely thorough
                for tc_id in generated_tc_ids:
                    if tc_id and tc_id not in deleted_ids:
                        deleted_ids.append(tc_id)
                
                print(f"Found {len(deleted_ids)} generated test cases to clean up from database...")
                for tc_id in deleted_ids:
                    c.execute("DELETE FROM task_testcases WHERE testcase_id = ?", (tc_id,))
                    c.execute("DELETE FROM testcases WHERE system_id = ?", (tc_id,))
                    
                # Clean custom subfolders and project plans
                c.execute("DELETE FROM plan_subfolders WHERE subfolder_name IN ('folder_abc', 'folder_xyz', 'folder_batch', 'test01', 'test02', 'folder_save_as', 'folder_v2')")
                # cascade delete via projects
                c.execute("DELETE FROM projects WHERE name IN ('Project_test', 'TEST_PROJ', 'TestProject_V9_Alpha', 'TestProject_V9_Beta', 'Patch_Test_Proj', 'Fork_Test_Proj')")
                
                conn.commit()
                conn.close()
                print("Database cleanup completed successfully.")
                
                # Clean physical script directories
                main_program_dir = str(MAIN_PROGRAM_DIR)
                deleted_dirs_count = 0
                for tc_id in deleted_ids:
                    if tc_id:
                        d = os.path.join(main_program_dir, "testcase_database", "scripts", tc_id)
                        if os.path.exists(d):
                            shutil.rmtree(d)
                            deleted_dirs_count += 1
                print(f"Deleted {deleted_dirs_count} generated step directory/directories on filesystem.")
                print("Filesystem script directory cleanup completed successfully.")
            else:
                print(f"Warning: Database path '{db_path}' does not exist, skipping DB cleanup.")
        except Exception as ex:
            print(f"Error occurred during teardown cleanup: {ex}")
    
    print("\nAll lifecycle tests completed successfully!")
    

FAKE_REDFISH_MODULE = '''
class FakeResponse:
    def __init__(self, status=200, data=None):
        self.status = status
        self.dict = data or {}
        self.text = ""
        self.headers = {"ETag": 'W/"sandbox"'}


class FakeClient:
    def __init__(self):
        self.indicator_led = "Lit"

    def login(self, auth="basic"):
        return None

    def logout(self):
        return None

    def get(self, path, *args, **kwargs):
        return FakeResponse(200, {
            "@odata.etag": 'W/"sandbox"',
            "IndicatorLED": self.indicator_led,
            "IndicatorLED@Redfish.AllowableValues": ["Lit", "Blinking", "Off"],
        })

    def patch(self, path, body=None, *args, **kwargs):
        if body and "IndicatorLED" in body:
            self.indicator_led = body["IndicatorLED"]
        return FakeResponse(204, {})


def redfish_client(**kwargs):
    return FakeClient()
'''


def _reserve_local_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _snapshot_database(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(source)) as source_conn:
        with closing(sqlite3.connect(destination)) as destination_conn:
            source_conn.backup(destination_conn)


def _create_shadow_project():
    SANDBOX_PARENT.mkdir(parents=True, exist_ok=True)
    sandbox = SANDBOX_PARENT / f"bmc-agent-lifecycle-{uuid.uuid4()}"
    sandbox.mkdir()

    shadow_web_ui = sandbox / "web_ui"
    shadow_main = sandbox / "main_program"
    shadow_workspace = shadow_web_ui / "workspace"
    shadow_web_ui.mkdir()
    shadow_main.mkdir()
    (shadow_workspace / "logs").mkdir(parents=True)
    (shadow_workspace / "results").mkdir()

    for name in ("app.py", "models.py", "plan_state.py", "single_case.py", "report_generator.py"):
        shutil.copy2(WEB_UI_DIR / name, shadow_web_ui / name)

    shutil.copy2(
        REPO_ROOT / "main_program" / "console_helper.py",
        shadow_main / "console_helper.py",
    )
    shutil.copytree(
        REPO_ROOT / "main_program" / "testcase_database",
        shadow_main / "testcase_database",
    )

    _snapshot_database(
        Path(os.environ.get("BMC_LIFECYCLE_SOURCE_DB", WEB_UI_DIR / "workspace" / "testcase_meta.db")),
        shadow_workspace / "testcase_meta.db",
    )
    source_backup = WEB_UI_DIR / "tests" / "fixtures" / "testcase_meta_legacy.db"
    if source_backup.is_file():
        shutil.copy2(
            source_backup,
            shadow_workspace / "testcase_meta_legacy.db",
        )
    else:
        _snapshot_database(
            Path(os.environ.get("BMC_LIFECYCLE_SOURCE_DB", WEB_UI_DIR / "workspace" / "testcase_meta.db")),
            shadow_workspace / "testcase_meta_legacy.db",
        )
    (shadow_main / "config.yaml").write_text(
        "redfish:\n"
        '  host: "https://sandbox.invalid"\n'
        '  username: "sandbox"\n'
        '  password: "sandbox"\n'
        "  verify_ssl: false\n",
        encoding="utf-8",
    )
    (shadow_web_ui / "redfish.py").write_text(
        FAKE_REDFISH_MODULE,
        encoding="utf-8",
    )
    return sandbox, shadow_web_ui, shadow_main, shadow_workspace


def _remove_shadow_project(sandbox):
    resolved_parent = SANDBOX_PARENT.resolve()
    resolved_sandbox = sandbox.resolve()
    if resolved_sandbox.parent != resolved_parent:
        raise RuntimeError(f"refusing to remove sandbox outside parent: {sandbox}")
    if not resolved_sandbox.name.startswith("bmc-agent-lifecycle-"):
        raise RuntimeError(f"refusing to remove unexpected sandbox: {sandbox}")

    last_error = None
    for _ in range(40):
        try:
            shutil.rmtree(resolved_sandbox)
            return
        except FileNotFoundError:
            return
        except OSError as error:
            last_error = error
            time.sleep(0.25)
    raise RuntimeError(f"could not remove sandbox {sandbox}: {last_error}")


class DatabaseLifecycleTest(unittest.TestCase):
    def test_full_lifecycle_in_shadow_project(self):
        sandbox, shadow_web_ui, shadow_main, shadow_workspace = (
            _create_shadow_project()
        )
        server = None
        server_log_handle = None
        keep_sandbox = os.environ.get("BMC_KEEP_TEST_SANDBOX") == "1"
        try:
            port = _reserve_local_port()
            server_log = sandbox / "server.log"
            server_log_handle = server_log.open("wb")
            server_env = os.environ.copy()
            server_env["BMC_WEB_UI_WORKSPACE_DIR"] = str(shadow_workspace)
            server_env["BMC_MAIN_PROGRAM_DIR"] = str(shadow_main)
            server_env["PYTHONPATH"] = os.pathsep.join(
                (str(shadow_web_ui), str(shadow_main))
            )
            server = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    (
                        "from app import app; "
                        f"app.run(host='127.0.0.1', port={port}, "
                        "debug=False, threaded=True, use_reloader=False)"
                    ),
                ],
                cwd=shadow_web_ui,
                env=server_env,
                stdout=server_log_handle,
                stderr=subprocess.STDOUT,
            )

            api_root = f"http://127.0.0.1:{port}/api"
            deadline = time.time() + 15
            while time.time() < deadline:
                if server.poll() is not None:
                    break
                try:
                    response = requests.get(f"{api_root}/projects", timeout=0.5)
                    if response.status_code == 200:
                        break
                except requests.RequestException:
                    time.sleep(0.1)
            else:
                self.fail(f"sandbox server did not start; log: {server_log}")

            self.assertIsNone(
                server.poll(),
                f"sandbox server exited early; log: {server_log}",
            )

            worker_env = os.environ.copy()
            worker_env.update(
                {
                    "BMC_LIFECYCLE_API": api_root,
                    "BMC_LIFECYCLE_WORKSPACE_DIR": str(shadow_workspace),
                    "BMC_LIFECYCLE_MAIN_PROGRAM_DIR": str(shadow_main),
                }
            )
            worker = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--worker"],
                cwd=REPO_ROOT,
                env=worker_env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=180,
            )
            if worker.returncode != 0:
                server_log_handle.flush()
                server_output = server_log.read_text(
                    encoding="utf-8",
                    errors="replace",
                )
                self.fail(
                    "lifecycle worker failed\n"
                    f"stdout:\n{worker.stdout}\n"
                    f"stderr:\n{worker.stderr}\n"
                    f"server:\n{server_output}"
                )
            for part in range(13):
                self.assertIn(
                    f"Part {part}:",
                    worker.stdout,
                    f"lifecycle worker skipped Part {part}",
                )
            self.assertIn(
                "All lifecycle tests completed successfully!",
                worker.stdout,
            )
        finally:
            if server is not None and server.poll() is None:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=5)
            if server_log_handle is not None:
                server_log_handle.close()
            if keep_sandbox:
                print(f"Lifecycle sandbox retained at: {sandbox}")
            else:
                _remove_shadow_project(sandbox)


if __name__ == "__main__":
    if "--worker" in sys.argv:
        main()
    else:
        unittest.main()
