import pickle
import typing as tp
import uuid

from satella.coding import update_key_if_true
from satella.coding.structures import HashableIntEnum
from satella.json import JSONAble
from satella.time import time_as_int


class Color(HashableIntEnum):
    """
    Event severity
    """
    WHITE = 0  #: least severe event
    YELLOW = 1  #: event of medium severity
    RED = 2  #: most severe event


class Event(JSONAble):
    """
    An object representing a single event in the SMOK system.

    :ivar uuid: event UUID (str)
    :ivar started_on: timestamp of event beginning, in seconds (int)
    :ivar ended_on: timestamp of event ending in seconds, or None if not ended (tp.Optional[int])
    :ivar color: event color (:class:`~smok.predicate.Color`)
    :ivar is_point: is the event a point one? (bool)
    :ivar token: token (str)
    :ivar group: event group (str)
    :ivar message: human-readable message (str)
    :ivar handled_by: user that handles this event (tp.Optional[str])
    :ivar metadata: event metadata (tp.Dict[str, str])
    """
    __slots__ = ('uuid', 'provisional_uuid', 'started_on', 'ended_on',
                 'color', 'is_point', 'token', 'group', 'message', 'handled_by',
                 'metadata')

    def to_pickle(self) -> bytes:
        """
        :return: pickled self
        """
        return pickle.dumps(self, pickle.HIGHEST_PROTOCOL)

    @classmethod
    def from_pickle(cls, y: bytes) -> 'Event':
        """
        Load an event from a pickle

        :param y: pickled Event
        :type y: bytes
        :return: unpickled Event
        :rtype: Event
        """
        return pickle.loads(y)

    def get_uuid(self) -> str:
        if self.uuid:
            return self.uuid
        else:
            return self.provisional_uuid

    def uuid_matches(self, uuid_: str) -> bool:
        return uuid_ == self.uuid or uuid_ == self.provisional_uuid

    def __eq__(self, other: 'Event') -> bool:
        return self.get_uuid() == other.get_uuid()

    def __hash__(self) -> int:
        return hash(self.get_uuid())

    def __init__(self, uuid_: tp.Optional[str], started_on: tp.Optional[int],
                 ended_on: tp.Optional[int],
                 color: Color, is_point: bool, token: str, group: str, message: str,
                 handled_by: tp.Optional[str], metadata: tp.Dict[str, str]):
        self.uuid = uuid_
        if self.uuid is None:
            self.provisional_uuid = uuid.uuid4().hex
        else:
            self.provisional_uuid = None
        self.started_on = started_on or time_as_int()
        self.ended_on = ended_on
        self.color = color
        self.is_point = is_point
        self.token = token
        self.group = group
        self.message = message
        self.handled_by = handled_by
        self.metadata = metadata

    def to_json(self) -> dict:
        """
        Convert self to JSON representation
        """
        dct = {
            'started_on': self.started_on,
            'color': self.color.value,
            'alarm_type': 1 if self.is_point else 0,
            'token': self.token,
            'group': self.group,
            'message': self.message,
            'metadata': self.metadata
        }
        update_key_if_true(dct, 'uuid', self.uuid)
        update_key_if_true(dct, 'handled_by', self.handled_by)
        update_key_if_true(dct, 'ended_on', self.ended_on)
        return dct

    def is_closed(self) -> bool:
        """
        :return: is given event closed?
        """
        if self.is_point:
            return True
        return self.ended_on is not None

    @classmethod
    def from_json(cls, dct: dict) -> 'Event':
        """
        Restore self from a JSON representation
        """
        return Event(dct.get('uuid'), dct['started_on'], dct.get('ended_on'),
                     Color(dct['color']), dct['alarm_type'] == 1, dct['token'],
                     dct['group'], dct['message'], dct['metadata'])
