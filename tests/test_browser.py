from gpt1.browser import BrowserSession


def test_browser_records_actions_and_fetches_content():
    fetched_urls = []

    def fake_fetcher(url: str) -> str:
        fetched_urls.append(url)
        return f"<h1>{url}</h1>"

    session = BrowserSession(base_url="https://example.com", fetcher=fake_fetcher)

    content = session.open_page("/docs")
    session.click("#cta")
    session.type_text("#input", "hello")

    assert "https://example.com/docs" in fetched_urls
    snapshot = session.snapshot()
    assert snapshot[0].action == "open"
    assert snapshot[1].action == "click"
    assert snapshot[2].value == "hello"
    assert "<h1>https://example.com/docs</h1>" in content
