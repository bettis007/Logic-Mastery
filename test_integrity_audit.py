"""Controlled fixture mutations only; no real compromise is inferred."""
import subprocess,tempfile
from pathlib import Path
from integrity_audit import audit
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp)
    def git(*args):return subprocess.check_output(['git','-C',tmp,*args],stderr=subprocess.DEVNULL).decode().strip()
    git('init');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid')
    (root/'app.js').write_text('original');git('add','app.js');git('commit','-m','fixture');sha=git('rev-parse','HEAD')
    assert audit(root,sha)['passed']
    (root/'app.js').write_text('altered');assert audit(root,sha)['files'][0]['status']=='changed'
    (root/'app.js').unlink();assert audit(root,sha)['files'][0]['status']=='missing'
    (root/'outside').write_text('original');(root/'app.js').symlink_to(root/'outside')
    assert audit(root,sha)['files'][0]['status']=='unsupported_or_symlink'
    (root/'app.js').unlink();(root/'app.js').write_text('original');(root/'outside').unlink()
    (root/'extra.js').write_text('extra');assert audit(root,sha)['unexpected_nonignored_files']==['extra.js']
    git('add','extra.js');assert audit(root,sha)['unexpected_nonignored_files']==['extra.js']
    try:audit(root,'HEAD');raise AssertionError('Unpinned reference accepted')
    except ValueError:pass
print('PASS: clean fixture, alteration, deletion, symlink, untracked addition, staged addition, and unpinned-reference rejection (7 checks).')
