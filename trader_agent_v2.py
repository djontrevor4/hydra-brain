#!/usr/bin/env python3
import os, sys, requests
from datetime import datetime

API_KEY = os.getenv("API_KEY", "")
API_URL = os.getenv("API_URL", "https://openrouter.ai/api/v1/chat/completions")
MODEL = os.getenv("MODEL", "deepseek/deepseek-chat")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.getenv("TG_CHAT_ID", "")
TICKERS = ["SBER", "GAZP", "LKOH", "SFIN", "MTLR"]

class AITrader:
    def get_signal(self, ticker):
        try:
            r = requests.post(API_URL, headers={"Authorization": "Bearer " + API_KEY},
                json={"model": MODEL, "messages": [
                    {"role": "system", "content": "MOEX analyst. Reply: BUY/SELL/HOLD confidence"},
                    {"role": "user", "content": "Analyze " + ticker}
                ], "max_tokens": 50}, timeout=30)
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return "ERROR: " + str(e)
    
    def scan(self):
        for t in TICKERS:
            print(t + ": " + self.get_signal(t))
    
    def alert(self):
        signals = [(t, self.get_signal(t)) for t in TICKERS]
        buys = [(t,s) for t,s in signals if "BUY" in s.upper()]
        now = datetime.now().strftime("%d.%m %H:%M")
        msg = "MOEX " + now + " - "
        if buys:
            msg += ", ".join([t + ":" + s[:20] for t,s in buys])
        else:
            msg += "no signals"
        requests.post("https://api.telegram.org/bot" + TG_BOT_TOKEN + "/sendMessage", json={"chat_id": TG_CHAT_ID, "text": msg})
        print("Sent: " + msg)

if __name__ == "__main__":
    t = AITrader()
    if len(sys.argv) > 1 and sys.argv[1] == "alert":
        t.alert()
    else:
        t.scan()
