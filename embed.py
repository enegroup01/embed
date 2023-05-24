
import pandas as pd
import tiktoken

from openai.embeddings_utils import get_embedding
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import os
import time
import openai


# embedding model parameters
embedding_model = "text-embedding-ada-002"
embedding_encoding = "cl100k_base"  # this the encoding for text-embedding-ada-002
max_tokens = 8000  # the maximum for text-embedding-ada-002 is 8191

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(
    cred, {'databaseURL': 'https://linebot-93aa8-default-rtdb.asia-southeast1.firebasedatabase.app/'})

ref = db.reference('testApiKey/')

while True:
    gptApiKey = ref.get()
    if gptApiKey is not None:
        break
    time.sleep(1)  # Wait for 1 second before checking again
openai.api_key = gptApiKey

input_datapath = 'combined/.csv'
df = pd.read_csv(input_datapath, index_col=0)

df["embedding"] = df.combined.apply(
    lambda x: get_embedding(x, engine=embedding_model))
df.to_csv("model/.csv")
# df.to_csv("chunks/.csv")
