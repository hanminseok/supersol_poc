import json
import os
from typing import Dict, Any, Optional
from pathlib import Path

class ConfigLoader:
    """Configuration loader for agent configurations"""
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            # Default to the config directory relative to this file
            config_dir = Path(__file__).parent
        self.config_dir = Path(config_dir)
        self._shared_config = None
        self._agent_configs = {}
    
    def load_shared_config(self) -> Dict[str, Any]:
        """Load shared configuration"""
        if self._shared_config is None:
            shared_config_path = self.config_dir / "shared_config.json"
            if shared_config_path.exists():
                with open(shared_config_path, 'r', encoding='utf-8') as f:
                    self._shared_config = json.load(f)
            else:
                self._shared_config = {}
        return self._shared_config
    
    def load_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """Load specific agent configuration"""
        if agent_name not in self._agent_configs:
            agent_config_path = self.config_dir / "agents" / f"{agent_name}.json"
            if agent_config_path.exists():
                with open(agent_config_path, 'r', encoding='utf-8') as f:
                    self._agent_configs[agent_name] = json.load(f)
            else:
                raise FileNotFoundError(f"Configuration file not found for agent: {agent_name}")
        return self._agent_configs[agent_name]
    
    def get_shared_value(self, key: str, default: Any = None) -> Any:
        """Get a value from shared configuration"""
        shared_config = self.load_shared_config()
        return shared_config.get(key, default)
    
    def get_agent_value(self, agent_name: str, key: str, default: Any = None) -> Any:
        """Get a value from specific agent configuration"""
        agent_config = self.load_agent_config(agent_name)
        return agent_config.get(key, default)
    
    def get_banking_domains(self) -> Dict[str, str]:
        """Get banking domains configuration"""
        return self.get_shared_value("banking_domains", {})
    
    def get_common_intents(self) -> Dict[str, str]:
        """Get common intents configuration"""
        return self.get_shared_value("common_intents", {})
    
    def get_common_topics(self) -> Dict[str, str]:
        """Get common topics configuration"""
        return self.get_shared_value("common_topics", {})
    
    def get_context_settings(self) -> Dict[str, Any]:
        """Get context settings configuration"""
        return self.get_shared_value("context_settings", {})
    
    def get_reference_resolution_rules(self) -> list:
        """Get reference resolution rules"""
        return self.get_shared_value("reference_resolution", {}).get("rules", [])
    
    def get_default_responses(self) -> Dict[str, str]:
        """Get default responses configuration"""
        return self.get_shared_value("default_responses", {})
    
    def get_intent_tool_mapping(self, agent_name: str) -> Dict[str, str]:
        """Get intent to tool mapping for specific agent"""
        return self.get_agent_value(agent_name, "intent_tool_mapping", {})
    
    def get_intent_domain_mapping(self, agent_name: str) -> Dict[str, str]:
        """Get intent to domain mapping for specific agent"""
        return self.get_agent_value(agent_name, "intent_domain_mapping", {})
    
    def get_intent_slots(self, agent_name: str) -> Dict[str, list]:
        """Get intent to slots mapping for specific agent"""
        return self.get_agent_value(agent_name, "intent_slots", {})
    
    def get_tools(self, agent_name: str) -> Dict[str, str]:
        """Get tools configuration for specific agent"""
        return self.get_agent_value(agent_name, "tools", {})
    
    def load_tools_config(self) -> Dict[str, Any]:
        """Load tools configuration from tools.json"""
        tools_config_path = self.config_dir / "agents" / "tools.json"
        if tools_config_path.exists():
            with open(tools_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {"tools": {}, "default_error_response": {"error": "Unknown tool"}}
    
    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """Get specific tool information including response format and sample response"""
        tools_config = self.load_tools_config()
        return tools_config.get("tools", {}).get(tool_name, {})
    
    def get_tool_sample_response(self, tool_name: str) -> Dict[str, Any]:
        """Get sample response for a specific tool"""
        tool_info = self.get_tool_info(tool_name)
        return tool_info.get("sample_response", {})
    
    def get_tool_response_format(self, tool_name: str) -> Dict[str, Any]:
        """Get response format for a specific tool"""
        tool_info = self.get_tool_info(tool_name)
        return tool_info.get("response_format", {})
    
    def get_default_error_response(self) -> Dict[str, Any]:
        """Get default error response"""
        tools_config = self.load_tools_config()
        return tools_config.get("default_error_response", {"error": "Unknown tool"})

# Global instance
config_loader = ConfigLoader() 