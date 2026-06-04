import queue
import random
from collections import OrderedDict
from typing import Callable

from lewis.core.statemachine import State
from lewis.devices import StateMachineDevice

from .states import DefaultState


class Measurement:
    def __init__(self, name: str) -> None:
        self.name = name
        self.range = 0
        self.values = queue.Queue()


class SimulatedKhly6517(StateMachineDevice):
    def _initialize_data(self) -> None:
        self.latest_reading = 0
        self.idle = True

        self.volt_data = Measurement("volt")
        self.curr_data = Measurement("curr")
        self.mode_dict = {measure.name: measure for measure in [self.volt_data, self.curr_data]}
        self.selected_data = self.volt_data

        self.error_queue = []

        self.curr_autorange = False
        self.zero_check = False

        # Mock data
        self.random_mode = True

    def _get_state_handlers(self) -> dict[str, State]:
        return {
            "default": DefaultState(),
        }

    def _get_initial_state(self) -> str:
        return "default"

    def _get_transition_handlers(self) -> dict[tuple[str, str], Callable[[], bool]]:
        return OrderedDict([])

    # This command does not trigger a new reading, only return last reading
    def fetch(self) -> float:
        return self.latest_reading

    def abort(self) -> None:
        self.idle = True
        self.latest_reading = 0

    def initiate(self) -> None:
        self.idle = False
        self.measurement()

    def get_selected_ranged_value(self) -> float:
        value = self.selected_data.values.get()
        if value > self.selected_data.range:
            # Parameter data out of range
            self.add_error(-222)
        return max(min(value, self.selected_data.range), 0)

    def add_random_reading(self) -> None:
        self.selected_data.values.put(random.random() * self.selected_data.range)

    def measurement(self) -> None:
        if self.random_mode:
            self.add_random_reading()
        if not self.selected_data.values.empty():
            self.latest_reading = self.get_selected_ranged_value()
        else:
            self.latest_reading = 0

    def add_error(self, error: int) -> None:
        if len(self.error_queue) < 9:
            self.error_queue.append(error)
        elif len(self.error_queue) == 9:
            # Queue overflow
            self.error_queue.append(-350)

    def get_error(self) -> int:
        if len(self.error_queue) > 0:
            error = self.error_queue[0]
            self.error_queue = self.error_queue[1:]
            return error
        else:
            return 0

    def clear_error_queue(self) -> None:
        self.error_queue = []

    def add_mock_errors(self) -> None:
        self.add_error(2)
        self.add_error(5)
        self.add_error(10)

    def insert_mock_readings(self, readings: list[float], mode: str) -> None:
        [self.mode_dict[mode.lower()].values.put(reading) for reading in readings]
