# 發布驗證 — 2026-10-30

BMCAgent已啟動於http://127.0.0.1:5000/。來源發布commit：[d3cb74a](https://github.com/baga0607-cpu/bmcauto/commit/d3cb74ab1e50f172b3763fbffecb43090e3121fe)。push後以ls-remote核對一致。接續入口：[2026-10-30-handoff.md](2026-10-30-handoff.md)。

## 本次測試
- Python：150 passed / 0 failures / 0 errors / 0 skipped。
- 模組：test_automation_labels、test_batch_case_import、test_mixed_case_selection、test_parameter_completion、test_report_case、test_report_exports、test_schedule_calendar、test_single_case_repository、test_source_created_at、test_task_actual_dates、test_task_day_counts、test_task_reference_package、test_task_schedule、test_task_status、test_task_types、test_task_owner、test_task_owner_history、test_project_import。
- 額外test_case_log_integration：8 passed；六支真實RF來源SDK/HTTP mocked，不連DUT。
- JavaScript：case_windows.test.cjs、execution_workspace.test.cjs、hierarchical_selection.test.cjs、task_management_list.test.cjs、keyword_search.test.cjs，全部exit 0。
- BMC_WEB_UI_WORKSPACE_DIR、BMC_MAIN_PROGRAM_DIR、TEMP/TMP指向本次隔離子目錄，PYTHONPATH=BMCAgent。
- 驗證器：bmca-runtime/verification/release-20261030/run_tests.py。未跑完整suite，歷史測試未計入。
- 暫存diff --check通過；排除正式DB、workspace、Log、runtime generation folders及.impeccable。
- 正式HTTP 200、integrity_check=ok、foreign_key_check=0、active Tasks=0。

## 發布範圍
- 保留遠端歷史，基準8a245db，非force push，未推退役origin。
- 本機來源提交115檔，遠端來源提交86檔；部分功能已先發布、Markdown清理本機路徑、換行標準化，造成差異。
- 包含程式、測試、功能文件、輸出規範、六支RF來源資產。
- DB使用SQLite backup，未被測試副本取代。既存binary fixture變更保留未提交。
- 發布文件清理機器路徑/私人LAN位址，不含正式設定、DB或證據。
- 來源發布後建立交接文件，另推文件commit；最終SHA與hash回執保留本機publication-result.json。

## 本機證據
<LOCAL_PATH>
- python-result.json、python-tests.log、case-log-integration.log、js-tests.log
- formal-health.json、formal-started.db（私人備份，不發布）
- source-files.json、publication-result.json（最終推送後產生）
