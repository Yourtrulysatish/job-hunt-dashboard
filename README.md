# Job hunt dashboard

A static page that lists roles in Northern Europe and remote roles open to Europe, with a tracker for status, next steps and notes.

- `index.html`, `app.js`: the page. Statuses and notes are saved only in the visitor's browser (localStorage). Use Backup and Restore to move them between devices.
- `data/jobs.json`: roles that were read posting by posting.
- `data/scan.json`: the daily scan, rebuilt by `.github/workflows/refresh.yml` every morning from public job feeds and company job boards. These roles are not checked by hand.
- `scripts/`: the scan scripts.

Open it at https://yourtrulysatish.github.io/job-hunt-dashboard/
