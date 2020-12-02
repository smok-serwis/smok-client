import typing as tp


def parse(invocation: str) -> tp.Tuple[str, tp.List[str]]:  # Parse Reparse-Point-type invocation
    """
    Parses reparse point variable code

    Invocation is ex. {abc}+12+{def}, where abc and def are paths.
    Their values would get substituted in place of those {}'s.
    Of course in resulting Python expressions you will have to make
    your dictionaries by dict() constructor, then.

    :param invocation: part of the path without 'r' and without it's type
    :return: tuple. First element is a Python expression. Aforementioned
        example would be parsed to v0+12+v1.
        Second element is a list of pathes of mentioned variables
    :raise ValueError: the path given was invalid
    """
    if not invocation:
        raise ValueError('Path is empty')

    paths = []
    expression = ''

    state = False  # Whether we are scanning a variable instead of a literal

    nesting = 0  # so that stuff like {a{1{2{3}}}} will be parsed
    # as 'a{1{2{3}}}' and not 'a{1{2{3'
    c_var = ''

    for c in invocation:
        if not state:  # scanning literal mode
            if c == '{':
                state = True
                nesting = 1
            else:
                expression += c
        else:  # scanning variable mode
            if c == '}':
                nesting -= 1
                if not nesting:
                    paths.append(c_var)
                    expression += 'v' + str(int(len(paths) - 1))
                    state = False
                    c_var = ''
                    continue
            elif c == '{':
                nesting += 1

            c_var += c

    if nesting:
        raise ValueError('No matching } found')

    return expression, paths


def reparse_to_native_components(path: str) -> tp.List[str]:
    """
    Analyze a reparse pathpoint and break it down to it's native components.
    Ie. if a reparse pathpoint consist of reparse pathpoints, it will be broken down
    as deep as possible.
    """
    if path[0] != 'r':
        return [path]
    paths = parse(path)[1]
    output = []
    for sub_path in paths:
        output.extend(reparse_to_native_components(sub_path))
    return output
