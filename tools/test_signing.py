"""Exercise restore/identity checks using disposable keys, never the release key."""
import base64
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class SigningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.temp.name)
        cls.key = cls.directory / 'fixture.p12'
        cls.password = 'disposable-test-password'
        cls.environment = dict(os.environ, KAI_KEYSTORE_PATH=str(cls.key),
            KAI_KEYSTORE_PASSWORD=cls.password, RUNNER_TEMP=str(cls.directory))
        cls.environment.pop('KAI_KEYSTORE_B64', None)
        cls.environment.pop('GITHUB_ENV', None)
        subprocess.run(['keytool', '-genkeypair', '-storetype', 'PKCS12', '-keystore', str(cls.key),
            '-storepass:env', 'KAI_KEYSTORE_PASSWORD', '-alias', 'cantonesemixeng', '-keyalg', 'RSA',
            '-keysize', '2048', '-validity', '1', '-dname', 'CN=Disposable test'],
            env=cls.environment, capture_output=True, check=True)
        certificate = subprocess.run(['keytool', '-exportcert', '-storetype', 'PKCS12', '-keystore', str(cls.key),
            '-storepass:env', 'KAI_KEYSTORE_PASSWORD', '-alias', 'cantonesemixeng'],
            env=cls.environment, capture_output=True, check=True).stdout
        cls.expected = cls.directory / 'fixture.sha256'
        cls.expected.write_text(hashlib.sha256(certificate).hexdigest() + '\n')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def restore(self, environment, expected=None):
        args = ['python3', str(ROOT / 'tools/restore_signing_key.py')]
        if expected:
            args += ['--expected-cert', str(expected)]
        return subprocess.run(args, env=environment, capture_output=True, text=True)

    def test_existing_local_key_verified_and_preserved(self):
        result = self.restore(self.environment, self.expected)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(self.key.is_file())

    def test_wrong_certificate_rejected_without_deleting_user_key(self):
        result = self.restore(self.environment)
        self.assertNotEqual(0, result.returncode)
        self.assertTrue(self.key.is_file())

    def test_missing_key_fails_closed(self):
        environment = dict(self.environment)
        environment.pop('KAI_KEYSTORE_PATH')
        self.assertNotEqual(0, self.restore(environment).returncode)

    def test_encoded_actions_key_verified_and_exports_stable_requirement(self):
        environment = dict(self.environment, KAI_KEYSTORE_B64=base64.b64encode(self.key.read_bytes()).decode())
        environment.pop('KAI_KEYSTORE_PATH')
        output = self.directory / 'actions.env'
        environment['GITHUB_ENV'] = str(output)
        result = self.restore(environment, self.expected)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('KAI_REQUIRE_STABLE_SIGNING=true', output.read_text())

    def test_wrong_encoded_key_is_removed(self):
        environment = dict(self.environment, KAI_KEYSTORE_B64=base64.b64encode(self.key.read_bytes()).decode())
        environment.pop('KAI_KEYSTORE_PATH')
        before = set(self.directory.glob('cantonesemixeng-signing-*.p12'))
        self.assertNotEqual(0, self.restore(environment).returncode)
        self.assertEqual(before, set(self.directory.glob('cantonesemixeng-signing-*.p12')))

    def test_gradle_rejects_wrong_persistent_signer(self):
        result = subprocess.run(['bash', './gradlew', 'help', '--no-daemon', '--max-workers=2'],
            cwd=ROOT, env=self.environment, capture_output=True, text=True)
        self.assertNotEqual(0, result.returncode)
        self.assertIn('Signing certificate differs from the pinned persistent signer', result.stdout + result.stderr)

    def test_release_cannot_package_without_original_key(self):
        environment = dict(self.environment)
        environment.pop('KAI_KEYSTORE_PATH')
        environment.pop('KAI_KEYSTORE_PASSWORD')
        environment.pop('KAI_REQUIRE_STABLE_SIGNING', None)
        result = subprocess.run(['bash', './gradlew', 'assembleRelease', '-PkaiKeystorePath=', '--no-daemon', '--max-workers=2'],
            cwd=ROOT, env=environment, capture_output=True, text=True)
        self.assertNotEqual(0, result.returncode)
        self.assertIn('Release packaging requires the pinned persistent signing key', result.stdout + result.stderr)

if __name__ == '__main__':
    unittest.main()
