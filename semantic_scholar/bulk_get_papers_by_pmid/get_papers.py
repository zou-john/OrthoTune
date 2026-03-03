#!/usr/bin/env python3
import dotenv
dotenv.load_dotenv()

import argparse
import csv
import os
from requests import Session
from typing import Generator, TypeVar, Union

import urllib3
urllib3.disable_warnings()

S2_API_KEY = os.environ.get('S2_API_KEY', '')

T = TypeVar('T')
def get_paper(session: Session, paper_id: str, fields: str = 'paperId,title', **kwargs) -> dict:
    params = {
        'fields': fields,
        **kwargs,
    }
    headers = {
        'X-API-KEY': S2_API_KEY,
    }

    with session.get(f'https://api.semanticscholar.org/graph/v1/paper/{paper_id}', params=params, headers=headers) as response:
        response.raise_for_status()
        return response.json()


def download_pdf(session: Session, url: str, path: str, user_agent: str = 'requests/2.0.0'):
    # send a user-agent to avoid server error
    headers = {
        'user-agent': user_agent,
    }

    # stream the response to avoid downloading the entire file into memory
    with session.get(url, headers=headers, stream=True, verify=False) as response:
        # check if the request was successful
        response.raise_for_status()

        if response.headers['content-type'] != 'application/pdf':
            raise Exception('The response is not a pdf')

        with open(path, 'wb') as f:
            # write the response to the file, chunk_size bytes at a time
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)


def download_paper(session: Session, paper_id: str, directory: str = 'papers', user_agent: str = 'requests/2.0.0') -> Union[str, None]:
    paper = get_paper(session, paper_id, fields='paperId,isOpenAccess,openAccessPdf')

    # check if the paper is open access
    if not paper['isOpenAccess']:
        return None

    if paper['openAccessPdf'] is None:
        return None

    paperId: str = paper['paperId']
    pdf_url: str = paper['openAccessPdf']['url']
    pdf_path = os.path.join(directory, f'{paperId}.pdf')

    # create the directory if it doesn't exist
    os.makedirs(directory, exist_ok=True)

    # check if the pdf has already been downloaded
    if not os.path.exists(pdf_path):
        download_pdf(session, pdf_url, pdf_path, user_agent=user_agent)

    return pdf_path


def download_papers(paper_ids: list[str], directory: str = 'papers', user_agent: str = 'requests/2.0.0') -> Generator[tuple[str, Union[str, None, Exception]], None, None]:
    # use a session to reuse the same TCP connection
    with Session() as session:
        for paper_id in paper_ids:
            try:
                yield paper_id, download_paper(session, paper_id, directory=directory, user_agent=user_agent)
            except Exception as e:
                yield paper_id, e
def batched(items: list[T], batch_size: int) -> list[T]:
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]


def get_paper_batch(session: Session, ids: list[str], fields: str = 'paperId,title', **kwargs) -> list[dict]:
    params = {
        'fields': fields,
        **kwargs,
    }
    headers = {
        'X-API-KEY': S2_API_KEY,
    }
    body = {
        'ids': ids,
    }

    # https://api.semanticscholar.org/api-docs/graph#tag/Paper-Data/operation/post_graph_get_papers
    with session.post('https://api.semanticscholar.org/graph/v1/paper/batch',
                       params=params,
                       headers=headers,
                       json=body) as response:
        response.raise_for_status()
        return response.json()


def get_papers(ids: list[str], batch_size: int = 100, **kwargs) -> Generator[dict, None, None]:
    # use a session to reuse the same TCP connection
    with Session() as session:
        # take advantage of S2 batch paper endpoint
        for ids_batch in batched(ids, batch_size=batch_size):
            yield from get_paper_batch(session, ids_batch, **kwargs)


def main(args: argparse.Namespace) -> None:
    with open(args.pmid_file, 'r') as pmid_file:
        pmids = [line.strip() for line in pmid_file.readlines()]

    count = 0
    paper_ids = []
    with open(args.output, 'w') as csvfile:
        fieldnames = ['pmid', 'title', 'first_author', 'year', 'abstract', 'ss_id']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        ids = [f'PMID:{pmid}' for pmid in pmids]
        fields = 'externalIds,title,authors,year,abstract'

        for paper in get_papers(ids, fields=fields):
            # If an ID is not found, the corresponding entry in the response will be null.
            if not paper:
                continue

            paper_authors = paper.get('authors', [])
            writer.writerow({
                'pmid': paper['externalIds']['PubMed'],
                'title': paper['title'],
                'first_author': paper_authors[0]['name'] if paper_authors else '<no_author_data>',
                'year': paper['year'],
                'abstract': paper['abstract'],
                'ss_id' : paper['paperId'],
            })
            paper_ids.append(paper['paperId'])
            count += 1

    print(f'Wrote {count} results to {args.output}')

    for paper_id, result in download_papers(paper_ids, directory='pdfs', user_agent='requests/2.0.0'):
        if isinstance(result, Exception):
            print(f"Failed to download '{paper_id}': {type(result).__name__}: {result}")
        elif result is None:
            print(f"'{paper_id}' is not open access")
        else:
            print(f"Downloaded '{paper_id}' to '{result}'")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', '-o', default='papers.csv')
    parser.add_argument('pmid_file', nargs='?', default='semantic_scholar/bulk_get_papers_by_pmid/test_pmids_small.txt')
    args = parser.parse_args()
    main(args)
