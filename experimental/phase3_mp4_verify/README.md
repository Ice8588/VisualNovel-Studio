# Phase 3 MP4 端到端驗收 fixture

## 內容
- `proj.vnsproj`：5 句對話的範例專案
- `assets/bg_room.png`：背景
- `assets/char_a.png`：紅色角色 A 立繪（左槽）
- `assets/char_b.png`：藍色角色 B 立繪（右槽）

## 預期效果

| 對話 | 內容 | 視覺要素 |
|---|---|---|
| ① | A：嗨，我們在左邊。 | A 在左 + B 在右 + rain |
| ② | B：我在右邊… | 同上 |
| ③ | A：第 3 句畫面會震動！ | 同上 + **screen_shake** + 文字 bold + shake |
| ④ | （雨繼續下、震動結束。）旁白 | A + B + rain（無震動） |
| ⑤ | B：兩個立繪、雨效… | 同上 |

## 驗收流程

```bash
# 1) 切到 Phase 3 分支
git checkout feature/phase-3-engine-mp4

# 2) 開 app
python main.py

# 3) File → Open
#    路徑：experimental/phase3_mp4_verify/proj.vnsproj

# 4) Preview 區域目視確認
#    - A 立繪（紅）在畫面左側
#    - B 立繪（藍）在畫面右側
#    - 雨點全程下落
#    - 點對話 ③ 時畫面震動

# 5) File → Export → MP4
#    輸出檔名隨意（例如 ~/phase3_verify.mp4）

# 6) 用播放器（VLC / mpv / Windows Media Player）播 MP4
#    逐項目視確認上表「視覺要素」全部出現
```

## 通過標準（用以解封 main merge）

- [ ] A 在 MP4 左半邊每一幀都出現（而非只在 A 說話時）
- [ ] B 在 MP4 右半邊每一幀都出現
- [ ] 雨效從第 1 秒到結尾都在
- [ ] 第 3 句對話那段畫面有左右震動
- [ ] 文字框無裁切、字體大小正常
- [ ] 對話順序 ①→②→③→④→⑤ 與專案一致
- [ ] 最後黑屏 / fade out 收尾正常

任一項不通過 → 回報症狀；通過 → 即可 merge phase-1 + phase-2 + phase-3 → main。

## 重新生成此 fixture

```bash
python scripts/build_phase3_mp4_fixture.py
```
