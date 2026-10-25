"""为已构建的便携目录补齐许可、构建信息、对应源码和 SHA-256。"""
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
APP = ROOT/'dist'/'MzCleanerFree'
OUT = ROOT/'dist'/'packages'
VERSION = '0.1.0'


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def main():
    if git('status', '--porcelain').strip():
        raise SystemExit('Commit source changes before packaging.')
    if not (APP/'MzCleanerFree.exe').is_file():
        raise SystemExit('Run build.ps1 first.')
    OUT.mkdir(parents=True, exist_ok=True)
    licenses = APP/'licenses'
    licenses.mkdir(exist_ok=True)
    packages = {}
    for dist in metadata.distributions():
        name = dist.metadata['Name']
        packages[name] = dist.version
        for file in dist.files or []:
            if any(word in file.name.lower() for word in ('license', 'copying', 'notice')):
                source = Path(dist.locate_file(file))
                if source.is_file() and source.suffix.lower() not in ('.py', '.pyc'):
                    target = licenses/name/str(file)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    python_license = Path(sys.base_prefix)/'LICENSE.txt'
    if python_license.exists():
        shutil.copy2(python_license, licenses/'Python-LICENSE.txt')
    for name in ('LICENSE', 'README.md'):
        shutil.copy2(ROOT/name, APP/name)
    sources = git('ls-files', '*.py').decode().splitlines()
    info = {
        'product': 'MzCleanerFree', 'version': VERSION,
        'source_commit': git('rev-parse', 'HEAD').decode().strip(),
        'upstream_commit': '852c9617737503ec5db3015565d8cd4609e0c6ea',
        'packaged_at_utc': datetime.now(timezone.utc).isoformat(),
        'python': sys.version.split()[0], 'architecture': 'Windows x64',
        'build_dependencies': dict(sorted(packages.items())),
        'source_hash_basis': 'Git blob bytes, matching the source ZIP',
        'source_sha256': {p: hashlib.sha256(git('show', f'HEAD:{p}')).hexdigest() for p in sources},
    }
    (APP/'BUILD-INFO.json').write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')
    files = sorted(p for p in APP.rglob('*') if p.is_file() and p.name != 'SHA256SUMS.txt')
    (APP/'SHA256SUMS.txt').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(APP).as_posix()}\n' for p in files), encoding='utf-8')
    portable = OUT/f'MzCleanerFree-{VERSION}-windows-x64-portable.zip'
    with zipfile.ZipFile(portable, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(APP.rglob('*')):
            if p.is_file():
                z.write(p, Path('MzCleanerFree')/p.relative_to(APP))
    source_zip = OUT/f'MzCleanerFree-{VERSION}-source.zip'
    subprocess.run(['git', '-C', str(ROOT), 'archive', '--format=zip',
                    '--prefix=MzCleanerFree-source/', '-o', str(source_zip), 'HEAD'], check=True)
    (OUT/'SHA256SUMS.txt').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in [portable, source_zip]), encoding='utf-8')
    print(json.dumps({'source_commit': info['source_commit'], 'packages': [str(portable), str(source_zip)]}, indent=2))


if __name__ == '__main__':
    main()
