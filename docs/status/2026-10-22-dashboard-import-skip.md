# Dashboard 與 Project 匯入 Skip — 2026-10-22

已部署至本機 http://127.0.0.1:5000 。

- Dashboard 移除標題下方說明、各 Project 名稱下方說明及 Next action 欄位。
- 自動建立 Project：解析完 SKU 與規格後直接進入處理選擇，不再要求規格預覽確認。
- 每個 SKU 必須選擇保留為 SKU、升級為 Project 或 Skip；Skip 不匯入該欄，也不修改既有 Project。
- 有保留 SKU 才建立主要 Project；全部選擇升級或跳過時省略主要 Project。無 SKU 的文件仍可建立主要 Project。全部 Skip 時禁止建立。
- 所選名稱仍須通過整批衝突檢查，不合併或覆寫既有 Project。

## 驗證
16 項隔離匯入測試通過，包含既有 Project/Plan/Task 保持不變、只升級獨立 Project、全部 Skip 不寫入。JS 語法檢查通過。瀏覽器確認直接進入三選項畫面、全部 Skip 按鈕停用、只升級時清單只包含升級 Project；正式 Dashboard 確認三欄與文字移除。

重啟前無執行中 Task，使用 SQLite backup 備份並在副本啟動驗證。重啟後正式資料逐列一致，integrity/foreign keys 通過。
備份（私有本機）：<LOCAL_PATH>
驗證畫面：<LOCAL_PATH>
