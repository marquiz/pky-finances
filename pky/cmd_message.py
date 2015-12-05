#!/usr/bin/python
# vim:fileencoding=utf-8:et:ts=4:sw=4:sts=4
#
# Copyright (C) 2014-2015 Markus Lehtonen <knaeaepae@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""The 'message' command"""
import os

from .common import CmdBase, ask_value


class CmdMessage(CmdBase):
    """Baseclass for commands"""

    def get_message(self):
        """Get email message body template"""
        # Get greeting message
        if self.args.message:
            if os.path.isfile(self.args.message):
                with open(self.args.message) as fobj:
                    message = fobj.read()
            else:
                message = self.args.message
        else:
            message = ask_value('Greeting message')
            message = message.decode('string_escape')
        return message.decode('utf-8')


