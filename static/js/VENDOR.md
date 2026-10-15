# Vendorte Bibliotheken

htmx und Alpine liegen lokal in diesem Verzeichnis statt per CDN (ADR-0023).
Beide Dateien sind byteidentisch mit der Datei aus dem npm-Paket der genannten
Version. Die übrigen Dateien hier sind eigener Code.

## htmx

- Datei: `htmx.min.js`
- Version: 2.0.11
- Quelle: npm-Paket `htmx.org@2.0.11`, Pfad `dist/htmx.min.js`
  (<https://registry.npmjs.org/htmx.org/-/htmx.org-2.0.11.tgz>)
- Übernommen: 2026-10-15

## Alpine

- Datei: `alpine.min.js`
- Version: 3.17.4
- Quelle: npm-Paket `alpinejs@3.17.4`, Pfad `dist/cdn.min.js`
  (<https://registry.npmjs.org/alpinejs/-/alpinejs-3.17.4.tgz>)
- Übernommen: 2026-10-15

## Prüfsummen

SHA-256 im Format von `sha256sum`. `config/tests/test_vendor.py` liest diesen
Block und schlägt fehl, wenn eine Datei nicht passt.

```text
d6fdc75f204e6bdefa99b69bf1e6d4ac69b8a364f77929f45c13476b4000f717  htmx.min.js
232519394c6c8fdba6f362b1d9da16106db513cdbf899011f00daab4051df31c  alpine.min.js
```

## Aktualisieren

Neue Version im Befehl einsetzen, im Repo-Wurzelverzeichnis ausführen, dann
Version, Quelle, Datum und den Prüfsummenblock oben nachführen. Vorher die
Release-Notes auf geändertes Verhalten prüfen und die Templates nachziehen.

```sh
tmp=$(mktemp -d)
npm pack htmx.org@2.0.11 alpinejs@3.17.4 --ignore-scripts --silent --pack-destination "$tmp"
for t in "$tmp"/*.tgz; do tar -xzf "$t" -C "$tmp" --transform "s|^package|$(basename "$t" .tgz)|"; done
cp "$tmp"/htmx.org-*/dist/htmx.min.js static/js/htmx.min.js
cp "$tmp"/alpinejs-*/dist/cdn.min.js static/js/alpine.min.js
(cd static/js && sha256sum htmx.min.js alpine.min.js)
```

Prüfen ohne Test:
`(cd static/js && sed -n '/^[0-9a-f]\{64\}  /p' VENDOR.md | sha256sum -c)`.
