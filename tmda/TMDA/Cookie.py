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

"""Crypto-cookie functions."""

# About characters case:
# RFC 5321 2.4 states that "SMTP implementations MUST take care to preserve
# the case of mailbox local-parts". This means TMDA may NOT modify the case
# of addresses, be it when holding/releasing pending messages or for outgoing
# messages sent via tmda-inject (and tmda-ofmipd).
# HOWEVER, one should not trust in the real world when creating and verifying
# TMDA tags (cookies). Thus, let's better be safe than sorry and handle those
# entirely on lower(ed) case data.
# PS: I know of a well- and long-known hardware and software supplier that
# stores and uses all-uppercased e-mail addresses, despite the originally
# communicated ones being all in lowercase (...).

import base64
from binascii import hexlify
import os
import re
import time
import hmac
import hashlib

from . import Defaults
from . import Util

def tmda_mac_encode(mac_bytes, rollover=False, legacy=False):
    """Encode the given bytes into a alphanumeric (Base64-derived) string,
    unless legacy/hexadecimal encoding is required or the new/alphanumeric
    version collides with it, stripped to HMAC_BYTES(_ROLLOVER) chars"""
    if rollover:
        mac_size = Defaults.HMAC_BYTES_ROLLOVER
    else:
        mac_size = Defaults.HMAC_BYTES
    if legacy:
        str_size = 2*mac_size
        mac_str = hexlify(mac_bytes).decode().lower()[:str_size]
    else:
        # Convert to lowercase Base64, stripped from non-alphanumeric chars
        # (1-char = 36 values)
        str_size = int(1.55*mac_size + 0.5)  # ceiling(log(256)/log(36)*mac_size)
        mac_str = base64.encodebytes(mac_bytes).decode().lower()
        mac_str = re.sub('[^a-z0-9]', '', mac_str)[:str_size]
        if Defaults.HMAC_ENCODING_COMPAT and not re.search('[g-z]', mac_str):
            # looks like an hexadecimal (collision!)
            mac_str = tmda_mac_encode(mac_bytes, rollover, True)
    return mac_str


def tmda_mac_bytes(*items, rollover=False):
    """Create a HMAC based on items (which must be strings), using the
    configured HMAC_ALGO(_ROLLOVER) algorithm along the CRYPT_KEY(_ROLLOVER),
    and return the corresponding bytes string."""
    items_bytes = ''.join(items).encode()
    if rollover:
        algo = Defaults.HMAC_ALGO_ROLLOVER.lower()
        if algo[:2] == 'p2':
            rounds = 10**Defaults.HMAC_ROUNDS_ROLLOVER
            # Let's use the (short) items_bytes as "password" and the known very long key as "salt"
            mac_bytes = hashlib.pbkdf2_hmac(algo[2:], items_bytes, Defaults.CRYPT_KEY_ROLLOVER, rounds)
        else:
            mac_bytes = hmac.new(Defaults.CRYPT_KEY_ROLLOVER, items_bytes, algo).digest()
    else:
        algo = Defaults.HMAC_ALGO.lower()
        if algo[:2] == 'p2':
            rounds = 10**Defaults.HMAC_ROUNDS
            # Let's use the (short) items_bytes as "password" and the known very long key as "salt"
            mac_bytes = hashlib.pbkdf2_hmac(algo[2:], items_bytes, Defaults.CRYPT_KEY, rounds)
        else:
            mac_bytes = hmac.new(Defaults.CRYPT_KEY, items_bytes, algo).digest()
    return mac_bytes


def make_confirm_mac(time, pid, keyword=None):
    """Expects time, pid and optionally keyword and returns an encoded HMAC."""
    time = str(time)
    pid = str(pid)
    if keyword is None: keyword = ''
    return tmda_mac_encode(tmda_mac_bytes(time, pid, keyword))


def verify_confirm_mac(mac, time, pid, keyword=None):
    """Verifies the given HMAC. Returns True on match, False otherwise"""
    mac = mac.lower()
    time = str(time)
    pid = str(pid)
    if keyword is None: keyword = ''
    legacy = Defaults.HMAC_ENCODING_COMPAT and not re.search('[g-z]', mac)
    verify = hmac.compare_digest(mac, tmda_mac_encode(tmda_mac_bytes(time, pid, keyword, rollover=False), rollover=False, legacy=legacy))
    if not verify and Defaults.CRYPT_KEY_ROLLOVER:
        verify = hmac.compare_digest(mac, tmda_mac_encode(tmda_mac_bytes(time, pid, keyword, rollover=True), rollover=True, legacy=legacy))
    return verify


def make_confirm_cookie(time, pid, keyword=None):
    """Return a confirmation-cookie (timestamp.process_id.HMAC)."""
    time = str(time)
    pid = str(pid)
    mac = make_confirm_mac(time, pid, keyword)
    return '%s.%s.%s' % (time, pid, mac)


def make_confirm_address(address, time, pid, keyword=None):
    """Return a full confirmation-style e-mail address."""
    confirm_cookie = make_confirm_cookie(time, pid, keyword)
    if Defaults.CONFIRM_ADDRESS:
        address = Defaults.CONFIRM_ADDRESS
    username, hostname = address.split('@')
    confirm_address = '%s%s%s%s%s@%s' % (username,
                                         Defaults.RECIPIENT_DELIMITER,
                                         Defaults.TAGS_CONFIRM[0],
                                         Defaults.RECIPIENT_DELIMITER,
                                         confirm_cookie, hostname)
    return confirm_address


def make_dated_mac(expire_time):
    """Expects expiration time (Unix epoch) and returns an encoded HMAC."""
    expire_time = str(expire_time)
    return tmda_mac_encode(tmda_mac_bytes(expire_time))


def verify_dated_mac(mac, expire_time):
    """Verifies the given HMAC. Returns True on match, False otherwise"""
    mac = mac.lower()
    expire_time = str(expire_time)
    legacy = Defaults.HMAC_ENCODING_COMPAT and not re.search('[g-z]', mac)
    verify = hmac.compare_digest(mac, tmda_mac_encode(tmda_mac_bytes(expire_time, rollover=False), rollover=False, legacy=legacy))
    if not verify and Defaults.CRYPT_KEY_ROLLOVER:
        verify = hmac.compare_digest(mac, tmda_mac_encode(tmda_mac_bytes(expire_time, rollover=True), rollover=True, legacy=legacy))
    return verify


def make_dated_cookie(time, timeout = None):
    """Return a dated-style cookie (expire date + HMAC)."""
    tmda_timeout = timeout or os.environ.get('TMDA_TIMEOUT')
    if not tmda_timeout:
        tmda_timeout = Defaults.DATED_TIMEOUT
    expire_time = int(time) + Util.seconds(tmda_timeout)
    mac = make_dated_mac(expire_time)
    return '%d.%s' % (expire_time, mac)


def make_dated_address(address, addrtime=None):
    """Return a full dated-style e-mail address."""
    if addrtime is None:
        addrtime = time.time()
    dated_cookie = make_dated_cookie(addrtime)
    username, hostname = address.split('@')
    dated_address = '%s%s%s%s%s@%s' %(username,
                                      Defaults.RECIPIENT_DELIMITER,
                                      Defaults.TAGS_DATED[0],
                                      Defaults.RECIPIENT_DELIMITER,
                                      dated_cookie, hostname)
    return dated_address


def make_sender_mac(address):
    """Expects sender address and returns an encoded HMAC."""
    address = address.lower()
    return tmda_mac_encode(tmda_mac_bytes(address))


def verify_sender_mac(mac, address):
    """Verifies the given HMAC. Returns True on match, False otherwise"""
    mac = mac.lower()
    address = address.lower()
    legacy = Defaults.HMAC_ENCODING_COMPAT and not re.search('[g-z]', mac)
    verify = hmac.compare_digest(mac, tmda_mac_encode(tmda_mac_bytes(address, rollover=False), rollover=False, legacy=legacy))
    if not verify and Defaults.CRYPT_KEY_ROLLOVER:
        verify = hmac.compare_digest(mac, tmda_mac_encode(tmda_mac_bytes(address, rollover=True), rollover=True, legacy=legacy))
    return verify


def make_sender_cookie(address):
    """Return a sender-style cookie based on the given address."""
    return make_sender_mac(address)


def make_sender_address(address, sender):
    """Return a full sender-style e-mail address."""
    sender_cookie = make_sender_cookie(sender)
    username, hostname = address.split('@')
    sender_address = '%s%s%s%s%s@%s' %(username,
                                       Defaults.RECIPIENT_DELIMITER,
                                       Defaults.TAGS_SENDER[0],
                                       Defaults.RECIPIENT_DELIMITER,
                                       sender_cookie, hostname)
    return sender_address


def sanitize_keyword(keyword):
    """Returns a sanitized keyword, safe to use in a RFC 2822 address."""
    # Characters outside of an RFC2822 atom token are changed to '?'
    keyword = re.sub("[^-a-zA-Z0-9!#$%&*+/=?^_`{|}'~]", "?", keyword)
    # We don't allow the RECIPIENT_DELIMITER in a keyword; replace with `?'
    keyword = keyword.replace(Defaults.RECIPIENT_DELIMITER, '?')
    return keyword

def make_keyword_mac(keyword):
    """Expects a keyword as a string, returns an encoded HMAC."""
    keyword = sanitize_keyword(keyword).lower()
    return tmda_mac_encode(tmda_mac_bytes(keyword))


def verify_keyword_mac(mac, keyword):
    """Verifies the given HMAC. Returns True on match, False otherwise"""
    mac = mac.lower()
    keyword = sanitize_keyword(keyword).lower()
    legacy = Defaults.HMAC_ENCODING_COMPAT and not re.search('[g-z]', mac)
    verify = hmac.compare_digest(mac, tmda_mac_encode(tmda_mac_bytes(keyword, rollover=False), rollover=False, legacy=legacy))
    if not verify and Defaults.CRYPT_KEY_ROLLOVER:
        verify = hmac.compare_digest(mac, tmda_mac_encode(tmda_mac_bytes(keyword, rollover=True), rollover=True, legacy=legacy))
    return verify


def make_keyword_cookie(keyword):
    """Return a keyword-style cookie (keyword + HMAC)."""
    keyword = sanitize_keyword(keyword)
    keywordmac = make_keyword_mac(keyword)
    return '%s.%s' % (keyword, keywordmac)


def make_keyword_address(address, keyword):
    """Return a full keyword-style e-mail address."""
    keyword_cookie = make_keyword_cookie(keyword)
    username, hostname = address.split('@')
    keyword_address = '%s%s%s%s%s@%s' %(username,
                                        Defaults.RECIPIENT_DELIMITER,
                                        Defaults.TAGS_KEYWORD[0],
                                        Defaults.RECIPIENT_DELIMITER,
                                        keyword_cookie, hostname)
    return keyword_address


def make_fingerprint(hdrlist):
    """Expects a list of strings or bytes strings, and returns a full
    (unsliced) HMAC as a base64 encoded string, but with the trailing
    '=' and newline removed."""
    algo = Defaults.HMAC_ALGO.lower()
    if algo[:2] == 'p2': algo = algo[2:]
    fp = hmac.new(Defaults.CRYPT_KEY, digestmod=algo)
    for hdr in hdrlist:
        if isinstance(hdr, str):
            hdr = hdr.encode()
        fp.update(hdr)
    return base64.encodebytes(fp.digest()).decode()[:-2] # Remove '=\n'
