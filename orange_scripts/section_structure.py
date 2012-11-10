import math
def get_structure_coefficient(i, r=None, do_print=False):
    headers = range(2,6)
    total_word_count = i['d_word_count']+0.0
    acc = 0.0
    weighted_acc = 0.0
    test = 0
    for h in headers:
        count_attr = 'd_h%s_text_count' % h
        mean_attr = 'd_h%s_text_mean' % h    
        try:
            cur_count = i[count_attr]
            cur_mean = i[mean_attr]
            test += (cur_count * cur_mean)
            acc += (cur_mean * cur_count)
            weighted_acc += (h * cur_mean * cur_count)
        except TypeError:
            continue
    if do_print:
        print 'guess total:', test, 'real:', total_word_count
        print weighted_acc, acc
    #return math.exp((weighted_acc / acc) - min(headers))
    return (weighted_acc / acc) - min(headers)
