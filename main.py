import os, sqlite3, json
from datetime import datetime
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI()
DB_PATH = "accounting_v8.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("CREATE TABLE IF NOT EXISTS records (id INTEGER PRIMARY KEY AUTOINCREMENT, account_type TEXT, amount INTEGER, category TEXT, created_at TEXT, entry_type TEXT DEFAULT 'expense')")
    conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("INSERT OR IGNORE INTO settings VALUES ('names', ?)", (json.dumps({'personal':'私人', 'company':'公司', 'invest':'投資'}),))
    conn.commit()
    conn.close()

init_db()

def render_page(current_type, names, totals, records=None, flow=None, top_expenses=None):
    total_val = totals.get(current_type, sum(totals.values()))
    
    # 底部導覽列
    nav = f"""<div style="position:fixed;bottom:0;left:0;right:0;background:white;display:grid;grid-template-columns:repeat(6,1fr);border-top:1px solid #efefef;padding:10px 0 env(safe-area-inset-bottom);height:80px;z-index:999;text-align:center;">
        <a href="/?type=summary" style="text-decoration:none;color:{'#ff5722' if current_type=='summary' else '#ccc'};"><span>📊</span><br><small>統整</small></a>
        <a href="/?type=personal" style="text-decoration:none;color:{'#ff5722' if current_type=='personal' else '#ccc'};"><span>🏠</span><br><small>{names['personal'][:2]}</small></a>
        <a href="/?type=company" style="text-decoration:none;color:{'#ff5722' if current_type=='company' else '#ccc'};"><span>🏢</span><br><small>{names['company'][:2]}</small></a>
        <a href="/?type=invest" style="text-decoration:none;color:{'#ff5722' if current_type=='invest' else '#ccc'};"><span>💰</span><br><small>{names['invest'][:2]}</small></a>
        <a href="/?type=report" style="text-decoration:none;color:{'#ff5722' if current_type=='report' else '#ccc'};"><span>📈</span><br><small>報表</small></a>
        <a href="/?type=settings" style="text-decoration:none;color:{'#ff5722' if current_type=='settings' else '#ccc'};"><span>⚙️</span><br><small>設定</small></a>
    </div>"""

    header = f'<div style="background:#121212;color:white;padding:45px 20px 60px;text-align:center;border-radius:0 0(35px);position:relative;"><small style="opacity:0.6;font-weight:bold;">{names.get(current_type, "全域資產")}</small><h1 style="font-weight:bold;margin-top:5px;font-size:2.5rem;">$ {total_val}</h1></div>'
    
    content = ""
    if current_type == "summary":
        for t in ['personal', 'company', 'invest']:
            content += f'<div style="background:white;margin:15px;padding:20px;border-radius:20px;display:flex;justify-content:space-between;box-shadow:0 4px 15px rgba(0,0,0,0.04);"><b>{names[t]}</b><span style="font-weight:bold;color:#333;">$ {totals[t]}</span></div>'
    elif current_type == "settings":
        content = f'<div style="padding:20px;"><form action="/update_settings" method="POST" style="background:white;padding:30px;border-radius:25px;box-shadow:0 10px 30px rgba(0,0,0,0.05);">'
        content += f'<label style="color:#888;font-size:0.8rem;font-weight:bold;">帳本1: {names["personal"]}</label><input name="n1" class="form-control mb-3" style="border-radius:12px;padding:12px;" value="{names["personal"]}">'
        content += f'<label style="color:#888;font-size:0.8rem;font-weight:bold;">帳本2: {names["company"]}</label><input name="n2" class="form-control mb-3" style="border-radius:12px;padding:12px;" value="{names["company"]}">'
        content += f'<label style="color:#888;font-size:0.8rem;font-weight:bold;">帳本3: {names["invest"]}</label><input name="n3" class="form-control mb-3" style="border-radius:12px;padding:12px;" value="{names["invest"]}">'
        content += '<button class="btn btn-dark w-100 py-3 fw-bold" style="border-radius:15px;">儲存修改內容</button></form></div>'
    else:
        content = f'<div style="background:white;margin:-30px 15px 20px;padding:25px;border-radius:25px;box-shadow:0 15px 30px rgba(0,0,0,0.08);position:relative;z-index:10;"><form action="/add" method="POST">'
        content += f'<input type="hidden" name="account_type" value="{current_type}">'
        content += '<select name="entry_type" style="background:#f1f3f6;border:none;border-radius:12px;padding:10px;width:100%;font-weight:bold;text-align:center;margin-bottom:15px;"><option value="expense">支出 💸</option><option value="income">收入 💰</option></select>'
        content += '<div style="display:flex;gap:10px;"><input type="number" name="amount" class="form-control" style="border-radius:10px;padding:12px;" placeholder="金額" required><input type="text" name="category" class="form-control" style="border-radius:10px;padding:12px;" placeholder="項目" required></div>'
        content += '<button class="btn w-100 py-3 mt-3 fw-bold text-white shadow-sm" style="background:#ff5722;border-radius:15px;">確認存入</button></form></div>'
        if records:
            for r in records:
                color = "#28a745" if r['entry_type'] == 'income' else "#dc3545"
                symbol = "+" if r['entry_type'] == 'income' else "-"
                content += f'<div style="background:white;margin:0 15px 12px;padding:18px;border-radius:18px;display:flex;justify-content:space-between;align-items:center;"><div><b style="font-size:1rem;">{r["category"]}</b><br><small style="color:#aaa;font-size:0.7rem;">{r["created_at"]}</small></div><div style="display:flex;align-items:center;"><b style="color:{color};font-size:1.1rem;">{symbol}$ {r["amount"]}</b><form action="/delete/{r["id"]}?type={current_type}" method="POST" style="margin-left:15px;"><button style="border:none;background:none;color:#ddd;font-size:1.4rem;">&times;</button></form></div></div>'

    full_html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"><style>body{{background:#f7f9fc;font-family:sans-serif;padding-bottom:100px;}}.nav-i span{{font-size:1.4rem;display:block;margin-bottom:2px;}}</style></head><body>{header}{content}{nav}</body></html>"""
    return full_html

@app.get("/", response_class=HTMLResponse)
async def index(type: str = "summary"):
    conn = get_db()
    names_row = conn.execute("SELECT value FROM settings WHERE key='names'").fetchone()
    names = json.loads(names_row['value'])
    bal = {{}}
    for t in ['personal', 'company', 'invest']:
        r = conn.execute("SELECT SUM(CASE WHEN entry_type='income' THEN amount ELSE -amount END) as s FROM records WHERE account_type=?", (t,)).fetchone()
        bal[t] = r['s'] if r['s'] else 0
    
    if type in ['summary', 'settings']:
        res_html = render_page(type, names, bal)
    else:
        records = conn.execute("SELECT * FROM records WHERE account_type=? ORDER BY created_at DESC LIMIT 50", (type,)).fetchall()
        res_html = render_page(type, names, bal, records=records)
    
    conn.close()
    return res_html

@app.post("/add")
async def add(account_type: str = Form(...), amount: int = Form(...), category: str = Form(...), entry_type: str = Form("expense")):
    conn = get_db()
    conn.execute("INSERT INTO records (account_type, amount, category, created_at, entry_type) VALUES (?,?,?,?,?)", (account_type, amount, category, datetime.now().strftime("%m-%d %H:%M"), entry_type))
    conn.commit(); conn.close()
    return RedirectResponse(url=f"/?type={{account_type}}", status_code=303)

@app.post("/delete/{{rid}}")
async def delete(rid: int, type: str):
    conn = get_db(); conn.execute("DELETE FROM records WHERE id=?", (rid,)); conn.commit(); conn.close()
    return RedirectResponse(url=f"/?type={{type}}", status_code=303)

@app.post("/update_settings")
async def update_settings(n1:str=Form(...), n2:str=Form(...), n3:str=Form(...)):
    conn = get_db(); conn.execute("UPDATE settings SET value=? WHERE key='names'", (json.dumps({{ 'personal':n1,'company':n2,'invest':n3 }}),)); conn.commit(); conn.close()
    return RedirectResponse(url="/?type=settings", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
