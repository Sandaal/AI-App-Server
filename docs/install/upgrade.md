# Upgrade and uninstall

## Upgrade

1. **Back up first:** `aiapp backup /backups/before-upgrade` (see [Backups](../operate/backups.md)).
2. **Install the new version over the old one:** run the install script again (it fetches the latest release), or replace the binary. With Docker or Helm, change the image tag.
3. **Restart the server.** Apps, data and versions are kept; apps come back by themselves.
4. **Read the release notes** on the [Download](../download.md) page for anything to do by hand.

Check the version with `aiapp version`.

## Uninstall

| Installed with | Remove |
|---|---|
| Windows installer | delete `%LOCALAPPDATA%\Programs\aiapp` and remove it from your PATH; delete `%USERPROFILE%\.aiapp` to remove the data |
| macOS / Linux installer | delete `~/.local/bin/aiapp` (or `/usr/local/bin/aiapp`); delete `~/.aiapp` to remove the data |
| Linux service | `sudo systemctl disable --now aiapp`, delete `/etc/systemd/system/aiapp.service`, `/usr/local/bin/aiapp`, `/etc/aiapp` and `/var/lib/aiapp` |
| Docker | `docker rm -f aiapp`; `docker volume rm aiapp-data` removes the data |
| Helm | `helm uninstall ai`; delete the PersistentVolumeClaim to remove the data |

!!! warning
    Deleting the data folder deletes every app's documents, memory, jobs and audit log for good.
