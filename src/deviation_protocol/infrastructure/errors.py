from deviation_protocol.application.ports import (
    ControllerBindingUniquenessConflictError,
)


class OptimisticLockError(RuntimeError):
    pass


class DuplicateClientRequestError(RuntimeError):
    pass


class PlayerCharacterRepositoryError(RuntimeError):
    """A structured player-character database operation failed."""


class PlayerCharacterRepositoryConflictError(PlayerCharacterRepositoryError):
    """A known immutable or unique repository constraint won a race."""


class PlayerCharacterControllerBindingConflictError(
    PlayerCharacterRepositoryConflictError,
    ControllerBindingUniquenessConflictError,
):
    """A duplicate at the exact controller-binding add flush."""
