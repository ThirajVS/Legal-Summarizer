import os
import hashlib
import magic
from datetime import datetime
from typing import Optional
import re

class FileValidator:
    ALLOWED_TEXT = ['.txt', '.doc', '.docx']
    ALLOWED_IMAGE = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp']
    ALLOWED_AUDIO = ['.mp3', '.wav', '.m4a', '.ogg', '.flac']
    MAX_FILE_SIZE = 50 * 1024 * 1024

    @classmethod
    def validate_file(cls, file_path: str, file_type: str) -> dict:
        if not os.path.exists(file_path):
            return {'valid': False, 'error': 'File not found'}
        file_size = os.path.getsize(file_path)
        if file_size > cls.MAX_FILE_SIZE:
            return {'valid': False, 'error': 'File too large'}
        if file_size == 0:
            return {'valid': False, 'error': 'Empty file'}
        ext = os.path.splitext(file_path)[1].lower()
        if file_type == 'text' and ext not in cls.ALLOWED_TEXT:
            return {'valid': False, 'error': 'Invalid text file format'}
        elif file_type == 'image' and ext not in cls.ALLOWED_IMAGE:
            return {'valid': False, 'error': 'Invalid image file format'}
        elif file_type == 'audio' and ext not in cls.ALLOWED_AUDIO:
            return {'valid': False, 'error': 'Invalid audio file format'}
        try:
            mime = magic.from_file(file_path, mime=True)
            if not cls._validate_mime(mime, file_type):
                return {'valid': False, 'error': 'File content does not match extension'}
        except:
            pass
        return {'valid': True, 'error': None}

    @classmethod
    def _validate_mime(cls, mime: str, file_type: str) -> bool:
        valid_mimes = {
            'text': ['text/', 'application/msword', 'application/vnd.openxmlformats'],
            'image': ['image/', 'application/pdf'],
            'audio': ['audio/']
        }
        return any(mime.startswith(prefix) for prefix in valid_mimes.get(file_type, []))

def calculate_file_hash(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

def sanitize_filename(filename: str) -> str:
    filename = os.path.basename(filename)
    filename = re.sub(r'[^\w\s\-\.]', '', filename)
    name, ext = os.path.splitext(filename)
    if len(name) > 200:
        name = name[:200]
    return name + ext

def format_file_size(size_bytes: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def extract_case_info(text: str) -> dict:
    info = {
        'fir_number': None,
        'date': None,
        'sections': [],
        'complainant': None,
        'accused': None
    }
    fir_match = re.search(r'(?:FIR|Case)\s*(?:No\.?|Number)?\s*:?\s*([A-Z0-9/-]+)', text, re.IGNORECASE)
    if fir_match:
        info['fir_number'] = fir_match.group(1)
    date_match = re.search(r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}', text)
    if date_match:
        info['date'] = date_match.group(0)
    section_matches = re.findall(r'(?:IPC|CrPC)?\s*Section\s+(\d+[A-Z]?)', text, re.IGNORECASE)
    info['sections'] = list(set(section_matches))
    return info

def calculate_reading_time(text: str, words_per_minute: int = 200) -> int:
    word_count = len(text.split())
    return max(1, word_count // words_per_minute)

def highlight_legal_terms(text: str) -> str:
    legal_terms = [
        r'\bIPC\b', r'\bCrPC\b', r'\bFIR\b',
        r'Section\s+\d+', r'Article\s+\d+',
        r'\baccused\b', r'\bwitness\b', r'\bcomplainant\b'
    ]
    highlighted = text
    for term in legal_terms:
        highlighted = re.sub(
            f'({term})',
            r'<mark>\1</mark>',
            highlighted,
            flags=re.IGNORECASE
        )
    return highlighted

class Logger:
    @staticmethod
    def log(level: str, message: str):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] [{level}] {message}")

    @staticmethod
    def info(message: str):
        Logger.log('INFO', message)

    @staticmethod
    def error(message: str):
        Logger.log('ERROR', message)

    @staticmethod
    def warning(message: str):
        Logger.log('WARNING', message)

def create_pdf_report(summary: dict, output_path: str):
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        doc = SimpleDocTemplate(output_path, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30
        )
        title = Paragraph(f"Legal Case Summary: {summary.get('case_id', 'N/A')}", title_style)
        story.append(title)
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph("<b>Overview</b>", styles['Heading2']))
        story.append(Paragraph(summary.get('overview', ''), styles['BodyText']))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("<b>Key Points</b>", styles['Heading2']))
        for i, point in enumerate(summary.get('key_points', []), 1):
            story.append(Paragraph(f"{i}. {point}", styles['BodyText']))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("<b>Case Entities</b>", styles['Heading2']))
        entities = summary.get('entities', {})
        entity_data = [
            ['Entity Type', 'Details'],
            ['Complainant', entities.get('complainant', 'N/A')],
            ['Accused', entities.get('accused', 'N/A')],
            ['Location', entities.get('location', 'N/A')],
            ['Date', entities.get('date', 'N/A')]
        ]
        entity_table = Table(entity_data)
        entity_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(entity_table)
        doc.build(story)
        return True
    except ImportError:
        print("reportlab not installed. Install with: pip install reportlab")
        return False
    except Exception as e:
        print(f"PDF generation failed: {e}")
        return False
