"""Sample Python file for relation extractor tests — has calls, inheritance, imports."""

from os.path import join
from pathlib import Path


class BaseService:
    """Base class."""

    def connect(self):
        pass


class UserService(BaseService):
    """Extends BaseService."""

    def get_user(self, user_id: int) -> dict:
        result = self.connect()
        return {"id": user_id}

    def delete_user(self, user_id: int) -> None:
        print(user_id)


def helper_function(x: int) -> int:
    result = len(str(x))
    return result
