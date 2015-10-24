import uuid

from coalib.misc.Decorators import (generate_repr,
                                    generate_ordering,
                                    enforce_signature)
from coalib.results.RESULT_SEVERITY import RESULT_SEVERITY
from coalib.results.SourceRange import SourceRange


@generate_repr("id",
               "origin",
               "affected_code",
               ("severity", RESULT_SEVERITY.reverse.get),
               "message")
@generate_ordering("affected_code",
                   "severity",
                   "origin",
                   "message",
                   "debug_msg",
                   "diffs")
class Result:
    """
    A result is anything that has an origin and a message.

    Optionally it might affect a file.
    """

    @enforce_signature
    def __init__(self,
                 origin,
                 message: str,
                 affected_code: tuple=(),
                 severity: int=RESULT_SEVERITY.NORMAL,
                 debug_msg="",
                 diffs: (dict, None)=None):
        """
        :param origin:        Class name or class of the creator of this object.
        :param message:       Message to show with this result.
        :param affected_code: A tuple of SourceRange objects pointing to related
                              positions in the source code.
        :param severity:      Severity of this result.
        :param debug_msg:     A message which may help the user find out why
                              this result was yielded.
        :param diffs:         A dictionary associating a Diff object with each
                              filename.
        """
        origin = origin or ""
        if not isinstance(origin, str):
            origin = origin.__class__.__name__

        self.origin = origin
        self.message = message
        self.debug_msg = debug_msg
        # Sorting is important for tuple comparison
        self.affected_code = tuple(sorted(affected_code))
        self.severity = severity
        self.diffs = diffs
        self.id = uuid.uuid4().int

    @classmethod
    @enforce_signature
    def from_values(cls,
                    origin,
                    message: str,
                    file: str,
                    line: (int, None)=None,
                    column: (int, None)=None,
                    end_line: (int, None)=None,
                    end_column: (int, None)=None,
                    severity: int=RESULT_SEVERITY.NORMAL,
                    debug_msg="",
                    diffs: (dict, None)=None):
        """
        Creates a result with only one SourceRange with the given start and end
        locations.

        :param origin:     Class name or class of the creator of this object.
        :param message:    A message to explain the result.
        :param file:       The related file.
        :param line:       The first related line in the file. (First line is 1)
        :param column:     The column indicating the first character. (First
                           character is 1)
        :param end_line:   The last related line in the file.
        :param end_column: The column indicating the last character.
        :param severity:   A RESULT_SEVERITY object.
        :param debug_msg:  Another message for debugging purposes.
        :param diffs:      A dictionary with filenames as key and Diff objects
                           associated with them.
        """
        range = SourceRange.from_values(file,
                                        line,
                                        column,
                                        end_line,
                                        end_column)

        return cls(origin=origin,
                   message=message,
                   affected_code=(range,),
                   severity=severity,
                   debug_msg=debug_msg,
                   diffs=diffs)

    def to_string_dict(self):
        """
        Makes a dictionary which has all keys and values as strings and
        contains all the data that the base Result has.

        FIXME: diffs are not serialized ATM.

        :return: Dictionary with keys and values as string.
        """
        retval = {}

        members = ["id",
                   "debug_msg",
                   "message",
                   "origin"]

        for member in members:
            value = getattr(self, member)
            retval[member] = "" if value == None else str(value)

        retval["severity"] = str(RESULT_SEVERITY.reverse.get(self.severity, ""))
        # FIXME: This is merely a workaround for DBus because changing it's
        # interface is more complicated. Takes only first range here.
        if len(self.affected_code) > 0:
            retval["file"] = self.affected_code[0].file
            line = self.affected_code[0].start.line
            retval["line_nr"] = "" if line is None else str(line)
        else:
            retval["file"], retval["line_nr"] = "", ""

        return retval

    @enforce_signature
    def apply(self, file_dict: dict):
        """
        Applies all contained diffs to the given file_dict. This operation will
        be done in-place.

        :param file_dict: A dictionary containing all files with filename as
                          key and all lines a value. Will be modified.
        """
        for filename in self.diffs:
            file_dict[filename] = self.diffs[filename].apply(
                file_dict[filename])

    def __add__(self, other):
        """
        Joins those patches to one patch.

        :param other: The other patch.
        """
        assert isinstance(self.diffs, dict)
        assert isinstance(other.diffs, dict)

        for filename in other.diffs:
            if filename in self.diffs:
                self.diffs[filename] += other.diffs[filename]
            else:
                self.diffs[filename] = other.diffs[filename]

        return self
