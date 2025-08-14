# post_jst.py — GitHub Actions用：JSTで1回だけ投稿（v2）＋ネタ切れ防止
import os, json, random
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tweepy

# ---- 認証（環境変数から） ----
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

# ---- JST 時刻 ----
JST = timezone(timedelta(hours=9))
now = datetime.now(JST)

# ---- 重複回避用の履歴 ----
STATE_DIR = Path(".state"); STATE_DIR.mkdir(exist_ok=True)
HIST_FILE = STATE_DIR / "history.json"
history = []
if HIST_FILE.exists():
    try: history = json.loads(HIST_FILE.read_text(encoding="utf-8"))
    except Exception: history = []
COOLDOWN_N = 30
recent_texts = {h.get("text","") for h in history[-COOLDOWN_N:]}

# ---- 文面ジェネレータ ----
weekday_ja = ["月","火","水","木","金","土","日"]
wd = weekday_ja[now.weekday()]
month, day, hour = now.month, now.day, now.hour
def season_of(m): return "春" if m in (3,4,5) else ("夏" if m in (6,7,8) else ("秋" if m in (9,10,11) else "冬"))
season = season_of(month)
def expand(t): return t.format(month=month, day=day, wd=wd, season=season)

common = [
    "今日もコツコツ積み上げ！ #水澄るう",
    "無理せず一歩ずつ。継続が力💪 #水澄るう",
    "水回りも心も、すっきり整えていこ〜！ #水澄るう",
    "深呼吸して姿勢を正すところから🌱 #水澄るう",
    "焦らず丁寧に、ひと仕事ずつ。#水澄るう",
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
weekday_flavor = {
    "月": ["月曜リスタート、ゆっくりギアを上げていこう。#水澄るう"],
    "火": ["火曜は着実に仕込みの日。#水澄るう"],
    "水": ["水曜は折り返し！水分補給忘れずに。#水澄るう"],
    "木": ["木曜こそ丁寧さで差がつく。#水澄るう"],
    "金": ["花金！最後まで安全にいこう。#水澄るう"],
    "土": ["土曜はメンテ日和。#水澄るう"],
    "日": ["日曜リカバリー。休むのも大事。#水澄るう"],
}
season_flavor = {
    "春": ["春のうらら、配管も心も軽やかに。#水澄るう"],
    "夏": ["夏バテ注意！こまめに休憩。#水澄るう"],
    "秋": ["秋の乾燥、パッキン点検も忘れずに。#水澄るう"],
    "冬": ["冬は凍結注意。事前の対策が命。#水澄るう"],
}

candidates = []
if 5 <= hour <= 10:
    candidates = [expand(t) for t in morning] + weekday_flavor[wd]
elif 18 <= hour <= 23:
    candidates = [expand(t) for t in evening] + weekday_flavor[wd]
else:
    candidates = [expand(t) for t in common] + weekday_flavor[wd]

# 季節の味付けをたまに混ぜる
if random.random() < 0.4:
    candidates += season_flavor[season]

# 直近重複の除外
candidates = [c for c in candidates if c not in recent_texts]
if not candidates: candidates = [f"{expand(random.choice(common))}（vari）"]
random.shuffle(candidates)
text = candidates[0]

# ---- 投稿 ----
me = client.get_me(); print("AUTH OK as @", me.data.username)
resp = client.create_tweet(text=text)
print("POSTED id=", resp.data["id"]); print("TEXT:", text)

# ---- 履歴保存 ----
history.append({"ts": now.isoformat(), "id": resp.data["id"], "text": text})
HIST_FILE.write_text(json.dumps(history[-300:], ensure_ascii=False, indent=2), encoding="utf-8")
