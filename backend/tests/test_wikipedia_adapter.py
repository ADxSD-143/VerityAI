import httpx
import pytest
import respx
from app.sources.wikipedia import WikipediaAdapter

WIKI = "https://en.wikipedia.org/w/api.php"
SEARCH_JSON = {"query": {"search": [{"title": "Paris"}]}}
EXTRACT_JSON = {
    "query": {
        "pages": [
            {
                "pageid": 12345,
                "title": "Paris",
                "extract": (
                    "Paris is the capital and largest city of France. "
                    "It sits on the Seine River in the north of the country."
                ),
            }
        ]
    }
}


@pytest.mark.asyncio
async def test_wikipedia_adapter_returns_passages_with_provenance():
    with respx.mock(assert_all_called=False) as mock:
        mock.get(WIKI, params__contains={"list": "search"}).mock(
            return_value=httpx.Response(200, json=SEARCH_JSON)
        )
        mock.get(WIKI, params__contains={"prop": "extracts"}).mock(
            return_value=httpx.Response(200, json=EXTRACT_JSON)
        )
        adapter = WikipediaAdapter(lang="en", user_agent="test/1.0", max_pages=1)
        async with httpx.AsyncClient() as client:
            result = await adapter.search("Paris is the capital of France", ["Paris"], client)

    assert result.status == "ok"
    assert result.passages
    passage = result.passages[0]
    assert passage.title == "Paris"
    assert passage.page_id == "12345"
    assert passage.url == "https://en.wikipedia.org/wiki/Paris"
    assert passage.publisher == "en.wikipedia.org"
    assert passage.retrieved_at


@pytest.mark.asyncio
async def test_wikipedia_adapter_missing_page_is_empty():
    with respx.mock(assert_all_called=False) as mock:
        mock.get(WIKI, params__contains={"list": "search"}).mock(
            return_value=httpx.Response(200, json=SEARCH_JSON)
        )
        mock.get(WIKI, params__contains={"prop": "extracts"}).mock(
            return_value=httpx.Response(
                200, json={"query": {"pages": [{"title": "Paris", "missing": True}]}}
            )
        )
        adapter = WikipediaAdapter(lang="en", user_agent="test/1.0", max_pages=1)
        async with httpx.AsyncClient() as client:
            result = await adapter.search("q", ["q"], client)

    assert result.status == "empty"
    assert result.passages == []


@pytest.mark.asyncio
async def test_wikipedia_adapter_search_failure_is_soft():
    with respx.mock(assert_all_called=False) as mock:
        mock.get(WIKI).mock(return_value=httpx.Response(500))
        adapter = WikipediaAdapter(lang="en", user_agent="test/1.0")
        async with httpx.AsyncClient() as client:
            result = await adapter.search("q", ["q"], client)

    assert result.status == "error"
    assert result.error
    assert result.passages == []
