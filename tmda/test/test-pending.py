import unittest
import sys
import time
import os
import io as StringIO
from email.parser import BytesParser

import lib.util
import imp
lib.util.testPrep()

from TMDA import Pending
from TMDA import Defaults
from TMDA import Util

verbose = False

# NOTE: 'From:' header omitted on purpose
test_messages = {
    '1243439251.12345' : [
        'X-TMDA-Recipient: testuser@example.com',
        'Return-Path: <return.path.1@example.com>',
        'Message-ID: <message.id.12345@example.com>',
        'Date: Fri, 17 Nov 2017 13:20:16 +0100',
        'To: Test User <testuser@example.com>',
        'Subject: Test message number one!',
        '',
        'This is a test message.',
    ],
    '1303349951.12346' : [
        'X-TMDA-Recipient: testuser@example.com',
        'Return-Path: <prvs=BATV-tag=return.path.2@example.com>',
        'Message-ID: <message.id.12346@example.com>',
        'Date: Fri, 17 Nov 2017 13:20:16 +0100',
        'To: =?utf-8?Q?"T=C3=A9st"_User?= <testuser@example.com>',
        'Subject: =?utf-8?Q?Test message "num=C3=A9ro" TWO (UTF-8)!?=',
        'Content-Type: text/plain; charset=utf-8',
        'Content-Transfer-Encoding: 8bit',
        '',
        b'This is another (UTF-8 encoded) test message (H\xc3\xa9! H\xc3\xa9! \xc3\x87a passe ou \xc3\xa7a casse!).',
    ],
    '1303433207.12347' : [
        'X-TMDA-Recipient: testuser-extension@example.com',
        'Return-Path: <SRS0=SRS-tag=example.com=return.path.3@example.org>',
        'Message-ID: <message.id.12347@example.com>',
        'Date: Fri, 17 Nov 2017 13:20:16 +0100',
        'To: =?ISO-8859-1?Q?"T=E9st"_User?= <testuser@example.com>',
        'Subject: =?ISO-8859-1?Q?Test message "num=E9ro" last (ISO-8859-1).?=',
        'Content-Type: text/plain; charset=ISO-8859-1',
        'Content-Transfer-Encoding: 8bit',
        '',
        'This is the last',
        '(ISO-8859-1 encoded)',
        'test message',
        b'(H\xe9! H\xe9! \xc7a passe ou \xe7a casse!)',
    ],
}

class MockMailQueue(object):
    parser = BytesParser()

    def __init__(self):
        self._msgs = {}

        for (msgid, body) in list(test_messages.items()):
            self._msgs[msgid] = b'\r\n'.join([line if isinstance(line, bytes) else line.encode() for line in body])

    def init(self):
        return self

    def exists(self):
        return True

    def fetch_ids(self):
        return list(self._msgs.keys())

    def find_message(self, msgid):
        return msgid in self._msgs

    def fetch_message(self, msgid):
        return self.parser.parsebytes(self._msgs[msgid])

    def delete_message(self, msgid):
        self._msgs.pop(msgid, None)

class QueueInitTests(unittest.TestCase):
    '''
    Basic tests for initializing TMDA.Pending.Queue.
    '''

    def setUp(self):
        Pending.Q = MockMailQueue()

    # Three types of initialization:

    def testInitQueueFromParams(self):
        # With a list provided, only those specific message IDs should be
        # present.
        pending = Pending.Queue(['11243439251.2345', '1303433207.12347'])
        pending.initQueue()
        self.assertEqual(pending.msgs, ['11243439251.2345', '1303433207.12347'])

    def testInitQueueFromStdin(self):
        saved_stdin = sys.stdin
        try:
            # With a '-', IDs should be read from stdin.
            sys.stdin = StringIO.StringIO(
                '1303349951.12346\n1243439251.12345\n')
            pending = Pending.Queue(['-'])
            pending.initQueue()
            self.assertEqual(pending.msgs, ['1243439251.12345',
                                            '1303349951.12346'])

            # With a '-' in combo with IDs, should include both stdin and the
            # specified IDs.
            sys.stdin = StringIO.StringIO('1303349951.12346\n')
            pending = Pending.Queue(['-', '1303433207.12347'])
            pending.initQueue()
            self.assertEqual(pending.msgs, ['1303349951.12346',
                                            '1303433207.12347'])
        finally:
            sys.stdin = saved_stdin

    def testInitQueueFromPending(self):
        # With no arguments, everything from the pending queue should be
        # included.
        pending = Pending.Queue()
        pending.initQueue()
        self.assertEqual(pending.msgs, ['1243439251.12345', '1303349951.12346',
                                        '1303433207.12347'])

class QueueLoopTestMixin(object):
    expected_addrs = ['return.path.1@example.com', 'return.path.2@example.com',
                      'return.path.3@example.com']
    db_params = dict(recipient='testuser@example.com', username='testuser',
                     hostname='example.com')

    def setUp(self):
        self.file_appends = []
        self.db_inserts = []
        self.pager_calls = []

        Util.append_to_file = self.recordFileAppend
        Util.db_insert = self.recordDbInsert
        Util.pager = self.nullPager

        Defaults.PENDING_WHITELIST_APPEND = 'whitelist_file'
        Defaults.PENDING_BLACKLIST_APPEND = 'blacklist_file'
        Defaults.PENDING_RELEASE_APPEND = 'release_file'
        Defaults.PENDING_DELETE_APPEND = 'delete_file'

        Defaults.DB_CONNECTION = 'db_connection'

        Defaults.DB_PENDING_WHITELIST_APPEND = 'whitelist_db_stmt'
        Defaults.DB_PENDING_BLACKLIST_APPEND = 'blacklist_db_stmt'
        Defaults.DB_PENDING_RELEASE_APPEND = 'release_db_stmt'
        Defaults.DB_PENDING_DELETE_APPEND = 'delete_db_stmt'

        # This changes the results of the whitelist tests, and isn't very
        # necessary since there's a separate release test anyway.
        Defaults.PENDING_WHITELIST_RELEASE = False

        Pending.Q = MockMailQueue()

    def tearDown(self):
        # Remove pending cache
        try:
            os.remove(Defaults.PENDING_CACHE)
        except:
            pass

        del Defaults.PENDING_WHITELIST_APPEND
        del Defaults.PENDING_BLACKLIST_APPEND
        del Defaults.PENDING_RELEASE_APPEND
        del Defaults.PENDING_DELETE_APPEND
        del Defaults.DB_CONNECTION
        del Defaults.DB_PENDING_WHITELIST_APPEND
        del Defaults.DB_PENDING_BLACKLIST_APPEND
        del Defaults.DB_PENDING_RELEASE_APPEND
        del Defaults.DB_PENDING_DELETE_APPEND
        del Defaults.PENDING_WHITELIST_RELEASE

        imp.reload(Defaults)
        imp.reload(Util)

    # DERIVED CLASS OVERRIDES
    dispose = None

    def dropFileAppend(self):
        '''Add options for appending to a file'''
        raise NotImplementedError()

    def dropDbInsert(self):
        '''Add options for inserting into a database'''
        raise NotImplementedError()

    def expectedFileAppends(self):
        return [(addr, self.append_file) for addr in self.expected_addrs]

    def expectedDbInserts(self):
        result = []
        for addr in self.expected_addrs:
            params = dict(self.db_params)
            params['sender'] = addr
            result.append(('db_connection', self.insert_stmt, params))

        return result

    # UTILITIES
    def recordFileAppend(self, *args):
        self.file_appends.append(args)

    def recordDbInsert(self, *args):
        self.db_inserts.append(args)

    def nullPager(self, *args):
        pass

    # TESTS
    def testFileAppend(self):
        queue = Pending.Queue(dispose=self.dispose, verbose=verbose)
        queue.initQueue()

        self.dropDbInsert()

        queue.mainLoop()
        self.assertEqual(self.file_appends, self.expectedFileAppends())
        self.assertEqual(self.db_inserts, [])

    def testDbAppend(self):
        queue = Pending.Queue(dispose=self.dispose, verbose=verbose)
        queue.initQueue()

        self.dropFileAppend()

        queue.mainLoop()
        self.assertEqual(self.file_appends, [])
        self.assertEqual(self.db_inserts, self.expectedDbInserts())

    def testBothAppend(self):
        queue = Pending.Queue(dispose=self.dispose, verbose=verbose)
        queue.initQueue()

        queue.mainLoop()
        self.assertEqual(self.file_appends, self.expectedFileAppends())
        self.assertEqual(self.db_inserts, self.expectedDbInserts())

    def testPretend(self):
        queue = Pending.Queue(dispose=self.dispose, verbose=verbose,
                              pretend=True)
        queue.initQueue()

        queue.mainLoop()
        self.assertEqual(self.file_appends, [])
        self.assertEqual(self.db_inserts, [])


# This version of the QueueLoopTestMixin is to be used with dispose methods that
# actually do append to a file and/or database (not 'show' or 'pass')
class QueueLoopTestAppendingMixin(QueueLoopTestMixin):
    # Threshold tests are in a separate mixin because nothing happens in cases
    # like 'pass' and 'show', so there's nothing to check.
    def testThresholdYounger(self):
        threshold = "%ds" % (time.time() - 1280000000)

        queue = Pending.Queue(dispose=self.dispose, verbose=verbose,
                              threshold=threshold, younger=True)
        queue.initQueue()

        queue.mainLoop()
        self.assertEqual(len(self.file_appends), 2)
        self.assertEqual(len(self.db_inserts), 2)

    def testThresholdOlder(self):
        threshold = "%ds" % (time.time() - 1280000000)

        queue = Pending.Queue(dispose=self.dispose, verbose=verbose,
                              threshold=threshold, older=True)
        queue.initQueue()

        queue.mainLoop()
        self.assertEqual(len(self.file_appends), 1)
        self.assertEqual(len(self.db_inserts), 1)

    def testCached(self):
        # First, cause some IDs to be cached.
        cache_ids = ['1243439251.12345', '1303433207.12347']
        queue = Pending.Queue(cache_ids, cache=True, dispose='pass',
                              verbose=verbose)
        queue.initQueue()

        queue.mainLoop()
        # Make sure the cached IDs are as expected.
        self.assertEqual(queue.msgcache, list(reversed(cache_ids)))

        # Revisit the loop, this time expected only the non-cached IDs to be
        # handled.
        queue = Pending.Queue(cache=True, dispose=self.dispose, verbose=verbose)
        queue.initQueue()

        queue.mainLoop()
        self.assertEqual(len(self.file_appends), 1)
        self.assertEqual(len(self.db_inserts), 1)


class QueueLoopPassTest(QueueLoopTestMixin, unittest.TestCase):
    dispose = 'pass'

    def dropFileAppend(self):
        pass

    def dropDbInsert(self):
        pass

    def expectedFileAppends(self):
        return []

    def expectedDbInserts(self):
        return []

class QueueLoopReleaseTest(QueueLoopTestAppendingMixin, unittest.TestCase):
    dispose = 'release'
    append_file = 'release_file'
    insert_stmt = 'release_db_stmt'

    def dropFileAppend(self):
        Defaults.PENDING_RELEASE_APPEND = None

    def dropDbInsert(self):
        Defaults.DB_PENDING_RELEASE_APPEND = None

class QueueLoopDeleteTest(QueueLoopTestAppendingMixin, unittest.TestCase):
    dispose = 'delete'
    append_file = 'delete_file'
    insert_stmt = 'delete_db_stmt'

    def dropFileAppend(self):
        Defaults.PENDING_DELETE_APPEND = None

    def dropDbInsert(self):
        Defaults.DB_PENDING_DELETE_APPEND = None

class QueueLoopWhitelistTest(QueueLoopTestAppendingMixin, unittest.TestCase):
    dispose = 'whitelist'
    append_file = 'whitelist_file'
    insert_stmt = 'whitelist_db_stmt'

    def dropFileAppend(self):
        Defaults.PENDING_WHITELIST_APPEND = None

    def dropDbInsert(self):
        Defaults.DB_PENDING_WHITELIST_APPEND = None

class QueueLoopBlacklistTest(QueueLoopTestAppendingMixin, unittest.TestCase):
    dispose = 'blacklist'
    append_file = 'blacklist_file'
    insert_stmt = 'blacklist_db_stmt'

    def dropFileAppend(self):
        Defaults.PENDING_BLACKLIST_APPEND = None

    def dropDbInsert(self):
        Defaults.DB_PENDING_BLACKLIST_APPEND = None

class QueueLoopShowTest(QueueLoopTestMixin, unittest.TestCase):
    dispose = 'show'
    append_file = 'unused'
    insert_stmt = 'unused'

    def dropFileAppend(self):
        pass

    def dropDbInsert(self):
        pass

    def expectedFileAppends(self):
        return []

    def expectedDbInserts(self):
        return []


if __name__ == '__main__':
    if '-v' in sys.argv:
        verbose = True
    runner = unittest.TextTestRunner(verbosity=2)
    unittest.main(testRunner=runner)
