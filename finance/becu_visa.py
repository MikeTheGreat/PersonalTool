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


from transitions import Machine
# from pdfreader import SimplePDFViewer
# from pdfminer.high_level import extract_text
import pymupdf

from finance.transaction import Transaction


previous_balance_date: date = None



class BecuReadingFSMStates(Enum):
    SEARCHING_FOR_PREVIOUS_BALANCE_DATE = "Statement Open Date"
    SEARCHING_FOR_TRANSACTION_DETAILS = "Transactions"
    POST_DATE = 'Post Date'
    XACT_DATE = 'Trans Date'
    REF = 'Reference'
    DESC = 'Description'
    AMT = 'Amount'
    Finished = "TOTAL FEES FOR THIS PERIOD"

rePREVIOUS_BALANCE_DATE = re.compile("(\d\d/\d\d/\d\d\d\d)")
reDateOfTransaction = re.compile("(\d\d/\d\d)")
rePAYMENT = re.compile("PAYMENT - THANK YOU")
reAmount = re.compile(r'-?\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d+(\.\d{2})?)')
class BecuReaderFSM:
    def __init__(self):

        file_reading_states = [
            BecuReadingFSMStates.SEARCHING_FOR_PREVIOUS_BALANCE_DATE,
            BecuReadingFSMStates.SEARCHING_FOR_TRANSACTION_DETAILS,
            BecuReadingFSMStates.POST_DATE,
            BecuReadingFSMStates.XACT_DATE,
            BecuReadingFSMStates.REF,
            BecuReadingFSMStates.DESC,
            BecuReadingFSMStates.AMT,
            BecuReadingFSMStates.Finished,
        ]

        file_reading_transitions = [
            # First, find the date of the prior statement, so we can figure out which year we're in
            {'trigger': 'process', 'source': BecuReadingFSMStates.SEARCHING_FOR_PREVIOUS_BALANCE_DATE,
             'conditions': lambda line: re.search(rePREVIOUS_BALANCE_DATE, line) is not None,
             'dest': BecuReadingFSMStates.SEARCHING_FOR_TRANSACTION_DETAILS,
             'after': 'save_previous_balance_date', },

            # The transactions are all listed together, so let's find where the transactions start:
            {'trigger': 'process', 'source': BecuReadingFSMStates.SEARCHING_FOR_TRANSACTION_DETAILS,
             'conditions': lambda line: BecuReadingFSMStates.SEARCHING_FOR_TRANSACTION_DETAILS.value in line,
             'dest': BecuReadingFSMStates.POST_DATE,
             },

            # Read through a given transaction
            {'trigger': 'process', 'source': BecuReadingFSMStates.POST_DATE,
             'conditions': lambda line: re.search(reDateOfTransaction, line) is not None,
             'dest': BecuReadingFSMStates.XACT_DATE,
             'after': 'save_post_date', },
            {'trigger': 'process', 'source': BecuReadingFSMStates.XACT_DATE,
             'conditions': lambda line: re.search(reDateOfTransaction, line) is not None,
             'dest': BecuReadingFSMStates.REF,
             'after': 'save_xact_date', },
            {'trigger': 'process', 'source': BecuReadingFSMStates.REF,
             'dest': BecuReadingFSMStates.DESC,
             'after': 'save_xact_ref_num', },
            {'trigger': 'process', 'source': BecuReadingFSMStates.DESC,
             'dest': BecuReadingFSMStates.AMT,
             'after': 'save_xact_desc'},
            {'trigger': 'process', 'source': BecuReadingFSMStates.AMT,
             'conditions': lambda line: re.search(reAmount, line) is not None,
             'dest': BecuReadingFSMStates.POST_DATE,  # Look for the next one
             'after': 'save_xact_amt_and_finish_xact'},

            {'trigger': 'process', 'source': BecuReadingFSMStates.POST_DATE,
             'conditions': lambda line: BecuReadingFSMStates.Finished.value in line,
             'dest': BecuReadingFSMStates.Finished},
        ]


        # Initialize the state machine with states and file_reading_transitions
        self.machine = Machine(model=self, states=file_reading_states, \
                               transitions=file_reading_transitions, \
                               initial=BecuReadingFSMStates.SEARCHING_FOR_PREVIOUS_BALANCE_DATE)
        self.previous_balance_date: date = None
        self.all_payments: [Transaction] = []
        self.all_other_credits: [Transaction] = []
        self.all_purchases: [Transaction] = []

        # Line (Transaction) Reader:
        self.current_xact_type = BecuReadingFSMStates.SEARCHING_FOR_TRANSACTION_DETAILS
        self.previous_date = None
        self.cur_xact = Transaction()

    def save_previous_balance_date(self, line):
        global previous_balance_date
        match = re.search(rePREVIOUS_BALANCE_DATE, line)
        assert match
        previous_balance_date = datetime.strptime(match.group(1), "%m/%d/%Y").date()

    def extract_date(self, line):
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

        return xact_date

    def save_post_date(self, line):
        self.cur_xact.post_date = self.extract_date(line)
    # Line reader methods:
    def save_xact_date(self, line):
        self.cur_xact.xact_date = self.extract_date(line)

    def save_xact_ref_num(self, line):
        self.cur_xact.reference_num = line

    def save_xact_desc(self, line):
        self.cur_xact.description = line

    def save_xact_amt_and_finish_xact(self, line):
        value = Decimal(re.sub(r'[^\d.]', '', line))
        self.cur_xact.amount = value

        if line[0] == '$':
            self.all_purchases.append(self.cur_xact)
        elif re.search(rePAYMENT, self.cur_xact.description) is not None:
            self.all_payments.append(self.cur_xact)
        else:
            self.all_other_credits.append(self.cur_xact)
        # print("Found transaction: " + str(self.cur_xact))

        self.cur_xact = Transaction()


class BreakLoop(Exception): pass # ChatGPT gave me this terrible hack;  I'm totally gonna use it :)

def ConvertBecuStatement(file_to_parse: str, output_file: str):
    program_state = BecuReaderFSM()

    doc = pymupdf.open(file_to_parse)  # open a document

    try:
        for page in doc:  # iterate the document pages
            lines = page.get_text().split("\n")  # get plain text (is in UTF-8)
            for line in lines:
                program_state.process(line)
                print(str(program_state.state) + " : " + line)

                if program_state.state is BecuReadingFSMStates.Finished:
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
        csv_writer.writerow(["Account Name: BECU VISA Card"]) # With this here KMM won't ask for the account name
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
