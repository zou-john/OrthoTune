from semanticscholar import SemanticScholar

sch = SemanticScholar()

results = sch.search_paper(query="Orthopedics", year=2025, limit=2, 
                 publication_types=["JournalArticle"], 
                 open_access_pdf=True, fields_of_study=["Medicine"],
                 )
all_results = [item for item in results]

print("Search results: ", len(all_results))