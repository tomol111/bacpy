from bacpy.cli import (
    cli_window,
)


# =========
# CLI tools
# =========
"""
class cli_window(ContextDecorator):

    def __init__(
            self, header: str,
            fillchar: str = "=",
            wing_size: int = 5,
    ) -> None:
        self.header = header
        self.fillchar = fillchar
        self.wing_size = wing_size
        self.width = len(header) + 2 * (wing_size + 1)  # +1 is for space

    def __enter__(self):
        wing = self.fillchar * self.wing_size
        print(f"\n{wing} {self.header} {wing}")
        return self

    def __exit__(self, *exc):
        print(self.fillchar * self.width)
        return False
"""


def test_cli_window(capfd):

    at_enter = "=== header ===\n"
    at_exit = "==============\n"

    @cli_window("header", fillchar="=", wing_size=3)
    def cli_func():
        assert capfd.readouterr().out == at_enter

    cli_func()
    assert capfd.readouterr().out == at_exit
