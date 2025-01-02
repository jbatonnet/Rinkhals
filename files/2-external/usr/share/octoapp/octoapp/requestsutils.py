
class RequestsUtils:

    # Since most things use request Stream=True, this is a helpful util that will read the entire
    # content of a request and return it. Note if the request has no defined length, this will read
    # as long as the stream will go.
    @staticmethod
    def ReadAllContentFromStreamResponse(response):
        buffer = None
        # We can't simply use response.content, since streaming was enabled.
        # We need to use iter_content, since it will keep returning data until all is read.
        # We use a high chunk count, so most of the time it will read all of the content in one go.
        for chunk in response.iter_content(10000000):
            if buffer is None:
                buffer = chunk
            else:
                buffer += chunk
        return buffer
