# Basic plan:
# ConvertVenmoStatement is the entry point.
# It creates a ProgramStates FSM
# Initially we go looking for the 'previous statement date' to get the year to help us figure out if
#       this statement spans years
# Next we go looking for 'Transaction Details', which is where all the payments/credits/purchases are listed
#   Within Transaction Details we look for the PAYMENTS, then the OTHER_CREDITS, then PURCHASES sections
#   Each transaction listing can be interrupted by other stuff (identified via TRANSACTIONS_CONTINUED_LATER)
#       If that occurs we remember the current category into ProgramStates.current_xact_type
#   We then use the ReadingLineStates FSM to handle each chunk of a transaction
#       The idea is that the outer (ProgramStates) FSM passes line chunks into the inner (ReadingLineStates) FSM
#           until R.L.S has accumulated a full transaction
#       After the full transaction has been accumulated the outer FSM adds that transaction to the right category

import csv
from enum import Enum
from functools import reduce
import re
from datetime import date, datetime
from decimal import *
from operator import attrgetter
from typing import Any

from attrs import define
from pdfreader import SimplePDFViewer
from transitions import Machine

import logging

from transitions.extensions import HierarchicalMachine

# logging.basicConfig(format='%(levelname)s %(name)s - %(message)s')
#
# # This would add a _second_ console printer, but with our custom format:
# ch = logging.StreamHandler()
# ch.setLevel(logging.ERROR)
# formatter = logging.Formatter('NEW FORMATTER %(name)s - %(levelname)s - %(message)s')
# ch.setFormatter(formatter)
#
# # add the handlers to the logger
# logger = logging.getLogger('PersonalTool')
# logger.setLevel(logging.ERROR)
#
# logger_transactions = logging.getLogger('PersonalTool.venmo.transactions')
# logger_transactions.setLevel(logging.DEBUG)

# logging.basicConfig(level=logging.INFO)
# # Set transitions' log level to INFO; DEBUG messages will be omitted
# logging.getLogger('transitions').setLevel(logging.INFO)

previous_balance_date: date = None

@define
class Transaction:
    date: Any = None
    reference_num: str = ""
    description: str = ""
    amount: Decimal = 0

    @classmethod
    def get_csv_header(self):
        return ["Date", "Reference Num", "Description", "Amount"]

    # Make the transaction iterable
    # so that csv.writer can print it to a file
    def __iter__(self):
        for each in self.__slots__:
            if not each.startswith('__'):
                yield getattr(self, each, None)

    def __str__(self):
        return f'Transaction({self.amount},\t{self.reference_num},\t{self.description})'


class FileReadingFSMStates(Enum):
    PreviousBalanceDate = "Previous balance as of"
    SearchingForTransactionDetails = "Transaction details"
    # We'll see the "Transaction Details" h2 header, then later in the table we'll see payment / purchase / etc h3 headers
    # So start off in "SEARCHING_FOR_TRANSACTION_TYPE"

    SearchingForTransactionType = "Haven't found transactions type yet (this string does not occur in the file itself)"
    TRANSACTIONS_CONTINUED_LATER = "(Continued on next page)"
    START_OF_PAYMENTS = "Payments"
    Payments = "Reading payment lines (this string does not occur in the file itself)"
    START_OF_OTHER_CREDITS = "Other credits"
    OtherCredits = "Reading Other credits lines (this string does not occur in the file itself)"
    START_OF_PURCHASES = "Purchases and other debits"
    Purchases = "Reading purchase lines (this string does not occur in the file itself)"
    Finished = "Total fees charged this period"

class XactReadingFSMStates(Enum):
    DATE: str = 'date'
    REF: str = 'ref'
    DESC: str = 'desc'
    AMT: str = 'amt'
    FINISHED: str = 'FINISHED READING TRANSACTION LINE'

reDateOfTransaction = re.compile("(\d\d/\d\d)")

class LineReadingFSM:
    xact_reading_states = [
        XactReadingFSMStates.DATE,
        XactReadingFSMStates.REF,
        XactReadingFSMStates.DESC,
        XactReadingFSMStates.AMT,
        XactReadingFSMStates.FINISHED
    ]
    cur_xact: Transaction  # We'll reset this a lot
    previous_date: date  # So remember when the last transaction was separate from cur_xact
    def __init__(self):
        xact_reading_transitions = [
            {'trigger': 'process', 'source': XactReadingFSMStates.DATE,
             'conditions': lambda line: re.search(reDateOfTransaction, line) is not None,
             'dest': XactReadingFSMStates.REF,
             'before': 'save_xact_date', },
            {'trigger': 'process', 'source': XactReadingFSMStates.REF,
             'dest': XactReadingFSMStates.DESC,
             'after': 'save_xact_ref_num'},
            {'trigger': 'process', 'source': XactReadingFSMStates.DESC,
             'dest': XactReadingFSMStates.AMT,
             'after': 'save_xact_desc'},
            {'trigger': 'process', 'source': XactReadingFSMStates.AMT,
             'dest': XactReadingFSMStates.FINISHED,
             'after': 'save_xact_amt'},
        ]


        # Initialize the state machine with states and xact_reading_transitions
        self.machine = Machine(model=self, states=LineReadingFSM.xact_reading_states, transitions=xact_reading_transitions,
                               initial=XactReadingFSMStates.DATE)

        self.previous_date = None
        self.reset()

    def reset(self):
        self.cur_xact = Transaction()
        self.machine.set_state(XactReadingFSMStates.DATE)

    def save_xact_date(self, line):
        global previous_balance_date
        # print("FOUND A DATE!!!!!")
        assert previous_balance_date is not None

        if self.previous_date is not None:
            xact_year = self.previous_date.year
        else:
            xact_year = previous_balance_date.year

        xact_date = datetime.strptime(line + "/" + str(xact_year), "%m/%d/%Y").date()

        # if the previous date is in last Dec & the current date is in January:
        if self.previous_date is not None and \
                self.previous_date.month == 12 and xact_date.month == 1:
            xact_date = date(xact_date.year + 1, xact_date.month, xact_date.day)

        # If the first date we're seeing is in January but the prior balance
        # date is in Dec the move the year up
        if self.previous_date is None and \
                xact_date < previous_balance_date \
                and previous_balance_date.month == 12 \
                and xact_date.month == 1:
            xact_date = date(xact_date.year + 1, xact_date.month, xact_date.day)

        self.cur_xact.date = xact_date
        self.previous_date = xact_date

    def save_xact_ref_num(self, line):
        self.cur_xact.reference_num = line

    def save_xact_desc(self, line):
        self.cur_xact.description = line

    def save_xact_amt(self, line):
        value = Decimal(re.sub(r'[^\d.]', '', line))
        self.cur_xact.amount = value
        # print("Found transaction: " + str(self.cur_xact))

    def process_line(self, line):
        self.process(line)
        return self.machine.model.state


rePREVIOUS_BALANCE_DATE = re.compile("Previous balance as of (\d\d/\d\d/\d\d\d\d)")

class FileReaderFSM:
    def __init__(self):
        xact_reading_states = [
            XactReadingFSMStates.DATE,
            XactReadingFSMStates.REF,
            XactReadingFSMStates.DESC,
            XactReadingFSMStates.AMT,
            XactReadingFSMStates.FINISHED
        ]

        xact_reading_transitions = [
            {'trigger': 'processXact', 'source': XactReadingFSMStates.DATE,
             #'conditions': lambda line: re.search(reDateOfTransaction, line) is not None,
             'dest': XactReadingFSMStates.REF,
             'after': lambda line: print(line), },
            {'trigger': 'processXact', 'source': XactReadingFSMStates.REF,
             'dest': XactReadingFSMStates.DESC,
             'after': lambda line: print(line), },
            {'trigger': 'processXact', 'source': XactReadingFSMStates.DESC,
             'dest': XactReadingFSMStates.AMT,
             'after': lambda line: print(line), },
            {'trigger': 'processXact', 'source': XactReadingFSMStates.AMT,
             'dest': XactReadingFSMStates.FINISHED,
             'after': lambda line: print(line), },
        ]

        xact_reader_fsm = HierarchicalMachine(states=xact_reading_states, \
                                      transitions=xact_reading_transitions, \
                                      initial='XactReadingFSMStates.DATE')

        file_reading_states = [
            FileReadingFSMStates.PreviousBalanceDate,
            FileReadingFSMStates.SearchingForTransactionDetails,
            FileReadingFSMStates.SearchingForTransactionType,
            {'name': FileReadingFSMStates.Payments.name, 'children': xact_reader_fsm},
            {'name': FileReadingFSMStates.OtherCredits.name, 'children': xact_reader_fsm},
            {'name': FileReadingFSMStates.Purchases.name, 'children': xact_reader_fsm},
            FileReadingFSMStates.Finished
        ]

        file_reading_transitions = [
            # First, find the date of the prior statement, so we can figure out which year we're in
            {'trigger': 'process', 'source': FileReadingFSMStates.PreviousBalanceDate,
             'conditions': lambda line: re.search(rePREVIOUS_BALANCE_DATE, line) is not None,
             'dest': FileReadingFSMStates.SearchingForTransactionDetails,
             'after': 'save_previous_balance_date', },

            # The transactions are all listed together, so let's find where the transactions start:
            {'trigger': 'process', 'source': FileReadingFSMStates.SearchingForTransactionDetails,
             'conditions': lambda line: FileReadingFSMStates.SearchingForTransactionDetails.value in line,
             'dest': FileReadingFSMStates.SearchingForTransactionType,
             'after': 'found_search_for_xact'},

            # Transactions are subgrouped by type(payment to Venmo, credits / refunds, purchases)
            # (They always seem to be in PAYMENT, OTHER_CREDIT, PURCHASES order
            {'trigger': 'process', 'source': [FileReadingFSMStates.SearchingForTransactionType,
                                              FileReadingFSMStates.OtherCredits,
                                              FileReadingFSMStates.Payments],
             'conditions': lambda line: FileReadingFSMStates.START_OF_PAYMENTS.value in line,
             'dest': FileReadingFSMStates.Payments,
             'after': 'save_current_xact_type',},
            {'trigger': 'process', 'source': [FileReadingFSMStates.SearchingForTransactionType,
                                              FileReadingFSMStates.Purchases,
                                              FileReadingFSMStates.Payments, ],
             'conditions': lambda line: FileReadingFSMStates.START_OF_OTHER_CREDITS.value in line,
             'dest': FileReadingFSMStates.OtherCredits,
             'after': 'save_current_xact_type'},
            {'trigger': 'process', 'source': [FileReadingFSMStates.SearchingForTransactionType,
                                              FileReadingFSMStates.Payments,
                                              FileReadingFSMStates.OtherCredits, ],
             'conditions': lambda line: FileReadingFSMStates.START_OF_PURCHASES.value in line,
             'dest': FileReadingFSMStates.Purchases,
             'after': 'save_current_xact_type'},

            # Venmo always puts a boilerplate 2nd page, which interrupts the transaction list started on the 1st page
            {'trigger': 'process', 'source': [FileReadingFSMStates.SearchingForTransactionType,
                                              FileReadingFSMStates.Payments,
                                              FileReadingFSMStates.OtherCredits,
                                              FileReadingFSMStates.Purchases],
             'conditions': lambda line: FileReadingFSMStates.TRANSACTIONS_CONTINUED_LATER.value in line,
             'dest': FileReadingFSMStates.SearchingForTransactionDetails, },

            # Once we've found the end of the transactions we're done
            {'trigger': 'process', 'source': [FileReadingFSMStates.SearchingForTransactionType,
                                              FileReadingFSMStates.Payments,
                                              FileReadingFSMStates.Purchases,
                                              FileReadingFSMStates.OtherCredits, ],
             'conditions': lambda line: FileReadingFSMStates.Finished.value in line,
             'dest': FileReadingFSMStates.Finished, },

            # Internal file_reading_transitions MUST go last ########################################################################
            # otherwise they'll match and file_reading_transitions will stop any other real state file_reading_transitions from happening

            # If we've found transactions, take the next column and hand it off to the line reader
            {'trigger': 'process', 'source': [FileReadingFSMStates.Payments,
                                              FileReadingFSMStates.Purchases,
                                              FileReadingFSMStates.OtherCredits],
             'dest': None,  # internal transition - do this every time we call 'process' and we're in PAYMENTS
             'after': 'process_xact_chunk'},
        ]


        # Initialize the state machine with states and file_reading_transitions
        self.machine = HierarchicalMachine(model=self, states=file_reading_states, \
                                           transitions=file_reading_transitions, \
                                           initial=FileReadingFSMStates.PreviousBalanceDate)
        self.previous_balance_date: date = None
        self.current_xact_type = FileReadingFSMStates.SearchingForTransactionType
        self.line_reader = LineReadingFSM()
        #self.line_reader.log_state_machine.setLevel(logging.WARN)

        self.all_payments: [Transaction] = []
        self.all_other_credits: [Transaction] = []
        self.all_purchases: [Transaction] = []

    def process_xact_chunk(self, line):
        # print(f"process_xact_chunk: {self.state} line={line}")
        self.processXact(line)

        result = self.line_reader.process_line(line)

        if result == XactReadingFSMStates.FINISHED:
            current_xact_type = self.current_xact_type.split('_')[0]
            if current_xact_type == FileReadingFSMStates.Payments.name:
                self.all_payments.append(self.line_reader.cur_xact)
            elif current_xact_type == FileReadingFSMStates.OtherCredits.name:
                self.all_other_credits.append(self.line_reader.cur_xact)
            elif current_xact_type == FileReadingFSMStates.Purchases.name:
                self.all_purchases.append(self.line_reader.cur_xact)
            else:
                raise Exception(f"self.current_xact_type is neither PAYMENTS nor OTHER_CREDITS nor PURCHASES, but instead it's {self.current_xact_type}")

            self.line_reader.reset()

        return result

    def save_previous_balance_date(self, line):
        global previous_balance_date
        match = re.search(rePREVIOUS_BALANCE_DATE, line)
        assert match
        previous_balance_date = datetime.strptime(match.group(1), "%m/%d/%Y").date()

    def found_search_for_xact(self, line):
        if self.current_xact_type == FileReadingFSMStates.SearchingForTransactionType:
            self.machine.set_state(FileReadingFSMStates.SearchingForTransactionType)
        else:  # otherwise keep looking for whatever sort of xact we've most recently seen:
            self.machine.set_state(self.current_xact_type)

    def save_current_xact_type(self, line):
        self.current_xact_type = self.machine.model.state


class BreakLoop(Exception): pass # ChatGPT gave me this terrible hack;  I'm totally gonna use it :)

def ConvertVenmoStatement(file_to_parse: str, output_file: str):
    program_state = FileReaderFSM()

    fd = open(file_to_parse, "rb")
    viewer = SimplePDFViewer(fd)

    try:
        for canvas in viewer:
            # page_text = canvas.text_content # text_content has lots of extra info & formatting, etc
            page_strings = canvas.strings  # this is a list of the actual text that we want to process

            for line in page_strings:
                program_state.process(line)
                print(str(program_state.state) + ": cur_xact: " + str(program_state.current_xact_type) + " : " + line)

                if program_state.state is FileReadingFSMStates.Finished:
                    print("Finished parsing - exiting!")
                    raise BreakLoop

    except BreakLoop:
        pass
    print(" ")

    def print_xacts(xacts: [Transaction], name: str):
        total = Decimal(0)
        for p in xacts:
            print(p)
            total = total + p.amount

        print("\tFound a total of " + str(len(xacts)) + " " + name)
        print("\tTotal cost: " + str(total))
        print("")

    ### Write transactions to the file
    #  Make payments & credits negative, leave purchases positive
    all_xacts = [Transaction(xact.date, xact.reference_num, xact.description, -1 * xact.amount) for xact in
                 program_state.all_payments + program_state.all_other_credits] \
                + program_state.all_purchases
    all_xacts.sort(key=attrgetter('date'))

    with open(output_file, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(["Account Name: Venmo Credit Card"]) # With this here KMM won't ask for the account name
        csv_writer.writerow(Transaction.get_csv_header())
        csv_writer.writerows(all_xacts)

    ### Print summary of transactions
    xact_adder = lambda x, y: Decimal(x + y.amount)

    # print_xacts(all_xacts, "ALL TRANSACTIONS")
    # print("")

    # print_xacts(all_payments, "payments")
    total = reduce(xact_adder, program_state.all_payments, Decimal(0))
    print("Sum of payments: " + str(total))

    # print_xacts(all_other_credits, "other credits")
    total = reduce(xact_adder, program_state.all_other_credits, Decimal(0))
    print("Sum of other credits: " + str(total))

    # print_xacts(all_purchases, "purchases")
    total = reduce(xact_adder, program_state.all_purchases, Decimal(0))
    print("Sum of purchases: " + str(total))

    print("\nWrote all transactions to\n\t" + output_file)
