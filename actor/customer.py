from abc import ABC


class Customer(ABC):
    pass

class Guest(Customer):
    pass

class Member(Customer):
    pass