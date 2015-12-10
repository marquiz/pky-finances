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
"""Send mmessages from a csv file"""

from datetime import datetime


class EmailGroup(object):
    """A group email"""
    def __init__(self, rows, info_header, info_msg):
        self.rows = rows
        self.info_header = info_header
        self.info_msg = info_msg


class CmdBase(object):
    """Baseclass for commands"""
    name = None
    log_fields = None

    def __init__(self, args, config):
        self.args = args
        self.config = config


    @staticmethod
    def _inside_filter_ranges(val, ranges):
        """Check if value is found in filter ranges"""
        for ran in ranges:
            if isinstance(ran[0], int):
                val = int(val)
            elif isinstance(ran[0], datetime):
                val = std_date(val)
            if val in ran:
                return True
        return False

    @staticmethod
    def _inside_filters(row, filters):
        """Check if row is inside all given filters"""
        for key, ranges in filters.iteritems():
            # All filters must pass
            if not CmdBase._inside_filter_ranges(row[key], ranges):
                return False
        return True

    @staticmethod
    def _apply_filters(rows, filters):
        """Filter row data with given filters"""
        # Check filter validity
        for key in filters:
            if key not in rows[0]:
                raise Exception("Invalid filter column name '%s'" % key)

        for row in rows:
            if row['email']:
                if filters:
                    if CmdBase._inside_filters(row, filters):
                        yield row
                else:
                    yield row

    def subject_prefix(self):
        """Get subject prefif"""
        if self.args.subject_prefix is not None:
            subject_prefix = self.args.subject_prefix
        else:
            subject_prefix = self.config['subject-prefix']
        subject_prefix = subject_prefix + ' ' if subject_prefix else ''
        return subject_prefix

    def filter_data(self, rows):
        """Filter data"""
        # Common filter argument
        if self.args.filter_by:
            filters = {self.args.filter_by: [self.args.filter_value]}
        else:
            filters = None
        return [row for row in self._apply_filters(rows, filters)]

    def group_data(self, rows):
        """Return grouped row data"""
        return [EmailGroup(rows, "", "")]


    def get_message(self):
        """Get email message body template"""
        raise NotImplementedError()


def std_date(date_str):
    """Convert string to date"""
    return datetime.strptime(date_str, '%d.%m.%Y').date()

def ask_value(question, default=None, choices=None):
    """Ask user input"""
    choice_str = ' (%s)' % '/'.join(choices) if choices else ''
    default_str = ' [%s]' % default if default is not None else ''
    while True:

        val = raw_input(question + '%s:%s ' % (choice_str, default_str))
        if val:
            if not choices or val in choices:
                return val
        elif default is not None:
            return default

