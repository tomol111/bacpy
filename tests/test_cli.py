import inspect

from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.shortcuts import prompt as pt_prompt
import pytest

from bacpy.cli import (
    ask_ok,
    cli_window,
)


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


def test_ask_ok_prompt_message():
    prompt_message = "some prompt"

    def mock_prompt(message):
        assert message == prompt_message
        return "y"

    ask_ok(prompt_message, prompt_func=mock_prompt)


@pytest.mark.parametrize(
    "input_",
    ("yes", "ye", "y", " y", "y ", "YeS", "yEs"),
)
def test_ask_ok_yes(input_):
    assert ask_ok("some prompt", prompt_func=lambda _: input_)


@pytest.mark.parametrize(
    "input_",
    ("no", "n", " n", "n ", "No", "nO"),
)
def test_ask_ok_no(input_):
    assert not ask_ok("some prompt", prompt_func=lambda _: input_)


@pytest.mark.parametrize(
    "input_",
    ("yess", "nno", "1", ","),
)
def test_ask_ok_continue_when_invalid_input(input_):

    def mock_prompt():
        yield
        yield input_

    mock_prompt_iter = mock_prompt()
    next(mock_prompt_iter)
    with pytest.raises(StopIteration):
        ask_ok("some prompt", prompt_func=mock_prompt_iter.send)


def test_ask_ok_continue_on_KeyboardInterrupt():

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
def test_ask_ok_default_return(default):
    assert (
        ask_ok("some prompt", prompt_func=lambda _: "", default=default)
        == default
    )


def test_ask_ok_no_default_return():

    def mock_prompt():
        yield
        yield ""

    mock_prompt_iter = mock_prompt()
    next(mock_prompt_iter)
    with pytest.raises(StopIteration):
        ask_ok("some prompt", prompt_func=mock_prompt_iter.send, default=None)


def test_ask_ok_default_prompt(mock_input):
    assert (
        inspect.signature(ask_ok).parameters["prompt_func"].default
        == pt_prompt
    )

    prompt_message = "some prompt"
    mock_input.send_text("y\n")
    ask_ok(prompt_message)
