"""A navigation menu is not a document, and must never be quoted as a rule.

Three of the pages first scraped into the corpus were government homepages: real
fetches, real 200s, sound provenance, and no content. Retrieval ranked them above
the relevance floor, so asking "am I allowed to fish inside a marine protected
area?" returned "Skip to main content / Screen Reader Access", attributed to a
named authority. That is worse than the refusal this module is built to give --
a fisherman can act on a confident non-answer.

This is a separate fault from quarantine. Quarantine is for documents whose
provenance is false; these were fetched honestly and only their text is worthless.
"""

import pytest

from app.tools import evidence as store


MENU = (
    "Skip to main content Screen Reader Access A- | A | A+ Toggle navigation Home "
    "About Us What We Do Our Locations Knowledge Centres TC Genesis TC Track TC "
    "Landfall Bulletins Climatology Publications Awards Our Team Contact Sitemap"
)

DOCUMENT = (
    "In accordance with international procedure, ports are warned and advised to "
    "hoist signals whenever adverse weather is expected over the ports for the "
    "oceanic areas in which they are located. The warning messages normally contain "
    "information on the location, intensity, direction and speed of movement of the "
    "tropical cyclone and the expected weather over the port. The India Meteorological "
    "Department maintains a port warning service through its cyclone warning centres."
)


def test_a_menu_is_not_read_as_a_document():
    assert store.reads_like_a_document(MENU) is False
    assert store.prose_segments(MENU) == []


def test_real_prose_is_read_as_a_document():
    assert store.reads_like_a_document(DOCUMENT) is True
    assert len(store.prose_segments(DOCUMENT)) >= 3


def test_a_long_menu_run_is_not_mistaken_for_one_huge_sentence():
    """Why function words and not punctuation.

    A thousand characters of link labels ending at a single full stop satisfies
    any "does it contain a sentence" test, which is how the first attempt at this
    passed every homepage it was supposed to catch.
    """
    run = " ".join(["TC Genesis TC Track TC Landfall Bulletins Climatology"] * 30) + "."
    assert store.reads_like_a_document(run) is False


def test_furniture_is_stripped_from_the_front_and_the_document_kept():
    stripped = store.strip_furniture(MENU + " " + DOCUMENT)
    assert "Skip to main content" not in stripped
    assert "Screen Reader Access" not in stripped
    assert stripped.startswith("In accordance with international procedure")
    assert "cyclone warning centres" in stripped, "the document itself survives intact"


def test_stripping_only_removes_the_prefix_so_tables_survive():
    """A page about port signals carries the signal numbers in a table.

    Table cells are not prose, so anything that kept only prose would throw away
    exactly the part a fisherman needs. Only the leading menu is removed.
    """
    tail = " Signal No. 1 Signal No. 2 Signal No. 3 Danger Great Danger"
    stripped = store.strip_furniture(MENU + " " + DOCUMENT + tail)
    assert stripped.endswith(tail.strip())


def test_a_menu_only_document_is_excluded_from_retrieval():
    """The fault that was actually being served to people."""
    menu_doc = store.Document(
        id="menu-1", title="Some Authority Homepage", authority="Gov",
        url="https://example.gov.in/", text=MENU,
        http_status=200, content_sha256="a" * 64,
    )
    real_doc = store.Document(
        id="real-1", title="Port Warning Signals", authority="IMD",
        url="https://example.gov.in/port.php", text=DOCUMENT,
        http_status=200, content_sha256="b" * 64,
    )
    menu_doc.menu_only = not store.reads_like_a_document(menu_doc.text)
    real_doc.menu_only = not store.reads_like_a_document(real_doc.text)

    assert menu_doc.usable is False
    assert real_doc.usable is True

    hits = store.search("port warning signals hoisted at the port", corpus=[menu_doc, real_doc])
    titles = [
        (h.document.title if hasattr(h, "document") else h.get("title"))
        for h in hits
    ]
    assert "Some Authority Homepage" not in titles
    assert titles, "the real document is still found"


def test_provenance_and_content_are_judged_separately():
    """A menu keeps its honest provenance; it is simply not usable as evidence."""
    doc = store.Document(
        id="menu-2", title="Homepage", authority="Gov", url="https://example.gov.in/",
        text=MENU, http_status=200, content_sha256="c" * 64,
    )
    doc.menu_only = True
    assert doc.quarantined is False, "it really was fetched; nothing about it is forged"
    assert doc.verified is True, "so it stays verified"
    assert doc.usable is False, "but it is not fit to quote"


@pytest.mark.parametrize("text", ["", "   ", "Home About Contact"])
def test_nothing_and_near_nothing_are_not_documents(text):
    assert store.reads_like_a_document(text) is False


def test_text_that_already_starts_with_prose_is_left_alone():
    """The trimmer must not eat the opening of a clean document.

    A first pass used a 0.25 density bar, which is inside the range ordinary
    writing occupies: "The First Stage warning known as PRE CYCLONE WATCH issued
    72 hours in advance" measures 0.20, so its first three words were trimmed and
    the document lost the term it is about.
    """
    opening = (
        'The First Stage warning known as "PRE CYCLONE WATCH" issued 72 hours in '
        "advance contains early warning about the development of a cyclonic "
        "disturbance in the north Indian Ocean and the coastal belt likely to be "
        "affected by adverse weather over the following days."
    )
    assert store.strip_furniture(opening).startswith("The First Stage warning")


def test_a_document_opening_without_a_function_word_is_still_kept_whole():
    """"Discussions focused on..." opens on a content word and must survive."""
    opening = (
        "Discussions focused on strengthening cooperation in disaster preparedness "
        "and on the weather and climate services each country provides to its "
        "fishermen and farmers throughout the monsoon season."
    )
    assert store.strip_furniture(opening).startswith("Discussions focused on")
