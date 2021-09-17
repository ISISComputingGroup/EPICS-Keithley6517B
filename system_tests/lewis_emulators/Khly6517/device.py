from collections import OrderedDict
from .states import DefaultState
from lewis.devices import StateMachineDevice
import random


class SimulatedKhly6517(StateMachineDevice):

    def _initialize_data(self):
        self.function = 0
        self.latest_reading = 0
        self.idle = True
        self.volt_range = 0
        self.curr_range = 0
        self.error_queue = []

        # Mock data
        self.volt_values = []
        self.curr_values = []
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

    def substract_reading(self):
        if self.function == 0:
            self.volt_values = self.volt_values[1:]
        elif self.function == 1:
            self.curr_values = self.curr_values[1:]

    def get_mode_values(self):
        if self.function == 0:
            return [self.volt_range, self.volt_values]
        elif self.function == 1:
            return [self.curr_range, self.curr_values]

    def get_ranged_value(self, value):
        values = self.get_mode_values()
        if value > values[0]:
            # Parameter data out of range
            self.add_error(-222)
        return max(min(value, values[0]), 0)

    def add_random_reading(self):
        values = self.get_mode_values()
        values[1].append(random.random() * values[0])

    def measurement(self):
        if self.random_mode:
            self.add_random_reading()
        values = self.get_mode_values()
        if len(values[1]) > 0:
            self.latest_reading = self.get_ranged_value(values[1][0])
            self.substract_reading()
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
        if mode.lower() == "volt":
            self.volt_values += readings
        elif mode.lower() == "curr":
            self.curr_values += readings
