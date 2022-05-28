import csv
from functools import reduce
import re
from datetime import date, datetime
from decimal import *
from operator import attrgetter
from typing import Any


from attrs import define
from pdfreader import SimplePDFViewer

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


@define
class States:
    # what are we looking for next?
    possible_states: [str]
    current_state: int

    def __init__(self, states):
        self.possible_states = states
        self.current_state = 0

    def getCurrentState(self):
        return self.possible_states[self.current_state]

    def setCurrentState(self, newState: str):
        # index() "index raises ValueError when x is not found in s"
        # From: https://docs.python.org/3/library/stdtypes.html?highlight=list%20index
        self.current_state = self.possible_states.index(newState)


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
        super().__init__([DATE, REF, DESC, AMT, FINISHED])
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
                        xact_date < previous_balance_date:
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

            self.setCurrentState(FINISHED)

        elif self.getCurrentState() == FINISHED:
            pass

        return self.getCurrentState()


PREVIOUS_BALANCE_DATE: str = "Previous balance as of"
rePREVIOUS_BALANCE_DATE = re.compile("Previous balance as of (\d\d/\d\d/\d\d\d\d)")

START_OF_TRANSACTION_DETAILS: str = "Transaction details"
TYPE_OF_TRANSACTIONS: str = "TYPE_OF_TRANSACTIONS (this string does not occur in the file itself)"
END_OF_TRANSACTION_DETAILS: str = "(Continued on next page)"

START_OF_PAYMENTS: str = "Payments"
PAYMENTS: str = "Reading payment lines (this string does not occur in the file itself)"

START_OF_OTHER_CREDITS: str = "Other credits"
OTHER_CREDITS: str = "Reading Other credits lines (this string does not occur in the file itself)"

START_OF_PURCHASES: str = "Purchases and other debits"
PURCHASES: str = "Reading purchase lines (this string does not occur in the file itself)"

FINISHED: str = "Total fees charged this period"


class ProgramStates(States):
    def __init__(self):
        super().__init__([PREVIOUS_BALANCE_DATE, \
                          START_OF_TRANSACTION_DETAILS, \
                          TYPE_OF_TRANSACTIONS, \
                          # START_OF_PAYMENTS, \
                          PAYMENTS, \
                          # START_OF_OTHER_CREDITS, \
                          OTHER_CREDITS, \
                          # START_OF_PURCHASES, \
                          PURCHASES, \
                          END_OF_TRANSACTION_DETAILS, \
                          FINISHED])


NO_TRANSACTIONS_YET: str = "Haven't seen any transactions yet (this string does not occur in the file itself)"


class TransactionStates(States):
    def __init__(self):
        super().__init__([NO_TRANSACTIONS_YET, \
                          PAYMENTS, \
                          OTHER_CREDITS, \
                          PURCHASES])


previous_balance_date: date = None

def ConvertVenmoStatement(file_to_parse: str, output_file: str):
    global previous_balance_date
    previous_balance_date = None
    program_state = ProgramStates()
    current_xact_type = TransactionStates()
    line_reader = ReadingLineStates()
    continue_searching = True  # to break out of nested loops
    all_payments: [Transaction] = []
    all_other_credits: [Transaction] = []
    all_purchases: [Transaction] = []
    fd = open(file_to_parse, "rb")
    viewer = SimplePDFViewer(fd)
    for canvas in viewer:
        # page_text = canvas.text_content # text_content has lots of extra info & formatting, etc
        page_strings = canvas.strings  # this is a list of the actual text that we want to process

        for line in page_strings:
            # print("\t\tline: " + line)

            if program_state.getCurrentState() == PREVIOUS_BALANCE_DATE:
                match = re.search(rePREVIOUS_BALANCE_DATE, line)
                if match:
                    previous_balance_date = datetime.strptime(match.group(1), "%m/%d/%Y").date()
                    # print("previous_balance_date: " + str(previous_balance_date) + " <= This is the starting year =================")
                    program_state.setCurrentState(START_OF_TRANSACTION_DETAILS)

            elif program_state.getCurrentState() == START_OF_TRANSACTION_DETAILS:
                if START_OF_TRANSACTION_DETAILS in line:
                    # print("FOUND TRANSACTION DETAILS!!!!! ===================================================")

                    if current_xact_type.getCurrentState() == NO_TRANSACTIONS_YET:
                        program_state.setCurrentState(TYPE_OF_TRANSACTIONS)
                    else:  # otherwise keep looking for whatever sort of xact we've most recently seen:
                        program_state.setCurrentState(current_xact_type.getCurrentState())

            elif program_state.getCurrentState() == TYPE_OF_TRANSACTIONS:
                if START_OF_PAYMENTS in line:
                    # print("  PAYMENTS!!!!! ===================================================")
                    program_state.setCurrentState(PAYMENTS)
                    current_xact_type.setCurrentState(PAYMENTS)
                    line_reader = ReadingLineStates()

                elif START_OF_OTHER_CREDITS in line:
                    # print("FOUND OTHER CREDITS!!!!! ===================================================")
                    program_state.setCurrentState(OTHER_CREDITS)
                    current_xact_type.setCurrentState(OTHER_CREDITS)
                    line_reader = ReadingLineStates()

                elif START_OF_PURCHASES in line:
                    # print("FOUND START_OF_PURCHASES !!!!! ===================================================")
                    program_state.setCurrentState(PURCHASES)
                    current_xact_type.setCurrentState(PURCHASES)
                    line_reader = ReadingLineStates()

                elif END_OF_TRANSACTION_DETAILS in line:
                    program_state.setCurrentState(START_OF_TRANSACTION_DETAILS)
                    # print("END OF TRANSACTION DETAILS ==========================================================")
                    line_reader.reset()  # dump any partial info

            elif program_state.getCurrentState() == PAYMENTS:
                if START_OF_PURCHASES in line:
                    program_state.setCurrentState(PURCHASES)
                    current_xact_type.setCurrentState(PURCHASES)
                    # print("END OF PAYMENTS, START OF PURCHASES!!!! =========================================================")
                    line_reader = ReadingLineStates()

                elif START_OF_OTHER_CREDITS in line:
                    program_state.setCurrentState(OTHER_CREDITS)
                    current_xact_type.setCurrentState(OTHER_CREDITS)
                    # print( "END OF PAYMENTS, START OF OTHER_CREDITS!!!! =====================================================")
                    line_reader = ReadingLineStates()

                elif END_OF_TRANSACTION_DETAILS in line:
                    program_state.setCurrentState(START_OF_TRANSACTION_DETAILS)
                    # print("END OF TRANSACTION DETAILS ==========================================================")
                    line_reader.reset()  # dump any partial info

                elif line_reader.processLine(line) == FINISHED:
                    all_payments.append(line_reader.cur_xact)
                    line_reader.reset()

            elif program_state.getCurrentState() == OTHER_CREDITS:
                if START_OF_PURCHASES in line:
                    program_state.setCurrentState(PURCHASES)
                    current_xact_type.setCurrentState(PURCHASES)
                    # print( "END OF OTHER_CREDITS, START OF PURCHASES!!!! =========================================================")
                    line_reader = ReadingLineStates()

                elif END_OF_TRANSACTION_DETAILS in line:
                    program_state.setCurrentState(START_OF_TRANSACTION_DETAILS)
                    # print("END OF TRANSACTION DETAILS ==========================================================")
                    line_reader.reset()  # dump any partial info

                elif line_reader.processLine(line) == FINISHED:
                    all_other_credits.append(line_reader.cur_xact)
                    line_reader.reset()


            elif program_state.getCurrentState() == PURCHASES:
                # If we see the 'end of purchases' marker then go directly to the FINISHED state
                if FINISHED in line:
                    program_state.setCurrentState(FINISHED)
                    # print("END OF TRANSACTIONS!!!! ============================================================")
                elif line_reader.processLine(line) == FINISHED:
                    all_purchases.append(line_reader.cur_xact)
                    line_reader.reset()

            elif program_state.getCurrentState() == FINISHED:
                continue_searching = False
                break

            else:
                print("ERROR!! Unknown State!")
                exit(-1)

        if continue_searching is False:
            break
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
                 all_payments + all_other_credits] \
                + all_purchases
    all_xacts.sort(key=attrgetter('date'))

    with open(output_file, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(Transaction.get_csv_header())
        csv_writer.writerows(all_xacts)

    ### Print summary of transactions
    xact_adder = lambda x, y: Decimal(x + y.amount)

    # print_xacts(all_xacts, "ALL TRANSACTIONS")

    print("")

    # print_xacts(all_payments, "payments")
    total = reduce(xact_adder, all_payments, Decimal(0))
    print("Sum of payments: " + str(total))

    # print_xacts(all_other_credits, "other credits")
    total = reduce(xact_adder, all_other_credits, Decimal(0))
    print("Sum of other credits: " + str(total))

    # print_xacts(all_purchases, "purchases")
    total = reduce(xact_adder, all_purchases, Decimal(0))
    print("Sum of purchases: " + str(total))

    print("Wrote all transactions to\n\t" + output_file)
