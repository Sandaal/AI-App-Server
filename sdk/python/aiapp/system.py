"""Built-in system handlers run by the core's own worker (app "aiapp-system").

``parse`` extracts text for ingestion: PDF (pypdf) and, with the standard
library only, DOCX, PPTX (one page per slide), XLSX (one page per sheet),
HTML, CSV and EML (email). Zip parts are read with a size cap, so a
crafted file can't exhaust memory.

``presidio`` redacts named entities (people, places, ...) with Microsoft
Presidio for the presidio guardrail. It needs ``pip install
presidio-analyzer presidio-anonymizer`` and a spaCy model (``python -m
spacy download en_core_web_sm``) in the server's Python.
"""

from __future__ import annotations

import csv
import email
import threading
import email.policy
import io
import re
import zipfile
from html.parser import HTMLParser
from xml.etree import ElementTree

from aiapp.request import Request

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class ParseError(Exception):
    pass


def parse_pdf(data: bytes) -> list[dict]:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise ParseError("PDF support needs pypdf: pip install 'aiapp[ingest]'") from e
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as e:
            raise ParseError("PDF is password-protected") from e
    return [{"page": i + 1, "text": page.extract_text() or ""} for i, page in enumerate(reader.pages)]


def parse_docx(data: bytes) -> list[dict]:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            xml = z.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError) as e:
        raise ParseError("not a valid .docx file") from e
    root = ElementTree.fromstring(xml)
    paragraphs = []
    for p in root.iter(W + "p"):
        parts = []
        for node in p.iter():
            if node.tag == W + "t" and node.text:
                parts.append(node.text)
            elif node.tag == W + "tab":
                parts.append("\t")
            elif node.tag in (W + "br", W + "cr"):
                parts.append("\n")
        paragraphs.append("".join(parts))
    text = "\n\n".join(p for p in paragraphs if p.strip())
    return [{"page": 0, "text": text}]


MAX_PART = 50 << 20  # decompressed bytes read from one zip member
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _zip_read(z: zipfile.ZipFile, name: str) -> bytes:
    info = z.getinfo(name)
    if info.file_size > MAX_PART:
        raise ParseError(f"{name} is too large to read")
    with z.open(info) as f:
        data = f.read(MAX_PART + 1)
    if len(data) > MAX_PART:
        raise ParseError(f"{name} is too large to read")
    return data


def _num(name: str) -> int:
    m = re.search(r"(\d+)\.xml$", name)
    return int(m.group(1)) if m else 0


def parse_pptx(data: bytes) -> list[dict]:
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as e:
        raise ParseError("not a valid .pptx file") from e
    with z:
        slides = sorted((n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)), key=_num)
        if not slides:
            raise ParseError("not a valid .pptx file (no slides)")
        pages = []
        for n in slides:
            root = ElementTree.fromstring(_zip_read(z, n))
            paras = []
            for p in root.iter(A + "p"):
                text = "".join(t.text or "" for t in p.iter(A + "t"))
                if text.strip():
                    paras.append(text)
            notes = f"ppt/notesSlides/notesSlide{_num(n)}.xml"
            if notes in z.namelist():
                nroot = ElementTree.fromstring(_zip_read(z, notes))
                note = " ".join(t.text or "" for t in nroot.iter(A + "t")).strip()
                if note and not note.isdigit():
                    paras.append("Notes: " + note)
            pages.append({"page": _num(n), "text": "\n".join(paras)})
        return pages


def parse_xlsx(data: bytes) -> list[dict]:
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as e:
        raise ParseError("not a valid .xlsx file") from e
    with z:
        names = z.namelist()
        shared = []
        if "xl/sharedStrings.xml" in names:
            for si in ElementTree.fromstring(_zip_read(z, "xl/sharedStrings.xml")).iter(S + "si"):
                shared.append("".join(t.text or "" for t in si.iter(S + "t")))
        titles = {}
        if "xl/workbook.xml" in names:
            for i, sh in enumerate(ElementTree.fromstring(_zip_read(z, "xl/workbook.xml")).iter(S + "sheet"), start=1):
                titles[i] = sh.get("name", f"Sheet{i}")
        sheets = sorted((n for n in names if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)), key=_num)
        if not sheets:
            raise ParseError("not a valid .xlsx file (no sheets)")
        pages = []
        for n in sheets:
            rows = []
            for row in ElementTree.fromstring(_zip_read(z, n)).iter(S + "row"):
                cells = []
                for c in row.iter(S + "c"):
                    v = c.find(S + "v")
                    if c.get("t") == "s" and v is not None and v.text and v.text.isdigit() and int(v.text) < len(shared):
                        cells.append(shared[int(v.text)])
                    elif c.get("t") == "inlineStr":
                        cells.append("".join(t.text or "" for t in c.iter(S + "t")))
                    else:
                        cells.append(v.text if v is not None and v.text else "")
                if any(x.strip() for x in cells):
                    rows.append("\t".join(cells))
                if len(rows) >= 20_000:
                    break
            title = titles.get(_num(n), f"Sheet{_num(n)}")
            pages.append({"page": _num(n), "text": f"# {title}\n" + "\n".join(rows)})
        return pages


class _TextHTML(HTMLParser):
    BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "header",
             "footer", "table", "ul", "ol", "pre", "blockquote", "title"}
    SKIP = {"script", "style", "noscript", "template", "svg", "nav"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag in self.BLOCK:
            self.out.append("\n")
        if tag in ("h1", "h2", "h3") and not self.skip:
            self.out.append("#" * int(tag[1]) + " ")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def html_text(markup: str) -> str:
    p = _TextHTML()
    p.feed(markup)
    text = re.sub(r"[ \t\r\f\v]+", " ", "".join(p.out))
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def parse_html(data: bytes) -> list[dict]:
    return [{"page": 0, "text": html_text(data.decode("utf-8", errors="replace"))}]


def parse_csv(data: bytes) -> list[dict]:
    text = data.decode("utf-8-sig", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.reader(io.StringIO(text), dialect))
    if not rows:
        return [{"page": 0, "text": ""}]
    header, lines = rows[0], []
    for r in rows[1:50_001]:
        # "column: value" keeps each row's meaning when it lands in a chunk on its own.
        lines.append("; ".join(f"{h}: {v}" for h, v in zip(header, r) if str(v).strip()))
    return [{"page": 0, "text": "\n".join(lines) if lines else ", ".join(header)}]


def parse_eml(data: bytes) -> list[dict]:
    msg = email.message_from_bytes(data, policy=email.policy.default)
    head = [f"{k}: {msg[k]}" for k in ("Subject", "From", "To", "Cc", "Date") if msg[k]]
    body = msg.get_body(preferencelist=("plain", "html"))
    text = ""
    if body is not None:
        content = body.get_content()
        text = html_text(content) if body.get_content_type() == "text/html" else content
    attachments = [a.get_filename() for a in msg.iter_attachments() if a.get_filename()]
    if attachments:
        head.append("Attachments: " + ", ".join(attachments))
    return [{"page": 0, "text": "\n".join(head) + "\n\n" + text.strip()}]


PARSERS = {"pdf": parse_pdf, "docx": parse_docx, "pptx": parse_pptx, "xlsx": parse_xlsx,
           "html": parse_html, "htm": parse_html, "csv": parse_csv, "eml": parse_eml}


def parse(req: Request) -> dict:
    name = req.headers.get("x-aiapp-filename", "")
    ext = re.sub(r"^.*\.", "", name.lower()) if "." in name else ""
    parser = PARSERS.get(ext)
    if parser is None:
        raise ParseError(f"unsupported file type: {name!r}")
    return {"pages": parser(req.body)}


# --- presidio ------------------------------------------------------------------

_analyzers: dict = {}
_analyzer_lock = threading.Lock()

PRESIDIO_HELP = ("Presidio is not installed in the server's Python: pip install presidio-analyzer "
                 "presidio-anonymizer, then python -m spacy download {model}")


def _analyzer(model: str, language: str):
    key = (model, language)
    with _analyzer_lock:
        if key not in _analyzers:
            from presidio_analyzer import AnalyzerEngine
            from presidio_analyzer.nlp_engine import NlpEngineProvider

            nlp = NlpEngineProvider(nlp_configuration={
                "nlp_engine_name": "spacy", "models": [{"lang_code": language, "model_name": model}]}).create_engine()
            _analyzers[key] = AnalyzerEngine(nlp_engine=nlp, supported_languages=[language])
        return _analyzers[key]


def presidio(req: Request) -> dict:
    """{"texts", "entities", "score", "language", "model"} -> {"texts" (redacted), "entities": {TYPE: count}}"""
    b = req.json() or {}
    model, language = b.get("model") or "en_core_web_sm", b.get("language") or "en"
    try:
        analyzer = _analyzer(model, language)
        from presidio_anonymizer import AnonymizerEngine
        from presidio_anonymizer.entities import OperatorConfig
    except (ImportError, OSError) as e:  # OSError: the spaCy model isn't downloaded
        return {"error": PRESIDIO_HELP.format(model=model) + f" ({type(e).__name__}: {e})"}
    anonymizer = AnonymizerEngine()
    entities, score = b.get("entities") or None, float(b.get("score") or 0.5)
    out, counts = [], {}
    for text in b.get("texts") or []:
        if not text or not text.strip():
            out.append(text)
            continue
        found = [r for r in analyzer.analyze(text=text, entities=entities, language=language) if r.score >= score]
        if not found:
            out.append(text)
            continue
        for r in found:
            counts[r.entity_type] = counts.get(r.entity_type, 0) + 1
        ops = {r.entity_type: OperatorConfig("replace", {"new_value": f"[{r.entity_type}]"}) for r in found}
        out.append(anonymizer.anonymize(text=text, analyzer_results=found, operators=ops).text)
    return {"texts": out, "entities": counts}
