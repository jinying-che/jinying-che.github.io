"""Build the searchable /x/ index from the standalone HTML files."""

import json
import subprocess
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote


ARCHIVE = Path("static/x")
INDEX = ARCHIVE / "index.html"
BLOCK_TAGS = {
    "article", "aside", "blockquote", "br", "dd", "div", "dl", "dt", "figcaption",
    "footer", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "li", "main",
    "nav", "ol", "p", "pre", "section", "table", "td", "th", "tr", "ul",
}
IGNORED_TAGS = {"script", "style", "template", "noscript"}


class PageText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = []
        self.text = []
        self.summary = ""
        self.tags = []
        self.dates = []
        self.in_head = False
        self.in_title = False
        self.ignored = []

    def handle_starttag(self, tag, attrs):
        if tag in IGNORED_TAGS:
            self.ignored.append(tag)
        if self.ignored:
            return
        if tag == "head":
            self.in_head = True
        elif tag == "body":
            self.in_head = False
        elif tag == "title" and self.in_head:
            self.in_title = True
        elif tag in {"meta", "time"}:
            attrs = dict(attrs)
            name = (attrs.get("name") or "").lower()
            if tag == "meta" and self.in_head:
                content = attrs.get("content") or ""
                if name == "description" and not self.summary:
                    self.summary = " ".join(content.split())
                elif name == "keywords":
                    self.tags.extend(" ".join(keyword.split()) for keyword in content.split(","))
            if (
                attrs.get("property") == "article:published_time"
                or attrs.get("itemprop") == "datePublished"
                or attrs.get("name") == "date"
            ):
                self.dates.append(attrs.get("content") or attrs.get("datetime"))
        if tag in BLOCK_TAGS:
            self.text.append(" ")

    def handle_endtag(self, tag):
        if self.ignored:
            if tag == self.ignored[-1]:
                self.ignored.pop()
            return
        if tag == "head":
            self.in_head = False
        elif tag == "title":
            self.in_title = False
        if tag in BLOCK_TAGS:
            self.text.append(" ")

    def handle_data(self, data):
        if self.ignored:
            return
        if self.in_title:
            self.title.append(data)
        elif not self.in_head:
            self.text.append(data)


def creation_date(path, published_dates):
    for value in published_dates:
        if not value:
            continue
        try:
            date = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            continue
        return date.replace(tzinfo=date.tzinfo or timezone.utc)

    added = subprocess.check_output(
        ["git", "--literal-pathspecs", "log", "-1", "--follow", "--diff-filter=A",
         "--format=%aI", "--", str(path)],
        text=True,
    ).strip()
    if added:
        return datetime.fromisoformat(added)
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)


def main(destination):
    pages = []
    for path in sorted(ARCHIVE.rglob("*")):
        if path == INDEX or path.suffix.lower() not in {".html", ".htm"}:
            continue
        if not path.is_file() or path.is_symlink():
            continue

        parser = PageText()
        parser.feed(path.read_text(encoding="utf-8-sig", errors="replace"))
        parser.close()
        relative = path.relative_to(ARCHIVE)
        is_directory_index = relative.name == "index.html"
        route = f"{relative.parent.as_posix()}/" if is_directory_index else relative.as_posix()
        title = " ".join("".join(parser.title).split())
        fallback_title = relative.parent.name if is_directory_index else relative.stem
        created = creation_date(path, parser.dates).astimezone(timezone.utc)
        pages.append((created, {
            "title": title or fallback_title.replace("-", " ").replace("_", " "),
            "path": f"/x/{route}",
            "href": "./" + quote(route),
            "date": created.date().isoformat(),
            "summary": parser.summary,
            "tags": list(dict.fromkeys(tag for tag in parser.tags if tag)),
            "text": " ".join("".join(parser.text).split()),
        }))

    pages.sort(key=lambda entry: entry[0], reverse=True)
    # An HTML document's text can contain a literal closing script tag.
    data = json.dumps({"archivePages": [page for _, page in pages]}, ensure_ascii=False)
    data = data.replace("<", r"\u003c")
    output = destination / "x/index.html"
    html = output.read_text(encoding="utf-8")
    marker = '{"archivePages":[]}'
    if html.count(marker) != 1:
        raise ValueError(f"Expected one archive data placeholder in {output}")
    output.write_text(html.replace(marker, data, 1), encoding="utf-8")
    print(f"Indexed {len(pages)} HTML pages in {output}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
