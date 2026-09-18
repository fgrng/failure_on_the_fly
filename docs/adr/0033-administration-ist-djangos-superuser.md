---
status: accepted
---

# Administration ist Djangos Superuser, nicht eine Group

Die Administrator:in wird technisch durch `Konto.is_superuser` repräsentiert.
`Konto.save()` setzt dazu stets `is_staff`, damit der Django-Admin denselben
Status für Tür und Innenraum nutzt. Autor:in, Ausbilder:in und Forschende:r
bleiben permissionfreie Django-Groups nach ADR-0019.

Eine Datenmigration befördert die Mitglieder der ehemaligen Administrations-
Group zu Superusern und entfernt die Group. Diese Rechteausweitung ist
beabsichtigt; produktive Instanzen werden noch nicht betrieben.

Die Ko-Autorinnen-Regel liegt als benannte Konto-QuerySet-Methode vor: Sie
findet die jeweilige Fachrolle oder eine Administrator:in. So bleibt die
Ausnahme an einer Stelle, wie `sichtbar_fuer` in ADR-0019.

## Erwogene Optionen

- **Eigene `AdminSite` mit `has_permission()` gegen die Group** — verworfen.
  Das öffnet nur die Tür; permissionfreie Groups sehen danach keinen Admin-Inhalt.
- **Derselbe Group-Gate über den `default_site`-Haken von `AdminConfig`** —
  verworfen. Es hat dieselbe unvollständige Berechtigungssemantik und versteckt
  sie zusätzlich in Django-Konfiguration.
- **Django-Permissions an der Group** — verworfen. Das widerspricht der
  permissionfreien Rollenentscheidung und schafft eine zweite Rechtewahrheit.
- **`is_staff` per `m2m_changed` aus der Group ableiten** — verworfen. Ein
  Signal koppelt ein Türflag an eine gelöschte fachliche Rolle und lässt
  `is_superuser` und `is_staff` auseinanderlaufen.

## Folgen

- `manage.py createsuperuser` ist der idiomatische Bootstrap.
- Die Sidebar behandelt eine Administrator:in ohne Fachrolle nicht als
  Teilnehmer:in.
- Die Anwendung prüft Administration über `is_superuser`; die ehemalige Group
  existiert nicht mehr.
