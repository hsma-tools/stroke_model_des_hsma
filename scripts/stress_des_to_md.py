from pathlib import Path
import pandas as pd

# Paths
excel_path = Path("checklists/stress_des.xlsx")
output_md = Path("docs/stress_des.md")

# Read Excel
df = pd.read_excel(excel_path, skiprows=3).fillna("")

# Replace line breaks inside cells
df = df.map(
    lambda x: str(x).replace("\r\n", "<br>").replace("\n", "<br>") if pd.notna(x) else x
)

# Generate Markdown
markdown_table = df[
    ["Section/Subsection", "Item", "Recommendation", "Details"]
].to_markdown(index=False)

# Optional header / intro text
content = f"""---
hide:
  - toc
---

# Stress DES Checklist

This table is auto-generated from `checklists/{excel_path.name}`.

{markdown_table}
"""

# Write output
output_md.write_text(content, encoding="utf-8")
