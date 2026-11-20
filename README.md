# 繁體中文版客戶端製作專案

本儲存庫用於整理 Ragnarok Online 客戶端繁體中文化、工具設定、登入器整合、測試結果與交付文件。

## 來源

- WARP 工具專案：[zVictorHG/WARP2026-Project](https://github.com/zVictorHG/WARP2026-Project)
- 客戶端 EXE：使用者已提供，已完成 PE32 靜態檢查及部分 WARP 簽章相容性掃描；二進位檔未公開提交、未修改。
- WARP Session：已收到舊式登入及 SSO 兩種設定並完成差異比對。
- 登入器：使用者後續提供，收到後再進行相容性分析與整合。
- 完整客戶端資料夾／GRF／DLL：仍待提供。

## 工作原則

1. 不直接覆蓋原始客戶端，不破壞既有功能。
2. 先備份並建立檔案清單、雜湊與版本基準，再逐項修改。
3. 繁體中文使用正體中文（台灣用語）；保留程式識別字、封包欄位、路徑、資源 ID 與必要格式。
4. 每個階段記錄修改內容、風險、驗證方式及結果。
5. 未經實際執行測試，不宣稱客戶端或登入器已可正常使用。
6. 所有可交付成果、文件及測試紀錄集中提交於本儲存庫。

## 目前狀態

- [x] 建立專案成果儲存庫與工作分支
- [x] 初步盤點 WARP 原始碼及補丁定義
- [x] 收到客戶端 EXE 並記錄 PE32 架構及 SHA-256
- [x] 收到兩份 WARP Session 並確認登入模式差異
- [x] 完成選定 WARP 補丁簽章的唯讀掃描
- [x] 建立 CP950 繁體中文 8 項候選映射並驗證容量與格式參數
- [x] 確認 CustomCodePage 的 EXE 靜態前置簽章符合 WARP 腳本預期
- [x] 建立可重跑的唯讀簽章檢查工具
- [ ] 取得完整客戶端資料夾、GRF 與相依 DLL
- [ ] 取得登入器並確認啟動流程
- [ ] 由 WARP 讀取 Exe.BuildDate，確認 CustomCodePage 的版本條件
- [ ] 確認實際字型、中文字形與完整客戶端資源
- [ ] 建立繁體中文翻譯檔及術語表
- [ ] 在 Windows 執行 WARP 補丁並產生候選 EXE
- [ ] 實際啟動、顯示、登入及相容性測試

## 文件與工具

- [專案規劃與進度](docs/專案規劃與進度.md)
- [WARP 來源盤點](docs/來源盤點.md)
- [使用者已提供檔案分析](docs/已提供檔案分析.md)
- [WARP 靜態補丁相容性檢查](docs/靜態補丁相容性檢查.md)
- [繁體中文硬編碼字串翻譯初稿](docs/繁體中文硬編碼字串初稿.md)
- [CP950 碼頁與字型相容性](docs/繁體中文CP950與字型相容性.md)
- [CP950 翻譯映射](localization/Translations_zhTW.yml)
- [CP950 翻譯唯讀驗證工具](tools/validate_zhTW_translations.py)
- [CP950 翻譯驗證報告](reports/zhTW_translation_validation_2026-11-20.json)
- [唯讀簽章檢查工具](tools/verify_client_signatures.py)
- [靜態掃描 JSON 結果](reports/client_static_scan_2026-11-20.json)

## 工作分支

所有開發先在 `work/traditional-chinese-client` 工作分支進行；測試未完成前不合併至 `main`。
