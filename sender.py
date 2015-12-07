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
"""Helper for sending PKY invoices"""

import argparse
import email.charset
import csv
import os
import re
import smtplib
import string
import sys
from ConfigParser import ConfigParser
from datetime import datetime
from email.header import Header
from email.mime.text import MIMEText

from pky.cmd_message import CmdMessage
from pky.cmd_invoice import CmdInvoice
from pky.common import ask_value, std_date


def write_log_entry(log_f, status, row_data, fields):
    """Write entry to log file"""
    email_addr = split_email_address(row_data['email'])[1]
    details = ' '.join([u'%s: %s' % (field, row_data[field]) for
                field in fields])
    log_f.write(('%s to %s: %s\n' %
                (status, email_addr, details)).encode('utf-8'))


def compose_email(headers, message):
    """Compose email text"""
    msg = MIMEText(message, _charset='utf-8')
    for key, val in headers.iteritems():
        msg[key.capitalize()] = val
    return msg


def pprint_email(msg):
    """Pretty print email"""
    for key, val in msg.items():
        # Filter out uninteresting parts
        if key.lower() not in ['content-type', 'mime-version',
                               'content-transfer-encoding']:
            print '%s: %s' % (key, unicode(val))
    print ""
    print msg.get_payload(decode=True)


def utf8_reader(input_stream, dialect=None):
    """Wrapper for reading UTF8-encoded csv files"""
    reader = csv.reader(input_stream, dialect=dialect)
    for row in reader:
        yield [unicode(cell, 'utf-8') for cell in row]


def to_u(text):
    """Convert text to unicode, assumes UTF-8 for str input"""
    if isinstance(text, str):
        return unicode(text, 'utf-8')
    else:
        return unicode(text)


def utf8_header(text):
    """Email header wih UTF-8 encoding"""
    # Convert text to unicode (assume we're using UTF-8)
    return Header(to_u(text), 'utf-8')


def utf8_address_header(addr):
    """Create an internationalized header from name, email tuple"""
    if isinstance(addr, tuple) or isinstance(addr, basestring):
        addr = [addr]

    header = utf8_header('')
    for address in addr:
        if isinstance(address, basestring):
            name, email_addr = split_email_address(address)
        else:
            name, email_addr = address
        if str(header):
            header.append(u', ')
        if name:
            header.append(to_u(name))
            header.append(to_u(' <%s>' % email_addr))
        else:
            header.append(to_u(email_addr))
    return header


def split_email_address(text):
    """Split name and address out of an email address

    >>> split_email_address('foo@bar.com')
    ('', 'foo@bar.com')
    >>> split_email_address('Foo Bar foo@bar.com')
    ('Foo Bar', 'foo@bar.com')
    >>> split_email_address('  "Foo Bar" <foo@bar.com>, ')
    ('Foo Bar', 'foo@bar.com')
    """
    split = text.strip().rsplit(None, 1)
    email_re = r'.*?([^<%s]\S*@\S+[a-zA-Z])' % string.whitespace
    match = re.match(email_re, split[-1])
    if not match:
        raise Exception("Invalid email address: '%s'" % text)
    email_addr = match.group(1)

    name = ''
    if len(split) > 1:
        non_letter = string.punctuation + string.whitespace
        name_re = r'.*?([^%s].*[^%s])' % (non_letter, non_letter)
        match = re.match(name_re, split[0])
        if match:
            name = match.group(1)
    return (name, email_addr)


def parse_config(path, command):
    """Read config file"""
    defaults = {'smtp-server': '',
                'from': '',
                'subject-prefix': '',
                'log-dir': 'logs'}
    parser = ConfigParser(defaults)
    parser.add_section(command)

    filepath = os.path.join(path, 'sender.conf')
    confs = parser.read(filepath)
    if confs:
        print "Read config file %s" % confs
    else:
        print "Did not find config file %s" % filepath

    # Only use one section, i.e. that of the specified command
    return dict(parser.items(command))


def parse_args(argv):
    """Parse command line arguments"""
    main_parser = argparse.ArgumentParser()
    parser = main_parser
    parser.add_argument('-d', '--dry-run', action='store_true',
                        help='Do everything but send email')
    parser.add_argument('-l', '--log-dir',
                        help='Directory for log files')
    parser.add_argument('--from', dest='sender', type=split_email_address,
                        help="Sender's email")
    parser.add_argument('--cc', action='append', default=[],
                        type=split_email_address,
                        help='Carbon copy to this email')
    parser.add_argument('--bcc', action='append', default=[],
                        type=split_email_address,
                        help='Blind (hidden) carbon copy to this email')
    parser.add_argument('--smtp-server', help="Address of the SMTP server")
    parser.add_argument('--subject',
                        help="Messgae subject, used for all emails")
    parser.add_argument('--subject-prefix', metavar='PREFIX',
                        help='Prefix all email subjects with %(metavar)s')
    parser.add_argument('-F', '--filter-by', metavar='KEY',
                        help='Filter messages by this KEY')
    parser.add_argument('-f', '--filter-value', action='append',
                        help='Send rows having this value in the filter '
                             'column')
    parser.add_argument('csv',
                        help='CSV file containing invoice entries')

    subparsers = parser.add_subparsers()

    # 'invoice' subcommand
    parser = subparsers.add_parser('invoice', help='Send invoices from CSV')
    parser.add_argument('-m', '--message',
                        help='Greeting message, used for all invoices')
    parser.add_argument('--msg-details',
                        help='Invoice details template')
    parser.add_argument('-r', '--reminder', action='store_true',
                        help='Only send invoices whose due date has passed')
    parser.add_argument('-G', '--group-by', metavar='KEY', default='viite',
                        help='Mass-send invoices with the same value of KEY')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-D', '--date', type=std_date, action='append',
                       help='Send invoices having this date')
    group.add_argument('-I', '--index',
                       help='Send invoices having these index numbers')
    parser.set_defaults(cmd_class=CmdInvoice, cmd_name='invoice')

    # 'message' subcommand
    parser = subparsers.add_parser('message',
                                  help='Compose and send emails from CSV file')
    parser.add_argument('-m', '--message',
                        help='Message template')
    parser.set_defaults(cmd_class=CmdMessage, cmd_name='message')

    return main_parser.parse_args(argv[1:])


def main(argv=None):
    """Script entry point"""

    print "Welcome to PKY email sender!"

    args = parse_args(argv)
    config = parse_config(os.path.dirname(argv[0]), args.cmd_name)
    cmd = args.cmd_class(args)

    # Change email header encoding to QP for easier readability of raw data
    email.charset.add_charset('utf-8', email.charset.QP, email.charset.QP)

    with open(args.csv, 'r') as fobj:
        dialect = csv.Sniffer().sniff(fobj.read(512))
        fobj.seek(0)
        reader = utf8_reader(fobj, dialect)
        print "CSV file time stamp:", reader.next()[0]
        header_row = reader.next()
        headers = [val.lower() for val in header_row if val]

        all_data = []
        for row in reader:
            all_data.append(dict(zip([val.lower() for val in header_row], row)))

    send_data = cmd.filter_data(all_data)

    if not send_data:
        print "No messages to send, exiting"
        return 0

    # Get SMTP server
    if args.smtp_server:
        smtp_server = args.smtp_server
    else:
        smtp_server = config['smtp-server'] or ask_value('SMTP server')

    # Get sender email
    if args.sender:
        sender = args.sender
    else:
        if 'EMAIL' in os.environ:
            sender = os.environ['EMAIL']
        sender = split_email_address(config['from'] or
                                     ask_value('From', default=sender))

    server = smtplib.SMTP(smtp_server)

    # Get subject prefix
    if args.subject_prefix is not None:
        subject_prefix = args.subject_prefix
    else:
        subject_prefix = config['subject-prefix']
    subject_prefix = subject_prefix + ' ' if subject_prefix else ''

    # Open initialize log files
    log_dir = args.log_dir if args.log_dir else config['log-dir']
    log_dir = os.path.join(os.path.dirname(argv[0]), log_dir)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_f_basename = datetime.now().strftime('%Y-%m-%d-%H%M%S')
    if args.dry_run:
        log_f_basename += '-dry-run'
    log_f = open(os.path.join(log_dir, log_f_basename + '.log'), 'w')
    log_fields = cmd.log_fields or headers[0:3]
    emails_f = open(os.path.join(log_dir, log_f_basename + '-emails.txt'), 'w')

    try:
        groups = cmd.group_data(send_data)

        # Send grouped emails
        for group in groups:
            rows = group.rows
            if group.info_header:
                print "\n==== " + group.info_header + " " + \
                        "="*(76-5-len(group.info_header))
                print group.info_msg

            # Email headers
            headers = {'from': utf8_address_header(sender)}

            if args.subject:
                headers['subject'] = utf8_header(subject_prefix + args.subject)
            else:
                headers['subject'] = utf8_header(subject_prefix +
                                                 ask_value('Subject'))
            if args.cc:
                headers['cc'] = utf8_address_header(args.cc)
            if args.bcc:
                headers['bcc'] = utf8_address_header(args.bcc)

            # Get message body
            message = cmd.get_message()

            # Ask for confirmation
            headers['to'] = utf8_address_header(rows[0]['email'])
            example = compose_email(headers, message % rows[0])
            print '\n' + '-' * 79
            pprint_email(example)
            print '-' * 79 + '\n'
            recipients = ['<%s>' % split_email_address(row['email'])[1] for
                            row in rows]
            proceed = ask_value("Send an email like above to %d recipients "
                            "(%s)" % (len(recipients), ', '.join(recipients)),
                            choices=['n', 'y'])
            if proceed == 'y':
                for row in rows:
                    to_name, to_email = split_email_address(row['email'])
                    recipients = [to_email] + \
                                 [cc[1] for cc in args.cc] + \
                                 [bcc[1] for bcc in args.bcc]
                    headers['to'] = utf8_address_header((to_name, to_email))
                    msg = compose_email(headers, message % row)

                    if not args.dry_run:
                        print "Sending email to <%s>..." % recipients[0]
                        rsp = server.sendmail(sender[1],
                                        recipients, msg.as_string(),
                                        rcpt_options=['NOTIFY=FAILURE,DELAY'])
                    else:
                        print "Would send email to <%s>..." % recipients[0]
                        rsp = 0
                    if rsp:
                        write_log_entry(log_f, 'FAILED', row, log_fields)
                        print "Mail delivery failed: %s" % rsp
                    else:
                        write_log_entry(log_f, 'OK', row, log_fields)
                        emails_f.write('-'*79 + '\n')
                        emails_f.write(msg.as_string())
                        emails_f.write('\n')
            else:
                print "Did not send!"
                for row in rows:
                    write_log_entry(log_f, 'SKIPPED', row, log_fields)

    finally:
        server.quit()
        log_f.close()
        emails_f.close()

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
