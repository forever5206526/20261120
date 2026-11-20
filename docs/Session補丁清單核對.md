# WARP Session 補丁清單核對

核對日期：2026-11-20  
WARP 來源：`zVictorHG/WARP2026-Project`，`main`，commit `57a3e7ba7af8c848ac765fc3b40be376425198fd`  
來源 Session：`rAthena_Session.yml`、`rAthena_Session_SSOMode.yml`

## 1. 核對結果

- 兩份 Session 均可由 PyYAML `safe_load` 解析。
- 每份 Session 都列出 54 個補丁。
- 兩份清單共有 53 個相同補丁；唯一差異為 `UseOldLogin` 與 `UseSSOLogin`。
- WARP 現行 9 個 `Patches/*.yml` 分類檔共定義 294 個 patch key。
- Session 的 53 個名稱可在現行分類檔找到完全相同的 key。
- 唯一未出現在現行分類檔及 `Tables/Patch.yml` 的名稱是 `RestoreBattlegroundUI`。

## 2. RestoreBattlegroundUI 特別狀態

在 WARP 現行 `main`：
- `Scripts/Patches/RestoreBattlegroundUI.qjs` 檔案確實存在。
- 該腳本包含 2026 branch 的 Battleground button ID `0x178` 特別處理。
- 但 `Patches/Character.yml`、`Client.yml`、`Data.yml`、`Env.yml`、`Network.yml`、`Sound.yml`、`Special.yml`、`UI.yml`、`Window.yml` 都沒有該 patch 的 UI 分類項目。
- `Tables/Patch.yml` 也沒有該名稱。

**判讀：** 腳本存在不等於它已註冊在目前 WARP 的 patch 選單。Session 中仍列出該項，可能是舊版／自訂 Session 遺留項目。不能只憑腳本檔存在，就假定目前 WARP 會正常載入並執行它。需在 WARP TestBench 載入 Session 時確認是否識別、是否執行及是否報錯。

## 3. 與繁體中文化相關的 Session 設定

| 項目 | 原 Session 狀態 | 繁體中文測試處理 |
|---|---|---|
| `TranslateClient` | 已啟用，指向英文映射檔 | 保留原檔，另用 `localization/Translations_zhTW.yml` |
| `AlwaysAscii` | 已啟用 | CP950 測試先不沿用；先確認字型及多位元組字碼頁行為 |
| `UseOldLogin`／`UseSSOLogin` | 各 Session 分別啟用其一 | 兩者互斥；等待登入器與伺服器協定確認 |
| `NoLoginOTP` | 兩份都啟用 | 先不視為中文化必要條件；待登入器驗證流程確認 |
| `CustomCodePage` | 原 Session 未啟用 | 新版 WARP 有此補丁；目標 EXE 靜態簽章符合，候選值 950，BuildDate gate 待 WARP 讀取 |
| `CustomFontCharset` | 原 Session 未啟用 | 候選選項為 `CHINESEBIG5 (136)`，需在 WARP 中選擇並實機測試 |
| `FixFontsCharset`／`EnableEotFonts` | 原 Session 未啟用 | 等完整客戶端字型資源盤點後決定是否需要 |

## 4. 後續處理

1. 不修改或覆蓋使用者原始兩份 Session。
2. 建立獨立的繁體中文測試 Session；先只加入語系測試必要項目，不混入未確認的登入／DLL 功能。
3. WARP 實際載入時，特別記錄 `RestoreBattlegroundUI` 是否被識別。
4. 測試通過後才整理正式登入模式及其他原有功能。

本文件是靜態清單核對，不等於 WARP 實際執行測試。
