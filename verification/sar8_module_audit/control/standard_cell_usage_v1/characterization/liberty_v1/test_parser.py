"""One focused synthetic parser/reference test; no real library/server access."""
from pathlib import Path
import gzip
import hashlib
import json
import struct
import tempfile
import unittest
import liberty_semantics as liberty
import measured_comparison as measured

HERE=Path(__file__).resolve().parent


class Chunked(object):
    def __init__(self,blob):self.blob=blob;self.position=0;self.maximum_request=0
    def read_some(self,size):
        if size>65536 or size<1:raise AssertionError('Unbounded member read')
        self.maximum_request=max(self.maximum_request,size)
        result=self.blob[self.position:self.position+min(size,17)]
        self.position+=len(result);return result


class ParserEvidence(unittest.TestCase):
    def test_skip_scope_template_references_and_actual_thresholds(self):
        text=r'''
/* boundary-split comment with braces { } and quote " */
library(synthetic_ff) {
 time_unit : "1ns"; capacitive_load_unit(1,pf);
 voltage_unit : "1V"; nom_voltage : 0.99; nom_temperature : -40;
 slew_lower_threshold_pct_rise : 30; slew_upper_threshold_pct_rise : 70;
 slew_lower_threshold_pct_fall : 20; slew_upper_threshold_pct_fall : 80;
 slew_derate_from_library : 1.0; default_max_transition : 0.4;
 default_operating_conditions : ff;
 operating_conditions(ff) { process: 1; voltage: 0.99; temperature: -40; }
 cell(OTHER) { pin(X) { output_current_rise(CCS) { values("'''
        text+='0.123, '*350000
        text+=r''' \\" escaped } { still in quote"); } } }
 cell(DFCNQD1BWP12T30P140) {
  slew_lower_threshold_pct_rise:25; slew_upper_threshold_pct_rise:75;
  ff(IQ,IQN) { clocked_on:"CP"; next_state:"D"; clear:"!CDN"; }
  pin(D) { direction:input; capacitance:0.001;
   timing() { related_pin:"CP"; timing_type:setup_rising; when:"CDN";
    rise_constraint(setup_tpl) { index_1("0.02,0.04"); values("-0.01,0.03","0.05,0.07"); }
    fall_constraint(scalar) { values("-0.02"); }
   }
  }
  pin(CP) { direction:input; clock:true; max_transition:0.2;
   slew_lower_threshold_pct_rise:30; slew_upper_threshold_pct_rise:70;
   timing() { related_pin:"CP"; timing_type:min_pulse_width;
    rise_constraint(pulse_tpl) { values("0.04,0.05"); }
   }
  }
  pin(CDN) { direction:input; capacitance:0.002;
   timing() { related_pin:"CP"; timing_type:recovery_rising; rise_constraint(scalar) { values("0.01"); } }
   timing() { related_pin:"CP"; timing_type:removal_rising; fall_constraint(scalar) { values("-0.002"); } }
  }
  pin(Q) { direction:output; function:"IQ"; max_capacitance:0.1;
   timing() { related_pin:"CP"; timing_type:rising_edge; timing_sense:non_unate;
    cell_rise(delay_tpl) { values("0.01,0.02", \
                                  "0.03,0.04"); }
    rise_transition(delay_tpl) { values("0.01,0.02","0.03,0.04"); }
    output_current_rise(CCS) { vector() { values("'''
        text+='0.5, '*30000
        text+=r'''"); } }
   }
  }
 }
 /* templates after references: must not be silently dropped */
 lu_table_template(setup_tpl) {
  variable_1:constrained_pin_transition; variable_2:related_pin_transition;
  index_1("0.01,0.03"); index_2("0.02,0.06");
 }
 lu_table_template(delay_tpl) {
  variable_1:input_net_transition; variable_2:total_output_net_capacitance;
  index_1("0.01,0.1"); index_2("0.001,0.1");
 }
 lu_table_template(pulse_tpl) { variable_1:constrained_pin_transition; index_1("0.01,0.2"); }
}
'''
        # Replace the deliberate escaped quote with a single Liberty escape.
        text=text.replace(r'\\" escaped',r'\" escaped')
        blob=text.encode('ascii');source=Chunked(blob)
        cfg=json.loads((HERE/'semantic_config.json').read_text())
        result=liberty.Semantics(source,cfg).parse()
        self.assertTrue(result['parser_complete']);self.assertEqual(source.position,len(blob))
        self.assertLessEqual(source.maximum_request,65536)
        self.assertEqual(result['target_cell']['arguments'],['DFCNQD1BWP12T30P140'])
        self.assertEqual(result['unresolved_template_references'],[])
        setup=next(a for a in result['timing_arcs'] if a['attributes']['timing_type']=='setup_rising')
        table=setup['tables'][0]
        self.assertEqual(table['effective_axes']['1'],[.02,.04]);self.assertEqual(table['axis_sources']['1'],'arc_override')
        self.assertEqual(table['effective_axes']['2'],[.02,.06]);self.assertTrue(table['value_count_matches_axes'])
        self.assertEqual(table['values_summary'],dict(count=4,min=-.01,max=.07,matrix_not_retained=True))
        self.assertLess(len(json.dumps(result)),50000)
        self.assertNotIn('output_current_rise',json.dumps(result))
        self.assertEqual({p['arguments'][0] for p in result['target_cell']['groups'] if p['kind']=='pin'},{'D','CP','CDN','Q'})
        with tempfile.TemporaryDirectory(prefix='_focused_',dir=HERE) as tmp:
            root=Path(tmp);path=root/'native.bin.gz';pack=struct.Struct('<5d')
            data=b''.join(pack.pack(*r) for r in [(0.,.99,0.,0.,.99),(10e-12,.99,.99,.99,0.),(20e-9,.99,.99,.99,0.)])
            with gzip.open(path,'wb') as f:f.write(data)
            refs=dict(cases={'synthetic':dict(file=path.name,native_points=3,decoded_bytes=len(data),decoded_sha256=hashlib.sha256(data).hexdigest())})
            comparison=measured.compare(result,refs,str(root))
            edge=comparison['actual_edges']['synthetic']['CP']['rise']
            self.assertAlmostEqual(edge['raw_range_s'][0]/1e-12,4.)
            self.assertAlmostEqual(comparison['actual_edges']['synthetic']['D']['rise']['raw_range_s'][0]/1e-12,5.)
            self.assertEqual(comparison['threshold_basis']['CP']['rise']['slew_lower_threshold_pct_rise']['source'],'pin')
            self.assertEqual(comparison['threshold_basis']['D']['rise']['slew_lower_threshold_pct_rise']['source'],'cell')
            self.assertEqual(comparison['threshold_basis']['CDN']['fall']['slew_lower_threshold_pct_fall']['source'],'library')
            self.assertEqual(edge['events'][0]['lower']['native_bracket_s'],[0.,10e-12])
            self.assertAlmostEqual(comparison['actual_edges']['synthetic']['CDN']['fall']['raw_range_s'][0]/1e-12,6.)
            self.assertAlmostEqual(comparison['pin_limits']['Q']['max_capacitance']['SI_value']/1e-12,.1)
            self.assertIsNone(comparison['effective_actual_Q_load_F'])
            self.assertFalse(comparison['slew_derating_semantics_applied'])
            self.assertAlmostEqual(setup['tables'][0]['values_time_extrema_s'][0]/1e-12,-10.)
            self.assertAlmostEqual(setup['tables'][0]['values_time_extrema_s'][1]/1e-12,70.)
        print('SYNTHETIC_ONLY: >2MB CCS skipped in17B chunks; postdefined template/override/negative constraint and30-70 native slew verified')


if __name__=='__main__':unittest.main()
