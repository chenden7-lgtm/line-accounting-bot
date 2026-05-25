import os, sqlite3, json
from datetime import datetime
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI()
DB_PATH = "accounting_v2.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# 初始化資料庫
conn = get_db()
conn.execute("CREATE TABLE IF NOT EXISTS records (id INTEGER PRIMARY KEY AUTOINCREMENT, account_type TEXT, amount INTEGER, category TEXT, created_at TEXT, entry_type TEXT DEFAULT 'expense')")
conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
conn.execute("INSERT OR IGNORE INTO settings VALUES ('names', ?)", (json.dumps({'personal':'私人','company':'公司','invest':'投資'}),))
conn.commit()
conn.close()

def get_nav(current, names):
    return f"""
    <div style="position:fixed; bottom:0; left:0; right:0; background:white; border-top:1px solid #eee; display:grid; grid-template-columns:repeat(5, 1fr); padding:10px 0; text-align:center; height:70px; z-index:999;">
        <a href="/" style="text-decoration:none; color:{'#ff5722' if current=='summary' else '#ccc'};">📊<br><small>總覽</small></a>
        <a href="/?type=personal" style="text-decoration:none; color:{'#ff5722' if current=='personal' else '#ccc'};">🏠<br><small>{names.get('personal','私人')[:2]}</small></a>
        <a href="/?type=company" style="text-decoration:none; color:{'#ff5722' if current=='company' else '#ccc'};">🏢<br><small>{names.get('company','公司')[:2]}</small></a>
        <a href="/?type=invest" style="text-decoration:none; color:{'#ff5722' if current=='invest' else '#ccc'};">💰<br><small>{names.get('invest','投資')[:2]}</small></a>
        <a href="/?type=settings" style="text-decoration:none; color:{'#ff5722' if current=='settings' else '#ccc'};">⚙️<br><small>設定</small></a>
    </div>
    """

@app.get("/", response_class=HTMLResponse)
async def index(type: str = "summary"):
    conn = get_db()
    names = json.loads(conn.execute("SELECT value FROM settings WHERE key='names'").fetchone()['value'])
    
    bal = {}
    for t in ['personal', 'company', 'invest']:
        r = conn.execute("SELECT SUM(CASE WHEN entry_type='income' THEN amount ELSE -amount END) as s FROM records WHERE account_type=?", (t,)).fetchone()
        bal[t] = r['s'] if r['s'] else 0
    total = sum(bal.values())

    html = f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>滷蛋記帳</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head>
    <body style="background:#f8f9fa; padding-bottom:80px;">
    <div style="background:#121212; color:white; padding:40px 20px; text-align:center;">
        <small>{names.get(type, '資產總覽')}</small><h1 style="font-weight:bold;">$ {bal.get(type, total)}</h1>
    </div>"""

    if type == "summary":
        html += '<div class="container mt-4">'
        for t in ['personal', 'company', 'invest']:
            html += f'<div class="card p-3 mb-2"><b>{names[t]}</b>: $ {bal[t]}</div>'
        html += "</div>"
    elif type == "settings":
        html += f"""<div class="p-4"><form action="/update_settings" method="POST">
            名稱1: <input name="n1" class="form-control mb-2" value="{names['personal']}">
            名稱2: <input name="n2" class="form-control mb-2" value="{names['company']}">
            名稱3: <input name="n3" class="form-control mb-2" value="{names['invest']}">
            <button class="btn btn-dark w-100 mt-2">儲存</button></form></div>"""
    else:
        html += f"""<div class="card m-3 p-3 shadow-sm"><form action="/add" method="POST">
            <input type="hidden" name="account_type" value="{type}">
            <select name="entry_type" class="form-select mb-2"><option value="expense">支出</option><option value="income">收入</option></select>
            <input type="number" name="amount" class="form-control mb-2" placeholder="金額" required>
            <input type="text" name="category" class="form-control mb-2" placeholder="項目" required>
            <button class="btn btn-danger w-100">存入</button></form></div>"""

    html += get_nav(type, names) + "</body></html>"
    conn.close()
    return html

@app.post("/add")
async def add(account_type: str = Form(...), amount: int = Form(...), category: str = Form(...), entry_type: str = Form("expense")):
    conn = get_db()
    conn.execute("INSERT INTO records (account_type, amount, category, created_at, entry_type) VALUES (?,?,?,?,?)", (account_type, amount, category, datetime.now().strftime("%m-%d %H:%M"), entry_type))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/?type={account_type}", status_code=303)

@app.post("/update_settings")
async def update(n1:str=Form(...), n2:str=Form(...), n3:str=Form(...)):
    conn = get_db()
    conn.execute("UPDATE settings SET value=? WHERE key='names'", (json.dumps({'personal':n1,'company':n2,'invest':n3}),))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/?type=settings", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
