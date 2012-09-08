def mean(vals):
    if vals:
        return sum(vals, 0.0) / len(vals)
    else:
        return 0.0


def median(vals):
    if not vals:
        return 0
    copy = sorted(vals)
    size = len(vals)
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
    return {
        'mean':     mean(vals),
        'median':   median(vals),
        'variance': variance(vals),
        'std_dev':  std_dev(vals),
        'rel_std_dev':  rel_std_dev(vals),
        'skewness': skewness(vals),
        'kurtosis': kurtosis(vals),
        'size': len(vals)
    }
