import spacy
import re
from typing import Dict, List
import string

class PreprocessingModule:
    
    def __init__(self):
        try:
            self.nlp = spacy.load('en_core_web_sm')
        except:
            print("SpaCy model not found. Install with: python -m spacy download en_core_web_sm")
            self.nlp = None
        
        self.legal_patterns = {
            'IPC_SECTION': r'(?:IPC|Indian Penal Code)\s*(?:Section)?\s*(\d+[A-Z]?)',
            'CRPC_SECTION': r'(?:CrPC|Criminal Procedure Code)\s*(?:Section)?\s*(\d+[A-Z]?)',
            'CASE_NUMBER': r'(?:FIR|Case)\s*(?:No\.?|Number)?\s*:?\s*([A-Z0-9/-]+)',
            'DATE': r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',
            'TIME': r'\d{1,2}:\d{2}\s*(?:AM|PM|hrs)?'
        }
    
    def clean_text(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        ocr_corrections = {
            r'\b0\b': 'O',
            r'\bl\b': 'I',
            r'\|\|': 'll',
            r'\|': 'I',
        }
        for pattern, replacement in ocr_corrections.items():
            text = re.sub(pattern, replacement, text)
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace('’', "'").replace('‘', "'")
        text = re.sub(r'\.{2,}', '.', text)
        text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
        text = ' '.join(text.split())
        return text.strip()
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        entities = {
            'PERSON': [],
            'GPE': [],
            'ORG': [],
            'DATE': [],
            'TIME': [],
            'LAW': [],
            'CASE_NUMBER': [],
            'ACCUSED': [],
            'WITNESS': []
        }
        if self.nlp:
            doc = self.nlp(text)
            for ent in doc.ents:
                if ent.label_ in entities:
                    entities[ent.label_].append(ent.text)
        for pattern_type, pattern in self.legal_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if pattern_type in ['IPC_SECTION', 'CRPC_SECTION']:
                entities['LAW'].extend(matches)
            elif pattern_type == 'CASE_NUMBER':
                entities['CASE_NUMBER'].extend(matches)
            elif pattern_type == 'DATE':
                entities['DATE'].extend(matches)
            elif pattern_type == 'TIME':
                entities['TIME'].extend(matches)
        entities['ACCUSED'] = self._identify_accused(text)
        entities['WITNESS'] = self._identify_witnesses(text)
        for key in entities:
            entities[key] = list(set(entities[key]))
        return entities
    
    def _identify_accused(self, text: str) -> List[str]:
        accused = []
        patterns = [
            r'(?:accused|defendant|respondent)\s+(?:named\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:is|was)\s+accused',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            accused.extend(matches)
        return list(set(accused))
    
    def _identify_witnesses(self, text: str) -> List[str]:
        witnesses = []
        patterns = [
            r'witness(?:es)?\s+(?:named\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:witnessed|testified)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            witnesses.extend(matches)
        return list(set(witnesses))
    
    def tokenize(self, text: str) -> List[str]:
        if self.nlp:
            doc = self.nlp(text)
            return [token.text for token in doc]
        else:
            return text.split()
    
    def lemmatize(self, text: str) -> str:
        if self.nlp:
            doc = self.nlp(text)
            lemmatized = ' '.join([token.lemma_ for token in doc])
            return lemmatized
        return text
    
    def remove_stopwords(self, text: str) -> str:
        if self.nlp:
            doc = self.nlp(text)
            legal_keep_words = {
                'against', 'under', 'before', 'after', 'between',
                'section', 'act', 'case', 'court'
            }
            filtered = [
                token.text for token in doc 
                if not token.is_stop or token.text.lower() in legal_keep_words
            ]
            return ' '.join(filtered)
        return text
    
    def extract_sentences(self, text: str) -> List[str]:
        if self.nlp:
            doc = self.nlp(text)
            return [sent.text.strip() for sent in doc.sents]
        else:
            sentences = re.split(r'[.!?]+', text)
            return [s.strip() for s in sentences if s.strip()]
    
    def post_process(self, summary: Dict) -> Dict:
        if 'overview' in summary:
            summary['overview'] = self._clean_summary_text(summary['overview'])
        if 'key_points' in summary:
            summary['key_points'] = self._rank_key_points(summary['key_points'])
        if 'timeline' in summary:
            summary['timeline'] = self._validate_timeline(summary['timeline'])
        if 'legal_references' in summary:
            summary['legal_references'] = list(set(summary['legal_references']))
        return summary
    
    def _clean_summary_text(self, text: str) -> str:
        if text:
            text = text[0].upper() + text[1:]
        redundant_phrases = [
            r'\b(the|a|an)\s+(the|a|an)\b',
            r'\bthat\s+that\b',
            r'\bwhich\s+which\b',
        ]
        for phrase in redundant_phrases:
            text = re.sub(phrase, r'\1', text, flags=re.IGNORECASE)
        if text and text[-1] not in '.!?':
            text += '.'
        return text
    
    def _rank_key_points(self, key_points: List[str]) -> List[str]:
        importance_keywords = [
            'accused', 'witness', 'evidence', 'section', 'fir',
            'complaint', 'theft', 'assault', 'murder', 'case'
        ]
        scored_points = []
        for point in key_points:
            score = 0
            point_lower = point.lower()
            for keyword in importance_keywords:
                if keyword in point_lower:
                    score += 1
            scored_points.append((point, score))
        scored_points.sort(key=lambda x: x[1], reverse=True)
        return [point for point, score in scored_points]
    
    def _validate_timeline(self, timeline: List[Dict]) -> List[Dict]:
        valid_timeline = [
            event for event in timeline 
            if event.get('event') and event.get('time')
        ]
        valid_timeline.sort(key=lambda x: x.get('time', ''))
        return valid_timeline
    
    def extract_key_terms(self, text: str, n: int = 10) -> List[str]:
        if not self.nlp:
            return []
        doc = self.nlp(text.lower())
        key_terms = []
        for token in doc:
            if (token.pos_ in ['NOUN', 'PROPN'] and 
                not token.is_stop and 
                len(token.text) > 3):
                key_terms.append(token.text)
        from collections import Counter
        term_freq = Counter(key_terms)
        return [term for term, count in term_freq.most_common(n)]
    
    def normalize_legal_text(self, text: str) -> str:
        text = re.sub(
            r'(?:Section|Sec\.?)\s+(\d+)',
            r'Section \1',
            text,
            flags=re.IGNORECASE
        )
        abbreviations = {
            r'\bFIR\b': 'First Information Report',
            r'\bIPC\b': 'Indian Penal Code',
            r'\bCrPC\b': 'Criminal Procedure Code',
            r'\bHon\'?ble\b': 'Honorable',
        }
        for abbr, expansion in abbreviations.items():
            text = re.sub(
                abbr,
                f'{abbr} ({expansion})',
                text,
                flags=re.IGNORECASE
            )
        return text
    
    def detect_language(self, text: str) -> str:
        hindi_chars = set('अआइईउऊएऐओऔकखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह')
        text_chars = set(text)
        if text_chars.intersection(hindi_chars):
            return 'hi'
        return 'en'
    
    def segment_document(self, text: str) -> Dict[str, str]:
        segments = {
            'header': '',
            'facts': '',
            'arguments': '',
            'evidence': '',
            'conclusion': ''
        }
        sentences = self.extract_sentences(text)
        current_section = 'header'
        for sent in sentences:
            sent_lower = sent.lower()
            if 'facts of the case' in sent_lower or 'brief facts' in sent_lower:
                current_section = 'facts'
            elif 'argument' in sent_lower or 'submission' in sent_lower:
                current_section = 'arguments'
            elif 'evidence' in sent_lower or 'exhibit' in sent_lower:
                current_section = 'evidence'
            elif 'conclusion' in sent_lower or 'prayer' in sent_lower:
                current_section = 'conclusion'
            segments[current_section] += sent + ' '
        for key in segments:
            segments[key] = segments[key].strip()
        return segments
