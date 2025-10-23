from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, Http404
from django.db.models import Q
from django.utils import timezone
import os

from .models import (
    Material, MaterialCategory, MaterialRating, MaterialDownload,
    Assignment, StudentSubmission, VideoLesson, Model3D
)
from .serializers import (
    MaterialCategorySerializer,
    MaterialSerializer,
    MaterialRatingSerializer,
    AssignmentSerializer,
    StudentSubmissionSerializer,
    VideoLessonSerializer,
    Model3DSerializer
)


class MaterialCategoryListView(generics.ListAPIView):
    """Material kategoriyalari ro'yxati"""
    queryset = MaterialCategory.objects.all()
    serializer_class = MaterialCategorySerializer
    permission_classes = [permissions.AllowAny]


class MaterialListView(generics.ListCreateAPIView):
    """Materiallar ro'yxati va yaratish"""
    serializer_class = MaterialSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Material.objects.filter(is_public=True)
        
        # Filtrlash
        category = self.request.query_params.get('category')
        material_type = self.request.query_params.get('type')
        subject = self.request.query_params.get('subject')
        grade_level = self.request.query_params.get('grade')
        search = self.request.query_params.get('search')
        
        if category:
            queryset = queryset.filter(category_id=category)
        if material_type:
            queryset = queryset.filter(material_type=material_type)
        if subject:
            queryset = queryset.filter(author__subject=subject)
        if grade_level:
            queryset = queryset.filter(grade_level=grade_level)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(tags__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class MaterialDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Material tafsilotlari"""
    serializer_class = MaterialSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Material.objects.filter(
            Q(is_public=True) | Q(author=self.request.user)
        )


class MaterialCreateView(generics.CreateAPIView):
    """Yangi material yaratish"""
    serializer_class = MaterialSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class MaterialUpdateView(generics.UpdateAPIView):
    """Materialni yangilash"""
    serializer_class = MaterialSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Material.objects.filter(author=self.request.user)


class MaterialDeleteView(generics.DestroyAPIView):
    """Materialni o'chirish"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Material.objects.filter(author=self.request.user)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_material(request, pk):
    """Materialni yuklab olish"""
    material = get_object_or_404(Material, pk=pk)
    
    # Yuklab olish huquqini tekshirish
    if not material.is_public and material.author != request.user:
        return Response({
            'error': 'Bu materialni yuklab olish huquqingiz yo\'q'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        # Yuklab olish statistikasini yangilash
        material.download_count += 1
        material.save()
        
        # Yuklab olish tarixini saqlash
        MaterialDownload.objects.create(
            material=material,
            user=request.user,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        # Faylni yuklab olish
        if os.path.exists(material.file.path):
            with open(material.file.path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/octet-stream')
                response['Content-Disposition'] = f'attachment; filename="{material.title}.{material.file.name.split(".")[-1]}"'
                return response
        else:
            return Response({
                'error': 'Fayl topilmadi'
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        return Response({
            'error': 'Faylni yuklab olishda xatolik'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rate_material(request, pk):
    """Materialni baholash"""
    material = get_object_or_404(Material, pk=pk)
    
    rating_value = request.data.get('rating')
    comment = request.data.get('comment', '')
    
    if not rating_value or not (1 <= int(rating_value) <= 5):
        return Response({
            'error': 'Reyting 1 dan 5 gacha bo\'lishi kerak'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Mavjud reytingni yangilash yoki yangi yaratish
    rating, created = MaterialRating.objects.get_or_create(
        material=material,
        user=request.user,
        defaults={'rating': rating_value, 'comment': comment}
    )
    
    if not created:
        rating.rating = rating_value
        rating.comment = comment
        rating.save()
    
    # Material reytingini yangilash
    ratings = MaterialRating.objects.filter(material=material)
    avg_rating = sum(r.rating for r in ratings) / ratings.count()
    material.rating = avg_rating
    material.save()
    
    return Response({
        'message': 'Reyting muvaffaqiyatli saqlandi',
        'rating': MaterialRatingSerializer(rating).data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_materials(request):
    """Materiallarni qidirish"""
    query = request.query_params.get('q', '')
    category = request.query_params.get('category')
    material_type = request.query_params.get('type')
    subject = request.query_params.get('subject')
    grade_level = request.query_params.get('grade')
    
    queryset = Material.objects.filter(is_public=True)
    
    if query:
        queryset = queryset.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(tags__icontains=query)
        )
    
    if category:
        queryset = queryset.filter(category_id=category)
    if material_type:
        queryset = queryset.filter(material_type=material_type)
    if subject:
        queryset = queryset.filter(author__subject=subject)
    if grade_level:
        queryset = queryset.filter(grade_level=grade_level)
    
    # Natijalarni tartiblash
    sort_by = request.query_params.get('sort', '-created_at')
    queryset = queryset.order_by(sort_by)
    
    serializer = MaterialSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_materials(request):
    """Foydalanuvchining materiallari"""
    materials = Material.objects.filter(author=request.user).order_by('-created_at')
    serializer = MaterialSerializer(materials, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def material_stats(request):
    """Material statistikasi"""
    user = request.user
    
    total_materials = Material.objects.filter(author=user).count()
    total_downloads = sum(m.download_count for m in Material.objects.filter(author=user))
    avg_rating = Material.objects.filter(author=user).aggregate(
        avg_rating=models.Avg('rating')
    )['avg_rating'] or 0
    
    # Eng ko'p yuklab olingan materiallar
    popular_materials = Material.objects.filter(author=user).order_by('-download_count')[:5]
    
    return Response({
        'total_materials': total_materials,
        'total_downloads': total_downloads,
        'avg_rating': round(avg_rating, 2),
        'popular_materials': MaterialSerializer(popular_materials, many=True).data
    })


# ============ ASSIGNMENT VIEWS ============

class AssignmentListView(generics.ListCreateAPIView):
    """Topshiriqlar ro'yxati va yaratish"""
    serializer_class = AssignmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Assignment.objects.filter(is_active=True)
        
        # Filtrlash
        category = self.request.query_params.get('category')
        assignment_type = self.request.query_params.get('type')
        subject = self.request.query_params.get('subject')
        grade_level = self.request.query_params.get('grade')
        teacher = self.request.query_params.get('teacher')
        
        if category:
            queryset = queryset.filter(category_id=category)
        if assignment_type:
            queryset = queryset.filter(assignment_type=assignment_type)
        if subject:
            queryset = queryset.filter(subject=subject)
        if grade_level:
            queryset = queryset.filter(grade_level=grade_level)
        if teacher:
            queryset = queryset.filter(teacher_id=teacher)
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)


class AssignmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Topshiriq tafsilotlari"""
    serializer_class = AssignmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Assignment.objects.filter(
            Q(is_active=True) | Q(teacher=self.request.user)
        )


class StudentSubmissionListView(generics.ListCreateAPIView):
    """O'quvchi topshirig'lari ro'yxati"""
    serializer_class = StudentSubmissionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        assignment_id = self.request.query_params.get('assignment')
        if assignment_id:
            return StudentSubmission.objects.filter(assignment_id=assignment_id)
        return StudentSubmission.objects.none()
    
    def perform_create(self, serializer):
        serializer.save()


class StudentSubmissionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """O'quvchi topshirig'i tafsilotlari"""
    serializer_class = StudentSubmissionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return StudentSubmission.objects.all()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def grade_submission(request, pk):
    """O'quvchi ishini baholash"""
    submission = get_object_or_404(StudentSubmission, pk=pk)
    
    grade = request.data.get('grade')
    feedback = request.data.get('feedback', '')
    
    if not grade or not (0 <= int(grade) <= submission.assignment.max_points):
        return Response({
            'error': f'Ball 0 dan {submission.assignment.max_points} gacha bo\'lishi kerak'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    submission.grade = grade
    submission.feedback = feedback
    submission.status = 'graded'
    submission.graded_by = request.user
    submission.graded_at = timezone.now()
    submission.save()
    
    return Response({
        'message': 'Ish muvaffaqiyatli baholandi',
        'submission': StudentSubmissionSerializer(submission).data
    })


# ============ VIDEO LESSON VIEWS ============

class VideoLessonListView(generics.ListCreateAPIView):
    """Video darsliklar ro'yxati"""
    serializer_class = VideoLessonSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = VideoLesson.objects.filter(is_public=True)
        
        # Filtrlash
        category = self.request.query_params.get('category')
        subject = self.request.query_params.get('subject')
        grade_level = self.request.query_params.get('grade')
        search = self.request.query_params.get('search')
        
        if category:
            queryset = queryset.filter(category_id=category)
        if subject:
            queryset = queryset.filter(subject=subject)
        if grade_level:
            queryset = queryset.filter(grade_level=grade_level)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(tags__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class VideoLessonDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Video darslik tafsilotlari"""
    serializer_class = VideoLessonSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return VideoLesson.objects.filter(
            Q(is_public=True) | Q(author=self.request.user)
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def watch_video(request, pk):
    """Video ko'rish statistikasini yangilash"""
    video = get_object_or_404(VideoLesson, pk=pk)
    
    if not video.is_public and video.author != request.user:
        return Response({
            'error': 'Bu videoni ko\'rish huquqingiz yo\'q'
        }, status=status.HTTP_403_FORBIDDEN)
    
    video.view_count += 1
    video.save()
    
    return Response({
        'message': 'Video ko\'rish statistikasi yangilandi',
        'view_count': video.view_count
    })


# ============ 3D MODEL VIEWS ============

class Model3DListView(generics.ListCreateAPIView):
    """3D modellar ro'yxati"""
    serializer_class = Model3DSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Model3D.objects.filter(is_public=True)
        
        # Filtrlash
        category = self.request.query_params.get('category')
        model_type = self.request.query_params.get('type')
        subject = self.request.query_params.get('subject')
        grade_level = self.request.query_params.get('grade')
        is_interactive = self.request.query_params.get('interactive')
        search = self.request.query_params.get('search')
        
        if category:
            queryset = queryset.filter(category_id=category)
        if model_type:
            queryset = queryset.filter(model_type=model_type)
        if subject:
            queryset = queryset.filter(subject=subject)
        if grade_level:
            queryset = queryset.filter(grade_level=grade_level)
        if is_interactive:
            queryset = queryset.filter(is_interactive=True)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class Model3DDetailView(generics.RetrieveUpdateDestroyAPIView):
    """3D model tafsilotlari"""
    serializer_class = Model3DSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Model3D.objects.filter(
            Q(is_public=True) | Q(author=self.request.user)
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_3d_model(request, pk):
    """3D modelni yuklab olish"""
    model = get_object_or_404(Model3D, pk=pk)
    
    if not model.is_public and model.author != request.user:
        return Response({
            'error': 'Bu modelni yuklab olish huquqingiz yo\'q'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        # Yuklab olish statistikasini yangilash
        model.download_count += 1
        model.save()
        
        # Faylni yuklab olish
        if os.path.exists(model.model_file.path):
            with open(model.model_file.path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/octet-stream')
                response['Content-Disposition'] = f'attachment; filename="{model.title}.{model.model_file.name.split(".")[-1]}"'
                return response
        else:
            return Response({
                'error': 'Fayl topilmadi'
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        return Response({
            'error': 'Faylni yuklab olishda xatolik'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)