#!/usr/bin/env python3
"""Mixed layout: Chinese front matter, chapters, TOC and appendices vertical; bilingual unchanged."""
import argparse
import hashlib
import pathlib
import re
import uuid
import zipfile

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
body.tes-vertical-readable nav ol { padding-left: 0; padding-right: 1.2em; }
body.tes-vertical-readable .titlepage { margin-top: 0; margin-right: 18%; }
body.tes-vertical-readable .part { margin-top: 0; margin-right: 25%; }
body.tes-vertical-readable .meta { border-left: 0; border-right: 2px solid; padding-left: 0; padding-right: 0.8em; }
body.tes-vertical-readable img { max-width: 100%; max-height: 90%; }
html:not(.tes-vertical-readable), body:not(.tes-vertical-readable) { writing-mode: horizontal-tb; }
"""

def sha(data):
    return hashlib.sha256(data).hexdigest()

def transform(source, dest):
    readable = re.compile(r"OEBPS/(?:r|z)[0-9]{2}\.xhtml$")
    front = re.compile(r"OEBPS/f[0-9]{2}\.xhtml$")
    appendix = re.compile(r"OEBPS/a[a-z]\.xhtml$")
    vertical_named = {"OEBPS/titlepage.xhtml", "OEBPS/nav.xhtml", "OEBPS/p1.xhtml", "OEBPS/p3.xhtml"}
    def vertical(name):
        return bool(readable.fullmatch(name) or front.fullmatch(name) or appendix.fullmatch(name) or name in vertical_named)
    bilingual = re.compile(r"OEBPS/(?:c|e)[0-9]{2}\.xhtml$")
    count = 0
    bilingual_count = 0
    modified_sections = []
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
                data = updated.encode("utf-8")
                count += 1
                modified_sections.append(item.filename)
            elif item.filename == "OEBPS/content.opf":
                x = data.decode("utf-8")
                replacement_id = "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, "https://github.com/CassiaLin/Troy-Epic-Series/proof/vertical-v4/01"))
                x, id_count = re.subn(r"(<dc:identifier id=\"pub-id\">)[^<]+(</dc:identifier>)", lambda m: m.group(1) + replacement_id + m.group(2), x, count=1)
                x, title_count = re.subn(r"(<dc:title id=\"t1\">)([^<]+)(</dc:title>)", lambda m: m.group(1) + m.group(2) + "（直排測試四版）" + m.group(3), x, count=1)
                if id_count != 1 or title_count != 1:
                    raise ValueError("Unexpected OPF metadata")
                x, spine_count = re.subn(r"<spine(?=[ >])([^>]*)>", lambda m: '<spine' + re.sub(r'\\s+page-progression-direction="[^"]*"', '', m.group(1)) + ' page-progression-direction="rtl">', x, count=1)
                if spine_count != 1:
                    raise ValueError("Missing OPF spine")
                data = x.encode("utf-8")
            elif item.filename == "OEBPS/toc.ncx":
                x = data.decode("utf-8")
                replacement_id = "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, "https://github.com/CassiaLin/Troy-Epic-Series/proof/vertical-v4/01"))
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
            if bilingual.fullmatch(name) and sha(original.read(name)) != sha(converted.read(name)):
                raise ValueError("Bilingual chapter changed: " + name)
    expected_front = sorted(n for n in names if front.fullmatch(n))
    expected_appendix = sorted(n for n in names if appendix.fullmatch(n))
    required = set(expected_front + expected_appendix + [n for n in vertical_named if n in names])
    if not expected_front or not expected_appendix:
        raise ValueError("Source EPUB lacks front matter or appendices")
    if count == 0 or bilingual_count == 0 or not required.issubset(set(modified_sections)):
        raise ValueError("Missing vertical sections: " + str(sorted(required - set(modified_sections))))
    print(f"Front matter vertical: {len(expected_front)}; appendices vertical: {len(expected_appendix)}")
    print(f"Vertical XHTML files: {count}; sections: {modified_sections}")
    print(f"Bilingual chapters preserved byte-for-byte: {bilingual_count}")
    print(f"Output: {dest}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=pathlib.Path)
    parser.add_argument("destination", type=pathlib.Path)
    args = parser.parse_args()
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    transform(args.source, args.destination)
