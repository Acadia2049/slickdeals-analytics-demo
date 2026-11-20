"""Build a synthetic, credential-free demo using the actual dbt models and reports."""
from collections import Counter
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import duckdb

from bundle import FILES, MARTS, digest, verify
from report_contract import describe_queries, write_json

ROOT = Path(__file__).resolve().parents[1]
RELEASE = 'sd-synthetic-demo-v1'
STORE = ROOT / 'demo/local'


def inputs(root):
    schema = json.loads((ROOT / 'demo/clean_schema.json').read_text())
    fields = [r['name'] for r in schema]
    con = duckdb.connect()
    con.execute('create table observations (' + ','.join(f'"{r["name"]}" {r["type"]}' for r in schema) + ')')
    # Fictional observations deliberately include missing counters, a negative change,
    # disappearance/reappearance, a merchant transfer and a four-hour sampling gap.
    events = [
        [(1,'Demo Market',0,10,'fixed',1),(2,'Demo Market',10,10,'starting_at',5),
         (3,'Demo Market',0,0,'fixed',100),(4,'Demo Market',1,0,'fixed',101),
         (8,'Demo Market',0,0,'fixed',102),(7,'Demo Books',0,0,'other',None)],
        [(1,'Demo Market',2,10,'fixed',1),(2,'Demo Market',20,6,'fixed',50),(3,'Demo Outlet',100,100,'fixed',90)],
        [(1,'Demo Market',5,12,'fixed',1),(5,'Demo Market',0,0,'fixed',200)],
        [(1,'Demo Market',9,None,'fixed',1)],
        [(1,'Demo Market',None,30,'fixed',1)],
        [(1,'Demo Market',12,33,'fixed',1),(7,'Demo Books',1,1,'other',None)],
    ]
    runs = []
    for i, observations in enumerate(events):
        ts = datetime(2026, 11, 4, 1) + timedelta(hours=2*i + (2 if i == 5 else 0))
        timestamp = ts.isoformat() + 'Z'
        key = f'synthetic-{i:03d}'
        raw = json.dumps(observations, sort_keys=True).encode()
        raw_hash = hashlib.sha256(raw).hexdigest()
        raw_uri = f'demo://synthetic/{key}/observations.json'
        evidence = root / f'source/evidence/collection_14d/campaign_id=slickdeals-14d/run_id={key}'
        evidence.mkdir(parents=True)
        (evidence/'observations.json').write_bytes(raw)
        run = dict(run_key=key, run_id=key, schema_version=2, raw_schema_version=2,
                   parser_version='frontpage-v2', data_scope='server_html_frontpage_slickdeals',
                   scheduled_at=timestamp, observed_at=timestamp, completed_at=timestamp,
                   snapshot_timestamp=timestamp, row_count=len(observations), candidate_records=len(observations),
                   omitted_count=0, is_truncated=False, validation_status='passed', raw_location=raw_uri,
                   raw_sha256=raw_hash, verified_sha256=raw_hash, selector_failures=0,
                   required_field_completeness=1.0, volume_assessment={'status':'passed','reason':'synthetic fixture'})
        runs.append(run)
        write_json(evidence/'verification.json', dict(run_key=key,run_id=key,observed_at=timestamp,
                   verified_at=timestamp,row_count=len(observations),status='success',raw_uri=raw_uri,raw_sha256=raw_hash))
        for position, (deal, shop, votes, comments, kind, amount) in enumerate(observations, 1):
            row = dict(snapshot_timestamp=ts,snapshot_date=ts.date(),deal_id=deal,store=shop,
                       store_normalized=shop.lower(),title=f'Synthetic example item {deal}',
                       title_link=f'https://example.com/demo/{deal}',deal_path=f'/demo/{deal}',
                       deal_price_raw=str(amount),deal_price_type=kind,deal_price_amount=amount,
                       price_parse_success=kind!='other',vote_count=votes,comment_count=comments,
                       page_section='frontpage',card_layout='synthetic',record_position=position,
                       record_position_source='parser',dom_position=position,section_position=position,
                       raw_schema_version=2,parser_version='frontpage-v2',data_scope=run['data_scope'],
                       candidate_records=len(observations),omitted_count=0,is_truncated=False,
                       snapshot_timestamp_source='synthetic_fixture',source_file='observations.json',
                       pipeline_run_id='synthetic-demo',record_hash=hashlib.sha256(f'{key}:{deal}'.encode()).hexdigest())
            con.execute('insert into observations values ('+','.join('?' for _ in fields)+')', [row.get(c) for c in fields])
    (root/'clean').mkdir()
    con.execute('copy observations to ? (format parquet, partition_by (snapshot_date))',[str(root/'clean')])
    con.close()
    (root/'source/metadata').mkdir()
    write_json(root/'source/metadata/collection_runs.json',runs)


def build():
    # Demo storage is separate from the operator's approved local/current pointer.
    if (STORE/'current').exists():
        pointer=json.loads((STORE/'current').read_text())
        verify(STORE/'versions'/pointer['release_id'],pointer['manifest_sha256'])
        print(f'Existing verified demo: {STORE}. Remove analytics/demo/local to rebuild.')
        return
    ROOT.joinpath('demo/builds').mkdir(parents=True,exist_ok=True)
    work=Path(tempfile.mkdtemp(prefix='run-',dir=ROOT/'demo/builds'))
    inputs(work/'input')
    env=dict(os.environ,SD_INPUT_ROOT=str(work/'input'),SD_CANDIDATE_DB=str(work/'analytics.duckdb'),
             DBT_SEND_ANONYMOUS_USAGE_STATS='false',DBT_USE_COLORS='false',PYTHONDONTWRITEBYTECODE='1')
    executable=Path(sys.executable).with_name('dbt')
    for action in ('build','compile'):
        target=work/action/'target'
        cmd=[str(executable),action,'--project-dir',str(ROOT/'project'),'--profiles-dir',str(ROOT/'profiles'),
             '--target-path',str(target),'--log-path',str(work/action/'logs')]
        with (work/f'{action}.log').open('w') as out:
            result=subprocess.run(cmd,env=env,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError((work/f'{action}.log').read_text()[-12000:])
    env['SD_TEST_BUILD']=str(work)
    with (work/'business-tests.log').open('w') as out:
        subprocess.run([sys.executable,'-B',str(ROOT/'tests/test_business_queries.py')],env=env,cwd=ROOT,
                       stdout=out,stderr=subprocess.STDOUT,check=True)
    results=json.loads((work/'build/target/run_results.json').read_text())['results']
    counts=dict(Counter(r['status'] for r in results))
    assert all(r['status'] in ('pass','success') for r in results)
    package=work/RELEASE
    (package/'bin').mkdir(parents=True)
    for name in ('report_query.py','comment_velocity.py','bundle.py'):
        shutil.copyfile(ROOT/'tools'/name,package/'bin'/name)
    shutil.copytree(work/'compile/target/compiled/slickdeals_analytics/analyses',package/'sql')
    meta=json.loads((work/'compile/target/manifest.json').read_text())
    with duckdb.connect(str(package/'analytics.duckdb')) as db:
        source_path=str(work/'analytics.duckdb').replace("'", "''")
        db.execute(f"attach '{source_path}' as rebuilt (read_only)")
        db.execute('create schema analytics_marts')
        for name in MARTS:
            db.execute(f'create table analytics_marts.{name} as select * from rebuilt.analytics_marts.{name}')
        db.execute('detach rebuilt')
        write_json(package/'contract.json',describe_queries(db,meta,package/'sql',RELEASE))
        db.execute("comment on table analytics_marts.mart_collection_quality is '"+digest(package/'contract.json')+"'")
    (package/'README.md').write_text('# Synthetic demo\nFictional observations, not collected data or research findings.\n')
    write_json(package/'acceptance.json',dict(status='passed',release_id=RELEASE,dbt=counts,
               business_fixture_tests='passed',synthetic=True))
    write_json(package/'manifest.json',dict(release_id=RELEASE,purpose='synthetic-demo',metric_contract_version='1.0.0',
               dependencies={'duckdb':duckdb.__version__},files={name:digest(package/name) for name in sorted(FILES)}))
    verify(package)
    (STORE/'versions').mkdir(parents=True,exist_ok=True)
    shutil.copytree(package,STORE/'versions'/RELEASE)
    write_json(STORE/'current',dict(release_id=RELEASE,manifest_sha256=digest(package/'manifest.json')))
    print(json.dumps(dict(status='passed',synthetic=True,dbt=counts,store=str(STORE),evidence=str(work)),indent=2))


if __name__=='__main__':
    build()
