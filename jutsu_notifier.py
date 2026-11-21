"""
Слежение за страницами аниме на jut-su.net + уведомление в Telegram.
Версия для GitHub Actions: токен и chat id берутся из переменных окружения (Secrets).
"""
import html
import json
import os
import re
import sys
import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")

# Страницы, за которыми следим (можно добавлять сколько угодно)
URLS = [
    "https://jut-su.net/9034-chernyj-klever-2-sezon-x1.html",
]

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jutsu_state.json")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}


def fetch_info(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    r.encoding = "utf-8"
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", r.text, flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    text = re.sub(r"\s+", " ", text)

    title_m = re.search(r"<title>(.*?)</title>", r.text, flags=re.S)
    title = html.unescape(title_m.group(1)).strip() if title_m else url
    title = re.sub(r"\s+смотреть.*$", "", title, flags=re.I)

    count_m = re.search(r"(\d+)\s+сери(?:я|и|й)\b", text)
    next_m = re.search(
        r"Следующий эпизод:\s*(\d{1,2}\s+\S+\s+\d{4}(?:,\s*\d{1,2}:\d{2})?)", text
    )
    return {
        "title": title,
        "episodes": int(count_m.group(1)) if count_m else None,
        "next": next_m.group(1) if next_m else None,
    }


def send_telegram(msg):
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg},
        timeout=15,
    )
    r.raise_for_status()


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def main():
    if os.environ.get("PING") == "1":
        send_telegram("✅ Тест: уведомления работают")
        print("Тестовое сообщение отправлено")
        return

    state = load_state()

    for url in URLS:
        try:
            info = fetch_info(url)
        except requests.RequestException as e:
            print(f"Ошибка загрузки {url}: {e}")
            continue

        print(info)
        if info["episodes"] is None:
            print("Не удалось найти число серий — возможно, сайт поменял вёрстку")
            continue

        old = state.get(url)
        if old is not None and info["episodes"] > old:
            msg = f"🎬 {info['title']}\nВышла новая серия: {info['episodes']}\n{url}"
            if info["next"]:
                msg += f"\nСледующая: {info['next']}"
            send_telegram(msg)
        state[url] = info["episodes"]

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
