"""Offline end-to-end build -> publication copies -> preflight -> Gmail ticket -> ack."""
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from grocery_flyer_watch.quality_cli import main
from grocery_flyer_watch.quality_gate import check, artifacts, unit_cost
from grocery_flyer_watch.reviewed_delivery import connector_publication_fetcher, publication_urls
from grocery_flyer_watch.review import ReviewError
from quality_fixture import fixture


class QualityCLITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.b,self.p,self.now=fixture()
        self.plan=self.root/'review.json';self.plan.write_text(json.dumps(self.b))
        self.config=self.root/'profile.toml'
        self.config.write_text('retailer="Example retailer"\nmarket="Example City, Ontario"\ntimezone="UTC"\n'
            'sources=["https://example.org/flyer", "https://other.example/flyer"]\n'
            'state_file="private/old.json"\noutput_dir="public"\nnotification="none"\npublication="local"\n')
        self.approved=check(self.b,self.p,now=self.now)
        self.out=self.root/'artifacts'
        self.subdir=self.out/self.approved.selection['selection_sha256']
        self.receipt={'repository':'example/project','commit':'a'*40,
                      'directory':'reports/reviewed/'+self.approved.selection['selection_sha256']}
        self.publication=self.root/'publication.json';self.publication.write_text(json.dumps(self.receipt))
        self.proof=dict(**self.receipt,verified_at=self.now.isoformat(),
            evidence_refs={'selection.json':'synthetic-connector-selection','report.md':'synthetic-connector-report'},
            sha256={k:hashlib.sha256(v).hexdigest() for k,v in artifacts(self.approved).items()})
        self.proof_path=self.root/'connector-proof.json';self.proof_path.write_text(json.dumps(self.proof))
        self.journal=self.root/'state'/'journal.sqlite'
        self.recipient='first@example.invalid'
        self.env=patch.dict(os.environ,{'FLYER_RECIPIENT':self.recipient,
                    'FLYER_MAIL_TO':self.recipient+',second@example.invalid'},clear=True)
        self.env.start();self.addCleanup(self.env.stop)

    def invoke(self,args):
        with patch('sys.stdout',new_callable=io.StringIO) as out,patch('sys.stderr',new_callable=io.StringIO) as err:
            result=main([str(x) for x in args])
        return result,out.getvalue(),err.getvalue()

    def build(self):
        result,_,err=self.invoke(['build',self.plan,'--config',self.config,'--out',self.out])
        self.assertEqual(result,0,err)

    def common(self,command):
        return [command,self.plan,'--config',self.config,'--publication',self.publication,
                '--published-copy',self.subdir,'--publication-proof',self.proof_path]

    def seed(self):
        old=self.root/'handled.json'
        base=self.b['audit']['baseline']
        old.write_text(json.dumps({'flyer':{'id':'synthetic-old','retailer':self.p['retailer'],
          'market':self.p['market'],'starts_on':base['starts_on'],'ends_on':base['ends_on'],
          'url':'https://example.org/flyer'},'offers':[{'name':'Old synthetic item','price_cad':'4.00',
           'pricing':'each','priority':3,'why':'Synthetic archived item.'}]}))
        result,_,err=self.invoke(['seed','--config',self.config,'--journal',self.journal,
                                 '--source-scope','weekly-flyer','--snapshot',old])
        self.assertEqual(result,0,err)

    def test_cli_check_and_build_are_offline(self):
        with patch('grocery_flyer_watch.reviewed_delivery.urlopen') as network:
            result,_,err=self.invoke(['check',self.plan,'--config',self.config])
            self.assertEqual(result,0,err)
            self.build();network.assert_not_called()
        self.assertEqual({x.name for x in self.subdir.iterdir()},{'selection.json','report.md'})
        self.assertFalse(self.journal.exists())

    def test_build_reuses_only_identical_files(self):
        self.build();self.build()
        (self.subdir/'report.md').write_text('tampered')
        result,_,err=self.invoke(['build',self.plan,'--config',self.config,'--out',self.out])
        self.assertEqual(result,2);self.assertIn('artifact_differs',err)

    def test_connector_copies_can_be_verified_without_python_network(self):
        self.build()
        body=self.root/'private-body.md'
        with patch('grocery_flyer_watch.reviewed_delivery.urlopen') as network:
            result,_,err=self.invoke(self.common('preflight')+['--body-out',body])
            self.assertEqual(result,0,err);network.assert_not_called()
        self.assertEqual(body.read_text().count('- **'),9)
        self.assertIn('/'+'a'*40+'/',body.read_text())

    def test_tampered_connector_copy_rejected(self):
        self.build();(self.subdir/'selection.json').write_text('{}')
        result,_,err=self.invoke(self.common('preflight'))
        self.assertEqual(result,2);self.assertIn('copy_hash_mismatch',err)

    def test_connector_proof_must_match_actual_commit(self):
        self.build();self.proof['commit']='b'*40;self.proof_path.write_text(json.dumps(self.proof))
        result,_,err=self.invoke(self.common('preflight'))
        self.assertEqual(result,2);self.assertIn('scope_mismatch',err)

    def test_preflight_may_not_skip_publication_with_just_copies(self):
        self.build()
        args=self.common('preflight');args=args[:-2]
        result,_,err=self.invoke(args)
        self.assertEqual(result,2);self.assertIn('both_connector_copy',err)

    def test_gmail_ticket_and_ack_only_after_full_gate(self):
        self.build();self.seed()
        body=self.root/'private-body.md'
        result,_,err=self.invoke(self.common('preflight')+['--body-out',body]);self.assertEqual(result,0,err)
        lookup=self.root/'sent-lookup.json'
        lookup.write_text(json.dumps({'recipient':self.recipient,'event_id':self.approved.event_id,
            'checked_at':self.now.isoformat(),'already_sent':False,'evidence_ref':'synthetic-sent-search'}))
        auth=self.root/'authorization.json'
        result,out,err=self.invoke(self.common('authorize')+['--journal',self.journal,'--sent-lookup',lookup,
                                 '--check-body',body,'--authorization-out',auth])
        self.assertEqual(result,0,err)
        self.assertEqual(json.loads(out)['status'],'authorized')
        self.assertNotIn(self.recipient,out)
        self.assertNotIn('ticket',out)
        receipt=self.root/'accepted.json';receipt.write_text('{"evidence_ref":"synthetic-send-confirmation"}')
        result,_,err=self.invoke(['ack','--journal',self.journal,'--authorization',auth,
                                 '--outcome','sent','--receipt',receipt])
        self.assertEqual(result,0,err)
        result,out,err=self.invoke(self.common('authorize')+['--journal',self.journal,'--sent-lookup',lookup,
                         '--check-body',body,'--authorization-out',self.root/'second-auth.json'])
        self.assertEqual(result,0,err)
        self.assertEqual(json.loads(out)['status'],'already_handled')

    def test_send_without_explicit_flag_is_preflight_not_email(self):
        self.build()
        with patch('grocery_flyer_watch.quality_cli.send') as transport:
            result,out,err=self.invoke(self.common('send')+['--journal',self.journal])
            self.assertEqual(result,0,err);transport.assert_not_called()
        self.assertFalse(self.journal.exists())
        self.assertIn('not_sent',out)

    def test_invalid_json_diagnostic_hides_values(self):
        self.plan.write_text('{ "SECRET_PERSONAL_VALUE": ')
        result,out,err=self.invoke(['check',self.plan,'--config',self.config])
        self.assertEqual(result,2);self.assertNotIn('SECRET_PERSONAL_VALUE',out+err)

    def test_existing_cli_dispatches_quality_subcommand(self):
        from grocery_flyer_watch.__main__ import main as top
        with patch.object(sys,'argv',['grocery-flyer-watch','quality','check',str(self.plan),'--config',str(self.config)]):
            with patch('sys.stdout',new_callable=io.StringIO):self.assertEqual(top(),0)

    def test_unit_prices_come_from_verified_pack_not_name(self):
        item={'price_cad':'4.00','pricing':'package','pack':'500 g'}
        self.assertEqual(unit_cost(item),'$8.00/kg')
        item.update(price_cad='3.99',pack='6 x 710 mL')
        self.assertEqual(unit_cost(item),'$0.94/L')
        item.update(price_cad='3.49',pack='12-count')
        self.assertEqual(unit_cost(item),'$0.29 each')
        item.update(pack='selected sizes')
        self.assertEqual(unit_cost(item),'')


if __name__=='__main__':unittest.main()
