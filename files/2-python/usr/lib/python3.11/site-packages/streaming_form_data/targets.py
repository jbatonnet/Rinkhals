import hashlib
from pathlib import Path
import smart_open  # type: ignore
from typing import Callable, List, Optional


class BaseTarget:
    """
    Targets determine what to do with some input once the parser is done
    processing it. Any new Target should inherit from this base class and
    override the :code:`data_received` function.

    Attributes:
        multipart_filename: the name of the file advertised by the user,
            extracted from the :code:`Content-Disposition` header. Please note
            that this value comes directly from the user input and is not
            sanitized, so be careful in using it directly.
        multipart_content_type: MIME Content-Type of the file, extracted from
            the :code:`Content-Type` HTTP header
    """

    def __init__(self, validator: Optional[Callable] = None):
        self.multipart_filename = None
        self.multipart_content_type = None

        self._started = False
        self._finished = False
        self._validator = validator

    def _validate(self, chunk: bytes):
        if self._validator:
            self._validator(chunk)

    def start(self):
        self._started = True
        self.on_start()

    def on_start(self):
        pass

    def data_received(self, chunk: bytes):
        self._validate(chunk)
        self.on_data_received(chunk)

    def on_data_received(self, chunk: bytes):
        raise NotImplementedError()

    def finish(self):
        self.on_finish()
        self._finished = True

    def on_finish(self):
        pass


class NullTarget(BaseTarget):
    """NullTarget ignores whatever input is passed in.

    This is mostly useful for internal use and should (normally) not be
    required by external users.
    """

    def on_data_received(self, chunk: bytes):
        pass


class ValueTarget(BaseTarget):
    """ValueTarget stores the input in an in-memory list of bytes.

    This is useful in case you'd like to have the value contained in an
    in-memory string.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._values = []

    def on_data_received(self, chunk: bytes):
        self._values.append(chunk)

    @property
    def value(self):
        return b"".join(self._values)


class FileTarget(BaseTarget):
    """FileTarget writes (streams) the input to an on-disk file."""

    def __init__(self, filename: str, allow_overwrite: bool = True, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.filename = filename

        self._mode = "wb" if allow_overwrite else "xb"
        self._fd = None

    def on_start(self):
        self._fd = open(self.filename, self._mode)

    def on_data_received(self, chunk: bytes):
        if self._fd:
            self._fd.write(chunk)

    def on_finish(self):
        if self._fd:
            self._fd.close()


class DirectoryTarget(BaseTarget):
    """DirectoryTarget writes (streams) the different inputs to an on-disk
    directory."""

    def __init__(
        self, directory_path: str, allow_overwrite: bool = True, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.directory_path = directory_path

        self._mode = "wb" if allow_overwrite else "xb"
        self._fd = None
        self.multipart_filenames: List[str] = []
        self.multipart_content_types: List[str] = []

    def on_start(self):
        # Properly handle the case where user does not upload a file
        if not self.multipart_filename:
            return

        # Path().resolve().name only keeps file name to prevent path traversal
        self.multipart_filename = Path(self.multipart_filename).resolve().name
        self._fd = open(Path(self.directory_path) / self.multipart_filename, self._mode)

    def on_data_received(self, chunk: bytes):
        if self._fd:
            self._fd.write(chunk)

    def on_finish(self):
        self.multipart_filenames.append(self.multipart_filename)
        self.multipart_content_types.append(self.multipart_content_type)
        if self._fd:
            self._fd.close()


class SHA256Target(BaseTarget):
    """SHA256Target calculates the SHA256 hash of the given input."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._hash = hashlib.sha256()

    def on_data_received(self, chunk: bytes):
        self._hash.update(chunk)

    @property
    def value(self):
        return self._hash.hexdigest()


class S3Target(BaseTarget):
    """
    S3Target enables chunked uploads to S3 buckets (using smart_open)"""

    def __init__(self, file_path, mode, transport_params=None, **kwargs):
        super().__init__(**kwargs)

        self._file_path = file_path
        self._mode = mode
        self._transport_params = transport_params
        self._fd = None

    def on_start(self):
        self._fd = smart_open.open(
            self._file_path,
            self._mode,
            transport_params=self._transport_params,
        )

    def on_data_received(self, chunk: bytes):
        if self._fd:
            self._fd.write(chunk)

    def on_finish(self):
        if self._fd:
            self._fd.close()


class CSVTarget(BaseTarget):
    """
    CSVTarget enables the processing and release of CSV lines as soon as they are
    completed by a chunk.
    It enables developers to apply their own logic (e.g save to a db or send the entry
    to another API) to each line and free it from the memory in sequence, without the
    need to wait for the whole file and/or save the file locally.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lines = []
        self._previous_partial_line = ""

    def on_data_received(self, chunk: bytes):
        # join the previous partial line with the new chunk
        combined = self._previous_partial_line + chunk.decode("utf-8")

        # split the combined string into lines
        lines = combined.splitlines(keepends=True)

        # process all lines except the last one (which may be partial)
        for line in lines[:-1]:
            self._lines.append(line.replace("\n", ""))

        # if the last line ends with a newline, it is complete
        if lines[-1].endswith("\n"):
            self._lines.append(lines[-1].replace("\n", ""))
            self._previous_partial_line = ""
        else:
            # otherwise, it is partial, and we save it for later
            self._previous_partial_line = lines[-1]

    def pop_lines(self, include_partial_line: bool = False):
        # this clears the lines to keep memory usage low
        lines = self._lines
        if include_partial_line and self._previous_partial_line:
            lines.append(self._previous_partial_line)
            self._previous_partial_line = ""
        self._lines = []
        return lines

    def get_lines(self, include_partial_line: bool = False):
        # this never clears the lines
        lines = self._lines.copy()
        if include_partial_line and self._previous_partial_line:
            lines.append(self._previous_partial_line)
        return lines
