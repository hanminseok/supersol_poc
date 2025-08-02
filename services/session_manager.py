import json
import os
import aiofiles
from typing import Dict, Any, List, Optional
from datetime import datetime
from Config import Config
from utils.logger import service_logger

class SessionManager:
    def __init__(self):
        self.session_dir = Config.SESSION_DIR
        self.max_history = Config.MAX_SESSION_HISTORY
        os.makedirs(self.session_dir, exist_ok=True)
        self.logger = service_logger
    
    def _get_session_file_path(self, session_id: str) -> str:
        """세션 파일 경로 생성"""
        return os.path.join(self.session_dir, f"{session_id}.json")
    
    async def create_session(self, session_id: str, customer_info: Optional[Dict[str, Any]] = None) -> bool:
        """새 세션 생성"""
        try:
            session_data = {
                "session_id": session_id,
                "created_at": datetime.now().isoformat(),
                "customer_info": customer_info or {},
                "conversation_history": [],
                "last_updated": datetime.now().isoformat()
            }
            
            file_path = self._get_session_file_path(session_id)
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(session_data, ensure_ascii=False, indent=2))
            
            self.logger.info(f"Session created: {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create session {session_id}: {str(e)}")
            return False
    
    async def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """세션 로드"""
        try:
            file_path = self._get_session_file_path(session_id)
            if not os.path.exists(file_path):
                return None
            
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                session_data = json.loads(content)
            
            self.logger.info(f"Session loaded: {session_id}")
            return session_data
            
        except Exception as e:
            self.logger.error(f"Failed to load session {session_id}: {str(e)}")
            return None
    
    async def save_conversation(self, session_id: str, user_query: str, agent_response: str, agent_log: str) -> bool:
        """대화 내역 저장"""
        try:
            session_data = await self.load_session(session_id)
            if not session_data:
                return False
            
            conversation_entry = {
                "timestamp": datetime.now().isoformat(),
                "user_query": user_query,
                "agent_response": agent_response,
                "agent_log": agent_log
            }
            
            session_data["conversation_history"].append(conversation_entry)
            session_data["last_updated"] = datetime.now().isoformat()
            
            # 최대 대화 내역 제한
            if len(session_data["conversation_history"]) > self.max_history:
                session_data["conversation_history"] = session_data["conversation_history"][-self.max_history:]
            
            # 세션 저장
            file_path = self._get_session_file_path(session_id)
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(session_data, ensure_ascii=False, indent=2))
            
            self.logger.info(f"Conversation saved for session: {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save conversation for session {session_id}: {str(e)}")
            return False
    
    async def get_conversation_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """대화 내역 조회"""
        try:
            session_data = await self.load_session(session_id)
            if not session_data:
                return []
            
            history = session_data.get("conversation_history", [])
            if limit:
                history = history[-limit:]
            
            return history
            
        except Exception as e:
            self.logger.error(f"Failed to get conversation history for session {session_id}: {str(e)}")
            return []
    
    async def delete_session(self, session_id: str) -> bool:
        """세션 삭제"""
        try:
            file_path = self._get_session_file_path(session_id)
            if os.path.exists(file_path):
                os.remove(file_path)
                self.logger.info(f"Session deleted: {session_id}")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to delete session {session_id}: {str(e)}")
            return False
    
    async def list_sessions(self) -> List[str]:
        """세션 목록 조회"""
        try:
            sessions = []
            for filename in os.listdir(self.session_dir):
                if filename.endswith('.json'):
                    session_id = filename[:-5]  # .json 제거
                    sessions.append(session_id)
            return sessions
            
        except Exception as e:
            self.logger.error(f"Failed to list sessions: {str(e)}")
            return []
    
    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """세션 정보 조회"""
        try:
            session_data = await self.load_session(session_id)
            if not session_data:
                return None
            
            return {
                "session_id": session_data.get("session_id"),
                "created_at": session_data.get("created_at"),
                "last_updated": session_data.get("last_updated"),
                "customer_info": session_data.get("customer_info", {}),
                "conversation_count": len(session_data.get("conversation_history", []))
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get session info for {session_id}: {str(e)}")
            return None 