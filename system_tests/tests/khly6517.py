import unittest

from utils.channel_access import ChannelAccess
from utils.ioc_launcher import get_default_ioc_dir
from utils.test_modes import TestModes
from utils.testing import get_running_lewis_and_ioc, skip_if_recsim
import time
import random

DEVICE_PREFIX = "KHLY6517_01"

IOCS = [
    {
        "name": DEVICE_PREFIX,
        "directory": get_default_ioc_dir("KHLY6517"),
        "macros": {},
        "emulator": "Khly6517",
    },
]

TEST_MODES = [TestModes.DEVSIM]


class Khly6517Tests(unittest.TestCase):
    """
    Tests for the Khly6517 IOC.
    """

    def setUp(self):
        self._lewis, self._ioc = get_running_lewis_and_ioc("Khly6517", DEVICE_PREFIX)
        self.ca = ChannelAccess(device_prefix=DEVICE_PREFIX)

    def set_pv(self, pvName, pvVal):
        self.ca.assert_that_pv_exists(pvName)
        self.ca.set_pv_value(pvName, pvVal)
        self.ca.process_pv(pvName)
        self.ca.assert_that_pv_is(pvName, pvVal)

    def set_and_check(self, setpointPVname, setpointPVvalue, checkPVname, checkPVvalue):
        # Sets the setpoint PV and checks if checkPV was updated to expected value
        self.ca.assert_that_pv_exists(setpointPVname)
        self.ca.assert_that_pv_exists(checkPVname)
        self.ca.set_pv_value(setpointPVname, setpointPVvalue)
        self.ca.process_pv(setpointPVname)
        self.ca.assert_that_pv_is(setpointPVname, setpointPVvalue)
        self.ca.process_pv(checkPVname)
        self.ca.assert_that_pv_is(checkPVname, checkPVvalue)

    def test_WHEN_set_pv_is_set_THEN_pv_updated_func(self):
        self.set_and_check("FUNC:SP", "VOLT:DC", "FUNC", "VOLT")
        self.set_and_check("FUNC:SP", "CURR:DC", "FUNC", "CURR")

    def test_WHEN_set_pv_is_set_THEN_pv_updated_rang(self):
        self.set_and_check("CURR:DC:RANG:SP", 10, "CURR:DC:RANG", "10.0")
        self.set_and_check("VOLT:DC:RANG:SP", 5, "VOLT:DC:RANG", "5.0")

    def test_WHEN_periodic_refresh_scanned_THEN_func_updated_and_errors_shown(self):
        # First lets make sure queue is clear
        self.ca.assert_that_pv_exists("*CLS")
        self.ca.process_pv("*CLS")

        self.set_pv("FUNC:SP", "CURR:DC")
        # This will add errors in following sequence to the device: 2, 5, 10 which then should be read by PVs
        self._lewis.backdoor_run_function_on_device("add_mock_errors")
        # Note that behaviour below is strange due to SYST:ERR and STAT:QUE doing the same thing
        # and yet it was used seperately. This is to be discussed with the scientists and/or tested
        # on real Keithley. See manual: 14-124
        self.ca.assert_that_pv_is("SYST:ERR", 2, 3)
        self.ca.assert_that_pv_is("STAT:QUE", 5, 3)
        self.ca.assert_that_pv_is("SYST:ERR", 10, 3)

    def test_WHEN_button_pressed_THEN_queue_cleared(self):
        # First lets make sure queue is clear
        self.ca.assert_that_pv_exists("*CLS")
        self.ca.process_pv("*CLS")

        self._lewis.backdoor_run_function_on_device("add_mock_errors")
        self.ca.process_pv("BTN:CURR")
        self.ca.assert_that_pv_is("SYST:ERR", 0)
        self.ca.assert_that_pv_is("STAT:QUE", 0)
        # This is to double check that REFRESH record didnt add errors as its set to scan 1 second
        time.sleep(1)
        self.ca.assert_that_pv_is("SYST:ERR", 0)
        self.ca.assert_that_pv_is("STAT:QUE", 0)

        # Check same things for other button
        self._lewis.backdoor_run_function_on_device("add_mock_errors")
        self.ca.process_pv("BTN:VOLT")
        self.ca.assert_that_pv_is("SYST:ERR", 0)
        self.ca.assert_that_pv_is("STAT:QUE", 0)
        time.sleep(1)
        self.ca.assert_that_pv_is("SYST:ERR", 0)
        self.ca.assert_that_pv_is("STAT:QUE", 0)

    def test_WHEN_button_current_pressed_THEN_PVs_set(self):
        self.ca.process_pv("BTN:CURR")
        # Test above checks for CLS separately
        self.ca.assert_that_pv_is("FUNC", "CURR")
        # Currently hard-coded to 0.02 in IOC, change this test if this behaviour is changed
        self.ca.assert_that_pv_is("CURR:DC:RANG", "0.02")
        # This PV is for OPI rule to show different RANG readback box. 0=CURR 1=VOLT
        self.ca.assert_that_pv_is("RANG:MODE", 0)

        # Now the other button. Same comments apply
        self.ca.process_pv("BTN:VOLT")
        self.ca.assert_that_pv_is("FUNC", "VOLT")
        self.ca.assert_that_pv_is("VOLT:DC:RANG", "2.0")
        self.ca.assert_that_pv_is("RANG:MODE", 1)

    def test_WHEN_errors_added_THEN_refresh_clears_queue_over_time(self):
        # First lets make sure queue is clear
        self.ca.assert_that_pv_exists("*CLS")
        self.ca.process_pv("*CLS")

        self._lewis.backdoor_run_function_on_device("add_mock_errors")
        # REFRESH should clear errors added above within this time
        time.sleep(3)
        self.ca.assert_that_pv_is("SYST:ERR", 0)
        self.ca.assert_that_pv_is("STAT:QUE", 0)

    def button_and_check(self, expectedReading, buttonPV):
        self.ca.process_pv(buttonPV)
        self.ca.assert_that_pv_is("READ", str(expectedReading))

    def test_WHEN_buttons_pressed_THEN_readings_read_from_device(self):
        self._lewis.backdoor_set_on_device("random_mode", False)
        test_data_volt = [0.1, 1.1, 2.0, 2.5]
        test_data_curr = [0.005, 0.01, 0.02, 0.03]
        test_answer_expected_volt = test_data_volt[:-1] + [test_data_volt[-2]]
        test_answer_expected_curr = test_data_curr[:-1] + [test_data_curr[-2]]

        # Behaviour expected is that last value is above range so it should be clamped and device gives error
        # Second-to-last value is currently hard-coded max
        self._lewis.backdoor_run_function_on_device("insert_mock_readings", (test_data_volt, "volt"))
        self._lewis.backdoor_run_function_on_device("insert_mock_readings", (test_data_curr, "curr"))

        # Order of checking this should not matter
        volt = "BTN:VOLT"
        curr = "BTN:CURR"
        checkingOrder = ((0, volt), (1, volt), (0, curr), (2, volt), (1, curr), (2, curr), (3, curr), (3, volt))
        for i in range(len(test_data_volt) + len(test_data_curr)):
            if checkingOrder[i][1] == volt:
                self.button_and_check(test_answer_expected_volt[checkingOrder[i][0]], volt)
            elif checkingOrder[i][1] == curr:
                self.button_and_check(test_answer_expected_curr[checkingOrder[i][0]], curr)
