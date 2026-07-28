class OptimisticLockError(RuntimeError):
    pass


class DuplicateClientRequestError(RuntimeError):
    pass


class PlayerCharacterRepositoryError(RuntimeError):
    """A structured player-character database operation failed."""


class PlayerCharacterRepositoryConflictError(PlayerCharacterRepositoryError):
    """A known immutable or unique repository constraint won a race."""
