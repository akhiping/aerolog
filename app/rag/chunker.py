from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ManualChunk:
    doc_title: str
    ata_chapter: str
    section: str
    content: str
    chunk_id: str = field(default="")

    def __post_init__(self):
        if not self.chunk_id:
            raw = f"{self.doc_title}:{self.section}:{self.content[:120]}"
            self.chunk_id = hashlib.sha256(raw.encode()).hexdigest()[:16]


_ATA_RE = re.compile(r"ATA\s+(?:Chapter\s+)?(\d{2,3})", re.IGNORECASE)
_TABLE_HEADER_RE = re.compile(r"^\s*\|.*\|.*\|", re.MULTILINE)
_TABLE_ROW_RE = re.compile(r"^\s*\|[^-].*\|", re.MULTILINE)
_SEPARATOR_RE = re.compile(r"^\s*\|[-\s|]+\|", re.MULTILINE)


def _extract_ata_chapter(text: str) -> str:
    m = _ATA_RE.search(text)
    return m.group(1) if m else ""


def _is_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|")


def _is_separator_line(line: str) -> bool:
    return bool(_SEPARATOR_RE.match(line))


def _split_table_rows(table_block: str, section: str, doc_title: str, ata: str) -> list[ManualChunk]:
    """Break a markdown table into per-row chunks for granular torque-spec search."""
    lines = table_block.strip().splitlines()
    if len(lines) < 3:
        return [ManualChunk(doc_title=doc_title, ata_chapter=ata, section=section, content=table_block)]

    header_line = lines[0]
    headers = [h.strip() for h in header_line.strip("|").split("|")]
    chunks: list[ManualChunk] = []

    # Keep the full table as one chunk too — useful for broad queries
    chunks.append(ManualChunk(doc_title=doc_title, ata_chapter=ata, section=section, content=table_block))

    for line in lines[2:]:  # skip header + separator
        if not _is_table_line(line) or _is_separator_line(line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        row_text_parts = []
        for h, c in zip(headers, cells):
            if c:
                row_text_parts.append(f"{h}: {c}")
        row_text = ", ".join(row_text_parts)
        # Prepend section context for better retrieval
        enriched = f"{section} — {row_text}"
        chunks.append(ManualChunk(doc_title=doc_title, ata_chapter=ata, section=section, content=enriched))

    return chunks


def chunk_manual(filepath: str) -> list[ManualChunk]:
    """Read a markdown manual file and split into searchable chunks.

    Strategy:
    - Title comes from the first ``# `` heading.
    - ATA chapter is extracted from the first ATA reference found.
    - Splits on ``##`` and ``###`` headings into sections.
    - Tables are kept intact AND each data row is also emitted as its own
      chunk so torque-spec lookups hit a small, focused text.
    - Non-table text sections longer than ~1200 chars are split on blank
      lines, keeping paragraphs together.
    """
    text = Path(filepath).read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    doc_title = ""
    ata_chapter = ""
    chunks: list[ManualChunk] = []

    # Extract title from first # heading
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            doc_title = stripped.lstrip("# ").strip()
            break

    ata_chapter = _extract_ata_chapter(text)

    # Split into sections by ## or ### headings
    sections: list[tuple[str, list[str]]] = []
    current_heading = "Introduction"
    current_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## ") or stripped.startswith("### "):
            if current_lines:
                sections.append((current_heading, current_lines))
            current_heading = stripped.lstrip("#").strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_heading, current_lines))

    for section_name, sec_lines in sections:
        # Separate table blocks from prose
        i = 0
        prose_buf: list[str] = []
        while i < len(sec_lines):
            line = sec_lines[i]
            if _is_table_line(line):
                # Flush accumulated prose
                if prose_buf:
                    _flush_prose(prose_buf, doc_title, ata_chapter, section_name, chunks)
                    prose_buf = []
                # Collect entire table block
                table_lines: list[str] = []
                while i < len(sec_lines) and (_is_table_line(sec_lines[i]) or _is_separator_line(sec_lines[i])):
                    table_lines.append(sec_lines[i])
                    i += 1
                table_block = "".join(table_lines)
                chunks.extend(_split_table_rows(table_block, section_name, doc_title, ata_chapter))
            else:
                prose_buf.append(line)
                i += 1

        if prose_buf:
            _flush_prose(prose_buf, doc_title, ata_chapter, section_name, chunks)

    return chunks


def _flush_prose(
    lines: list[str],
    doc_title: str,
    ata_chapter: str,
    section: str,
    chunks: list[ManualChunk],
    max_len: int = 1200,
) -> None:
    """Add prose lines as one or more chunks, splitting on blank lines if too long."""
    full = "".join(lines).strip()
    if not full:
        return

    if len(full) <= max_len:
        chunks.append(ManualChunk(doc_title=doc_title, ata_chapter=ata_chapter, section=section, content=full))
        return

    # Split on double-newline (paragraph break)
    paragraphs = re.split(r"\n\s*\n", full)
    buf = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if buf and len(buf) + len(para) + 2 > max_len:
            chunks.append(ManualChunk(doc_title=doc_title, ata_chapter=ata_chapter, section=section, content=buf.strip()))
            buf = para
        else:
            buf = f"{buf}\n\n{para}" if buf else para

    if buf.strip():
        chunks.append(ManualChunk(doc_title=doc_title, ata_chapter=ata_chapter, section=section, content=buf.strip()))
