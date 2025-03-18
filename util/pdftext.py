import fitz  # PyMuPDF


def extract_section(pdf_path):
    text_content = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text_content += page.get_text() + " "

    text_content = text_content.replace("\n", " ")

    ref_marker = "References"
    ref_index = text_content.find(ref_marker)
    text_content = text_content[:ref_index]

    return text_content


if __name__ == "__main__":
    pdf_path = "data/downloaded_pdfs/2503.03395.pdf"

    section_text = extract_section(pdf_path)

    with open("extract.txt", "w", encoding="utf-8") as f:
        f.write(section_text)
