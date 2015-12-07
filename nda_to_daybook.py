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
"""Handle bank account statement in NDA format"""

import argparse
import csv
import sys
from datetime import datetime


def nda_str_decode(string):
    """Decode Scandic letters"""
    return string.replace('{', 'ä').replace('[', 'Ä').replace('\\', 'Ö')


def parse_transactions(filepath):
    """Parse transaction records out of a bank statement in NDA format"""
    tr_list = []
    with open(filepath) as fobj:
        for line in fobj.readlines():
            rec_type = line[1:6]
            if rec_type == '10188' and line[187] == ' ':
                amount = float(line[87:106]) / 100
                new_tr = {
                        'index': int(line[6:12]),
                        'amount': amount,
                        'amount_str': '%.2f' % amount,
                        'name': nda_str_decode(line[108:143].strip()),
                        'reference': line[160:180].strip().lstrip('0'),
                        'date': datetime.strptime(line[30:36], '%y%m%d'),
                        }
                tr_list.append(new_tr)
    return tr_list


def parse_args(argv):
    """Parse command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument('-H', '--human-readable', action='store_true',
                        help='Simple human readable output of the transactions')
    parser.add_argument('nda',
                        help='Nordea bank statement in NDA format')
    return parser.parse_args(argv[1:])


def main(argv=None):
    """Script entry point"""
    args = parse_args(argv)

    trs = parse_transactions(args.nda)

    if args.human_readable:
        for tra in trs:
            print '%3d %s %+9.2f %6s %s' % (
                    tra['index'],
                    tra['date'].strftime('%d.%m'),
                    tra['amount'],
                    tra['reference'],
                    tra['name'])
    else:
        writer = csv.writer(sys.stdout)
        for tra in trs:
            if tra['amount'] > 0:
                debit = tra['amount_str']
                credit = ''
            else:
                debit = ''
                credit = tra['amount_str']
            writer.writerow(['', tra['date'].strftime('%d.%m.%Y'), '1910',
                            '', debit, credit, tra['reference']])
            # Write another row with countered debit and credit
            if debit:
                debit = '-' + debit
            if credit:
                credit = credit.lstrip('-')
            writer.writerow(['', '', '', '', credit, debit, ''])

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
