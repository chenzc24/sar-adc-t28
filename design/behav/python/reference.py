"""Two reference captures and break-before-make gate levels, LSB first."""


class ReferenceControl:
    precharge_word=128

    def __init__(self, timing, deadtime_s=100e-12):
        if deadtime_s<0:raise ValueError('Nonnegative nonoverlap required')
        self.timing,self.deadtime_s=timing,deadtime_s

    def captures(self, update_s):
        first=update_s+self.timing['update_to_capture_s']
        return first,first+self.timing['capture_gap_s']

    def next_compare(self, second_capture_s):
        return second_capture_s+self.timing['capture_to_next_compare_s']

    def gates(self, old_word, new_word, elapsed_s):
        if any(not isinstance(x,int) or not 0<=x<=255 for x in (old_word,new_word)):
            raise ValueError('Unsigned eight-bit reference words required')
        rows=[]
        for bit in range(8):
            q=(new_word>>bit)&1
            blank=((old_word^new_word)>>bit)&1 and elapsed_s<self.deadtime_s
            rows.append((0,1,0,1) if blank else (1-q,1-q,q,q))
        return tuple(rows)
