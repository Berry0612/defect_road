# 物件追蹤

這個專案使用 YOLO 與 BoT-SORT 來處理影像序列追蹤。

## 功能

- 從資料夾讀取輸入影像。
- 使用 `best.pt` 與 `botsort.yaml` 進行追蹤。
- 將標註後的影格輸出到 `output_dir/processed_frames`。
- 將偵測與追蹤資料寫入 `output_dir/tracking_log.csv`。

## 使用方式

```bash
python track.py <input_dir> <output_dir>
```

`input_dir` 內需包含影像檔，例如 `.jpg`、`.jpeg`、`.png` 或 `.bmp`。

## 需求

- Python
- `uv`
- `opencv-python`
- `pillow`
- `ultralytics`

## uv 初始化

這個資料夾已經補上 `pyproject.toml`，可先執行 `uv sync` 同步依賴，再用 `uv run python track_ui.py` 或雙擊 `launch_track_ui.bat` 啟動 UI。

## 專案檔案

- `track.py`：主要追蹤腳本。
- `track_ui.py`：視覺化 UI，左邊顯示原圖，右邊顯示追蹤後結果。
- `launch_track_ui.bat`：Windows 雙擊啟動器。
- `best.pt`：模型權重。
- `botsort.yaml`：追蹤器設定。

## UI 方式

雙擊 `launch_track_ui.bat`，它會用 `uv` 啟動 UI；選擇輸入圖像資料夾後按「開始追蹤並預覽」。
畫面會以每張圖為單位，左邊顯示原圖，右邊顯示處理後結果。

## 更新規則

如果腳本行為有變更，請同時更新這份 README。
如果 CLI、輸入、輸出、依賴或檔名有變更，請先更新這份文件，讓人可以直接對照目前行為。