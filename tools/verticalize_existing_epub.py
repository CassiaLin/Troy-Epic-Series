#!/usr/bin/env python3
"""Mixed layout: Chinese front matter, chapters, TOC and appendices vertical; bilingual unchanged."""
import argparse
import hashlib
import pathlib
import re
import uuid
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter

STYLE = """
/* Chinese reading portions vertical; bilingual and cover stay horizontal. */
html.tes-vertical-readable, body.tes-vertical-readable {
  writing-mode: vertical-rl;
  -webkit-writing-mode: vertical-rl;
  -epub-writing-mode: vertical-rl;
  text-orientation: mixed;
  -webkit-text-orientation: mixed;
  line-height: 1.85;
  margin: 3% 0;
  text-align: justify;
}
body.tes-vertical-readable p { text-indent: 2em; margin: 0 0 0 .8em; }
body.tes-vertical-readable h1, body.tes-vertical-readable h2 { text-align: start; }
body.tes-vertical-readable .xlink, body.tes-vertical-readable .fnlab { text-indent: 0; }
body.tes-vertical-readable .footnotes {
  border-top: none;
  border-right: 1px solid;
  padding-top: 0;
  padding-right: .5em;
  margin-top: 0;
  margin-right: 1em;
}
/* Wide tables remain horizontal even inside vertical Chinese appendices. */
body.tes-vertical-readable table { writing-mode: horizontal-tb; width: auto; max-width: 100%; }
body.tes-vertical-readable th, body.tes-vertical-readable td { writing-mode: horizontal-tb; }
body.tes-vertical-readable .tes-table-records { margin: 1.1em 0; }
body.tes-vertical-readable .tes-table-labels { font-size: 0.85em; opacity: 0.85; margin: 0 0 0.7em; }
body.tes-vertical-readable .tes-table-record { margin: 0 0 1.25em; padding: 0 0.6em; border-right: 1px solid; break-inside: avoid; }
body.tes-vertical-readable .tes-table-record p { text-indent: 0; margin: 0 0 0.4em; }
body.tes-vertical-readable .tes-record-title { font-weight: bold; }
body.tes-vertical-readable .tes-record-detail { font-size: 0.95em; }
body.tes-vertical-readable nav ol { padding-left: 0; padding-right: 1.2em; }
body.tes-vertical-readable .titlepage { margin-top: 0; margin-right: 18%; }
body.tes-vertical-readable .part { margin-top: 0; margin-right: 25%; }
body.tes-vertical-readable .meta { border-left: 0; border-right: 2px solid; padding-left: 0; padding-right: 0.8em; }
body.tes-vertical-readable img { max-width: 90vw; max-height: 85vh; width: auto; height: auto; object-fit: contain; }
body.tes-vertical-readable figure { writing-mode: horizontal-tb; text-align: center; max-width: 90vw; break-inside: avoid; }
body.tes-vertical-readable figure img { max-width: 90vw; max-height: 82vh; width: auto; height: auto; object-fit: contain; }
body.tes-vertical-readable figcaption { text-align: center; }
html:not(.tes-vertical-readable), body:not(.tes-vertical-readable) { writing-mode: horizontal-tb; }
"""


def verticalize_tables(x):
    """Present horizontal Markdown tables as legible vertical records, preserving each cell."""
    count = 0

    def convert(match):
        nonlocal count
        rows = re.findall(r"<tr>(.*?)</tr>", match.group(0), flags=re.S)
        parsed = []
        for row in rows:
            cells = re.findall(r"<(?:td|th)>(.*?)</(?:td|th)>", row, flags=re.S)
            if not cells:
                raise ValueError("Empty or unsupported table row")
            parsed.append(cells)
        if not parsed:
            raise ValueError("Unrecognized XHTML table")
        is_header = "<th>" in rows[0]
        headers = parsed.pop(0) if is_header else []
        markup = ['<div class="tes-table-records">']
        if headers:
            markup.append('<div class="tes-table-labels"><p>' + '／'.join(headers) + '</p></div>')
        for cells in parsed:
            markup.append('<div class="tes-table-record">')
            markup.append('<p class="tes-record-title">' + cells[0] + '</p>')
            for i, cell in enumerate(cells[1:], start=1):
                label = ('<strong>' + headers[i] + '：</strong>') if i < len(headers) and len(headers) > 2 else ''
                markup.append('<p class="tes-record-detail">' + label + cell + '</p>')
            markup.append('</div>')
        markup.append('</div>')
        count += 1
        return ''.join(markup)

    converted = re.sub(r"<table>.*?</table>", convert, x, flags=re.S)
    if '<table' in converted:
        raise ValueError("Unhandled table in vertical XHTML")
    return converted, count

def sha(data):
    return hashlib.sha256(data).hexdigest()

def image_references(x):
    root = ET.fromstring(x)
    return Counter(node.attrib.get("src", "") for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "img")

def xml_text(x):
    return "".join(ET.fromstring(x).itertext())

def transform(source, dest, vol=None):
    readable = re.compile(r"OEBPS/(?:r|z)[0-9]{2}\.xhtml$")
    front = re.compile(r"OEBPS/f[0-9]{2}\.xhtml$")
    appendix = re.compile(r"OEBPS/a[a-z]\.xhtml$")
    vertical_named = {"OEBPS/titlepage.xhtml", "OEBPS/nav.xhtml", "OEBPS/p1.xhtml", "OEBPS/p3.xhtml"}
    if vol is None:
        match = re.search(r"TroyEpic_(\\d{2})_", source.name)
        if not match:
            raise ValueError("Specify --volume for unknown source filename")
        vol = match.group(1)
    if vol not in ("01", "02", "03", "04", "05", "90"):
        raise ValueError("Unknown volume: " + vol)
    is_90 = vol == "90"
    if is_90:
        vertical_named.discard("OEBPS/p3.xhtml")
    def vertical(name):
        return bool(readable.fullmatch(name) or front.fullmatch(name) or appendix.fullmatch(name) or name in vertical_named)
    bilingual = re.compile(r"OEBPS/(?:c|e)[0-9]{2}\.xhtml$")
    count = 0
    bilingual_count = 0
    modified_sections = []
    table_count = 0
    original_images = []
    with zipfile.ZipFile(source) as inp, zipfile.ZipFile(dest, "w") as out:
        names = inp.namelist()
        if not names or names[0] != "mimetype":
            raise ValueError("Source has invalid EPUB mimetype ordering")
        if "OEBPS/css/book.css" not in names:
            raise ValueError("Unexpected EPUB CSS path")
        if not any(bilingual.fullmatch(n) for n in names):
            raise ValueError("No bilingual XHTML found; refusing to generate")
        for item in inp.infolist():
            data = inp.read(item.filename)
            if vertical(item.filename):
                x = data.decode("utf-8")
                if '<body' not in x or 'class="tes-vertical-readable"' in x:
                    raise ValueError("Unexpected readable XHTML: " + item.filename)
                updated, n = re.subn(r"<body(?=[ >])", '<body class="tes-vertical-readable"', x, count=1)
                if n != 1:
                    raise ValueError("Failed to mark readable XHTML")
                updated, html_count = re.subn(r'<html(?=[ >])', '<html class="tes-vertical-readable"', updated, count=1)
                if html_count != 1:
                    raise ValueError("Missing XHTML root")
                updated, converted_tables = verticalize_tables(updated)
                table_count += converted_tables
                data = updated.encode("utf-8")
                count += 1
                modified_sections.append(item.filename)
            elif item.filename == "OEBPS/content.opf":
                x = data.decode("utf-8")
                replacement_id = "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, f"https://github.com/CassiaLin/Troy-Epic-Series/proof/vertical-series-v7/{vol}"))
                x, id_count = re.subn(r"(<dc:identifier id=\"pub-id\">)[^<]+(</dc:identifier>)", lambda m: m.group(1) + replacement_id + m.group(2), x, count=1)
                x, title_count = re.subn(r"(<dc:title id=\"t1\">)([^<]+)(</dc:title>)", lambda m: m.group(1) + m.group(2) + "（直排測試版）" + m.group(3), x, count=1)
                if id_count != 1 or title_count != 1:
                    raise ValueError("Unexpected OPF metadata")
                x, spine_count = re.subn(r"<spine(?=[ >])([^>]*)>", lambda m: '<spine' + re.sub(r'\\s+page-progression-direction="[^"]*"', '', m.group(1)) + ' page-progression-direction="rtl">', x, count=1)
                if spine_count != 1:
                    raise ValueError("Missing OPF spine")
                data = x.encode("utf-8")
            elif item.filename == "OEBPS/toc.ncx":
                x = data.decode("utf-8")
                replacement_id = "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, f"https://github.com/CassiaLin/Troy-Epic-Series/proof/vertical-series-v7/{vol}"))
                x, ncx_count = re.subn(r'(<meta name="dtb:uid" content=")[^"]+("/>)', lambda m: m.group(1) + replacement_id + m.group(2), x, count=1)
                if ncx_count != 1:
                    raise ValueError("Unexpected NCX identifier")
                data = x.encode("utf-8")
            elif item.filename == "OEBPS/css/book.css":
                data += ("\n" + STYLE).encode("utf-8")
            elif bilingual.fullmatch(item.filename):
                bilingual_count += 1
            out.writestr(item, data)
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(dest) as converted:
        if original.namelist() != converted.namelist():
            raise ValueError("ZIP file list changed")
        for name in original.namelist():
            before, after = original.read(name), converted.read(name)
            if vertical(name) or name in ("OEBPS/css/book.css", "OEBPS/content.opf", "OEBPS/toc.ncx"):
                continue
            if before != after:
                raise ValueError("Unexpected change: " + name)
        for name in original.namelist():
            if name.startswith("OEBPS/images/") or re.search(r"\\.(?:png|jpe?g|svg|gif|webp)$", name, re.I):
                original_images.append(name)
                if original.read(name) != converted.read(name):
                    raise ValueError("Image bytes changed: " + name)
        for name in original.namelist():
            if vertical(name) and name.endswith(".xhtml"):
                old, new = original.read(name).decode("utf-8"), converted.read(name).decode("utf-8")
                if image_references(old) != image_references(new):
                    raise ValueError("Image references changed: " + name)
                if "<table" not in old and xml_text(old) != xml_text(new):
                    raise ValueError("Text changed in XHTML: " + name)
        for name in original.namelist():
            if bilingual.fullmatch(name) and sha(original.read(name)) != sha(converted.read(name)):
                raise ValueError("Bilingual chapter changed: " + name)
    expected_front = sorted(n for n in names if front.fullmatch(n))
    expected_appendix = sorted(n for n in names if appendix.fullmatch(n))
    required = set(expected_front + expected_appendix + [n for n in vertical_named if n in names])
    if not expected_front or (not is_90 and not expected_appendix):
        raise ValueError("Source EPUB lacks expected front matter or appendices")
    if is_90:
        if not any(n.endswith("cover-epub.jpg") for n in original_images) or len(original_images) < 22:
            raise ValueError("Volume 90 missing expected cover and 21 image files")
        if not any(readable.fullmatch(n) for n in modified_sections):
            raise ValueError("Volume 90 Chinese chapters not converted")
    if count == 0 or bilingual_count == 0 or not required.issubset(set(modified_sections)):
        raise ValueError("Missing vertical sections: " + str(sorted(required - set(modified_sections))))
    if table_count == 0:
        print("No tables needed conversion")
    print(f"Converted tables to vertical records: {table_count}")
    print(f"Images preserved byte-for-byte: {len(original_images)}")
    print(f"Front matter vertical: {len(expected_front)}; appendices vertical: {len(expected_appendix)}")
    print(f"Vertical XHTML files: {count}; sections: {modified_sections}")
    print(f"Bilingual chapters preserved byte-for-byte: {bilingual_count}")
    print(f"Output: {dest}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=pathlib.Path)
    parser.add_argument("destination", type=pathlib.Path)
    parser.add_argument("--volume", choices=["01","02","03","04","05","90"])
    args = parser.parse_args()
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    transform(args.source, args.destination, args.volume)
