"""Convert a Claude Docs prose read (saved MCP JSON result) into Markdown.

Usage:
  python doc2md.py <read-result.json> <output.md> <artifact-slug> <copy-date YYYY-MM-DD>

The input is the file Claude Code saves when a `read` of a doc's body node
(no payload) is too large to show inline: {"data": {"xml": "<doc>...</doc>"}}.
"""
import json
import sys
import xml.etree.ElementTree as ET


def inline(el):
    s = el.text or ""
    for c in el:
        if c.tag == "date":
            t = c.get("value", "")
        elif c.tag == "mention":
            t = "@" + c.get("name", "")
        elif c.tag == "br":
            t = "<br/>"
        else:
            t = inline(c)
            if c.tag == "bold":
                t = f"**{t}**"
            elif c.tag == "code":
                t = f"`{t}`"
        s += t + (c.tail or "")
    # Run kode bersebelahan (hasil edit per karakter) jadi satu span: `ba``lance` -> `balance`.
    return s.replace("``", "")


def block(el, depth=0):
    if el.tag == "paragraph":
        h = el.get("heading")
        t = inline(el)
        return ("#" * int(h) + " " + t) if h else t
    if el.tag == "codeBlock":
        body = "".join(el.itertext()).strip("\n")
        return f"```{el.get('language') or 'text'}\n{body}\n```"
    if el.tag == "list":
        kind = el.get("kind")
        out = []
        for n, li in enumerate(el, 1):
            marker = {
                "ordered": f"{n}.",
                "check": "- [x]" if li.get("checked") == "true" else "- [ ]",
            }.get(kind, "-")
            parts = [block(c, depth + 1) for c in li]
            out.append("    " * depth + marker + " " + (parts[0] if parts else ""))
            out.extend(parts[1:])
        return "\n".join(out)
    if el.tag == "table":
        rows = [
            "| " + " | ".join(" ".join(inline(p) for p in c).replace("|", r"\|") for c in r) + " |"
            for r in el
        ]
        rows.insert(1, "|" + " --- |" * len(el[0]))
        return "\n".join(rows)
    return inline(el)


def main():
    src, dst, slug, copied = sys.argv[1:5]
    data = json.load(open(src, encoding="utf-8"))
    root = ET.fromstring(data["data"]["xml"])
    blocks = [block(c) for c in root]
    blocks.insert(
        2,
        f"> Sumber: Claude Docs https://claude.ai/code/artifact/{slug} "
        f"(disalin ke repo {copied}). Dokumen di claude.ai adalah versi induk; "
        f"salinan ini acuan saat coding. Jangan diedit langsung: catat perubahan di "
        f"`sdbot/docs/PENDING-CHANGES.md` (skill `sdbot-docs-sync`).",
    )
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n\n".join(blocks) + "\n")


if __name__ == "__main__":
    main()
