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

    def getRangedValue(self, value, mode):
        if mode.lower() == "volt":
            if value > self.volt_range:
                # Parameter data out of range
                self.add_error(-222)
            return max(min(value, self.volt_range), 0)
        elif mode.lower() == "curr":
            if value > self.curr_range:
                # Parameter data out of range
                self.add_error(-222)
            return max(min(value, self.curr_range), 0)

    def measurement(self):
        if self.function == 0:
            if self.random_mode:
                self.volt_values.append(random.random() * self.volt_range)
            if len(self.volt_values) > 0:
                self.latest_reading = self.getRangedValue(self.volt_values[0], "volt")
                self.volt_values = self.volt_values[1:]
            else:
                self.latest_reading = 0
        elif self.function == 1:
            if self.random_mode:
                self.curr_values.append(random.random() * self.curr_range)
            if len(self.curr_values) > 0:
                self.latest_reading = self.getRangedValue(self.curr_values[0], "curr")
                self.curr_values = self.curr_values[1:]
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
