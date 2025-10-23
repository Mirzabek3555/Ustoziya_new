from rest_framework import serializers
from .models import Material, MaterialCategory, MaterialRating, MaterialDownload


class MaterialCategorySerializer(serializers.ModelSerializer):
    """Material kategoriya serializeri"""
    
    materials_count = serializers.SerializerMethodField()
    
    class Meta:
        model = MaterialCategory
        fields = ['id', 'name', 'description', 'icon', 'materials_count']
    
    def get_materials_count(self, obj):
        """Kategoriyadagi materiallar soni"""
        return obj.materials.filter(is_public=True).count()


class MaterialSerializer(serializers.ModelSerializer):
    """Material serializeri"""
    
    author_name = serializers.SerializerMethodField()
    author_subject = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    tags_list = serializers.SerializerMethodField()
    material_type_display = serializers.SerializerMethodField()
    ratings_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Material
        fields = [
            'id', 'title', 'description', 'material_type', 'material_type_display',
            'category', 'category_name', 'author', 'author_name', 'author_subject',
            'file', 'file_url', 'thumbnail', 'thumbnail_url', 'tags', 'tags_list',
            'grade_level', 'is_public', 'download_count', 'rating', 'ratings_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'author', 'download_count', 'rating', 'created_at', 'updated_at']
    
    def get_author_name(self, obj):
        """Muallif nomini qaytaradi"""
        return obj.author.get_full_name()
    
    def get_author_subject(self, obj):
        """Muallif fanini qaytaradi"""
        return obj.author.get_subject_display()
    
    def get_category_name(self, obj):
        """Kategoriya nomini qaytaradi"""
        return obj.category.name if obj.category else None
    
    def get_file_url(self, obj):
        """Fayl URL ini qaytaradi"""
        if obj.file:
            return obj.file.url
        return None
    
    def get_thumbnail_url(self, obj):
        """Kichik rasm URL ini qaytaradi"""
        if obj.thumbnail:
            return obj.thumbnail.url
        return None
    
    def get_tags_list(self, obj):
        """Teglarni ro'yxat ko'rinishida qaytaradi"""
        return obj.get_tags_list()
    
    def get_material_type_display(self, obj):
        """Material turi nomini qaytaradi"""
        return obj.get_material_type_display()
    
    def get_ratings_count(self, obj):
        """Reytinglar soni"""
        return obj.ratings.count()


class MaterialRatingSerializer(serializers.ModelSerializer):
    """Material reyting serializeri"""
    
    user_name = serializers.SerializerMethodField()
    material_title = serializers.SerializerMethodField()
    
    class Meta:
        model = MaterialRating
        fields = [
            'id', 'material', 'material_title', 'user', 'user_name',
            'rating', 'comment', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']
    
    def get_user_name(self, obj):
        """Foydalanuvchi nomini qaytaradi"""
        return obj.user.get_full_name()
    
    def get_material_title(self, obj):
        """Material sarlavhasini qaytaradi"""
        return obj.material.title


class MaterialDownloadSerializer(serializers.ModelSerializer):
    """Material yuklab olish serializeri"""
    
    user_name = serializers.SerializerMethodField()
    material_title = serializers.SerializerMethodField()
    
    class Meta:
        model = MaterialDownload
        fields = [
            'id', 'material', 'material_title', 'user', 'user_name',
            'downloaded_at', 'ip_address'
        ]
        read_only_fields = ['id', 'downloaded_at']
    
    def get_user_name(self, obj):
        """Foydalanuvchi nomini qaytaradi"""
        return obj.user.get_full_name()
    
    def get_material_title(self, obj):
        """Material sarlavhasini qaytaradi"""
        return obj.material.title


class MaterialCreateSerializer(serializers.ModelSerializer):
    """Material yaratish serializeri"""
    
    class Meta:
        model = Material
        fields = [
            'title', 'description', 'material_type', 'category',
            'file', 'thumbnail', 'tags', 'grade_level', 'is_public'
        ]
    
    def validate_file(self, value):
        """Fayl hajmini tekshirish"""
        if value.size > 50 * 1024 * 1024:  # 50MB
            raise serializers.ValidationError("Fayl hajmi 50MB dan katta bo'lmasligi kerak")
        return value
    
    def validate_tags(self, value):
        """Teglarni tozalash"""
        if value:
            # Vergul bilan ajratilgan tegni tozalash
            tags = [tag.strip() for tag in value.split(',') if tag.strip()]
            return ', '.join(tags)
        return value
