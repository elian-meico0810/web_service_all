from rest_framework import serializers

class ExtraFieldSerializer(serializers.Serializer):
    callback_to_representation= None
    def __init__(self, *args, **kwargs):
      self.callback_to_representation = kwargs.pop('callback_to_representation',None)
      super(ExtraFieldSerializer, self).__init__(*args, **kwargs)

    def to_representation(self, instance):
        return self.callback_to_representation(instance) if self.callback_to_representation is not None else None

    def to_internal_value(self, data):
        return {
          self.field_name:data
        }
class SerializerExtraField(serializers.Serializer):
    callback_to_representation= None
    def __init__(self, *args, **kwargs):
      self.callback_to_representation = kwargs.pop('callback_to_representation',None)
      super(SerializerExtraField, self).__init__(*args, **kwargs)

    def to_representation(self, instance):
        return self.callback_to_representation(instance) if self.callback_to_representation is not None else None

    def to_internal_value(self, data):

        return data


class EagerLoadingMixin:
    @classmethod
    def setup_eager_loading(cls, queryset):
        """
        This function allow dynamic addition of the related objects to
        the provided query.
        @parameter param1: queryset
        """

        if hasattr(cls, "select_related_fields"):
            queryset = queryset.select_related(*cls.select_related_fields)
        if hasattr(cls, "prefetch_related_fields"):
            queryset = queryset.prefetch_related(*cls.prefetch_related_fields)
        return queryset

