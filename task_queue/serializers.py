from rest_framework import serializers

class ImageConversionSerializer(serializers.Serializer):
    openid = serializers.CharField()
    prompt = serializers.CharField()
    base64_image = serializers.CharField()