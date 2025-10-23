from rest_framework import serializers
from apps.base.extensions.general_serializers import EagerLoadingMixin

#serializers de web service a Sql Server
class ScriptSqlServerSerializer(serializers.Serializer, EagerLoadingMixin):
    path = serializers.CharField(
        required=True,
        allow_null=False,
        allow_blank=False,
        error_messages={
            "invalid": "La ruta relativa no es válido",
            "required": "La ruta relativa es requerido",
            "blank": "La ruta relativa no puede estar vacío",
            "null": "La ruta relativa no puede ser nulo",
        }
    )
    

