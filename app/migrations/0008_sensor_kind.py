from django.db import migrations, models


def set_kind_from_name(apps, schema_editor):
    """Sensors added before this field existed: infer the type from the name they were saved with."""
    Sensor = apps.get_model('app', 'Sensor')
    for sensor in Sensor.objects.all():
        upper = (sensor.name or '').upper()
        if 'BEACON' in upper:
            sensor.kind = 'MOKO'
        elif 'MST' in upper:
            sensor.kind = 'MST01'
        else:
            continue
        sensor.save(update_fields=['kind'])


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0007_alter_datasensor_humidity_alter_datasensor_pressure_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='sensor',
            name='kind',
            field=models.CharField(blank=True, default='', max_length=10),
        ),
        migrations.RunPython(set_kind_from_name, migrations.RunPython.noop),
    ]
