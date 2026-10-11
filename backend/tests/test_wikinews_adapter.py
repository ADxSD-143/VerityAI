import httpx
import respx
from app.config import Settings
from app.sources.registry import build_adapters
from app.sources.wikipedia import WikinewsAdapter, WikipediaAdapter


def test_wikipedia_adapter_default_host_is_unchanged():
    adapter = WikipediaAdapter(user_agent="test")
    assert adapter.host == "en.wikipedia.org"
    assert adapter.endpoint == "https://en.wikipedia.org/w/api.php"


async def test_wikinews_adapter_uses_wikinews_host_and_provenance():
    adapter = WikinewsAdapter(user_agent="test", max_pages=1)
    assert adapter.name == "wikinews"
    assert adapter.endpoint == "https://en.wikinews.org/w/api.php"

    search = {"query": {"search": [{"title": "Example news"}]}}
    extract = {
        "query": {
            "pages": [
                {
                    "pageid": 7,
                    "title": "Example news",
                    "extract": (
                        "This is a reasonably long sentence about the news event that "
                        "happened today in the city."
                    ),
                }
            ]
        }
    }

    def router(request):
        if request.url.params.get("list") == "search":
            return httpx.Response(200, json=search)
        return httpx.Response(200, json=extract)

    with respx.mock(assert_all_called=False) as mock:
        mock.get("https://en.wikinews.org/w/api.php").mock(side_effect=router)
        async with httpx.AsyncClient() as client:
            result = await adapter.search("news event", ["news event"], client)

    assert result.status == "ok"
    passage = result.passages[0]
    assert passage.source == "wikinews"
    assert passage.url.startswith("https://en.wikinews.org/wiki/")
    assert passage.publisher == "en.wikinews.org"


def test_registry_excludes_wikinews_by_default():
    adapters = build_adapters(Settings(verity_preload_models=False))
    assert [adapter.name for adapter in adapters] == [
        "wikipedia",
        "wikidata",
        "openalex",
        "factcheck",
    ]


def test_registry_includes_wikinews_when_enabled():
    adapters = build_adapters(
        Settings(verity_preload_models=False, verity_enable_wikinews=True)
    )
    assert "wikinews" in [adapter.name for adapter in adapters]
