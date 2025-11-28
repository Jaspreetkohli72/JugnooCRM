
lines = open("app.py", "r", encoding="utf-8").readlines()

# Dedent lines 655 to 806 (indices 654 to 805)
# We want to remove 4 spaces from the beginning of each line.
start_idx = 654
end_idx = 806

for i in range(start_idx, end_idx):
    if lines[i].startswith("    "):
        lines[i] = lines[i][4:]

with open("app.py", "w", encoding="utf-8") as f:
    f.writelines(lines)
print("Dedentation applied.")
