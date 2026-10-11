import httpx
import respx
from app.sources.factcheck import FactCheckAdapter
from app.sources.openalex import OpenAlexAdapter, abstract_from_inverted
from app.sources.wikidata import WikidataAdapter


def test_abstract_from_inverted_orders_by_position():
    assert abstract_from_inverted({"b": [1], "a": [0]}) == "a b"
    assert abstract_from_inverted(None) == ""
    assert abstract_from_inverted({}) == ""


async def test_openalex_success_keeps_provenance():
    adapter = OpenAlexAdapter(user_agent="test")
    payload = {
        "results": [
            {
                "id": "https://openalex.org/W1",
                "title": "A study of Paris",
                "publication_year": 1999,
                "primary_location": {
                    "landing_page_url": "https://example.org/w1",
                    "source": {"display_name": "Example Journal"},
                },
                "abstract_inverted_index": {
                    "Paris": [0], "is": [1], "the": [2], "capital": [3], "of": [4], "France": [5]
                },
            }
        ]
    }
    with respx.mock(assert_all_called=False) as mock:
        mock.get("https://api.openalex.org/works").mock(return_value=httpx.Response(200, json=payload))
        async with httpx.AsyncClient() as client:
            result = await adapter.search("Paris is the capital of France", ["q"], client)
    assert result.status == "ok"
    passage = result.passages[0]
    assert passage.text == "Paris is the capital of France"
    assert passage.url == "https://example.org/w1"
    assert passage.publisher == "Example Journal"
    assert passage.published_at == "1999"


async def test_openalex_failure_is_soft_error():
    adapter = OpenAlexAdapter(user_agent="test")
    with respx.mock(assert_all_called=False) as mock:
        mock.get("https://api.openalex.org/works").mock(return_value=httpx.Response(500))
        async with httpx.AsyncClient() as client:
            result = await adapter.search("x", ["x"], client)
    assert result.status == "error"
    assert result.passages == []


async def test_wikidata_success_renders_structured_facts():
    adapter = WikidataAdapter(user_agent="test")
    entity = {
        "id": "Q42",
        "labels": {"en": {"value": "Douglas Adams"}},
        "descriptions": {"en": {"value": "English writer"}},
        "claims": {
            "P569": [
                {
                    "mainsnak": {
                        "snaktype": "value",
                        "datavalue": {
                            "type": "time",
                            "value": {"time": "+1952-03-11T00:00:00Z"},
                        },
                    }
                }
            ],
            "P27": [
                {
                    "mainsnak": {
                        "snaktype": "value",
                        "datavalue": {"type": "wikibase-entityid", "value": {"id": "Q1"}},
                    }
                }
            ],
        },
    }

    def api_router(request):
        action = request.url.params.get("action")
        if action == "wbsearchentities":
            return httpx.Response(200, json={"search": [{"id": "Q42"}]})
        if action == "wbgetentities":
            return httpx.Response(
                200, json={"entities": {"Q1": {"labels": {"en": {"value": "United Kingdom"}}}}}
            )
        return httpx.Response(400)

    with respx.mock(assert_all_called=False) as mock:
        mock.get("https://www.wikidata.org/w/api.php").mock(side_effect=api_router)
        mock.get("https://www.wikidata.org/wiki/Special:EntityData/Q42.json").mock(
            return_value=httpx.Response(200, json={"entities": {"Q42": entity}})
        )
        async with httpx.AsyncClient() as client:
            result = await adapter.search("Douglas Adams was born in 1952.", ["q"], client)

    assert result.status == "ok"
    texts = [p.text for p in result.passages]
    assert any("date of birth" in t and "1952-03-11" in t for t in texts)
    assert any("United Kingdom" in t for t in texts)


async def test_wikidata_failure_is_soft_error():
    adapter = WikidataAdapter(user_agent="test")
    with respx.mock(assert_all_called=False) as mock:
        mock.get("https://www.wikidata.org/w/api.php").mock(return_value=httpx.Response(500))
        async with httpx.AsyncClient() as client:
            result = await adapter.search("Douglas Adams was born in 1952.", ["q"], client)
    assert result.status == "error"
    assert result.passages == []


async def test_factcheck_returns_publisher_verdicts_separately():
    adapter = FactCheckAdapter(user_agent="test", api_key="dummy")
    payload = {
        "claims": [
            {
                "text": "Some claim",
                "claimReview": [
                    {
                        "publisher": {"name": "Example FC"},
                        "textualRating": "False",
                        "url": "https://fc.example/1",
                        "reviewDate": "2020-01-01",
                    }
                ],
            }
        ]
    }
    with respx.mock(assert_all_called=False) as mock:
        mock.get("https://factchecktools.googleapis.com/v1alpha1/claims:search").mock(
            return_value=httpx.Response(200, json=payload)
        )
        async with httpx.AsyncClient() as client:
            result = await adapter.search("Some claim", ["Some claim"], client)
    assert result.status == "ok"
    assert result.passages == []
    assert result.fact_checks[0].publisher == "Example FC"
    assert result.fact_checks[0].publisher_verdict == "False"


async def test_factcheck_skipped_without_key():
    adapter = FactCheckAdapter(user_agent="test", api_key=None)
    async with httpx.AsyncClient() as client:
        result = await adapter.search("x", ["x"], client)
    assert result.status == "skipped"
    assert result.fact_checks == []


async def test_factcheck_failure_is_soft_error():
    adapter = FactCheckAdapter(user_agent="test", api_key="dummy")
    with respx.mock(assert_all_called=False) as mock:
        mock.get("https://factchecktools.googleapis.com/v1alpha1/claims:search").mock(
            return_value=httpx.Response(500)
        )
        async with httpx.AsyncClient() as client:
            result = await adapter.search("x", ["x"], client)
    assert result.status == "error"
