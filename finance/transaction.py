from decimal import Decimal
from attrs import define
from datetime import date

@define
class Transaction:
    post_date: date = None
    xact_date: date = None
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
            if not each.startswith('__') and not each.startswith('post_date'):
                yield getattr(self, each, None)

    def __str__(self):
        return f'Transaction({self.amount},\t{self.reference_num},\t{self.description})'