import os
import sqlite3
import json
from datetime import datetime
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
DB_PATH = os.path.join(BASE_DIR, "accounting.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS records
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  account_type TEXT, amount INTEGER, category TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings
                 (key TEXT PRIMARY KEY, value TEXT)''')
    # 預設名稱
    c.execute("INSERT OR IGNORE INTO settings VALUES ('names', ?)", 
              (json.dumps({'personal': '私人私帳', 'company': '公司公帳', 'invest': '投資理財'}),))
    conn.commit()
    conn.close()

init_db()

def get_settings():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key='names'")
    res = c.fetchone()
    conn.close()
    return json.loads(res['value']) if res else {'personal': '私人私帳', 'company': '公司公帳', 'invest': '投資理財'}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, type: str = "summary"):
    conn = get_db()
    c = conn.cursor()
    names = get_settings()
    
    c.execute("SELECT account_type, SUM(amount) as total FROM records GROUP BY account_type")
    totals = {row['account_type']: row['total'] for row in c.fetchall()}
    grand_total = sum(totals.values())
    
    if type == "summary":
        c.execute("SELECT * FROM records ORDER BY created_at DESC LIMIT 15")
        records = c.fetchall()
        return templates.TemplateResponse(request, "summary.html", {
            "totals": totals, "grand_total": grand_total, "records": records, "names": names, "current_type": "summary"
        })
    elif type == "settings":
        return templates.TemplateResponse(request, "settings.html", {"names": names, "current_type": "settings"})
    else:
        # 獲取分類統計
        c.execute("SELECT category, SUM(amount) as s FROM records WHERE account_type = ? GROUP BY category ORDER BY s DESC", (type,))
        stats = c.fetchall()
        c.execute("SELECT * FROM records WHERE account_type = ? ORDER BY created_at DESC LIMIT 50", (type,))
        records = c.fetchall()
        return templates.TemplateResponse(request, "index.html", {
            "current_type": type, "records": records, "total": totals.get(type, 0), "names": names, "stats": stats
        })

@app.post("/add")
async def add_record(account_type: str = Form(...), amount: int = Form(...), category: str = Form(...)):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO records (account_type, amount, category, created_at) VALUES (?, ?, ?, ?)",
              (account_type, amount, category, datetime.now().strftime("%m-%d %H:%M")))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/?type={account_type}", status_code=303)

@app.post("/delete/{record_id}")
async def delete_record(record_id: int, type: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/?type={type}", status_code=303)

@app.post("/update_settings")
async def update_settings(n1: str = Form(...), n2: str = Form(...), n3: str = Form(...)):
    conn = get_db()
    c = conn.cursor()
    new_names = {'personal': n1, 'company': n2, 'invest': n3}
    c.execute("UPDATE settings SET value = ? WHERE key = 'names'", (json.dumps(new_names),))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/?type=settings", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
