import typing as tp
from abc import ABCMeta, abstractmethod

from satella.coding.typing import Number

from smok.pathpoint.typing import ValueOrExcept, PathpointValueType


class BaseDataToSynchronize(metaclass=ABCMeta):
    __slots__ = ()

    @abstractmethod
    def acknowledge(self) -> None:
        """
        Mark the data as successfully synchronized
        """

    @abstractmethod
    def negative_acknowledge(self) -> None:
        """
        Mark the data as failed to synchronize
        """

    @abstractmethod
    def to_json(self) -> tp.List:
        """
        Return a JSON structure that looks like this
        (specification expressed in OpenAPI 3.0 format)

        ::

            type: array
            items:
                type: object
                properties:
                    path:
                        type: string
                        description: Name of the pathpoint to serve
                    values:
                        type: array
                        items:
                            type: object
                            description: This has either error_code or value
                            properties:
                                timestamp:
                                    type: integer
                                    format: int64
                                    description: Timestamp in milliseconds
                                error_code:
                                    type: string
                                    description: Reason of error code
                                    enum:
                                        - malformed
                                        - timeout
                                        - invalid
                                value:
                                    type:
                                        oneOf:
                                            - integer
                                            - string
                                            - number
                                    description: Value of the pathpoint
                            required:
                                - timestamp
       """


class BasePathpointDatabase(metaclass=ABCMeta):
    """
    An abstract base class for pathpoint archives database.

    Try to make it reasonably thread-safe. It is documented which call is called by which thread.
    """
    __slots__ = ()

    @abstractmethod
    def checkpoint(self) -> None:
        """
        Called by the communicator thread, once every about 60 seconds.
        May be called much more often, it's the function responsibility to throttle.
        """

    @abstractmethod
    def on_new_data(self, pathpoint: str, timestamp: Number,
                    value_or_exception: ValueOrExcept) -> None:
        """
        Called whenever there's a new value.

        Called by order executor thread and user-threads if you make use of
        method :meth:`~smokclient.pathpoint.Pathpoint.set_new_value`.

        :param pathpoint: :term:`Native` pathpoint that has been written
        :param timestamp: timestamp of the operation in milliseconds
        :param value_or_exception: a value of the pathpoint or an OperationFailedError instance
        """

    @abstractmethod
    def get_current_value(self, pathpoint: str) -> tp.Tuple[Number, PathpointValueType]:
        """
        Get the current value for given pathpoint.

        Called by user threads.

        :param pathpoint: name of the pathpoint
        :return: a tuple of timestamp, value
        :raises OperationFailedError: read of this pathpoint has failed
        :raises NotReadedError: pathpoint has no last value (or does not exist)
        """

    @abstractmethod
    def get_archive_data(self, pathpoint: str, start: tp.Optional[Number],
                         stop: tp.Optional[Number]) -> tp.Iterator[tp.Tuple[Number, ValueOrExcept]]:
        """
        Return some archival data for this pathpoint

        Called by user threads.

        :param pathpoint: name of the pathpoint
        :param start: start of the period, in milliseconds since Epoch,
            or the earliest timestamp that is registered if None
        :param stop: stop of the period, in milliseconds since Epoch,
            or the latest timestamp that is registered if None
        :return: an iterator of two-tuple (timestamp in milliseconds, value or
            OperationReadError instance)
        """

    @abstractmethod
    def get_data_to_sync(self) -> tp.Optional[BaseDataToSynchronize]:
        """
        At most one instance of BaseDataToSynchronize is guaranteed to exist at given time.

        Called by communicator thread.

        :return: return data to synchronize, or None if nothing is to synchronize
        """
