"""
trader_agent_v2.py - AI Trader + Telegram alerts
"""
import sqlite3, os, json, requests
from datetime import datetime
from config import API_KEY, API_URL, MODEL

KNOW_DB = os.path.expanduser("~/findata/knowledge.db")
EP_DB = os.path.expanduser("~/findata/episodes.db")
HISTORY_DB = os.path.expanduser("~/findata/history.db")

# Telegram (из config или напрямую)
try:
    from config import TG_BOT_TOKEN, TG_CHAT_ID
except:
    TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
    TG_CHAT_ID = os.getenv("TG_CHAT_ID", "")

class AITrader:
    def __init__(self):
        self.know = sqlite3.connect(KNOW_DB)
        self.ep = sqlite3.connect(EP_DB)
    def get_oi(self, ticker):
        try:
            hist = sqlite3.connect(HISTORY_DB)
            rows = hist.execute("SELECT date, YUR, FIZ FROM futoi WHERE ticker=? ORDER BY date DESC LIMIT 5", (ticker,)).fetchall()
            hist.close()
            return rows
        except: return []
    
    def get_battle_patterns(self, ticker):
        try:
            rows = self.know.execute("SELECT trigger_asset, target_asset, win_rate, n, strategy FROM battle_patterns WHERE target_asset=?", (ticker,)).fetchall()
            return rows
        except: return []
    
    def get_regime(self):
        try:
            r = self.know.execute("SELECT regime, confidence FROM market_regimes ORDER BY rowid DESC LIMIT 1").fetchone()
            return {"regime": r[0], "conf": r[1]} if r else {"regime": "unknown"}
        except: return {"regime": "unknown"}
    
    def get_hot(self):
        try:
            return self.know.execute("SELECT ticker, source, reason FROM hot_tickers ORDER BY score DESC LIMIT 10").fetchall()
        except: return []

    
    def _llm(self, prompt, max_tokens=500):
        try:
            r = requests.post(API_URL,
                headers={"Authorization": f"Bearer {API_KEY}"},
                json={"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
                timeout=60)
            return r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            return f"ERROR: {e}"
    
    def _send_tg(self, text):
        """Отправить в Telegram"""
        if not TG_BOT_TOKEN or not TG_CHAT_ID:
            return False
        try:
            url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=10)
            return True
        except:
            return False
    
    def get_context(self, ticker):
        ctx = {"ticker": ticker}
        
        # Сигналы
        sigs = self.know.execute(
            "SELECT dt, source, price, trend_1d FROM signals WHERE ticker=? ORDER BY dt DESC LIMIT 5",
            (ticker,)).fetchall()
        ctx["signals"] = [{"dt": s[0], "trend": s[3]} for s in sigs]
        
        # Паттерны (без tickers)
        try:
            patterns = self.know.execute(
                "SELECT name, win_rate FROM patterns LIMIT 5").fetchall()
            ctx["patterns"] = [{"name": p[0], "win_rate": p[1]} for p in patterns]
        except:
            ctx["patterns"] = []
        
        # Опыт
        episodes = self.ep.execute(
            "SELECT task, result, score FROM episodes WHERE task LIKE ? ORDER BY score DESC LIMIT 5",
            (f"%{ticker}%",)).fetchall()
        ctx["experience"] = [{"task": e[0], "score": e[2]} for e in episodes]
        
        # Цена
        try:
            hist = sqlite3.connect(HISTORY_DB)
            price = hist.execute(
                "SELECT close, date FROM prices WHERE ticker=? ORDER BY date DESC LIMIT 1",
                (ticker,)).fetchone()
            if price:
                ctx["price"] = price[0]
                ctx["date"] = price[1]
            hist.close()
        except: pass
        
        return ctx
    
    def decide(self, ticker):
        ctx = self.get_context(ticker)
        
        confidence = 0.5
        reason = "no data"
        
        if ctx.get("signals"):
            trend = ctx["signals"][0].get("trend", 0)
            if trend and abs(trend) > 10:
                confidence = 0.75
                reason = f"STRONG {trend:+.1f}%"
            elif trend and abs(trend) > 5:
                confidence = min(0.8, 0.5 + abs(trend)/100)
                reason = f"trend {trend:+.1f}%"
        
        if ctx.get("patterns"):
            best_wr = max((p.get("win_rate") or 0) for p in ctx["patterns"])
            if best_wr > 60:
                confidence = max(confidence, best_wr/100)
        
        if confidence > 0.6:
            action = "BUY" if ctx.get("signals") and ctx["signals"][0].get("trend", 0) > 0 else "SELL"
        elif confidence < 0.3:
            action = "AVOID"
        else:
            action = "WAIT"
        
        return {"ticker": ticker, "action": action, "confidence": round(confidence, 2), "reason": reason, "price": ctx.get("price")}
    
    def scan_opportunities(self, min_trend=5):
        rows = self.know.execute("""
            SELECT DISTINCT ticker, trend_1d FROM signals 
            WHERE trend_1d IS NOT NULL AND (trend_1d > ? OR trend_1d < ?)
            ORDER BY ABS(trend_1d) DESC LIMIT 10
        """, (min_trend, -min_trend)).fetchall()
        
        opps = []
        for ticker, trend in rows:
            opp = self.decide(ticker)
            opp["trend"] = trend
            opps.append(opp)
        return opps
    
    def alert(self, ticker=None):
        """Сканировать и отправить алерты в TG"""
        if ticker:
            opps = [self.decide(ticker)]
        else:
            opps = self.scan_opportunities()
        
        strong = [o for o in opps if o["confidence"] >= 0.6 and o["action"] in ("BUY", "SELL")]
        
        if strong:
            msg = "<b>🚨 TRADING ALERTS</b>"
            for o in strong:
                emoji = "🟢" if o["action"] == "BUY" else "🔴"
                msg += f"{emoji} <b>{o['ticker']}</b>: {o['action']}"
                msg += f"   Confidence: {o['confidence']}"
                msg += f"   Reason: {o['reason']}"
                if o.get('price'):
                    msg += f"   Price: {o['price']}"
                msg += ""
            
            self._send_tg(msg)
            return {"sent": len(strong), "alerts": strong}
        
        return {"sent": 0, "message": "no strong signals"}
    
    def learn(self, ticker, action, result):
        score = {"win": 1.0, "lose": 0.0, "breakeven": 0.5}.get(result, 0.5)
        self.ep.execute(
            "INSERT INTO episodes (ts, task, approach, result, score) VALUES (?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), f"trade:{ticker}", action, result, score))
        self.ep.commit()
        return {"learned": ticker, "score": score}

if __name__ == "__main__":
    import sys
    trader = AITrader()
    
    if len(sys.argv) < 2:
        print("AI Trader v2")
        print("  scan    - scan opportunities")
        print("  decide TICKER")
        print("  alert   - scan + send to TG")
        print("  learn TICKER ACTION RESULT")
    elif sys.argv[1] == "scan":
        for o in trader.scan_opportunities():
            print(f"{o['ticker']}: {o['action']} ({o['confidence']}) {o['reason']}")
    elif sys.argv[1] == "decide" and len(sys.argv) > 2:
        print(trader.decide(sys.argv[2]))
    elif sys.argv[1] == "alert":
        r = trader.alert(sys.argv[2] if len(sys.argv) > 2 else None)
        print(f"Alerts sent: {r['sent']}")
        if r.get('alerts'):
            for a in r['alerts']:
                print(f"  {a['ticker']}: {a['action']}")
    elif sys.argv[1] == "learn" and len(sys.argv) > 4:
        print(trader.learn(sys.argv[2], sys.argv[3], sys.argv[4]))
