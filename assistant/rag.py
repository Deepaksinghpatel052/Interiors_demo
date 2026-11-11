"""Retrieval for the assistants: chunking, BM25 index (rank-bm25) and retrieval filtered by audience.

The index is built in memory per audience and rebuilt whenever the knowledge base changes
(a version number in the cache is bumped on every save/delete, so all processes notice).
"""
import io
import re
import threading
from dataclasses import dataclass

from django.core.cache import cache
from rank_bm25 import BM25Okapi

from .models import KnowledgeChunk, KnowledgeDocument

CHUNK_SIZE = 800
CHUNK_OVERLAP = 160
TOP_K = 5
VERSION_KEY = "kb_index_version"
MAX_EXTRACT_CHARS = 200_000
MAX_PDF_PAGES = 60

STOPWORDS = set("""
a an and are as at be been but by can could do does did for from had has have how i if in into is it its me my of on or our
should so than that the their them then there these they this to was we were what when where which who why will with would you
your yours us about also any all just more most much very please tell know want need get like one some
""".split())

_lock = threading.Lock()
_indexes = {}  # audience -> (version, bm25, chunks)
_local_version = [0]  # in-process counter (also works when the cache is a dummy, e.g. in tests)


# ------------------------------------------------------------------------------ text helpers
def normalize_token(tok: str) -> str:
    """Tiny stemmer so 'warranties'/'warranty', 'payments'/'payment', 'designed'/'design' match."""
    if len(tok) > 5 and tok.endswith("ies"):
        return tok[:-3] + "y"                       # warranties -> warranty
    if len(tok) > 5 and tok.endswith(("sses", "xes", "zes", "ches", "shes")):
        return tok[:-2]                             # finishes -> finish, boxes -> box
    if len(tok) > 6 and tok.endswith("ing"):
        return tok[:-3]                             # designing -> design
    if len(tok) > 5 and tok.endswith("ed") and not tok.endswith("eed"):
        return tok[:-2]                             # designed -> design
    if len(tok) > 3 and tok.endswith("s") and not tok.endswith(("ss", "us", "is")):
        return tok[:-1]                             # wardrobes -> wardrobe, payments -> payment
    return tok


def tokenize(text: str):
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return [normalize_token(w) for w in words if w not in STOPWORDS and len(w) > 1]


def chunk_text(text: str, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split into ~size-char chunks on paragraph/sentence boundaries, with overlap between neighbours."""
    text = re.sub(r"[ \t]+", " ", (text or "").replace("\r", "")).strip()
    if not text:
        return []
    pieces = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        if len(para) <= size:
            pieces.append(para)
        else:
            pieces.extend(s.strip() for s in re.split(r"(?<=[.!?])\s+", para) if s.strip())
    chunks, current = [], ""
    for piece in pieces:
        while len(piece) > size:  # a single very long sentence
            chunks.append((current + " " + piece[:size]).strip() if current else piece[:size])
            current, piece = "", piece[size - overlap:]
        if current and len(current) + len(piece) + 1 > size:
            chunks.append(current)
            tail = current[-overlap:]
            tail = tail[tail.find(" ") + 1:] if " " in tail else tail
            current = f"{tail} {piece}".strip()
        else:
            current = f"{current}\n{piece}".strip() if current else piece
    if current:
        chunks.append(current)
    return chunks


def extract_file_text(django_file) -> str:
    """Text from an uploaded PDF or TXT (never executed, only read)."""
    name = (django_file.name or "").lower()
    django_file.open("rb")
    try:
        data = django_file.read()
    finally:
        django_file.close()
    if name.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        parts = []
        for page in reader.pages[:MAX_PDF_PAGES]:
            parts.append(page.extract_text() or "")
            if sum(map(len, parts)) > MAX_EXTRACT_CHARS:
                break
        return "\n\n".join(parts)[:MAX_EXTRACT_CHARS]
    return data.decode("utf-8", errors="ignore")[:MAX_EXTRACT_CHARS]


# ------------------------------------------------------------------------------ indexing
def bump_version():
    _local_version[0] += 1
    try:
        cache.incr(VERSION_KEY)
    except ValueError:
        cache.set(VERSION_KEY, 1, None)


def _current_version():
    return (cache.get(VERSION_KEY) or 0, _local_version[0])


def index_document(doc: KnowledgeDocument):
    """(Re)build the chunks for one document."""
    text = doc.content or ""
    if doc.file and not text.strip():
        try:
            text = extract_file_text(doc.file)
        except Exception:  # unreadable file: keep the document, no chunks
            text = ""
    KnowledgeChunk.objects.filter(document=doc).delete()
    header = f"{doc.title}\n"
    KnowledgeChunk.objects.bulk_create([
        KnowledgeChunk(document=doc, index=i, text=(header + c) if i == 0 else c)
        for i, c in enumerate(chunk_text(text))
    ])
    bump_version()


def reindex_all():
    count = 0
    for doc in KnowledgeDocument.objects.all():
        index_document(doc)
        count += 1
    return count


def _audiences_for(audience):
    return [KnowledgeDocument.Audience.PUBLIC] if audience == "public" else [KnowledgeDocument.Audience.PUBLIC,
                                                                            KnowledgeDocument.Audience.INTERNAL]


def _get_index(audience):
    version = _current_version()
    cached = _indexes.get(audience)
    if cached and cached[0] == version:
        return cached[1], cached[2]
    with _lock:
        chunks = list(KnowledgeChunk.objects.filter(document__is_active=True,
                                                    document__audience__in=_audiences_for(audience))
                      .select_related("document").order_by("document_id", "index"))
        corpus = [tokenize(c.text) for c in chunks]
        for c, toks in zip(chunks, corpus):
            c.token_set = set(toks)
        bm25 = BM25Okapi(corpus) if corpus and any(corpus) else None
        _indexes[audience] = (version, bm25, chunks)
        return bm25, chunks


@dataclass
class Hit:
    chunk: KnowledgeChunk
    score: float

    @property
    def document(self):
        return self.chunk.document


def retrieve(question: str, audience="public", k=TOP_K):
    """Top-k chunks for the question, best first. Only documents the audience may see are searched.

    Relevance = the chunk contains at least one of the question's words (so unrelated questions return
    nothing); ranking = BM25 score (which can be negative on very small collections, so it isn't a cutoff)."""
    query = tokenize(question)
    if not query:
        return []
    bm25, chunks = _get_index(audience)
    if bm25 is None:
        return []
    scores = bm25.get_scores(query)
    q = set(query)
    candidates = [i for i, c in enumerate(chunks) if q & c.token_set]
    ranked = sorted(candidates, key=lambda i: (len(q & chunks[i].token_set), scores[i]), reverse=True)
    return [Hit(chunks[i], float(scores[i])) for i in ranked[:k]]
