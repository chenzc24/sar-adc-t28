"""Effective bit weights and explicitly timed one-pole trial approximation."""
import math


class Cdac:
    def __init__(self, spec, analog):
        self.spec,self.analog=spec,analog
        self.reset(0.0)

    def threshold(self, word):
        if not isinstance(word,int) or not 0<=word<=255:raise ValueError('Unsigned eight-bit word required')
        return -self.spec.vref+self.spec.lsb*sum((1<<b)*(1+self.analog.weight_errors[b]) for b in range(8) if word&(1<<b))

    def reset(self, seq_close_s):
        self.voltage=self.previous_target=0.0
        self.mark=self.last_eval=seq_close_s

    def evaluate(self, trial, now_s):
        target=self.threshold(trial);tau=self.analog.dac_tau_s
        if tau:
            self.voltage=self.previous_target+(self.voltage-self.previous_target)*math.exp(-max(0,self.mark-self.last_eval)/tau)
            self.voltage=target+(self.voltage-target)*math.exp(-max(0,now_s-self.mark)/tau)
        else:self.voltage=target
        return self.voltage

    def commit(self, trial, compared_s, updated_s):
        self.previous_target=self.threshold(trial)
        self.last_eval,self.mark=compared_s,updated_s
