import sys
import os
import logging
import json
import re

# 加入套件路徑
sys.path.append(os.path.join(os.path.dirname(__file__), 'packages'))

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    TemplateSendMessage, ButtonsTemplate, PostbackAction, MessageAction
)
from accounting_brain import AccountingBrain
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
# 使用 accounting_bot.db
brain = AccountingBrain('accounting_bot.db')

SECRET = os.environ.get('LINE_CHANNEL_SECRET', '').strip("'").strip()
TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '').strip("'").strip()
line_bot_api = LineBotApi(TOKEN)
handler = WebhookHandler(SECRET)

@app.route("/", methods=['GET'])
def index():
    return "<h1>🥚 滷蛋記帳：專業開發版 v3.1</h1><p>目前服務狀態：正常運行中✅</p><p>多帳本切換與按鈕選單功能已更新！</p>", 200

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except Exception as e:
        logger.error(f"Error: {e}")
        abort(400)
    return 'OK', 200

@app.route("/report/<line_id>", methods=['GET'])
def report(line_id):
    ledger_id = brain.get_user_ledger(line_id)
    ledger_name = brain.get_ledger_name(ledger_id)
    records = brain.get_all_records(ledger_id)
    
    html = f"""
    <html>
    <head>
        <title>小蛋記帳報表 - {ledger_name}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: -apple-system, sans-serif; padding: 20px; background-color: #fff7f2; color: #333; }}
            .container {{ max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
            h1 {{ color: #ff5722; text-align: center; border-bottom: 2px solid #ffede7; padding-bottom: 15px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #fcfcfc; }}
            th {{ background-color: #fff3e0; color: #e64a19; border-radius: 5px; }}
            tr:hover {{ background-color: #fff8f6; }}
            .total {{ font-size: 22px; font-weight: bold; margin-top: 25px; text-align: right; color: #ff5722; }}
            .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #bbb; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📑 {ledger_name} 明細</h1>
            <table>
                <thead>
                    <tr><th>日期</th><th>項目</th><th>金額</th></tr>
                </thead>
                <tbody>
                    {"".join([f"<tr><td>{r[0].split()[0] if r[0] else '-'}</td><td>{r[1]}</td><td>${r[2]}</td></tr>" for r in records])}
                </tbody>
            </table>
            <div class="total">💰 累計總額：${sum([r[2] for r in records])}</div>
            <div class="footer">由 小蛋 (OpenClaw) 專業維護</div>
        </div>
    </body>
    </html>
    """
    return html, 200

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()
    
    if text == "帳本":
        ledgers = brain.get_user_ledgers(user_id)
        actions = []
        for name in ledgers[:3]:
            actions.append(MessageAction(label=f"📂 {name}", text=f"切換 {name}"))
        
        if "家庭帳本" not in ledgers:
            actions.append(MessageAction(label="🏠 建立家庭帳本", text="切換 家庭帳本"))
        elif "旅行帳本" not in ledgers:
            actions.append(MessageAction(label="✈️ 建立旅行帳本", text="切換 旅行帳本"))

        buttons_template = ButtonsTemplate(
            title="小蛋帳本控制中心",
            text="滷蛋，今天要切換到哪個帳本？",
            actions=actions[:4]
        )
        template_message = TemplateSendMessage(
            alt_text='請在手機上查看帳本選單喔！',
            template=buttons_template
        )
        line_bot_api.reply_message(event.reply_token, template_message)

    elif text == "查帳":
        reply = brain.get_summary(user_id) + "\n\n🥚：小蛋幫你監督著預算呢！"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        
    elif text == "報表":
        render_url = "https://ludan-web.onrender.com"
        reply = f"📊 滷蛋的帳本報表在此：\n{render_url}/report/{user_id}\n\n點擊連結查看詳細明細喔！"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

    elif text.startswith("切換 "):
        new_name = text.replace("切換 ", "").strip()
        reply = brain.switch_ledger(user_id, new_name)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

    elif any(char.isdigit() for char in text):
        res = brain.add_record(user_id, text)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"{res}\n\n🥚：小蛋記好囉！"))
    else:
        reply = f"收到！滷蛋說：『{text}』\n雖然我還在學習，但我會一直陪著你的！🥚"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3001))
    app.run(host='0.0.0.0', port=port)
