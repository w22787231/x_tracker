# X 帳號追蹤推送器

追蹤特定 X (Twitter) 帳號的新貼文，翻譯成繁體中文，自動推送到 Discord 頻道。

## 運作方式

每隔幾秒輪詢一次設定的 X 帳號 → 發現新貼文 → 翻譯成繁中 → 發到 Discord。
已推送過的貼文不會重發；推送失敗的貼文下一輪會自動重試。

## 安裝

```powershell
cd x_tracker
pip install -r requirements.txt
```

需要 Python 3.9+。

## 設定（三步）

### 1. 取得 twitterapi.io 金鑰

X 官方 API 自 2026 年起取消免費方案，本程式改用第三方 [twitterapi.io](https://twitterapi.io)（pay-per-use，$1 = 100,000 credits，追蹤 1–5 個帳號月成本約幾美分）。

1. 到 https://twitterapi.io 用 Google 登入
2. 複製 API key

### 2. 建立 Discord Webhook

1. 在你的 Discord 頻道：**編輯頻道 → 整合 → 建立 Webhook**
2. 複製 Webhook URL

### 3. 填寫設定檔

複製範本並填入你的值：

```powershell
Copy-Item .env.example .env
Copy-Item config.example.json config.json
```

編輯 `.env`：
```
TWITTERAPI_IO_KEY=你的_twitterapi_io_金鑰
DISCORD_WEBHOOK_URL=你的_discord_webhook_url
```

編輯 `config.json`：
```json
{
  "accounts": ["要追蹤的帳號1", "帳號2"],
  "poll_interval_seconds": 60,
  "translate": true,
  "target_lang": "zh-TW"
}
```
- `accounts`：X 帳號的 username（不含 @），1–5 個
- `poll_interval_seconds`：多久檢查一次（秒）
- `translate`：是否翻譯成繁中（`false` 則只推原文）

## 執行

```powershell
python tracker.py
```

程式會持續在背景執行。**首次啟動只會記錄目前最新貼文為基準、不會回推歷史貼文**（避免洗版）。之後每有新貼文就會推送。按 `Ctrl+C` 結束。

## 雲端執行（GitHub Actions，免費、電腦關機也照跑）

不想一直開著電腦的話，可以部署到 GitHub Actions：每 5 分鐘自動跑一次，完全免費。

### ⚠️ 先重建 Discord Webhook

若你的 webhook URL 曾經外流過，先到 Discord **刪除舊的、重建新的**（避免被亂發訊息）。新 URL 只放進 GitHub Secrets，不寫進任何檔案。

### 部署步驟

1. **建一個 public GitHub repo**（public 才能免費無限使用 Actions），把整個 `x_tracker` 專案推上去。
   - `config.json` 會一起上傳（只有帳號清單與間隔，**無金鑰**，可公開）
   - `.env` / `state.json` 已被 `.gitignore` 排除，不會上傳
2. repo → **Settings → Secrets and variables → Actions → New repository secret**，新增兩個：
   - `TWITTERAPI_IO_KEY`
   - `DISCORD_WEBHOOK_URL`
3. 到 **Actions** 分頁，選 `Track X accounts` → **Run workflow** 手動觸發一次，確認跑綠。
4. 之後每 5 分鐘自動執行。

### 運作說明

- 雲端跑的是「單次模式」：`python tracker.py --once`（跑一輪就結束）
- 去重狀態 `state.json` 存在 **GitHub Actions Cache**，跨次保留
- 首次執行只建基準、不洗版；之後有新貼文才推送
- cron 最小間隔 5 分鐘，GitHub 偶爾會延遲幾分鐘（非即時）

### 本機單次模式（測試用）

```powershell
python tracker.py --once
```

## 容錯設計

| 情況 | 處理 |
|------|------|
| twitterapi.io 暫時掛掉 | 本輪該帳號跳過，下輪重試 |
| 翻譯端點失敗 | 退回只推原文，不開天窗 |
| Discord 推送失敗 | 不更新進度，下輪自動重試該則 |
| 金鑰/webhook 未設定 | 啟動時報錯並中止 |

## 測試

```powershell
python -m pytest -q
```

## 檔案說明

| 檔案 | 用途 |
|------|------|
| `tracker.py` | 主程式：輪詢迴圈 |
| `twitter_api.py` | 封裝 twitterapi.io 呼叫，過濾出新貼文 |
| `translator.py` | Google 免費翻譯（失敗退回原文） |
| `discord.py` | 組裝 Discord embed 並推送 |
| `state.py` | 記錄各帳號最後已推送的貼文 ID（去重） |
| `config.json` / `.env` | 你的設定與金鑰（已被 .gitignore 排除） |
| `state.json` | 自動產生的去重狀態 |

## 未來可擴充（目前未做）

- 推送到 Telegram / Email
- 雲端 24/7 常駐
- 圖片/影片/轉推的完整還原
