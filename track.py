"""
物件追蹤系統 - YOLO11n + BoT-SORT
Usage: python track.py <input_dir> <output_dir>
"""

import re
import csv
import sys
import colorsys
import uuid
from pathlib import Path

import cv2
import ultralytics
from ultralytics import YOLO

MODEL_NAME = "best.pt"
# 使用自訂的設定
TRACKER_CFG = str(Path(__file__).parent / "botsort.yaml")
#TRACKER_CFG = str(Path(ultralytics.__file__).parent / "cfg" / "trackers" / "botsort.yaml")

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}


def natural_key(path: Path) -> list:
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", path.name)]


def track_color(track_id: int) -> tuple:
    hue = (track_id * 0.618033988749895) % 1.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.85, 0.95)
    return (int(b * 255), int(g * 255), int(r * 255))  # BGR for OpenCV


def draw_track(frame, x1, y1, x2, y2, track_id, cls_name, conf, color):
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    label = f"ID:{track_id} {cls_name} {conf:.2f}"
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
    cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw, y1), color, -1)
    cv2.putText(frame, label, (x1, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)


def run(input_dir: Path, output_dir: Path, model_path: str | None = None) -> None:
    frames = sorted(
        [p for p in input_dir.iterdir() if p.suffix.lower() in IMG_EXTS],
        key=natural_key,
    )
    if not frames:
        raise SystemExit(f"No images found in {input_dir}")

    frames_out = output_dir / "processed_frames"
    frames_out.mkdir(parents=True, exist_ok=True)

    model = YOLO(model_path if model_path is not None else MODEL_NAME)
    log_rows = []
    
    # 用來將 BoT-SORT 的整數 ID 映射到特定的 UUID
    track_to_uuid = {}

    for frame_idx, img_path in enumerate(frames, start=1):
        frame = cv2.imread(str(img_path))
        results = model.track(frame, tracker=TRACKER_CFG, persist=True, verbose=False, conf=0.05)

        annotated = frame.copy()
        result = results[0]

        if result.boxes is not None:
            xyxy = result.boxes.xyxy.cpu().numpy()
            confs = result.boxes.conf.cpu().numpy()
            clss = result.boxes.cls.cpu().numpy().astype(int)
            # IDs may be missing depending on tracker behavior; handle gracefully
            ids = None
            try:
                ids = result.boxes.id.cpu().numpy().astype(int)
            except Exception:
                ids = [None] * len(xyxy)

            for i, box in enumerate(xyxy):
                x1, y1, x2, y2 = map(int, box)
                conf = float(confs[i])
                cls = int(clss[i])
                tid = ids[i]
                cls_name = model.names[cls]
                
                # 將 tid 轉換為 uuid
                if tid is not None:
                    if tid not in track_to_uuid:
                        track_to_uuid[tid] = str(uuid.uuid4())
                    defect_uuid = track_to_uuid[tid]
                else:
                    # 如果沒有被追蹤到，給他一個隨機的一次性 UUID
                    defect_uuid = str(uuid.uuid4())
                
                # 為了保留顏色計算邏輯，將顏色使用整數做依據
                color_id = tid if tid is not None else (i + frame_idx * 1000)
                color = track_color(color_id)
                
                # 顯示的 ID 取 UUID 的前 8 碼避免畫面塞滿
                short_uuid = defect_uuid[:8]
                draw_track(annotated, x1, y1, x2, y2, short_uuid, cls_name, conf, color)
                log_rows.append([
                    frame_idx,
                    defect_uuid,  # 寫入完整的 UUID 到 CSV
                    x1,
                    y1,
                    x2 - x1,
                    y2 - y1,
                    f"{conf:.4f}",
                    cls_name,
                ])

        cv2.imwrite(str(frames_out / img_path.name), annotated)
        print(f"  [{frame_idx}/{len(frames)}] {img_path.name}")

    csv_path = output_dir / "tracking_log.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Frame_ID", "Track_ID", "X", "Y", "W", "H", "Confidence", "Class"])
        writer.writerows(log_rows)

    unique_ids = len({r[1] for r in log_rows})
    print(f"\nDone.")
    print(f"  Frames  -> {frames_out}")
    print(f"  Log     -> {csv_path}")
    print(f"  Result  : {unique_ids} unique Track IDs across {len(frames)} frames")


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        raise SystemExit("Usage: python track.py <input_dir> <output_dir> [model_path]")
    model_arg = sys.argv[3] if len(sys.argv) == 4 else None
    run(Path(sys.argv[1]), Path(sys.argv[2]), model_arg)