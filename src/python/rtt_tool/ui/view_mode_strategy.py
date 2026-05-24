from abc import ABC, abstractmethod


class ViewModeStrategy(ABC):

    @abstractmethod
    def activate(self, plot_widget, channels) -> None:
        pass

    @abstractmethod
    def deactivate(self, plot_widget) -> None:
        pass

    @abstractmethod
    def apply_time_base(self, plot_widget, time_base_us: int,
                        center_x: float) -> None:
        pass

    @abstractmethod
    def update_view_range(self, plot_widget,
                          x_min: float, x_max: float,
                          y_min: float, y_max: float) -> None:
        pass

    @abstractmethod
    def handle_wheel(self, plot_widget, delta: int,
                     current_tb_idx: int) -> int:
        pass

    @abstractmethod
    def set_drag_enabled(self, plot_widget,
                         x_enabled: bool, y_enabled: bool) -> None:
        pass
