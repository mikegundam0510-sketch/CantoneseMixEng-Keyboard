# Persistent APK signing

All distributed APKs must keep applicationId `hk.kaiboard.android`, use the
pinned signing certificate and increase `versionCode` for every release.
An ordinary in-place update preserves app settings and learning preferences;
uninstalling or clearing app data removes them.

## One-time repository setup

Keep the `cantonesemixeng-persistent-signing-backup-0.6.19.zip` backup securely.
It contains the PKCS12 private key and its password. Do not commit its contents.
In GitHub → repository Settings → Secrets and variables → Actions, add:

- `KAI_KEYSTORE_B64`: the contents of `KAI_KEYSTORE_B64.txt` in the backup.
- `KAI_KEYSTORE_PASSWORD`: the contents of `KAI_KEYSTORE_PASSWORD.txt`.

Replace any old signing-secret values with this new 0.6.19 backup, then run Combined signed APK. The workflow restores the
same key into runner temporary storage, checks the public certificate fingerprint,
and signs app and test APKs with it. Missing secrets or another key fail the build
instead of publishing an APK with a temporary signature. Other existing APK
workflows use the same restore step.

Certificate SHA-256 is pinned in `.github/signing-cert.sha256`. That file is
public certificate metadata, not a private key. The alias is `cantonesemixeng`.
The encrypted private keystore remains in the backup and repository secrets.

## Existing installations

Previous builds generated a fresh debug key on each runner. No old private key
was found in the repository or its packaging workflow. The new persistent key
cannot update an APK signed with an old debug key. Recovering the APK's public
certificate does not recover its private key.

If the original private key cannot be recovered, the first persistent-key APK
requires an uninstall/reinstall and existing app data cannot be promised to survive.
Subsequent releases keep this persistent key and can update that installation.
Do not uninstall an existing installation expecting the new key to preserve its data.

## Local builds

Set `KAI_KEYSTORE_PATH` to the retained `.p12` and `KAI_KEYSTORE_PASSWORD` to its
password. Set `KAI_REQUIRE_STABLE_SIGNING=true` for distribution builds. Both
debug and release build types then use the persistent signer. A local development
build without these settings may use Android's temporary debug key; do not
distribute it as an update.

Android reference: https://developer.android.com/studio/publish/app-signing
GitHub reference: https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets

## 0.6.19 signing baseline

The previous 0.6.18 private key could not be recovered. At the user's request,
0.6.19 establishes a new persistent certificate:
`78c3bd69b5625c63b3dff5357681154f063020a49c5b862fdfa9fed575fccb63`.
The old pinned public certificate was
`345d5db4540e0d44c06223c129abeb07c476e0c9a95ae5d8dea71fc99529af14`;
its public certificate cannot recover the private key.

This first transition cannot update an installation signed by that old key.
It may require reinstalling and prior learning cannot be promised to survive.
From the new 0.6.19 installation onward, retain this new key for in-place updates.
The application ID and preference formats remain unchanged; version code is 26
and must increase for future releases.

Local Gradle builds now verify the certificate as well as the Actions restore
step. Release packaging fails when this retained key is absent. Validate an
existing local key without printing its password:

```sh
python3 tools/restore_signing_key.py
KAI_REQUIRE_STABLE_SIGNING=true bash ./gradlew testDebugUnitTest lintDebug assembleDebug --no-daemon --max-workers=2
python3 tools/verify_apk_signing.py app/build/outputs/apk/debug/app-debug.apk
```

Provide `KAI_KEYSTORE_PATH` and `KAI_KEYSTORE_PASSWORD` through a secure local
binding beforehand, or reuse the existing GitHub Actions secrets and dispatch
**Combined signed APK** on the branch containing these changes. Never put the
password or base64 private key in source control, chat text, or build logs.
The verification workflow restores the retained key and checks the APK signer
before upload. A development APK with a temporary debug key is not an update.

In this prepared cloud machine, the private key and password remain outside
the checkout under `/workspace/keyboard-release-signing/`. The retained Gradle
user properties contain only key/password-file paths and automatically reuse
the signer for debug and release builds. The private backup archive contains
the key and password: download it, retain it securely and never publish it.
The cloud snapshot alone is not an independent key backup. If the key is missing
in a later machine, restore this archive; do not generate a replacement key.
