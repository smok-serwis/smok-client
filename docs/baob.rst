BAOB
====

BAOBs, or Binary All-sized OBjects, are the preferred way of sharing files between
SMOK server and SMOK devices. They are monotonically versioned, with each update to the file
adding a 1 to version.

Upon reconnection, a synchronization with the server proceeds, with the usual last-write-wins rule.

.. autoclass:: smok.baob.BAOB
    :members:
