"""Read-only file-integrity audit against an explicitly trusted Git commit.
No RF sensing, malware attribution, network scanning or backend installation.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path

def audit(root,commit):
    root=Path(root).resolve()
    if not re.fullmatch(r'[0-9a-fA-F]{40}',commit):raise ValueError('Supply a full trusted 40-character commit SHA.')
    def git(*args):return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.PIPE)
    entries=git('ls-tree','-r','-z',commit).split(b'\0');records=[]
    for entry in entries:
        if not entry:continue
        info,name=entry.split(b'\t',1);mode,kind,oid=info.decode().split();name=name.decode()
        relative=Path(name)
        if relative.is_absolute() or '..' in relative.parts:raise ValueError('Unsafe reference path')
        path=root/relative
        expected=hashlib.sha256(git('cat-file','blob',oid)).hexdigest() if kind=='blob' else None
        symlink=any((root/Path(*relative.parts[:i])).is_symlink() for i in range(1,len(relative.parts)+1))
        actual=None
        if mode not in ('100644','100755') or symlink:status='unsupported_or_symlink'
        elif not path.is_file():status='missing'
        else:
            actual=hashlib.sha256(path.read_bytes()).hexdigest()
            status='unchanged' if actual==expected else 'changed'
        records.append({'path':name,'status':status,'expected_sha256':expected,'actual_sha256':actual})
    unexpected=git('ls-files','--others','--exclude-standard','-z').decode().strip('\0').split('\0')
    unexpected=[p for p in unexpected if p]
    # Index additions are not in ls-tree(reference), nor in the untracked list.
    expected_names={r['path'] for r in records}
    unexpected=sorted(set(unexpected)|{p for p in git('ls-files','-z').decode().split('\0') if p and p not in expected_names})
    return {'scope':'Tracked file bytes versus supplied Git reference; ignored files, dependencies, processes, browser extensions and RF are not assessed.',
            'reference_commit':commit,'passed':all(r['status']=='unchanged' for r in records) and not unexpected,
            'files':records,'unexpected_nonignored_files':unexpected,
            'interpretation':'Differences may be authorized edits. Hash agreement is not proof of a trustworthy baseline or an uncompromised machine.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parent);p.add_argument('--reference',required=True);a=p.parse_args()
    result=audit(a.root,a.reference);print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 1)
