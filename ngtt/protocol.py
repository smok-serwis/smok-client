import minijson

import struct
import typing as tp

from satella.coding.structures import HashableIntEnum, ReprableMixin

from .exceptions import InvalidFrame


class NGTTHeaderType(HashableIntEnum):
    PING = 0  #: a PING, sent by the client, server responds alike
    ORDER = 1  #: sent by the server
    ORDER_CONFIRM = 2  #: sent by the client
    LOGS = 3  #: sent by the client
    DATA_STREAM = 4  #: sent by the client
    DATA_STREAM_CONFIRM = 5  #: sent by the server
    DATA_STREAM_REJECT = 6  #: sent by the server
    ORDER_REJECT = 9  #: sent by the client, currently unused (by the client)
    FETCH_ORDERS = 10  #: a request by the client to fetch orders


STRUCT_LHH = struct.Struct('>LHH')


class NGTTFrame(ReprableMixin):
    """
    A basic NGTT protocol frame. It's big endian. It starts with a header of:

    uint32 data_size
    uint16 order_id
    uint16 packet_type
    bytes[data_size] data

    Data is represented using minijson.

    :param tid: order ID
    :param packet_type: type of the packet
    :param data: data. Any class that has a __bytes__ property will do.
    """
    _REPR_FIELDS = 'tid', 'packet_type', 'data'

    def __init__(self, tid: int, packet_type: NGTTHeaderType, data=b''):
        self.tid = tid
        self.packet_type = packet_type
        self.data = bytes(data)

    def __str__(self) -> str:
        return repr(self)

    @property
    def real_data(self) -> tp.Union[dict, list]:
        """
        Unserialize the data

        :return: JSON unserialized data
        :raises ValueError: invalid MiniJSON
        """
        return minijson.loads(self.data)

    def __len__(self):
        return STRUCT_LHH.size + len(self.data)

    def __bytes__(self):
        return STRUCT_LHH.pack(len(self.data), self.tid, self.packet_type.value) + self.data

    @classmethod
    def from_bytes(cls, b: tp.Union[bytes, bytearray]) -> 'NGTTFrame':
        length, tid, h_type = STRUCT_LHH.unpack(b[:STRUCT_LHH.size])
        if h_type > NGTTHeaderType.DATA_STREAM_REJECT.value:
            raise InvalidFrame('Unrecognized packet type %s' % (h_type,))
        return NGTTFrame(tid, NGTTHeaderType(h_type), b[STRUCT_LHH.size:STRUCT_LHH.size + length])

    @classmethod
    def from_buffer(cls, buffer: bytearray) -> tp.Optional[tp.Tuple[int, 'NGTTFrame']]:
        """
        Try to construct a frame from a buffer.

        If successful, a tuple will be output of amount of bytes consumed and an instance of
        :class:`~ngtt.protocol.NGTTFrame`.
        If failure, None will be returned
        """
        if len(buffer) < STRUCT_LHH.size:
            return None
        length, tid, h_type = STRUCT_LHH.unpack(buffer[:STRUCT_LHH.size])
        if not length:
            return STRUCT_LHH.size, NGTTFrame(tid, NGTTHeaderType(h_type))
        if len(buffer) < length + STRUCT_LHH.size:
            return None
        return length + STRUCT_LHH.size, NGTTFrame(tid, NGTTHeaderType(h_type),
                                                   buffer[STRUCT_LHH.size:STRUCT_LHH.size + length])


def env_to_hostname(env: int) -> str:
    return {0: 'api.smok.co',
            1: 'api.test.smok-serwis.pl'}.get(env, 'rapid-rs')
