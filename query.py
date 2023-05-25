# imports
import ast  # for converting embeddings saved as strings back to arrays
import openai  # for calling the OpenAI API
import pandas as pd  # for storing text and embeddings data
import tiktoken  # for counting tokens
from scipy import spatial  # for calculating vector similarities for search
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import os
import time
import gradio as gr
import json
import re


cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(
    cred, {'databaseURL': 'https://linebot-93aa8-default-rtdb.asia-southeast1.firebasedatabase.app/'})

ref = db.reference('testApiKey/')
memberRef = db.reference('members/')

while True:
    gptApiKey = ref.get()
    if gptApiKey is not None:
        break
    time.sleep(1)  # Wait for 1 second before checking again
os.environ['OPENAI_API_KEY'] = gptApiKey
openai.api_key = gptApiKey

# models
EMBEDDING_MODEL = "text-embedding-ada-002"
GPT_MODEL = "gpt-3.5-turbo"

embeddings_path = "model/chunksEmbeddedModel.csv"
myProfileId = 'Ued7ae416eb03f3295c1a6600fda84b9e'

df = pd.read_csv(embeddings_path)
df['embedding'] = df['embedding'].apply(ast.literal_eval)


def has_image_link(text):
    pattern = r'\b(?:https?://\S+(?:\.png|\.jpg|\.jpeg|\.gif))\b'
    match = re.search(pattern, text)
    return match is not None


def getOnlyImageLink(text):
    # Define the regex pattern to match the URL
    url_pattern = r"https?://[^\s]+"

    # Find all matches of the URL pattern
    matches = re.findall(url_pattern, text)

    # Filter the matches to get only the image URL
    image_urls = [url for url in matches if url.endswith(
        ('.png', '.jpg', '.jpeg', '.gif'))]
    return image_urls


# search function
def strings_ranked_by_relatedness(
    query: str,
    df: pd.DataFrame,
    relatedness_fn=lambda x, y: 1 - spatial.distance.cosine(x, y),
    top_n: int = 10
) -> tuple[list[str], list[float]]:
    """Returns a list of strings and relatednesses, sorted from most related to least."""
    query_embedding_response = openai.Embedding.create(
        model=EMBEDDING_MODEL,
        input=query,
    )
    print(
        f'{query_embedding_response["usage"]["prompt_tokens"]} embedded tokens counted by the OpenAI API.')

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

# If the answer cannot be found in the information, write "抱歉，這個問題我不清楚，您可以說詳細一點嗎？或是可以詢問餐廳人員。"
# 'Use the below information to answer the subsequent question and in traditional chinese.'


def query_message(
    query: str,
    df: pd.DataFrame,
    model: str,
    token_budget: int
) -> str:
    """Return a message for GPT, with relevant source texts pulled from a dataframe."""
    strings, relatednesses = strings_ranked_by_relatedness(query, df)

    introduction = 'Use the below information to answer the subsequent question in traditional chinese. Be concise'
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
        print('*=======query message')
        print(message)

    messages = [
        {"role": "system", "content": "You are a helpful assistant that helps answer questions about the restaurant. Be concise."}
    ]
    if memberRef.child('Ued7ae416eb03f3295c1a6600fda84b9e').get() is not None:
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
        latest_chats = memberRef.child('Ued7ae416eb03f3295c1a6600fda84b9e' + '/chats').order_by_child(
            'timestamp').limit_to_last(8).get()
        jsonChats = json.dumps(latest_chats)
        data_dict = json.loads(jsonChats)
        print('*===============finish json work================*')
        print(data_dict)

        for _, chat_data in data_dict.items():
            role = chat_data["role"]
            content = chat_data["content"]
            if role == "user":
                messages.append(
                    {"role": "user", "content": content})
            elif role == "assistant":
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
    # else:

    #     uploadProfile(profile=profile)

    messages.append({"role": "user", "content": message})
    print('*===== ask messages:')
    print(messages)
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=0
    )
    print(
        f'{response["usage"]["prompt_tokens"]} prompt tokens counted by the OpenAI API.')

    response_message = response["choices"][0]["message"]["content"]
    # print(response_message)
    uploadConversation(query, myProfileId, response_message)

    print(has_image_link(response_message))
    return response_message
    # return "testing"


def uploadConversation(query, profileId, aiResponse):
    timestamp = int(time.time() * 1000)
    updatedAskMessage = {"role": "user",
                         "content": query, "timestamp": timestamp}
    memberRef.child(profileId + '/chats').push(updatedAskMessage)
    timestamp = int(time.time() * 1000)
    updatedAnswerMessage = {"role": "assistant",
                            "content": aiResponse, "timestamp": timestamp}
    memberRef.child(profileId + '/chats').push(updatedAnswerMessage)


def answerMe(question):
    strings, relatednesses = strings_ranked_by_relatedness(
        question, df, top_n=5)
    for string, relatedness in zip(strings, relatednesses):
        print(f"{relatedness=:.3f}")
        print(string)

    return ask(question, print_message=True)


chatBot = gr.Interface(fn=answerMe, inputs='text', outputs='text')
chatBot.launch(inline=False, share=True)


# query = f"""Use the below article about the restaurant to answer the subsequent question in Traditional Chinese. If the answer cannot be found, write I don't know.

# Article:
# \"\"\"
# {eatEnjoy}
# \"\"\"

# Question: 你們店在哪裡?"""


# response = openai.ChatCompletion.create(
#     messages=[
#         {'role': 'system', 'content': 'Answer question about this restaurant'},
#         {'role': 'user', 'content': query},
#     ],
#     model=GPT_MODEL,
#     temperature=0,
# )

# print(response['choices'][0]['message']['content'])


eatEnjoy = """ 
Q. 你們牛肉用哪的？
A. 美國喔
Q. 你們豬肉用哪的？
A. 台灣豬
Q. 你們龍蝦哪來的？
A. 斯里蘭卡
Q. 你們可以訂位嗎？
A. 可以
Q. 你們有下午茶嗎？
A. 有
Q. 你們推薦什麼餐點？
A. 我們的千層蛋糕是客人來必點
Q. 你們什麼好吃？
A. 都好吃誒看你想吃什麼
Q. 你們千層怎麼那麼貴？
A. 一分錢一分貨
Q. 你們千層自己做的嗎？
A. 對 我們有自己的甜點部門專門在開發生產
Q. 你們店生意好嗎？
A. 好啊 看不出來嗎
Q. 你們用餐有限時嗎? 
A. 90分鐘
Q. 你們上班累嗎？
A. 有客人滿意的笑容,我們都不累當作在play
Q. 店狗為什麼瞎掉？
A. 白內障 老了
Q. 店狗是什麼狗？
A. 法鬥
Q. 千層內餡是用什麼？
A. 卡士達
Q. 店內賣幾種酒? 
A. 2種
Q. 目前有幾家分店? 
A. 2家
Q. 你們有會員嗎? 
A. 有啊ocard
Q. 你們老闆有幾個小孩? 
A. 2個
Q. 你們店長幾歲? 
A. 27
Q. 你們店長是那個男生嗎？
A. 沒戴眼鏡那個
Q. 請寫出菜單上哪幾種餐點(飯/麵)內，不包含”蒜泥”? 
A. 一.  橄欖油時蔬炒飯 二. 松露時蔬炒飯 三.  xo炒飯 四. 南瓜海鮮飯 五. 南瓜烤雞飯 六. 兒童餐
Q. XO醬肉醬燉飯內.蒜頭的部分是在燉飯內還是XO醬? 
A. XO醬
Q. 請問漢堡的生菜內，包含了什麼蔬菜，以及數量為多少? 
A.  一. 酸黃瓜2片 二. 紫洋蔥些許 三. 茄片2片 四. 羅蔓or美生菜
Q. 請問店內素食餐點有哪些? 
A.  一. 時蔬炒飯/麵 二. 瑪披 三. 松披 四. 炒野菇 五. 薯條 六. 時蔬沙拉
Q. 店內所有餐點都可以做不辣嗎? 
A. 大部分都可以，不能的餐點為:  炙燒牛五花辣椒捲(開胃菜)，炙燒鮭魚生干貝佐南洋紅咖哩燉飯，舒肥雞(蒜辣)
Q. 餐點擺盤上，綠色的葉子/像樹枝的東西/紅色的絲，分別是什麼
A. 綠色的葉子:綠捲，像樹枝的東西:炸麵條，紅色的絲:辣椒絲
Q. 凡是海鮮類的餐點，必定會加什麼東西去腥味?
A. 白酒
Q. 兒童餐內，是否有包含蒜泥成分?
A. 否(只有洋泥)
Q. 六種早午餐中，餐點必定包含哪四種配料?
A. 一. 麵包 二. 沙拉 三. 薯塊 四. 蛋
Q. 早午餐中，哪兩種餐點只需要選飲料?
A. 明太子炙燒鮭魚可頌, 醬燒豬五花可頌
Q. 開胃菜中四種沙拉的醬分別為什麼?小點內時蔬沙拉醬汁又為何?
A. 凱薩烤雞:凱薩醬, 炙燒牛肉:胡麻醬 ,鮮蝦培根:胡麻醬 ,時蔬沙拉:蜂蜜芥末
Q. 請問蒜香炸雞，雞肉的部位為何?一份有多少呢?旁邊的醬又是什麼?
A. 雞胸肉 250克 甜雞醬
Q. 炙燒牛五花捲及BBQ燒烤雞翅一份各有幾隻?
A. 炙燒牛五花捲:6捲, BBQ燒烤雞翅:6隻
Q. 脆醬薯條份量為190克, 起司肉醬薯條及奶油松露薯條分量為幾克?
A. 薯條一份為190克, 起司肉醬薯條及奶油松露薯條皆為1.5份 285克
Q. 小點中，酥炸洋蔥圈份量為多少?
A. 一份為8個
Q. 店內牛肉產品中，肉品來源皆為?
A. 美國
Q. 炭烤無骨牛小排/炭烤牛小排奶油松露燉飯/最強炭烤牛小排早午餐 肉的部分分別為幾盎司呢?一般建議為幾分熟?
A. 8盎司/4盎司/4盎司, 5分熟
Q. 請寫出下列主食一份的數量或內含物。 
A. 牛肉漢堡排:一片(全牛), 骰子牛:90克, 松阪豬:5~6片, 牛五花:3~4片, 碳烤雞腿:一片, 蝦子(白蝦):5隻, 海鮮料:蝦3隻 魚肉 , 淡菜一個 蟹管 蛤蠣3 ,鮭魚:四片  干貝:一顆, 炸物拼盤:蒜香炸雞，洋蔥圈, 薯條，杏鮑菇
Q. 店內使用豬肉及龍蝦產地為何?
A. 豬肉:台灣, 龍蝦:澳洲
Q. 菜單上什麼餐點需要等待時間較長?時間分別為多久?
A. 鱸魚麵:25~30分, 龍蝦麵: 25~30分, 舒肥雞麵/飯: 25~30分, 牛小排(排餐/飯/早午餐):20分, 豬腳: 30分, 辣味脆雞披撒: 25~30分
Q. 飲料中，哪幾種飲料含咖啡因
A. 濃縮/美式/拿鐵/卡布/抹茶拿鐵/鐵觀音拿鐵/水果茶/鮮煮奶茶/貝里斯奶茶
Q. 奶昔是用什麼做的?
A. 冰淇淋
Q. 單點飲料中，哪幾種飲料可以製作無糖?
A. 濃縮/美式/拿鐵(原味)/卡布/葡萄柚汁/奇異果汁/奇異蘋果汁, 其餘飲料最低製作至半糖(冰沙奶昔類生啤類不可調整)
Q. 水果茶/鮮煮奶茶/貝里斯奶茶/鮮榨果汁類中，加的糖為什麼糖?
A. 鳳梨糖漿/黑糖/黑糖/蜂蜜
Q. 甜點菜單連結
A. https://drive.google.com/file/d/10ahQogwAwM_FWiy4DIeE7c3Enr9wDfZc/view?usp=sharing
Q. 我該如何預留訂購甜點呢?
A. https://lin.ee/zoef18D
Q. 請問蛋糕有提供什麼尺寸?
A. 6吋和9吋
Q. 有無開放甜點外帶的服務?
A. 甜點提供單純「外帶」和「內用」的服務，務必提前一天詢問並預留，當日「一律不提供預留」，僅提供現場挑選購買的服務。
Q. 請問我可以購買切片蛋糕拼成一模嗎?
A. 可以，一模蛋糕需挑選8~10切片即可拼成一個圓，需另外酌收$80包材費用，連結是https://drive.google.com/file/d/10ahQogwAwM_FWiy4DIeE7c3Enr9wDfZc/view
Q. 切片蛋糕如何預訂?
A. 如需切片小蛋糕需要依循我們當日有提供的口味來做挑選，因為每天提供的菜單口味不一樣。預留完成後務必先匯款訂單才會成立。
Q. 蛋糕需要多久前預訂?
A. 需要3~7天前事先預訂
Q. 現場是否有販售整模蛋糕
A. 店內僅提供切片蛋糕販售，不會提供整模蛋糕的販售
Q. 蛋糕的保存期限為幾天?
A. 冷藏3天，包含取貨當天
Q. 蛋糕是否需要冷藏保存?
A. 室溫保存僅30分鐘為限，務必放置冷藏保存
Q. 蛋糕是否可以冷凍保存?
A. 不可以，冷凍會影響蛋糕口感
Q. 蛋糕是否可以宅配寄送?
A. 宅配部分可能會需要承擔些許風險，因為我們是和黑貓宅急便配合，他們僅提供配送服務，但不會承擔配送品質。不過包裝部分我們一定會盡可能去保護蛋糕，但收到的樣貌可能還是跟店內享用到的會有落差
Q. 請問你們餐廳的位置在哪裡?
A. 林口以及新店
Q. 請問你們林口店的在哪裡?
A. 林口店, 新北市林口區文化三路一段390-1（三井outlet旁邊，機場捷運A9站）. 
Q. 請問你們新店店的在哪裡?
A. 新店店, 新北市新店區北新路一段88巷9號（新店區公所捷運站2號出口旁邊巷子）
Q. 慶生時可以自己帶蛋糕來嗎？ 
A. 可以，但是慶生結束後要把蛋糕帶走。


"""
