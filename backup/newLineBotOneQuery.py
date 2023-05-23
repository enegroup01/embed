from flask import Flask, request, abort
from linebot.models import *
import os
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import time
import re
from linebot import LineBotApi, WebhookHandler, WebhookParser
from linebot.exceptions import InvalidSignatureError
from urllib.parse import parse_qsl
from datetime import datetime, timedelta
import json
import openai
import pandas as pd
import tiktoken  # for counting tokens
from scipy import spatial  # for calculating vector similarities for search
import ast  # for converting embeddings saved as strings back to arrays


# import openai
app = Flask(__name__)

line_bot_api = LineBotApi(os.environ['CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['CHANNEL_SECRET'])
parser = WebhookParser(os.environ['CHANNEL_SECRET'])

# openai vars
# models
EMBEDDING_MODEL = "text-embedding-ada-002"
GPT_MODEL = "gpt-3.5-turbo"
embeddings_path = "myEmbeddedModel.csv"
df = pd.read_csv(embeddings_path)
df['embedding'] = df['embedding'].apply(ast.literal_eval)

# index = None
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
openai.api_key = gptApiKey


def strings_ranked_by_relatedness(
    query: str,
    df: pd.DataFrame,
    relatedness_fn=lambda x, y: 1 - spatial.distance.cosine(x, y),
    top_n: int = 100
) -> tuple[list[str], list[float]]:
    """Returns a list of strings and relatednesses, sorted from most related to least."""
    query_embedding_response = openai.Embedding.create(
        model=EMBEDDING_MODEL,
        input=query,
    )
    query_embedding = query_embedding_response["data"][0]["embedding"]
    strings_and_relatednesses = [
        (row["combined"], relatedness_fn(query_embedding, row["embedding"]))
        for i, row in df.iterrows()
    ]
    strings_and_relatednesses.sort(key=lambda x: x[1], reverse=True)
    strings, relatednesses = zip(*strings_and_relatednesses)
    return strings[:top_n], relatednesses[:top_n]


def num_tokens(text: str, model: str = GPT_MODEL) -> int:
    """Return the number of tokens in a string."""
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))


def query_message(
    query: str,
    df: pd.DataFrame,
    model: str,
    token_budget: int
) -> str:
    """Return a message for GPT, with relevant source texts pulled from a dataframe."""
    strings, relatednesses = strings_ranked_by_relatedness(query, df)
    introduction = 'Use the below information to answer the subsequent question and in traditional chinese.'
    question = f"\n\nQuestion: {query}"
    message = introduction
    for string in strings:
        next_article = f'\n\ next information:\n"""\n{string}\n"""'
        if (
            num_tokens(message + next_article + question, model=model)
            > token_budget
        ):
            break
        else:
            message += next_article
    return message + question


def ask(
    query: str,
    df: pd.DataFrame = df,
    model: str = GPT_MODEL,
    token_budget: int = 4096 - 500,
    print_message: bool = False,
) -> str:
    """Answers a query using GPT and a dataframe of relevant texts and embeddings."""
    message = query_message(query, df, model=model, token_budget=token_budget)
    if print_message:
        print(message)
    messages = [
        {"role": "system", "content": "You answer questions about the restaurant."},
        {"role": "user", "content": message},
    ]
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=0
    )
    response_message = response["choices"][0]["message"]["content"]
    print(response_message)

    strings, relatednesses = strings_ranked_by_relatedness(
        query, df, top_n=5)
    for string, relatedness in zip(strings, relatednesses):
        print(f"{relatedness=:.3f}")
        print(string)
    return response_message


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

    messages = [
        {"role": "system", "content": "You are a helpful assistant that helps answer questions about the restaurant."}
    ]
    if memberRef.child(profileId).get() is not None:
        print('*==== I have profile')
        # userChatRef = memberRef.child(profileId + '/chats')
        # query = userChatRef.order_by_child('timestamp').start_at(
        #     one_week_ago.timestamp() * 1000)
        # formatted_messages = []
        # for _, value in query.get().items():
        #     formatted_message = f"{value['role']}: {value['content'].strip()}"
        #     formatted_messages.append(formatted_message)
        # result_string = ", ".join(formatted_messages)
        # messagesToAsk = result_string
        # if userChatRef.get() is not None:
        #     # in case has no chats
        #     chat_length = len(userChatRef.get())
        # else:
        #     chat_length = 0

        # (2) when query by last 8 question
        latest_chats = memberRef.child(profileId + '/chats').order_by_child(
            'timestamp').limit_to_last(8).get()
        jsonChats = json.dumps(latest_chats)
        data_dict = json.loads(jsonChats)

        for _, chat_data in data_dict.items():
            role = chat_data["role"]
            content = chat_data["content"]
            if role == "question":
                messages.append(
                    {"role": "user", "content": content})
            elif role == "answer":
                messages.append(
                    {"role": "assistant", "content": content})
        print("*==== got message")
        print(messages)

        # result = ', '.join(
        #     [f"{value['role']}: {value['content']}" for value in data_dict.values()])
        # if need conversation history
        # messagesToAsk = result
        # print('*===conversation history')
        # print(result)
    else:

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
        # replyWithLlama(event, chat_length, messagesToAsk, profileId)
        aiResponse = ask(receivedMsg)
        uploadConversation(event, profileId, aiResponse)
        reply_msg = str(aiResponse).replace('\n', '')
        if reply_msg.startswith("A:"):
            reply_msg = reply_msg[2:].lstrip()
        message = TextSendMessage(text=reply_msg)
        line_bot_api.reply_message(event.reply_token, message)


def uploadConversation(event, profileId, aiResponse):
    timestamp = int(time.time() * 1000)
    updatedAskMessage = {"role": "question",
                         "content": event.message.text, "timestamp": timestamp}

    memberRef.child(profileId + '/chats').push(updatedAskMessage)

    timestamp = int(time.time() * 1000)
    updatedAnswerMessage = {"role": "answer",
                            "content": aiResponse, "timestamp": timestamp}

    memberRef.child(profileId + '/chats').push(updatedAnswerMessage)


@handler.add(PostbackEvent)
def handle_postback(event):
    data = event.postback.data
    dataDict = parse_qsl(data)
    params_dict = {key: value for key, value in dataDict}
    if params_dict['action'] == 'book':
        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text=params_dict['text']))


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
