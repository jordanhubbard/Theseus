"""Priority and restart safety for the metadata scan frontier."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from theseus import fabric
from theseus.scan_queue import plan, run


def recipe(root, name, deps=None, ecosystem='pypi', registry_name=None, covered=True):
    record = dict(schema_version='1.0', identity=dict(canonical_name=name,canonical_id='pkg:'+name,
        ecosystem=ecosystem,ecosystem_id=registry_name or name,version='1.0'),
        dependencies=deps or {},descriptive=dict(summary='Metadata fixture',license=['MIT'],homepage=''),
        provenance=dict(imported_at='2026-01-01T00:00:00+00:00',source_path='metadata fixture',confidence=0.9),
        extensions={ecosystem:{'source_repository':'https://github.com/example/'+name}},sources=[])
    path=root/'specs'/fabric.package_filename(name);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(record))
    if covered:
        fingerprint=fabric.recipe_to_fingerprint(record,str(path.relative_to(root)),root=root)
        dest=root/'fabric/packages'/fabric.package_filename(name);dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps(fingerprint))
    return record


def entry(queue, name, ecosystem='pypi'):
    return next(e for e in queue['entries'] if e['name']==name and e['ecosystem']==ecosystem)


def test_counts_unique_consumers_not_scopes_or_duplicate_recipes(tmp_path):
    rec=recipe(tmp_path,'consumer',{'build':['Num_Py'],'runtime':['numpy'],'test':['numpy']})
    p=tmp_path/'examples/copy.json';p.parent.mkdir();p.write_text(json.dumps(rec))
    recipe(tmp_path,'consumer2',{'runtime':['numpy']})
    assert entry(plan(tmp_path),'numpy')['ref_count']==2
    assert entry(plan(tmp_path),'numpy')['referrers']==['consumer','consumer2']


def test_namespace_isolation_coverage_and_stable_ties(tmp_path):
    recipe(tmp_path,'a',{'runtime':['shared','bbb']})
    recipe(tmp_path,'b',{'runtime':['shared']},ecosystem='npm')
    recipe(tmp_path,'shared',ecosystem='npm')
    q=plan(tmp_path)
    assert entry(q,'shared')['state']=='pending'
    assert entry(q,'shared','npm')['state']=='covered'
    assert q==plan(tmp_path)
    assert [e['name'] for e in q['entries']]==['bbb','shared','shared']


def test_fingerprint_without_recipe_is_not_covered(tmp_path):
    recipe(tmp_path,'a',{'runtime':['numpy']});recipe(tmp_path,'numpy')
    (tmp_path/'specs/numpy.json').unlink()
    assert entry(plan(tmp_path),'numpy')['state']=='pending'


def test_scoped_npm_and_native_manual_sources(tmp_path):
    recipe(tmp_path,'a',{'runtime':['@types/node','${bad}','lib/x.so']},ecosystem='npm')
    recipe(tmp_path,'b',{'build':['pkg-config']},ecosystem='nixpkgs')
    q=plan(tmp_path)
    assert entry(q,'@types/node','npm')['state']=='pending'
    assert entry(q,'pkg-config','nixpkgs')['state']=='manual'
    assert len(q['entries'])==2
    assert fabric.extract_depends_on(json.loads((tmp_path/'specs/a.json').read_text()))==[
        {'name':'@types/node','scope':'runtime','ecosystem':'npm'}]
    assert fabric.extract_dropped_dependencies(json.loads((tmp_path/'specs/a.json').read_text()))==[
        {'name':'${bad}','scope':'runtime','reason':'unresolved_token'},
        {'name':'lib/x.so','scope':'runtime','reason':'unresolved_token'}]


def test_scoped_registry_id_coverage_uses_actual_npm_name(tmp_path):
    recipe(tmp_path,'a',{'runtime':['@types/node']},ecosystem='npm')
    recipe(tmp_path,'types__node',ecosystem='npm',registry_name='@types/node')
    assert entry(plan(tmp_path),'@types/node','npm')['state']=='covered'


def test_scan_priority_limit_validation_and_idempotent_old_queue(tmp_path):
    recipe(tmp_path,'a',{'runtime':['popular','other']})
    recipe(tmp_path,'b',{'runtime':['popular']})
    q=plan(tmp_path)
    fetched=[]
    def fetch(name,timeout):
        fetched.append(name)
        return recipe(tmp_path/'upstream',name,covered=False)
    with patch('theseus.scan_queue.importer.pypi_record',side_effect=fetch):
        report=run(tmp_path,q,limit=1)
        assert report['scanned']==1 and not report['failed']
        assert fetched==['popular']
        assert entry(plan(tmp_path),'popular')['state']=='covered'
        report=run(tmp_path,q,limit=1)
        assert report['stale_plan'] and report['scanned']==1
        assert fetched==['popular','other']
        assert run(tmp_path,q)['attempted']==0


def test_failed_registry_fetch_preserves_existing_bytes_and_continues(tmp_path):
    recipe(tmp_path,'a',{'runtime':['one','two']});old=recipe(tmp_path,'one')
    path=tmp_path/'specs/one.json';before=path.read_bytes()
    with patch('theseus.scan_queue.importer.pypi_record',side_effect=[None,recipe(tmp_path/'upstream','two',covered=False)]):
        report=run(tmp_path,plan(tmp_path),refresh_covered=True)
    assert report['failed']==1 and report['scanned']==1
    assert path.read_bytes()==before


def test_identity_mismatch_fails_without_writing_recipe(tmp_path):
    recipe(tmp_path,'a',{'runtime':['desired']})
    with patch('theseus.scan_queue.importer.pypi_record',return_value=recipe(tmp_path/'upstream','wrong',covered=False)):
        report=run(tmp_path,plan(tmp_path))
    assert report['failed']==1 and not (tmp_path/'specs/desired.json').exists()


def test_scoped_scan_and_refresh_preserves_other_ecosystem_metadata(tmp_path):
    recipe(tmp_path,'a',{'runtime':['@types/node']},ecosystem='npm')
    upstream=recipe(tmp_path/'upstream','types__node',ecosystem='npm',registry_name='@types/node',covered=False)
    with patch('theseus.scan_queue.importer.npm_record',return_value=upstream):
        result=run(tmp_path,plan(tmp_path))
        assert result['scanned']==1
        result=run(tmp_path,plan(tmp_path),refresh_covered=True)
        assert result['scanned']==1
    assert fabric.load_store(tmp_path).get('types__node') is not None


@pytest.mark.parametrize('limit,timeout',[(0,15),(501,15),(1,0),(1,121)])
def test_invalid_bounds_fail_before_network(tmp_path,limit,timeout):
    with pytest.raises(ValueError):
        run(tmp_path,{'schema':'theseus-scan-queue@1','entries':[]},limit=limit,timeout=timeout)


def test_batch_ingest_preserves_unchanged_fingerprint_bytes(tmp_path):
    recipe(tmp_path,'unchanged')
    fabric.ingest(tmp_path,[tmp_path/'specs'],jobs=1)
    path=tmp_path/'fabric/packages/unchanged.json';before=path.read_bytes()
    data=json.loads(before);data['tracking']['ingested_at']='a different collection time'
    fabric.write_fingerprint(path,data)
    assert path.read_bytes()==before
    data['summary']='Actual new evidence'
    fabric.write_fingerprint(path,data)
    assert json.loads(path.read_text())['summary']=='Actual new evidence'


def test_bounded_parallel_metadata_fetch_commits_and_reports_in_priority_order(tmp_path):
    from threading import Barrier, Lock, current_thread, main_thread
    from theseus import scan_queue
    recipe(tmp_path, 'consumer', {'runtime': ['one', 'two', 'three', 'four']})
    queue = plan(tmp_path)
    records = {name: recipe(tmp_path / 'upstream', name, covered=False) for name in ['one', 'two', 'three', 'four']}
    barrier, lock = Barrier(2), Lock()
    active, peak = 0, 0
    writes = []
    atomic = scan_queue._atomic_json
    def fetch(name, timeout):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        barrier.wait(timeout=5)
        with lock:
            active -= 1
        return records[name]
    def write(path, data):
        assert current_thread() is main_thread()
        writes.append(data['identity']['canonical_name'])
        atomic(path, data)
    with patch.object(scan_queue.importer, 'pypi_record', side_effect=fetch), patch.object(scan_queue, '_atomic_json', side_effect=write):
        report = run(tmp_path, queue, jobs=2)
    expected = [e['name'] for e in queue['entries'] if e['state'] == 'pending']
    assert report['scanned'] == 4 and report['failed'] == 0
    assert [r['name'] for r in report['results']] == writes == expected
    assert peak == 2
    assert run(tmp_path, queue, jobs=2)['attempted'] == 0


@pytest.mark.parametrize('jobs', [0, 17])
def test_invalid_worker_bounds_are_rejected_before_fetch(tmp_path, jobs):
    with pytest.raises(ValueError, match='jobs'):
        run(tmp_path, plan(tmp_path), jobs=jobs)
