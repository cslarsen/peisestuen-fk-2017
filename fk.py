#!/usr/bin/env python3

"""
Peisestuen Ferieklubbs Trip Calculator 3000
"""

from datetime import datetime, date, timedelta
from decimal import Decimal as NOK
import decimal
import elv
import os
import re
import sys
import urllib.request

url = "https://www.dropbox.com/s/arjg8jdcyf7jvj2/data.csv?dl=0"

class Trip(object):
    def __init__(self, alias, to, by, on, days, settled):
        """
        Args:
            to (str): Trip to
            who (str): Organizers
            on (datetime): Date of outbound flight
            days (int): Number of days, date+days should be the day of the
                return.
            settled (datetime): Incluside date when all money transfers related
                to this trip were settled. All transactions from the previous
                settlement date + 1 day and up to and including this will be
                counted towards this trip.
        """
        self.alias = alias
        self.destination = to
        self.organizers = by
        self.date = on
        self.days = days
        self.settled = settled

    def __gt__(self, other):
        return self.date > other.date

    def __str__(self):
        return "Trip on {date} to {destination}".format(**self.__dict__)

    def __repr__(self):
        s = "<Trip "
        s += " date=%s" % repr(self.date)
        s += " destination=%s" % repr(self.destination)
        s += " organizers=%s" % repr(self.organizers)
        s += " days=%d" % self.days
        s += " settled=%s" % repr(self.settled)
        s += ">"
        return s


TRIPS = [
    Trip(alias="Tur 2009",
         to="Stockholm", by="André og Christian",
         on=date(2010, 4, 23), days=2, settled=date(2010, 4, 25)),

    Trip(alias="Tur 2011",
         to="Bratislava", by="Einar og Øystein",
         on=date(2011, 9, 16), days=2, settled=date(2011, 9, 18)),

    Trip(alias="Tur 2014",
         to="London", by="Dagfinn og Glenn",
         on=date(2014, 10, 3), days=2, settled=date(2014, 10, 10)),

    Trip(alias="Tur 2015",
         to="Aberdeen", by="Christian og Rolf",
         on=date(2015, 9, 4), days=2, settled=date(2015, 9, 14)),

    Trip(alias="Tur 2016",
         to="Haarlem", by="Glenn og Morten",
         on=date(2016, 10, 28), days=2, settled=date(2017, 1, 22)),

    Trip(alias="Tur 2017",
         to="Unknown", by="André og Øystein",
         on=date(2017, 12, 31), days=2, settled=date(2017, 12, 31)),
]

# Price per person, use this to get an accurate amount
PRICE_STOCKHOLM  = NOK("-37921.00") / 8
PRICE_BRATISLAVA = NOK("-59799.00") / 9

# Tactic: Total cost, minus special circumstances, then divide the rest equally
# among the remaining travellers
PRICE_LONDON = -( # Must be negative
        NOK("81805.12") # Total cost in trans
      - NOK("1949.48") # Renter
      - NOK("2706.00") # Marius fly og div
      - NOK("1800.00") # Marius Watford
    ) / 8
PRICE_ABERDEEN = -( # Must be negative
        NOK("40651.04")
      - NOK("3186.00") # Øysti kunne ikke bli med
    ) / 7

PRICE_HAARLEM = -(
        NOK("8700.00") # Lagt ut av Glenn, mat og transport
      + NOK("11124.52") # Lagt ut av Glenn
      + NOK("47924.64") # Lagt ut av Morten, fly hotell
    ) / 8
# Each traveller, which trip they went to, and the amount they had to pay.
COSTS = {
    "André": [
        PRICE_STOCKHOLM,
        PRICE_BRATISLAVA,
        PRICE_LONDON,
        PRICE_ABERDEEN,
        PRICE_HAARLEM,
    ],

    "Christian": [
        PRICE_STOCKHOLM,
        PRICE_BRATISLAVA,
        PRICE_LONDON,
        PRICE_ABERDEEN,
        PRICE_HAARLEM,
    ],

    "Dagfinn": [
        PRICE_STOCKHOLM,
        PRICE_BRATISLAVA,
        PRICE_LONDON,
        PRICE_ABERDEEN,
        PRICE_HAARLEM,
    ],

    "Einar": [
        NOK("0.00"), # Stockholm, var med men kjøpte Marius si billett. Så
                     # beløpet skal stå på Marius
        PRICE_BRATISLAVA,
        PRICE_LONDON,
        PRICE_ABERDEEN,
        PRICE_HAARLEM,
    ],

    "Glenn": [
        PRICE_STOCKHOLM,
        PRICE_BRATISLAVA,
        PRICE_LONDON,
        PRICE_ABERDEEN,
        PRICE_HAARLEM,
    ],

    "Marius": [
        PRICE_STOCKHOLM, # Stockholm, var ikke med, Einar kjøpt billetten
        PRICE_BRATISLAVA,
        NOK("-4506.00"), # London, ikke med, måtte betale en del
        NOK("0.00"),     # Aberdeen, var ikke med
    ],

    "Morten": [
        PRICE_STOCKHOLM,
        PRICE_BRATISLAVA,
        PRICE_LONDON,
        PRICE_ABERDEEN,
        PRICE_HAARLEM,
    ],

    "Rolf": [
        PRICE_STOCKHOLM,
        PRICE_BRATISLAVA,
        PRICE_LONDON,
        PRICE_ABERDEEN,
        PRICE_HAARLEM,
    ],

    "Øystein": [
        PRICE_STOCKHOLM,
        PRICE_BRATISLAVA,
        PRICE_LONDON,
        NOK("-3186.00"), # Aberdeen, var ikke med, måtte betale en del
        PRICE_HAARLEM,
    ],

    # Earned interest that we decided to spend on a trip
    "(Renter)": [
        NOK("0.00"), # Stockholm
        NOK("0.00"), # Bratislava
        NOK("-1949.48"), # London
        NOK("0.00"), # Aberdeen
    ],

    # Gebyr
    "(Gebyr)": [
        NOK("0.0"),
        NOK("0.0"),
        NOK("0.0"),
        NOK("0.0"),
    ],
}

person_regex = {
    "André":     [".*Mortensen.*"],
    "Asbjørn":   [".*Asbj.rn.*"],
    "Christian": [".*Christian.*", "^Peisestuen FK", "32602120707"],
    "Dagfinn":   [".*Frances.*"],
    "Einar":     [".*Einar.*"],
    "Frode":     [".*Frode.*"],
    "Glenn":     [".*Glenn.*"],
    "Jarle":     [".*Jarle.*"],
    "Jørgen":    [".*J.rgen Helland.*"],
    "Marius":    [".*Wolla.*", ".*Marius.*"],
    "Morten":    [".*Morten Haugeland.*"],
    "Rolf":      [".*Rolf.*"],
    "RuneAa":    [".*Aanestad.*"],
    "RuneB":     [".*Brevik.*"],
    "Tor Asle":  [".*Asle.*"],
    "Øystein":   [".*ystein.*"],
}

other_regex = {
    "Tur 2009": ["Kontantuttak.*", ".*Fly og hotell.*"],
    "Tur 2011": [".*Wien betaling [1-9].*"],
    "Tur 2014": [".*Reise2014.*"],
    "Tur 2015": [".*Reise2015.*", "TUR2015.*", "PEISESTUEN TUR  2015 TAXI", ],
    "Tur 2016": [".*Reise2016.*",
                 "3250\.22\.52800, Glenn Stange", # overføring 16/11-16 feilnotert
                 ],
    "(Renter)":  [".*Kreditrente.*"],
    "(Gebyr)":   [".*Gebyr.*"],
}

def merge_dicts(a, b):
    c = a.copy()
    c.update(b)
    return c

all_regex = merge_dicts(person_regex, other_regex)
warnings = []

def print_warnings():
    if len(warnings) == 0:
        return
    else:
        print("WARNINGS:")
        for w in warnings:
            print("  %s" % w)
        print("")

def message_to_person(message):
    """Converts a message to a person."""
    global all_regex, warnings
    message = message.upper()

    out = None
    match = None

    for person, regexes in reversed(sorted(all_regex.items())):
        for regex in regexes:
            if re.search(regex.upper(), message):
                if out is not None:
                    msg = "Collision for '%s' and '%s' in message '%s'" % (
                        match, regex, message)
                    warnings.append(msg)
                else:
                    out = person
                    match = regex
    if out is None:
        warnings.append("Couldn't map message to person: '%s'" % message)
        return "???"
    else:
        return out

def banner(s, char='=', nl=True):
    if nl:
        print("")
    print(char*len(s))
    print(s)
    print(char*len(s))
    if nl:
        print("")

def log(s):
    sys.stdout.write("%s\n" % s)
    sys.stdout.flush()

class ReadURL(object):
    def __init__(self, url):
        self.url = url
        self.handle = None

    def open(self):
        self.handle = urllib.request.urlopen(self.url)
        return self.handle

    def close(self):
        self.handle.close()
        self.handle = None

    def __enter__(self):
        return self.open()

    def __exit__(self, type, value, tb):
        self.close()


def older_than(filename, delta):
    """Checks if file is older than the given timedelta."""
    age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(filename))
    return age > delta

def round_nok(nok):
    return nok.quantize(NOK('.01'), rounding=decimal.ROUND_DOWN)

def read_transactions():
    tempfile = os.path.join("/", "tmp", "data.csv")

    if len(sys.argv[1:]) > 0:
        global url
        url = "file://" + os.path.abspath(sys.argv[1])
    else:
        # Reuse tempfile if it's not that old
        if os.path.exists(tempfile):
            if not older_than(tempfile, timedelta(minutes=5)):
                url = "file://" + tempfile

    with ReadURL(url) as handle:
        data = handle.read()

        # Update tempfile
        with open(tempfile, "wb") as f:
            f.write(data)

        trans = elv.parse(tempfile)

        # Tack on aliases
        for t in trans:
            t.alias = message_to_person(t.message)
        return trans


def transactions_per_person(trans):
    person = {}
    for name in sorted(all_regex.keys()):
        t = trans.group_by(name, field=lambda x: x.alias)
        if len(t) > 0:
            person[name] = t
    return person

def print_person_totals(transactions_per_person):
    xfer = lambda x: x.xfer
    person = transactions_per_person

    # Order by total descending, name ascending
    order = lambda x: (-person[x].total(), x)
    for name in sorted(person, key=order):
        t = person[name]
        i, o = t.balance()
        s = "%-9s kr %9s  %3d trans  %9s inn %9s ut  %s sist" % (
            name, t.total(), len(t), i, o, max(t, key=xfer).xfer)
        print(s)

def main():
    trans = read_transactions()
    banner("Peisestuen FK Balanse per %s" % trans.latest.xfer)

    # Find totals for each person
    grouped = transactions_per_person(trans)

    for trip in sorted(TRIPS):
        if trip.alias in grouped:
            cost = grouped[trip.alias].total()
        else:
            cost = NOK("0.00")
        print("Tur den %s til %-10s organisert av %s" % (
            trip.date, trip.destination, trip.organizers))

    banner("Kontobevegelser %s — %s" % (trans.first.xfer, trans.last.xfer))
    print_person_totals(grouped)

    # For each person, subtract trip costs and print the new totals
    balance = {}
    for name, costs in COSTS.items():
        paid = grouped[name].total()
        cost = sum(costs)
        balance[name] = paid + cost # costs are negative

    banner("Individuelle Balanser")
    for name, amount in sorted(balance.items()):
        print("%-9s kr %9s" % (name, round_nok(amount)))
    print("%-9s kr %9s" % ("Sum", round_nok(sum(balance.values()))))

    print("\n%-9s kr %9s" % ("På konto", round_nok(trans.total())))
    print("%-9s kr %9s" % ("Avvik",
        round_nok(trans.total() - sum(balance.values()))))

    print("")
    print("MERK: Du kan betale ekstra ved å sende penger til 3290.53.84308")
    print("      Det er VIKTIG å merke overføringen med ditt navn!")
    print("      Nåværende månedlig beløp er kr 500")

if __name__ == "__main__":
    main()
