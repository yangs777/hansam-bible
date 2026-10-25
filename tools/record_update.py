"""Append one site-update record before publishing a non-edition change."""
import argparse, pathlib
from datetime import datetime, timezone
from update_log import append_entry

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--id',required=True);p.add_argument('--title',required=True)
    p.add_argument('--detail',action='append',required=True);p.add_argument('--url',default='/updates/')
    a=p.parse_args()
    changed=append_entry(pathlib.Path(__file__).resolve().parents[1],{
        'id':a.id,'kind':'site','recorded_at':datetime.now(timezone.utc).isoformat(),
        'time_basis':'change_recorded_at','title_ko':a.title,'summary_ko':a.detail,
        'links':[{'label':'관련 페이지','url':a.url}]})
    print('Recorded' if changed else 'Already recorded')
