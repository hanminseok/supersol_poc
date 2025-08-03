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
        """새 세션 생성 - 컨텍스트 관리 기능 추가"""
        try:
            session_data = {
                "session_id": session_id,
                "created_at": datetime.now().isoformat(),
                "customer_info": customer_info or {},
                "conversation_history": [],
                "current_context": {
                    "selected_account": None,
                    "pending_action": None,
                    "missing_slots": [],
                    "last_intent": None,
                    "last_slots": [],
                    "conversation_depth": 0
                },
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
            
            # 이전 버전 호환성을 위한 컨텍스트 초기화
            if "current_context" not in session_data:
                session_data["current_context"] = {
                    "selected_account": None,
                    "pending_action": None,
                    "missing_slots": [],
                    "last_intent": None,
                    "last_slots": [],
                    "conversation_depth": len(session_data.get("conversation_history", []))
                }
            
            self.logger.info(f"Session loaded: {session_id}")
            return session_data
            
        except Exception as e:
            self.logger.error(f"Failed to load session {session_id}: {str(e)}")
            return None
    
    async def save_conversation(self, session_id: str, user_query: str, agent_response: str, agent_log: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """대화 내역 저장 - 컨텍스트 정보 포함"""
        try:
            session_data = await self.load_session(session_id)
            if not session_data:
                return False
            
            conversation_entry = {
                "timestamp": datetime.now().isoformat(),
                "user_query": user_query,
                "agent_response": agent_response,
                "agent_log": agent_log,
                "context_snapshot": context.get("current_state", {}) if context else {}
            }
            
            session_data["conversation_history"].append(conversation_entry)
            session_data["last_updated"] = datetime.now().isoformat()
            
            # 컨텍스트 정보 업데이트
            if context:
                session_data["current_context"] = {
                    "selected_account": context.get("current_state", {}).get("selected_account"),
                    "pending_action": context.get("current_state", {}).get("pending_action"),
                    "missing_slots": context.get("missing_slots", []),
                    "last_intent": context.get("last_intent"),
                    "last_slots": context.get("last_slots", []),
                    "conversation_depth": context.get("depth", 0)
                }
            
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
        """대화 내역 조회 - 컨텍스트 정보 포함"""
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
    
    async def get_current_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """현재 세션의 컨텍스트 정보 조회"""
        try:
            session_data = await self.load_session(session_id)
            if not session_data:
                return None
            
            return session_data.get("current_context", {})
            
        except Exception as e:
            self.logger.error(f"Failed to get current context for session {session_id}: {str(e)}")
            return None
    
    async def update_context(self, session_id: str, context_updates: Dict[str, Any]) -> bool:
        """세션 컨텍스트 업데이트"""
        try:
            session_data = await self.load_session(session_id)
            if not session_data:
                return False
            
            current_context = session_data.get("current_context", {})
            current_context.update(context_updates)
            session_data["current_context"] = current_context
            session_data["last_updated"] = datetime.now().isoformat()
            
            # 세션 저장
            file_path = self._get_session_file_path(session_id)
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(session_data, ensure_ascii=False, indent=2))
            
            self.logger.info(f"Context updated for session: {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update context for session {session_id}: {str(e)}")
            return False
    
    async def clear_context(self, session_id: str) -> bool:
        """세션 컨텍스트 초기화"""
        try:
            session_data = await self.load_session(session_id)
            if not session_data:
                return False
            
            session_data["current_context"] = {
                "selected_account": None,
                "pending_action": None,
                "missing_slots": [],
                "last_intent": None,
                "last_slots": [],
                "conversation_depth": 0
            }
            session_data["last_updated"] = datetime.now().isoformat()
            
            # 세션 저장
            file_path = self._get_session_file_path(session_id)
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(session_data, ensure_ascii=False, indent=2))
            
            self.logger.info(f"Context cleared for session: {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clear context for session {session_id}: {str(e)}")
            return False
    
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
        """세션 정보 조회 - 컨텍스트 정보 포함"""
        try:
            session_data = await self.load_session(session_id)
            if not session_data:
                return None
            
            return {
                "session_id": session_data.get("session_id"),
                "created_at": session_data.get("created_at"),
                "last_updated": session_data.get("last_updated"),
                "customer_info": session_data.get("customer_info", {}),
                "conversation_count": len(session_data.get("conversation_history", [])),
                "current_context": session_data.get("current_context", {})
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get session info for {session_id}: {str(e)}")
            return None 