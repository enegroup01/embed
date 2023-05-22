import re
from urllib.parse import urlparse

string = "有的，我們有奶昔。奶昔是用冰淇淋做的，可以參考這個圖片 https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Milk-shake.jpg/900px-Milk-shake.jpg 看看奶昔的樣子。不過奶昔無法做去冰，因為奶昔是用巧克力冰下去打的，無法去冰。如果您對奶昔有興趣，可以參考這個推薦連結 https://eatenjoyforever.com/luna-handmade-dessert/。"
imgString = '有的，我們的龍蝦是青殼龍蝦，產地在澳洲。連在在這：https://eatenjoyforever.com/news/。如果您想知道我們的龍蝦來源，它是從斯里蘭卡進口的。此外，如果您想看到龍蝦的圖片，可以點擊這個連結：https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/Monogrammist_JHV_Still_life_with_a_lobster.jpg/500px-Monogrammist_JHV_Still_life_with_a_lobster.jpg。'
anotherString = '可以的，我們的奶昔推薦連結是 https://eatenjoyforever.com/news/，也可以看看奶昔的圖片 https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Milk-shake.jpg/900px-Milk-shake.jpg。奶昔是用冰淇淋做的，無法做去冰。如果您喜歡甜點，我們的千層蛋糕是客人來必點的，招牌口味是原味香草千層和鐵觀音千層，也推薦榛果巧克力千層。另外，我們有下午茶，牛肉是使用美國的。'
newTest = '請問您要哪一張圖片呢？奶昔的圖片在 https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Milk-shake.jpg/900px-Milk-shake.jpg，龍蝦的圖片在 https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/Monogrammist_JHV_Still_life_with_a_lobster.jpg/500px-Monogrammist_JHV_Still_life_with_a_lobster.jpg。'
# Define the regex pattern to match URLs


def getWebsiteLinks(text):

    # Define the regex pattern to match URLs
    url_pattern = r"(?P<url>https?://[^\s，。]+)"

    # Find all matches of the URL pattern
    matches = re.findall(url_pattern, text)
    website_links = [url for url in matches if not url.endswith(
        ('.png', '.jpg', '.jpeg', '.gif'))]

    print('*==== get only website link')
    print(website_links)


def getOnlyImageLink(text):

    # Define the regex pattern to match the URL
    # url_pattern = r"https?://[^\s]+\.(?:png|jpe?g|gif)(?:/[^\s]*)?"
    url_pattern = r"(?P<url>https?://[^\s，。]+)"

    # Find all matches of the URL pattern
    matches = re.findall(url_pattern, text)

    # Filter the matches to get only the image URL
    image_urls = [url for url in matches if url.endswith(
        ('.png', '.jpg', '.jpeg', '.gif'))]
    print('*==== got only image url')
    print(image_urls)


getWebsiteLinks(newTest)
