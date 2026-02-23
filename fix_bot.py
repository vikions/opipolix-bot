#!/usr/bin/env python
import re

# Read the file
with open('app/bot.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and replace the print line that contains Token balance
for i, line in enumerate(lines):
    if 'Token balance:' in line and 'print(f"' in line:
        # Replace the line
        lines[i] = '            logger.debug(f"Token balance: {token_balance_raw} raw = {token_balance} tokens")\n'
        print(f"Fixed line {i+1}")
        break

# Write back
with open('app/bot.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Done")
