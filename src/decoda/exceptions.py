# Copyright Andrew Dodd
from numbers import Number


class UnknownReferenceError(Exception):
    pass


class CouldBeAnyLength(Exception):
    pass


class UnsupportedLocationSpec(ValueError):
    pass


class MissingBitLength(ValueError):
    pass


class ScalarRangeError(ValueError):
    def __init__(self, message: str, error_code: Number = None):
        super().__init__(message)
        self.error_code = error_code

    def value(self):
        return str(self)

    def display_value(self):
        if self.error_code is None:
            return self.value()
        return f"{self.value()} ({self.error_code})"


class NotAvaiableRangeError(ScalarRangeError):
    def __init__(self, error_code: Number):
        super().__init__("Not available", error_code)


class ErrorIndicatorRangeError(ScalarRangeError):
    def __init__(self, error_code: Number):
        super().__init__("Error indicator", error_code)


class ParameterSpecificIndicatorError(ScalarRangeError):
    def __init__(self, error_code: Number):
        super().__init__("Parameter specific indicator", error_code)
