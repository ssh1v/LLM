from app.bot import handlers
from tests.conftest import FakeMessage, make_token


async def test_token_command_saves_token(fake_redis):
    token = make_token(sub="555")
    message = FakeMessage(f"/token {token}", user_id=555)

    await handlers.cmd_token(message)

    stored = await fake_redis.get("token:555")
    assert stored == token
    assert message.answers  # пользователю отправлено подтверждение


async def test_text_without_token_does_not_call_celery(mocker):
    spy = mocker.patch("app.bot.handlers.llm_request")
    message = FakeMessage("Привет", user_id=777)

    await handlers.handle_text(message)

    spy.delay.assert_not_called()
    assert "токен" in message.answers[0].lower()


async def test_text_with_token_calls_celery(fake_redis, mocker):
    token = make_token(sub="888")
    await fake_redis.set("token:888", token)
    spy = mocker.patch("app.bot.handlers.llm_request")

    message = FakeMessage("Напиши годы жизни Л. Н. Толстого", user_id=888, chat_id=999)
    await handlers.handle_text(message)

    spy.delay.assert_called_once_with(999, "Напиши годы жизни Л. Н. Толстого")
    assert any("принят" in a.lower() for a in message.answers)
