from rest_framework import serializers

from .models import Collection


class CollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = ("id", "name", "owner", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at", "owner")

    def validate(self, attrs):
        request = self.context.get("request")
        if request is None:
            raise serializers.ValidationError("Request context is required.")

        name = attrs.get("name", self.instance.name if self.instance else None)
        if name is None:
            # name не передан (PATCH без name) — проверять нечего
            return attrs

        owner = request.user

        qs = Collection.objects.filter(owner=owner, name=name)
        if self.instance is not None:
            # при PATCH/PUT исключаем текущий объект из проверки
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError(
                {"name": "Collection with this name already exists."}
            )

        return attrs
