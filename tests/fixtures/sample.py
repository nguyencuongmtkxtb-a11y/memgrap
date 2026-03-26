"""Sample Python file for AST parser tests."""



class UserService:
    """Sample class."""

    def get_user(self, user_id: int) -> dict:
        return {"id": user_id}

    def delete_user(self, user_id: int) -> None:
        pass


def helper_function(x: int) -> int:
    return x + 1
