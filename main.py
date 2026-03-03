from src.scipdf_parser import PDFParser

p = PDFParser("data/prospective_2_RCT.pdf")
print(p.title)
print(p.abstract)
methods = p.get_section("methods")
print(p.summary())
