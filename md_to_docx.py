import pypandoc
import sys

if len(sys.argv) < 3:
    print("Usage: python md_to_docx.py <input.md> <output.docx>")
    sys.exit(1)

input_file = sys.argv[1]
output_file = sys.argv[2]

try:
    print("Checking for pandoc...")
    pypandoc.get_pandoc_version()
except Exception:
    print("Pandoc not found, downloading...")
    pypandoc.download_pandoc()

print(f"Converting {input_file} to {output_file}...")
pypandoc.convert_file(input_file, 'docx', outputfile=output_file)
print("Conversion successful.")
