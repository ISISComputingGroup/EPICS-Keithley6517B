import time
import unittest

from parameterized import parameterized
from utils.channel_access import ChannelAccess
from utils.ioc_launcher import get_default_ioc_dir
from utils.test_modes import TestModes
from utils.testing import get_running_lewis_and_ioc

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
        self.ca = ChannelAccess(
            default_timeout=5, device_prefix=DEVICE_PREFIX, default_wait_time=0.0
        )

    def test_WHEN_set_pv_is_set_THEN_pv_updated_func(self):
        self.ca.assert_setting_setpoint_sets_readback("VOLT:DC", "FUNC", "FUNC:SP", "VOLT")
        self.ca.assert_setting_setpoint_sets_readback("CURR:DC", "FUNC", "FUNC:SP", "CURR")

    @parameterized.expand([(10,), (5,)])
    def test_WHEN_set_pv_is_set_THEN_pv_updated_rang(self, setpoint):
        self.ca.process_pv("POLLING:DISABLE")
        self.ca.assert_setting_setpoint_sets_readback(
            setpoint, "CURR:DC:RANG", "CURR:DC:RANG:SP", str(setpoint) + ".0"
        )

    def test_WHEN_periodic_refresh_scanned_THEN_func_updated_and_errors_shown(self):
        # First lets make sure queue is clear
        self.ca.process_pv("POLLING:DISABLE")
        self.ca.assert_that_pv_exists("*CLS")
        self.ca.process_pv("*CLS")

        self.ca.assert_setting_setpoint_sets_readback("CURR:DC", "FUNC", "FUNC:SP", "CURR")
        # This will add errors in following sequence to the device: 2, 5, 10 which then should be read by PVs
        self._lewis.backdoor_run_function_on_device("add_mock_errors")
        # Note that behaviour below is strange due to SYST:ERR and STAT:QUE doing the same thing
        # and yet it was used seperately. This is to be discussed with the scientists and/or tested
        # on real Keithley. See manual: 14-124
        self.ca.assert_that_pv_is("SYST:ERR", 2, 3)
        self.ca.assert_that_pv_is("STAT:QUE", 5, 3)
        self.ca.assert_that_pv_is("SYST:ERR", 10, 3)

    @parameterized.expand([("BTN:CURR",), ("BTN:VOLT",)])
    def test_WHEN_button_pressed_THEN_queue_cleared(self, btn):
        # First lets make sure queue is clear
        self.ca.process_pv("POLLING:DISABLE")
        self.ca.assert_that_pv_exists("*CLS")
        self.ca.process_pv("*CLS")

        self._lewis.backdoor_run_function_on_device("add_mock_errors")
        self.ca.process_pv(btn)
        self.ca.assert_that_pv_is("SYST:ERR", 0)
        self.ca.assert_that_pv_is("STAT:QUE", 0)
        # This is to double check that REFRESH record didnt add errors as its set to scan 1 second
        time.sleep(1)
        self.ca.assert_that_pv_is("SYST:ERR", 0)
        self.ca.assert_that_pv_is("STAT:QUE", 0)

    @parameterized.expand(
        [
            ("BTN:CURR", "CURR", "CURR:DC:RANG", "0.02", 0),
            ("BTN:VOLT", "VOLT", "VOLT:DC:RANG", "2.0", 1),
        ]
    )
    def test_WHEN_button_current_pressed_THEN_PVs_set(
        self, btn, mode, rang_mode, setpoint, btn_status
    ):
        self.ca.process_pv("POLLING:DISABLE")
        self.ca.process_pv(btn)
        # Test above checks for CLS separately
        self.ca.assert_that_pv_is("FUNC", mode)
        # Currently hard-coded to 0.02 in IOC, change this test if this behaviour is changed
        self.ca.assert_that_pv_is(rang_mode, setpoint)
        # This PV is for OPI rule to show different RANG readback box. 0=CURR 1=VOLT
        self.ca.assert_that_pv_is("RANG:MODE", btn_status)

    def test_WHEN_errors_added_THEN_refresh_clears_queue_over_time(self):
        # First lets make sure queue is clear
        self.ca.process_pv("POLLING:DISABLE")
        self.ca.assert_that_pv_exists("*CLS")
        self.ca.process_pv("*CLS")

        self._lewis.backdoor_run_function_on_device("add_mock_errors")
        # REFRESH should clear errors added above within this time
        time.sleep(3)
        self.ca.assert_that_pv_is("SYST:ERR", 0)
        self.ca.assert_that_pv_is("STAT:QUE", 0)

    def button_and_check(self, expected_reading, button_pv):
        self.ca.process_pv("POLLING:DISABLE")
        self.ca.process_pv(button_pv)
        self.ca.assert_that_pv_is("READ", str(expected_reading))

    def test_WHEN_buttons_pressed_THEN_readings_read_from_device(self):
        self.ca.process_pv("POLLING:DISABLE")
        self._lewis.backdoor_set_on_device("random_mode", False)
        test_data_volt = [0.1, 1.1, 2.0, 2.5]
        test_data_curr = [0.005, 0.01, 0.02, 0.03]
        test_answer_expected_volt = test_data_volt[:-1] + [test_data_volt[-2]]
        test_answer_expected_curr = test_data_curr[:-1] + [test_data_curr[-2]]

        # Behaviour expected is that last value is above range so it should be clamped and device gives error
        # Second-to-last value is currently hard-coded max
        self._lewis.backdoor_run_function_on_device(
            "insert_mock_readings", (test_data_volt, "volt")
        )
        self._lewis.backdoor_run_function_on_device(
            "insert_mock_readings", (test_data_curr, "curr")
        )

        # Order of checking this should not matter
        volt = "BTN:VOLT"
        curr = "BTN:CURR"
        checking_order = (
            (0, volt),
            (1, volt),
            (0, curr),
            (2, volt),
            (1, curr),
            (2, curr),
            (3, curr),
            (3, volt),
        )
        for check in checking_order:
            index = check[0]
            context = check[1]
            self.button_and_check(
                test_answer_expected_volt[index]
                if context == volt
                else test_answer_expected_curr[index],
                context,
            )

    def button_and_check_reading(self, button, equals):
        self.ca.process_pv(button)
        # Give time for btn to process
        time.sleep(1)
        expected_reading = self.ca.get_pv_value("READ")
        # Reading would change in given time if continuous on
        time.sleep(3)
        if equals:
            self.ca.assert_that_pv_is("READ", expected_reading)
        else:
            self.ca.assert_that_pv_is_not("READ", expected_reading)

    def test_WHEN_one_shot_polling_set_THEN_read_only_on_demand(self):
        self._lewis.backdoor_set_on_device("random_mode", True)
        self.ca.process_pv("POLLING:DISABLE")
        self.ca.assert_that_pv_is("POLLING:MODE", "One-Shot")

        self.button_and_check_reading("BTN:CURR", True)
        self.button_and_check_reading("BTN:VOLT", True)

    def test_WHEN_continuous_polling_set_THEN_read_at_intervals(self):
        self._lewis.backdoor_set_on_device("random_mode", True)
        self.ca.process_pv("POLLING:ENABLE")
        self.ca.assert_that_pv_is("POLLING:MODE", "Continuous")

        self.button_and_check_reading("BTN:CURR", False)
        self.button_and_check_reading("BTN:VOLT", False)
