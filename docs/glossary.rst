Glossary
========

.. glossary::

    Native
      A native pathpoint is a readable endpoint. It tells it's own value, it's value does not
      depend on other pathpoint

    Reparse
      A reparse pathpoint starts with a `r`, then goes it's type, and the remaining is an expression
      with other pathpoints taken in braces `{}`.
      The value of the reparse pathpoint is the result of the expression.
      Writing a reparse pathpoint is a no-op.
      You don't need to care about implementing and providing these, smok-client will demand
      you to provide only :term:`native` pathpoints.

    Statistic
      A base class for predicate. Generally the logic, that given some configuration watches
      over an aspect of the system, and reports events when something goes wrong (or just if
      a condition is reached).

    Predicate
      An instance of a statistic, identified by it's predicate ID.

    Slave device
      A slave device is a device that works under it's :term:`master controller`. Meaning
      it writes pathpoint values with the device ID of it's master controller.

    Master controller
      A single device, that is seen by the user as whole.
      Composed at least of a single :term:`slave`

    Point event
      A event that occurs at a point in time. It does not span a period, and it's created
      in state closed.

    Color
      A severity of an event. Red is highest, yellow is medium and white is the least severe.

    Pathpoint
      Essentially a named, typed variable. It's first letter of the name (path) identifies it's
      type. This should correspond 1:1 to measure points, eg. temperature sensors and so on.

    Sensor
      Information processed from pathpoints to be displayed to the user. Server manages these. It
      consists of one (or more) pathpoints, has a type and a tag name.

    Tag name
      Set of words separated by space identifying given sensor. Note that a set has no meaning of
      order, so "ud test" is the same as "test ud"

    FQTS
      Fully-Qualified Tag System, or a canonical representation of a tag name, is the tag name
      split by space, entries sorted and joined with a " ".

    Advise level
      A QoS of a read/write order as presented to the system. Advise means best-effort, while force
      will pack much more, and it is allowed to non-executable-right-now writes to block the order
      queue. There are two advise levels:

        * `AdviseLevel.ADVISE` - best effort
        * `AdviseLevel.FORCE` - carry out this order for sure

      For example, calendar-issued writes have the `FORCE` advise level.
