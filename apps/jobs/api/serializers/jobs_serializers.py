from rest_framework import serializers


class JobSqlServerSerializer(serializers.Serializer):
    
    def validate(self, data):
        return data
  