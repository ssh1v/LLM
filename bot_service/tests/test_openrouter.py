import httpx
import respx

from app.core.config import settings
from app.services.openrouter_client import call_openrouter


@respx.mock
def test_call_openrouter_returns_text():
    url = f"{settings.openrouter_base_url}/chat/completions"
    route = respx.post(url).mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Лев Толстой: 1828-1910."}}]},
        )
    )

    result = call_openrouter("Годы жизни Толстого?")

    assert result == "Лев Толстой: 1828-1910."
    assert route.called


@respx.mock
def test_call_openrouter_non_200_raises():
    url = f"{settings.openrouter_base_url}/chat/completions"
    respx.post(url).mock(return_value=httpx.Response(500, text="boom"))

    try:
        call_openrouter("ping")
        raised = False
    except RuntimeError:
        raised = True
    assert raised
