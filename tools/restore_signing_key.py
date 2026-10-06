"""Restore the persistent APK key from Actions secrets; reject a different signer."""
import argparse
import base64
import hashlib
import os
from pathlib import Path
import subprocess

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-cert', type=Path, default=Path(__file__).resolve().parents[1] / '.github/signing-cert.sha256')
    args = parser.parse_args()
    encoded = os.environ.get('KAI_KEYSTORE_B64', '')
    password = os.environ.get('KAI_KEYSTORE_PASSWORD', '').strip()
    existing = os.environ.get('KAI_KEYSTORE_PATH', '')
    if not password or not (encoded or existing):
        raise SystemExit('Supply the existing KAI_KEYSTORE_PATH (or KAI_KEYSTORE_B64) and KAI_KEYSTORE_PASSWORD securely. Refusing a temporary APK signer.')
    os.environ['KAI_KEYSTORE_PASSWORD'] = password
    created = False
    if existing:
        key = Path(existing).resolve(strict=True)
    else:
        data = base64.b64decode(encoded.strip(), validate=True)
        if not 1000 <= len(data) <= 32768:
            raise SystemExit('Invalid keystore size')
        directory = Path(os.environ.get('RUNNER_TEMP', '/tmp'))
        import tempfile
        fd, name = tempfile.mkstemp(prefix='cantonesemixeng-signing-', suffix='.p12', dir=directory)
        key = Path(name)
        with os.fdopen(fd, 'wb') as out:
            out.write(data)
        created = True
    try:
        result = subprocess.run(['keytool', '-exportcert', '-storetype', 'PKCS12',
            '-keystore', str(key), '-storepass:env', 'KAI_KEYSTORE_PASSWORD',
            '-alias', 'cantonesemixeng'], capture_output=True, check=True)
        fingerprint = hashlib.sha256(result.stdout).hexdigest()
        if fingerprint != args.expected_cert.read_text().strip().lower():
            raise ValueError('Signing certificate differs from the pinned persistent signer')
        if os.environ.get('GITHUB_ENV'):
            with Path(os.environ['GITHUB_ENV']).open('a') as out:
                out.write(f'KAI_KEYSTORE_PATH={key}\nKAI_REQUIRE_STABLE_SIGNING=true\n')
        print('Persistent signing certificate verified: ' + fingerprint)
        if not os.environ.get('GITHUB_ENV'):
            print('Verified key path: ' + str(key))
            print('Use this KAI_KEYSTORE_PATH and KAI_REQUIRE_STABLE_SIGNING=true for the build.')
    except Exception:
        if created:
            key.unlink(missing_ok=True)
        raise

if __name__ == '__main__':
    main()
