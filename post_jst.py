# post_jst.py — JSTで1回投稿（v2）＋祝日＆曜日テーマ強化版（直近重複回避つき）
import os, json, random
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tweepy
import jpholiday  # ← 祝日判定

# ==== 認証（環境変数から） ====
API_KEY        = os.environ["X_API_KEY"]
API_SECRET     = os.environ["X_API_SECRET"]
ACCESS_TOKEN   = os.environ["X_ACCESS_TOKEN"]
ACCESS_SECRET  = os.environ["X_ACCESS_SECRET"]
BEARER_TOKEN   = os.environ.get("X_BEARER_TOKEN")  # 任意

client = tweepy.Client(
    bearer_token=BEARER_TOKEN,
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_SECRET,
    wait_on_rate_limit=True,
)

# ==== JST ====
JST = timezone(timedelta(hours=9))
now = datetime.now(JST)
month, day, hour = now.month, now.day, now.hour
wd_idx = now.weekday()            # 0=月 … 6=日
weekday_ja = ["月","火","水","木","金","土","日"]
wd = weekday_ja[wd_idx]

# 祝日
holiday_name = jpholiday.is_holiday_name(now.date())  # 祝日名 or None
is_holiday = holiday_name is not None

# ==== 履歴（直近重複回避） ====
STATE_DIR = Path(".state"); STATE_DIR.mkdir(exist_ok=True)
HIST_FILE = STATE_DIR / "history.json"
try:
    history = json.loads(HIST_FILE.read_text(encoding="utf-8"))
except Exception:
    history = []
COOLDOWN_N = 30
recent_texts = {h.get("text","") for h in history[-COOLDOWN_N:]}

# ==== ユーティリティ ====
def season_of(m):
    if m in (3,4,5):  return "春"
    if m in (6,7,8):  return "夏"
    if m in (9,10,11):return "秋"
    return "冬"

def expand(t):
    return t.format(month=month, day=day, wd=wd, season=season_of(month), holiday=holiday_name or "")

# ==== 文面プール ====
common = [
    "今日もコツコツ積み上げ！ #水澄るう",
    "無理せず一歩ずつ。継続が力💪 #水澄るう",
    "深呼吸して姿勢を正すところから🌱 #水澄るう",
    "焦らず丁寧に、ひと仕事ずつ。#水澄るう",
    "水回りも心も、すっきり整えていこ〜！ #水澄るう",
]
morning = [
    "おはようございます☀ {season}の朝、まずは給水してスタート！ #水澄るう",
    "朝活スタート！安全第一・笑顔第一でいきましょう。#水澄るう",
    "{month}月{day}日({wd})、いい一日にしよう！ #水澄るう",
    "配管チェックOK？体調チェックOK？いってきます！ #水澄るう",
]
evening = [
    "お疲れさまでした🌙 今日はしっかり休んで明日にバトン。#水澄るう",
    "今日も無事完走！湯船でリセットしてね🛁 #水澄るう",
    "片付けまでが仕事、心までスッキリと。#水澄るう",
    "{month}月{day}日({wd}) 締めの一言：よく頑張った！ #水澄るう",
]

# 曜日テーマ（強化版）
weekday_flavor = {
    "月": ["月曜リスタート。無理せずウォームアップ。#水澄るう"],
    "火": ["火曜は仕込みの日、未来の自分が喜ぶ段取りを。#水澄るう"],
    "水": ["水曜は折り返し！水分補給＆姿勢リセット。#水澄るう"],
    "木": ["木曜は丁寧さで差がつく。安全・品質・スピード。#水澄るう"],
    "金": ["花金！最後まで安全第一でいこう。#水澄るう"],
    "土": ["土曜はメンテ日和。見えないところを整える日。#水澄るう"],
    "日": ["日曜リカバリー。休むのも仕事のうち。#水澄るう"],
}

# 祝日用（名前入り）
holiday_lines = [
    "今日は{holiday}🎌 ゆっくり英気を養っていこう。#水澄るう",
    "{holiday}ですね🎌 安全運転＆無理はしないでね。#水澄るう",
    "{holiday}に感謝しつつ、心と体をいたわる日。#水澄るう",
]

# 季節味付け
season_flavor = {
    "春": ["春のうらら、配管も心も軽やかに。#水澄るう"],
    "夏": ["夏バテ注意！こまめに休憩・給水を。#水澄るう"],
    "秋": ["秋の乾燥、パッキン点検も忘れずに。#水澄るう"],
    "冬": ["冬は凍結注意。事前の対策が命。#水澄るう"],
}

# ==== 候補生成 ====
candidates = []

# 時間帯ごとのベース
if 5 <= hour <= 10:
    candidates += [expand(t) for t in morning]
elif 18 <= hour <= 23:
    candidates += [expand(t) for t in evening]
else:
    candidates += [expand(t) for t in common]

# 曜日フレーバー
candidates += weekday_flavor[wd]

# 祝日が最優先
if is_holiday:
    candidates = [expand(t) for t in holiday_lines] + candidates

# 季節をたまに混ぜる
sf = season_flavor[season_of(month)]
if random.random() < 0.5:
    candidates += sf

# 直近重複の除外
candidates = [c for c in dict.fromkeys(candidates) if c not in recent_texts]

# フォールバック（全て重複した場合）
if not candidates:
    candidates = [expand(random.choice(common)) + "（vari）"]

# ランダムで最終選定
random.shuffle(candidates)
text = candidates[0]

# ==== 投稿 ====
me = client.get_me()
print("AUTH OK as @", me.data.username)
resp = client.create_tweet(text=text)
print("POSTED id=", resp.data["id"])
print("TEXT:", text)

# ==== 履歴保存 ====
history.append({"ts": now.isoformat(), "id": resp.data["id"], "text": text})
HIST_FILE.write_text(json.dumps(history[-300:], ensure_ascii=False, indent=2), encoding="utf-8")

