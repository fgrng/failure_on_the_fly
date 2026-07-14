"""Initiale Persistenzmodelle der Sitzungen."""

# Erzeugt von Django 6.0.7 am 2026-07-14 08:33.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Legt die anfänglichen Tabellen der Sitzungs-Persistenz an."""

    initial = True

    dependencies = [
        ('simulation', '0002_modellkonfiguration_aktivemodellkonfiguration'),
        ('vignetten', '0002_alter_vignette_arbeitsheft_bild'),
    ]

    operations = [
        migrations.CreateModel(
            name='Gespraechsschritt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('eingabe', models.TextField()),
                ('denkspur', models.TextField(blank=True, null=True)),
                ('aeusserung', models.TextField(blank=True, null=True)),
                ('native_reasoning_spur', models.TextField(blank=True, null=True)),
                ('reihenfolge', models.PositiveIntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='Teilnahme',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='Fehlversuch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('grund', models.TextField()),
                ('rohantwort', models.TextField()),
                ('gespraechsschritt', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sitzungen.gespraechsschritt')),
            ],
        ),
        migrations.CreateModel(
            name='Sitzung',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('laufend', 'Laufend'), ('abgeschlossen', 'Abgeschlossen'), ('abgebrochen', 'Abgebrochen'), ('gescheitert', 'Gescheitert')], default='laufend', max_length=13)),
                ('modell_konfiguration', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='simulation.modellkonfiguration')),
                ('simulationskern', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='simulation.simulationskern')),
                ('vignette', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='vignetten.vignette')),
                ('teilnahme', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sitzungen.teilnahme')),
            ],
        ),
        migrations.AddField(
            model_name='gespraechsschritt',
            name='sitzung',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sitzungen.sitzung'),
        ),
        migrations.CreateModel(
            name='Diagnose',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField()),
                ('sitzung', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='sitzungen.sitzung')),
            ],
        ),
        migrations.AddConstraint(
            model_name='gespraechsschritt',
            constraint=models.UniqueConstraint(fields=('sitzung', 'reihenfolge'), name='sitzungen_reihenfolge_ist_je_sitzung_eindeutig'),
        ),
        migrations.AddConstraint(
            model_name='gespraechsschritt',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('aeusserung__isnull', False), ('denkspur__isnull', False)), models.Q(('aeusserung__isnull', True), ('denkspur__isnull', True)), _connector='OR'), name='sitzungen_antwort_hat_denkspur_und_aeusserung_oder_keine'),
        ),
    ]
