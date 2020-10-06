import tables


def _get_description_for_event(
    int_names,
    float_names,
    str_names,
    int_size=32,
    float_size=32,
    str_size=20,
    timestamp=True,
):
    int_constructor = tables.Int64Col
    if int_size == 32:
        int_constructor = tables.Int32Col
    elif not int_size in (32, 64):
        raise "int_size must be left unspecified, or should equal 32 or 64"
    float_constructor = tables.Float32Col
    if float_size == 64:
        float_constructor = tables.Float64Col
    elif not float_size in (32, 64):
        raise "float_size must be left unspecified, or should equal 32 or 64"
    str_constructor = tables.StringCol
    description = {}
    pos = 0
    if timestamp:
        description["timestamp"] = tables.StringCol(itemsize=10, pos=pos)
        pos += 1
    for n in int_names:
        description[n] = int_constructor(pos=pos)
        pos += 1
    for n in float_names:
        description[n] = float_constructor(pos=pos)
        pos += 1
    for n in str_names:
        description[n] = str_constructor(itemsize=str_size, pos=pos)
        pos += 1
    return description
