# -*- python -*-
#
# Copyright (C) 2001-2007 Jason R. Mastaler <jason@mastaler.com>
#
# This file is part of TMDA.
#
# TMDA is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.  A copy of this license should
# be included in the file COPYING.
#
# TMDA is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License
# along with TMDA; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

"""Manage a TMDA-style Auto Response."""


from email import message_from_bytes, message_from_string
from email.charset import add_alias
from email.errors import MessageError
from email.header import Header, decode_header
from email.mime.message import MIMEMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, parseaddr

import os
import time

from . import Defaults
from . import Util
from . import Version


# Extend Charset.ALIASES with some charsets which don't already have
# convenient aliases.
add_alias('cyrillic', 'iso-8859-5')
add_alias('greek', 'iso-8859-7')
add_alias('hebrew', 'iso-8859-8')
add_alias('japanese', 'euc-jp')
add_alias('korean', 'euc-kr')
add_alias('russian', 'koi8-r')
add_alias('thai', 'tis-620')
add_alias('turkish', 'iso-8859-9')
add_alias('vietnamese', 'viscii')


class AutoResponse:
    def __init__(self, msgin, bouncetext, response_type, recipient):
        """
        msgin is an email.message object representing the incoming
        message we are responding to.

        bouncetext is a string of rfc822 headers/body created from a
        TMDA template.

        response_type is the type of auto response we should send
        ('request' is a confirmation request, 'accept' is a
        confirmation acceptance notice, and 'bounce' is a failure
        notice).

        recipient is the recipient e-mail address of this auto
        response.  Normally the envelope sender address.
        """
        self.msgin_as_bytes = Util.msg_as_bytes(msgin)
        self.msgin_headers_as_bytes = Util.headers_as_bytes(msgin)
        # Only do this step if the user wants to include the entire message.
        if Defaults.AUTORESPONSE_INCLUDE_SENDER_COPY > 1:
            max_msg_size = int(Defaults.CONFIRM_MAX_MESSAGE_SIZE)
            # Don't include the payload if it's over a certain size.
            if max_msg_size and max_msg_size < len(self.msgin_as_bytes):
                msgin.set_payload('[ Message body suppressed '
                                  '(exceeded %s bytes) ]' % max_msg_size)
                self.msgin_as_bytes = Util.msg_as_bytes(msgin)
            # Now try to re-parse the message and store that as self.msgin.
            # If that fails, there is no choice but to use the original
            # version, so to prevent later Generator failures, we reset
            # AUTORESPONSE_INCLUDE_SENDER_COPY to include only the headers.
            try:
                self.msgin = message_from_bytes(self.msgin_as_bytes)
            except (KeyError, MessageError, TypeError, ValueError):
                self.msgin = msgin
                Defaults.AUTORESPONSE_INCLUDE_SENDER_COPY = 1
        else:
            self.msgin = msgin
        self.bouncemsg = message_from_string(bouncetext)
        self.responsetype = response_type
        self.recipient = recipient


    def create(self):
        """
        Create an auto response object from whole cloth.

        The auto response is a MIME compliant entity with either one
        or two bodyparts, depending on what
        Defaults.AUTORESPONSE_INCLUDE_SENDER_COPY is set to.

        In most cases, the object will look like:

        multipart/mixed
                text/plain (response text)
                message/rfc822 or text/rfc822-headers (sender's message)
        """
        # Headers that users shouldn't be setting in their templates.
        bad_headers = ['X-TMDA-Template-Charset',
                       'MIME-Version',
                       'Content-Type', 'Content-Transfer-Encoding', 'Content-Length',
                       'Content-Disposition', 'Content-Description']
        for h in bad_headers:
            if h in self.bouncemsg:
                del self.bouncemsg[h]
        textpart = MIMEText(self.bouncemsg.get_payload(), 'plain')
        bodyparts = 1 + Defaults.AUTORESPONSE_INCLUDE_SENDER_COPY
        if bodyparts == 1:
            # A single text/plain entity.
            self.mimemsg = textpart
        elif bodyparts > 1:
            # A multipart/mixed entity with two bodyparts.
            self.mimemsg = MIMEMultipart('mixed')
            if self.responsetype == 'request':
                textpart['Content-Description'] = 'Confirmation Request'
            elif self.responsetype == 'accept':
                textpart['Content-Description'] = 'Confirmation Acceptance'
            elif self.responsetype == 'bounce':
                textpart['Content-Description'] = 'Failure Notice'
            textpart['Content-Disposition'] = 'inline'
            self.mimemsg.attach(textpart)
            if Defaults.AUTORESPONSE_INCLUDE_SENDER_COPY == 1:
                # include the headers only as a text/rfc822-headers part.
                rfc822part = MIMEText(self.msgin_headers_as_bytes.decode('utf-8', errors='replace'), 'rfc822-headers')
                rfc822part['Content-Description'] = 'Original Message Headers'
            elif Defaults.AUTORESPONSE_INCLUDE_SENDER_COPY == 2:
                # include the entire message as a message/rfc822 part.
                # If the message was > CONFIRM_MAX_MESSAGE_SIZE, it has already
                # been truncated appropriately in the constructor.
                rfc822part = MIMEMessage(self.msgin)
                rfc822part['Content-Description'] = 'Original Message'
            rfc822part['Content-Disposition'] = 'inline'
            self.mimemsg.attach(rfc822part)
        # RFC 2183 section 2.10 permits the use Content-Disposition in
        # the main body of the message.
        self.mimemsg['Content-Disposition'] = 'inline'
        # fold the template headers into the main entity.
        for k, v in list(self.bouncemsg.items()):
            # as from TMDA 1.3, template is decoded into a string (natively UTF-8, as per PEP-3120),
            # including the template headers (which are not supposed to contain anything but ASCII characters).
            # When those headers DO contain non-ASCII (UTF-8) characters, 'v' actually is a Header object
            # with an 'unknown-8bit' encoding, which we must re-encode into a proper ASCII-only header.
            if isinstance(v, Header):
                v = str(Header(decode_header(v)[0][0], 'utf-8', header_name=k))
            if k.lower() in [s.lower() for s in Defaults.TEMPLATE_EMAIL_HEADERS]:
                name, addr = parseaddr(v)
                # Note: email.utils.formataddr automatically encodes non-ascii values as UTF-8
                self.mimemsg[k] = formataddr((name, addr))
            elif k.lower() in [s.lower() for s in Defaults.TEMPLATE_ENCODED_HEADERS]:
                # Note: email.header.Header() does NOT automatically encode non-ascii values
                try:
                    v.encode('us-ascii')
                    self.mimemsg[k] = Header(v, 'us-ascii', header_name=k)
                except UnicodeEncodeError:
                    self.mimemsg[k] = Header(v, 'utf-8', header_name=k)
        # Add some new headers to the main entity.
        timesecs = time.time()
        self.mimemsg['Date'] = Util.make_date(timesecs) # required by RFC 2822
        self.mimemsg['Message-ID'] = Util.make_msgid(timesecs) # Ditto
        # References
        refs = []
        for h in ['references', 'message-id']:
            if h in self.msgin:
                refs = refs + self.msgin.get(h).split()
        if refs:
            self.mimemsg['References'] = '\n\t'.join(refs)
        # In-Reply-To
        if 'message-id' in self.msgin:
            self.mimemsg['In-Reply-To'] =  self.msgin.get('message-id')
        self.mimemsg['To'] = self.recipient
        # Some auto responders respect this header.
        self.mimemsg['Precedence'] = 'bulk'
        # Auto-Submitted per draft-moore-auto-email-response-00.txt
        if self.responsetype in ('request', 'accept'):
            self.mimemsg['Auto-Submitted'] = 'auto-replied'
        elif self.responsetype == 'bounce':
            self.mimemsg['Auto-Submitted'] = 'auto-generated (failure)'
        self.mimemsg['X-Delivery-Agent'] = 'TMDA/%s (%s)' % (Version.TMDA,
                                                             Version.CODENAME)
        # Optionally, add some custom headers.
        Util.add_headers(self.mimemsg, Defaults.ADDED_HEADERS_SERVER)
        # Optionally, remove some headers.
        Util.purge_headers(self.mimemsg, Defaults.PURGED_HEADERS_SERVER)


    def send(self):
        """
        Inject the auto response into the mail transport system.
        """
        Util.sendmail(Util.msg_as_bytes(self.mimemsg, 78),
                      self.recipient, Defaults.BOUNCE_ENV_SENDER)


    def record(self):
        """
        Record this auto response.  Used as part of TMDA's auto
        response rate limiting feature, controlled by
        Defaults.MAX_AUTORESPONSES_PER_DAY.
        """
        response_filename = '%s.%s.%s' % (int(time.time()),
                                          Defaults.PID,
                                          Util.normalize_sender(self.recipient))
        # Create ~/.tmda/responses if necessary.
        if not os.path.exists(Defaults.RESPONSE_DIR):
            os.makedirs(Defaults.RESPONSE_DIR, 0o700)
        fp = open(os.path.join(Defaults.RESPONSE_DIR,
                               response_filename), 'w')
        fp.close()

