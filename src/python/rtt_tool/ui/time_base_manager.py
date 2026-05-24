class TimeBaseManager:

    STEPS_US = [
        1, 2, 5,
        10, 20, 50,
        100, 200, 500,
        1000, 2000, 5000,
        10000, 20000, 50000,
        100000, 200000, 500000,
        1000000, 2000000, 5000000,
        10000000, 20000000, 50000000,
        100000000, 200000000, 500000000,
    ]

    def __init__(self, default_idx: int = 9):
        self._idx = default_idx

    @property
    def index(self) -> int:
        return self._idx

    @index.setter
    def index(self, value: int) -> None:
        self._idx = max(0, min(value, len(self.STEPS_US) - 1))

    def current_value(self) -> int:
        return self.STEPS_US[self._idx]

    def current_x_range_sec(self, h_divs: int = 10) -> float:
        return self.STEPS_US[self._idx] * h_divs / 1_000_000.0

    def step_up(self) -> bool:
        if self._idx < len(self.STEPS_US) - 1:
            self._idx += 1
            return True
        return False

    def step_down(self) -> bool:
        if self._idx > 0:
            self._idx -= 1
            return True
        return False

    @staticmethod
    def to_display_string(us_val: int) -> str:
        if us_val < 1000:
            return f"{us_val} µs/div"
        elif us_val < 1_000_000:
            return f"{us_val / 1000:.3g} ms/div"
        else:
            return f"{us_val / 1_000_000:.3g} s/div"
