from unittest import mock

from prompt_toolkit.application import create_app_session
from prompt_toolkit.document import Document
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.validation import ValidationError
import pytest

from bacpy.cli import (
    ask_ok,
    cli_window,
    control_score_saving,
    Difficulty,
    get_toolbar,
    MainPromptValidator,
    player_name_getter,
    PlayerNameValidator,
    present_hints,
    present_ranking,
    present_score_and_saving_factory,
)
from bacpy.core import GuessRecord, NumberParams


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


# cli_window
# ----------


def test_cli_window(capfd):

    at_enter = "=== header ===\n"
    at_exit = "==============\n"

    @cli_window("header", fillchar="=", wing_size=3)
    def cli_func():
        assert capfd.readouterr().out == at_enter

    cli_func()
    assert capfd.readouterr().out == at_exit


# ask_ok
# ------


@mock.patch("bacpy.cli.prompt", autospec=True, side_effect=StopIteration)
def test_ask_ok__use_prompt_message(mock_prompt):
    with pytest.raises(StopIteration):
        ask_ok("message")

    assert mock_prompt.call_args == mock.call("message")


@pytest.mark.parametrize(
    "input_",
    ("yes", "ye", "y", "YeS", "yEs"),
)
def test_ask_ok__yes(input_, mock_input):
    mock_input.send_text(input_ + "\n")
    assert ask_ok("some prompt")


@pytest.mark.parametrize(
    "input_",
    ("no", "n", "No", "nO"),
)
def test_ask_ok__no(input_, mock_input):
    mock_input.send_text(input_ + "\n")
    assert not ask_ok("some prompt")


@pytest.mark.parametrize(
    "input_",
    ("yess", "nno", "1", ","),
)
def test_ask_ok__continue_when_invalid_input(input_, mock_input):
    mock_input.send_text(input_ + "\n\n")
    with pytest.raises(EOFError):
        ask_ok("some prompt")


@mock.patch("bacpy.cli.prompt", autospec=True)
def test_ask_ok__continue_on_KeyboardInterrupt(mock_prompt):
    def mock_prompt_side_effect():
        raise KeyboardInterrupt
        yield
    mock_prompt.side_effect = mock_prompt_side_effect()

    with pytest.raises(StopIteration):
        ask_ok("some prompt")


@pytest.mark.parametrize(
    "default",
    (True, False),
)
def test_ask_ok__default_return_on_empty_input(default, mock_input):
    mock_input.send_text("\n")
    assert ask_ok("some prompt", default=default) is default


@mock.patch("bacpy.cli.prompt", autospec=True)
def test_ask_ok__no_default_return_on_empty_input(mock_prompt):
    mock_prompt.side_effect = iter([""])
    with pytest.raises(StopIteration):
        ask_ok("some prompt", default=None)


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


# ===========
# Round tools
# ===========


# present_ranking
# ---------------


@mock.patch("bacpy.cli.ranking_table", autospec=True)
@mock.patch("bacpy.cli.pager", autospec=True)
def test_present_ranking(mock_pager, mock_ranking_table):
    ranking, table = object(), object()
    mock_ranking_table.return_value = table

    present_ranking(ranking)

    assert mock_ranking_table.call_args == mock.call(ranking)
    assert mock_pager.call_args == mock.call(table)


# control_score_saving
# --------------------


def test_control_score_saving__save_score():
    mock_save_score = mock.Mock()
    control_score_saving(mock_save_score, iter(["Bob"]))
    assert mock_save_score.call_args == mock.call(
        "Bob", present_ranking
    )


def test_control_score_saving__do_not_save_score_if_player_name_is_None():
    mock_save_score = mock.Mock()
    control_score_saving(mock_save_score, iter([None]))
    assert not mock_save_score.called


# present_and_save_score_factory
# ------------------------------


def test_present_and_save_score_factory__only_present_score_if_not_score_saver(capfd):
    present_score_and_saving = present_score_and_saving_factory(iter([]))
    present_score_and_saving(7, None)
    assert capfd.readouterr().out == "\n*** You guessed in 7 steps ***\n\n"


@mock.patch("bacpy.cli.control_score_saving", autospec=True)
def test_present_and_save_score_factory__call_control_score_saving_if_score_saver(
        mock_control_score_saving, capfd
):
    save_score, player_name_iter = object(), object()
    present_score_and_saving = present_score_and_saving_factory(player_name_iter)
    present_score_and_saving(5, save_score)

    assert capfd.readouterr().out == "\n*** You guessed in 5 steps ***\n\n"
    assert mock_control_score_saving.call_args == mock.call(
        save_score, player_name_iter
    )


# present_hints
# -------------


def test_present_hints__single_digits_hints(capfd):
    present_hints(GuessRecord("1234", 1, 2))
    assert capfd.readouterr().out == "bulls:  1, cows:  2\n"


def test_present_hints__double_digits_hints(capfd):
    present_hints(GuessRecord("123456789abcdefghijkl", 10, 11))
    assert capfd.readouterr().out == "bulls: 10, cows: 11\n"
