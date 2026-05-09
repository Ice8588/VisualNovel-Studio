"""task.md #11：立繪匯入時自動標準化。

把不同尺寸的角色圖統一成相同畫布（GALGAME 慣例 3:4，腰部以上構圖）。
匯入時呼叫，不影響使用者原檔。
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

# 對齊預覽畫面 1080×1440（3:4 直幅）
TARGET_WIDTH = 1080
TARGET_HEIGHT = 1440


def normalize_sprite(src: Path, dst: Path) -> None:
    """把 src 圖片標準化（透明背景的 PNG 為佳）後存到 dst。

    流程：
    1. 開檔轉 RGBA。
    2. 用 getbbox 裁掉透明 padding，取得實際內容 bbox。
    3. 等比縮放，使內容高度 = TARGET_HEIGHT * 0.95（留邊）。
    4. 新建 TARGET_WIDTH × TARGET_HEIGHT 透明畫布。
    5. 內容水平置中、底部留 2.5% 邊（腰部以上構圖：人物頂部離畫布頂約 2.5%）。
    """
    img = Image.open(src).convert("RGBA")
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    target_h = int(TARGET_HEIGHT * 0.95)
    if img.height <= 0:
        # 防呆：空圖直接輸出空白畫布
        Image.new("RGBA", (TARGET_WIDTH, TARGET_HEIGHT), (0, 0, 0, 0)).save(dst, "PNG")
        return

    scale = target_h / img.height
    new_w = max(1, int(img.width * scale))
    new_h = target_h
    img = img.resize((new_w, new_h), Image.LANCZOS)

    canvas = Image.new("RGBA", (TARGET_WIDTH, TARGET_HEIGHT), (0, 0, 0, 0))
    x = (TARGET_WIDTH - new_w) // 2
    y = TARGET_HEIGHT - new_h - int(TARGET_HEIGHT * 0.025)
    # 若內容寬度超過畫布，水平裁切（保留中央）
    if new_w > TARGET_WIDTH:
        crop_left = (new_w - TARGET_WIDTH) // 2
        img = img.crop((crop_left, 0, crop_left + TARGET_WIDTH, new_h))
        x = 0
    canvas.paste(img, (x, y), img)
    canvas.save(dst, "PNG")
