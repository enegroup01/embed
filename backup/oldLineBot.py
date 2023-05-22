from flask import Flask, request, abort
from linebot.models import *
import os
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import time
from llama_index import ResponseSynthesizer, LLMPredictor, ServiceContext, QuestionAnswerPrompt
from llama_index.retrievers import VectorIndexRetriever
from llama_index.query_engine import RetrieverQueryEngine
from llama_index.indices.postprocessor import SimilarityPostprocessor
from llama_index import StorageContext, load_index_from_storage
import re
from linebot import LineBotApi, WebhookHandler, WebhookParser
from linebot.exceptions import InvalidSignatureError
from urllib.parse import parse_qsl
from langchain import OpenAI
from datetime import datetime, timedelta
import json


# import openai
app = Flask(__name__)

line_bot_api = LineBotApi(os.environ['CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['CHANNEL_SECRET'])
parser = WebhookParser(os.environ['CHANNEL_SECRET'])
yourID = 'Ued7ae416eb03f3295c1a6600fda84b9e'

index = None
eatEnjoyImageUrl = 'https://scontent.ftpe7-2.fna.fbcdn.net/v/t39.30808-6/287060490_1450234702064967_2189301953826091703_n.jpg?_nc_cat=109&ccb=1-7&_nc_sid=09cbfe&_nc_ohc=pXBveza6NOcAX_g_l00&_nc_ht=scontent.ftpe7-2.fna&oh=00_AfDxCEKDpv4WbAHV_KbVz0ndRSLlN1wLVOsPZXPQcPsaGg&oe=645BD6A6'
smallEatEnjoyImageUrl = 'https://eatenjoyforever.com/wp-content/uploads/2022/05/cropped-eat-enjoy-logo-02.png'
cred = credentials.Certificate("serviceAccountKey.json")

firebase_admin.initialize_app(
    cred, {'databaseURL': 'https://linebot-93aa8-default-rtdb.asia-southeast1.firebasedatabase.app/'})
ref = db.reference('apiKey/')
memberRef = db.reference('members/')
# userRef = db.reference('members/user01/')
# userChatRef = db.reference('members/user01/chats')

while True:
    gptApiKey = ref.get()
    if gptApiKey is not None:
        break
    time.sleep(1)  # Wait for 1 second before checking again
os.environ['OPENAI_API_KEY'] = gptApiKey
# openai.api_key = gptApiKey


def initialize_index():
    global index
    tokens = 256
    llm_predictor = LLMPredictor(llm=OpenAI(
        temperature=0, model_name="text-davinci-003", max_tokens=tokens))
    service_context = ServiceContext.from_defaults(llm_predictor=llm_predictor)
    storage_context = StorageContext.from_defaults(persist_dir='model')
    # load index
    index = load_index_from_storage(
        storage_context=storage_context, service_context=service_context)


@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# Eat enjoy意享美式廚房新店店 231新北市新店區北新路一段88巷9號  24.9674302,121.5401599


def uploadProfile(profile):
    userRef = memberRef.child(profile.user_id)
    userRef.child('display_name').set(profile.display_name)
    userRef.child('picture_url').set(profile.picture_url)
    userRef.child('language').set(profile.language)
    return


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    UserId = event.source.user_id
    profile = line_bot_api.get_profile(UserId)
    profileId = profile.user_id

    now = datetime.now()
    one_week_ago = now - timedelta(days=7)

    if memberRef.child(profileId).get() is not None:
        print('*==== I have profile')
        userChatRef = memberRef.child(profileId + '/chats')
        query = userChatRef.order_by_child('timestamp').start_at(
            one_week_ago.timestamp() * 1000)
        formatted_messages = []
        for _, value in query.get().items():
            formatted_message = f"{value['role']}: {value['content'].strip()}"
            formatted_messages.append(formatted_message)
        result_string = ", ".join(formatted_messages)
        messagesToAsk = result_string
        if userChatRef.get() is not None:
            # in case has no chats
            chat_length = len(userChatRef.get())
        else:
            chat_length = 0
    else:
        messagesToAsk = ''
        chat_length = 0
        uploadProfile(profile=profile)

    receivedMsg = event.message.text
    if re.match(receivedMsg, '3'):
        line_bot_api.push_message(
            event.source.user_id, TextSendMessage(text='安安您好！今天想要怎樣的呢？'))
    elif re.match(receivedMsg, '1'):
        line_bot_api.reply_message(event.reply_token, LocationSendMessage(
            title='Eat enjoy意享美式廚房新店店', address='231新北市新店區北新路一段88巷9號', latitude=24.9674302, longitude=121.5401599))
    elif re.match(receivedMsg, '2'):
        buttons_template = TemplateSendMessage(
            alt_text='歡迎來到Eat Enjoy',
            template=ButtonsTemplate(
                title='歡迎來到Eat Enjoy意想美式餐廳',
                text='想不到吧～～',
                thumbnail_image_url=smallEatEnjoyImageUrl,
                actions=[
                    MessageTemplateAction(
                        label='一段文字',
                        text='送給你'
                    ),
                    URITemplateAction(
                        label='一支影片',
                        uri='https://dsqqu7oxq6o1v.cloudfront.net/motion-array-1283879-ctLR7Fp3LN-high.mp4'
                    ),
                    PostbackTemplateAction(
                        label='含有文字的訊息',
                        text='還給你',
                        data='這段訊息'
                    )

                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)
    elif re.match(receivedMsg, '4'):
        Confirm_template = TemplateSendMessage(
            alt_text='開始訂位',
            template=ConfirmTemplate(
                title='您要直接訂位嗎？',
                text='目前尚有空位，請儘速訂位',
                actions=[
                    PostbackTemplateAction(
                        label='馬上訂位',
                        text='好的',
                        data='action=book&text=馬上訂位'
                    ),
                    MessageTemplateAction(
                        label='再看看',
                        text='再看看'
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, Confirm_template)
    elif re.match(receivedMsg, '5'):
        buttons_template_message = TemplateSendMessage(
            alt_text='線上點餐',
            template=ButtonsTemplate(
                thumbnail_image_url=eatEnjoyImageUrl,
                title='點餐系統',
                text='請選擇',
                actions=[
                    URIAction(
                        label='直接點餐',
                        uri='https://eatenjoyforever.com/order-online/'
                    ),
                    MessageAction(
                        label='再看看',
                        text='我再考慮一下'
                    ),
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template_message)
    else:
        replyWithLlama(event, chat_length, messagesToAsk, profileId)


@handler.add(PostbackEvent)
def handle_postback(event):
    data = event.postback.data
    dataDict = parse_qsl(data)
    params_dict = {key: value for key, value in dataDict}
    if params_dict['action'] == 'book':
        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text=params_dict['text']))


def replyWithLlama(event, chat_length, messagesToAsk, profileId):
    global index
    # configure retriever
    retriever = VectorIndexRetriever(
        index=index,
        similarity_top_k=2,
    )

    # configure response synthesizer
    response_synthesizer = ResponseSynthesizer.from_args(
        node_postprocessors=[
            SimilarityPostprocessor(similarity_cutoff=0.7)
        ]
    )
    query_engine = RetrieverQueryEngine(
        retriever=retriever,
        response_synthesizer=response_synthesizer,
    )

    messagesToAsk += 'question:' + event.message.text
    '''
    DEFAULT_TEXT_QA_PROMPT_TMPL = (
        "Context information is below. \n"
        "---------------------\n"
        "{context_str}"
        "\n---------------------\n"
        "Given the context information and not prior knowledge, "
        "answer the question: {query_str}\n"
    )
    DEFAULT_TEXT_QA_PROMPT = QuestionAnswerPrompt(DEFAULT_TEXT_QA_PROMPT_TMPL)
    '''

    QA_PROMPT_TMPL = (
        "你是一個AI客服助手, 專門回答客人有關我們餐廳的問題, 根據我提供的餐廳背景資訊來回答問題."
        "如果你從我提供的背景資訊中找不到相關的答案,只需說 「嗯,抱歉,我不確定，有相關問題可以來電詢問客服」,不要試圖編造答案."
        "餐廳背景資訊: {context_str}"
        "請用繁體中文回答問題：{query_str}"
        "如果背景資訊中有提到與問題相關內容的網站連結，請在回答的最後提供連結，表示這是推薦給客人的。"
        "如果客人的問題與任何背景資訊裡的網站連結都沒有關係，則不做任何推薦，也不要提供網站連結給客人，也絕對不要提供任何不屬於背景信息的外部網站連結。」"
    )
    QA_PROMPT = QuestionAnswerPrompt(QA_PROMPT_TMPL)
    query_engine = index.as_query_engine(
        text_qa_template=QA_PROMPT,
        retriever=retriever,
        response_synthesizer=response_synthesizer,
    )
    print(messagesToAsk)
    response = query_engine.query(messagesToAsk)

    timestamp = int(time.time() * 1000)  # Convert to milliseconds
    updatedAskMessage = {"role": "question",
                         "content": event.message.text, "timestamp": timestamp}
    new_index = int(chat_length)
    memberRef.child(profileId + '/chats').child(str(new_index)
                                                ).set(updatedAskMessage)

    updatedAnswerMessage = {"role": "answer",
                            "content": response.response, "timestamp": timestamp}
    new_index = int(chat_length + 1)
    memberRef.child(profileId + '/chats').child(str(new_index)
                                                ).set(updatedAnswerMessage)

    # response = query_engine.query(event.message.text + '?')

    # response = openai.Completion.create(
    #     model='text-davinci-003',
    #     prompt=event.message.text,
    #     max_tokens=256,
    #     temperature=0.5,
    # )
    # 接收到回覆訊息後，移除換行符號
    # reply_msg = response["choices"][0]["text"].replace('\n', '')
    reply_msg = str(response).replace('\n', '')
    if reply_msg.startswith("A:"):
        reply_msg = reply_msg[2:].lstrip()
    message = TextSendMessage(text=reply_msg)
    line_bot_api.reply_message(event.reply_token, message)


if __name__ == "__main__":
    initialize_index()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
