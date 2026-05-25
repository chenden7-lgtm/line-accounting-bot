import os, sqlite3, json
from datetime import datetime
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 修正樣板讀取路徑
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
DB_PATH = os.path.join(BASE_DIR, "ludan_final.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS records (id INTEGER PRIMARY KEY AUTOINCREMENT, account_type TEXT, amount INTEGER, category TEXT, created_at TEXT, entry_type TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("INSERT OR IGNORE INTO settings VALUES ('names', ?)", (json.dumps({'personal':'私人', 'company':'公司', 'invest':'投資'}),))
    conn.commit()
    conn.close()

init_db()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, type: str = "summary"):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    names = json.loads(conn.execute("SELECT value FROM settings WHERE key='names'").fetchone()['value'])
    
    bal = {}
    for t in ['personal', 'company', 'invest']:
        r = conn.execute("SELECT SUM(CASE WHEN entry_type='income' THEN amount ELSE -amount END) as s FROM records WHERE account_type=?", (t,)).fetchone()
        bal[t] = r['s'] if r['s'] else 0
    total = sum(bal.values())
    
    if type == "summary":
        records = conn.execute("SELECT * FROM records ORDER BY created_at DESC LIMIT 10").fetchall()
        return templates.TemplateResponse("summary.html", {"request":request, "names":names, "totals":bal, "records":records, "grand_total":total, "current_type":type})
    elif type == "settings":
        return templates.TemplateResponse("settings.html", {"request":request, "names":names, "current_type":type})
    else:
        records = conn.execute("SELECT * FROM records WHERE account_type=? ORDER BY created_at DESC LIMIT 30", (type,)).fetchall()
        return templates.TemplateResponse("index.html", {"request":request, "names":names, "records":records, "total":bal.get(type, 0), "current_type":type})

@app.post("/add")
async def add(account_type: str = Form(...), amount: int = Form(...), category: str = Form(...), entry_type: str = Form("expense")):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO records (account_type, amount, category, created_at, entry_type) VALUES (?,?,?,?,?)", (account_type, amount, category, datetime.now().strftime("%m-%d %H:%M"), entry_type))
    conn.commit(); conn.close()
    return RedirectResponse(url=f"/?type={account_type}", status_code=303)

@app.post("/update_settings")
async def update(n1:str=Form(...), n2:str=Form(...), n3:str=Form(...)):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE settings SET value=? WHERE key='names'", (json.dumps({'personal':n1,'company':n2,'invest':n3}),))
    conn.commit(); conn.close()
    return RedirectResponse(url="/?type=settings", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
