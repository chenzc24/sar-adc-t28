"""Generate a separate full-history observer without touching frozen analyzers."""
import prepare_first_event as base

OWN=base.OWN


def observations(gate):
    p='XDUT.XCTRL.XTIM.'
    stress={
        'MP1_VSG':dict(positive_node='VDD!',negative_node=gate,limit_abs_v=.99),
        'MP1_VGD':dict(positive_node=gate,negative_node=p+'X020.N',limit_abs_v=.99),
        'INV_MN_VGS':dict(positive_node=p+'X020.N',negative_node='0',limit_abs_v=.99),
    }
    power={'VDD':dict(voltage_node='VDD!',current='VVDD:1')}
    for branch in ['10','14']:
        for node in ['N','MID']:
            power['BIAS'+branch+'_'+node]=dict(voltage_node=p+'SNLOAD'+branch+'_'+node,
                                             current=p+'VBIAS'+branch+'_'+node+':1')
    return dict(stress_voltage_pairs=stress,source_power_ports=power)


def generate():
    original=(OWN/'first_event_analyze.py').read_bytes()
    if base.digest(original)!='da5ac34ce446cdde78490fe6b79f7f533e3f34e866ecd11cece28d67643003c8':
        raise ValueError('Frozen current analyzer changed')
    text=original.decode()
    anchor='    previous_edges = {}\n'
    if text.count(anchor)!=1:raise ValueError('Observer insertion anchor differs')
    text=text.replace(anchor,anchor+'''    full_stress, source_energy, power_previous = {}, {}, {}
    for pair in cfg.get('stress_voltage_pairs', {}).values():
        for key in ('positive_node', 'negative_node'):
            if norm(pair[key]) != '0' and norm(pair[key]) not in selected:
                raise ValueError('Missing full-history stress voltage: ' + pair[key])
    for port in cfg.get('source_power_ports', {}).values():
        if norm(port['voltage_node']) not in selected or norm(port['current']) not in selected:
            raise ValueError('Missing full-history source power observation')
''')
    anchor="        for node, expected in cfg['expected_edges'].items():\n"
    if text.count(anchor)!=1:raise ValueError('Snapshot insertion anchor differs')
    text=text.replace(anchor,'''        for label, pair in cfg.get('stress_voltage_pairs', {}).items():
            def node_value(name):
                return 0. if norm(name) == '0' else values[norm(name)]
            value = node_value(pair['positive_node']) - node_value(pair['negative_node'])
            item = full_stress.setdefault(label, dict(min_v=value, max_v=value,
                min_time_s=t, max_time_s=t, max_abs_v=abs(value), max_abs_time_s=t,
                native_points=0, over_limit_native_points=0, first_over_limit_s=None,
                last_over_limit_s=None, limit_abs_v=pair['limit_abs_v']))
            item['native_points'] += 1
            if value < item['min_v']: item.update(min_v=value, min_time_s=t)
            if value > item['max_v']: item.update(max_v=value, max_time_s=t)
            if abs(value) > item['max_abs_v']: item.update(max_abs_v=abs(value), max_abs_time_s=t)
            if abs(value) > pair['limit_abs_v']:
                item['over_limit_native_points'] += 1
                if item['first_over_limit_s'] is None: item['first_over_limit_s'] = t
                item['last_over_limit_s'] = t
        for label, port in cfg.get('source_power_ports', {}).items():
            power = -values[norm(port['voltage_node'])] * values[norm(port['current'])]
            item = source_energy.setdefault(label, dict(net_delivered_j=0., min_power_w=power,
                max_power_w=power, min_power_time_s=t, max_power_time_s=t,
                first_time_s=t, last_time_s=t, native_points=0))
            previous = power_previous.get(label)
            if previous is not None:
                item['net_delivered_j'] += .5 * (previous[1] + power) * (t - previous[0])
            if power < item['min_power_w']: item.update(min_power_w=power, min_power_time_s=t)
            if power > item['max_power_w']: item.update(max_power_w=power, max_power_time_s=t)
            item['native_points'] += 1; item['last_time_s'] = t
            power_previous[label] = (t, power)
'''+anchor)
    anchor='        missing_required_signals=[], circuit_repair_claim=False,\n'
    if text.count(anchor)!=1:raise ValueError('Result insertion anchor differs')
    text=text.replace(anchor,anchor+'''        full_history_voltage_stress=full_stress, full_history_source_energy=source_energy,
        full_history_observation=dict(start_s=0., stop_s=current_time, native_points=points,
            voltage_pairs='Simultaneous native values at every parsed point, not extrema subtraction',
            energy='Trapezoid of delivered -V*I at original native points; current enters source positive terminal',
            scope='Local fixture sources including ideal bias work; no whole-ADC power qualification'),
''')
    base.exact_write(OWN/'full_gate_analyze.py',text)
    return OWN/'full_gate_analyze.py'
