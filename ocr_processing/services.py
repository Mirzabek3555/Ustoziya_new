import cv2
import numpy as np
import pytesseract
from PIL import Image
import re
import json
from django.conf import settings
from .models import OCRProcessing, TestResult
import logging
from google.cloud import vision
from google.oauth2 import service_account
import io
import openai
import requests
import base64
import google.generativeai as genai

logger = logging.getLogger(__name__)


class OCRService:
    """OCR xizmati"""
    
    def __init__(self):
        # Tesseract yo'lini sozlash (Windows uchun)
        self.tesseract_available = False
        try:
            if hasattr(settings, 'TESSERACT_PATH'):
                pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH
            
            # Tesseract mavjudligini tekshirish
            pytesseract.get_tesseract_version()
            self.tesseract_available = True
            logger.info("Tesseract OCR muvaffaqiyatli yuklandi")
        except Exception as e:
            logger.warning(f"Tesseract OCR topilmadi: {e}")
            self.tesseract_available = False
        
        # Google Vision API'ni sozlash
        try:
            # API key orqali autentifikatsiya
            import os
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = getattr(settings, 'GOOGLE_API_KEY', '')
            self.vision_client = vision.ImageAnnotatorClient()
        except Exception as e:
            logger.warning(f"Google Vision API sozlanmadi: {e}")
            self.vision_client = None
        
        # OpenAI API'ni sozlash
        try:
            openai.api_key = getattr(settings, 'OPENAI_API_KEY', '')
            self.openai_client = openai.OpenAI(api_key=openai.api_key)
            self.openai_available = True
            logger.info("OpenAI API muvaffaqiyatli yuklandi")
        except Exception as e:
            logger.warning(f"OpenAI API sozlanmadi: {e}")
            self.openai_client = None
            self.openai_available = False
        
        # Azure Computer Vision API'ni sozlash
        try:
            self.azure_endpoint = getattr(settings, 'AZURE_VISION_ENDPOINT', '')
            self.azure_key = getattr(settings, 'AZURE_VISION_KEY', '')
            self.azure_available = bool(self.azure_endpoint and self.azure_key)
            if self.azure_available:
                logger.info("Azure Computer Vision API muvaffaqiyatli yuklandi")
        except Exception as e:
            logger.warning(f"Azure Computer Vision API sozlanmadi: {e}")
            self.azure_available = False
    
    def preprocess_image(self, image_path):
        """Rasmni oldindan qayta ishlash"""
        try:
            # Rasmni o'qish
            image = cv2.imread(image_path)
            
            # Rangli rasmni kulrangga aylantirish
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Shovqinni kamaytirish
            denoised = cv2.medianBlur(gray, 3)
            
            # Kontrastni oshirish
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)
            
            # Otsu thresholding
            _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            return thresh
        except Exception as e:
            logger.error(f"Rasmni qayta ishlashda xatolik: {e}")
            return None
    
    def extract_text(self, image_path):
        """Rasmdan matnni ajratib olish - ko'p AI model bilan"""
        try:
            # 1. OpenAI GPT-4 Vision (eng yuqori aniqlik)
            if self.openai_available:
                text, confidence = self.extract_text_openai(image_path)
                if text and confidence > 0.8:
                    logger.info("OpenAI GPT-4 Vision natijasi qabul qilindi")
                    return text, confidence
            
            # 2. Google Vision API
            if self.vision_client:
                text, confidence = self.extract_text_google(image_path)
                if text and confidence > 0.7:
                    logger.info("Google Vision API natijasi qabul qilindi")
                    return text, confidence
            
            # 3. Azure Computer Vision
            if self.azure_available:
                text, confidence = self.extract_text_azure(image_path)
                if text and confidence > 0.7:
                    logger.info("Azure Computer Vision natijasi qabul qilindi")
                    return text, confidence
            
            # 4. Tesseract OCR (fallback)
            if self.tesseract_available:
                logger.info("Tesseract OCR ishlatilmoqda")
                return self.extract_text_tesseract(image_path)
            else:
                logger.error("Barcha OCR xizmatlari mavjud emas")
                return "OCR xizmatlari mavjud emas. Iltimos, API kalitlarini tekshiring.", 0.0
            
        except Exception as e:
            logger.error(f"OCR qilishda xatolik: {e}")
            return None, 0.0
    
    def extract_text_google(self, image_path):
        """Google Vision API orqali OCR"""
        try:
            with io.open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            image = vision.Image(content=content)
            response = self.vision_client.text_detection(image=image)
            texts = response.text_annotations
            
            if texts:
                # Birinchi text - butun rasm matni
                full_text = texts[0].description
                # Ishonch darajasini hisoblash
                confidence = 0.9  # Google Vision odatda yuqori ishonch darajasi
                return full_text.strip(), confidence
            
            return None, 0.0
            
        except Exception as e:
            logger.error(f"Google Vision OCR xatoligi: {e}")
            return None, 0.0
    
    def extract_text_tesseract(self, image_path):
        """Tesseract orqali OCR"""
        try:
            # Rasmni qayta ishlash
            processed_image = self.preprocess_image(image_path)
            
            if processed_image is None:
                return None, 0.0
            
            # OCR qilish
            custom_config = r'--oem 3 --psm 6 -l uzb+eng'
            text = pytesseract.image_to_string(processed_image, config=custom_config)
            
            # Ishonch darajasini olish
            data = pytesseract.image_to_data(processed_image, output_type=pytesseract.Output.DICT)
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return text.strip(), avg_confidence
            
        except Exception as e:
            logger.error(f"Tesseract OCR xatoligi: {e}")
            return None, 0.0
    
    def extract_text_openai(self, image_path):
        """OpenAI GPT-4 Vision orqali OCR"""
        try:
            # Rasmni base64 formatga o'tkazish
            with open(image_path, 'rb') as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # OpenAI'ga so'rov yuborish
            response = self.openai_client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Bu rasmda ko'rsatilgan barcha matnni o'zbek tilida aniq va to'liq o'qing. Agar test javoblari bo'lsa, ularni ham ajratib ko'rsating."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )
            
            text = response.choices[0].message.content.strip()
            confidence = 0.95  # OpenAI GPT-4 Vision yuqori ishonchlilik
            return text, confidence
            
        except Exception as e:
            logger.error(f"OpenAI GPT-4 Vision OCR xatoligi: {e}")
            return None, 0.0
    
    def extract_text_azure(self, image_path):
        """Azure Computer Vision orqali OCR"""
        try:
            # Rasmni o'qish
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
            
            # Azure API'ga so'rov yuborish
            headers = {
                'Ocp-Apim-Subscription-Key': self.azure_key,
                'Content-Type': 'application/octet-stream'
            }
            
            url = f"{self.azure_endpoint}/vision/v3.2/read/analyze"
            
            response = requests.post(url, headers=headers, data=image_data)
            
            if response.status_code == 202:  # Accepted
                # Natijani olish uchun ikkinchi so'rov
                operation_url = response.headers['Operation-Location']
                
                # Natija tayyor bo'lgunga qadar kutish
                import time
                for _ in range(10):  # 10 sekund kutish
                    time.sleep(1)
                    result_response = requests.get(operation_url, headers=headers)
                    if result_response.status_code == 200:
                        result_data = result_response.json()
                        if result_data.get('status') == 'succeeded':
                            # Matnni yig'ish
                            text_lines = []
                            for read_result in result_data.get('analyzeResult', {}).get('readResults', []):
                                for line in read_result.get('lines', []):
                                    text_lines.append(line.get('text', ''))
                            
                            text = '\n'.join(text_lines)
                            confidence = 0.85  # Azure Computer Vision o'rtacha ishonchlilik
                            return text, confidence
            
            return None, 0.0
            
        except Exception as e:
            logger.error(f"Azure Computer Vision OCR xatoligi: {e}")
            return None, 0.0
    
    def parse_test_answers(self, text):
        """Test javoblarini tahlil qilish"""
        try:
            # O'quvchi ismini topish
            student_name = self.extract_student_name(text)
            
            # Javoblarni topish
            answers = self.extract_answers(text)
            
            return {
                'student_name': student_name,
                'answers': answers
            }
        except Exception as e:
            logger.error(f"Test javoblarini tahlil qilishda xatolik: {e}")
            return None
    
    def extract_student_name(self, text):
        """O'quvchi ismini ajratib olish"""
        # Ism uchun regex patternlar
        name_patterns = [
            r'ism[:\s]*([A-Za-z\u0400-\u04FF\u0500-\u052F\u2D00-\u2D2F\u2D30-\u2D7F\s]+)',
            r'foydalanuvchi[:\s]*([A-Za-z\u0400-\u04FF\u0500-\u052F\u2D00-\u2D2F\u2D30-\u2D7F\s]+)',
            r'ismi[:\s]*([A-Za-z\u0400-\u04FF\u0500-\u052F\u2D00-\u2D2F\u2D30-\u2D7F\s]+)',
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return "Noma'lum o'quvchi"
    
    def extract_answers(self, text):
        """Javoblarni ajratib olish"""
        answers = {}
        
        # Javob uchun regex patternlar
        answer_patterns = [
            r'(\d+)[\.\)]\s*([A-Da-d])',  # 1. A, 2) B format
            r'savol\s*(\d+)[:\s]*([A-Da-d])',  # Savol 1: A format
            r'(\d+)\s*-\s*([A-Da-d])',  # 1 - A format
        ]
        
        for pattern in answer_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for question_num, answer in matches:
                answers[int(question_num)] = answer.upper()
        
        return answers


class TestGradingService:
    """Test baholash xizmati"""
    
    def __init__(self):
        self.ocr_service = OCRService()
        self.analysis_service = TestAnalysisService()
    
    def grade_test(self, ocr_processing, test):
        """Testni baholash - AI tahlil bilan"""
        try:
            # OCR natijasini olish
            if not ocr_processing.processed_text:
                return None
            
            # Test savollarini olish
            questions = test.questions.all().order_by('order')
            
            # AI tahlil xizmati orqali javoblarni tahlil qilish
            analysis_data = self.analysis_service.analyze_test_answers(
                ocr_processing.processed_text, 
                questions
            )
            
            if not analysis_data:
                # AI ishlamasa, oddiy tahlil
                parsed_data = self.ocr_service.parse_test_answers(ocr_processing.processed_text)
                if not parsed_data:
                    return None
                student_name = parsed_data['student_name']
                student_answers = parsed_data['answers']
            else:
                # AI tahlil natijasi
                student_name = analysis_data['student_name']
                student_answers = analysis_data['answers']
            
            total_questions = questions.count()
            correct_answers = 0
            wrong_answers = 0
            
            # Har bir savolni tekshirish
            for question in questions:
                question_num = question.order
                student_answer = student_answers.get(str(question_num))  # String key uchun
            
                if student_answer and student_answer != 'N':  # N = javob yo'q
                    # To'g'ri javobni topish
                    correct_answer = question.answers.filter(is_correct=True).first()
                    
                    if correct_answer and student_answer == correct_answer.answer_text:
                        correct_answers += 1
                    else:
                        wrong_answers += 1
            
            # Ball va foizni hisoblash
            score = correct_answers
            percentage = (correct_answers / total_questions * 100) if total_questions > 0 else 0
            
            # Baholash
            grade = self.calculate_grade(percentage)
            
            # Natijani saqlash
            test_result = TestResult.objects.create(
                ocr_processing=ocr_processing,
                student_name=student_name,
                total_questions=total_questions,
                correct_answers=correct_answers,
                wrong_answers=wrong_answers,
                score=score,
                percentage=percentage,
                grade=grade
            )
            
            # AI feedback yaratish
            if analysis_data:
                feedback = self.analysis_service.generate_test_feedback(test_result, analysis_data)
                if feedback:
                    # Feedback ni saqlash (ixtiyoriy)
                    logger.info(f"AI feedback yaratildi: {feedback.get('overall_feedback', '')}")
            
            return test_result
            
        except Exception as e:
            logger.error(f"Test baholashda xatolik: {e}")
            return None
    
    def calculate_grade(self, percentage):
        """Baholash hisoblash"""
        if percentage >= 90:
            return "A'lo"
        elif percentage >= 80:
            return "Yaxshi"
        elif percentage >= 70:
            return "Qoniqarli"
        elif percentage >= 60:
            return "Qoniqarsiz"
        else:
            return "Yomon"


class ExcelExportService:
    """Excel eksport xizmati"""
    
    def __init__(self):
        import pandas as pd
        self.pd = pd
    
    def export_test_results(self, test, results):
        """Test natijalarini Excel ga eksport qilish"""
        try:
            # Ma'lumotlarni tayyorlash
            data = []
            for result in results:
                data.append({
                    'O\'quvchi ismi': result.student_name,
                    'Sinf': result.student_class or '',
                    'Jami savollar': result.total_questions,
                    'To\'g\'ri javoblar': result.correct_answers,
                    'Noto\'g\'ri javoblar': result.wrong_answers,
                    'Ball': result.score,
                    'Foiz': f"{result.percentage:.1f}%",
                    'Baholash': result.grade,
                    'Qayta ishlangan vaqt': result.processed_at.strftime('%Y-%m-%d %H:%M:%S')
                })
            
            # DataFrame yaratish
            df = self.pd.DataFrame(data)
            
            # Excel fayl yaratish
            excel_path = f"media/excel_exports/test_{test.id}_{results[0].processed_at.strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            with self.pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Test natijalari', index=False)
                
                # Qo'shimcha ma'lumotlar
                summary_data = {
                    'Test nomi': [test.title],
                    'Fan': [test.get_subject_display()],
                    'Sinf darajasi': [test.grade_level],
                    'Jami o\'quvchilar': [len(results)],
                    'O\'rtacha foiz': [f"{sum(r.percentage for r in results) / len(results):.1f}%"],
                    'Eksport vaqti': [results[0].processed_at.strftime('%Y-%m-%d %H:%M:%S')]
                }
                
                summary_df = self.pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Umumiy ma\'lumot', index=False)
            
            return excel_path
            
        except Exception as e:
            logger.error(f"Excel eksportda xatolik: {e}")
            return None


class TestAnalysisService:
    """Test tahlil qilish xizmati - Google Gemini AI"""
    
    def __init__(self):
        # Google Gemini API'ni sozlash - TEZLASHTIRILGAN
        try:
            genai.configure(api_key=settings.GOOGLE_GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            self.available = True
            # Cache uchun
            self._cache = {}
            logger.info("Google Gemini AI test tahlil xizmati muvaffaqiyatli yuklandi")
        except Exception as e:
            logger.warning(f"Google Gemini AI sozlanmadi: {e}")
            self.available = False
    
    def analyze_test_answers(self, ocr_text, test_questions):
        """OCR matnidan test javoblarini tahlil qilish"""
        try:
            if not self.available:
                return self._fallback_analysis(ocr_text, test_questions)
            
            # Test savollarini formatlash
            questions_text = self._format_questions_for_ai(test_questions)
            
            # AI uchun prompt yaratish
            # O'QUVCHI ISMINI O'QISH UCHUN YAXSHILANGAN PROMPT
            prompt = f"""OCR matnidan o'quvchi ismini va test javoblarini tahlil qiling:

OCR MATN:
{ocr_text[:500]}

SAVOLLAR:
{questions_text[:300]}

TALABLAR:
1. O'quvchi ismini toping (ism, familiya)
2. Har bir savolga javobni aniqlang
3. To'g'ri/noto'g'ri ekanligini belgilang

Qaytarish: {{"student_name": "To'liq ism", "answers": {{"1": "A", "2": "B"}}, "confidence": 0.8}}"""
            
            # Gemini'ga so'rov yuborish - TEZLASHTIRILGAN
            response = self.model.generate_content(prompt, generation_config={
                'max_output_tokens': 800,
                'temperature': 0.1,
                'top_p': 0.8
            })
            response_text = response.text.strip()
            
            # JSON parse qilish
            analysis_result = self._parse_ai_analysis(response_text)
            
            if analysis_result:
                logger.info("Google Gemini AI test tahlili muvaffaqiyatli")
                return analysis_result
            else:
                logger.warning("AI tahlilini parse qila olmadi, fallback ishlatilmoqda")
                return self._fallback_analysis(ocr_text, test_questions)
                
        except Exception as e:
            logger.error(f"Test tahlilida xatolik: {e}")
            return self._fallback_analysis(ocr_text, test_questions)
    
    def _format_questions_for_ai(self, test_questions):
        """Test savollarini AI uchun formatlash"""
        questions_text = ""
        for i, question in enumerate(test_questions, 1):
            questions_text += f"\n{i}. {question.question_text}\n"
            for answer in question.answers.all():
                marker = "✓" if answer.is_correct else "○"
                questions_text += f"   {marker} {answer.answer_text}\n"
        return questions_text
    
    def _parse_ai_analysis(self, response_text):
        """AI javobini parse qilish"""
        try:
            # JSON qismini ajratib olish
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                logger.error("JSON format topilmadi")
                return None
            
            json_text = response_text[start_idx:end_idx]
            analysis_data = json.loads(json_text)
            
            return {
                'student_name': analysis_data.get('student_name', 'Noma\'lum o\'quvchi'),
                'answers': analysis_data.get('answers', {}),
                'confidence': analysis_data.get('confidence', 0.0),
                'analysis_notes': analysis_data.get('analysis_notes', ''),
                'ai_used': 'Google Gemini AI'
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse xatoligi: {e}")
            return None
        except Exception as e:
            logger.error(f"AI tahlilini parse qilishda xatolik: {e}")
            return None
    
    def _fallback_analysis(self, ocr_text, test_questions):
        """Fallback tahlil (AI ishlamasa)"""
        try:
            # Oddiy regex bilan javoblarni topish
            answers = {}
            student_name = "Noma'lum o'quvchi"
            
            # O'quvchi ismini topish
            name_patterns = [
                r'ism[:\s]*([A-Za-z\u0400-\u04FF\u0500-\u052F\u2D00-\u2D2F\u2D30-\u2D7F\s]+)',
                r'foydalanuvchi[:\s]*([A-Za-z\u0400-\u04FF\u0500-\u052F\u2D00-\u2D2F\u2D30-\u2D7F\s]+)',
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, ocr_text, re.IGNORECASE)
                if match:
                    student_name = match.group(1).strip()
                    break
            
            # Javoblarni topish
            answer_patterns = [
                r'(\d+)[\.\)]\s*([A-Da-d])',
                r'savol\s*(\d+)[:\s]*([A-Da-d])',
                r'(\d+)\s*-\s*([A-Da-d])',
            ]
            
            for pattern in answer_patterns:
                matches = re.findall(pattern, ocr_text, re.IGNORECASE)
                for question_num, answer in matches:
                    answers[int(question_num)] = answer.upper()
            
            return {
                'student_name': student_name,
                'answers': answers,
                'confidence': 0.6,  # Fallback uchun past ishonchlilik
                'analysis_notes': 'Oddiy regex tahlil (AI ishlamadi)',
                'ai_used': 'Fallback Analysis'
            }
            
        except Exception as e:
            logger.error(f"Fallback tahlilida xatolik: {e}")
            return {
                'student_name': 'Noma\'lum o\'quvchi',
                'answers': {},
                'confidence': 0.0,
                'analysis_notes': 'Tahlil qilishda xatolik',
                'ai_used': 'Error'
            }
    
    def generate_test_feedback(self, test_result, analysis_data):
        """Test natijasi uchun AI feedback yaratish"""
        try:
            if not self.available:
                return self._generate_simple_feedback(test_result)
            
            # QISQARTIRILGAN FEEDBACK PROMPT
            prompt = f"""Test natijasi: {test_result.correct_answers}/{test_result.total_questions} ({test_result.percentage:.1f}%) - {test_result.grade}

Qisqa feedback yarating: {{"overall_feedback": "Feedback", "strengths": ["Kuchli"], "weaknesses": ["Zaif"], "recommendations": ["Maslahat"]}}"""
            
            # TEZLASHTIRILGAN feedback
            response = self.model.generate_content(prompt, generation_config={
                'max_output_tokens': 300,
                'temperature': 0.1
            })
            feedback_data = self._parse_feedback_response(response.text)
            
            if feedback_data:
                return feedback_data
            else:
                return self._generate_simple_feedback(test_result)
                
        except Exception as e:
            logger.error(f"Feedback yaratishda xatolik: {e}")
            return self._generate_simple_feedback(test_result)
    
    def _parse_feedback_response(self, response_text):
        """Feedback javobini parse qilish"""
        try:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                return None
            
            json_text = response_text[start_idx:end_idx]
            return json.loads(json_text)
            
        except Exception as e:
            logger.error(f"Feedback parse xatoligi: {e}")
            return None
    
    def _generate_simple_feedback(self, test_result):
        """Oddiy feedback yaratish"""
        if test_result.percentage >= 90:
            return {
                "overall_feedback": "A'lo natija! Siz juda yaxshi ishladingiz.",
                "strengths": ["Yuqori aniqlik", "Yaxshi tayyorgarlik"],
                "weaknesses": [],
                "recommendations": ["Davom eting"],
                "encouragement": "Sizning ishlaringiz ajoyib!"
            }
        elif test_result.percentage >= 70:
            return {
                "overall_feedback": "Yaxshi natija, lekin yaxshilash mumkin.",
                "strengths": ["Yaxshi tayyorgarlik"],
                "weaknesses": ["Ba'zi mavzularni takrorlash kerak"],
                "recommendations": ["Zaif mavzularni o'rganing"],
                "encouragement": "Siz yaxshi ishlayapsiz!"
            }
        else:
            return {
                "overall_feedback": "Natija qoniqarsiz, qo'shimcha o'rganish kerak.",
                "strengths": [],
                "weaknesses": ["Ko'p mavzularni takrorlash kerak"],
                "recommendations": ["Darslarni diqqat bilan tinglang", "Qo'shimcha mashq qiling"],
                "encouragement": "Harakat qiling, siz uddalaysiz!"
            }
