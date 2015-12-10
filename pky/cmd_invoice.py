#!/usr/bin/python
# vim:fileencoding=utf-8:et:ts=4:sw=4:sts=4
#
# Copyright (C) 2015 Markus Lehtonen <knaeaepae@gmail.com>
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
"""The 'invoice' command"""
import os
from collections import defaultdict
from datetime import datetime

from .common import ask_value, std_date, CmdBase, EmailGroup


DEFAULT_DETAILS_TEMPLATE = u"""
Selite: %(selite)s
Saaja: Polyteknikkojen Kuoron kannatusyhdistys ry
Pankkiyhteys: Nordea
Tilinumero: FI14 1112 3000 3084 34
Viitenumero: %(viitenro)s
Summa: %(summa)s
Eräpäivä: %(eräpäivä)s
"""

FOOTER = u"""

Parhain terveisin,
  Markus Lehtonen
  PKY
"""

class CmdInvoice(CmdBase):
    """Functionality for 'invoice' command"""
    log_fields = ['nro', 'selite', 'summa', 'viitenro']

    @staticmethod
    def range_to_filter(range_str):
        """Convert integer range string into filter value"""
        values = []
        ranges = range_str.split(',')
        for ran in ranges:
            split = ran.split('-', 1)
            if len(split) == 1:
                values.append([int(split[0])])
            else:
                values.append(xrange(int(split[0]), int(split[1]) + 1))
        return values

    def subject_prefix(self):
        """Get subject prefif"""
        if self.args.subject_prefix is not None:
            subject_prefix = self.args.subject_prefix
        elif self.args.reminder and 'reminder-subject-prefix' in self.config:
            subject_prefix = self.config['reminder-subject-prefix']
        else:
            subject_prefix = self.config['subject-prefix']
        subject_prefix = subject_prefix + ' ' if subject_prefix else ''
        return subject_prefix

    def filter_data(self, rows):
        """Create message filters"""
        # Additional filters
        filters = defaultdict(list)
        if self.args.filter_by and self.args.filter_value:
            filters[self.args.filter_by] = [self.args.filter_value]
        if self.args.index:
            filters[u'nro'].extend(self.range_to_filter(self.args.index))
        if self.args.date or (not self.args.reminder and not filters):
            date = self.args.date or datetime.now().date()
            filters[u'pvm'].append([date])

        rows = [row for row in self._apply_filters(rows, filters)]

        # Special treatment if reminder emails are requested
        if self.args.reminder:
            # Only take rows whose due date has passed
            today = datetime.now().date()
            rows = [row for row in rows if
                        not row[u'maksettu'] and
                        std_date(row[u'eräpäivä']) < today]
            # Mangle due dates
            for row in rows:
                row[u'eräpäivä'] = 'HETI'
        return rows

    def group_data(self, rows):
        """Return grouped row data"""
        # Group data
        if self.args.group_by:
            group_dict = defaultdict(list)
            for row in rows:
                group_dict[row[self.args.group_by]].append(row)
            grouped_data = group_dict.values()
        else:
            grouped_data = [[row] for row in rows]

        groups = []
        for ind, group in enumerate(grouped_data, 1):
            if len(group) > 1:
                info_header = "#%d: INVOICE GROUP" % ind
                info_msg = "%s: %s\n" % (self.args.group_by.upper(),
                                     group[0][self.args.group_by])
            else:
                info_header = "#%d: SINGLE INVOICE" % ind
                info_msg = 'EMAIL: %(email)s\nVIITE: %(viite)s\n' \
                       'SUMMA:%(summa)s\n' % group[0]
            groups.append(EmailGroup(group, info_header, info_msg))
        return groups

    def get_message(self):
        """Get email message body template"""
        # Get greeting message
        if self.args.message:
            if os.path.isfile(self.args.message):
                with open(self.args.message) as fobj:
                    greeting_msg = fobj.read()
            else:
                greeting_msg = self.args.message
        else:
            greeting_msg = "Hei,\n\nOhessa lasku."
            greeting_msg = ask_value('Greeting message',
                                     default=greeting_msg)
            greeting_msg = greeting_msg.decode('string_escape')
        greeting_msg = greeting_msg.decode('utf-8')

        # Get invoice details template
        if self.args.msg_details:
            if os.path.isfile(self.args.msg_details):
                with open(self.args.msg_details) as fobj:
                    msg_details = fobj.read()
            else:
                msg_details = self.args.msg_details
            msg_details = msg_details.decode('utf-8')
        else:
            msg_details = DEFAULT_DETAILS_TEMPLATE

        # Form message template
        return greeting_msg + u'\n' + msg_details + FOOTER

