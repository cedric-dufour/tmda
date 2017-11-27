import unittest
import sys

import lib.util
lib.util.testPrep()

import TMDA.Cookie as Cookie

class Cookies(unittest.TestCase):
    time = 1262937386
    pid = 12345
    sender_address = 'Sender@EXAMPLE.org'
    user_address = 'TestUser@example.com'

    keyword_cookies = [
        # (keyword, cookie (new encoding, alphanumeric)
        ('keywordtest', 'keywordtest.bgdjayyt'),
        ('keyword-test', 'keyword?test.e0u9ycqc'),
        # Note: make_keyword_mac lower-cases the keyword.
        ('KeyWordTest0123', 'KeyWordTest0123.3xr6bnvr'),
        # All non-alphanumeric characters that should not be replaced with ?
        ("!#$%&*+/=^_`{|}'~", "!#$%&*+/=^_`{|}'~.crbfvp6a"),
        # Some characters that should be replaced with ?
        (' "():;<>?@[\\]', '?????????????.wxn0fd90'),
        # Characters TMDA 1.1.12 gets wrong due to a bad regex in make_keyword_cookie.
        ('.,', '??.kvirbrjs'),
    ]

    keyword_cookies_rollover = [
        # (keyword, legacy cookie (legacy encoding, hexadecimal)
        ('keywordtest', 'keywordtest.243548'),
        ('keyword-test', 'keyword?test.0de87a'),
        # Note: make_keyword_mac lower-cases the keyword.
        ('KeyWordTest0123', 'KeyWordTest0123.94bc2c'),
        # All non-alphanumeric characters that should not be replaced with ?
        ("!#$%&*+/=^_`{|}'~", "!#$%&*+/=^_`{|}'~.269c47"),
        # Some characters that should be replaced with ?
        (' "():;<>?@[\\]', '?????????????.372018'),
        # Characters TMDA 1.1.12 gets wrong due to a bad regex in make_keyword_cookie.
        ('.,', '??.925dcc'),
    ]

    def testConfirmMac(self):
        # Current key (new encoding, alphanumeric)
        self.assertTrue(Cookie.verify_confirm_mac('05rib1ru', self.time, self.pid))
        self.assertTrue(Cookie.verify_confirm_mac('wbf9rkhf', self.time, self.pid, 'keyword'))

        # Rollover key (legacy encoding, hexadecimal)
        self.assertTrue(Cookie.verify_confirm_mac('a45167', self.time, self.pid))
        self.assertTrue(Cookie.verify_confirm_mac('f5ee35', self.time, self.pid, 'keyword'))

    def testConfirmCookie(self):
        calculated = Cookie.make_confirm_cookie(self.time, self.pid)
        self.assertEqual(calculated, '1262937386.12345.05rib1ru')

        calculated = Cookie.make_confirm_cookie(self.time, self.pid, 'keyword')
        self.assertEqual(calculated, '1262937386.12345.wbf9rkhf')

    def testConfirmAddress(self):
        calculated = Cookie.make_confirm_address(self.user_address, self.time, self.pid)
        self.assertEqual(calculated, 'TestUser-confirm-1262937386.12345.05rib1ru@example.com')

        calculated = Cookie.make_confirm_address(self.user_address, self.time, self.pid, 'keyword')
        self.assertEqual(calculated, 'TestUser-confirm-1262937386.12345.wbf9rkhf@example.com')

    def testDatedMac(self):
        # Current key (new encoding, alphanumeric)
        self.assertTrue(Cookie.verify_dated_mac('st6b94yp', self.time+432000))
        self.assertTrue(Cookie.verify_dated_mac('uh2nsnln', self.time+60))

        # Rollover key (legacy encoding, hexadecimal)
        self.assertTrue(Cookie.verify_dated_mac('df2137', self.time+432000))
        self.assertTrue(Cookie.verify_dated_mac('926a58', self.time+60))

    def testDatedCookie(self):
        calculated = Cookie.make_dated_cookie(self.time)
        self.assertEqual(calculated, '1263369386.st6b94yp')

        calculated = Cookie.make_dated_cookie(self.time, '1m')
        self.assertEqual(calculated, '1262937446.uh2nsnln')

    def testDatedAddress(self):
        calculated = Cookie.make_dated_address(self.user_address, self.time)
        self.assertEqual(calculated, 'TestUser-dated-1263369386.st6b94yp@example.com')

        # "Now" address. Can't predict exactly how it will come out,
        # but make sure it at least succeeds.
        import re
        pattern = re.compile(r'TestUser-dated-\d{10}\.[0-9a-z]{8}@example\.com')
        calculated = Cookie.make_dated_address(self.user_address)
        self.assertTrue(pattern.match(calculated))

    def testSenderMac(self):
        # Current key (new encoding, alphanumeric)
        self.assertTrue(Cookie.verify_sender_mac('nn0cfv94', self.sender_address))
        self.assertTrue(Cookie.verify_sender_mac('nn0cfv94', self.sender_address.lower()))
        self.assertTrue(Cookie.verify_sender_mac('nn0cfv94', self.sender_address.upper()))

        # Rollover key (legacy encoding, hexadecimal)
        self.assertTrue(Cookie.verify_sender_mac('c7795c', self.sender_address))
        self.assertTrue(Cookie.verify_sender_mac('c7795c', self.sender_address.lower()))
        self.assertTrue(Cookie.verify_sender_mac('c7795c', self.sender_address.upper()))

    def testSenderCookie(self):
        calculated = Cookie.make_sender_cookie(self.sender_address)
        self.assertEqual(calculated, 'nn0cfv94')

    def testSenderAddress(self):
        calculated = Cookie.make_sender_address(self.user_address, self.sender_address)
        self.assertEqual(calculated, 'TestUser-sender-nn0cfv94@example.com')

    def testKeywordMac(self):
        # Current key (new encoding, alphanumeric)
        for (keyword, cookie) in self.keyword_cookies:
            mac = cookie.split('.')[-1]
            self.assertTrue(Cookie.verify_keyword_mac(mac, keyword))
            self.assertTrue(Cookie.verify_keyword_mac(mac, keyword.lower()))
            self.assertTrue(Cookie.verify_keyword_mac(mac, keyword.upper()))

        # Rollover key (legacy encoding, hexadecimal)
        for (keyword, cookie) in self.keyword_cookies_rollover:
            mac = cookie.split('.')[-1]
            self.assertTrue(Cookie.verify_keyword_mac(mac, keyword))
            self.assertTrue(Cookie.verify_keyword_mac(mac, keyword.lower()))
            self.assertTrue(Cookie.verify_keyword_mac(mac, keyword.upper()))

    def testKeywordCookie(self):
        for (keyword, cookie) in self.keyword_cookies:
            calculated = Cookie.make_keyword_cookie(keyword)
            self.assertEqual(calculated, cookie)

    def testKeywordAddress(self):
        for (keyword, cookie) in self.keyword_cookies:
            calculated = Cookie.make_keyword_address(self.user_address, keyword)
            expected = 'TestUser-keyword-%s@example.com' % cookie
            self.assertEqual(calculated, expected)

class Fingerprints(unittest.TestCase):
    def testFingerprint(self):
        headers = ['foo', 'bar', 'baz', '012456789', ' ' * 40]

        fingerprints = [
            'dy6gjEMA1R/YnVRZieLkmzzzYGAa6UfYrRaTzIPM5mY',
            '1xg9wGzfPyg4D1xhxh7nen6ydOmls5d7bI4V+Ft2Kws',
            'I6h/q907N0a9FqDlvO1+pWCKWlpmYf3ALI7uKJFlT1E',
            '/CTW/qgIPl2egp4V3WcrMFiTJYOhPIUFedCKqf9NWVY',
            'i95kW3TOm+B7fdTl9lNxzZBXf2M50e9gzGYua/2i6VY',
        ]
        for (i, header) in enumerate(headers):
            calculated = Cookie.make_fingerprint(headers[:i+1])
            self.assertEqual(calculated, fingerprints[i])

        fingerprints = [
            'i95kW3TOm+B7fdTl9lNxzZBXf2M50e9gzGYua/2i6VY',
            '1Et2YBe9Cgb+Hz/XIKpI2XO0xskmbIglPnhhBlyftdo',
            'eduzF71dLq3KSw0fBsMhie2h/5cRwP0pVUmP9QvIkSs',
            'S/9I2ED15PTR+ljdRWJtEOZnH6DnFsmN0MRFHb3C48w',
            'flEh7ccDcPUl8H7f57ym3bb82iJu4ZLeqefjDvxyj9k',
        ]
        for (i, header) in enumerate(headers):
            calculated = Cookie.make_fingerprint(headers[i:])
            self.assertEqual(calculated, fingerprints[i])

        Defaults_headers = [
            '<20011212192455.A7060@nightshade.la.mastaler.com>',
            '"Jason R. Mastaler" <jason-dated-1008901496.5356ec@mastaler.com>'
            'Wed, 12 Dec 2001 19:24:55 -0700',
        ]
        self.assertEqual('RosHVeKk7RxuFw9vi26R6w07MmC+LyBngj0i/Ty34mk',
                         Cookie.make_fingerprint(Defaults_headers))


if __name__ == '__main__':
    runner = unittest.TextTestRunner(verbosity=2)
    unittest.main(testRunner=runner)
