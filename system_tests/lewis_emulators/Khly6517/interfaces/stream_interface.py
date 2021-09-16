from lewis.adapters.stream import StreamInterface, Cmd
from lewis.utils.command_builder import CmdBuilder
from lewis.core.logging import has_log
from lewis.utils.replies import conditional_reply
import random

functions = {0: 'VOLT', 1: 'CURR'}


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
        # According to the manual, SYST:ERR? and STAT:QUE? perform the same function (14-124 in manual)
        CmdBuilder("get_err").escape(":SYST").optional("em").escape(":ERR").optional("or").escape("?").eos().build(),
        CmdBuilder("get_err").escape(":STAT").optional("us").escape(":QUE").optional("ue").escape("?").eos().build(),
    }

    in_terminator = "\r\n"
    out_terminator = "\r\n"

    def handle_error(self, request, error):
        self.log.error("An error occurred at request " + repr(request) + ": " + repr(error))

    def catch_all(self, command):
        pass

    def get_func(self):
        return "{}".format(functions[self._device.function])

    def get_read(self):
        self._device.abort()
        self._device.initiate()
        return "{}".format(self._device.fetch())

    def get_rang(self, mode):
        if mode.lower() == "volt":
            return self._device.volt_range
        elif mode.lower() == "curr":
            return self._device.curr_range
        else:
            # Program syntax error
            self._device.add_error(-285)
            return 0

    def set_rang(self, mode, rang):
        if mode.lower() == "volt":
            self._device.volt_range = rang
        elif mode.lower() == "curr":
            self._device.curr_range = rang
        else:
            # Program syntax error
            self._device.add_error(-285)

    def clear_error_queue(self):
        self._device.clear_error_queue()

    def set_func(self, mode):
        if mode == "VOLT":
            self._device.function = 0
        elif mode == "CURR":
            self._device.function = 1
        else:
            # Program syntax error
            self._device.add_error(-285)

    def get_err(self):
        return self._device.get_error()
