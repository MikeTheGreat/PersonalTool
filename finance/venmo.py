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

from pdfreader import SimplePDFViewer
from transitions import Machine

from finance.transaction import Transaction

previous_balance_date: date = None


class FileReadingFSMStates(Enum):
    PREVIOUS_BALANCE_DATE = "Previous balance as of"
    SEARCHING_FOR_TRANSACTION_DETAILS = "Transaction details"
    SEARCHING_FOR_TRANSACTION_TYPE = "Haven't found transactions type yet (this string does not occur in the file itself)"
    TRANSACTIONS_CONTINUED_LATER = "(Continued on next page)"
    START_OF_PAYMENTS = "Payments"
    PAYMENTS = "Reading payment lines (this string does not occur in the file itself)"
    START_OF_OTHER_CREDITS = "Other credits"
    OTHER_CREDITS = "Reading Other credits lines (this string does not occur in the file itself)"
    START_OF_PURCHASES = "Purchases and other debits"
    PURCHASES = "Reading purchase lines (this string does not occur in the file itself)"
    DATE = 'date'
    REF = 'ref'
    DESC = 'desc'
    AMT = 'amt'
    Finished = "Total fees charged this period"

reDateOfTransaction = re.compile("(\d\d/\d\d)")
rePREVIOUS_BALANCE_DATE = re.compile("Previous balance as of (\d\d/\d\d/\d\d\d\d)")

class FileReaderFSM:
    def __init__(self):

        file_reading_states = [
            FileReadingFSMStates.PREVIOUS_BALANCE_DATE,
            FileReadingFSMStates.SEARCHING_FOR_TRANSACTION_DETAILS,
            FileReadingFSMStates.SEARCHING_FOR_TRANSACTION_TYPE,
            FileReadingFSMStates.PAYMENTS,
            FileReadingFSMStates.OTHER_CREDITS,
            FileReadingFSMStates.PURCHASES,
            FileReadingFSMStates.Finished,
            FileReadingFSMStates.DATE,
            FileReadingFSMStates.REF,
            FileReadingFSMStates.DESC,
            FileReadingFSMStates.AMT
        ]

        file_reading_transitions = [
            # First, find the date of the prior statement, so we can figure out which year we're in
            {'trigger': 'process', 'source': FileReadingFSMStates.PREVIOUS_BALANCE_DATE,
             'conditions': lambda line: re.search(rePREVIOUS_BALANCE_DATE, line) is not None,
             'dest': FileReadingFSMStates.SEARCHING_FOR_TRANSACTION_DETAILS,
             'after': 'save_previous_balance_date', },

            # The transactions are all listed together, so let's find where the transactions start:
            {'trigger': 'process', 'source': FileReadingFSMStates.SEARCHING_FOR_TRANSACTION_DETAILS,
             'conditions': lambda line: FileReadingFSMStates.SEARCHING_FOR_TRANSACTION_DETAILS.value in line,
             'dest': FileReadingFSMStates.SEARCHING_FOR_TRANSACTION_TYPE,
             'after': 'found_search_for_xact'},

            # Transactions are subgrouped by type(payment to Venmo, credits / refunds, purchases)
            # (They always seem to be in PAYMENT, OTHER_CREDIT, PURCHASES order
            {'trigger': 'process', 'source': [FileReadingFSMStates.SEARCHING_FOR_TRANSACTION_TYPE,
                                              FileReadingFSMStates.OTHER_CREDITS,
                                              FileReadingFSMStates.PURCHASES,
                                              FileReadingFSMStates.DATE],
             'conditions': lambda line: FileReadingFSMStates.START_OF_PAYMENTS.value == line,
             'dest': FileReadingFSMStates.PAYMENTS,
             'after': 'save_current_xact_type', },
            {'trigger': 'process', 'source': FileReadingFSMStates.PAYMENTS,
             'dest': FileReadingFSMStates.DATE },

            {'trigger': 'process', 'source': [FileReadingFSMStates.SEARCHING_FOR_TRANSACTION_TYPE,
                                              FileReadingFSMStates.PURCHASES,
                                              FileReadingFSMStates.PAYMENTS,
                                              FileReadingFSMStates.DATE,],
             'conditions': lambda line: FileReadingFSMStates.START_OF_OTHER_CREDITS.value in line,
             'dest': FileReadingFSMStates.OTHER_CREDITS,
             'after': 'save_current_xact_type', },
            {'trigger': 'process', 'source': FileReadingFSMStates.OTHER_CREDITS,
             'dest': FileReadingFSMStates.DATE, },

            {'trigger': 'process', 'source': [FileReadingFSMStates.SEARCHING_FOR_TRANSACTION_TYPE,
                                              FileReadingFSMStates.PAYMENTS,
                                              FileReadingFSMStates.OTHER_CREDITS,
                                              FileReadingFSMStates.DATE,],
             'conditions': lambda line: FileReadingFSMStates.START_OF_PURCHASES.value in line,
             'dest': FileReadingFSMStates.PURCHASES,
             'after': 'save_current_xact_type', },
            {'trigger': 'process', 'source': FileReadingFSMStates.PURCHASES,
             'dest': FileReadingFSMStates.DATE},

            # Venmo always puts a boilerplate 2nd page, which interrupts the transaction list started on the 1st page
            {'trigger': 'process', 'source': [FileReadingFSMStates.SEARCHING_FOR_TRANSACTION_TYPE,
                                              FileReadingFSMStates.PAYMENTS,
                                              FileReadingFSMStates.OTHER_CREDITS,
                                              FileReadingFSMStates.PURCHASES,
                                              FileReadingFSMStates.DATE],
             'conditions': lambda line: FileReadingFSMStates.TRANSACTIONS_CONTINUED_LATER.value in line,
             'dest': FileReadingFSMStates.SEARCHING_FOR_TRANSACTION_DETAILS, },

            # Once we've found the end of the transactions we're done
            {'trigger': 'process', 'source': [FileReadingFSMStates.SEARCHING_FOR_TRANSACTION_TYPE,
                                              FileReadingFSMStates.PAYMENTS,
                                              FileReadingFSMStates.PURCHASES,
                                              FileReadingFSMStates.OTHER_CREDITS,
                                              FileReadingFSMStates.DATE],
             'conditions': lambda line: FileReadingFSMStates.Finished.value in line,
             'dest': FileReadingFSMStates.Finished, },

            # Read through a given transaction
            {'trigger': 'process', 'source': FileReadingFSMStates.DATE,
             'conditions': lambda line: re.search(reDateOfTransaction, line) is not None,
             'dest': FileReadingFSMStates.REF,
             'after': 'save_xact_date', },
            {'trigger': 'process', 'source': FileReadingFSMStates.REF,
             'dest': FileReadingFSMStates.DESC,
             'after': 'save_xact_ref_num', },
            {'trigger': 'process', 'source': FileReadingFSMStates.DESC,
             'dest': FileReadingFSMStates.AMT,
             'after': 'save_xact_desc'},
            {'trigger': 'process', 'source': FileReadingFSMStates.AMT,
             'dest': FileReadingFSMStates.DATE,  # Look for the next one
             'after': 'save_xact_amt_and_finish_xact'},

            # Internal file_reading_transitions MUST go last ########################################################################
            # otherwise they'll match and file_reading_transitions will stop any other real state file_reading_transitions from happening

            # If we've found transactions, take the next column and hand it off to the line reader
            # {'trigger': 'process', 'source': [FileReadingFSMStates.Payments,
            #                                   FileReadingFSMStates.Purchases,
            #                                   FileReadingFSMStates.OtherCredits],
            #  'dest': None,  # internal transition - do this every time we call 'process' and we're in PAYMENTS
            #  'after': 'processXact'},
        ]


        # Initialize the state machine with states and file_reading_transitions
        self.machine = Machine(model=self, states=file_reading_states, \
                               transitions=file_reading_transitions, \
                               initial=FileReadingFSMStates.PREVIOUS_BALANCE_DATE)
        self.previous_balance_date: date = None
        self.all_payments: [Transaction] = []
        self.all_other_credits: [Transaction] = []
        self.all_purchases: [Transaction] = []

        # Line (Transaction) Reader:
        self.current_xact_type = FileReadingFSMStates.SEARCHING_FOR_TRANSACTION_TYPE
        self.previous_date = None
        self.cur_xact = Transaction()

    def save_previous_balance_date(self, line):
        global previous_balance_date
        match = re.search(rePREVIOUS_BALANCE_DATE, line)
        assert match
        previous_balance_date = datetime.strptime(match.group(1), "%m/%d/%Y").date()

    def found_search_for_xact(self, line):
        if self.current_xact_type == FileReadingFSMStates.SEARCHING_FOR_TRANSACTION_TYPE:
            self.machine.set_state(FileReadingFSMStates.SEARCHING_FOR_TRANSACTION_TYPE)
        else:  # otherwise keep looking for whatever sort of xact we've most recently seen:
            self.machine.set_state(self.current_xact_type)

    def save_current_xact_type(self, line):
        self.current_xact_type = self.machine.model.state

    # Line reader methods:
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

        self.cur_xact.xact_date = xact_date
        self.previous_date = xact_date

    def save_xact_ref_num(self, line):
        self.cur_xact.reference_num = line

    def save_xact_desc(self, line):
        self.cur_xact.description = line

    def save_xact_amt_and_finish_xact(self, line):
        value = Decimal(re.sub(r'[^\d.]', '', line))
        self.cur_xact.amount = value
        # print("Found transaction: " + str(self.cur_xact))

        # Saved in case we want to check pytransitions state:
        # self.machine.is_state("Payments", self, allow_substates=True)

        if self.current_xact_type == FileReadingFSMStates.PAYMENTS:
            self.all_payments.append(self.cur_xact)
        elif self.current_xact_type == FileReadingFSMStates.OTHER_CREDITS:
            self.all_other_credits.append(self.cur_xact)
        elif self.current_xact_type == FileReadingFSMStates.PURCHASES:
            self.all_purchases.append(self.cur_xact)
        else:
            raise Exception(f"self.current_xact_type is neither PAYMENTS nor OTHER_CREDITS nor PURCHASES, but instead it's {self.current_xact_type}")

        self.cur_xact = Transaction()


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
                # print(str(program_state.state) + ": cur_xact: " + str(program_state.current_xact_type) + " : " + line)

                if program_state.state is FileReadingFSMStates.Finished:
                    # print("Finished parsing - exiting!")
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
    all_xacts = [Transaction(None, xact.xact_date, xact.reference_num, xact.description, -1 * xact.amount) for xact in
                 program_state.all_payments + program_state.all_other_credits] \
                + program_state.all_purchases
    all_xacts.sort(key=attrgetter('xact_date'))

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
