class ReceptionError(Exception):
    pass


class UnsupportedFileTypeError(ReceptionError):
    pass


class FileTooLargeError(ReceptionError):
    pass