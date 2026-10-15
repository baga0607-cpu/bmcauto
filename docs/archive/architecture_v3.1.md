# Redfish Interactive Playbook - 系統架構與狀態流程圖

本文件展示了 Redfish 測試框架（v3.0+）的專案架構，並特別標示了**檔案之間的依賴關係**、**使用者需要自訂的區塊**，以及最新的**有狀態執行流程 (Stateful Execution Flow)**。

---

## 1. 專案架構與檔案關聯圖

此圖表展示了專案中的檔案層級，並透過顏色區分了「核心系統」與「使用者自訂區域」。

> [!TIP]
> **顏色說明：**
> - 🟡 **黃色區塊 (User Customization)**：使用者日常測試需要頻繁修改、新增參數或建立新檔案的地方。
> - 🔵 **藍色區塊 (Core Engine)**：框架底層引擎，除非要修改框架核心邏輯，否則**不需更動**。
> - ⚪ **灰色區塊 (Outputs)**：系統自動產生的日誌。

```mermaid
graph TD
    classDef core fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000;
    classDef user fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#000;
    classDef log fill:#f5f5f5,stroke:#9e9e9e,stroke-width:2px,color:#000;

    Root["v3.0/ (專案根目錄)"]

    subgraph "核心程式區 (main_program/)"
        direction TB
        
        subgraph "1. 測試劇本與設定 (日常操作區)"
            Scen["📜 scenarios.yaml<br>劇本清單：定義有哪些測試可選<br>及要呼叫哪個 TestCase"]:::user
            Config["⚙️ config.yaml<br>BMC IP、帳號、密碼"]:::user
        end

        subgraph "2. 測試案例庫 (擴充開發區)"
            TC["📁 testcase_database/"]:::user
            
            subgraph "特定的測試案例 (例如：LED控制)"
                Controller["📄 __testcase__.py<br>控制器：負責排列該案例的<br>原子步驟與預設參數"]:::user
                Step1["📄 step_lit.py<br>原子步驟：發送 API 控制 LED 亮起"]:::user
                Step2["📄 common/human_check.py<br>共用模組：暫停並等待人工確認"]:::user
                
                Controller -->|載入與傳遞參數| Step1
                Controller -->|載入| Step2
            end
        end

        subgraph "3. 核心驅動引擎 (系統底層)"
            Main["📄 main.py<br>主程式：生成選單、動態載入模組、<br>維護共享 Context、代理 API 請求"]:::core
        end

        subgraph "4. 輸出與觀測日誌"
            LogResult["📝 result.log<br>測試結果紀錄 (Pass/Fail)"]:::log
            LogAPI["📝 api.log<br>詳細 API 請求與回應封包追蹤"]:::log
        end

        %% 關聯線
        Scen -.->|告訴引擎要跑哪些測試| Main
        Config -.->|提供 BMC 連線資訊| Main
        Main ===>|動態解析並執行| Controller
        Main -.->|攔截並記錄| LogAPI
        Main -.->|寫入最終結果| LogResult
    end
    
    Root --> Main
    TC --> Controller
```

---

## 2. 有狀態執行流程 (Stateful Execution Flow)

本框架最大的特色在於**狀態共享 (Context Sharing)**。
在同一個 TestCase（測試劇本）中，多個獨立的原子步驟（Atomic Steps）可以透過一個共享的 `context` 字典來傳遞資訊。例如：第一個步驟取得 `ETag` 或 `Resource ID`，並交給第二個步驟去進行寫入動作。

```mermaid
sequenceDiagram
    autonumber
    actor User as 測試人員
    participant Main as main.py (主引擎)
    participant Ctx as Context (共享狀態字典 {})
    participant Step1 as Step 1 (準備階段)
    participant Step2 as Step 2 (執行階段)
    participant BMC as 目標伺服器 (BMC)

    User->>Main: 啟動 main.py 並選擇測試劇本
    Main->>Main: 登入 BMC 並建立空的 context = {}
    
    rect rgb(240, 248, 255)
        Note right of Main: 階段一：收集必要資訊 (例如：取得 ETag)
        Main->>Step1: 呼叫 execute(client, context)
        Step1->>BMC: GET /redfish/v1/Systems/1
        BMC-->>Step1: 回傳 JSON (包含 @odata.etag: "W/12345")
        Step1->>Ctx: 將資訊寫入 context["etag"] = "W/12345"
        Step1-->>Main: 步驟一執行完畢
    end

    rect rgb(255, 250, 240)
        Note right of Main: 階段二：利用共享資訊執行變更
        Main->>Step2: 呼叫 execute(client, context, preset)
        Step2->>Ctx: 讀取 context["etag"]
        Ctx-->>Step2: 獲得 "W/12345"
        Step2->>BMC: PATCH /redfish/v1/Systems/1<br/>Header: If-Match "W/12345"
        BMC-->>Step2: 回傳 204 No Content (更新成功)
        Step2-->>Main: 步驟二執行完畢
    end
    
    rect rgb(240, 255, 240)
        Note right of Main: 階段三：Human-in-the-loop 人機互動
        Main->>User: CLI 暫停提示：「請確認硬體行為是否正確? (y/n)」
        User-->>Main: 輸入 y (Pass)
    end
    
    Main->>Main: 將結果寫入 result.log 並結束測試
```

## 3. 使用者自定義指南

為了讓團隊成員快速上手，以下是日常使用與擴充時需要操作的檔案：

### 🛠️ 日常測試執行
1. **`config.yaml`**: 填入當下要測試的 BMC IP 與帳號密碼。
2. **`scenarios.yaml`**: 決定今天要跑哪些測試。可以直接寫 TestCase 名稱，或是用 `- testcase_database.xxx` 陣列來混搭不同步驟。

### 🧩 新增測試功能 (擴充)
當你需要撰寫新的測試案例時，流程如下：
1. **建立原子步驟 (`step_xxx.py`)**: 撰寫單一的 Redfish API 呼叫邏輯。記得在 `execute(client, context, preset=None)` 中利用 `context` 傳遞狀態。
2. **編輯控制器 (`__testcase__.py`)**: 在 `testcase_database/你的類別/` 內，定義 `STEPS = [...]` 陣列，把剛剛寫好的原子步驟排好順序，也可以透過 `(路徑, 參數)` 傳入 Preset 值。
3. **註冊到選單**: 將這個 TestCase 加進 `scenarios.yaml`。
