import json
import os
import asyncio
import aiofiles
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from Config import Config
from utils.logger import service_logger

class SessionOptimizer:
    """대용량 세션 파일 관리 최적화 클래스"""
    
    def __init__(self):
        self.session_dir = Config.SESSION_DIR
        self.max_history = Config.MAX_SESSION_HISTORY
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.compression_threshold = 5 * 1024 * 1024  # 5MB
        self.logger = service_logger
    
    async def optimize_session_file(self, session_id: str) -> bool:
        """세션 파일 최적화"""
        try:
            file_path = os.path.join(self.session_dir, f"{session_id}.json")
            
            if not os.path.exists(file_path):
                return True
            
            # 파일 크기 확인
            file_size = os.path.getsize(file_path)
            
            if file_size > self.max_file_size:
                await self._compress_session_file(session_id)
            elif file_size > self.compression_threshold:
                await self._cleanup_old_history(session_id)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to optimize session {session_id}: {str(e)}")
            return False
    
    async def _compress_session_file(self, session_id: str) -> bool:
        """대용량 세션 파일 압축"""
        try:
            file_path = os.path.join(self.session_dir, f"{session_id}.json")
            
            # 세션 데이터 로드
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                session_data = json.loads(content)
            
            # 대화 내역 압축
            conversation_history = session_data.get("conversation_history", [])
            if len(conversation_history) > self.max_history:
                # 최근 대화만 유지
                compressed_history = conversation_history[-self.max_history:]
                
                # 중요 정보만 유지 (agent_log 제거)
                for entry in compressed_history:
                    if "agent_log" in entry:
                        entry["agent_log"] = "[압축됨]"
                
                session_data["conversation_history"] = compressed_history
                session_data["compression_info"] = {
                    "compressed_at": datetime.now().isoformat(),
                    "original_count": len(conversation_history),
                    "compressed_count": len(compressed_history)
                }
            
            # 압축된 데이터 저장
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(session_data, ensure_ascii=False, indent=2))
            
            self.logger.info(f"Session {session_id} compressed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to compress session {session_id}: {str(e)}")
            return False
    
    async def _cleanup_old_history(self, session_id: str) -> bool:
        """오래된 대화 내역 정리"""
        try:
            file_path = os.path.join(self.session_dir, f"{session_id}.json")
            
            # 세션 데이터 로드
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                session_data = json.loads(content)
            
            conversation_history = session_data.get("conversation_history", [])
            
            if len(conversation_history) > self.max_history * 0.8:  # 80% 도달 시 정리
                # 최근 대화만 유지
                cleaned_history = conversation_history[-self.max_history:]
                session_data["conversation_history"] = cleaned_history
                
                # 정리된 데이터 저장
                async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(session_data, ensure_ascii=False, indent=2))
                
                self.logger.info(f"Session {session_id} history cleaned up")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup session {session_id}: {str(e)}")
            return False
    
    async def get_large_sessions(self) -> List[Tuple[str, int]]:
        """대용량 세션 파일 목록 조회"""
        large_sessions = []
        
        try:
            for filename in os.listdir(self.session_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.session_dir, filename)
                    file_size = os.path.getsize(file_path)
                    
                    if file_size > self.compression_threshold:
                        session_id = filename.replace('.json', '')
                        large_sessions.append((session_id, file_size))
            
            # 파일 크기 순으로 정렬
            large_sessions.sort(key=lambda x: x[1], reverse=True)
            
        except Exception as e:
            self.logger.error(f"Failed to get large sessions: {str(e)}")
        
        return large_sessions
    
    async def optimize_all_sessions(self) -> Dict[str, Any]:
        """모든 세션 파일 최적화"""
        results = {
            "total_sessions": 0,
            "optimized_sessions": 0,
            "large_sessions": 0,
            "errors": []
        }
        
        try:
            for filename in os.listdir(self.session_dir):
                if filename.endswith('.json'):
                    session_id = filename.replace('.json', '')
                    results["total_sessions"] += 1
                    
                    file_path = os.path.join(self.session_dir, filename)
                    file_size = os.path.getsize(file_path)
                    
                    if file_size > self.compression_threshold:
                        results["large_sessions"] += 1
                        
                        if await self.optimize_session_file(session_id):
                            results["optimized_sessions"] += 1
                        else:
                            results["errors"].append(session_id)
            
        except Exception as e:
            self.logger.error(f"Failed to optimize all sessions: {str(e)}")
            results["errors"].append(f"General error: {str(e)}")
        
        return results
    
    async def cleanup_old_sessions(self, days: int = 30) -> int:
        """오래된 세션 파일 정리"""
        cleaned_count = 0
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            for filename in os.listdir(self.session_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.session_dir, filename)
                    
                    # 파일 수정 시간 확인
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    if file_mtime < cutoff_date:
                        os.remove(file_path)
                        cleaned_count += 1
                        self.logger.info(f"Removed old session: {filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old sessions: {str(e)}")
        
        return cleaned_count 