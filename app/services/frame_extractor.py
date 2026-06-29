import os
from datetime import datetime
import cv2


def extract_frames_every_n_seconds(video_path: str, out_dir: str, every_n_seconds: float = 1.0) -> int:
    os.makedirs(out_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    if fps <= 0:
        # 有些视频拿不到 fps，兜底按 25
        fps = 25.0

    frame_interval = int(round(fps * every_n_seconds))
    if frame_interval <= 0:
        frame_interval = 1

    count = 0
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        if idx % frame_interval == 0:
            # 000001.jpg 这种方便排序
            filename = f"{count:06d}.jpg"
            cv2.imwrite(os.path.join(out_dir, filename), frame)
            count += 1

        idx += 1

    cap.release()
    return count