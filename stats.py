def mean(vals):
    return sum(vals) / len(vals)

def median(vals):
    copy = sorted(vals)
    size = len(vals)
    if size % 2 == 1:
        return copy[(size - 1) / 2]
    else:
        return (copy[size/2 - 1] + copy[size/2]) / 2

def pow_diff(vals, power):
    m = mean(vals)
    return [(v - m) ** power for v in vals]

def variance(vals):
    return mean(pow_diff(vals, 2))

def std_dev(vals):
    return variance(vals) ** 0.5

def rel_std_dev(vals):
    return std_dev(vals) / mean(vals)

def skewness(vals):
    return (sum(pow_diff(vals, 3)) / 
            ((len(vals) - 1) * (std_dev(vals) ** 3)))

def kurtosis(vals):
    return (sum(pow_diff(vals, 4)) / 
            ((len(vals) - 1) * (std_dev(vals) ** 4)))

def num_stats(vals):
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
