import csv

input_datapath = "eatEnjoy.csv"
output_file = 'combined.csv'

with open(input_datapath, 'r') as infile, open(output_file, 'w', newline='') as outfile:
    reader = csv.DictReader(infile)
    fieldnames = reader.fieldnames + ['combined']
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    for row in reader:
        question = row['question']
        answer = row['answer']
        combined = f"question: {question}; answer: {answer}"
        row['combined'] = combined
        writer.writerow(row)
