import scipdf


class PDFParser:
    """Wrapper around scipdf_parser for structured extraction of scientific PDFs.

    Requires a running GROBID service (default: http://localhost:8070).
    Start it with: bash serve_grobid.sh
    """

    def __init__(self, pdf_path: str, as_list: bool = False):
        """
        Args:
            pdf_path: Path to a local PDF file or a direct URL to a PDF.
            as_list:  If True, section text is returned as a list of paragraphs
                      rather than a single string.
        """
        self.pdf_path = pdf_path
        self.as_list = as_list
        self._data: dict | None = None

    # ------------------------------------------------------------------
    # Lazy-loaded parsed data
    # ------------------------------------------------------------------

    @property
    def data(self) -> dict:
        """Parse the PDF on first access and cache the result."""
        if self._data is None:
            self._data = scipdf.parse_pdf_to_dict(self.pdf_path, as_list=self.as_list)
        return self._data

    def parse(self) -> "PDFParser":
        """Explicitly trigger parsing (useful for early error detection).

        Returns self to allow chaining: parser = PDFParser(...).parse()
        """
        _ = self.data
        return self

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    @property
    def title(self) -> str:
        return self.data.get("title", "")

    @property
    def abstract(self) -> str:
        return self.data.get("abstract", "")

    @property
    def sections(self) -> list[dict]:
        """List of {'heading': str, 'text': str} dicts."""
        return self.data.get("sections", [])

    @property
    def references(self) -> list[dict]:
        """List of {'title', 'year', 'journal', 'author'} dicts."""
        return self.data.get("references", [])

    @property
    def figures(self) -> list[dict]:
        """List of {'figure_label', 'figure_type', 'figure_id',
        'figure_caption', 'figure_data'} dicts."""
        return self.data.get("figures", [])

    @property
    def doi(self) -> str:
        return self.data.get("doi", "")

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def full_text(self, separator: str = "\n\n") -> str:
        """Return the full body text (all sections concatenated).

        Args:
            separator: String inserted between sections.
        """
        parts = []
        for section in self.sections:
            heading = section.get("heading", "")
            text = section.get("text", "")
            if isinstance(text, list):
                text = " ".join(text)
            if heading:
                parts.append(f"{heading}\n{text}")
            else:
                parts.append(text)
        return separator.join(parts)

    def get_section(self, heading_query: str, case_sensitive: bool = False) -> dict | None:
        """Find the first section whose heading contains *heading_query*.

        Args:
            heading_query:  Substring to search for in section headings.
            case_sensitive: Whether the match is case-sensitive.

        Returns:
            The matching section dict, or None if not found.
        """
        query = heading_query if case_sensitive else heading_query.lower()
        for section in self.sections:
            heading = section.get("heading", "")
            target = heading if case_sensitive else heading.lower()
            if query in target:
                return section
        return None

    def summary(self) -> str:
        """Return a brief human-readable summary of the parsed document."""
        lines = [
            f"Title    : {self.title}",
            f"DOI      : {self.doi}",
            f"Abstract : {self.abstract[:200]}{'...' if len(self.abstract) > 200 else ''}",
            f"Sections : {len(self.sections)}",
            f"References: {len(self.references)}",
            f"Figures  : {len(self.figures)}",
        ]
        return "\n".join(lines)

    def __repr__(self) -> str:
        parsed = "parsed" if self._data is not None else "unparsed"
        return f"PDFParser(pdf_path={self.pdf_path!r}, {parsed})"
