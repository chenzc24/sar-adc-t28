import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest

from tools.saradc import candidates,schematic
from tools.saradc.rnl import Sheet,instances,strip
from tools.saradc.rnl_layouts import annotate
from tools.saradc.rnl_viewer import public_files

ROOT=Path(__file__).resolve().parents[1]
CLI=ROOT/'work/tools/rnl-0.5.5/cli/rnl.exe'

class RnlChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.levels,cls.ports,cls.origin,_=schematic.sources(ROOT)

    def test_native_comments_preserve_statements_and_cover_every_instance(self):
        native=[n for n in self.levels if self.origin[n].startswith(('design/top','design/xtor'))]
        self.assertEqual(len(native),38)
        for n in native:
            body=self.levels[n];drawn,count=annotate(n,body,self.ports)
            self.assertEqual(schematic.electrical_statements(body),schematic.electrical_statements(drawn),n)
            self.assertEqual(drawn,annotate(n,drawn,self.ports)[0],n)
            placed=re.findall(r'#(\w+) @PLACE\(',drawn)
            self.assertEqual(set(placed),set(instances(body)),n)
            self.assertEqual(len(placed),count,n)

    def test_a_drawn_wire_cannot_join_different_electrical_nets(self):
        s=Sheet('sar_strongarm_t28',self.levels['sar_strongarm_t28'],self.ports)
        s.place('MNINN',0,0);s.place('MNINP',20,0)
        with self.assertRaisesRegex(ValueError,'not TAIL'):s.wire('TAIL','MNINN:1','MNINP:3')
        s.wire('TAIL','MNINN:3','MNINP:3')

    def test_grouped_bus_order_is_checked(self):
        name='sar_adc8_join_r4';s=Sheet(name,self.levels[name],self.ports)
        s.place('XCTRL',0,0);s.place('XREF',50,0)
        s.bus([('XCTRL','CODE0'),('XREF','CODE0')])
        s.parts['XREF'][0][0],s.parts['XREF'][0][1]=s.parts['XREF'][0][1],s.parts['XREF'][0][0]
        with self.assertRaisesRegex(ValueError,'Bus order'):s.bus([('XCTRL','CODE0'),('XREF','CODE0')])

    def test_viewer_serves_only_declared_inputs(self):
        lock=json.loads((ROOT/'tools/saradc/rnl_viewer.lock.json').read_text())
        files=public_files(ROOT,ROOT/'work/tools/rnl-viewer-0.5.3',lock)
        self.assertIn('/repo/design/top/adc_top.scs',files)
        self.assertIn('/viewer/core/rnl_runtime_wasm.wasm',files)
        self.assertNotIn('/repo/design/frozen/b/dut.scs',files)
        self.assertNotIn('/repo/.git/config',files)
        self.assertNotIn('/repo/results/mc/reference_5126.json',files)
        workspace=json.loads((ROOT/'design/rnl/workspace.json').read_text())
        for row in workspace['files']:
            data=files['/repo/'+row['path']].read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(),row['sha256'])
            self.assertEqual(len(data),row['size'])

    @unittest.skipUnless(CLI.is_file(),'Install pinned RNL 0.5.5 to validate rendering')
    def test_split_workspace_and_portable_export_have_no_diagnostics(self):
        for p in ['current.scs','export.scs']:
            report=schematic.validate(str(CLI),ROOT/'design/rnl'/p)
            self.assertIn('0 errors, 0 warnings, 0 hints',report)

    @unittest.skipUnless(CLI.is_file(),'Install pinned RNL 0.5.5 to validate candidate rendering')
    def test_candidate_display_uses_actual_candidate_without_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for folder in ['design','specs','tb','tools']:
                shutil.copytree(ROOT/folder,root/folder,ignore=shutil.ignore_patterns('__pycache__'))
            source=root/'design/xtor/comparator/comparator.scs';original=source.read_bytes()
            alternative=source.with_name('display_test.scs')
            alternative.write_text(source.read_text().replace('w=1u','w=2u'),encoding='utf-8')
            candidates.add('comparator','display-test',alternative.relative_to(root).as_posix(),root)
            catalog=candidates.catalog(root)
            schematic.candidate_exports(root,str(CLI),catalog)
            row=next(r for r in catalog if r['candidate']=='display-test')
            self.assertIn('w=2u',row['changed_levels']['sar_strongarm_t28']['source'])
            self.assertIn('w=2u',row['changed_levels']['sar_strongarm_t28']['svg'])
            self.assertFalse(row['selected'])
            self.assertEqual(candidates.read(root)['modules']['comparator']['selected'],'b')
            self.assertEqual(source.read_bytes(),original)
            self.assertIn('/candidate/comparator-display-test/',row['workspace'])

if __name__=='__main__':unittest.main()
