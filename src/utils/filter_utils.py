import numpy as np
import numba

@numba.jit(nopython=True)
def fast_filter_rows(data, condition_keys, condition_values):
    result = []
    for row in data:
        match = True
        for i in range(len(condition_keys)):
            if row[condition_keys[i]] != condition_values[i]:
                match = False
                break
        if match:
            result.append(row)
    return result

def filter_rows(chunk, conditions):
    if not chunk:
        return []
    condition_keys = list(conditions.keys())
    condition_values = list(conditions.values())
    try:
        dtype = [(key, type(value)) for key, value in chunk[0].items()]
        np_data = np.array([tuple(row.values()) for row in chunk], dtype=dtype)
        return fast_filter_rows(np_data, condition_keys, condition_values)
    except Exception:
        return [row for row in chunk if all(row.get(k) == v for k, v in conditions.items())]