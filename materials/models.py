from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class MaterialCategory(models.Model):
    """Material kategoriyalari"""
    
    name = models.CharField(max_length=100, verbose_name='Kategoriya nomi')
    description = models.TextField(blank=True, null=True, verbose_name='Tavsif')
    icon = models.CharField(max_length=50, blank=True, null=True, verbose_name='Ikona')
    
    class Meta:
        verbose_name = 'Material kategoriyasi'
        verbose_name_plural = 'Material kategoriyalari'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Material(models.Model):
    """Ta'lim materiallari"""
    
    MATERIAL_TYPE_CHOICES = [
        ('presentation', 'PPT taqdimot'),
        ('document', 'Word hujjat'),
        ('handout', 'Tarqatma material'),
        ('worksheet', 'Ish varaqasi'),
        ('test', 'Test'),
        ('methodology', 'Metodika'),
        ('fact', 'Qiziqarli fakt'),
        ('other', 'Boshqa'),
    ]
    
    title = models.CharField(max_length=200, verbose_name='Sarlavha')
    description = models.TextField(verbose_name='Tavsif')
    material_type = models.CharField(
        max_length=20,
        choices=MATERIAL_TYPE_CHOICES,
        verbose_name='Material turi'
    )
    category = models.ForeignKey(
        MaterialCategory,
        on_delete=models.CASCADE,
        related_name='materials',
        verbose_name='Kategoriya'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='materials',
        verbose_name='Muallif'
    )
    file = models.FileField(
        upload_to='materials/',
        verbose_name='Fayl'
    )
    thumbnail = models.ImageField(
        upload_to='material_thumbnails/',
        blank=True,
        null=True,
        verbose_name='Kichik rasm'
    )
    tags = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='Teglar (vergul bilan ajrating)'
    )
    grade_level = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Sinf darajasi'
    )
    is_public = models.BooleanField(
        default=True,
        verbose_name='Umumiy foydalanish'
    )
    download_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Yuklab olishlar soni'
    )
    rating = models.FloatField(
        default=0.0,
        verbose_name='Reyting'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Yaratilgan vaqt'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Yangilangan vaqt'
    )
    
    class Meta:
        verbose_name = 'Material'
        verbose_name_plural = 'Materiallar'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def get_tags_list(self):
        """Teglarni ro'yxat ko'rinishida qaytaradi"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',')]
        return []


class MaterialRating(models.Model):
    """Material reytinglari"""
    
    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name='ratings',
        verbose_name='Material'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='material_ratings',
        verbose_name='Foydalanuvchi'
    )
    rating = models.PositiveIntegerField(
        choices=[(i, i) for i in range(1, 6)],
        verbose_name='Reyting'
    )
    comment = models.TextField(
        blank=True,
        null=True,
        verbose_name='Izoh'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Yaratilgan vaqt'
    )
    
    class Meta:
        verbose_name = 'Material reytingi'
        verbose_name_plural = 'Material reytinglari'
        unique_together = ['material', 'user']
    
    def __str__(self):
        return f"{self.material.title} - {self.user.get_full_name()} ({self.rating})"


class MaterialDownload(models.Model):
    """Material yuklab olishlar tarixi"""
    
    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name='downloads',
        verbose_name='Material'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='material_downloads',
        verbose_name='Foydalanuvchi'
    )
    downloaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Yuklab olingan vaqt'
    )
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name='IP manzil'
    )
    
    class Meta:
        verbose_name = 'Material yuklab olish'
        verbose_name_plural = 'Material yuklab olishlar'
        ordering = ['-downloaded_at']
    
    def __str__(self):
        return f"{self.material.title} - {self.user.get_full_name()}"