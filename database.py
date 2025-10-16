import sqlite3
import json
from typing import Dict, List, Optional
from datetime import datetime
import os

class DatabaseManager:
    
    def __init__(self, db_path: str = "legal_summarizer.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cases (
                case_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                upload_date TEXT NOT NULL,
                processed_date TEXT,
                status TEXT DEFAULT 'pending',
                error TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS summaries (
                case_id TEXT PRIMARY KEY,
                overview TEXT,
                key_points TEXT,
                entities TEXT,
                timeline TEXT,
                legal_references TEXT,
                confidence_score REAL,
                processing_time REAL,
                FOREIGN KEY (case_id) REFERENCES cases(case_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                rating INTEGER NOT NULL,
                comments TEXT,
                corrections TEXT,
                feedback_date TEXT NOT NULL,
                processed BOOLEAN DEFAULT 0,
                FOREIGN KEY (case_id) REFERENCES cases(case_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                recorded_date TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
        
        print("✅ Database initialized")
    
    def create_case(
        self,
        case_id: str,
        filename: str,
        file_type: str,
        file_path: str,
        upload_date: str
    ):
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO cases (case_id, filename, file_type, file_path, upload_date, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (case_id, filename, file_type, file_path, upload_date, 'pending'))
        
        conn.commit()
        conn.close()
    
    def update_status(
        self,
        case_id: str,
        status: str,
        error: Optional[str] = None
    ):
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if status == 'completed':
            cursor.execute('''
                UPDATE cases 
                SET status = ?, processed_date = ?, error = ?
                WHERE case_id = ?
            ''', (status, datetime.now().isoformat(), error, case_id))
        else:
            cursor.execute('''
                UPDATE cases 
                SET status = ?, error = ?
                WHERE case_id = ?
            ''', (status, error, case_id))
        
        conn.commit()
        conn.close()
    
    def save_summary(self, case_id: str, summary: Dict):
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO summaries 
            (case_id, overview, key_points, entities, timeline, legal_references, 
             confidence_score, processing_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            case_id,
            summary.get('overview', ''),
            json.dumps(summary.get('key_points', [])),
            json.dumps(summary.get('entities', {})),
            json.dumps(summary.get('timeline', [])),
            json.dumps(summary.get('legal_references', [])),
            summary.get('confidence_score', 0.0),
            summary.get('processing_time', 0.0)
        ))
        
        conn.commit()
        conn.close()
    
    def get_summary(self, case_id: str) -> Optional[Dict]:
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.*, s.*
            FROM cases c
            LEFT JOIN summaries s ON c.case_id = s.case_id
            WHERE c.case_id = ?
        ''', (case_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        result = dict(row)
        
        if result.get('key_points'):
            result['key_points'] = json.loads(result['key_points'])
        if result.get('entities'):
            result['entities'] = json.loads(result['entities'])
        if result.get('timeline'):
            result['timeline'] = json.loads(result['timeline'])
        if result.get('legal_references'):
            result['legal_references'] = json.loads(result['legal_references'])
        
        if result.get('overview'):
            result['summary'] = {
                'overview': result['overview'],
                'key_points': result.get('key_points', []),
                'entities': result.get('entities', {}),
                'timeline': result.get('timeline', []),
                'legal_references': result.get('legal_references', []),
                'confidence_score': result.get('confidence_score', 0.0)
            }
        
        return result
    
    def list_cases(
        self,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if status:
            cursor.execute('''
                SELECT * FROM cases 
                WHERE status = ?
                ORDER BY upload_date DESC
                LIMIT ?
            ''', (status, limit))
        else:
            cursor.execute('''
                SELECT * FROM cases 
                ORDER BY upload_date DESC
                LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def delete_case(self, case_id: str):
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM summaries WHERE case_id = ?', (case_id,))
        cursor.execute('DELETE FROM feedback WHERE case_id = ?', (case_id,))
        cursor.execute('DELETE FROM cases WHERE case_id = ?', (case_id,))
        
        conn.commit()
        conn.close()
    
    def save_feedback(
        self,
        case_id: str,
        rating: int,
        comments: Optional[str] = None,
        corrections: Optional[Dict] = None
    ):
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO feedback 
            (case_id, rating, comments, corrections, feedback_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            case_id,
            rating,
            comments,
            json.dumps(corrections) if corrections else None,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_pending_feedback(self) -> List[Dict]:
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM feedback 
            WHERE processed = 0
            ORDER BY feedback_date DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        feedback_list = []
        for row in rows:
            data = dict(row)
            if data.get('corrections'):
                data['corrections'] = json.loads(data['corrections'])
            feedback_list.append(data)
        
        return feedback_list
    
    def mark_feedback_processed(self, feedback_ids: List[int]):
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        placeholders = ','.join('?' * len(feedback_ids))
        cursor.execute(f'''
            UPDATE feedback 
            SET processed = 1
            WHERE id IN ({placeholders})
        ''', feedback_ids)
        
        conn.commit()
        conn.close()
    
    def get_statistics(self) -> Dict:
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        cursor.execute('SELECT COUNT(*) FROM cases')
        stats['total'] = cursor.fetchone()[0]
        
        for status in ['completed', 'processing', 'failed', 'pending']:
            cursor.execute('SELECT COUNT(*) FROM cases WHERE status = ?', (status,))
            stats[status] = cursor.fetchone()[0]
        
        cursor.execute('SELECT AVG(confidence_score) FROM summaries')
        avg_confidence = cursor.fetchone()[0]
        stats['avg_confidence'] = round(avg_confidence, 2) if avg_confidence else 0.0
        
        cursor.execute('SELECT AVG(processing_time) FROM summaries')
        avg_time = cursor.fetchone()[0]
        stats['avg_processing_time'] = round(avg_time, 2) if avg_time else 0.0
        
        conn.close()
        
        return stats
    
    def log_metric(self, metric_name: str, metric_value: float):
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO analytics (metric_name, metric_value, recorded_date)
            VALUES (?, ?, ?)
        ''', (metric_name, metric_value, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_metrics_history(
        self,
        metric_name: str,
        limit: int = 100
    ) -> List[Dict]:
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM analytics 
            WHERE metric_name = ?
            ORDER BY recorded_date DESC
            LIMIT ?
        ''', (metric_name, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
