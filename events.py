"""This file define game game events and other exceptions"""


class GameEvent(Exception):
    """Base game event class."""
    pass


class QuitGame(GameEvent):
    """Quit game event."""
    pass


class RestartGame(GameEvent):
    """Restart game event."""
    pass

class CancelOperation(GameEvent):
    """Operation canceled event."""
    pass
