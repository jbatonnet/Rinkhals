class ValidationError(Exception):
    pass


class MaxSizeValidator:
    def __init__(self, max_size: int):
        self.so_far = 0
        self.max_size = max_size

    def __call__(self, chunk: bytes):
        self.so_far += len(chunk)

        if self.so_far > self.max_size:
            raise ValidationError(
                "Size must not be greater than {}".format(self.max_size)
            )
