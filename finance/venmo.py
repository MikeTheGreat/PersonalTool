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

logging.basicConfig(level=logging.INFO)
# Set transitions' log level to INFO; DEBUG messages will be omitted
logging.getLogger('transitions').setLevel(logging.INFO)

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


@define
class States:
    # what are we looking for next?
    possible_states: [str]
    current_state: int
    log_state_machine: Any

    def __init__(self, states):
        self.possible_states = states
        self.current_state = 0
        log_name = "PersonalTool.Venmo.StateMachine" + "." + type(self).__name__
        self.log_state_machine = logging.getLogger(log_name)
        self.log_state_machine.setLevel(logging.ERROR)

    def getCurrentState(self):
        return self.possible_states[self.current_state]

    def setCurrentState(self, newState: str):
        # index() "index raises ValueError when x is not found in s"
        # From: https://docs.python.org/3/library/stdtypes.html?highlight=list%20index
        self.current_state = self.possible_states.index(newState)
        self.log_state_machine.info(
            "State Machine changed state to " + str(self.current_state) + ": \"" + self.getCurrentState() + "\"")


DATE: str = 'date'
reDateOfTransaction = re.compile("(\d\d/\d\d)")
REF: str = 'ref'
DESC: str = 'desc'
AMT: str = 'amt'


@define
class ReadingLineStates(States):
    cur_xact: Transaction  # We'll reset to a new object a lot
    previous_date: date  # So remember when the last transaction was separate from cur_xact

    def __init__(self):
        super().__init__([DATE, REF, DESC, AMT, TransactionStates.FINISHED.name])
        self.previous_date = None
        self.reset()

    def reset(self):
        self.cur_xact = Transaction()
        self.setCurrentState(DATE)

    def processLine(self, line):
        global previous_balance_date

        if self.getCurrentState() == DATE:
            if re.search(reDateOfTransaction, line):
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
                self.setCurrentState(REF)

        elif self.getCurrentState() == REF:
            self.cur_xact.reference_num = line
            self.setCurrentState(DESC)

        elif self.getCurrentState() == DESC:
            self.cur_xact.description = line
            self.setCurrentState(AMT)

        elif self.getCurrentState() == AMT:
            value = Decimal(re.sub(r'[^\d.]', '', line))
            self.cur_xact.amount = value

            print("Found transaction: " + str(self.cur_xact))

            self.setCurrentState(TransactionStates.FINISHED.name)

        elif self.getCurrentState() == TransactionStates.FINISHED.name:
            pass

        return self.getCurrentState()


rePREVIOUS_BALANCE_DATE = re.compile("Previous balance as of (\d\d/\d\d/\d\d\d\d)")
class TransactionStates(Enum):
    PREVIOUS_BALANCE_DATE = "Previous balance as of"
    SEARCHING_FOR_TRANSACTION_DETAILS = "Transaction details"
    # We'll see the "Transaction Details" h2 header, then later in the table we'll see payment / purchase / etc h3 headers
    # So start off in "SEARCHING_FOR_TRANSACTION_TYPE"

    SEARCHING_FOR_TRANSACTION_TYPE = "Haven't found transactions type yet (this string does not occur in the file itself)"
    TRANSACTIONS_CONTINUED_LATER = "(Continued on next page)"
    START_OF_PAYMENTS = "Payments"
    PAYMENTS = "Reading payment lines (this string does not occur in the file itself)"
    START_OF_OTHER_CREDITS = "Other credits"
    OTHER_CREDITS = "Reading Other credits lines (this string does not occur in the file itself)"
    START_OF_PURCHASES = "Purchases and other debits"
    PURCHASES = "Reading purchase lines (this string does not occur in the file itself)"
    FINISHED = "Total fees charged this period"



class ProgramStates:
    states = [
        TransactionStates.PREVIOUS_BALANCE_DATE.name,
        TransactionStates.SEARCHING_FOR_TRANSACTION_DETAILS.name,
        TransactionStates.SEARCHING_FOR_TRANSACTION_TYPE.name,
        TransactionStates.PAYMENTS.name,
        TransactionStates.OTHER_CREDITS.name,
        TransactionStates.PURCHASES.name,
        TransactionStates.FINISHED.name
    ]

    def __init__(self):
        transitions = [
            {'trigger': 'process', 'source': TransactionStates.PREVIOUS_BALANCE_DATE.name,
             'conditions': lambda line: re.search(rePREVIOUS_BALANCE_DATE, line) is not None,
             'dest': TransactionStates.SEARCHING_FOR_TRANSACTION_DETAILS.name,
             'before': 'save_previous_balance_date', },
            {'trigger': 'process', 'source': TransactionStates.SEARCHING_FOR_TRANSACTION_DETAILS.name,
             'conditions': lambda line: TransactionStates.SEARCHING_FOR_TRANSACTION_DETAILS.value in line,
             'dest': TransactionStates.SEARCHING_FOR_TRANSACTION_TYPE.name,
             'after': 'found_search_for_xact'},

            #################### SEARCHING_FOR_TRANSACTION_TYPE ########################################################
            {'trigger': 'process', 'source': TransactionStates.SEARCHING_FOR_TRANSACTION_TYPE.name, 'dest': TransactionStates.PAYMENTS.name,
             'before': self.make_store_current_xact_type(TransactionStates.PAYMENTS),
             'conditions': lambda line: TransactionStates.START_OF_PAYMENTS.value in line,}, ## TODO: ReadingLineStates
            {'trigger': 'process', 'source': TransactionStates.SEARCHING_FOR_TRANSACTION_TYPE.name,
             'conditions': lambda line: TransactionStates.START_OF_OTHER_CREDITS.value in line,
             'dest': TransactionStates.OTHER_CREDITS.name,
             'before': self.make_store_current_xact_type(TransactionStates.OTHER_CREDITS)},  ## TODO: ReadingLineStates
            {'trigger': 'process', 'source': TransactionStates.SEARCHING_FOR_TRANSACTION_TYPE.name,
             'conditions': lambda line: TransactionStates.START_OF_PURCHASES.value in line,
             'dest': TransactionStates.PURCHASES.name,
             'before': self.make_store_current_xact_type(TransactionStates.PURCHASES)},  ## TODO: ReadingLineStates
            {'trigger': 'process', 'source': TransactionStates.SEARCHING_FOR_TRANSACTION_TYPE.name,
             'conditions': lambda line: TransactionStates.TRANSACTIONS_CONTINUED_LATER.value in line,
            'dest': TransactionStates.SEARCHING_FOR_TRANSACTION_DETAILS.name,},
             # 'before': },  ## TODO: line_reader.reset()  # dump any partial info

            #################### PAYMENTS ##############################################################################
            {'trigger': 'process', 'source': TransactionStates.PAYMENTS.name,
             'conditions': lambda line: TransactionStates.START_OF_PURCHASES.value in line,
             'dest': TransactionStates.PURCHASES.name,
             'before': self.make_store_current_xact_type(TransactionStates.PURCHASES)},  ## TODO: ReadingLineStates
            {'trigger': 'process', 'source': TransactionStates.PAYMENTS.name,
             'dest': TransactionStates.OTHER_CREDITS.name,
             'conditions': lambda line: TransactionStates.START_OF_OTHER_CREDITS.value in line,
             'before': self.make_store_current_xact_type(TransactionStates.OTHER_CREDITS)},  ## TODO: ReadingLineStates
            {'trigger': 'process', 'source': TransactionStates.PAYMENTS.name,
             'dest': TransactionStates.SEARCHING_FOR_TRANSACTION_DETAILS.name,
             'conditions': lambda line: TransactionStates.TRANSACTIONS_CONTINUED_LATER.value in line},
             # 'before': },  ## TODO: line_reader.reset()  # dump any partial info
            {'trigger': 'process', 'source': TransactionStates.PAYMENTS.name,
             'dest': None, # internal transition - do this every time we call 'process' and we're in PAYMENTS
             'before': 'process_xact_chunk'},
            #     elif line_reader.processLine(line) == FINISHED:
            #         all_payments.append(line_reader.cur_xact)
            #         line_reader.reset()

            #################### OTHER CREDITS #########################################################################
            {'trigger': 'process', 'source': TransactionStates.OTHER_CREDITS.name,
             'conditions': lambda line: TransactionStates.START_OF_PURCHASES.value in line,
             'dest': TransactionStates.PURCHASES.name,
             'before': self.make_store_current_xact_type(TransactionStates.PURCHASES)},  ## TODO: ReadingLineStates
            {'trigger': 'process', 'source': TransactionStates.OTHER_CREDITS.name,
             'conditions': lambda line: TransactionStates.FINISHED.value in line,
             'dest': TransactionStates.FINISHED.name,},
            {'trigger': 'process', 'source': TransactionStates.OTHER_CREDITS.name,
             'conditions': lambda line: TransactionStates.TRANSACTIONS_CONTINUED_LATER.value in line,
             'dest': TransactionStates.SEARCHING_FOR_TRANSACTION_DETAILS.name,},
            # 'before': },  ## TODO: line_reader.reset()  # dump any partial info
            {'trigger': 'process', 'source': TransactionStates.OTHER_CREDITS.name,
             'dest': None, # internal transition - do this every time we call 'process' and we're in PAYMENTS
             'before': 'process_xact_chunk'},

            #################### PURCHASES #############################################################################
            {'trigger': 'process', 'source': TransactionStates.PURCHASES.name,
             'conditions': lambda line: TransactionStates.FINISHED.value in line,
             'dest': TransactionStates.FINISHED.name,},
            {'trigger': 'process', 'source': TransactionStates.PURCHASES.name,
             'conditions': lambda line: TransactionStates.TRANSACTIONS_CONTINUED_LATER.value in line,
             'dest': TransactionStates.SEARCHING_FOR_TRANSACTION_DETAILS.name,},
             # 'before': },  ## TODO: line_reader.reset()  # dump any partial info

            {'trigger': 'process', 'source': TransactionStates.PURCHASES.name,
             'dest': None, # internal transition - do this every time we call 'process' and we're in PAYMENTS
             'before': 'process_xact_chunk'},
        ]


        # Initialize the state machine with states and transitions
        self.machine = Machine(model=self, states=ProgramStates.states, transitions=transitions,
                               initial=TransactionStates.PREVIOUS_BALANCE_DATE.name)
        self.previous_balance_date: date = None
        self.current_xact_type = TransactionStates.SEARCHING_FOR_TRANSACTION_TYPE.name
        self.line_reader = ReadingLineStates()
        self.line_reader.log_state_machine.setLevel(logging.WARN)

        self.all_payments: [Transaction] = []
        self.all_other_credits: [Transaction] = []
        self.all_purchases: [Transaction] = []

    def process_xact_chunk(self, line):
        # print(f"process_xact_chunk: {self.state} line={line}")
        result = self.line_reader.processLine(line)

        if result == TransactionStates.FINISHED.name:
            if self.current_xact_type == TransactionStates.PAYMENTS.name:
                self.all_payments.append(self.line_reader.cur_xact)
            elif self.current_xact_type == TransactionStates.OTHER_CREDITS.name:
                self.all_other_credits.append(self.line_reader.cur_xact)
            elif self.current_xact_type == TransactionStates.PURCHASES.name:
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
        if self.current_xact_type == TransactionStates.SEARCHING_FOR_TRANSACTION_TYPE.name:
            self.machine.set_state(TransactionStates.SEARCHING_FOR_TRANSACTION_TYPE.name)
        else:  # otherwise keep looking for whatever sort of xact we've most recently seen:
            self.machine.set_state(self.current_xact_type)

    def make_store_current_xact_type(self, xact_state: TransactionStates):
        return lambda event_data: self._set_current_xact_type(xact_state)

    def _set_current_xact_type(self, xact_state: TransactionStates):
        self.current_xact_type = xact_state.name
        ## line_reader = ReadingLineStates() ## TODO: LINE READING!!!!


class BreakLoop(Exception): pass # ChatGPT gave me this terrible hack;  I'm totally gonna use it :)

def ConvertVenmoStatement(file_to_parse: str, output_file: str):
    program_state = ProgramStates()

    fd = open(file_to_parse, "rb")
    viewer = SimplePDFViewer(fd)

    try:
        for canvas in viewer:
            # page_text = canvas.text_content # text_content has lots of extra info & formatting, etc
            page_strings = canvas.strings  # this is a list of the actual text that we want to process

            for line in page_strings:
                program_state.process(line)
                #print(program_state.state + ": cur_xact: " + program_state.current_xact_type + " : " + line)

                if program_state.state is TransactionStates.FINISHED.name:
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
