import os, sqlite3, json
from datetime import datetime
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI()
DB_PATH = "accounting_v3.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# 初始化資料庫
conn = get_db()
conn.execute("CREATE TABLE IF NOT EXISTS records (id INTEGER PRIMARY KEY AUTOINCREMENT, account_type TEXT, amount INTEGER, category TEXT, created_at TEXT, entry_type TEXT DEFAULT 'expense')")
conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
conn.execute("INSERT OR IGNORE INTO settings VALUES ('names', ?)", (json.dumps({'personal':'私人私帳','company':'公司公帳','invest':'投資理財'}),))
conn.commit()
conn.close()

def get_common_head(title):
    return f"""
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1.0,user-scalable=no,viewport-fit=cover">
        <title>{title}</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            :root {{ --p: #ff5722; --income: #28a745; --expense: #dc3545; }}
            body {{ background: #f7f9fc; font-family: sans-serif; padding-bottom: 100px; margin: 0; }}
            .top-area {{ background: #121212; color: white; padding: 40px 20px 60px; text-align: center; border-radius: 0 0 35px 35px; }}
            .glass-card {{ background: white; border-radius: 25px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); margin: -40px 15px 20px; padding: 20px; position: relative; z-index: 10; }}
            .bot-nav {{ position: fixed; bottom: 0; left: 0; right: 0; background: white; display: grid; grid-template-columns: repeat(6, 1fr); border-top: 1px solid #efefef; padding: 10px 0 env(safe-area-inset-bottom); height: 80px; z-index: 9999; }}
            .nav-i {{ text-decoration: none !important; color: #ccc; text-align: center; font-size: 0.65rem; font-weight: bold; }}
            .nav-i span {{ font-size: 1.3rem; display: inline-block; margin-bottom: 2px; }}
            .nav-i.active {{ color: var(--p); }}
            .item-row {{ background: white; border-radius: 18px; padding: 15px; margin: 0 15px 12px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 8px rgba(0,0,0,0.02); }}
            .btn-save {{ background: var(--p); color: white; border-radius: 12px; padding: 12px; border: none; font-weight: bold; width: 100%; }}
            .type-toggle {{ display: flex; background: #f1f3f6; border-radius: 12px; padding: 4px; margin-bottom: 20px; }}
            .toggle-btn {{ flex: 1; border: none; background: none; padding: 10px; border-radius: 10px; font-weight: bold; color: #888; }}
            .toggle-btn.active-exp {{ background: white; color: var(--expense); box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
            .toggle-btn.active-inc {{ background: white; color: var(--income); box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        </style>
    </head>
    """

def get_nav_html(current, names):
    return f"""
    <div class="bot-nav">
        <a href="/" class="nav-i {'active' if current=='summary' else ''}"><span>📊</span><br>總覽</a>
        <a href="/?type=personal" class="nav-i {'active' if current=='personal' else ''}"><span>🏠</span><br>{names['personal'][:2]}</a>
        <a href="/?type=company" class="nav-i {'active' if current=='company' else ''}"><span>🏢</span><br>{names['company'][:2]}</a>
        <a href="/?type=invest" class="nav-i {'active' if current=='invest' else ''}"><span>💰</span><br>{names['invest'][:2]}</a>
        <a href="/?type=report" class="nav-i {'active' if current=='report' else ''}"><span>📈</span><br>報表</a>
        <a href="/?type=settings" class="nav-i {'active' if current=='settings' else ''}"><span>⚙️</span><br>設定</a>
    </div>
    """

@app.get("/", response_class=HTMLResponse)
async def index(type: str = "summary"):
    conn = get_db()
    names = json.loads(conn.execute("SELECT value FROM settings WHERE key='names'").fetchone()['value'])
    bal = {{}}
    for t in ['personal', 'company', 'invest']:
        r = conn.execute("SELECT SUM(CASE WHEN entry_type='income' THEN amount ELSE -amount END) as s FROM records WHERE account_type=?", (t,)).fetchone()
        bal[t] = r['s'] if r['s'] else 0
    total = sum(bal.values())

    html = get_common_head("滷蛋記帳") + "<body>"
    html += f'<div class="top-area"><small class="opacity-50 fw-bold">{{names.get(type, "全域資產總覽")}}</small><h1 class="display-5 fw-bold mt-1">$ {bal.get(type, total)}</h1></div>'

    if type == "summary":
        html += '<div class="container mt-4">'
        for t in ['personal', 'company', 'invest']:
            html += f'<div class="item-row"><b>{names[t]}</b><b class="text-dark">$ {{bal[t]}}</b></div>'
        html += '<h6 class="fw-bold mt-4 mb-3 ms-3">最近動態</h6>'
        records = conn.execute("SELECT * FROM records ORDER BY created_at DESC LIMIT 10").fetchall()
        for r in records:
            color = "#28a745" if r['entry_type'] == 'income' else "#dc3545"
            sym = "+" if r['entry_type'] == 'income' else "-"
            html += f'<div class="item-row"><div><b>{r["category"]}</b><br><small class="text-muted">{r["created_at"]}</small></div><b style="color:{color}">{sym}$ {r["amount"]}</b></div>'
        html += "</div>"
    elif type == "report":
        flow = {{row['entry_type']: row['s'] for row in conn.execute("SELECT entry_type, SUM(amount) as s FROM records GROUP BY entry_type").fetchall()}}
        top = conn.execute("SELECT category, SUM(amount) as s FROM records WHERE entry_type='expense' GROUP BY category ORDER BY s DESC LIMIT 5").fetchall()
        html += f"""<div class="glass-card text-center"><small class="text-muted">收入 vs 支出</small>
        <canvas id="flowChart" style="max-height:150px;" class="mt-2"></canvas></div>
        <div class="container"><h6 class="fw-bold mb-3">🔥 支出排行</h6>"""
        for r in top:
            html += f'<div class="item-row"><b>{r["category"]}</b><b class="text-danger">$ {r["s"]}</b></div>'
        html += f"""</div><script>
            new Chart(document.getElementById('flowChart').getContext('2d'), {{
                type: 'doughnut', data: {{ labels:['收','支'], datasets:[{{data:[{flow.get('income',1)}, {flow.get('expense',1)}], backgroundColor:['#28a745','#dc3545']}}] }}
            }});
        </script>"""
    elif type == "settings":
        html += f"""<div class="glass-card"><form action="/update_settings" method="POST">
            <label class="small fw-bold text-muted">帳本 1</label><input name="n1" class="form-control mb-3" value="{names['personal']}">
            <label class="small fw-bold text-muted">帳本 2</label><input name="n2" class="form-control mb-3" value="{names['company']}">
            <label class="small fw-bold text-muted">帳本 3</label><input name="n3" class="form-control mb-3" value="{names['invest']}">
            <button class="btn-save">儲存設定</button></form></div>"""
    else:
        html += f"""<div class="glass-card"><form action="/add" method="POST" id="xf">
            <input type="hidden" name="account_type" value="{type}"><input type="hidden" name="entry_type" id="et" value="expense">
            <div class="type-toggle"><button type="button" id="eb" class="toggle-btn active-exp" onclick="st('expense')">支出</button><button type="button" id="ib" class="toggle-btn" onclick="st('income')">收入</button></div>
            <div class="row g-2"><div class="col-6"><input type="number" name="amount" class="form-control" placeholder="金額" required></div>
            <div class="col-6"><input type="text" name="category" class="form-control" placeholder="項目" required></div>
            <div class="col-12 mt-3"><button type="submit" id="sb" class="btn-save" style="background:var(--expense)">存入支出</button></div></div></form></div>"""
        records = conn.execute("SELECT * FROM records WHERE account_type=? ORDER BY created_at DESC LIMIT 50", (type,)).fetchall()
        for r in records:
            color = "#28a745" if r['entry_type'] == 'income' else "#dc3545"
            sym = "+" if r['entry_type'] == 'income' else "-"
            html += f'<div class="item-row"><div><b>{r["category"]}</b><br><small class="text-muted">{r["created_at"]}</small></div><div class="d-flex align-items-center"><b style="color:{color}">{sym}$ {r["amount"]}</b><form action="/delete/{{r["id"]}}?type={{type}}" method="POST" class="ms-2"><button type="submit" style="background:none;border:none;color:#ddd;font-size:1.2rem;">&times;</button></form></div></div>'

    html += get_nav_html(type, names) + f"""<script>
        function st(t) {{
            document.getElementById('et').value = t;
            document.getElementById('eb').className = (t === 'expense' ? 'toggle-btn active-exp' : 'toggle-btn');
            document.getElementById('ib').className = (t === 'income' ? 'toggle-btn active-inc' : 'toggle-btn');
            const b = document.getElementById('sb'); b.innerText = t === 'expense' ? '存入支出' : '存入收入';
            b.style.background = t === 'expense' ? 'var(--expense)' : 'var(--income)';
        }}
    </script></body></html>"""
    conn.close()
    return html

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
async def update(n1:str=Form(...), n2:str=Form(...), n3:str=Form(...)):
    conn = get_db(); conn.execute("UPDATE settings SET value=? WHERE key='names'", (json.dumps({{ 'personal':n1,'company':n2,'invest':n3 }}),)); conn.commit(); conn.close()
    return RedirectResponse(url="/?type=settings", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
