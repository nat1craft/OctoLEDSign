from enum import IntEnum

class AlignX(IntEnum):
    CENTER = 0
    MIDDLE = 0
    LEFT = 1
    RIGHT = 2

class AlignY(IntEnum):
    MIDDLE = 0
    CENTER = 0
    TOP = 1
    BOTTOM = 2

class SignFont(IntEnum):
    TINY = 0
    NORMAL = 10
    LARGE = 20
    CUSTOM = 30
    DEFAULT = 0

class SignScroll(IntEnum):
    NO = 0
    YES = 1
    AUTO = 2

class ClipDirection(IntEnum):
    NONE = 0
    X = 1
    X_LOW = 2
    X_HIGH = 3
    Y = 10
    Y_LOW = 11
    Y_HIGH = 12
    XY = 20
