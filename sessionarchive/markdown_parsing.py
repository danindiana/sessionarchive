"""
Small, dependency-free markdown parsing helpers.

Vendored from paper_processor's neo4j_viz/neo4j_importer.py (same two
functions, unchanged) so this package has no dependency on paper_processor —
these are pure Python (re/json only), safe to duplicate rather than import
across repos.
"""
import re


def clean_markdown_headers(content: str) -> dict:
    """Splits markdown content by H2 headers and returns a dict mapping headers to text."""
    sections = {}
    current_header = "Intro"
    current_text = []

    for line in content.splitlines():
        if line.startswith("## "):
            if current_text:
                sections[current_header] = "\n".join(current_text).strip()
            current_header = line[3:].strip()
            current_text = []
        elif line.startswith("# "):
            continue
        else:
            current_text.append(line)

    if current_text:
        sections[current_header] = "\n".join(current_text).strip()

    return sections


def parse_logic_definitions(text: str) -> list:
    """Parses definitions under a header, shaped as '- **Name**: Description' bullets."""
    definitions = []
    pattern = r"-\s*\*\*([^*]+)\*\*:\s*(.*)"
    for line in text.splitlines():
        m = re.match(pattern, line.strip())
        if m:
            definitions.append({
                "name": m.group(1).strip(),
                "definition": m.group(2).strip(),
            })
    return definitions
