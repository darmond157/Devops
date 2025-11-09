import re

# Define the input and output file paths
input_file = 'logs.txt'
output_file = 'filtered_logs.txt'

# Define the regex pattern to match the timestamp, duration, and statement/execute/parse prefixes
# This will match lines like `execute <unnamed>: SELECT ...`
pattern_1 = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}\s+duration: \d+\.\d+\s+ms\s+(execute|bind|parse)\s*<unnamed>:?\s*'

# Define the regex pattern to match lines with `statement:` (e.g., `DISCARD ALL`, `COMMIT`, etc.)
pattern_2 = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}\s+duration: \d+\.\d+\s+ms\s+statement:\s*(\S+)'

# Open the input file for reading and output file for writing
with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
    for line in infile:
        # Apply regex substitution to remove the timestamp, duration, and handle the statement types
        modified_line = re.sub(pattern_1, '', line)  # Removes execute, bind, parse lines
        modified_line = re.sub(pattern_2, r'\1', modified_line)  # Keeps only the statement part

        # Write the modified line to the output file
        outfile.write(modified_line)

print(f"Filtered content has been written to {output_file}")
