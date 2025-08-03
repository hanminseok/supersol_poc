import asyncio
from typing import Dict, Any, Optional, List
from agents import RewritingAgent, PreprocessingAgent, SupervisorAgent, DomainAgent
from agents.base_agent import BaseAgent
from utils.logger import service_logger

class AgentManager:
    """Agent 간 직접 통신을 관리하는 매니저 클래스"""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.logger = service_logger
        self._initialize_agents()
    
    def _initialize_agents(self):
        """모든 Agent를 초기화하고 등록"""
        try:
            self.agents["rewriting"] = RewritingAgent()
            self.agents["preprocessing"] = PreprocessingAgent()
            self.agents["supervisor"] = SupervisorAgent()
            self.agents["domain"] = DomainAgent()
            self.logger.info("All agents initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize agents: {str(e)}")
            raise
    
    def get_agent_by_config_name(self, config_name: str) -> Optional[BaseAgent]:
        """Agent 설정 이름으로 Agent 인스턴스 반환"""
        # Agent 설정 이름과 등록된 Agent 이름 매핑
        name_mapping = {
            "rewriting_agent": "rewriting",
            "preprocessing_agent": "preprocessing", 
            "supervisor_agent": "supervisor",
            "domain_agent": "domain"
        }
        
        agent_name = name_mapping.get(config_name, config_name)
        return self.agents.get(agent_name)
    
    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """Agent 이름으로 Agent 인스턴스 반환"""
        return self.agents.get(agent_name)
    
    def get_next_agent(self, current_agent: BaseAgent, result: Dict[str, Any]) -> Optional[BaseAgent]:
        """현재 Agent의 결과를 바탕으로 다음 Agent 결정"""
        try:
            # should_skip_next_agent 플래그 확인
            if result.get("should_skip_next_agent", False):
                self.logger.info(f"Skipping next agent due to should_skip_next_agent flag from {current_agent.config.name}")
                return None
            
            # Agent 설정에서 next_agent 가져오기
            next_agent_names = current_agent.config.next_agent
            
            if not next_agent_names:
                self.logger.info(f"No next agent configured for {current_agent.config.name}")
                return None
            
            # 첫 번째 next_agent 반환 (현재는 단순 라우팅)
            next_agent_name = next_agent_names[0]
            
            # Agent 설정 이름으로 Agent 찾기 시도
            next_agent = self.get_agent_by_config_name(next_agent_name)
            if not next_agent:
                # 직접 Agent 이름으로 찾기 시도
                next_agent = self.get_agent(next_agent_name)
            
            if next_agent:
                self.logger.info(f"Routing from {current_agent.config.name} to {next_agent_name}")
                return next_agent
            else:
                self.logger.error(f"Next agent '{next_agent_name}' not found")
                return None
                
        except Exception as e:
            self.logger.error(f"Error determining next agent: {str(e)}")
            return None
    
    async def execute_workflow(self, start_agent_name: str, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """워크플로우 실행 - Agent 체인을 따라 순차 실행"""
        try:
            # Agent 설정 이름으로 Agent 찾기 시도
            current_agent = self.get_agent_by_config_name(start_agent_name)
            if not current_agent:
                # 직접 Agent 이름으로 찾기 시도
                current_agent = self.get_agent(start_agent_name)
            
            if not current_agent:
                raise ValueError(f"Start agent '{start_agent_name}' not found")
            
            self.logger.info(f"Starting workflow with {start_agent_name}")
            
            # 현재 Agent 실행 (agent_manager 전달)
            result = await current_agent.execute(input_data, context, self)
            
            # 다음 Agent 결정 및 실행
            next_agent = self.get_next_agent(current_agent, result)
            
            if next_agent:
                # 다음 Agent의 입력 데이터 준비
                next_input = self._prepare_next_agent_input(current_agent.config.name, result, input_data)
                
                # 재귀적으로 다음 Agent 실행 (agent_manager 전달)
                next_result = await self.execute_workflow(next_agent.config.name, next_input, context)
                
                # 결과 병합
                return self._merge_results(result, next_result)
            else:
                # 워크플로우 종료
                self.logger.info(f"Workflow completed at {current_agent.config.name}")
                return result
                
        except Exception as e:
            self.logger.error(f"Workflow execution failed: {str(e)}")
            raise
    
    def _prepare_next_agent_input(self, current_agent_name: str, current_result: Dict[str, Any], original_input: Dict[str, Any]) -> Dict[str, Any]:
        """다음 Agent의 입력 데이터 준비"""
        if current_agent_name == "rewriting":
            return {
                "rewritten_text": current_result.get("rewritten_text", ""),
                "topic": current_result.get("topic", ""),
                "conversation_context": original_input.get("conversation_context", []),
                "current_state": original_input.get("current_state", {})
            }
        elif current_agent_name == "preprocessing":
            return {
                "normalized_text": current_result.get("normalized_text", ""),
                "intent": current_result.get("intent", ""),
                "slot": current_result.get("slot", []),
                "conversation_context": original_input.get("conversation_context", []),
                "current_state": original_input.get("current_state", {})
            }
        elif current_agent_name == "supervisor":
            return {
                "target_domain": current_result.get("target_domain", ""),
                "normalized_text": current_result.get("normalized_text", ""),
                "intent": current_result.get("intent", ""),
                "slot": current_result.get("slot", []),
                "context": original_input.get("context", {})
            }
        else:
            # 기본적으로 현재 결과를 그대로 전달
            return current_result
    
    def _merge_results(self, current_result: Dict[str, Any], next_result: Dict[str, Any]) -> Dict[str, Any]:
        """Agent 결과 병합"""
        merged = current_result.copy()
        merged.update(next_result)
        return merged
    
    async def execute_single_agent(self, agent_name: str, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """단일 Agent 실행"""
        agent = self.get_agent(agent_name)
        if not agent:
            raise ValueError(f"Agent '{agent_name}' not found")
        
        return await agent.execute(input_data, context) 