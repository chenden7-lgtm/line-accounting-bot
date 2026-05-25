from flask import Flask, render_template, request, redirect, url_for
import datetime

app = Flask(__name__)

# 模擬資料庫
records = [
    {"id": 1, "date": "2026-05-23", "amount": 1000, "category": "辦公室租金", "description": "5月租金", "account_type": "work"},
    {"id": 2, "date": "2026-05-23", "amount": 100, "category": "午餐", "description": "排骨飯", "account_type": "personal"},
    {"id": 3, "date": "2026-05-24", "amount": 500, "category": "晚餐", "description": "火鍋", "account_type": "family"}
]

LEDGERS = {
    "personal": "個人生活",
    "work": "工作商務",
    "family": "家庭公庫"
}

@app.route('/')
def index():
    account_type = request.args.get('type', 'personal')
    if account_type not in LEDGERS:
        account_type = 'personal'
    
    filtered_records = [r for r in records if r['account_type'] == account_type]
    total = sum(r['amount'] for r in filtered_records)
    return render_template('index.html', records=filtered_records, current_type=account_type, ledgers=LEDGERS, total=total)

@app.route('/analysis')
def analysis():
    account_type = request.args.get('type', 'personal')
    filtered = [r for r in records if r['account_type'] == account_type]
    
    # 算類別總額
    cat_data = {}
    for r in filtered:
        cat_data[r['category']] = cat_data.get(r['category'], 0) + r['amount']
    
    return render_template('analysis.html', 
                         cat_labels=list(cat_data.keys()), 
                         cat_values=list(cat_data.values()), 
                         current_type=account_type,
                         ledgers=LEDGERS)

@app.route('/add', methods=['POST'])
def add_record():
    new_record = {
        "id": len(records) + 1,
        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "amount": int(request.form.get('amount', 0)),
        "category": request.form.get('category'),
        "description": request.form.get('description'),
        "account_type": request.form.get('account_type')
    }
    records.append(new_record)
    return redirect(url_for('index', type=new_record['account_type']))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3001)
