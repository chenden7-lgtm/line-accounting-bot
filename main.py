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

def render_page(current_type, names, totals, records=None):
    total_val = totals.get(current_type, sum(totals.values()))
    
    # 底部導覽列精修
    nav = f"""<div style="position:fixed;bottom:0;left:0;right:0;background:rgba(255,255,255,0.98);display:grid;grid-template-columns:repeat(6,1fr);border-top:1px solid #f0f0f0;padding:8px 0 env(safe-area-inset-bottom);height:75px;z-index:999;text-align:center;">
        <a href="/?type=summary" style="text-decoration:none;color:{'#ff5722' if current_type=='summary' else '#ccc'};"><span>📊</span><br><small style="font-size:0.6rem;font-weight:bold;">統整</small></a>
        <a href="/?type=personal" style="text-decoration:none;color:{'#ff5722' if current_type=='personal' else '#ccc'};"><span>🏠</span><br><small style="font-size:0.6rem;font-weight:bold;">{names['personal'][:2]}</small></a>
        <a href="/?type=company" style="text-decoration:none;color:{'#ff5722' if current_type=='company' else '#ccc'};"><span>🏢</span><br><small style="font-size:0.6rem;font-weight:bold;">{names['company'][:2]}</small></a>
        <a href="/?type=invest" style="text-decoration:none;color:{'#ff5722' if current_type=='invest' else '#ccc'};"><span>💰</span><br><small style="font-size:0.6rem;font-weight:bold;">{names['invest'][:2]}</small></a>
        <a href="/?type=report" style="text-decoration:none;color:{'#ff5722' if current_type=='report' else '#ccc'};"><span>📈</span><br><small style="font-size:0.6rem;font-weight:bold;">報表</small></a>
        <a href="/?type=settings" style="text-decoration:none;color:{'#ff5722' if current_type=='settings' else '#ccc'};"><span>⚙️</span><br><small style="font-size:0.6rem;font-weight:bold;">設定</small></a>
    </div>"""

    header = f'<div style="background:linear-gradient(135deg, #222 0%, #000 100%);color:white;padding:35px 20px 55px;text-align:center;border-radius:0 0 30px 30px;"><small style="opacity:0.6;letter-spacing:1px;">{names.get(current_type, "資產總額")}</small><h1 style="font-weight:800;margin-top:8px;font-size:2.2rem;">$ {total_val}</h1></div>'
    
    body_content = ""
    if current_type == "summary":
        for t in ['personal', 'company', 'invest']:
            body_content += f'<div style="background:white;margin:12px 15px;padding:18px;border-radius:20px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 6px 15px rgba(0,0,0,0.03); border:1px solid #f9f9f9;"><b>{names[t]}</b><span style="font-weight:bold;color:#ff5722;font-size:1.1rem;">$ {totals[t]}</span></div>'
    elif current_type == "settings":
        body_content = f'<div style="padding:15px;"><div style="background:white;padding:25px;border-radius:25px;box-shadow:0 10px 30px rgba(0,0,0,0.05); border:1px solid #fff;"><form action="/update_settings" method="POST">'
        for k, v in [('n1', names['personal']), ('n2', names['company']), ('n3', names['invest'])]:
            body_content += f'<label style="color:#999;font-size:0.75rem;font-weight:bold;margin-left:5px;">帳本名稱</label><input name="{k}" class="form-control mb-3" style="border-radius:12px;padding:12px;border:2px solid #f1f3f6;font-weight:bold;" value="{v}">'
        body_content += '<button class="btn btn-dark w-100 py-3 mt-2" style="border-radius:15px;font-weight:800;box-shadow:0 4px 12px rgba(0,0,0,0.1);">儲存設定</button></form></div></div>'
    else:
        body_content = f'<div style="background:white;margin:-30px 20px 25px;padding:20px;border-radius:25px;box-shadow:0 12px 25px rgba(0,0,0,0.08);position:relative;z-index:10;"><form action="/add" method="POST">'
        body_content += f'<input type="hidden" name="account_type" value="{current_type}">'
        body_content += '<div style="display:flex;background:#f1f3f6;border-radius:12px;padding:4px;margin-bottom:15px;"><select name="entry_type" style="background:none;border:none;width:100%;font-weight:bold;text-align:center;color:#555;"><option value="expense">支出 💸</option><option value="income">收入 💰</option></select></div>'
        body_content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;"><input type="number" name="amount" class="form-control" style="border-radius:10px;padding:12px;border:1px solid #eee;" placeholder="金額" required><input type="text" name="category" class="form-control" style="border-radius:10px;padding:12px;border:1px solid #eee;" placeholder="項目" required></div>'
        body_content += '<button class="btn w-100 py-3 mt-3 fw-bold text-white" style="background:#ff5722;border-radius:15px;">存入紀錄</button></form></div>'
        if records:
            for r in records:
                color = "#28a745" if r['entry_type'] == 'income' else "#dc3545"
                symbol = "+" if r['entry_type'] == 'income' else "-"
                body_content += f'<div style="background:white;margin:0 20px 10px;padding:15px;border-radius:15px;display:flex;justify-content:space-between;align-items:center;border:1px solid #f0f0f0;"><div><b style="font-size:0.95rem;">{r["category"]}</b><br><small style="color:#bbb;font-size:0.65rem;">{r["created_at"]}</small></div><div style="display:flex;align-items:center;"><b style="color:{color};font-size:1.05rem;">{symbol}$ {r["amount"]}</b><form action="/delete/{r["id"]}?type={current_type}" method="POST" style="margin-left:12px;"><button style="border:none;background:none;color:#eee;font-size:1.4rem;">&times;</button></form></div></div>'

    final_html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"><style>body{{background:#f8f9fa;font-family:-apple-system,BlinkMacSystemFont,sans-serif;padding-bottom:120px;}}.nav-i span{{font-size:1.3rem;display:block;margin-bottom:2px;}}</style></head><body>{header}{body_content}{nav}</body></html>"""
    return final_html

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
