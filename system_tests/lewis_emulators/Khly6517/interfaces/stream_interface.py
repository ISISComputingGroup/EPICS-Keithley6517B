import logging
import typing

from lewis.adapters.stream import StreamInterface
from lewis.core.logging import has_log
from lewis.utils.command_builder import CmdBuilder

if typing.TYPE_CHECKING:
    from ..device import SimulatedKhly6517


@has_log
class Khly6517StreamInterface(StreamInterface):
    commands = {
        CmdBuilder("get_func").regex("FUNC\?").eos().build(),
        CmdBuilder("get_read").escape("READ?").eos().build(),
        CmdBuilder("get_rang").arg("CURR|VOLT").escape(":DC:RANGE?").eos().build(),
        CmdBuilder("clear_error_queue").escape("*CLS").eos().build(),
        CmdBuilder("set_func").escape("FUNC '").arg("CURR|VOLT").escape(":DC'").eos().build(),
        CmdBuilder("set_rang").arg("CURR|VOLT").escape(":DC:RANG ").float().eos().build(),
        CmdBuilder("set_rang").arg("curr|volt").escape(":dc:rang ").float().eos().build(),
        # According to the manual, SYST:ERR? and STAT:QUE?
        # perform the same function (14-124 in manual)
        CmdBuilder("get_err")
        .escape(":SYST")
        .optional("em")
        .escape(":ERR")
        .optional("or")
        .escape("?")
        .eos()
        .build(),
        CmdBuilder("get_err")
        .escape(":STAT")
        .optional("us")
        .escape(":QUE")
        .optional("ue")
        .escape("?")
        .eos()
        .build(),
        CmdBuilder("get_zero_check").escape(":SYST:ZCH?").eos().build(),
        CmdBuilder("set_zero_check").escape(":SYST:ZCH ").any().eos().build(),
        CmdBuilder("get_curr_autorange").escape(":SENS:CURR:RANG:AUTO?").eos().build(),
        CmdBuilder("set_curr_autorange").escape(":SENS:CURR:RANG:AUTO ").any().eos().build(),
    }

    in_terminator = "\r\n"
    out_terminator = "\r\n"

    _device: "SimulatedKhly6517"
    log: logging.Logger

    def handle_error(self, request: str, error: Exception) -> None:
        self.log.error("An error occurred at request " + repr(request) + ": " + repr(error))

    def catch_all(self, command: str) -> None:
        pass

    def get_func(self) -> str:
        return "{}".format(self._device.selected_data.name.upper())

    def get_read(self) -> str:
        self._device.abort()
        self._device.initiate()
        return "{}".format(self._device.fetch())

    def get_rang(self, mode: str) -> float:
        try:
            return self._device.mode_dict[mode.lower()].range
        except KeyError:
            # Program syntax error
            self._device.add_error(-285)
            return 0

    def set_rang(self, mode: str, rang: float) -> None:
        try:
            self._device.mode_dict[mode.lower()].range = rang
        except KeyError:
            # Program syntax error
            self._device.add_error(-285)

    def clear_error_queue(self) -> None:
        self._device.clear_error_queue()

    def set_func(self, mode: str) -> None:
        try:
            self._device.selected_data = self._device.mode_dict[mode.lower()]
        except KeyError:
            # Program syntax error
            self._device.add_error(-285)

    def get_err(self) -> int:
        return self._device.get_error()

    def get_curr_autorange(self) -> str:
        return "ON" if self._device.curr_autorange else "OFF"

    def set_curr_autorange(self, curr_autorange: str) -> None:
        self._device.curr_autorange = curr_autorange in ("ON", 1)

    def get_zero_check(self) -> str:
        return "ON" if self._device.zero_check else "OFF"

    def set_zero_check(self, zero_check: str) -> None:
        self._device.zero_check = zero_check in ("ON", 1)
