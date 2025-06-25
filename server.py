"""Unified server with login and improved user statistics.
Updated: Force deployment refresh to ensure debug endpoint is available.
"""

import hashlib
import os
import time
import json
import zipfile
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import normalizer functionality
from hassy_normalizer import (
    normalize_text,
    get_normalizer_stats,
    word_diff_simple,
    format_diff_html,
    get_change_stats,
)
from hassy_normalizer.data_loader import _get_data_file_path, _get_writable_data_path, clear_cache

# Log the normalizer version at startup
import importlib.metadata
try:
    version = importlib.metadata.version("hassy-normalizer")
    print(f"Hassy-Normalizer v{version}")
except Exception as e:
    print(f"Could not get normalizer version: {e}")

# Simple in-memory storage
class SimpleStorage:
    def __init__(self):
        self.paragraphs = []
        self.recordings = []
        self.variants = []
        self.next_id = 1
        
        # Add sample data
        self.paragraphs = [
            {
                "id": 1,
                "text_original": "مرحبا بكم في مسجل اللهجة الحسانية",
                "text_final": None,
                "status": "unassigned",
                "assigned_to": None,
                "created_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "id": 2,
                "text_original": "هذا نص تجريبي للتسجيل والتطبيع",
                "text_final": None,
                "status": "unassigned",
                "assigned_to": None,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        ]
        self.next_id = 3
    
    def add_paragraph(self, text: str) -> int:
        paragraph = {
            "id": self.next_id,
            "text_original": text,
            "text_final": None,
            "status": "unassigned",
            "assigned_to": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self.paragraphs.append(paragraph)
        self.next_id += 1
        return paragraph["id"]
    
    def get_next_unassigned(self, username: str) -> Optional[Dict]:
        for paragraph in self.paragraphs:
            if paragraph["status"] == "unassigned":
                paragraph["status"] = "assigned"
                paragraph["assigned_to"] = username
                return paragraph
        return None
    
    def complete_paragraph(self, para_id: int, text_final: str, username: str) -> bool:
        for paragraph in self.paragraphs:
            if paragraph["id"] == para_id and paragraph["assigned_to"] == username:
                paragraph["text_final"] = text_final
                paragraph["status"] = "done"
                return True
        return False
    
    def skip_paragraph(self, para_id: int, username: str) -> bool:
        for paragraph in self.paragraphs:
            if paragraph["id"] == para_id and paragraph["assigned_to"] == username:
                paragraph["status"] = "skipped"
                return True
        return False
    
    def add_recording(self, para_id: int, username: str, filename: str):
        recording = {
            "id": len(self.recordings) + 1,
            "paragraph_id": para_id,
            "user": username,
            "filename": filename,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self.recordings.append(recording)
        return recording["id"]
    
    def add_variant(self, word: str, suggestion: str, reporter: str):
        variant = {
            "id": len(self.variants) + 1,
            "word": word,
            "suggestion": suggestion,
            "reporter": reporter,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self.variants.append(variant)
        return variant["id"]
    def delete_variant(self, variant_id: int, reporter: str):
        """Delete a grammar variant if it belongs to the reporter"""
        for i, variant in enumerate(self.variants):
            if variant["id"] == variant_id and variant["reporter"] == reporter:
                del self.variants[i]
                return True
        return False
    
    def add_linked_word(self, wrong: str, correct: str, reporter: str):
        """Add a linked word pair and update the JSON file in real-time"""
        # Read from existing location first
        read_file = _get_data_file_path("linked_words.json")
        write_file = _get_writable_data_path("linked_words.json")
        
        # Load existing data
        try:
            if read_file.exists():
                with open(read_file, 'r', encoding='utf-8') as f:
                    linked_words = json.load(f)
            else:
                linked_words = []
        except Exception:
            linked_words = []
        
        # Add new entry
        new_entry = {
            "wrong": wrong,
            "correct": correct,
            "reporter": reporter,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Check if entry already exists
        exists = any(item.get("wrong") == wrong and item.get("correct") == correct 
                    for item in linked_words)
        
        if not exists:
            linked_words.append(new_entry)
            
            # Save to writable file
            try:
                 write_file.parent.mkdir(parents=True, exist_ok=True)
                 with open(write_file, 'w', encoding='utf-8') as f:
                     json.dump(linked_words, f, ensure_ascii=False, indent=2)
                 # Clear cache so normalizer uses updated data
                 clear_cache()
                 return len(linked_words)
            except Exception as e:
                print(f"Error saving linked words: {e}")
                return None
        return None
    
    def add_variant_word(self, canonical: str, variant: str, reporter: str):
        """Add a variant word and update the JSONL file in real-time"""
        # Read from existing location first
        read_file = _get_data_file_path("hassaniya_variants.jsonl")
        write_file = _get_writable_data_path("hassaniya_variants.jsonl")
        
        # Load existing data
        variants_data = {}
        try:
            if read_file.exists():
                with open(read_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            entry = json.loads(line)
                            variants_data[entry["canonical"]] = entry["variants"]
        except Exception:
            variants_data = {}
        
        # Add new variant
        if canonical in variants_data:
            if variant not in variants_data[canonical]:
                variants_data[canonical].append(variant)
            else:
                return None  # Variant already exists
        else:
            variants_data[canonical] = [variant]
        
        # Save to writable file
        try:
            write_file.parent.mkdir(parents=True, exist_ok=True)
            with open(write_file, 'w', encoding='utf-8') as f:
                for canonical_word, variant_list in variants_data.items():
                    entry = {
                        "canonical": canonical_word,
                        "variants": variant_list
                    }
                    f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            # Clear cache so normalizer uses updated data
            clear_cache()
            return len(variants_data)
        except Exception as e:
            print(f"Error saving variant words: {e}")
            return None
    
    def get_linked_words(self):
        """Get all linked words from the JSON file"""
        linked_words_file = _get_data_file_path("linked_words.json")
        try:
            if linked_words_file.exists():
                with open(linked_words_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return []
    
    def get_variant_words(self):
        """Get all variant words from the JSONL file"""
        variants_file = _get_data_file_path("hassaniya_variants.jsonl")
        variants = []
        try:
            if variants_file.exists():
                with open(variants_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            variants.append(json.loads(line))
        except Exception:
            pass
        return variants
    
    def delete_linked_word(self, wrong: str, correct: str):
        """Delete a linked word pair from the JSON file"""
        # Read from existing location first
        read_file = _get_data_file_path("linked_words.json")
        write_file = _get_writable_data_path("linked_words.json")
        
        try:
            if read_file.exists():
                with open(read_file, 'r', encoding='utf-8') as f:
                    linked_words = json.load(f)
                
                # Remove the entry
                linked_words = [item for item in linked_words 
                              if not (item.get("wrong") == wrong and item.get("correct") == correct)]
                
                # Save back to writable file
                write_file.parent.mkdir(parents=True, exist_ok=True)
                with open(write_file, 'w', encoding='utf-8') as f:
                    json.dump(linked_words, f, ensure_ascii=False, indent=2)
                
                return True
        except Exception as e:
            print(f"Error deleting linked word: {e}")
            return False
        return False
    
    def delete_variant_word(self, canonical: str, variant: str = None):
        """Delete a variant word or entire canonical entry from the JSONL file"""
        # Read from existing location first
        read_file = _get_data_file_path("hassaniya_variants.jsonl")
        write_file = _get_writable_data_path("hassaniya_variants.jsonl")
        
        try:
            if read_file.exists():
                variants_data = {}
                with open(read_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            entry = json.loads(line)
                            variants_data[entry["canonical"]] = entry["variants"]
                
                # Remove variant or entire canonical entry
                if canonical in variants_data:
                    if variant and variant in variants_data[canonical]:
                        # Remove specific variant
                        variants_data[canonical].remove(variant)
                        # If no variants left, remove the canonical entry
                        if not variants_data[canonical]:
                            del variants_data[canonical]
                    else:
                        # Remove entire canonical entry
                        del variants_data[canonical]
                
                # Save back to writable file
                write_file.parent.mkdir(parents=True, exist_ok=True)
                with open(write_file, 'w', encoding='utf-8') as f:
                    for canonical_word, variant_list in variants_data.items():
                        entry = {
                            "canonical": canonical_word,
                            "variants": variant_list
                        }
                        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
                
                return True
        except Exception as e:
            print(f"Error deleting variant word: {e}")
            return False
        return False
    
    def reset_user_stats(self, username: str) -> bool:
        """Reset all statistics for a specific user."""
        try:
            # Remove user's recordings
            self.recordings = [r for r in self.recordings if r["user"] != username]
            
            # Reset user's paragraph assignments and completions
            for paragraph in self.paragraphs:
                if paragraph["assigned_to"] == username:
                    paragraph["assigned_to"] = None
                    paragraph["status"] = "unassigned"
                    paragraph["text_final"] = None
            
            # Remove user's audio files
            import glob
            audio_files = glob.glob(f"data/audio/*{username}*")
            for file_path in audio_files:
                try:
                    os.remove(file_path)
                except OSError:
                    pass  # File might not exist or be in use
            
            return True
        except Exception:
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        total = len(self.paragraphs)
        assigned = len([p for p in self.paragraphs if p["status"] == "assigned"])
        completed = len([p for p in self.paragraphs if p["status"] == "done"])
        skipped = len([p for p in self.paragraphs if p["status"] == "skipped"])
        
        # Calculate user statistics with more precise minute tracking
        user_stats = {}
        user_recording_times = {}  # Track actual recording durations
        
        for recording in self.recordings:
            user = recording["user"]
            if user not in user_stats:
                user_stats[user] = {
                    "recordings": 0,
                    "paragraphs_completed": 0,
                    "transcription_minutes": 0.0
                }
            user_stats[user]["recordings"] += 1
            
            # Try to get actual audio duration, fallback to estimate
            audio_duration = self._get_audio_duration(recording.get("filename", ""))
            user_stats[user]["transcription_minutes"] += audio_duration
        
        for paragraph in self.paragraphs:
            if paragraph["status"] == "done" and paragraph["assigned_to"]:
                user = paragraph["assigned_to"]
                if user not in user_stats:
                    user_stats[user] = {
                        "recordings": 0,
                        "paragraphs_completed": 0,
                        "transcription_minutes": 0.0
                    }
                user_stats[user]["paragraphs_completed"] += 1

        
        return {
            "total_paragraphs": total,
            "assigned_paragraphs": assigned,
            "completed_paragraphs": completed,
            "skipped_paragraphs": skipped,
            "total_recordings": len(self.recordings),
            "total_recording_minutes": sum(user_stats[user]["transcription_minutes"] for user in user_stats),
            "user_stats": user_stats
        }
    
    def _get_audio_duration(self, filename: str) -> float:
        """Get audio file duration in minutes. Fallback to estimate if file not accessible."""
        if not filename:
            return 2.5  # Default estimate
        
        try:
            file_path = AUDIO_DIR / filename
            if file_path.exists():
                # Try to get actual duration using file size estimation
                # WebM files are roughly 1KB per second of audio
                file_size_kb = file_path.stat().st_size / 1024
                duration_seconds = file_size_kb  # Rough estimate
                return max(0.5, min(10.0, duration_seconds / 60))  # Clamp between 0.5-10 minutes
            else:
                return 2.5  # Default estimate
        except Exception:
            return 2.5  # Default estimate

# Global storage instance
storage = SimpleStorage()

# Ensure data directories exist
DATA_DIR = Path("data")
AUDIO_DIR = DATA_DIR / "audio"
DATA_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)

# Users that can login
USERS = ["EMIN", "ETHMAN", "ZAIN", "MOUHAMEDOU"]

# API Models
class NormalizationRequest(BaseModel):
    text: str
    show_diff: bool = False

class ParagraphSubmission(BaseModel):
    text_final: str

class VariantReport(BaseModel):
    word: str
    suggestion: str
    reporter: str

class LinkedWordReport(BaseModel):
    wrong: str
    correct: str
    reporter: str

class VariantWordReport(BaseModel):
    canonical: str
    variant: str
    reporter: str

# Create FastAPI app
app = FastAPI(
    title="Hassaniya Unified Platform",
    description="Complete platform for Hassaniya Arabic recording, normalization, and management",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def authenticate_user(username: str) -> bool:
    """Check if user is valid."""
    return username in USERS

@app.get("/healthz")
async def health_check():
    """Health check endpoint for Docker and deployment platforms."""
    return {"status": "healthy", "service": "hassaniya-normalizer"}

@app.get("/", response_class=HTMLResponse)
async def serve_login_page():
    """Serve the login page."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hassaniya Platform - Login</title>
    <style>
        * { 
            margin: 0; 
            padding: 0; 
            box-sizing: border-box; 
        }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            min-height: 100vh; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .login-container { 
            padding: 40px; 
            background: white; 
            border-radius: 12px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); 
            max-width: 400px; 
            width: 100%; 
            text-align: center; 
        }
        .login-container h1 { 
            color: #333; 
            margin-bottom: 10px; 
            font-size: 2em;
        }
        .login-container p { 
            color: #666; 
            margin-bottom: 30px; 
        }
        input[type="text"] { 
            width: 100%; 
            padding: 15px; 
            margin: 10px 0; 
            border-radius: 8px; 
            border: 2px solid #e1e1e1; 
            font-size: 16px;
            transition: border-color 0.3s ease;
        }
        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
        }
        button { 
            width: 100%; 
            padding: 15px; 
            margin: 15px 0;
            border-radius: 8px; 
            border: none;
            background-color: #667eea; 
            color: white; 
            font-size: 16px;
            font-weight: 600;
            cursor: pointer; 
            transition: all 0.3s ease;
        }
        button:hover { 
            background-color: #5a6fd8; 
            transform: translateY(-2px);
        }
        .error { 
            color: #e74c3c; 
            margin-top: 10px;
            font-weight: 500;
        }
        .users-list {
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }
        .users-list h3 {
            color: #666;
            font-size: 14px;
            margin-bottom: 10px;
        }
        .user-pills {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            justify-content: center;
        }
        .user-pill {
            background: #f8f9fa;
            color: #495057;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .user-pill:hover {
            background: #667eea;
            color: white;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>🎤 Hassaniya Platform</h1>
        <p>Please enter your username to access the recording platform</p>
        <input type="text" id="username" placeholder="Enter your username" maxlength="20">
        <button onclick="login()">Login</button>
        <div id="error" class="error"></div>
        
        <div class="users-list">
            <h3>Authorized Users:</h3>
            <div class="user-pills">
                <span class="user-pill" onclick="selectUser('EMIN')">EMIN</span>
                <span class="user-pill" onclick="selectUser('ETHMAN')">ETHMAN</span>
                <span class="user-pill" onclick="selectUser('ZAIN')">ZAIN</span>
                <span class="user-pill" onclick="selectUser('MOUHAMEDOU')">MOUHAMEDOU</span>
            </div>
        </div>
    </div>
    
    <script>
        function selectUser(username) {
            document.getElementById('username').value = username;
            document.getElementById('error').textContent = '';
        }
        
        function login() {
            const username = document.getElementById('username').value.trim().toUpperCase();
            if (!username) {
                document.getElementById('error').textContent = 'Please enter a username';
                return;
            }
            
            const validUsers = ['EMIN', 'ETHMAN', 'ZAIN', 'MOUHAMEDOU'];
            if (!validUsers.includes(username)) {
                document.getElementById('error').textContent = 'Invalid username. Please select from authorized users.';
                return;
            }
            
            localStorage.setItem('username', username);
            window.location.href = '/dashboard';
        }
        
        // Check if user is already logged in
        if (localStorage.getItem('username')) {
            window.location.href = '/dashboard';
        }
        
        // Allow Enter key to login
        document.getElementById('username').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                login();
            }
        });
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)

@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the main dashboard."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hassaniya Platform</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background-color: #f8fafc;
            color: #334155;
            line-height: 1.6;
        }
        
        .container {
            display: flex;
            min-height: 100vh;
        }
        
        /* Sidebar */
        .sidebar {
            width: 280px;
            background: white;
            border-right: 1px solid #e2e8f0;
            padding: 24px 0;
            display: flex;
            flex-direction: column;
        }
        
        .logo {
            display: flex;
            align-items: center;
            padding: 0 24px 24px;
            margin-bottom: 24px;
            border-bottom: 1px solid #e2e8f0;
        }
        
        .logo-icon {
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 12px;
            color: white;
            font-size: 20px;
        }
        
        .logo-text {
            font-size: 20px;
            font-weight: 600;
            color: #1e293b;
        }
        
        .nav {
            flex: 1;
            padding: 0 16px;
        }
        
        .nav-item {
            display: flex;
            align-items: center;
            padding: 12px 16px;
            margin: 4px 0;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
            color: #64748b;
            font-weight: 500;
        }
        
        .nav-item:hover {
            background-color: #f1f5f9;
            color: #334155;
        }
        
        .nav-item.active {
            background-color: #10b981;
            color: white;
        }
        
        .nav-icon {
            width: 20px;
            height: 20px;
            margin-right: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .user-info {
            padding: 16px 24px;
            border-top: 1px solid #e2e8f0;
            margin-top: auto;
        }
        
        .user-avatar {
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            margin-right: 12px;
        }
        
        .user-name {
            font-weight: 600;
            color: #1e293b;
        }
        
        .logout-btn {
            background: none;
            border: none;
            color: #64748b;
            cursor: pointer;
            font-size: 12px;
            margin-top: 4px;
        }
        
        /* Main Content */
        .main-content {
            flex: 1;
            padding: 32px;
            overflow-y: auto;
        }
        
        .content-area {
            display: none;
        }
        
        .content-area.active {
            display: block;
        }
        
        .page-header {
            margin-bottom: 32px;
        }
        
        .page-title {
            font-size: 28px;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 8px;
        }
        
        .page-description {
            color: #64748b;
            font-size: 16px;
        }
        
        .card {
            background: white;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
        }
        
        .card-title {
            font-size: 18px;
            font-weight: 600;
            color: #1e293b;
            margin-bottom: 16px;
        }
        
        /* Upload Area */
        .upload-area {
            border: 2px dashed #cbd5e1;
            border-radius: 12px;
            padding: 48px 24px;
            text-align: center;
            background: #f8fafc;
            transition: all 0.3s;
            cursor: pointer;
        }
        
        .upload-area:hover {
            border-color: #10b981;
            background: #f0fdf4;
        }
        
        .upload-icon {
            width: 48px;
            height: 48px;
            background: #e2e8f0;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 16px;
            color: #64748b;
            font-size: 20px;
        }
        
        .upload-title {
            font-size: 18px;
            font-weight: 600;
            color: #1e293b;
            margin-bottom: 8px;
        }
        
        .upload-description {
            color: #64748b;
            margin-bottom: 24px;
        }
        
        /* Buttons */
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 12px 24px;
            border-radius: 8px;
            border: none;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            text-decoration: none;
            font-size: 14px;
        }
        
        .btn-primary {
            background: #10b981;
            color: white;
        }
        
        .btn-primary:hover {
            background: #059669;
            transform: translateY(-1px);
        }
        
        .btn-secondary {
            background: #f1f5f9;
            color: #475569;
            border: 1px solid #e2e8f0;
        }
        
        .btn-secondary:hover {
            background: #e2e8f0;
        }
        
        .btn-danger {
            background: #ef4444;
            color: white;
        }
        
        .btn-danger:hover {
            background: #dc2626;
        }
        
        .btn-icon {
            margin-right: 8px;
        }
        
        /* Form Elements */
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-label {
            display: block;
            font-weight: 600;
            color: #374151;
            margin-bottom: 8px;
        }
        
        .form-input {
            width: 100%;
            padding: 12px 16px;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.2s;
        }
        
        .form-input:focus {
            outline: none;
            border-color: #10b981;
            box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1);
        }
        
        .form-textarea {
            width: 100%;
            padding: 12px 16px;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            font-size: 14px;
            resize: vertical;
            min-height: 120px;
            font-family: inherit;
        }
        
        .form-textarea:focus {
            outline: none;
            border-color: #10b981;
            box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1);
        }
        
        /* Status Messages */
        .status {
            padding: 12px 16px;
            border-radius: 8px;
            margin: 16px 0;
            font-weight: 500;
        }
        
        .status-success {
            background: #d1fae5;
            color: #065f46;
            border: 1px solid #a7f3d0;
        }
        
        .status-error {
            background: #fee2e2;
            color: #991b1b;
            border: 1px solid #fca5a5;
        }
        
        .status-warning {
            background: #fef3c7;
            color: #92400e;
            border: 1px solid #fde68a;
        }
        
        .status-info {
            background: #dbeafe;
            color: #1e40af;
            border: 1px solid #93c5fd;
        }
        
        /* Statistics */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 32px;
        }
        
        .stat-card {
            background: white;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            padding: 24px;
            text-align: center;
        }
        
        .stat-number {
            font-size: 32px;
            font-weight: 700;
            color: #10b981;
            margin-bottom: 8px;
        }
        
        .stat-label {
            color: #64748b;
            font-weight: 500;
        }
        
        /* Recording Interface */
        .recording-interface {
            text-align: center;
            padding: 40px 20px;
        }
        
        .record-button {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            border: none;
            margin: 20px auto;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .record-button.recording {
            background: #ef4444;
            color: white;
            animation: pulse 2s infinite;
        }
        
        .record-button.stopped {
            background: #10b981;
            color: white;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .container {
                flex-direction: column;
            }
            
            .sidebar {
                width: 100%;
                border-right: none;
                border-bottom: 1px solid #e2e8f0;
            }
            
            .main-content {
                padding: 16px;
            }
        }
        
        .hidden {
            display: none !important;
        }
        
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <div class="logo">
                <div class="logo-icon">🎤</div>
                <div class="logo-text">Hassaniya</div>
            </div>
            
            <nav class="nav">
                <div class="nav-item active" onclick="showPage('dashboard')">
                    <div class="nav-icon">📊</div>
                    Dashboard
                </div>
                <div class="nav-item" onclick="showPage('record')">
                    <div class="nav-icon">🎙️</div>
                    Record
                </div>
                <div class="nav-item" onclick="showPage('normalize')">
                    <div class="nav-icon">📝</div>
                    Normalize
                </div>
                <div class="nav-item" onclick="showPage('upload')">
                    <div class="nav-icon">📤</div>
                    Upload Text
                </div>
                <div class="nav-item" onclick="showPage('export')">
                    <div class="nav-icon">💾</div>
                    Export
                </div>
                <div class="nav-item" onclick="showPage('statistics')">
                    <div class="nav-icon">📈</div>
                    Statistics
                </div>
                <div class="nav-item" onclick="showPage('variants')">
                    <div class="nav-icon">🔤</div>
                    Variants
                </div>
            </nav>
            
            <div class="user-info">
                <div style="display: flex; align-items: center;">
                    <div class="user-avatar" id="userAvatar">U</div>
                    <div>
                        <div class="user-name" id="userName">User</div>
                        <button class="logout-btn" onclick="logout()">Logout</button>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="main-content">
            <!-- Dashboard Page -->
            <div id="dashboard" class="content-area active">
                <div class="page-header">
                    <h1 class="page-title">Dashboard</h1>
                    <p class="page-description">Overview of your recording progress and platform statistics</p>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number" id="totalParagraphs">0</div>
                        <div class="stat-label">Total Paragraphs</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" id="completedParagraphs">0</div>
                        <div class="stat-label">Completed</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" id="userRecordings">0</div>
                        <div class="stat-label">Your Recordings</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" id="recordingMinutes">0</div>
                        <div class="stat-label">Minutes Recorded</div>
                    </div>
                </div>
                
                <div class="card">
                    <h3 class="card-title">User Actions</h3>
                    <button class="btn btn-danger" onclick="resetUserStats()" style="margin: 8px;">
                        <span class="btn-icon">🗑️</span> Reset My Statistics
                    </button>
                </div>
                
                <div class="card">
                    <h3 class="card-title">Recent Activity</h3>
                    <div id="recentActivity">Loading recent activity...</div>
                </div>
            </div>
            
            <!-- Record Page -->
            <div id="record" class="content-area">
                <div class="page-header">
                    <h1 class="page-title">Record Audio</h1>
                    <p class="page-description">Record Hassaniya Arabic speech for the assigned text</p>
                </div>
                
                <div class="card">
                    <h3 class="card-title">Text to Record</h3>
                    <textarea id="textToRecord" class="form-textarea" readonly placeholder="Loading text to record..."></textarea>
                    <button class="btn btn-secondary" onclick="loadNextParagraph()" style="margin-top: 16px;">
                        <span class="btn-icon">🔄</span> Load Next Text
                    </button>
                </div>
                
                <div class="card">
                    <h3 class="card-title">Recording Controls</h3>
                    <div class="recording-interface">
                        <button class="record-button stopped" id="recordBtn" onclick="toggleRecording()">
                            <span id="recordIcon">🔴</span>
                        </button>
                        <div style="margin: 20px 0;">
                            <button class="btn btn-secondary" onclick="skipText()" style="margin: 0 8px;">
                                <span class="btn-icon">⏭️</span> Skip
                            </button>
                            <button class="btn btn-primary" onclick="submitRecording()" style="margin: 0 8px;">
                                <span class="btn-icon">✅</span> Submit
                            </button>
                        </div>
                        <div class="status status-info" id="recordStatus">Ready to record</div>
                    </div>
                </div>
                
                <div class="card">
                    <h3 class="card-title">Edit Text (Optional)</h3>
                    <textarea id="editedText" class="form-textarea" placeholder="Make any corrections to the text here..."></textarea>
                </div>
            </div>
            
            <!-- Normalize Page -->
            <div id="normalize" class="content-area">
                <div class="page-header">
                    <h1 class="page-title">Text Normalization</h1>
                    <p class="page-description">Normalize Hassaniya Arabic text to standard form</p>
                </div>
                
                <div class="card">
                    <h3 class="card-title">Input Text</h3>
                    <textarea id="inputText" class="form-textarea" placeholder="Enter Hassaniya Arabic text to normalize..."></textarea>
                    <div style="margin-top: 16px;">
                        <button class="btn btn-primary" onclick="normalizeText()">
                            <span class="btn-icon">🔄</span> Normalize
                        </button>
                        <button class="btn btn-secondary" onclick="showDiff()">
                            <span class="btn-icon">🔍</span> Show Diff
                        </button>
                    </div>
                </div>
                
                <div class="card">
                    <h3 class="card-title">Normalized Result</h3>
                    <textarea id="outputText" class="form-textarea" readonly placeholder="Normalized text will appear here..."></textarea>
                </div>
                
                <div class="card hidden" id="diffSection">
                    <h3 class="card-title">Differences</h3>
                    <div id="diffOutput" style="background: #f8fafc; padding: 16px; border-radius: 8px; font-family: monospace;"></div>
                </div>
            </div>
            
            <!-- Upload Page -->
            <div id="upload" class="content-area">
                <div class="page-header">
                    <h1 class="page-title">Upload Text</h1>
                    <p class="page-description">Upload text files to create recording assignments</p>
                </div>
                
                <div class="card">
                    <h3 class="card-title">Select Text File</h3>
                    <div class="upload-area" onclick="document.getElementById('fileInput').click()">
                        <div class="upload-icon">📄</div>
                        <div class="upload-title">Select Text File</div>
                        <div class="upload-description">Upload a text file containing paragraphs to be recorded (.txt format)</div>
                        <button class="btn btn-primary">
                            <span class="btn-icon">📤</span> Choose File
                        </button>
                        <input type="file" id="fileInput" accept=".txt" style="display: none;" onchange="uploadFile()">
                    </div>
                    <div id="uploadStatus"></div>
                </div>
            </div>
            
            <!-- Export Page -->
            <div id="export" class="content-area">
                <div class="page-header">
                    <h1 class="page-title">Export Data</h1>
                    <p class="page-description">Download recordings and statistics for analysis</p>
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 24px;">
                    <div class="card">
                        <h3 class="card-title">Export Recordings</h3>
                        <p style="color: #64748b; margin-bottom: 20px;">Download all recordings with metadata in Whisper-compatible format</p>
                        <button class="btn btn-primary" onclick="exportRecordings()">
                            <span class="btn-icon">💾</span> Export Recordings
                        </button>
                    </div>
                    
                    <div class="card">
                        <h3 class="card-title">Export Statistics</h3>
                        <p style="color: #64748b; margin-bottom: 20px;">Download comprehensive platform statistics and user data</p>
                        <button class="btn btn-secondary" onclick="exportStats()">
                            <span class="btn-icon">📊</span> Export Statistics
                        </button>
                    </div>
                </div>
            </div>
            
            <!-- Statistics Page -->
            <div id="statistics" class="content-area">
                <div class="page-header">
                    <h1 class="page-title">Statistics</h1>
                    <p class="page-description">Detailed platform and user statistics</p>
                </div>
                
                <div class="card">
                    <h3 class="card-title">Platform Overview</h3>
                    <div id="detailedStats">Loading statistics...</div>
                </div>
            </div>
            
            <!-- Variants Page -->
            <div id="variants" class="content-area">
                <div class="page-header">
                    <h1 class="page-title">Variants Management</h1>
                    <p class="page-description">Manage linked words and variant words for real-time updates</p>
                </div>
                
                <!-- Linked Words Section -->
                <div class="card">
                    <h3 class="card-title">Linked Words (Wrong → Correct)</h3>
                    <p style="color: #64748b; margin-bottom: 20px;">Add word corrections that will be saved to linked_words.json</p>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr auto; gap: 12px; margin-bottom: 20px; align-items: end;">
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-weight: 500; color: #374151;">Wrong Word:</label>
                            <input type="text" id="wrongWord" class="form-input" placeholder="Enter wrong word" style="width: 100%;">
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-weight: 500; color: #374151;">Correct Word:</label>
                            <input type="text" id="correctWord" class="form-input" placeholder="Enter correct word" style="width: 100%;">
                        </div>
                        <button class="btn btn-primary" onclick="addLinkedWord()" style="height: 44px;">
                            <span class="btn-icon">➕</span> Add
                        </button>
                    </div>
                    
                    <div id="linkedWordStatus" class="status status-info" style="display: none;"></div>
                    
                    <div style="margin-top: 24px;">
                        <h4 style="margin-bottom: 12px; color: #374151;">Current Linked Words:</h4>
                        <div id="linkedWordsList" style="max-height: 300px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px;">
                            Loading linked words...
                        </div>
                    </div>
                </div>
                
                <!-- Variant Words Section -->
                <div class="card">
                    <h3 class="card-title">Variant Words (Canonical → Variant)</h3>
                    <p style="color: #64748b; margin-bottom: 20px;">Add word variants that will be saved to hassaniya_variants.jsonl</p>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr auto; gap: 12px; margin-bottom: 20px; align-items: end;">
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-weight: 500; color: #374151;">Canonical Word:</label>
                            <input type="text" id="canonicalWord" class="form-input" placeholder="Enter canonical word" style="width: 100%;">
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-weight: 500; color: #374151;">Variant Word:</label>
                            <input type="text" id="variantWord" class="form-input" placeholder="Enter variant word" style="width: 100%;">
                        </div>
                        <button class="btn btn-primary" onclick="addVariantWord()" style="height: 44px;">
                            <span class="btn-icon">➕</span> Add
                        </button>
                    </div>
                    
                    <div id="variantWordStatus" class="status status-info" style="display: none;"></div>
                    
                    <div style="margin-top: 24px;">
                        <h4 style="margin-bottom: 12px; color: #374151;">Current Variant Words:</h4>
                        <div id="variantWordsList" style="max-height: 300px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px;">
                            Loading variant words...
                        </div>
                    </div>
                </div>
                
                <!-- Grammar Variants Section (Existing) -->
                <div class="card">
                    <h3 class="card-title">Grammar Variants (Existing Feature)</h3>
                    <p style="color: #64748b; margin-bottom: 20px;">Report grammar variants and suggestions</p>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr auto; gap: 12px; margin-bottom: 20px; align-items: end;">
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-weight: 500; color: #374151;">Word:</label>
                            <input type="text" id="variantReportWord" class="form-input" placeholder="Enter word" style="width: 100%;">
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-weight: 500; color: #374151;">Suggestion:</label>
                            <input type="text" id="variantReportSuggestion" class="form-input" placeholder="Enter suggestion" style="width: 100%;">
                        </div>
                        <button class="btn btn-primary" onclick="addVariantReport()" style="height: 44px;">
                            <span class="btn-icon">📝</span> Report
                        </button>
                    </div>
                    
                    <div id="variantReportStatus" class="status status-info" style="display: none;"></div>
                    
                    <div style="margin-top: 24px;">
                        <h4 style="margin-bottom: 12px; color: #374151;">Current Grammar Variants:</h4>
                        <div id="grammarVariantsList" style="max-height: 300px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px;">
                            Loading grammar variants...
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Check login status
        const currentUser = localStorage.getItem('username');
        if (!currentUser) {
            window.location.href = '/';
        }
        
        // Set current user context
        let currentUsername = currentUser;
        document.getElementById('userName').textContent = currentUsername;
        document.getElementById('userAvatar').textContent = currentUsername.charAt(0);
        
        let isRecording = false;
        let mediaRecorder;
        let audioChunks = [];
        let currentParagraph = null;
        
        // Navigation
        function showPage(pageId) {
            // Hide all pages
            document.querySelectorAll('.content-area').forEach(area => {
                area.classList.remove('active');
            });
            
            // Remove active class from nav items
            document.querySelectorAll('.nav-item').forEach(item => {
                item.classList.remove('active');
            });
            
            // Show selected page
            document.getElementById(pageId).classList.add('active');
            
            // Add active class to clicked nav item
            event.target.closest('.nav-item').classList.add('active');
            
            // Load data for specific pages
            if (pageId === 'dashboard') {
                loadStats();
            }
            if (pageId === 'variants') {
                loadLinkedWords();
                loadVariantWords();
                loadGrammarVariants();
            }
        }
        
        function logout() {
            localStorage.removeItem('username');
            window.location.href = '/';
        }
        
        // Recording functions
        async function toggleRecording() {
            const btn = document.getElementById('recordBtn');
            const icon = document.getElementById('recordIcon');
            const status = document.getElementById('recordStatus');
            
            if (!isRecording) {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    mediaRecorder = new MediaRecorder(stream);
                    audioChunks = [];
                    
                    mediaRecorder.ondataavailable = event => {
                        audioChunks.push(event.data);
                    };
                    
                    mediaRecorder.start();
                    isRecording = true;
                    icon.textContent = '⏹️';
                    btn.className = 'record-button recording';
                    status.textContent = 'Recording... 🎙️';
                    status.className = 'status status-success';
                } catch (error) {
                    status.textContent = 'Error: Could not access microphone';
                    status.className = 'status status-error';
                }
            } else {
                mediaRecorder.stop();
                isRecording = false;
                icon.textContent = '🔴';
                btn.className = 'record-button stopped';
                status.textContent = 'Recording stopped. Ready to submit.';
                status.className = 'status status-info';
            }
        }
        
        async function loadNextParagraph() {
            const username = currentUsername;
            
            document.getElementById('textToRecord').value = 'Loading next paragraph...';
            
            try {
                const response = await fetch(`/api/para/next?username=${username}`);
                if (response.ok) {
                    currentParagraph = await response.json();
                    document.getElementById('textToRecord').value = currentParagraph.text_original;
                    document.getElementById('editedText').value = currentParagraph.text_original;
                    
                    const status = document.getElementById('recordStatus');
                    status.textContent = `Paragraph ${currentParagraph.id} ready to record`;
                    status.className = 'status status-info';
                } else {
                    document.getElementById('textToRecord').value = 'No more paragraphs available';
                    const status = document.getElementById('recordStatus');
                    status.textContent = 'No paragraphs available';
                    status.className = 'status status-warning';
                }
            } catch (error) {
                console.error('Error loading paragraph:', error);
                document.getElementById('textToRecord').value = 'Error loading paragraph';
                const status = document.getElementById('recordStatus');
                status.textContent = 'Error loading paragraph';
                status.className = 'status status-error';
            }
        }
        
        async function skipText() {
            if (!currentParagraph) return;
            
            try {
                await fetch(`/api/para/${currentParagraph.id}/skip?username=${currentUsername}`, {
                    method: 'POST'
                });
                
                const status = document.getElementById('recordStatus');
                status.textContent = 'Paragraph skipped';
                status.className = 'status status-warning';
                
                setTimeout(loadNextParagraph, 1000);
            } catch (error) {
                console.error('Error skipping paragraph:', error);
            }
        }
        
        async function submitRecording() {
            if (!currentParagraph || audioChunks.length === 0) {
                const status = document.getElementById('recordStatus');
                status.textContent = 'No recording to submit';
                status.className = 'status status-warning';
                return;
            }
            
            try {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                const formData = new FormData();
                formData.append('username', currentUsername);
                formData.append('text_final', document.getElementById('editedText').value);
                formData.append('audio_file', audioBlob, 'recording.webm');
                
                const response = await fetch(`/api/para/${currentParagraph.id}/submit`, {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    const status = document.getElementById('recordStatus');
                    status.textContent = 'Recording submitted successfully!';
                    status.className = 'status status-success';
                    audioChunks = [];
                    setTimeout(loadNextParagraph, 1000);
                } else {
                    throw new Error('Submission failed');
                }
            } catch (error) {
                console.error('Error submitting recording:', error);
                const status = document.getElementById('recordStatus');
                status.textContent = 'Error submitting recording';
                status.className = 'status status-error';
            }
        }
        
        // Normalization functions
        async function normalizeText() {
            const input = document.getElementById('inputText').value;
            if (!input.trim()) {
                alert('Please enter some text to normalize');
                return;
            }
            
            try {
                const response = await fetch('/api/normalize', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: input, show_diff: true })
                });
                
                if (response.ok) {
                    const result = await response.json();
                    document.getElementById('outputText').value = result.normalized;
                    
                    // Automatically show diff if there are changes
                    if (result.diff_html || input !== result.normalized) {
                        showDiffVisualization(result.original, result.normalized, result.changes);
                    } else {
                        hideDiffVisualization();
                    }
                }
            } catch (error) {
                console.error('Error normalizing text:', error);
            }
        }
        
        function showDiffVisualization(original, normalized, changes) {
            const diffSection = document.getElementById('diffSection');
            const diffOutput = document.getElementById('diffOutput');
            
            // Create visual diff
            const originalWords = original.split(' ');
            const normalizedWords = normalized.split(' ');
            
            let diffHtml = '<div style="margin-bottom: 20px;">';
            diffHtml += '<h4 style="margin-bottom: 10px; color: #374151;">Original Text:</h4>';
            diffHtml += '<div style="padding: 12px; background: #f9fafb; border-radius: 6px; margin-bottom: 15px; line-height: 1.6;">';
            
            // Highlight original words that will be changed
            originalWords.forEach((word, index) => {
                if (normalizedWords[index] && word !== normalizedWords[index]) {
                    diffHtml += `<span style="background: #fef3c7; padding: 2px 4px; border-radius: 3px; margin: 1px;">${word}</span> `;
                } else {
                    diffHtml += `${word} `;
                }
            });
            
            diffHtml += '</div>';
            diffHtml += '<h4 style="margin-bottom: 10px; color: #374151;">Normalized Text:</h4>';
            diffHtml += '<div style="padding: 12px; background: #f0fdf4; border-radius: 6px; line-height: 1.6;">';
            
            // Highlight normalized words that were changed
            normalizedWords.forEach((word, index) => {
                if (originalWords[index] && word !== originalWords[index]) {
                    diffHtml += `<span style="background: #bbf7d0; color: #065f46; padding: 2px 6px; border-radius: 3px; margin: 1px; font-weight: 500;">${word}</span> `;
                } else {
                    diffHtml += `${word} `;
                }
            });
            
            diffHtml += '</div></div>';
            
            // Add change summary
            const changedWords = originalWords.filter((word, index) => 
                normalizedWords[index] && word !== normalizedWords[index]
            ).length;
            
            if (changedWords > 0) {
                diffHtml += `<div style="padding: 10px; background: #dbeafe; border-radius: 6px; border-left: 4px solid #3b82f6;">`;
                diffHtml += `<strong>Changes:</strong> ${changedWords} word${changedWords > 1 ? 's' : ''} normalized`;
                diffHtml += '</div>';
            } else {
                diffHtml += `<div style="padding: 10px; background: #f0fdf4; border-radius: 6px; border-left: 4px solid #10b981;">`;
                diffHtml += '<strong>No changes:</strong> Text is already normalized';
                diffHtml += '</div>';
            }
            
            diffOutput.innerHTML = diffHtml;
            diffSection.classList.remove('hidden');
        }
        
        function hideDiffVisualization() {
            const diffSection = document.getElementById('diffSection');
            diffSection.classList.add('hidden');
        }
        
        function showDiff() {
            const input = document.getElementById('inputText').value;
            const output = document.getElementById('outputText').value;
            
            if (!input || !output) {
                alert('Please normalize text first');
                return;
            }
            
            showDiffVisualization(input, output);
        }
        
        // Upload function
        async function uploadFile() {
            const fileInput = document.getElementById('fileInput');
            const file = fileInput.files[0];
            
            if (!file) return;
            
            const statusDiv = document.getElementById('uploadStatus');
            statusDiv.innerHTML = '<div class="status status-info">Uploading file...</div>';
            
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const response = await fetch('/api/text/upload', {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    const result = await response.json();
                    statusDiv.innerHTML = `<div class="status status-success">Successfully uploaded ${result.paragraphs_added} paragraphs</div>`;
                    loadStats();
                } else {
                    throw new Error('Upload failed');
                }
            } catch (error) {
                statusDiv.innerHTML = '<div class="status status-error">Error uploading file</div>';
            }
        }
        
        // Export functions
        async function exportRecordings() {
            try {
                const response = await fetch('/api/export/recordings');
                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `hassaniya_recordings_${new Date().toISOString().split('T')[0]}.zip`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);
                }
            } catch (error) {
                console.error('Export error:', error);
            }
        }
        
        async function exportStats() {
            try {
                const response = await fetch('/api/export/statistics');
                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `hassaniya_statistics_${new Date().toISOString().split('T')[0]}.zip`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);
                }
            } catch (error) {
                console.error('Export error:', error);
            }
        }
        
        // Statistics function
        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                if (response.ok) {
                    const stats = await response.json();
                    
                    document.getElementById('totalParagraphs').textContent = stats.total_paragraphs;
                    document.getElementById('completedParagraphs').textContent = stats.completed_paragraphs;
                    
                    // User-specific stats
                    const userStats = stats.user_stats[currentUsername] || { recordings: 0, transcription_minutes: 0 };
                    document.getElementById('userRecordings').textContent = userStats.recordings;
                    document.getElementById('recordingMinutes').textContent = Math.round(userStats.transcription_minutes);
                    
                    // Detailed stats
                    const detailedStats = document.getElementById('detailedStats');
                    detailedStats.innerHTML = `
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;">
                            <div style="padding: 16px; background: #f8fafc; border-radius: 8px;">
                                <div style="font-weight: 600; color: #1e293b;">Assigned</div>
                                <div style="font-size: 24px; color: #10b981;">${stats.assigned_paragraphs}</div>
                            </div>
                            <div style="padding: 16px; background: #f8fafc; border-radius: 8px;">
                                <div style="font-weight: 600; color: #1e293b;">Skipped</div>
                                <div style="font-size: 24px; color: #f59e0b;">${stats.skipped_paragraphs}</div>
                            </div>
                            <div style="padding: 16px; background: #f8fafc; border-radius: 8px;">
                                <div style="font-weight: 600; color: #1e293b;">Total Recordings</div>
                                <div style="font-size: 24px; color: #3b82f6;">${stats.total_recordings}</div>
                            </div>
                        </div>
                    `;
                }
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        }
        
        // Reset user statistics function
        async function resetUserStats() {
            if (!confirm('Are you sure you want to reset all your statistics? This action cannot be undone and will delete all your recordings and progress.')) {
                return;
            }
            
            try {
                const response = await fetch(`/api/users/${currentUsername}/stats`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    alert('Your statistics have been reset successfully!');
                    // Reload the stats to show updated values
                    loadStats();
                } else {
                    const errorData = await response.json();
                    alert(`Error resetting statistics: ${errorData.detail || 'Unknown error'}`);
                }
            } catch (error) {
                console.error('Error resetting statistics:', error);
                alert('Error resetting statistics. Please try again.');
            }
        }
        
        // Variants functions
        async function addLinkedWord() {
            const wrong = document.getElementById('wrongWord').value.trim();
            const correct = document.getElementById('correctWord').value.trim();
            
            if (!wrong || !correct) {
                alert('Please fill in both fields');
                return;
            }
            
            try {
                const response = await fetch('/api/linked_words', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        wrong: wrong,
                        correct: correct,
                        reporter: currentUsername
                    })
                });
                
                if (response.ok) {
                    document.getElementById('wrongWord').value = '';
                    document.getElementById('correctWord').value = '';
                    alert('Linked word added successfully!');
                    loadLinkedWords();
                } else {
                    alert('Error adding linked word');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error adding linked word');
            }
        }
        
        async function addVariantWord() {
            const canonical = document.getElementById('canonicalWord').value.trim();
            const variant = document.getElementById('variantWord').value.trim();
            
            if (!canonical || !variant) {
                alert('Please fill in both fields');
                return;
            }
            
            try {
                const response = await fetch('/api/variant_words', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        canonical: canonical,
                        variant: variant,
                        reporter: currentUsername
                    })
                });
                
                if (response.ok) {
                    document.getElementById('canonicalWord').value = '';
                    document.getElementById('variantWord').value = '';
                    alert('Variant word added successfully!');
                    loadVariantWords();
                } else {
                    alert('Error adding variant word');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error adding variant word');
            }
        }
        
        async function loadLinkedWords() {
            try {
                const response = await fetch('/api/linked_words');
                if (response.ok) {
                    const data = await response.json();
                    const container = document.getElementById('linkedWordsList');
                    if (container && data.linked_words) {
                        if (data.linked_words.length === 0) {
                            container.innerHTML = '<div style="text-align: center; color: #64748b; padding: 20px;">No linked words found</div>';
                        } else {
                            container.innerHTML = data.linked_words
                                .map((item, index) => `
                                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: #f8fafc; border-radius: 6px; margin: 6px 0; border: 1px solid #e2e8f0;">
                                        <div>
                                            <strong style="color: #dc2626;">${item.wrong}</strong> → <strong style="color: #059669;">${item.correct}</strong>
                                        </div>
                                        <button onclick="deleteLinkedWordByIndex(${index})" style="background: #ef4444; color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 12px;" title="Delete this linked word">
                                            🗑️ Delete
                                        </button>
                                    </div>
                                `).join('');
                            
                            // Store the data globally for deletion
                            window.currentLinkedWords = data.linked_words;
                        }
                    }
                }
            } catch (error) {
                console.error('Error loading linked words:', error);
                const container = document.getElementById('linkedWordsList');
                if (container) {
                    container.innerHTML = '<div style="color: #ef4444; padding: 12px;">Error loading linked words</div>';
                }
            }
        }
        
        async function loadVariantWords() {
            try {
                const response = await fetch('/api/variant_words');
                if (response.ok) {
                    const data = await response.json();
                    const container = document.getElementById('variantWordsList');
                    if (container && data.variant_words) {
                        if (data.variant_words.length === 0) {
                            container.innerHTML = '<div style="text-align: center; color: #64748b; padding: 20px;">No variant words found</div>';
                        } else {
                            // Flatten the variant words data structure
                            const flatVariants = [];
                            data.variant_words.forEach(entry => {
                                if (entry.variants && Array.isArray(entry.variants)) {
                                    entry.variants.forEach(variant => {
                                        flatVariants.push({
                                            canonical: entry.canonical,
                                            variant: variant,
                                            reporter: 'System' // Default since JSONL doesn't have reporter info
                                        });
                                    });
                                }
                            });
                            
                            if (flatVariants.length === 0) {
                                container.innerHTML = '<div style="text-align: center; color: #64748b; padding: 20px;">No variant words found</div>';
                            } else {
                                container.innerHTML = flatVariants
                                    .map((variant, index) => `
                                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: #f8fafc; border-radius: 6px; margin: 6px 0; border: 1px solid #e2e8f0;">
                                            <div>
                                                <strong style="color: #7c3aed;">${variant.canonical}</strong> → <strong style="color: #059669;">${variant.variant}</strong>
                                                <small style="color: #64748b; margin-left: 8px;">(${variant.reporter})</small>
                                            </div>
                                            <button onclick="deleteVariantWordByIndex(${index})" style="background: #ef4444; color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 12px;" title="Delete this variant word">
                                                🗑️ Delete
                                            </button>
                                        </div>
                                    `).join('');
                                
                                // Store the data globally for deletion
                                window.currentVariantWords = flatVariants;
                            }
                        }
                    }
                }
            } catch (error) {
                console.error('Error loading variant words:', error);
                const container = document.getElementById('variantWordsList');
                if (container) {
                    container.innerHTML = '<div style="color: #ef4444; padding: 12px;">Error loading variant words</div>';
                }
            }
        }
        
        async function addVariantReport() {
            const word = document.getElementById('variantReportWord').value.trim();
            const suggestion = document.getElementById('variantReportSuggestion').value.trim();
            
            if (!word || !suggestion) {
                alert('Please fill in both fields');
                return;
            }
            
            try {
                const response = await fetch('/api/variants', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        word: word,
                        suggestion: suggestion,
                        reporter: currentUsername
                    })
                });
                
                if (response.ok) {
                    document.getElementById('variantReportWord').value = '';
                    document.getElementById('variantReportSuggestion').value = '';
                    alert('Grammar variant reported successfully!');
                    loadGrammarVariants();
                } else {
                    alert('Error reporting grammar variant');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error reporting grammar variant');
            }
        }
        
        async function loadGrammarVariants() {
            try {
                const response = await fetch('/api/variants');
                if (response.ok) {
                    const data = await response.json();
                    const container = document.getElementById('grammarVariantsList');
                    if (container && data.variants) {
                        // Store globally for delete functionality
                        window.currentGrammarVariants = data.variants;
                        
                        container.innerHTML = data.variants
                            .map((variant, index) => `
                                <div style="padding: 8px; background: #f8fafc; border-radius: 4px; margin: 4px 0; display: flex; justify-content: space-between; align-items: center;">
                                    <div>
                                        <strong>${variant.word}</strong> → ${variant.suggestion}
                                        <small style="color: #64748b; margin-left: 8px;">(by ${variant.reporter})</small>
                                    </div>
                                    <button onclick="deleteGrammarVariantByIndex(${index})" 
                                            style="background: #ef4444; color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 12px;"
                                            title="Delete this grammar variant">
                                        Delete
                                    </button>
                                </div>
                            `).join('');
                    }
                }
            } catch (error) {
                console.error('Error loading grammar variants:', error);
            }
        }

        async function deleteLinkedWordByIndex(index) {
            if (!window.currentLinkedWords || !window.currentLinkedWords[index]) {
                showMessage('Error: Invalid linked word selection', 'error');
                return;
            }
            
            const item = window.currentLinkedWords[index];
            if (!confirm(`Are you sure you want to delete the linked word "${item.wrong}" → "${item.correct}"?`)) {
                return;
            }
            
            try {
                const response = await fetch(`/api/linked_words/${encodeURIComponent(item.wrong)}/${encodeURIComponent(item.correct)}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    console.log('Linked word deleted successfully');
                    loadLinkedWords(); // Reload the list
                    showMessage('Linked word deleted successfully!', 'success');
                } else {
                    const error = await response.text();
                    console.error('Failed to delete linked word:', error);
                    showMessage('Failed to delete linked word', 'error');
                }
            } catch (error) {
                console.error('Error deleting linked word:', error);
                showMessage('Error deleting linked word', 'error');
            }
        }

        async function deleteVariantWordByIndex(index) {
            if (!window.currentVariantWords || !window.currentVariantWords[index]) {
                showMessage('Error: Invalid variant word selection', 'error');
                return;
            }
            
            const variant = window.currentVariantWords[index];
            if (!confirm(`Are you sure you want to delete the variant "${variant.canonical}" → "${variant.variant}"?`)) {
                return;
            }
            
            try {
                const response = await fetch(`/api/variant_words/${encodeURIComponent(variant.canonical)}/${encodeURIComponent(variant.variant)}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    console.log('Variant word deleted successfully');
                    loadVariantWords(); // Reload the list
                    showMessage('Variant word deleted successfully!', 'success');
                } else {
                    const error = await response.text();
                    console.error('Failed to delete variant word:', error);
                    showMessage('Failed to delete variant word', 'error');
                }
            } catch (error) {
                console.error('Error deleting variant word:', error);
                showMessage('Error deleting variant word', 'error');
            }
        }

        async function deleteGrammarVariantByIndex(index) {
            if (!window.currentGrammarVariants || !window.currentGrammarVariants[index]) {
                showMessage('Error: Invalid grammar variant selection', 'error');
                return;
            }
            
            const variant = window.currentGrammarVariants[index];
            if (!confirm(`Are you sure you want to delete the grammar variant "${variant.word}" → "${variant.suggestion}"?`)) {
                return;
            }
            
            try {
                const response = await fetch(`/api/variants/${encodeURIComponent(variant.id)}?reporter=${encodeURIComponent(variant.reporter)}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    console.log('Grammar variant deleted successfully');
                    loadGrammarVariants(); // Reload the list
                    showMessage('Grammar variant deleted successfully!', 'success');
                } else {
                    const error = await response.text();
                    console.error('Failed to delete grammar variant:', error);
                    showMessage('Failed to delete grammar variant', 'error');
                }
            } catch (error) {
                console.error('Error deleting grammar variant:', error);
                showMessage('Error deleting grammar variant', 'error');
            }
        }

        // Keep the original functions for backward compatibility
        async function deleteLinkedWord(wrongWord, correctWord) {
            if (!confirm(`Are you sure you want to delete the linked word "${wrongWord}" → "${correctWord}"?`)) {
                return;
            }
            
            try {
                const response = await fetch(`/api/linked_words/${encodeURIComponent(wrongWord)}/${encodeURIComponent(correctWord)}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    console.log('Linked word deleted successfully');
                    loadLinkedWords(); // Reload the list
                    showMessage('Linked word deleted successfully!', 'success');
                } else {
                    const error = await response.text();
                    console.error('Failed to delete linked word:', error);
                    showMessage('Failed to delete linked word', 'error');
                }
            } catch (error) {
                console.error('Error deleting linked word:', error);
                showMessage('Error deleting linked word', 'error');
            }
        }

        async function deleteVariantWord(canonical, variant) {
            if (!confirm(`Are you sure you want to delete the variant "${canonical}" → "${variant}"?`)) {
                return;
            }
            
            try {
                const response = await fetch(`/api/variant_words/${encodeURIComponent(canonical)}/${encodeURIComponent(variant)}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    console.log('Variant word deleted successfully');
                    loadVariantWords(); // Reload the list
                    showMessage('Variant word deleted successfully!', 'success');
                } else {
                    const error = await response.text();
                    console.error('Failed to delete variant word:', error);
                    showMessage('Failed to delete variant word', 'error');
                }
            } catch (error) {
                console.error('Error deleting variant word:', error);
                showMessage('Error deleting variant word', 'error');
            }
        }

        function showMessage(message, type = 'info') {
            const messageDiv = document.createElement('div');
            messageDiv.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 12px 20px;
                border-radius: 6px;
                color: white;
                font-weight: 500;
                z-index: 1000;
                animation: slideIn 0.3s ease-out;
                ${type === 'success' ? 'background: #059669;' : type === 'error' ? 'background: #dc2626;' : 'background: #3b82f6;'}
            `;
            messageDiv.textContent = message;
            
            document.body.appendChild(messageDiv);
            
            setTimeout(() => {
                messageDiv.style.animation = 'slideOut 0.3s ease-in';
                setTimeout(() => {
                    document.body.removeChild(messageDiv);
                }, 300);
            }, 3000);
        }

        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            loadStats();
            loadNextParagraph();
            loadLinkedWords();
            loadVariantWords();
            loadGrammarVariants();
        });
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)

# API Endpoints
@app.post("/api/normalize")
async def normalize_text_api(request: NormalizationRequest):
    """Normalize text via API."""
    try:
        original_text = request.text
        normalized_text = normalize_text(original_text)
        
        response = {
            "original": original_text,
            "normalized": normalized_text
        }
        
        if request.show_diff:
            # Generate word-level diff information
            original_words = original_text.split()
            normalized_words = normalized_text.split()
            
            changes = []
            for i, (orig, norm) in enumerate(zip(original_words, normalized_words)):
                if orig != norm:
                    changes.append({
                        "index": i,
                        "original": orig,
                        "normalized": norm
                    })
            
            response["changes"] = changes
            response["total_changes"] = len(changes)
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Normalization error: {str(e)}")

@app.get("/api/para/next")
async def get_next_paragraph(username: str):
    """Get the next unassigned paragraph."""
    if not authenticate_user(username):
        raise HTTPException(status_code=401, detail="Invalid user")
    
    paragraph = storage.get_next_unassigned(username)
    if not paragraph:
        raise HTTPException(status_code=404, detail="No unassigned paragraphs available")
    return paragraph

@app.post("/api/para/{para_id}/submit")
async def submit_paragraph(
    para_id: int,
    username: str = Form(...),
    text_final: str = Form(...),
    audio_file: UploadFile = File(...)
):
    """Submit a recorded paragraph."""
    if not authenticate_user(username):
        raise HTTPException(status_code=401, detail="Invalid user")
    
    try:
        # Save audio file
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"para_{para_id}__user_{username}__{timestamp}.webm"
        file_path = AUDIO_DIR / filename
        
        with open(file_path, "wb") as f:
            f.write(await audio_file.read())
        
        # Update paragraph
        success = storage.complete_paragraph(para_id, text_final, username)
        if not success:
            raise HTTPException(status_code=404, detail="Paragraph not found or not assigned to user")
        
        # Add recording
        storage.add_recording(para_id, username, filename)
        
        return {"success": True, "id": para_id, "audio": filename}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting paragraph: {str(e)}")

@app.post("/api/para/{para_id}/skip")
async def skip_paragraph(para_id: int, username: str):
    """Skip a paragraph."""
    if not authenticate_user(username):
        raise HTTPException(status_code=401, detail="Invalid user")
    
    success = storage.skip_paragraph(para_id, username)
    if not success:
        raise HTTPException(status_code=404, detail="Paragraph not found or not assigned to user")
    return {"success": True}

@app.get("/api/stats")
async def get_stats():
    """Get application statistics."""
    return storage.get_stats()

@app.get("/api/debug/data-files")
async def debug_data_files():
    """Debug endpoint to check data file accessibility."""
    try:
        from src.hassy_normalizer.data_loader import _get_data_file_path
        from pathlib import Path
        import os
        
        debug_info = {
            "data_files_status": {},
            "environment": {
                "cwd": str(Path.cwd()),
                "__file__": __file__ if '__file__' in globals() else "Not available",
                "HASSY_DATA_DIR": os.getenv("HASSY_DATA_DIR", "Not set")
            },
            "normalizer_stats": get_normalizer_stats()
        }
        
        # Check each data file
        data_files = [
            "hassaniya_variants.jsonl",
            "exception_words_g_q.json",
            "linked_words.json"
        ]
        
        for filename in data_files:
            try:
                filepath = _get_data_file_path(filename)
                debug_info["data_files_status"][filename] = {
                    "found": True,
                    "path": str(filepath),
                    "exists": filepath.exists(),
                    "size": filepath.stat().st_size if filepath.exists() else 0
                }
            except Exception as e:
                debug_info["data_files_status"][filename] = {
                    "found": False,
                    "error": str(e)
                }
        
        return debug_info
        
    except Exception as e:
        return {
            "error": f"Debug endpoint failed: {str(e)}",
            "normalizer_stats": get_normalizer_stats()
        }

@app.post("/api/variants")
async def add_variant(report: VariantReport):
    """Add a variant report."""
    variant_id = storage.add_variant(report.word, report.suggestion, report.reporter)
    return {"success": True, "id": variant_id}

@app.get("/api/variants")
async def get_variants():
    """Get all variant reports."""
    return {"variants": storage.variants}

@app.post("/api/linked_words")
async def add_linked_word(report: LinkedWordReport):
    """Add a linked word pair."""
    result = storage.add_linked_word(report.wrong, report.correct, report.reporter)
    if result is not None:
        return {"success": True, "total_count": result}
    else:
        return {"success": False, "message": "Entry already exists or error occurred"}

@app.get("/api/linked_words")
async def get_linked_words():
    """Get all linked words."""
    return {"linked_words": storage.get_linked_words()}

@app.post("/api/variant_words")
async def add_variant_word(report: VariantWordReport):
    """Add a variant word."""
    result = storage.add_variant_word(report.canonical, report.variant, report.reporter)
    if result is not None:
        return {"success": True, "total_count": result}
    else:
        return {"success": False, "message": "Variant already exists or error occurred"}

@app.get("/api/variant_words")
async def get_variant_words():
    """Get all variant words."""
    return {"variant_words": storage.get_variant_words()}

@app.delete("/api/linked_words/{wrong_word}/{correct_word}")
async def delete_linked_word(wrong_word: str, correct_word: str):
    """Delete a linked word pair."""
    success = storage.delete_linked_word(wrong_word, correct_word)
    if success:
        return {"success": True, "message": "Linked word deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Linked word not found")

@app.delete("/api/variant_words/{canonical}/{variant}")
async def delete_variant_word(canonical: str, variant: str):
    """Delete a variant word."""
    success = storage.delete_variant_word(canonical, variant)
    if success:
        return {"success": True, "message": "Variant word deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Variant word not found")

@app.delete("/api/variants/{variant_id}")
async def delete_variant(variant_id: str, reporter: str):
    """Delete a grammar variant report."""
    try:
        variant_id_int = int(variant_id)
        success = storage.delete_variant(variant_id_int, reporter)
        if success:
            return {"success": True, "message": "Grammar variant deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Grammar variant not found or unauthorized")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid variant ID format")

@app.delete("/api/users/{username}/stats")
async def reset_user_stats(username: str):
    """Reset all statistics for a specific user."""
    if not authenticate_user(username):
        raise HTTPException(status_code=404, detail="User not found")
    
    success = storage.reset_user_stats(username)
    if success:
        return {"success": True, "message": f"All statistics for user {username} have been reset successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to reset user statistics")

@app.post("/api/text/upload")
async def upload_text(file: UploadFile = File(...)):
    """Upload a text file and split it into paragraphs."""
    try:
        content = await file.read()
        text = content.decode("utf-8")
        
        # Split text into paragraphs (empty line delimiter)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        
        # Function to split text into 20-30 word segments
        def split_into_segments(text, min_words=20, max_words=30):
            words = text.split()
            segments = []
            current_segment = []
            
            for word in words:
                current_segment.append(word)
                
                # If we reach max words or find a natural break
                if (len(current_segment) >= max_words or 
                    (len(current_segment) >= min_words and word.endswith(('.', '!', '?', '؟', '.')))):
                    segments.append(' '.join(current_segment))
                    current_segment = []
            
            # Add remaining words if any
            if current_segment:
                if len(current_segment) >= min_words:
                    segments.append(' '.join(current_segment))
                elif segments:  # Merge with last segment if too short
                    segments[-1] += ' ' + ' '.join(current_segment)
                else:  # If it's the only segment, keep it even if short
                    segments.append(' '.join(current_segment))
            
            return segments
        
        # Split each paragraph into 20-30 word segments
        all_segments = []
        for paragraph in paragraphs:
            segments = split_into_segments(paragraph)
            all_segments.extend(segments)
        
        # Add segments to storage
        added_count = 0
        for segment_text in all_segments:
            storage.add_paragraph(segment_text)
            added_count += 1
        
        return {"success": True, "paragraphs_added": added_count}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.get("/api/audio/{filename}")
async def serve_audio(filename: str):
    """Serve audio files."""
    file_path = AUDIO_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(file_path, media_type="audio/webm")

@app.get("/api/export/recordings")
async def export_recordings():
    """Export recordings as a ZIP file."""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Create JSONL file with transcription data
        jsonl_data = []
        
        for recording in storage.recordings:
            paragraph = next((p for p in storage.paragraphs if p["id"] == recording["paragraph_id"]), None)
            if paragraph and paragraph["status"] == "done":
                jsonl_entry = {
                    "audio_file": recording["filename"],
                    "text": paragraph["text_final"] or paragraph["text_original"],
                    "original_text": paragraph["text_original"],
                    "user": recording["user"],
                    "paragraph_id": recording["paragraph_id"],
                    "recording_id": recording["id"],
                    "created_at": recording["created_at"]
                }
                jsonl_data.append(jsonl_entry)
        
        # Add JSONL file to ZIP
        jsonl_content = "\n".join(json.dumps(entry, ensure_ascii=False) for entry in jsonl_data)
        zip_file.writestr("transcriptions.jsonl", jsonl_content.encode('utf-8'))
        
        # Add audio files to ZIP
        for recording in storage.recordings:
            audio_path = AUDIO_DIR / recording["filename"]
            if audio_path.exists():
                zip_file.write(audio_path, f"recordings/{recording['filename']}")
        
        # Add README
        readme_content = """# Hassaniya Recordings Export

This ZIP file contains:
- transcriptions.jsonl: Metadata and transcriptions in JSONL format
- recordings/: Audio files in WebM format

The JSONL file is compatible with Whisper fine-tuning workflows.
"""
        zip_file.writestr("README.md", readme_content)
    
    zip_buffer.seek(0)
    
    return StreamingResponse(
        io.BytesIO(zip_buffer.read()),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=hassaniya_recordings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"}
    )

@app.get("/api/export/statistics")
async def export_statistics():
    """Export statistics as a ZIP file."""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        stats = storage.get_stats()
        
        detailed_stats = {
            "summary": stats,
            "paragraphs": storage.paragraphs,
            "recordings": storage.recordings,
            "variants_reported": storage.variants
        }
        
        zip_file.writestr("statistics.json", json.dumps(detailed_stats, ensure_ascii=False, indent=2).encode('utf-8'))
        
        if storage.variants:
            variants_data = {"total_variants": len(storage.variants), "variants": storage.variants}
            zip_file.writestr("variant_reports.json", json.dumps(variants_data, ensure_ascii=False, indent=2).encode('utf-8'))
        
        # Add user statistics
        user_stats = stats["user_stats"]
        zip_file.writestr("user_statistics.json", json.dumps(user_stats, ensure_ascii=False, indent=2).encode('utf-8'))
        
        readme_content = """# Hassaniya Statistics Export

This ZIP file contains:
- statistics.json: Complete system statistics and data
- variant_reports.json: User-reported grammar variants
- user_statistics.json: Per-user activity statistics
"""
        zip_file.writestr("README.md", readme_content)
    
    zip_buffer.seek(0)
    
    return StreamingResponse(
        io.BytesIO(zip_buffer.read()),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=hassaniya_statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"}
    )

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8002))
    uvicorn.run(app, host="0.0.0.0", port=port)
