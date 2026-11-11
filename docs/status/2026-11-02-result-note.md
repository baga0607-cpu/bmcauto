# RF recommendation results and execution Note — 2026-11-02

## User decisions

RF-01-008 and RF-01-013 use DSP0266 1.25.0 section 6.7 Table 4 (Required=No) and DSP0268 2026.2 section 6.61. Accept explicitly permitted deviations as PASS and retain their reason in Note. Report layout is deferred to the separate chat "BMCAgent 報告格式與 Note 欄位討論"; no HTML/PDF field was added. Renderer sources were compared to pre-task copies and are unchanged.

## Delivered

- RF-01-008: final HTTP 404 is PASS with Note explaining the non-mandatory endpoint and unperformed content validation. HTTP 200 still requires valid YAML/mapping/declared property types; other HTTP, connection, redirect and content errors retain Fail/Error.
- RF-01-013: accepts declared same-origin supported JSON/XML files without a path-prefix whitelist. Complete discovery, at least one supported file and every file's acquisition/recognition remain necessary. /Schemas/ recommendation evidence is independent; missing evidence is an accepted PASS check with Note, not a claim the unprobed endpoint is absent. Archive-only declarations remain outside current individual-file support and explicitly incomplete; not evidence of a mandatory DUT violation.
- Compatible optional note argument on CaseLog.check/step/finish. Recorded note remains separate from expected/actual and reason. save_result derives result_json.note and task_testcases.result_note from explicit evidence; summaries read the small field without fetching full logs. Additive nullable migration preserves historical results. Reruns clear the field; manual overrides retain the execution note.
- Execution table shows an escaped, wrapping Note field, with an em dash for legacy/empty notes. Full new logs retain Note, including existing report log attachments. No report layout changes.

## Validation

- 9 RF-01-008 offline groups and 13 RF-01-013 offline groups passed, with network blocked and warnings treated as errors. New expectations first reproduced failures before implementation.
- 12 targeted platform tests passed: real runner persistence, summary exposure, rerun clearing/manual preservation, idempotent additive migration, old log compatibility and existing log integration. Test databases/scripts and TEMP/TMP were isolated under bmca-runtime/verification/result-note-20261102.
- Execution Note browser fixture passed: PASS remains PASS, long/malicious-looking text is escaped, legacy empty values render, light/dark screenshots inspected. JS syntax check passed.
- Captured formal RF-01-013 HTTP responses replayed offline: PASS, three recognized local files, zero recommended entries, nonempty Note; no DUT/network request.
- An exploratory broad suite encountered two pre-existing inherited tests expecting full evidence from the now-lightweight summary API; targeted summary contract test passed. Existing execution-controls browser suite reached a sandbox-canceled download; the new isolated Note browser test passed. No claim that the entire repository suite passed.

## Local rollout and preservation

Backup: bmca-runtime/verification/result-note-20261102/formal-before.db plus original Plan sources and touched-source copies. Confirmed no active Task before restart. Service restarted and HTTP 200 verified. Two new Repository versions imported and the two matching Plan copies updated through supported APIs (only blank-line differences from their original sources). Plan source creation timestamps and settings retained, revision incremented and prior results marked for rerun. Old Repository versions retained.

All formal Task membership status/result_json/log_text/api_log_text/executed_at/manual overrides compared equal to backup after migration and source update. SQLite integrity_check=ok and foreign_key_check empty. Summary Note field verified empty for historical runs, with rerun flags set. No physical BMC execution and no GitHub publication.

後續決定（11/3 核對）：Execution 測項列表移除 Note 欄，維持六欄。此決定取代上文較早的顯示規格。結果與報告仍保留 Note。對應回歸測試見 web_ui/tests/result_note.test.cjs。
