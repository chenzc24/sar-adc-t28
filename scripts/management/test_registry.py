"""Focused checks for run identity, safe references and observation semantics."""
import unittest
import project

class RegistrySemantics(unittest.TestCase):
    def test_other_libraries_are_not_claimed_as_project_runs(self):
        base='/home/chenzc_intern25/TSMC28/llm_IO'
        self.assertEqual(project.directory_scope(base+'/SAR_ADC_T28',set(),[]),'project_OA')
        catalog=[{'name':'OTHER','path':base+'/OTHER'}]
        self.assertEqual(project.directory_scope(base+'/OTHER',set(),catalog),'other_library_read_only')
        self.assertEqual(project.directory_scope(base+'/runs',{base+'/runs/one'},[]),'registered_run_or_container')

    def test_identical_case_names_in_different_experiments_are_distinct(self):
        a='output/a/null_ff_m40';b='output/b/null_ff_m40'
        self.assertEqual(project.uid(a),project.uid(a))
        self.assertNotEqual(project.uid(a),project.uid(b))

    def test_untrusted_remote_values_never_become_commands(self):
        for p in ['/home/other/run','/tmp/virtuoso_bridge_chenzc_intern25/90590/../secret',
                  '/home/chenzc_intern25/TSMC28/llm_IO/run\nother']:
            self.assertFalse(project.safe_remote(p))
        p='/home/chenzc_intern25/TSMC28/llm_IO/test/run'
        self.assertTrue(project.safe_remote(p))
        data={'remote':p,'metadata':{'command':'spectre '+p+'/test.scs -raw '+p+'/test.raw'}}
        self.assertEqual(project.remote_references(data),[p,p+'/test.raw'])

    def test_missing_remote_path_does_not_erase_recorded_success(self):
        p='/tmp/virtuoso_bridge_chenzc_intern25/90590/old/case'
        d={'runs':[{'remote_paths':[p],'native_execution':'exit_0_recorded','verdict':'not_inferred'}]}
        project.merge_observations(d,{'directories':[{'path':p,'exists':False}],'observed_at_utc':'fixture'})
        self.assertEqual(d['runs'][0]['native_execution'],'exit_0_recorded')
        self.assertEqual(d['runs'][0]['verdict'],'not_inferred')
        self.assertFalse(d['runs'][0]['remote_observations'][0]['exists'])

    def test_exit_zero_does_not_imply_analysis_or_pass(self):
        p='/home/chenzc_intern25/TSMC28/llm_IO/current/case'
        d={'runs':[{'remote_paths':[p],'native_execution':'unknown','analysis':'unknown','verdict':'not_inferred'}]}
        project.merge_observations(d,{'directories':[{'path':p,'exists':True,'exit_code':'0'}],'observed_at_utc':'fixture'})
        self.assertEqual(d['runs'][0]['native_execution'],'exit_0_observed')
        self.assertEqual(d['runs'][0]['analysis'],'unknown')
        self.assertEqual(d['runs'][0]['verdict'],'not_inferred')

if __name__=='__main__':unittest.main()
