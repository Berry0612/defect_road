# Agent Notes

在編輯專案前請先閱讀這份文件。

## 目前行為

- 入口：`track.py`
- 輸入：一個影像資料夾
- 輸出：標註後影格到 `output_dir/processed_frames`
- 輸出：追蹤 CSV 到 `output_dir/tracking_log.csv`
- UI：`track_ui.py` 以左右對照方式顯示原圖與處理後影像
- Windows 啟動器：`launch_track_ui.bat`，透過 `uv` 啟動 `track_ui.py`
- uv 專案檔：`pyproject.toml`
- 模型權重：`best.pt`
- 追蹤器設定：`botsort.yaml`

## 編輯規則

- 變更要小而聚焦。
- 除非任務明確要求，否則保留 `track.py` CLI 不變。
- 如果你改了輸入、輸出、依賴、檔名或執行行為，請在同一次變更裡同步更新這份文件與 `README.md`。
- 如果你發現重複出現的錯誤或專案慣例，請記錄到 memory，方便後續 session 使用。

## 工作提示

在做程式修改前，只需要檢查 `track.py` 和附近設定，確認能做出局部且可驗證的修改即可。