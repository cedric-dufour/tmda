TMDA is an open source software application designed to significantly
reduce the amount of spam (Internet junk-mail) you receive.  TMDA
strives to be more effective, yet less time-consuming than traditional
spam filters.  TMDA can also be used as a general purpose local mail
delivery agent to filter, sort, deliver and dispose of incoming mail.

The technical countermeasures used by TMDA to thwart spam include:

* whitelists: accept mail from known, trusted senders.

* blacklists: refuse mail from undesired senders.

* challenge/response: allows unknown senders which aren't on the
  whitelist or blacklist the chance to confirm that their message is
  legitimate (non-spam).

* tagged addresses: special-purpose e-mail addresses such as
  time-dependent addresses, or addresses which only accept certain
  kinds of communication.  These increase the transparency of TMDA for
  unknown senders by allowing them to safely circumvent the
  challenge/response system.

For more information, visit the TMDA homepage and TmdaWiki:

  http://tmda.net/
  http://wiki.tmda.net/

See the 'doc' subdirectory for a copy of the wiki documentation that
matches this release.

Information on the TMDA mailing lists can be found at:

  http://wiki.tmda.net/MailingLists

*This* version/package results:
1. from the original TMDA source code
   (apparently no longer maintained as of November 2017)
2. Git-imported and further maintained by Kevin Goodsell
   at https://github.com/KevinGoodsell/tmda-fork
   (apparently no longer maintained as of November 2017)
3. ported to Python 3 and further maintained by Cédric Dufour
   at https://github.com/cedric-dufour/tmda
   (since November 2017)

See the ./tmda/README file for further details

