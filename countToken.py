import tiktoken
import csv


def num_tokens_from_string(string: str, encoding_name: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens
# print(num_tokens_from_string("tiktoken is great!", "cl100k_base"))


def countFromCSV():
    total_tokens = 0
    with open('combinedOnly.csv', 'r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            text = row['combined']
            encoding = tiktoken.get_encoding('cl100k_base')
            num_tokens = len(encoding.encode(text))
            total_tokens += num_tokens
        print(f"Total tokens: {total_tokens}")


countFromCSV()
