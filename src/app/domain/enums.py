from enum import StrEnum

class Role(StrEnum):
    CLIENT = "CLIENT"
    ADMIN = "ADMIN"

class TxType(StrEnum):
    DEPOSIT = "DEPOSIT"
    PREDICTION_CHARGE = "PREDICTION_CHARGE"

class JobStatus(StrEnum):
    OK = "OK"
    ERROR = "ERROR"