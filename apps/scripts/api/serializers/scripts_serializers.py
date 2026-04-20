from rest_framework import serializers
from datetime import date
import calendar as cal

class ScriptSqlServerSerializer(serializers.Serializer):
    path = serializers.CharField(
        required=True,
        allow_null=False,
        allow_blank=False,
        error_messages={
            "invalid": "La ruta no es válida",
            "required": "La ruta es requerida",
            "blank": "La ruta no puede estar vacía",
            "null": "La ruta no puede ser nula",
        }
    )

    year = serializers.IntegerField(
        required=False,
        min_value=2000,
        max_value=2100,
        error_messages={
            "invalid": "El año debe ser un número",
            "min_value": "El año debe ser mayor o igual a 2000",
            "max_value": "El año debe ser menor o igual a 2100",
        }
    )

    month = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=12,
        error_messages={
            "invalid": "El mes debe ser un número",
            "min_value": "El mes debe estar entre 1 y 12",
            "max_value": "El mes debe estar entre 1 y 12",
        }
    )

    day = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=31,
        error_messages={
            "invalid": "El día debe ser un número",
            "min_value": "El día debe estar entre 1 y 31",
            "max_value": "El día debe estar entre 1 y 31",
        }
    )

    #  Validación cruzada (importante)
    def validate(self, data):
        today = date.today()

        year = data.get("year", today.year)
        month = data.get("month", today.month)
        day = data.get("day", today.day)

        # validar día real del mes
        _, last_day = cal.monthrange(year, month)

        if day > last_day:
            raise serializers.ValidationError({
                "day": f"El día no es válido para el mes {month} del año {year}"
            })

        return data