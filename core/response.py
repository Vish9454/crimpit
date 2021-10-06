from rest_framework.response import Response


class SuccessResponse(Response):
    """
        SuccessResponse class used to handle the success response.
    """
    def __init__(self, data=None, status=200):
        """
            override the default constructor
        :param data:
        :param status:
        """
        result = {"data": data}
        super().__init__(result, status)
