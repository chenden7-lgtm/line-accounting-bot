import os
import sqlite3
from datetime import datetime
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
DB_PATH = os.path.join(BASE_DIR, "accounting.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS records
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  account_type TEXT,
                  amount INTEGER,
                  category TEXT,
                  description TEXT,
                  created_at TEXT)''')
    conn.commit()
    conn.close()

init_db()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, type: str = "personal"):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM records WHERE account_type = ? ORDER BY created_at DESC LIMIT 50", (type,))
    records = c.fetchall()
    c.execute("SELECT SUM(amount) FROM records WHERE account_type = ?", (type,))
    res = c.fetchone()
    total = res[0] if res and res[0] else 0
    conn.close()
    
    return templates.TemplateResponse(request, "index.html", {
        "current_type": type, 
        "records": records, 
        "total": total
    })

@app.post("/add")
async def add_record(account_type: str = Form(...), amount: int = Form(...), 
                    category: str = Form(...), description: str = Form("")):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO records (account_type, amount, category, description, created_at) VALUES (?, ?, ?, ?, ?)",
              (account_type, amount, category, description, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/?type={account_type}", status_code=303)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
