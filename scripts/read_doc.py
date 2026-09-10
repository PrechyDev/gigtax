"""
Reads the .docx file and saves all text to output.txt
Run from Implementation folder:
    poetry install
    poetry run python read_doc.py
"""

from docx import Document

doc_path = r"c:\Users\HP\Desktop\Final year project\Precious_chapter_one_to_three.docx"
output_path = r"c:\Users\HP\Desktop\Final year project\doc_output.txt"

print(f"Opening: {doc_path}")
doc = Document(doc_path)

lines = []
for i, para in enumerate(doc.paragraphs):
    if para.text.strip():
        lines.append(para.text)

full_text = "\n".join(lines)

with open(output_path, "w", encoding="utf-8") as f:
    f.write(full_text)

print(f"Done! Total paragraphs: {len(lines)}")
print(f"Total characters: {len(full_text)}")
print(f"Saved to: {output_path}")
