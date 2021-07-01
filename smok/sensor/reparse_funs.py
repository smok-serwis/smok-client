"""
This exports a function to evaluate Python expression that use eval() within SAI5.
"""
import struct
import typing as tp


# fun stuff
def D(real, ref):
    return abs(ref - real)


def d(real, ref):
    return abs(D(real, ref) / real)


def ked(real, ref):
    """
    Return relative error between referential value (real) and measured value (ref)
    real and ref are respective
    returns zero if referential value is below 20
    """
    if real < 20:
        return 0
    return d(real, ref)


def huba505(voltage):
    """
    Given that v is voltage in Volts, return pressure as given by a HUBA 505 transducer

    The transducer is:
    0.5V    -   0 bar
    3.5V    -   4 bar
    """
    pressure = 4 * (voltage - 0.5) / 3
    if pressure > 0:
        return pressure
    else:
        return 0


KTY81 = [
    (-40, 1136),
    (-20, 1250),
    (-10, 1372),
    (0, 1500),
    (10, 1634),
    (20, 1774),
    (25, 1922),
    (30, 2000),
    (40, 2078),
    (50, 2240),
    (60, 2410),
    (70, 2590),
    (80, 2780),
    (90, 2978),
    (100, 3182),
    (110, 3392),
]


def kty81(r):
    """Given that r is resistance in Ohms, convert it to KTY81 centigrades.
    Return bounding value if out of range"""
    if r <= 1136:
        return -40
    if r >= 3276:
        return 94.4

    p_temp, p_resistance = KTY81[0]

    for r_temp, r_resistance in KTY81[1:]:
        if p_resistance < r < r_resistance:
            return (r_temp - p_temp) * (r - p_resistance) / (r_resistance - p_resistance) + p_temp

        p_temp, p_resistance = r_temp, r_resistance


PT100 = [80.31, 82.29, 84.27, 86.25, 88.22, 90.19, 92.16, 94.12, 96.09, 98.04,
         100.0, 101.95, 103.9, 105.85, 107.79, 109.73, 111.67, 113.61, 115.54, 117.47,
         119.4, 121.32, 123.24, 125.16, 127.07, 128.98, 130.89, 132.8, 134.7, 136.6,
         138.5, 140.39, 142.29, 157.31, 175.84, 195.84]


def pt1000(r):
    """Given that r is resistance in Ohms, convert it to PT1000 centigrades"""
    r /= 10.0

    t = -50
    i = 0
    if r > PT100[0]:
        while 250 > t:
            dt = 5 if t < 110 else (50 if t > 110 else 40)
            i += 1
            if r < PT100[i]:
                return t + (r - PT100[i - 1]) * dt / (PT100[i] - PT100[i - 1])
            t += dt
    return t


STRUCT_F = struct.Struct('f')
STRUCT_HH = struct.Struct('>HH')
STRUCT_l = struct.Struct('>l')


def _pack_hh(ho, lo) -> bytes:
    return STRUCT_HH.pack(ho, lo)


def mkflt(ho, lo):
    return STRUCT_F.unpack(_pack_hh(ho, lo))[0]


def mkint32(ho, lo):
    return STRUCT_l.unpack(_pack_hh(ho, lo))[0]


def ecre_eval(expression: str, my_locals=None, args: tp.Union[tp.Any, tp.Tuple[tp.Any]] = ()):
    """
    Our limited form of secure Python evaluation.

    Note that this is not really secure against malicious code. See
    https://nedbatchelder.com/blog/201206/eval_really_is_dangerous.html for details.

    Always trust the code you execute!

    :param expression: expression to evaluate
    :param my_locals: locals to use. Additionally, locals from the ecre_eval runtime environment
        will be added
    :param args: args to use. They will be available in the expression as v0, v1, v2..
        If a single non-sequence value is passed, it will be available as v0.
    :return: evaluated value
    """

    my_locals = my_locals or {}
    if not isinstance(args, tp.Iterable):
        my_locals['v0'] = args
    else:
        for index, value in enumerate(args):
            my_locals['v%s' % (index, )] = value

    my_locals.update({'d': d, 'D': D, 'ked': ked, 'pt1000': pt1000, 'huba505': huba505,
                      'negz': lambda x: 0 if x < 0 else x,
                      'mkflt': mkflt,
                      'str': str,
                      'kty81': kty81,
                      'mkint32': mkint32})
    return eval(expression, {}, my_locals)
