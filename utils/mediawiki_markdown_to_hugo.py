#!/usr/bin/python
"""Add Hugo front matter to Mediawiki markdown pages.

Used on output from:
https://github.com/outofcontrol/mediawiki-to-gfm

Known issues:

- Need to clean up the wikilinks; serialize AST back to Markdown.
- Handle Mediawiki redirect tags.
- Read missing data from the Mediawiki XML export.

Q: The script messed up my directory! I want to restore the previous files!
A: for f in *.orig; do mv -v "${f}" "${f/.orig}"; done

TODO: Make the above recursive? This is surprisingly nontrivial.

This doesn't work: 

```
find content -name '*.md.orig' -exec \
    mv -f {} "$(echo -n {} | sed -e 's/\\.orig$//')" \;
```

The reason is quite funny: What `find` gets in argv is `mv -f {} {}` because the
"$( ... )" block gets executed by shell before `find` has a chance to see it.
"""

from typing import List
from dataclasses import dataclass, field

import argparse
import commonmark  # type: ignore
import os
import os.path
import re
import shutil
import toml
import unidecode


# Language dependent
CATEGORY_TAG = "kategoria"


@dataclass
class Link:
  anchor: str
  url: str
  title: str


@dataclass
class Wikilink:
  anchor: str
  destination: str


@dataclass
class FrontMatter:
  title: str
  slug: str
  date: str = field(init=False, default="2005-01-01T00:00:00+01:00")
  categories: List[str] = field(init=False, default_factory=list)
  links: List[Link] = field(init=False, default_factory=list)
  wikilinks: List[Wikilink] = field(init=False, default_factory=list)

  def ToString(self) -> str:
    wiki_destinations = [f"{wl.destination}" for wl in self.wikilinks]
    wikilinks_text = f"wikilinks: {wiki_destinations}"
    return f"""---
title: "{self.title}"
slug: "{self.slug}"
date: {self.date}
kategorie: {self.categories}
draft: false
{wikilinks_text}
---
"""


def Slugify(s: str) -> str:
  shaven = unidecode.unidecode(s)
  lowercased = shaven.lower()
  segments = re.split("\s+", lowercased)
  return "-".join(segments)


def FrontMatterFromContent(content: str, title: str) -> FrontMatter:
  parser = commonmark.Parser()
  ast = parser.parse(content)
  if ast is None:
    raise Exception("Parsing failed?")
  fm = FrontMatter(title=title, slug=Slugify(title))
  # ast.walker seems to visit some nodes more than once.
  # This is surprising.
  already_seen = set()
  for node, unused_entering in ast.walker():
    if node in already_seen:
      continue
    already_seen.add(node)
    if node.t == "link":
      anchor = node.first_child.literal
      url = node.destination
      title = node.title
      if anchor.startswith(f'{CATEGORY_TAG}:'):
        category = anchor.replace(f"{CATEGORY_TAG}:", "")
        fm.categories.append(category)
      elif title == "wikilink":
        fm.wikilinks.append(Wikilink(anchor, url))
      else:
        fm.links.append(Link(anchor, url, title))
  return fm

# I hope this is a temporary workaround.
KNOWN_DANGLING_REFS = [
  "akompaniament)](Walking_\\(akompaniament\\)",
  "tercja_mała",
  "akompaniament)](Bossa_Nova_\\(akompaniament\\)",
  "G♭7",
  "Em",
  "Solmizacja",
  "Em",
  "Dźwięki_alterowane",
  "Em",
  "czterodźwięk",
  "trójdźwięk",
  "pięciodźwięk",
  "czterodźwięk",
  "Am9",
  "F13",
  "add11)](Am7♭5\\(add11\\)",
  "F13",
  "F13♯11",
  "Fmaj9",
  "swing",
  "Count_Basie",
  "Freddie_Green",
  ":Kategoria:Tabele_chwytów",
  ":kategoria:Akordy_durowe",
  "akompaniament)](Walking_\\(akompaniament\\)",
]

# TODO: Change this to not do I/O.
def TryToFixWikilinks(content: str) -> str:
  """When the target file does not exist on disk, don't sub."""
  # Pattern matching the destination.
  dest_pattern = '[^\s]+'
  anchor_pat = '\[(?P<anchor>[^\]]+)\]'
  identify_pat = anchor_pat + '\((?P<dest>[^\s]+) "wikilink"\)'
  def repl(m) -> str:
    def annotate_invalid(s: str) -> str:
      return f"{s}<!-- link nie odnosił się do niczego -->"
    dest = m['dest']
    anchor = m['anchor']
    if (dest in KNOWN_DANGLING_REFS
        or dest.startswith(":Kat")
        or dest.startswith(":kat")
        or dest.startswith("Użytkownik")):
      # Stripping the link entirely.
      print(f"{anchor} links to {dest}, a dangling reference")
      return annotate_invalid(anchor)
    # We've found a destination, does it exist on disk?
    # Desperate measures here. I wanted this to not do I/O.
    # This is also not configured correctly and won't work on anyone else's
    # setup.
    dest_path = os.path.join("content/książka", dest + ".md")
    if not os.path.exists(dest_path):
      print(f"Dangling reference to {dest_path}, not replacing")
      return annotate_invalid(anchor)
    return '[%s]({{< relref "%s" >}})' % (anchor, dest + '.md')
  return re.sub(identify_pat, repl, content)


def RemoveCategoryLinks(content: str) -> str:
  pattern = '\[:?[Kk]ategoria:[^\]]+\]\([^\)]+\)'
  return re.sub(pattern, '', content)


def RemoveGraphicsTags(content: str) -> str:
  pattern = '\[:?[Gg]rafika:[^\]]+\]\([^\)]+\)'
  return re.sub(pattern, '', content)


def RemoveThumbs(content: str) -> str:
  pattern = '\[thumb\]\([^\)]+\)'
  return re.sub(pattern, '', content)


def AnnotateMarkdown(content: str, title: str) -> str:
  """Analyze the content and add front matter."""
  fm = FrontMatterFromContent(content, title)
  return fm.ToString() + RemoveThumbs(
    TryToFixWikilinks(RemoveGraphicsTags(
      RemoveCategoryLinks(content))))


def ProcessFile(path) -> None:
  # First things first, let's check if we're even going to try.
  backup_path = path + ".orig"
  if os.path.exists(backup_path):
    # print(f"Backup file {backup_path} already exists; "
    #       "will not overwrite. Skipping.")
    print(f"Backup file {backup_path} already exists; "
          "Restoring it first.")
    shutil.move(backup_path, path)
  with open(path, "rb") as fd:
    content_bytes = fd.read()
  markdown_text = content_bytes.decode("utf-8")
  if markdown_text.startswith("---"):
    print(f"File {path} seems to contain Front Matter already. Skipping.")
    return
  title = TitleFromPath(path)
  updated_content: str = AnnotateMarkdown(markdown_text, title)
  # Let's not destroy people's work.
  shutil.copy(path, backup_path)
  with open(path, "wb") as fd:
    fd.write(updated_content.encode("utf-8"))


def MarkdownPaths(dirname: str) -> List[str]:
  file_list = []
  for root, dirs, files in os.walk(dirname):
    for f in files:
      fullpath = os.path.join(root, f)
      if f.endswith('.md'):
        file_list.append(fullpath)
  return file_list


def TitleFromPath(path:str ) -> str:
  _, filename = os.path.split(path)
  base, _ = os.path.splitext(filename)
  return base.replace("_", " ")


if __name__ == '__main__':
  parser = argparse.ArgumentParser(
      description="Convert markdown from mediawiki-to-gfm to hugo.")
  parser.add_argument(
      "content_directory", metavar="PATH",
      help="Content directory, usually named 'content'.")
  args = parser.parse_args()
  markdown_paths = MarkdownPaths(args.content_directory)
  for path in markdown_paths:
    ProcessFile(path)
