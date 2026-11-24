# Backups and restore

## Back up (while the server runs)

```bash
aiapp backup /backups/2026-11-23
```

This is a consistent copy of every app's data, versions and the audit log, still encrypted. The **master key is not included** unless you add `--include-key`; keep it somewhere else (a password manager, a vault, a Kubernetes Secret).

Schedule it, for example with cron:

```cron
0 3 * * * aiapp backup /backups/$(date +\%F) && find /backups -maxdepth 1 -mtime +14 -exec rm -rf {} +
```

## Restore

With the server **stopped**, into an **empty** data folder:

```bash
aiapp restore /backups/2026-11-23 --data-dir /new/data
cp /safe/place/master.key /new/data/master.key     # if the backup doesn't include it
aiapp serve --data-dir /new/data
```

## The master key

- It is `master.key` in the data folder, created on first start.
- Without it, data and backups can't be read. Losing it means losing the data.
- On Kubernetes, keep it in a Secret (`masterKey.existingSecret` in the Helm values), so volume snapshots don't contain it.
- `AIAPP_MASTER_KEY_FILE` points the server at a key stored elsewhere.

## Test your restores

Restore to a spare machine now and then, start the server, and run `aiapp apps` and a question to each app.
