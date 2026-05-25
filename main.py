import os, sqlite3, json
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
    c.execute('''CREATE TABLE IF NOT EXISTS records (id INTEGER PRIMARY KEY AUTOINCREMENT, account_type TEXT, amount INTEGER, category TEXT, created_at TEXT, entry_type TEXT DEFAULT 'expense')''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute("INSERT OR IGNORE INTO settings VALUES ('names', ?)", (json.dumps({'personal': '私人私帳', 'company': '公司公帳', 'invest': '投資理財'}),))
    try: c.execute("SELECT entry_type FROM records LIMIT 1")
    except: c.execute("ALTER TABLE records ADD COLUMN entry_type TEXT DEFAULT 'expense'")
    conn.commit()
    conn.close()

init_db()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, type: str = "summary"):
    conn = get_db()
    names_json = conn.execute("SELECT value FROM settings WHERE key='names'").fetchone()
    names = json.loads(names_json['value']) if names_json else {'personal':'私人','company':'公司','invest':'投資'}
    
    # 計算結餘
    balance_map = {}
    for t in ['personal', 'company', 'invest']:
        res = conn.execute("SELECT SUM(CASE WHEN entry_type='income' THEN amount ELSE -amount END) as bal FROM records WHERE account_type=?", (t,)).fetchone()
        balance_map[t] = res['bal'] if res['bal'] else 0
    grand_total = sum(balance_map.values())

    if type == "summary":
        records = conn.execute("SELECT * FROM records ORDER BY created_at DESC LIMIT 15").fetchall()
        return templates.TemplateResponse("summary.html", {"request": request, "totals": balance_map, "grand_total": grand_total, "records": records, "names": names, "current_type": "summary"})
    elif type == "report":
        flow = {row['entry_type']: row['s'] for row in conn.execute("SELECT entry_type, SUM(amount) as s FROM records GROUP BY entry_type").fetchall()}
        top = conn.execute("SELECT category, SUM(amount) as s FROM records WHERE entry_type='expense' GROUP BY category ORDER BY s DESC LIMIT 5").fetchall()
        return templates.TemplateResponse("report.html", {"request": request, "flow": flow, "top_expenses": top, "names": names, "current_type": "report"})
    elif type == "settings":
        return templates.TemplateResponse("settings.html", {"request": request, "names": names, "current_type": "settings"})
    else:
        records = conn.execute("SELECT * FROM records WHERE account_type=? ORDER BY created_at DESC LIMIT 50", (type,)).fetchall()
        stats = conn.execute("SELECT category, SUM(amount) as s FROM records WHERE account_type=? AND entry_type='expense' GROUP BY category ORDER BY s DESC", (type,)).fetchall()
        return templates.TemplateResponse("index.html", {"request": request, "current_type": type, "records": records, "total": balance_map.get(type, 0), "names": names, "stats": stats})

@app.post("/add")
async def add(account_type: str = Form(...), amount: int = Form(...), category: str = Form(...), entry_type: str = Form("expense")):
    conn = get_db()
    conn.execute("INSERT INTO records (account_type, amount, category, created_at, entry_type) VALUES (?, ?, ?, ?, ?)", (account_type, amount, category, datetime.now().strftime("%m-%d %H:%M"), entry_type))
    conn.commit()
    return RedirectResponse(url=f"/?type={account_type}", status_code=303)

@app.post("/delete/{rid}")
async def delete(rid: int, type: str):
    conn = get_db()
    conn.execute("DELETE FROM records WHERE id=?", (rid,))
    conn.commit()
    return RedirectResponse(url=f"/?type={type}", status_code=303)

@app.post("/update_settings")
async def update_settings(n1: str=Form(...), n2: str=Form(...), n3: str=Form(...)):
    conn = get_db()
    conn.execute("UPDATE settings SET value=? WHERE key='names'", (json.dumps({'personal':n1,'company':n2,'invest':n3}),))
    conn.commit()
    return RedirectResponse(url="/?type=settings", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
