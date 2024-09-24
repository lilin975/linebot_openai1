from flask import Flask, request, abort
import requests  # 新增 requests 函数库用于发送HTTP请求

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *

#======python的函數庫==========
import tempfile, os
import datetime
import time
import traceback
#======python的函數庫==========

app = Flask(__name__)
static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')

# Channel Access Token
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
# Channel Secret
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# Azure OpenAI API Key和URL初始化設定
azure_openai_key = os.getenv('AZURE_OPENAI_API_KEY')
azure_openai_url = f"https://{os.getenv('AZURE_RESOURCE_NAME')}.openai.azure.com/openai/deployments/{os.getenv('AZURE_DEPLOYMENT_NAME')}/completions?api-version=2023-05-15"

def azure_GPT_response(text):
    headers = {
        'Content-Type': 'application/json',
        'api-key': azure_openai_key,
    }
    data = {
        "prompt": text,
        "max_tokens": 500,
        "temperature": 0.5,
        "stop": None,
    }

    try:
        response = requests.post(azure_openai_url, headers=headers, json=data)
        response.raise_for_status()  # 如果HTTP响应状态码不是200，抛出异常
        result = response.json()
        answer = result['choices'][0]['text'].strip()
        return answer
    except Exception as e:
        print(f"Error during Azure OpenAI API call: {e}")
        return "Azure OpenAI API 发生错误，请稍后再试"


# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'


# 處理訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    try:
        GPT_answer = azure_GPT_response(msg)  # 调用Azure版本的GPT响应
        print(GPT_answer)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(GPT_answer))
    except:
        print(traceback.format_exc())
        line_bot_api.reply_message(event.reply_token, TextSendMessage('你所使用的Azure OpenAI API key可能有误，请于后台Log内确认错误讯息'))


@handler.add(PostbackEvent)
def handle_message(event):
    print(event.postback.data)


@handler.add(MemberJoinedEvent)
def welcome(event):
    uid = event.joined.members[0].user_id
    gid = event.source.group_id
    profile = line_bot_api.get_group_member_profile(gid, uid)
    name = profile.display_name
    message = TextSendMessage(text=f'{name}歡迎加入')
    line_bot_api.reply_message(event.reply_token, message)


import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
