2026-11-12 latest report: Case Name is the only disclosure; Test Data and Test Information expand together. Result Summary and standalone Note removed, method table retained under Test Data. Formal service updated at 16:17. See [report hierarchy](2026-11-12-report-hierarchy.md).

2026-11-12 latest deployment: Desktop launcher now offers Restart service and recognizes the Windows Python parent/child chain. Formal service restarted at 15:40; CP migration enabled, all 21 tables preserved. Existing saved FAIL results remain unchanged. See [restart handoff](2026-11-12-desktop-restart-cp.md).

2026-11-12 latest: RF-01-008 and shared Log / Execution / preview / HTML / PDF now support CP + mandatory Note, Skip + Reason, and Record COMPLETED. Standalone report Note removed; historical notes retained in table. Formal service restart / independent Plan source update pending. See [2026-11-12-rf008-conditional-pass.md](2026-11-12-rf008-conditional-pass.md).

**最新功能（2026-11-12）**：Execution 新增單一 Test Case 報告預覽；本機按鈕在 Log 右側，彈窗共用正式報告渲染並支援 Refresh。驗證、遠端舊版接點與精確本機 patch 見 [報告預覽交接](2026-11-12-execution-report-preview.md)。

**最新規則（2026-11-12）**：取消 S/C/R ID；採 Step／Type／Description／Result／Judgement 五欄，Type 僅 Command／Action／Checkpoint／Record。RF-01-001／002、Log 與報告同步更新，見 [編號與 Type 交接](2026-11-12-numbered-method-types.md)。

**最新報告更新（2026-11-12）**：HTML／PDF 加入 Step、Checkpoint、Record 關聯 ID 與結果表，採緊湊列距；驗證與發佈範圍見 [報告交接](2026-11-12-report-method-results.md)。

**最新測項更新（2026-11-11）**：RF-01-001／002 已採 Step／Checkpoint／Record 與關聯 ID，Log 同步更新；其他測項及正式 Repository／Plan 副本未改。見 [S/C/R 交接](2026-11-11-rf01-method-items.md)。

**同日後續：Connection UI** 已改為 BMC／Console Server／DUT OS 三個可收折區塊與九欄；Console Port 儲存使用 telnet 0，cpc 僅記錄為待實作連線規格，未修改 case.py。見 [Connection 更新](2026-11-11-connection-groups.md)。

# 三個開發對話統合交接 — 2026-11-11

本文件是封存前的最新入口；時間以 Asia/Taipei 為準。涵蓋「Test Case工作區」、「操作流暢度改動」、「調整Execution工作區」。同一主題以使用者後續定案及本次程式查核為準；歷史文件、對話內的「已完成／已上線」只代表當時本機狀態，不代表已發布的遠端程式具備相同功能。

## 來源與保存範圍

| 對話（原名稱） | Chat ID | 已讀回合 | 需求與結論備份 |
| --- | --- | ---: | --- |
| Test Case工作區 | 01a1c449-35d3-72d3-ac28-f990d1049a35 | 4 | [逐回合紀錄](conversation-records/2026-11-11-test-case.md) |
| 操作流暢度改動 | 01a19b81-6a85-7863-ae98-8ee94cb819cd | 25 | [逐回合紀錄](conversation-records/2026-11-11-task-ux.md) |
| 調整Execution工作區 | 01a18a73-6b0c-7fc2-a0e6-11ed38faecf3 | 26 | [逐回合紀錄](conversation-records/2026-11-11-execution.md) |

三個對話皆使用 read_thread 分頁讀至 hasMore=false，共55回合。備份保留工具所提供的使用者文字、最終答覆、turn ID、時間及狀態；不含圖片本體、工具輸出、推理或每則進度訊息，並非完整原始聊天匯出。發布副本移除本機個人路徑／私人網路位址；本機 conversation-backup-20261111 保存未做此替換的文字副本與整合前 Git 清單。本次未封存、刪除或傳訊至來源對話。

## 本機與發布狀態

- 工作區由 BMCAgent Git repository、外層 testcases/redfish、docs/redfish-compliance、HANDOFF.md 及 bmca-runtime 組成；外層不是這次發布 repository。
- 查核時本機 BMCAgent 位於 main / 38c1621，有179筆 Git status entries，包含既有程式、測試、文件、fixture及runtime生成檔。這不是179個已完成產品功能；不可用 reset/clean 或遠端版本覆蓋。
- 遠端發布基準是 baga0607-cpu/bmcauto 的 main / f6a7b12a011eff1b2e6c62251eaedb5709739154。舊 origin（Ulrox0880/BMC-Agent_Codex）已退役，不可推送。
- 本次使用 bmca-runtime/publish-handoff-20261111 獨立 checkout，發布交接與相關文件，不發布既有未提交產品程式、正式 DB、Log、憑證、匯入後測項副本或設計截圖。因此重新 clone 遠端後，不可假設下列「本機已完成」都已存在於遠端程式。
- 本次未重啟服務、未查寫正式 Task/DB、未匯入測項、未執行實體 DUT。歷史文件中的 active Tasks、資料筆數與 HTTP 200 不當作今日即時狀態。
- 本機13支 RF-01 工作來源與 BMCAgent/test_assets/redfish 的13支發布來源逐檔 byte compare 一致；RF-14 仍無已交付實作。

## 一、Test Case工作區

### 已完成與不可退回的契約

RF-01-001～013 均已有獨立 .py 與離線驗證紀錄。建立來源、匯入 Repository、加入 Plan、真正執行 DUT 是不同階段，不得混稱全部完成。完整清單見 [RF-01 handoff](../redfish-compliance/2026-11-02-rf01-handoff.md)、[case list](../redfish-compliance/rf-01-case-list.md)。

- 一個 Test Case 一個 .py，不恢復 step/block 執行架構；test_method 是文件 metadata。
- 英文 Python source／metadata／訊息及 Spec Ref.；保留來源 created_at，改版另記 modified_at。
- 使用 Task 的 context 連線資料，不硬編碼 DUT、不回退全域 YAML。
- 統一 CaseLog section/http/check/step/finish；Step／Criteria／Result 保存實際證據，未走到的步驟 Result=None。log.step 不自動產生獨立測項結果。
- 005 固定半自動：preset 優先，否則等待測試者提供預期版本；無回答 timer，空白提交 Fail。Task Connection 不算測項可編輯 Parameters。
- 008/013 的 PASS＋Note 只適用 [execution policy](../redfish-compliance/execution-policy.md) 明列分支：008 的404需精確 error.message；400需同一 ExtendedInfo 中的 Base.1.16.InvalidURI 與精確訊息；200仍驗證 YAML。013 必須取得／辨識必要宣告檔案，可接受政策支援的其他位置、archive與dialect；不能把任意缺證據視為PASS。
- Note 保存在結果與完整Log，與 Execution 列表是否顯示無關。最新 [report contract](../agents/report-step-output.md) 優先於早期報告表格構想。

### RF-14 / RF-01-014：規劃完成，未實作、未執行

使用者定案：RF-01-014 保留追蹤編號，合併進適當的 RF-14 .py，不另建014 .py、不重複操作DUT；舊的跨測項snapshot/offline adapter提案不是前置要求。詳見 [合併契約](../redfish-compliance/rf-01-014-evidence-contract.md)。

1. 先選定實際非同步操作，定義英文 Spec Ref.、生命週期成功條件、原值保存與還原方式。
2. 發送前保存 DUT 初始值；只記一次同次操作初始HTTP證據。
3. 014只使用初始HTTP 202的Location，保留request URI、raw Location、操作ID、時間、DUT/run來源。不可用Task body @odata.id、猜測URI或後續輪詢Location替代。
4. 三列Step為「確認初始證據／檢查Monitor URI／彙整全部操作範圍」。以原request URI解析Location；建議路徑為 /redfish/v1/TaskService/TaskMonitors/<id>，不改寫或解碼path後再冒充原證據。
5. 014 URI子結果與RF-14生命週期分開保存到log.step的JSON相容Result／log_records。URI Pass不代表生命週期Pass；其他Monitor路徑依現行014契約仍是未符合建議的Fail，不宣稱強制規範違反，也不擅自套用008/013例外。
6. 子檢查失敗不能跳過必要清理。正常／可處理例外路徑以finally還原並讀回驗證，保存原測試及還原失敗原因，清理後只呼叫一次log.finish。
7. RF-14總結果如何納入014判定須明列驗收條件。平台目前不會自動生成獨立014 Plan／報告結果列。

離線驗證待涵蓋：絕對／相對Location、缺失／多值歧義、非202、僅Task URI、同次多操作混合結果、URI與生命週期結果不一致、未執行步驟、子檢查失敗仍還原、只結案一次。強制停止不保證finally，須連同下述程序外復原設計處理。

### Connection：本次修正跨對話資訊落差

「只填裸BMC IP一律不能執行」是 Test Case 對話僅查後端後得到的不完整結論。本次查到：

| 入口／層級 | 現行程式行為 |
| --- | --- |
| Task Info 新七欄 Connection | task_info_drawer.js 儲存時，host無http(s) scheme就補https://；Console Port組合telnet localhost <port> |
| 後端 task_environment.configuration(require_host=True) | 仍要求完整http(s) URL，不會自行補協定 |
| Execution 舊Connection表單／直接API等入口 | 不可假定有相同正規化；仍應傳入完整URL並做一致性驗證 |
| 執行架構 | 仍有Redfish SDK前置登入，未成為通用IPMI/SSH/Redfish介面框架 |

七欄UI映射已完成，多介面transport設計尚未完成。方向為Connection提供環境資料、case宣告interface/路徑/命令與Criteria，共用連線層負責協定、port、帳密、逾時、登入及敏感資訊遮罩。對話裡 connection.ipmi(...)、redfish.get(...) 都是示意API，不是既有支援承諾。不能只改case就繞過平台前置登入。

## 二、操作流暢度改動

### 本機已完成的最終UI

- Task Name開啟右側Task Info滑出卡片，覆蓋部分清單；最新寬度560px並受viewport限制，保留清單位置。
- Test Task五頁籤：Overview / Scope / Connection / DUT Config / Note；Plan Task只有Overview / Note。
- 直接編輯，各分頁Save/Discard，切頁、換Task、關閉或離開時處理未儲存草稿；錯誤保留草稿與既有執行鎖定。
- New Task同樣採卡片。Task List的Assignee、Status是獨立欄位。移除My Task與語言切換，產品介面固定英文；Schedule/My Schedule仍在。
- Overview／Connection一列一組「標籤：欄位」。列間距10→7.5px、input上下padding6→4.5px；最新560px卡片取代早期790px及再次把欄位減半的解讀。移除Overview底部說明；iDesign Request ID、iDesign Link提升為直接欄位。
- 既有Task點日期或Status立即開Task List共用對話框，必填Note與變更在同一視窗完成；取消不修改。任何強制Note操作走對話框。新建Task初始日期仍按原建立流程。
- Task Info顯示文字History改Note，既存資料／API key不用全面改名。Note records由新到舊且不收折；FW Package Component/Version用欄內提示。
- Scope最終採Plan資料夾樹狀表格，移除Folder欄，支援空／巢狀資料夾、展開收折及整組勾選；收折不改選取／dirty狀態。這取代早期單純平面表格的設計。
- Delete Task須在對話框填刪除原因寫Note，設Deleted並由一般列表隱藏，保留Task/scope/results/logs；目前無Status=Deleted篩選UI。
- DUT Config仍待欄位定義，不能填入臆測需求。

細節與歷史驗證：[drawer](2026-11-10-task-info-drawer.md)、[create/soft delete](2026-11-10-task-create-soft-delete.md)、[compact/scope](2026-11-11-task-info-compact-scope.md)。

### 已確認但尚未修正：Plan刪除與證據生命週期

本次再次閱讀app.py delete_plan及models.py確認仍為session.delete(plan)與CASCADE。先前隔離重現為2個Task、1筆結果在刪Plan後皆歸零。Task的Deleted軟刪除不會保護它免於Plan連帶刪除。

| Plan/Task操作 | 現況 |
| --- | --- |
| Plan新增case | 不自動加入既有Task，需Scope選入，初始未執行 |
| 改case .py / Parameters / Preset | 舊結果Log保留、標需重測；下次用新內容 |
| 移動case/資料夾且ID不變 | 結果保留，位置跟隨現行Plan |
| 刪case/含case的資料夾 | 移除相關Task membership及其結果／Log |
| 刪Plan | 連帶實際刪除Task、Scope、結果／Log，包括Deleted任務 |
| 重新執行case | 先清原有結果Log，再存本次；無逐次執行版本 |

優先建議（尚未實作／尚非新架構定案）：先阻擋仍有任何Task關聯的Plan刪除，包含Deleted；再與使用者決定已執行Task的版本／證據保存策略。不要把助理提出的snapshot方案誤記為已批准或已支援。現行domain仍是current-state model。

### Connection路徑需求與其他未完成項目

- 七欄：Console Server IP/User/Password/Console Port，以及BMC IP/User/Password。其餘既有SSH port、TLS、DUT OS設定應保留；Console Port留空保留custom console command。
- Local指「由DUT OS連至BMC」；其他來源為Remote。KCS、USB Serial、USB LAN與Shared NCSI可由DUT OS執行。Console Server先SSH，再Telnet進DUT OS；每段SSH各有帳密，Console已在shell不重送登入，出現prompt才登入。
- DUT可有1/2/4個對外LAN加USB虛擬LAN，USB LAN IP不一定等於BMC LAN IP；不能從七欄推算所有介面、DUT OS登入或debug帳密。
- Remote IPMI/Redfish可由BMCAgent或Console Server發起；選Console Server時請求必須真正由該處發送且保留原始HTTP證據。Node Explorer路徑 /nodeexp；SOL與debug路徑仍屬需求圖，非本輪完整實作。
- 「基本七欄＋需要時補資料」、共用transport、登入辨識與路徑驗證仍待整體設計及真機驗證。四頁Connection示意圖已被七欄簡化設計取代。
- Schedule的Assignee/Status雙點編輯：查核確認未接上，僅時間軸改期；只診斷，未修正。
- Plan Task進度：僅評估工作清單／加權里程碑／人工填報，未定案亦未開發；不可把日期經過比例當實際完成率。
- 桌面啟動器已在本機建立，預設Chrome。Yes允許LAN、No預設本機、Cancel取消；切換須確認重啟，active Task阻擋。腳本位於外層Start-BMC.cmd、bmca-runtime/launch.ps1、launcher-firewall.ps1、start.ps1；屬本機工具，跨電腦連線未實測，本次未發布這些腳本。

## 三、調整Execution工作區

### 最終操作與版面

- 全寬列表，上方Task頁籤與固定工具列；舊右側工作區、重複Task標題／統計／說明與Test Plans連結移除。
- 工具列含自動化分類filter、全選／清除、Run/Stop、Scope、Connection；圖示保留tooltip/accessible name。
- 列上Status → Run/Stop → Log → Parameters；Run/Stop各合一，實心三角／正方形；圖示按鈕34×34px、圖示18×18px。Status固定80px、粗體置中。
- 全自動case隱藏Parameters；執行期間勾選及參數操作鎖定；Scope/Connection/Annotation/Log使用對話框。
- 列表無頂端欄名、無Note欄，六欄契約；有Note的case也只顯示狀態，不顯示Note內容。曾誤加回Note後已移除，result_note.test.cjs是保護此決策的回歸。
- 測項列上下padding由7px減半為3.5px，移除列分隔線。
- 同Task重繪保留列表捲動位置，關對話框焦點回原按鈕但不捲頁；Annotation重現由1270→0px，修正後維持1270px。
- 重跑不再詢問覆蓋確認；本次不更改最新結果覆寫模型。
- Plan只捲列表、固定標題／頁籤／工具列，下緣10px取代舊24px。舊Scope對話框18px外距、按鈕到列表12px；Task Info Scope另外依新樹狀卡片。
- Repository可一次匯入多個.py，各檔獨立成功／失敗顯示，單檔失敗不阻止其他檔。

### Log卡死已修正

事故：Log開啟時RF-01-009約460萬字元／75,483行，逐筆完整DOM重畫造成RESULT_CODE_HUNG。歷史當下Task完成9/11、010/011待跑且無worker；這是事故快照，不是今日Task狀態。browser佇列排程會因renderer卡死無法排下一項。

修正：100ms合併更新、畫面最多最後65,536字元並顯示提示；input事件／結束立即flush。保存與Export維持完整Log，包括執行中匯出的當下全文。摘要API不載完整Log，大欄位延後讀取，點Log才抓該case全文；既有active/idle/hidden輪詢節奏2/15/30秒不等於新IDLE計時器。歷史重播約3.9秒、合成回歸最大間隔約66ms，非本次重跑。見 [Log hang](2026-10-30-execution-log-hang.md)、[summary performance](2026-10-30-workspace-summary-performance.md)。

### Running/IDLE及立即停止已完成；DUT復原未完成

- 新worker活動後3秒內Running，之後IDLE: Ns，每秒更新；心跳與summary refresh不重設，無新增輪詢。IDLE只是沒有回報，不代表死鎖；百分比進度條提案已被簡化方案取代。
- case用獨立程序，Windows Job／POSIX process group管理本機子程序；停止時保存已收到證據。
- Row Stop：中止本case及本機helper，結果NR、Log記Stopped，續下一case。Toolbar Stop：中止當前並取消餘下佇列。
- 強制kill不保證case finally；DUT已接受的操作可能持續。DUT自動復原、復原後才允許續跑的gate都尚未實作，目前row stop仍直接依規則續下一項。
- 待設計程序外復原：寫入前持久化DUT身分／原值／預計新值；停止後讀回；仍原值免還原，符合本次寫入才還原，其他值交人工避免覆蓋他人修改；不能回復的FW更新／清除等暫停等人工。這是建議，非已交付功能。

詳見 [idle/stop](2026-11-03-execution-idle-stop.md)、[controls](2026-10-30-execution-controls.md)。

## 驗證證據與限制

以下是原對話／狀態文件的歷史結果，本次沒有重跑產品測試：

| 範圍 | 已記錄驗證 | 限制 |
| --- | --- | --- |
| RF來源 | 008最新11項、013最新15項離線驗證；其餘見各implementation文件 | 非整套compliance/真機完成證明 |
| Task Info drawer | 36項後端＋隔離瀏覽器＋正式唯讀檢查 | 七欄真機連線未驗證 |
| New Task / Deleted | 78任務＋13報告=91項；隔離/唯讀驗證 | Plan刪除CASCADE未解 |
| compact/Scope | 比例、收折/勾選/save、必填Note/取消/儲存、560px檢查 | 非新增DUT Config功能 |
| immediate stop | 24項targeted＋後續5項process、60秒sleep/helper中止/input/佇列驗證；controls及large log通過 | broader舊PDF current-fw斷言失敗尚無後續全綠證明 |
| earlier controls/Note | controls曾有2項舊後端斷言；Note廣測曾有2項summary/full-evidence契約舊斷言及download受限 | 有些後續已逐項更新，不宣稱整套全綠；詳原紀錄 |

接手可用 execution_controls.test.cjs、execution_log_performance.test.cjs、result_note.test.cjs、test_case_stop.py、test_task_management.py、test_task_environment.py 等適用測試；隔離workspace/main/temp，禁止對正式DB做破壞性測試。外層bmca-runtime/verification有歷史腳本與備份，不是遠端必備依賴。

本次文件驗證：讀完全部55回合；核對關鍵源碼、13份RF來源一致、發布Markdown連結與Git diff、確認提交只含文件。沒有把未解決項目標成完成。

## 接手順序與子代理人分工

以下是建議優先順序，並不代表已自動開始實作：

1. 先確定本機／遠端／正式服務現況與未提交差異，保留179筆既有項目；不能從本次文件push推論產品已全數發布。
2. 優先處理Plan刪除造成Task證據遺失，先防護再討論長期版本模型。
3. Connection所有入口正規化與多介面契約先對齊，再改case；保留現有RF原始HTTP與Log契約。
4. RF-14選操作、Criteria、還原及強制停止策略後，實作014子檢查與離線測試。
5. 再依使用者需要處理Deleted篩選、DUT Config、Schedule編輯、Plan Task進度，以及舊PDF斷言／產品來源發布。

使用者打算改採單一主對話＋子代理人。本次只建立可接手紀錄，未啟動子代理人。後續主代理人保存需求、整合與發布責任；可拆分：
- 測項代理人：RF來源、execution-policy、014驗收；不改Task UI。
- Task代理人：drawer/task management、Plan刪除證據保護。
- Execution代理人：case_process/stop、Log效能、Execution UI及復原契約。

共用app.py、models.py、workbench.js及CONTEXT需事先指定唯一修改者；子代理人回報已完成／待驗證／未完成、檔案、測試與資料影響，主代理人整合回本文件及next_plan。只在明確授權範圍操作正式服務或DUT。

接續提示：

> 先讀HANDOFF.md及docs/status/2026-11-11-consolidated-handoff.md，再讀AGENTS.md、CONTEXT.md與適用repository skill。這次三對話已合併為單一交接；先核對本機未提交工作與遠端差異，依本次指定需求分配子代理人。保留Execution無Note欄、七欄Connection入口差異、Task軟刪除但Plan仍CASCADE、強制停止尚無DUT自動復原，以及RF-01-014合併RF-14未實作等狀態。
