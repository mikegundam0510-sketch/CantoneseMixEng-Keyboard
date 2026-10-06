"""Verify an APK's cryptographic signature and the pinned update identity."""
import argparse
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('apk', type=Path)
    args = parser.parse_args()
    sdk = os.environ.get('ANDROID_HOME') or os.environ.get('ANDROID_SDK_ROOT')
    if not sdk:
        raise SystemExit('ANDROID_HOME is required')
    result = subprocess.run([str(Path(sdk) / 'build-tools/35.0.0/apksigner'),
        'verify', '--verbose', '--print-certs', str(args.apk)], capture_output=True, text=True, check=True)
    signers = re.findall(r'^Signer #\d+ certificate SHA-256 digest: ([0-9a-fA-F]+)$', result.stdout, re.M)
    expected = (ROOT / '.github/signing-cert.sha256').read_text().strip().lower()
    if [s.lower() for s in signers] != [expected]:
        raise SystemExit('APK signer differs from the pinned persistent certificate. Do not distribute as an update.')
    print('APK signature and persistent update identity verified: ' + expected)

if __name__ == '__main__':
    main()
