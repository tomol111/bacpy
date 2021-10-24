import inspect

from prompt_toolkit.application import create_app_session
from prompt_toolkit.document import Document
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.shortcuts import prompt as pt_prompt
from prompt_toolkit.validation import ValidationError
import pytest

from bacpy.cli import (
    ask_ok,
    cli_window,
    Difficulty,
    get_toolbar,
    MainPromptValidator,
    player_name_getter,
    PlayerNameValidator,
)
from bacpy.core import NumberParams


ARROW_UP = "\u001b[A"


# ========
# fixtures
# ========


@pytest.fixture(autouse=True, scope="function")
def mock_input():
    pipe_input = create_pipe_input()
    try:
        with create_app_session(input=pipe_input, output=DummyOutput()):
            yield pipe_input
    finally:
        pipe_input.close()


# =========
# CLI tools
# =========


def test_cli_window(capfd):

    at_enter = "=== header ===\n"
    at_exit = "==============\n"

    @cli_window("header", fillchar="=", wing_size=3)
    def cli_func():
        assert capfd.readouterr().out == at_enter

    cli_func()
    assert capfd.readouterr().out == at_exit


def test_ask_ok__prompt_message():
    prompt_message = "some prompt"

    def mock_prompt(message):
        assert message == prompt_message
        return "y"

    ask_ok(prompt_message, prompt_func=mock_prompt)


@pytest.mark.parametrize(
    "input_",
    ("yes", "ye", "y", "YeS", "yEs"),
)
def test_ask_ok__yes(input_):
    assert ask_ok("some prompt", prompt_func=lambda _: input_)


@pytest.mark.parametrize(
    "input_",
    ("no", "n", "No", "nO"),
)
def test_ask_ok__no(input_):
    assert not ask_ok("some prompt", prompt_func=lambda _: input_)


@pytest.mark.parametrize(
    "input_",
    ("yess", "nno", "1", ","),
)
def test_ask_ok__continue_when_invalid_input(input_):

    def mock_prompt():
        yield
        yield input_

    mock_prompt_iter = mock_prompt()
    next(mock_prompt_iter)
    with pytest.raises(StopIteration):
        ask_ok("some prompt", prompt_func=mock_prompt_iter.send)


def test_ask_ok__continue_on_KeyboardInterrupt():

    def mock_prompt():
        yield
        raise KeyboardInterrupt

    mock_prompt_iter = mock_prompt()
    next(mock_prompt_iter)
    with pytest.raises(StopIteration):
        ask_ok("some prompt", prompt_func=mock_prompt_iter.send)


@pytest.mark.parametrize(
    "default",
    (True, False),
)
def test_ask_ok__default_return(default):
    assert (
        ask_ok("some prompt", prompt_func=lambda _: "", default=default)
        == default
    )


def test_ask_ok__no_default_return():

    def mock_prompt():
        yield
        yield ""

    mock_prompt_iter = mock_prompt()
    next(mock_prompt_iter)
    with pytest.raises(StopIteration):
        ask_ok("some prompt", prompt_func=mock_prompt_iter.send, default=None)


def test_ask_ok__default_prompt(mock_input):
    assert (
        inspect.signature(ask_ok).parameters["prompt_func"].default
        == pt_prompt
    )

    prompt_message = "some prompt"
    mock_input.send_text("y\n")
    ask_ok(prompt_message)


# ===================
# Getting player name
# ===================


# PlayerNameValidator
# -------------------


@pytest.mark.parametrize(
    "name",
    ("abc", "abcdefghijk", "abcdefghijklmnopqrst")
)
def test_PlayerNameValidator__valid(name):
    PlayerNameValidator().validate(Document(name))


@pytest.mark.parametrize(
    "name",
    ("", "ab", "abcdefghijklmnopqrstu", "abcdefghijklmnopqrstuvwxyz")
)
def test_PlayerNameValidator__invalid(name):
    with pytest.raises(ValidationError):
        PlayerNameValidator().validate(Document(name))


# player_name_getter
# ------------------


def test_player_name_getter(mock_input):
    player_name_iter = player_name_getter()

    # parse name and confirm
    mock_input.send_text(
        "Tomek\n"
        "y\n"
    )
    assert next(player_name_iter) == "Tomek"

    # reuse
    mock_input.send_text(
        "Maciek\n"
        "y\n"
    )
    assert next(player_name_iter) == "Maciek"

    # don't parse invalid input
    mock_input.send_text(
        "D\n"
        "arek\n"
        "y\n"
    )
    assert next(player_name_iter) == "Darek"

    # not confirm and correct
    mock_input.send_text(
        "Tomek\n"
        "n\n"
        "Zosia\n"
        "y\n"
    )
    assert next(player_name_iter) == "Zosia"

    # return `None` on `EOFError`
    mock_input.send_text(
        "\n"
    )
    assert next(player_name_iter) is None

    # return `None` on `EOFError` while asking for confirmation
    mock_input.send_text(
        "Tomek\n"
        "\n"
    )
    assert next(player_name_iter) is None

    # history search
    mock_input.send_text(
        f"{ARROW_UP}\n"
        "y\n"
    )
    assert next(player_name_iter) == "Tomek"


# TODO: test `KeyboardInterrupt` handling


# ===========
# Main prompt
# ===========


# get_toolbar
# -----------


def test_get_toolbar():
    difficulty = NumberParams(
        Difficulty(4, 9), frozenset("123456789"), "[1-9]", "standard"
    )
    assert get_toolbar(difficulty) == (
        "Label: standard | Size: 4 | Digits: [1-9]"
    )


# MainPromptValidator
# -------------------


@pytest.mark.parametrize(
    ("input_", "difficulty"),
    (
        ("3621", NumberParams.standard(Difficulty(4, 8))),
        ("14829", NumberParams.standard(Difficulty(5, 9))),
    )
)
def test_MainPromptValidator__pass_on_valid_number(input_, difficulty):
    MainPromptValidator(difficulty).validate(Document(input_))


@pytest.mark.parametrize(
    "input_",
    ("3622", "14823", "1492")
)
def test_MainPromptValidator__raise_ValidationError_on_invalid_number(input_):
    difficulty = NumberParams.standard(Difficulty(4, 8))
    with pytest.raises(ValidationError):
        MainPromptValidator(difficulty).validate(Document(input_))


@pytest.mark.parametrize(
    "input_",
    (
        "!help",
        "! help ",
        "!help commands",
        "!restart -l",
        "!ra 'some difficulty'",
    )
)
def test_MainPromptValidator__pass_on_valid_command(input_):
    difficulty = NumberParams.standard(Difficulty(5, 10))
    MainPromptValidator(difficulty).validate(Document(input_))


@pytest.mark.parametrize(
    "input_",
    (
        "!help\\",  # No escaped character
        "!ra 'some difficulty",  # No clossing quotation
    )
)
def test_MainPromptValidator__raise_ValidationError_on_invalid_command(input_):
    difficulty = NumberParams.standard(Difficulty(3, 4))
    with pytest.raises(ValidationError):
        MainPromptValidator(difficulty).validate(Document(input_))
