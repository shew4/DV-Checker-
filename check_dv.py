"""Следит за страницами лотереи Green Card (DV) и шлёт уведомление в Telegram при изменениях."""
import hashlib
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import date

URLS = [
    "https://dvprogram.state.gov/",
    "https://travel.state.gov/content/travel/en/us-visas/immigrate/diversity-visa-program-entry.html",
    "https://travel.state.gov/content/travel/en/us-visas/immigrate/diversity-visa-program-entry/diversity-visa-instructions.html",
    "https://travel.state.gov/content/travel/en/News/visas-news.html",
]
# Если эти слова появились на странице, а раньше их не было - сообщение будет с пометкой "ВАЖНО"
KEYWORDS = ["DV-2027 registration", "DV-2028", "registration period", "entry period"]

STATE_FILE = "state.json"
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def send(text):
    data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": "true"}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data=data)
    urllib.request.urlopen(req, timeout=30).read()


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    html = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", errors="ignore")
    html = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def main():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            state = json.load(f)
    except FileNotFoundError:
        state = {}
    first_run = not state.get("pages")
    pages = state.setdefault("pages", {})
    alerts = []

    for url in URLS:
        try:
            text = fetch(url)
        except Exception as e:  # сайт мог временно не отвечать
            print(f"Не удалось загрузить {url}: {e}", file=sys.stderr)
            continue
        h = hashlib.sha256(text.encode()).hexdigest()
        old = pages.get(url, {})
        found = [k for k in KEYWORDS if k.lower() in text.lower()]
        if old and old.get("hash") != h:
            new_kw = [k for k in found if k not in old.get("keywords", [])]
            mark = "🚨 ВАЖНО: " if new_kw else "ℹ️ "
            extra = f"\nНовые ключевые слова: {', '.join(new_kw)}" if new_kw else ""
            alerts.append(f"{mark}Страница изменилась:\n{url}{extra}")
        pages[url] = {"hash": h, "keywords": found}

    if first_run:
        send("✅ Бот слежения за лотереей Green Card запущен. Я напишу, когда страницы изменятся.")
    for a in alerts:
        send(a)

    state["last_check"] = date.today().isoformat()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
