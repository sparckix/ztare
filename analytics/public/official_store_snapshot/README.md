# official_store_snapshot/

Read-only disaster-recovery copy of the daemon-owned
`/srv/ztare_official_store` from the VPS. Taken periodically by
`deploy/vps_pull.sh`. Never fed back as authority — the live store is
on the VPS, this is the local mirror.

Re-included for git tracking via the `!analytics/public/official_store_snapshot/`
exception in `.gitignore` because the publication surface needs to show
*what was authoritative at snapshot time*, not just the apparatus code.
