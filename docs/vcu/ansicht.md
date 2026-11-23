# 3D-Ansicht und interaktive Stückliste

Stand: DRAFT-Paket `rev-A3.1-DRAFT` (2026-11-23, Board unverändert seit A3). Beide Dateien sind
Kopien aus dem Paket (`scripts/kit export`), nicht von Hand bearbeitet. **DRAFT – nicht für die
Fertigung.**

## 3D-Modell

<script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/4.0.0/model-viewer.min.js"></script>
<model-viewer src="../../assets/rev-A3.1/board-view.glb" alt="RoverCore Rev 1, 3D-Ansicht der Platine"
  camera-controls touch-action="pan-y" shadow-intensity="0.6" exposure="1.1"
  camera-orbit="30deg 55deg auto" style="width:100%;height:520px;background:#f4f4f4"></model-viewer>

Ziehen dreht, Mausrad oder zwei Finger zoomen. Das Modell lädt etwa 6,7 MB; der Betrachter
([model-viewer](https://modelviewer.dev), Apache-2.0) kommt von Googles Hosted Libraries.

- Enthalten: Platine mit Lötstopplack und Bestückungsdruck, alle Bauteile mit KiCad-Bibliotheks-
  oder eigenem Modell. DNP-Teile fehlen, wie auf der bestückten Platine.
- **Fehlt:** J102 und J103 (Molex Micro-Fit 3.0). Ihre Herstellermodelle dürfen nicht weitergegeben
  werden (`restricted_3d_models` in `qa/verification.json`, Liste im Paket-Manifest unter
  `view_models`). Die Pads sind sichtbar, der Steckerkörper nicht.
- Kein Kupfer (Leiterbahnen, Flächen). Für Kupfer siehe die Gerber-Bilder im README.
- Datei herunterladen: [board-view.glb](../assets/rev-A3.1/board-view.glb).
  Für mechanische Arbeit ist `mechanical/board.step` aus dem Paket maßgebend; es wird nicht
  veröffentlicht, weil es die Herstellermodelle enthält.

## Interaktive Stückliste (iBOM)

[iBOM öffnen](../assets/rev-A3.1/ibom.html){ target=_blank } – Bauteile suchen, auf der Platine
hervorheben, Bestückung abhaken (InteractiveHtmlBom, aus dem Board erzeugt).

## Herkunft

| Datei | Quelle im Paket | SHA-256 (Anfang) |
|---|---|---|
| `assets/rev-A3.1/board-view.glb` | `mechanical/board-view.glb` | `137698dd44daa377` |
| `assets/rev-A3.1/ibom.html` | `assembly/ibom.html` | `bf5b600faf8ed12f` |

Paket erzeugt auf Commit `47dda5f` mit dem Kit-Stand, der danach als `4121937` committet wurde
(Template `db2a484`). Die KiCad-Quellen waren identisch mit
`rev-A3-DRAFT`; `scripts/kit compare-exports` fand alle 42 gemeinsamen Artefakte gleich.
Nach Änderungen am Board neu exportieren und beide Dateien gemeinsam ersetzen.
