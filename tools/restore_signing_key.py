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
    if not encoded or not password:
        raise SystemExit('Set repository secrets KAI_KEYSTORE_B64 and KAI_KEYSTORE_PASSWORD. Refusing a temporary APK signer.')
    os.environ['KAI_KEYSTORE_PASSWORD'] = password
    data = base64.b64decode(encoded.strip(), validate=True)
    if not 1000 <= len(data) <= 32768:
        raise SystemExit('Invalid keystore size')
    key = Path(os.environ['RUNNER_TEMP']) / 'cantonesemixeng-signing.p12'
    key.write_bytes(data)
    key.chmod(0o600)
    try:
        result = subprocess.run(['keytool', '-exportcert', '-storetype', 'PKCS12',
            '-keystore', str(key), '-storepass:env', 'KAI_KEYSTORE_PASSWORD',
            '-alias', 'cantonesemixeng'], capture_output=True, check=True)
        fingerprint = hashlib.sha256(result.stdout).hexdigest()
        if fingerprint != args.expected_cert.read_text().strip().lower():
            raise ValueError('Signing certificate differs from the pinned persistent signer')
        with Path(os.environ['GITHUB_ENV']).open('a') as out:
            out.write(f'KAI_KEYSTORE_PATH={key}\nKAI_REQUIRE_STABLE_SIGNING=true\n')
        print('Persistent signing certificate verified: ' + fingerprint)
    except Exception:
        key.unlink(missing_ok=True)
        raise

if __name__ == '__main__':
    main()
