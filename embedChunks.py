import pandas as pd  # for DataFrames to store article sections and embeddings


path_1 = "chunks/myEmbeddedModel1-2.csv"
path_2 = "chunks/myEmbeddedModel2-2.csv"


df1 = pd.read_csv(path_1)
df2 = pd.read_csv(path_2)

combined_df = pd.concat([df1, df2], ignore_index=True)
combined_df.to_csv("model/wholeEmbed.csv", index=False)
