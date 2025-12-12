import os
import requests
import sqlite3
import re
from datetime import datetime
import time

BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
CHAT_ID = os.getenv("TG_CHAT_ID", "")

def send_tg(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                     json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except: pass

# Ключевые слова для мониторинга
KEYWORDS = {
    "GMKN": [
        "норникель китай", "nornickel china", "xiamen",
        "china copper", "медный завод", "фанчэнган",
        "потанин пекин", "норникель переговоры"
    ],
    "SBER": [
        "сбербанк китай", "сбер цифровой рубль",
        "сбербанк ключевая ставка", "набиуллина"
    ],
    "GAZP": [
        "газпром китай", "сила сибири", "газпром контракт",
        "газпром переговоры"
    ],
    "LKOH": [
        "лукойл индия", "лукойл китай", "лукойл нпз"
    ]
}

# RSS источники
RSS_FEEDS = [
    "https://www.interfax.ru/rss.asp",
    "https://tass.ru/rss/v2.xml",
    "https://ria.ru/export/rss2/archive/index.xml",
]

def check_nornickel_calendar():
    """Проверяем корпоративный календарь"""
    try:
        url = "https://nornickel.ru/investors/calendar/"
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        # Ищем упоминания событий
        events = re.findall(r'(d{1,2}s+w+s+d{4}).*?(конференц|встреч|презентац|отчёт)',
                           r.text, re.IGNORECASE)
        return events[:5]
    except:
        return []

def check_e_disclosure():
    """Проверяем раскрытие информации"""
    try:
        # Норникель ИНН
        url = "https://www.e-disclosure.ru/portal/company.aspx?id=564"
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        # Последние существенные факты
        facts = re.findall(r'(d{2}.d{2}.d{4}).*?существенн', r.text, re.IGNORECASE)
        return facts[:5]
    except:
        return []

def check_lme_prices():
    """Проверяем цены на металлы"""
    metals = {}
    try:
        # Можно парсить investing.com или другие источники
        pass
    except:
        pass
    return metals

def monitor_news():
    """Основной цикл мониторинга"""
    print("News Monitor started")
    send_tg("📰 News Monitor STARTED\n\nМониторинг:\n- Норникель-Китай\n- Корпоративные события\n- OI сигналы")

    last_check = {}

    while True:
        try:
            alerts = []

            # Проверяем OI (главный сигнал)
            conn = sqlite3.connect("history.db")
            for ticker in ["GMKN", "SBER", "GAZP"]:
                oi_rows = conn.execute("""
                    SELECT date, oi FROM futures_oi
                    WHERE ticker = ? ORDER BY date DESC LIMIT 12
                """, (ticker,)).fetchall()

                if len(oi_rows) >= 12 and oi_rows[10][1]:
                    oi_ch = (oi_rows[0][1] / oi_rows[10][1] - 1) * 100

                    # Проверяем месяц (не экспирация)
                    month = datetime.now().month
                    if month not in [3, 6, 9, 12]:
                        if oi_ch > 50:
                            key = f"{ticker}_OI_{datetime.now().date()}"
                            if key not in last_check:
                                alerts.append(f"🐋 <b>{ticker}</b> OI +{oi_ch:.0f}%\nВозможное накопление!")
                                last_check[key] = True
            conn.close()

            # Отправляем алерты
            for alert in alerts:
                send_tg(alert)
                print(f"{datetime.now():%H:%M} {alert}")

            time.sleep(1800)  # 30 минут

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(300)

if __name__ == "__main__":
    monitor_news()