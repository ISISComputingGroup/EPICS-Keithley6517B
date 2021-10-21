from collections import OrderedDict
from .states import DefaultState
from lewis.devices import StateMachineDevice
import random
import queue


class Measurement:
    def __init__(self, name):
        self.name = name
        self.range = 0
        self.values = queue.Queue()


class SimulatedKhly6517(StateMachineDevice):

    def _initialize_data(self):
        self.latest_reading = 0
        self.idle = True

        self.volt_data = Measurement("volt")
        self.curr_data = Measurement("curr")
        self.mode_dict = {measure.name: measure for measure in [self.volt_data, self.curr_data]}
        self.selected_data = self.volt_data

        self.error_queue = []

        # Mock data
        self.random_mode = True

    def _get_state_handlers(self):
        return {
            'default': DefaultState(),
        }

    def _get_initial_state(self):
        return 'default'

    def _get_transition_handlers(self):
        return OrderedDict([])

    # This command does not trigger a new reading, only return last reading
    def fetch(self):
        return self.latest_reading

    def abort(self):
        self.idle = True
        self.latest_reading = 0

    def initiate(self):
        self.idle = False
        self.measurement()

    def get_selected_ranged_value(self):
        value = self.selected_data.values.get()
        if value > self.selected_data.range:
            # Parameter data out of range
            self.add_error(-222)
        return max(min(value, self.selected_data.range), 0)

    def add_random_reading(self):
        self.selected_data.values.put(random.random() * self.selected_data.range)

    def measurement(self):
        if self.random_mode:
            self.add_random_reading()
        if not self.selected_data.values.empty():
            self.latest_reading = self.get_selected_ranged_value()
        else:
            self.latest_reading = 0

    def add_error(self, error):
        if len(self.error_queue) < 9:
            self.error_queue.append(error)
        elif len(self.error_queue) == 9:
            # Queue overflow
            self.error_queue.append(-350)

    def get_error(self):
        if len(self.error_queue) > 0:
            error = self.error_queue[0]
            self.error_queue = self.error_queue[1:]
            return error
        else:
            return 0

    def clear_error_queue(self):
        self.error_queue = []

    def add_mock_errors(self):
        self.add_error(2)
        self.add_error(5)
        self.add_error(10)

    def insert_mock_readings(self, readings, mode):
        [self.mode_dict[mode.lower()].values.put(reading) for reading in readings]
