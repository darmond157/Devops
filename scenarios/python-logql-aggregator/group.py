from collections import Counter

topk = 4

# Define the input file path
input_file = 'filtered_logs.txt'

# Initialize a counter to store occurrences of each line
line_counter = Counter()

# Open the input file for reading
with open(input_file, 'r') as infile:
    for line in infile:
        # Skip blank lines
        if not line.strip():
            continue
        
        # Increment the count for the current line
        line_counter[line.strip()] += 1

# Sort the lines by occurrence in descending order and get the top 3
top_3_lines = line_counter.most_common(topk)

# Print the top 3 lines
print("Top 3 most frequent lines:")
for line, count in top_3_lines:
    print(f"{line} =====> {count}")
    print()
