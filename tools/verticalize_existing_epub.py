#!/usr/bin/env python3
"""Make an EPUB proof: readable chapters vertical, all other files unchanged."""
import argparse
import hashlib
import pathlib
import re
import uuid
import zipfile

STYLE = """
/* Only readable chapters are vertical; bilingual and front matter stay horizontal. */
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
body.tes-vertical-readable table { width: auto; }
body.tes-vertical-readable img { max-width: 100%; max-height: 90%; }
html:not(.tes-vertical-readable), body:not(.tes-vertical-readable) { writing-mode: horizontal-tb; }
"""

def sha(data):
    return hashlib.sha256(data).hexdigest()

def transform(source, dest):
    readable = re.compile(r"OEBPS/(?:r|z)[0-9]{2}\.xhtml$")
    bilingual = re.compile(r"OEBPS/(?:c|e)[0-9]{2}\.xhtml$")
    count = 0
    bilingual_count = 0
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
            if readable.fullmatch(item.filename):
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
            elif item.filename == "OEBPS/content.opf":
                x = data.decode("utf-8")
                replacement_id = "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, "https://github.com/CassiaLin/Troy-Epic-Series/proof/vertical-v2/01"))
                x, id_count = re.subn(r"(<dc:identifier id=\"pub-id\">)[^<]+(</dc:identifier>)", lambda m: m.group(1) + replacement_id + m.group(2), x, count=1)
                x, title_count = re.subn(r"(<dc:title id=\"t1\">)([^<]+)(</dc:title>)", lambda m: m.group(1) + m.group(2) + "（直排測試二版）" + m.group(3), x, count=1)
                if id_count != 1 or title_count != 1:
                    raise ValueError("Unexpected OPF metadata")
                x, spine_count = re.subn(r"<spine(?=[ >])([^>]*)>", lambda m: '<spine' + re.sub(r'\\s+page-progression-direction="[^"]*"', '', m.group(1)) + ' page-progression-direction="rtl">', x, count=1)
                if spine_count != 1:
                    raise ValueError("Missing OPF spine")
                data = x.encode("utf-8")
            elif item.filename == "OEBPS/toc.ncx":
                x = data.decode("utf-8")
                replacement_id = "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, "https://github.com/CassiaLin/Troy-Epic-Series/proof/vertical-v2/01"))
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
            if readable.fullmatch(name) or name in ("OEBPS/css/book.css", "OEBPS/content.opf", "OEBPS/toc.ncx"):
                continue
            if before != after:
                raise ValueError("Unexpected change: " + name)
        for name in original.namelist():
            if bilingual.fullmatch(name) and sha(original.read(name)) != sha(converted.read(name)):
                raise ValueError("Bilingual chapter changed: " + name)
    if count == 0 or bilingual_count == 0:
        raise ValueError("Missing readable/bilingual sections")
    print(f"Readable chapters set to vertical: {count}")
    print(f"Bilingual chapters preserved byte-for-byte: {bilingual_count}")
    print(f"Output: {dest}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=pathlib.Path)
    parser.add_argument("destination", type=pathlib.Path)
    args = parser.parse_args()
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    transform(args.source, args.destination)
