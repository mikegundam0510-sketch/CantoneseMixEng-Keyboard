# Persistent APK signing

All distributed APKs must keep applicationId `hk.kaiboard.android`, use the
pinned signing certificate and increase `versionCode` for every release.
An ordinary in-place update preserves app settings and learning preferences;
uninstalling or clearing app data removes them.

## One-time repository setup

Keep the `cantonesemixeng-persistent-signing-backup.zip` backup securely.
It contains the PKCS12 private key and its password. Do not commit its contents.
In GitHub → repository Settings → Secrets and variables → Actions, add:

- `KAI_KEYSTORE_B64`: the contents of `KAI_KEYSTORE_B64.txt` in the backup.
- `KAI_KEYSTORE_PASSWORD`: the contents of `KAI_KEYSTORE_PASSWORD.txt`.

Re-run Combined APK after configuring both secrets. The workflow restores the
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
