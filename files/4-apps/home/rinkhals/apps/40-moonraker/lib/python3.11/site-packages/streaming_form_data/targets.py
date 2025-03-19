import hashlib
from pathlib import Path
from typing import Callable, List, Optional, Union

import smart_open  # type: ignore


class BaseTarget:
    """
    Targets determine what to do with some input once the parser is done processing it.
    Any new Target should inherit from this base class and override the `data_received`
    method.

    Attributes:
        multipart_filename:
            the name of the file extracted from the `Content-Disposition` header.
            Please note that this value comes directly from the user input and is not
            sanitized.
        multipart_content_type:
            MIME Content-Type of the file, extracted from the `Content-Type` HTTP header
    """

    def __init__(self, validator: Optional[Callable] = None):
        self.multipart_filename: Optional[str] = None
        self.multipart_content_type: Optional[str] = None

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

    def set_multipart_filename(self, filename: str):
        self.multipart_filename = filename

    def set_multipart_content_type(self, content_type: str):
        self.multipart_content_type = content_type


class MultipleTargets(BaseTarget):
    """
    Target class that enables processing multiple inputs for one field
    """

    def __init__(self, next_target: Callable):
        """
        Args:
            next_target:
                A callable that returns a new target which should be used for the next
                input of the multiple inputs allowed for the specific field
        """

        self._next_target = next_target

        self.targets: List[BaseTarget] = []
        self._validator = None  # next_target should have a validator

        self._next_multipart_filename: Optional[str] = None
        self._next_multipart_content_type: Optional[str] = None

    def on_start(self):
        target = self._next_target()

        if self._next_multipart_filename is not None:
            target.set_multipart_filename(self._next_multipart_filename)
            self._next_multipart_filename = None
        if self._next_multipart_content_type is not None:
            target.set_multipart_filename(self._next_multipart_content_type)
            self._next_multipart_content_type = None

        self.targets.append(target)
        target.start()

    def on_data_received(self, chunk: bytes):
        self.targets[-1].data_received(chunk)

    def on_finish(self):
        self.targets[-1].finish()

    def set_multipart_filename(self, filename: str):
        self._next_multipart_filename = filename

    def set_multipart_content_type(self, content_type: str):
        self._next_multipart_content_type = content_type


class NullTarget(BaseTarget):
    """
    NullTarget ignores whatever input is passed in.

    This is mostly useful for internal use and should (normally) not be required by
    external users.
    """

    def on_data_received(self, chunk: bytes):
        pass


class ValueTarget(BaseTarget):
    """
    ValueTarget stores the input in an in-memory list of bytes.

    This is useful in case you'd like to have the value contained in an in-memory
    string.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._values = []

    def on_data_received(self, chunk: bytes):
        self._values.append(chunk)

    @property
    def value(self):
        return b"".join(self._values)


class ListTarget(BaseTarget):
    """
    ListTarget stores the input in an in-memory list of bytes, which is then joined
    into the final value and appended to an in-memory list of byte strings when each
    value is finished.

    This is useful for situations where more than one value may be submitted for the
    same argument.
    """

    def __init__(self, _type=bytes, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._temp_value = []
        self._values = []
        self._type = _type

    def on_data_received(self, chunk: bytes):
        self._temp_value.append(chunk)

    def on_finish(self):
        value = b"".join(self._temp_value)
        self._temp_value = []

        if self._type is str:
            value = value.decode("UTF-8")
        elif self._type is bytes:
            pass  # already is bytes, no need to do anything
        else:
            value = self._type(value)

        self._values.append(value)

    @property
    def value(self):
        return self._values

    @property
    def finished(self):
        return self._finished


class FileTarget(BaseTarget):
    """
    FileTarget writes (streams) the input to an on-disk file.
    """

    def __init__(
        self,
        filename: Union[str, Callable],
        allow_overwrite: bool = True,
        *args,
        **kwargs,
    ):
        """
        Args:
            filename:
                The name of the file to write to. This can also be a callable that
                accepts no arguments and returns a string.
            allow_overwrite:
                Whether or not an existing file should be overwritten
        """

        super().__init__(*args, **kwargs)

        self.filename = filename() if callable(filename) else filename

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
    """
    DirectoryTarget writes (streams) the different inputs to an on-disk directory.
    """

    def __init__(
        self,
        directory_path: Union[str, Callable],
        allow_overwrite: bool = True,
        *args,
        **kwargs,
    ):
        """
        Args:
            directory_path:
                The name of the directory to write to. This can also be a callable that
                accepts no arguments and returns a string.
            allow_overwrite:
                Whether or not an existing file should be overwritten
        """

        super().__init__(*args, **kwargs)

        self.directory_path = (
            directory_path() if callable(directory_path) else directory_path
        )

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
    """
    SHA256Target calculates the SHA256 hash of the given input.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._hash = hashlib.sha256()

    def on_data_received(self, chunk: bytes):
        self._hash.update(chunk)

    @property
    def value(self):
        return self._hash.hexdigest()


class SmartOpenTarget(BaseTarget):
    """
    SmartOpenTarget is an adapter for targets using the smart_open library.
    """

    def __init__(
        self,
        file_path: Union[str, Callable],
        mode: str,
        transport_params=None,
        **kwargs,
    ):
        """
        Args:
            file_path:
                The name of the file to write to. This can also be a callable that
                accepts no arguments and returns a string.
            mode:
                The mode in which the file should be opened
        """

        super().__init__(**kwargs)

        self._file_path = file_path() if callable(file_path) else file_path
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


class S3Target(SmartOpenTarget):
    """
    S3Target enables chunked uploads to S3 Buckets (using smart_open).
    """


class GCSTarget(SmartOpenTarget):
    """
    GCSTarget enables chunked uploads to Google Cloud Storage Buckets (using smart_open).
    """


class CSVTarget(BaseTarget):
    """
    CSVTarget enables the processing and release of CSV lines as soon as they are
    completed by a chunk.

    It enables developers to apply their own logic (e.g save to a database or send the
    entry to another API) to each line and free it from the memory in sequence, without
    the need to wait for the whole file and/or save the file locally.
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
