import requests
import os
import re
from bs4 import BeautifulSoup

PMC_ID_CONVERTER = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"


def pmid_to_pmcid(pmid):
    params = {"ids": pmid, "format": "json"}
    r = requests.get(PMC_ID_CONVERTER, params=params)
    r.raise_for_status()

    data = r.json()
    records = data.get("records", [])

    if records and "pmcid" in records[0]:
        return records[0]["pmcid"]

    return None


def find_pdf_link(pmcid):

    article_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/"

    headers = {"User-Agent": "Mozilla/5.0"}

    r = requests.get(article_url, headers=headers)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    for link in soup.find_all("a", href=True):
        if ".pdf" in link["href"]:
            pdf_url = link["href"]

            if pdf_url.startswith("/"):
                pdf_url = "https://www.ncbi.nlm.nih.gov" + pdf_url

            return pdf_url

    return None


def download_pdf(pmcid, path):

    headers = {"User-Agent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Accept-Language": "en-US,en;q=0.9"
    })
    article_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/"
    r = session.get(article_url)
    r.raise_for_status()

    with open(path, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)


def download_from_pmid(pmid, out_dir="pmc_pdfs"):

    os.makedirs(out_dir, exist_ok=True)

    pmcid = pmid_to_pmcid(pmid)

    if not pmcid:
        print(f"No PMC version for PMID {pmid}")
        return

    pdf_url = find_pdf_link(pmcid)

    if not pdf_url:
        print(f"No PDF found for {pmcid}")
        return

    path = os.path.join(out_dir, f"{pmcid}.pdf")

    download_pdf(pmcid, path)

    print(f"Downloaded {pmcid}")

if __name__ == "__main__":

    with open("get_pdf_pmc/test_pmids_small.txt") as f:
        pmids = [line.strip() for line in f]

    for pmid in pmids:
        download_from_pmid(pmid)