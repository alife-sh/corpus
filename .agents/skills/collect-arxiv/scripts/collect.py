#!/usr/bin/env python3
"""Preserve a versioned arXiv paper and figure assets, without ingestion."""

import argparse
from collections import deque
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import xml.etree.ElementTree as ET

HOSTS = {"arxiv.org", "www.arxiv.org", "export.arxiv.org"}
MAX_BYTES = 64 * 1024 * 1024
MAX_ASSETS = 128
ID_PATTERN = r"(?:\d{4}\.\d{4,5}|[A-Za-z][A-Za-z.-]*/\d{7})v[1-9]\d*"
CSS_URL = re.compile(r"url\(\s*['\"]?([^)'\"]+)['\"]?\s*\)", re.I)
CSS_IMPORT = re.compile(r"@import\s+(['\"])(.*?)\1", re.I)


def normalize_id(value):
    value = value.strip()
    if "://" in value:
        url = urlsplit(value)
        if url.scheme not in {"http", "https"} or url.hostname not in HOSTS:
            raise ValueError("Expected an arxiv.org abstract, HTML, or PDF URL")
        match = re.fullmatch(r"/(?:abs|html|pdf)/(.+)", url.path.rstrip("/"))
        if not match:
            raise ValueError("Expected an arXiv /abs/, /html/, or /pdf/ URL")
        value = match.group(1)
    value = re.sub(r"^arxiv:", "", value, flags=re.I)
    if value.endswith(".pdf"):
        value = value[:-4]
    if not re.fullmatch(ID_PATTERN, value):
        raise ValueError("Use an explicit versioned ID, e.g. 2206.01134v2")
    return value


def allowed_url(url):
    parsed = urlsplit(url)
    return (parsed.scheme == "https" and parsed.hostname in HOSTS
            and parsed.port in {None, 443} and not parsed.username)


class ArxivRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed_url(newurl):
            raise ValueError("Refusing redirect outside HTTPS arXiv hosts")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url):
    if not allowed_url(url):
        raise ValueError("Refusing download outside HTTPS arXiv hosts")
    opener = build_opener(ArxivRedirects())
    for attempt in range(3):
        try:
            req = Request(url, headers={"User-Agent": "alife-corpus-collector/1.0"})
            with opener.open(req, timeout=60) as response:
                data = response.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES:
                    raise ValueError("Asset exceeds the 64 MiB per-file limit")
                return data, response.headers.get("Content-Type", "")
        except HTTPError as error:
            error.close()
            if error.code not in {429, 500, 502, 503, 504} or attempt == 2:
                raise
            retry_after = error.headers.get("Retry-After", "")
            delay = min(int(retry_after), 30) if retry_after.isdigit() else 2 ** attempt
            time.sleep(delay)
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def css_refs(text):
    return [s.strip() for s in CSS_URL.findall(text)] + [s for _, s in CSS_IMPORT.findall(text)]


def srcset_refs(value):
    """Read URL candidates without splitting commas inside embedded data URLs."""
    refs = []
    while value.strip(" ,\t\r\n"):
        value = value.lstrip(" ,\t\r\n")
        token = re.match(r"\S+", value).group()
        value = value[len(token):]
        refs.append(token.rstrip(","))
        if token.endswith(","):
            continue
        separator = value.find(",")
        if separator < 0:
            break
        value = value[separator + 1:]
    return refs


class FigureRefs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.refs = []
        self.base = None
        self.document = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "").split()
        self.document |= "ltx_document" in classes
        if tag == "base" and self.base is None:
            self.base = attrs.get("href")
        if tag == "figure":
            self.depth += 1
        if not self.depth and "ltx_graphics" not in classes:
            return
        for key in {"img": ["src"], "object": ["data"],
                    "image": ["href", "xlink:href"], "source": ["src"]}.get(tag, []):
            if attrs.get(key):
                self.refs.append(attrs[key])
        if tag in {"img", "source"} and attrs.get("srcset"):
            self.refs.extend(srcset_refs(attrs["srcset"]))
        self.refs.extend(css_refs(attrs.get("style", "")))

    def handle_endtag(self, tag):
        if tag == "figure":
            self.depth = max(0, self.depth - 1)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)


def html_refs(data):
    parser = FigureRefs()
    parser.feed(data.decode("utf-8"))
    if not parser.document:
        raise ValueError("Response is not an arXiv full-paper HTML document")
    return parser


def asset_refs(data, path):
    if path.suffix.lower() == ".svg":
        root = ET.fromstring(data)
        if root.tag.split("}")[-1] != "svg":
            raise ValueError("Response is not an SVG")
        refs = []
        for node in root.iter():
            # Hyperlinks are not dependencies needed to display a figure.
            if node.tag.split("}")[-1] != "a":
                refs.extend(value for key, value in node.attrib.items() if key.split("}")[-1] == "href")
        return refs + css_refs(data.decode("utf-8"))
    if path.suffix.lower() == ".css":
        return css_refs(data.decode("utf-8"))
    return []


def validate(data, path, content_type=None):
    if not data:
        raise ValueError("Empty response")
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise ValueError("Response is not a PDF")
    elif suffix == ".html":
        html_refs(data)
    elif suffix == ".svg":
        asset_refs(data, path)
    elif suffix == ".css":
        if content_type and "text/css" not in content_type:
            raise ValueError("Response is not CSS")
    elif data.lstrip().lower().startswith((b"<!doctype html", b"<html")):
        raise ValueError("Received an HTML error page instead of an asset")
    elif content_type and not content_type.startswith(("image/", "font/", "application/")):
        raise ValueError(f"Unexpected asset type: {content_type}")


def digest(data):
    return hashlib.sha256(data).hexdigest()


class Collector:
    def __init__(self, paper_id, root):
        self.paper_id = normalize_id(paper_id)
        self.folder = (Path(root) / "raw" / "papers" / self.paper_id.replace("/", "-").lower()).resolve()
        self.files = []
        self.gaps = []
        self.owners = {}
        self.originals = {}

    def obtain(self, url, path):
        if path in self.owners:
            if self.owners[path] != url:
                raise ValueError("Different URLs would occupy the same local path")
        self.owners[path] = url
        reused = path.exists()
        if reused:
            data = path.read_bytes()
            validate(data, path)
            self.originals[path] = digest(data)
        else:
            data, content_type = fetch(url)
            validate(data, path, content_type)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(data)
        self.files.append({"url": url, "path": path.relative_to(self.folder).as_posix(),
                           "bytes": len(data), "sha256": digest(data), "reused": reused})
        return data

    def locate(self, parent_url, parent_path, ref):
        ref = ref.strip()
        if not ref or ref.startswith(("#", "data:")):
            return None
        parts = urlsplit(ref)
        url = urljoin(parent_url, ref).split("#", 1)[0]
        if not allowed_url(url):
            raise ValueError(f"External or non-HTTPS asset not fetched: {url}")
        if parts.scheme or parts.netloc or parts.path.startswith("/"):
            name = Path(unquote(urlsplit(url).path)).name or "asset"
            path = self.folder / "assets" / "external" / digest(url.encode())[:16] / name
            self.gaps.append(f"Archived asset remains non-local in unchanged source: {ref}")
        else:
            path = (parent_path.parent / unquote(parts.path)).resolve()
        if not path.is_relative_to(self.folder):
            raise ValueError(f"Asset path escapes paper folder: {ref}")
        return url, path

    def run(self):
        self.folder.mkdir(parents=True, exist_ok=True)
        html_url = f"https://arxiv.org/html/{self.paper_id}"
        pdf_url = f"https://arxiv.org/pdf/{self.paper_id}"
        html = None
        for name, url in [("paper.pdf", pdf_url), ("paper.html", html_url)]:
            try:
                data = self.obtain(url, self.folder / name)
                if name == "paper.html":
                    html = data
            except (OSError, ValueError, ET.ParseError) as error:
                if isinstance(error, HTTPError):
                    error.close()
                self.gaps.append(f"{url}: {error}")
        queue = deque()
        if html is not None:
            parser = html_refs(html)
            base = urljoin(html_url, parser.base) if parser.base else html_url
            if parser.base:
                self.gaps.append("HTML base element may prevent local figure resolution")
            queue.extend((base, self.folder / "paper.html", ref) for ref in parser.refs)
        seen = set()
        while queue:
            parent_url, parent_path, ref = queue.popleft()
            try:
                location = self.locate(parent_url, parent_path, ref)
                if location is None or location in seen:
                    continue
                seen.add(location)
                if len(seen) > MAX_ASSETS:
                    self.gaps.append("Figure dependency limit reached (128 assets)")
                    break
                url, path = location
                data = self.obtain(url, path)
                queue.extend((url, path, dep) for dep in asset_refs(data, path))
            except (OSError, ValueError, ET.ParseError) as error:
                if isinstance(error, HTTPError):
                    error.close()
                self.gaps.append(f"Figure dependency {ref}: {error}")
        for path, original_hash in self.originals.items():
            if digest(path.read_bytes()) != original_hash:
                raise RuntimeError(f"Existing source unexpectedly changed: {path}")
        now = datetime.now(timezone.utc)
        report = {"arxiv_id": self.paper_id, "collected_at": now.isoformat(),
                  "status": "partial" if self.gaps else "collected",
                  "files": self.files, "gaps": list(dict.fromkeys(self.gaps)),
                  "scope": "Collection only; no ingestion. Non-figure site assets excluded."}
        record = self.folder / f"collection-{now.strftime('%Y%m%dT%H%M%S%fZ')}.json"
        with record.open("x") as stream:
            json.dump(report, stream, indent=2)
            stream.write("\n")
        metadata = self.folder / "metadata.md"
        if not metadata.exists():
            lines = [f"# arXiv:{self.paper_id}", "", f"- Version: v{self.paper_id.rsplit('v', 1)[1]}",
                     f"- Source URL: {html_url}", f"- PDF URL: {pdf_url}",
                     f"- Collected: {now.date()}", "- Ingestion: Not performed", "",
                     "## Collection record", "", f"See [{record.name}]({record.name}) for file hashes, asset paths, and gaps.",
                     "", "## Local files", ""]
            lines.extend(f"- [{item['path']}]({item['path']})" for item in self.files)
            lines.extend(["", "## Gaps", ""] + ([f"- {gap}" for gap in report["gaps"]] or ["No missing figure dependencies detected."]))
            lines.extend(["", "Non-figure site styling, scripts, and interface assets are not archived.",
                          "Local figures do not make the entire page self-contained.", ""])
            with metadata.open("x") as stream:
                stream.write("\n".join(lines))
        report["directory"] = str(self.folder)
        report["record"] = str(record)
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paper", help="Versioned arXiv identifier or abstract/PDF/HTML URL")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root (default: current directory)")
    args = parser.parse_args()
    try:
        report = Collector(args.paper, args.root).run()
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Collection failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 2 if report["gaps"] else 0


if __name__ == "__main__":
    sys.exit(main())
