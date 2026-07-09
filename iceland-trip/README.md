# Iceland Trip

Standalone photo album + slideshow page, separate from the health app.

## Run it

```bash
cd iceland-trip
python3 -m http.server 8090
```

Then open http://127.0.0.1:8090 — serve it over http(s), don't just double-click
the file, since some browsers restrict IndexedDB on the `file://` origin.

## Notes

- Passphrase gate: default is `vatnajokull`, change the `PASSPHRASE` constant
  near the top of the `<script>` in `index.html`. It's a soft gate to keep
  casual visitors out, not real security — anyone with dev tools can read it.
- Photos are stored in the browser's IndexedDB (`iceland-trip-db`), so they
  persist across reloads but are local to that browser/device — clearing site
  data or using a different browser/device won't show them.
