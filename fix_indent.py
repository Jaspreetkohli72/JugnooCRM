
lines = open("app.py", "r", encoding="utf-8").readlines()

# Indent lines 606 to 806 (indices 605 to 805)
start_idx = 605
end_idx = 806

for i in range(start_idx, end_idx):
    # Only indent if the line is not empty, or indent everything?
    # Better to indent everything to maintain structure, even empty lines (though trailing whitespace is annoying, it's safe).
    # But let's check if line is just newline.
    if lines[i].strip():
        lines[i] = "    " + lines[i]
    # If it's just a newline, we can leave it or indent it. Streamlit doesn't care.
    # But if it's inside a string, we must be careful.
    # These are code lines, so indenting is correct.

with open("app.py", "w", encoding="utf-8") as f:
    f.writelines(lines)
print("Indentation applied.")
