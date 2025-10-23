from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone

from .models import Test, Question, Answer, TestAttempt, StudentAnswer, TestCategory
from .serializers import (
    TestCategorySerializer,
    TestSerializer,
    QuestionSerializer,
    AnswerSerializer,
    TestAttemptSerializer,
    StudentAnswerSerializer
)


class TestCategoryListView(generics.ListAPIView):
    """Test kategoriyalari ro'yxati"""
    queryset = TestCategory.objects.all()
    serializer_class = TestCategorySerializer
    permission_classes = [permissions.AllowAny]


class TestListView(generics.ListCreateAPIView):
    """Testlar ro'yxati va yaratish"""
    serializer_class = TestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Test.objects.filter(is_public=True, is_active=True)
        
        # Filtrlash
        category = self.request.query_params.get('category')
        subject = self.request.query_params.get('subject')
        grade_level = self.request.query_params.get('grade')
        difficulty = self.request.query_params.get('difficulty')
        search = self.request.query_params.get('search')
        
        if category:
            queryset = queryset.filter(category_id=category)
        if subject:
            queryset = queryset.filter(subject=subject)
        if grade_level:
            queryset = queryset.filter(grade_level=grade_level)
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class TestDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Test tafsilotlari"""
    serializer_class = TestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Test.objects.filter(
            Q(is_public=True) | Q(author=self.request.user)
        )


class TestCreateView(generics.CreateAPIView):
    """Yangi test yaratish"""
    serializer_class = TestSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class TestUpdateView(generics.UpdateAPIView):
    """Testni yangilash"""
    serializer_class = TestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Test.objects.filter(author=self.request.user)


class TestDeleteView(generics.DestroyAPIView):
    """Testni o'chirish"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Test.objects.filter(author=self.request.user)


class QuestionListView(generics.ListCreateAPIView):
    """Test savollari ro'yxati"""
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        test_id = self.kwargs['pk']
        test = get_object_or_404(Test, pk=test_id, author=self.request.user)
        return Question.objects.filter(test=test).order_by('order')
    
    def perform_create(self, serializer):
        test_id = self.kwargs['pk']
        test = get_object_or_404(Test, pk=test_id, author=self.request.user)
        serializer.save(test=test)


class QuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Savol tafsilotlari"""
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Question.objects.filter(test__author=self.request.user)


class QuestionCreateView(generics.CreateAPIView):
    """Yangi savol yaratish"""
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        test_id = self.kwargs['pk']
        test = get_object_or_404(Test, pk=test_id, author=self.request.user)
        serializer.save(test=test)


class QuestionUpdateView(generics.UpdateAPIView):
    """Savolni yangilash"""
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Question.objects.filter(test__author=self.request.user)


class QuestionDeleteView(generics.DestroyAPIView):
    """Savolni o'chirish"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Question.objects.filter(test__author=self.request.user)


class TestAttemptListView(generics.ListAPIView):
    """Test topshirishlar ro'yxati"""
    serializer_class = TestAttemptSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        test_id = self.kwargs['pk']
        test = get_object_or_404(Test, pk=test_id, author=self.request.user)
        return TestAttempt.objects.filter(test=test).order_by('-started_at')


class TestAttemptDetailView(generics.RetrieveAPIView):
    """Test topshirish tafsilotlari"""
    serializer_class = TestAttemptSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return TestAttempt.objects.filter(test__author=self.request.user)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_test(request, pk):
    """Testni boshlash"""
    test = get_object_or_404(Test, pk=pk, is_public=True, is_active=True)
    
    student_name = request.data.get('student_name')
    student_class = request.data.get('student_class', '')
    
    if not student_name:
        return Response({
            'error': 'O\'quvchi ismi kiritilishi kerak'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Yangi test topshirish yaratish
    attempt = TestAttempt.objects.create(
        test=test,
        student_name=student_name,
        student_class=student_class,
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    # Test savollarini olish
    questions = test.questions.all().order_by('order')
    questions_data = []
    
    for question in questions:
        answers = question.answers.all().order_by('order')
        questions_data.append({
            'id': question.id,
            'question_text': question.question_text,
            'question_type': question.question_type,
            'points': question.points,
            'order': question.order,
            'image': question.image.url if question.image else None,
            'answers': [
                {
                    'id': answer.id,
                    'answer_text': answer.answer_text,
                    'order': answer.order
                }
                for answer in answers
            ]
        })
    
    return Response({
        'message': 'Test muvaffaqiyatli boshlandi',
        'attempt': TestAttemptSerializer(attempt).data,
        'questions': questions_data,
        'time_limit': test.time_limit
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_test(request, pk):
    """Testni topshirish"""
    test = get_object_or_404(Test, pk=pk, is_public=True, is_active=True)
    
    attempt_id = request.data.get('attempt_id')
    student_answers = request.data.get('student_answers', [])
    
    if not attempt_id:
        return Response({
            'error': 'Test topshirish ID si kiritilishi kerak'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        attempt = TestAttempt.objects.get(id=attempt_id, test=test)
    except TestAttempt.DoesNotExist:
        return Response({
            'error': 'Test topshirish topilmadi'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Testni tugatish
    attempt.completed_at = timezone.now()
    attempt.is_completed = True
    
    # Javoblarni saqlash va baholash
    total_score = 0
    correct_answers = 0
    wrong_answers = 0
    
    for answer_data in student_answers:
        question_id = answer_data.get('question_id')
        selected_answers = answer_data.get('selected_answers', [])
        text_answer = answer_data.get('text_answer', '')
        
        try:
            question = Question.objects.get(id=question_id, test=test)
        except Question.DoesNotExist:
            continue
        
        # O'quvchi javobini saqlash
        student_answer = StudentAnswer.objects.create(
            attempt=attempt,
            question=question,
            text_answer=text_answer
        )
        
        # Tanlangan javoblarni saqlash
        for answer_id in selected_answers:
            try:
                answer = Answer.objects.get(id=answer_id, question=question)
                student_answer.selected_answers.add(answer)
            except Answer.DoesNotExist:
                continue
        
        # Javobni tekshirish
        is_correct = True
        correct_answers_list = question.answers.filter(is_correct=True)
        
        if question.question_type in ['single_choice', 'multiple_choice']:
            selected_correct = student_answer.selected_answers.filter(is_correct=True)
            if selected_correct.count() != correct_answers_list.count():
                is_correct = False
            elif not all(answer in selected_correct for answer in correct_answers_list):
                is_correct = False
        
        student_answer.is_correct = is_correct
        student_answer.points_earned = question.points if is_correct else 0
        student_answer.save()
        
        if is_correct:
            correct_answers += 1
            total_score += question.points
        else:
            wrong_answers += 1
    
    # Natijalarni saqlash
    attempt.score = total_score
    attempt.percentage = (total_score / test.total_points * 100) if test.total_points > 0 else 0
    attempt.save()
    
    return Response({
        'message': 'Test muvaffaqiyatli topshirildi',
        'attempt': TestAttemptSerializer(attempt).data,
        'results': {
            'score': total_score,
            'percentage': attempt.percentage,
            'correct_answers': correct_answers,
            'wrong_answers': wrong_answers,
            'total_questions': test.total_questions
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_tests(request):
    """Testlarni qidirish"""
    query = request.query_params.get('q', '')
    category = request.query_params.get('category')
    subject = request.query_params.get('subject')
    grade_level = request.query_params.get('grade')
    difficulty = request.query_params.get('difficulty')
    
    queryset = Test.objects.filter(is_public=True, is_active=True)
    
    if query:
        queryset = queryset.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        )
    
    if category:
        queryset = queryset.filter(category_id=category)
    if subject:
        queryset = queryset.filter(subject=subject)
    if grade_level:
        queryset = queryset.filter(grade_level=grade_level)
    if difficulty:
        queryset = queryset.filter(difficulty=difficulty)
    
    # Natijalarni tartiblash
    sort_by = request.query_params.get('sort', '-created_at')
    queryset = queryset.order_by(sort_by)
    
    serializer = TestSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_tests(request):
    """Foydalanuvchining testlari"""
    tests = Test.objects.filter(author=request.user).order_by('-created_at')
    serializer = TestSerializer(tests, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test_stats(request, pk):
    """Test statistikasi"""
    test = get_object_or_404(Test, pk=pk, author=request.user)
    
    attempts = test.attempts.all()
    total_attempts = attempts.count()
    completed_attempts = attempts.filter(is_completed=True).count()
    avg_score = attempts.filter(is_completed=True).aggregate(
        avg_score=models.Avg('score')
    )['avg_score'] or 0
    avg_percentage = attempts.filter(is_completed=True).aggregate(
        avg_percentage=models.Avg('percentage')
    )['avg_percentage'] or 0
    
    return Response({
        'test': TestSerializer(test).data,
        'total_attempts': total_attempts,
        'completed_attempts': completed_attempts,
        'avg_score': round(avg_score, 2),
        'avg_percentage': round(avg_percentage, 2)
    })