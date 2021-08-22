import unittest
import mediawiki_markdown_to_hugo as m

TEST_ARTICLE_1 = """
word

[web link](https://www.example.com "web link title")

[kategoria:technika gry](kategoria:technika_gry "wikilink")

[Another article](Another_article "wikilink")
"""

TEST_ARTICLE_2 = """

**Artykulacja** jest jednym z najważniejszych elementów muzycznych.
Często decyduje o tym, czy daną muzykę możemy nazwać jazzem czy nie.
Artykulacja jazzowa różni się zasadniczo od artykulacji stosowanej w
klasycznej muzyce europejskiej, bowiem inne jest podejście muzyka do
dźwięku i jego przebiegu. Do każdej improwizowanej frazy jazzman ma
stosunek bardziej osobisty - on jest przecież jej twórca w całym
znaczeniu tego słowa. Ta jedność kompozytora i wykonawcy skupiająca się
w osobie muzyka jazzowego, pozwala pominąć niedoskonały i nie oddający
wiernie intencji kompozytora zapis nutowy. Zresztą muzyk jazzowy grając
z nut, też ma ogromną swobodę, która wykracza ponad znaczenie słowa
„interpretacja". W technice gry, metody artykulacji zbliżone są do
metod, jakimi posługuje się muzyk wychowany w tradycji muzyki
europejskiej.

W tym rozdziale umieszczę trzy bardzo ważne elementy artykulacji:
[legato](legato "wikilink"), [staccato](staccato "wikilink") i
[akcentowanie](akcentowanie "wikilink").

  - [Legato](Legato "wikilink")
  - [Akcentowanie](Akcentowanie "wikilink")
  - [Ozdobniki](Ozdobniki "wikilink")
  - [Flażolety](Flażolet "wikilink")

[kategoria:technika gry](kategoria:technika_gry "wikilink")
[kategoria:inna kategoria](kategoria:inna_kategoria "wikilink")
"""

class ConversionTest(unittest.TestCase):

  def testBasicStuff(self):
    doc = m.Document(TEST_ARTICLE_1, "content/bar/Test_Article_1.md")
    self.assertEqual("bar/test-article-1", doc.URLPath())
    fm = doc.fm
    self.assertEqual(fm.title, "Test Article 1")
    self.assertEqual(fm.slug, "test-article-1")

  def testTitleFromPath(self):
    self.assertEqual(
      "Szła dzieweczka do laseczka",
      m.TitleFromPath("content/książka/Szła_dzieweczka_do_laseczka.md"))

  def testTitleFromPathWithSlash(self):
    self.assertEqual("F7/C", m.TitleFromPath("content/książka/F7/C.md"))

  def testSlugify(self):
    self.assertEqual(
      "szla-dzieweczka-do-laseczka",
      m.Slugify("Szła dzieweczka do laseczka"))

  def testRenderFrontMatter(self):
    fm = m.FrontMatter(title="Test title 1", slug="test-title-1")
    fm.wikilinks.append(m.Wikilink("Another article", "Another_article"))
    fm.categories.append("test-category")
    fm.aliases.append("alias")
    expected = """---
title: "Test title 1"
slug: "test-title-1"
date: 2005-01-01T00:00:00+01:00
kategorie: ['test-category']
draft: false
wikilinks: ['Another_article']
aliases: ['alias']
---
"""
    self.assertEqual(expected, fm.ToString())

  def testRenderFrontMatterNoAliases(self):
    fm = m.FrontMatter(title="Test title 1", slug="test-title-1")
    fm.wikilinks.append(m.Wikilink("Another article", "Another_article"))
    fm.categories.append("test-category")
    expected = """---
title: "Test title 1"
slug: "test-title-1"
date: 2005-01-01T00:00:00+01:00
kategorie: ['test-category']
draft: false
wikilinks: ['Another_article']
---
"""
    self.assertEqual(expected, fm.ToString())

  def testWikilinks(self):
    redirects = {}
    dest_doc = m.Document("", "content/książka/Modulatory_i_filtry_dźwięku.md")
    doc = m.Document('3.  [Modulatory i filtry dźwięku]'
                     '(Modulatory_i_filtry_dźwięku "wikilink")',
                     'content/książka/foo.md')
    by_path = {m.path: m for m in (dest_doc, doc)}
    dst = ('3.  [Modulatory i filtry dźwięku]'
          '({{< relref "Modulatory_i_filtry_dźwięku.md" >}})')
    self.assertEqual(dst, doc.TryToFixWikilinks(by_path, redirects).content)

  def testWikilinksParen(self):
    redirects = {}
    dest_doc = m.Document(
      "", "content/książka/Bossa_Nova_\\(akompaniament\\).md")
    doc = m.Document('[Coś tam (akompaniament)](Bossa_Nova_\(akompaniament\) '
                     '"wikilink")', 'content/książka/foo.md')
    by_path = {m.path: m for m in (dest_doc, doc)}
    dst = ('[Coś tam (akompaniament)]'
           '({{< relref "Bossa_Nova_\(akompaniament\).md" >}})')
    self.assertEqual(dst, doc.TryToFixWikilinks(by_path, redirects).content)

  def testRemoveCategoryLinks(self):
    doc = m.Document(
      'head[kategoria:technika gry](# "Niestety nic nie ma pod '
      'tym linkiem")tail', 'content/książka/foo.md')
    dst = 'headtail'
    self.assertEqual(dst, doc.RemoveCategoryLinks().content)

  def testRedirection(self):
    doc = m.Document(
      '1.  REDIRECT [Regulacja gryfu](Regulacja_gryfu "wikilink")',
      'foo/bar.md')
    self.assertEqual("Regulacja_gryfu" , doc.GetRedirect())

  def testRedirectionStruna(self):
    doc = m.Document(
      '1.  REDIRECT [Struna](Struna "wikilink")',
      'foo/bar.md')
    self.assertEqual("Struna", doc.GetRedirect())

  def testURLPathWithSlash(self):
    doc = m.Document(
      '1.  REDIRECT [C9sus](C9sus "wikilink")',
      'content/książka/B♭/C.md')
    self.assertEqual("C9sus", doc.GetRedirect())
    self.assertEqual("b/c", doc.fm.slug)
    self.assertEqual("książka/b/c", doc.URLPath())

if __name__ == '__main__':
  unittest.main()
