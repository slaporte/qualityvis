def mean(vals):
    if vals:
        return sum(vals, 0.0) / len(vals)
    else:
        return 0.0

def trim(vals, trim=0.25):
    if trim > 0.0:
        trim = float(trim)
        size = len(vals)
        size_diff = int(size * trim)
        vals = vals[size_diff:-size_diff]
    return vals

def median(vals):
    if not vals:
        return 0
    copy = sorted(vals)
    size = len(copy)
    if size % 2 == 1:
        return copy[(size - 1) / 2]
    else:
        return (copy[size / 2 - 1] + copy[size / 2]) / 2.0


def pow_diff(vals, power):
    m = mean(vals)
    return [(v - m) ** power for v in vals]


def variance(vals):
    return mean(pow_diff(vals, 2))


def std_dev(vals):
    return variance(vals) ** 0.5


def absolute_dev(vals, x):
    return [abs(x - v) for v in vals]


def median_abs_dev(vals):
    x = median(vals)
    return median(absolute_dev(vals, x))


def rel_std_dev(vals):
    val_mean = mean(vals)
    if val_mean:
        return std_dev(vals) / val_mean
    else:
        return 0.0


def skewness(vals):
    s_dev = std_dev(vals)
    if len(vals) > 1 and s_dev > 0:
        return (sum(pow_diff(vals, 3)) /
                float((len(vals) - 1) * (s_dev ** 3)))
    else:
        return 0.0


def kurtosis(vals):
    s_dev = std_dev(vals)
    if len(vals) > 1 and s_dev > 0:
        return (sum(pow_diff(vals, 4)) /
                float((len(vals) - 1) * (s_dev ** 4)))
    else:
        return 0.0


def dist_stats(vals):
    trimmed_vals = trim(vals)
    return {
        'mean':     mean(vals),
        'mean_trimmed': mean(trimmed_vals),
        'median':   median(vals),
        'median_abs_dev': median_abs_dev(vals),
        'variance': variance(vals),
        'std_dev':  std_dev(vals),
        'std_dev_trimmed': std_dev(trimmed_vals),
        'rel_std_dev':  rel_std_dev(vals),
        'skewness': skewness(vals),
        'skewness_trimmed': skewness(trimmed_vals),
        'kurtosis': kurtosis(vals),
        'kurtosis_trimmed': kurtosis(trimmed_vals),
        'count': len(vals) # used to be called size; sample/population size
    }
