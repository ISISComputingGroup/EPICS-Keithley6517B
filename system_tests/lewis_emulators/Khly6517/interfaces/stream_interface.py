from lewis.adapters.stream import StreamInterface, Cmd
from lewis.utils.command_builder import CmdBuilder
from lewis.core.logging import has_log


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
        return "{}".format(self._device.selected_data.name.upper())

    def get_read(self):
        self._device.abort()
        self._device.initiate()
        return "{}".format(self._device.fetch())

    def get_rang(self, mode):
        try:
            return self._device.mode_dict[mode.lower()].range
        except KeyError:
            # Program syntax error
            self._device.add_error(-285)
            return 0

    def set_rang(self, mode, rang):
        try:
            self._device.mode_dict[mode.lower()].range = rang
        except KeyError:
            # Program syntax error
            self._device.add_error(-285)

    def clear_error_queue(self):
        self._device.clear_error_queue()

    def set_func(self, mode):
        try:
            self._device.selected_data = self._device.mode_dict[mode.lower()]
        except KeyError:
            # Program syntax error
            self._device.add_error(-285)

    def get_err(self):
        return self._device.get_error()
