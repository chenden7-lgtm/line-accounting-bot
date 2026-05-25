import os, sqlite3, json
from datetime import datetime
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI()
DB_PATH = "ludan_v84.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# 初始化
conn = get_db()
conn.execute("CREATE TABLE IF NOT EXISTS records (id INTEGER PRIMARY KEY AUTOINCREMENT, account_type TEXT, amount INTEGER, category TEXT, created_at TEXT, entry_type TEXT)")
conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
conn.execute("INSERT OR IGNORE INTO settings VALUES ('names', ?)", (json.dumps({'personal':'私人', 'company':'公司', 'invest':'投資'}),))
conn.commit()
conn.close()

def build_html(type, names, bal, records=[]):
    total = sum(bal.values())
    curr_bal = bal.get(type, total)
    curr_name = names.get(type, "全域統整")
    
    # 底部導覽
    nav_btns = ""
    for k, icon, label in [('summary','📊','總覽'), ('personal','🏠',names['personal'][:2]), ('company','🏢',names['company'][:2]), ('invest','💰',names['invest'][:2]), ('settings','⚙️','設定')]:
        color = "#ff5722" if (type==k or (type=="summary" and k=="summary")) else "#ccc"
        url = "/" if k=="summary" else f"/?type={k}"
        nav_btns += f'<a href="{url}" style="text-decoration:none;color:{color};flex:1;"><span>{icon}</span><br><small style="font-size:0.6rem;">{label}</small></a>'

    content = ""
    if type == "summary":
        for k in ['personal', 'company', 'invest']:
            content += f'<div style="background:white;margin:15px;padding:20px;border-radius:15px;display:flex;justify-content:space-between;box-shadow:0 4px 10px rgba(0,0,0,0.05);"><b>{names[k]}</b><span>$ {bal[k]}</span></div>'
    elif type == "settings":
        content = f'<div style="padding:20px;"><form action="/update_settings" method="POST" style="background:white;padding:20px;border-radius:20px;"><input name="n1" class="form-control mb-2" value="{names["personal"]}"><input name="n2" class="form-control mb-2" value="{names["company"]}"><input name="n3" class="form-control mb-2" value="{names["invest"]}"><button class="btn btn-dark w-100">儲存</button></form></div>'
    else:
        content = f'<div style="padding:15px;"><form action="/add" method="POST" style="background:white;padding:20px;border-radius:20px;box-shadow:0 5px 15px rgba(0,0,0,0.05);"><input type="hidden" name="account_type" value="{type}"><select name="entry_type" class="form-select mb-2"><option value="expense">支出 💸</option><option value="income">收入 💰</option></select><div style="display:flex;gap:10px;"><input type="number" name="amount" class="form-control" placeholder="金額" required><input type="text" name="category" class="form-control" placeholder="項目" required></div><button class="btn btn-danger w-100 mt-2">存入</button></form></div>'
        for r in records:
            c = "#28a745" if r['entry_type']=='income' else "#dc3545"
            s = "+" if r['entry_type']=='income' else "-"
            content += f'<div style="background:white;margin:0 15px 10px;padding:15px;border-radius:15px;display:flex;justify-content:space-between;align-items:center;"><div><b>{r["category"]}</b><br><small style="color:#aaa;">{r["created_at"]}</small></div><b style="color:{c};">{s}$ {r["amount"]}</b></div>'

    return f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>body{{background:#f8f9fa;padding-bottom:100px;font-family:sans-serif;}}</style></head>
    <body><div style="background:#121212;color:white;padding:40px 20px;text-align:center;border-radius:0 0 30px 30px;"><small style="opacity:0.6;">{curr_name}</small><h1 style="font-weight:bold;">$ {curr_bal}</h1></div>
    {content}
    <div style="position:fixed;bottom:0;left:0;right:0;background:white;display:flex;border-top:1px solid #eee;padding:10px 0;text-align:center;height:75px;z-index:9999;">{nav_btns}</div>
    </body></html>"""

@app.get("/", response_class=HTMLResponse)
async def index(type: str = "summary"):
    conn = get_db()
    n = json.loads(conn.execute("SELECT value FROM settings WHERE key='names'").fetchone()['value'])
    bal = {{ k: (conn.execute("SELECT SUM(CASE WHEN entry_type='income' THEN amount ELSE -amount END) FROM records WHERE account_type=?", (k,)).fetchone()[0] or 0) for k in ['personal','company','invest'] }}
    recs = [] if type in ["summary", "settings"] else conn.execute("SELECT * FROM records WHERE account_type=? ORDER BY created_at DESC LIMIT 30", (type,)).fetchall()
    conn.close()
    return build_html(type, n, bal, recs)

@app.post("/add")
async def add(account_type: str = Form(...), amount: int = Form(...), category: str = Form(...), entry_type: str = Form("expense")):
    conn = get_db()
    conn.execute("INSERT INTO records (account_type, amount, category, created_at, entry_type) VALUES (?,?,?,?,?)", (account_type, amount, category, datetime.now().strftime("%m-%d %H:%M"), entry_type))
    conn.commit(); conn.close()
    return RedirectResponse(url=f"/?type={{account_type}}", status_code=303)

@app.post("/update_settings")
async def update(n1:str=Form(...), n2:str=Form(...), n3:str=Form(...)):
    conn = get_db(); conn.execute("UPDATE settings SET value=? WHERE key='names'", (json.dumps({'personal':n1,'company':n2,'invest':n3}),)); conn.commit(); conn.close()
    return RedirectResponse(url="/?type=settings", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
