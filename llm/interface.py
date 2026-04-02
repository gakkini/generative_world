"""
LLM接口封装 - OpenAI兼容格式 + MiniMax
统一管理所有LLM调用，所有客户端通过本模块访问
"""
import os
import re
import json
from typing import Optional


class LLMInterface:
    """LLM生成接口（统一封装，兼容旧代码）"""
    
    def __init__(self, client=None):
        self.client = client
    
    def generate(self, prompt: str, system_prompt: str = None,
                max_tokens: int = 1000, temperature: float = 0.8,
                **kwargs) -> str:
        """统一生成接口"""
        if self.client:
            return self.client.generate(
                prompt, system_prompt, 
                max_tokens=max_tokens, 
                temperature=temperature,
                **kwargs
            )
        return "[LLM未配置]"


def _expand_env_var(value: str) -> str:
    """展开字符串中的 ${VAR} 环境变量占位符"""
    if not isinstance(value, str):
        return value
    # 匹配 ${VAR} 格式
    pattern = r'\$\{([^}]+)\}'
    matches = re.findall(pattern, value)
    for var_name in matches:
        env_value = os.environ.get(var_name, '')
        if env_value:
            value = value.replace(f'${{{var_name}}}', env_value)
        else:
            # 如果环境变量不存在，保留原样（让后续检查失败）
            pass
    return value


class BaseLLMClient:
    """LLM客户端基类"""
    
    def generate(self, prompt: str, system_prompt: str = None,
                 max_tokens: int = 1000, temperature: float = 0.8,
                 **kwargs) -> str:
        raise NotImplementedError


class OpenAICompatibleClient(BaseLLMClient):
    """
    OpenAI兼容格式的LLM客户端
    支持: OpenAI, MiniMax, Ollama, vLLM 等
    """
    
    def __init__(self, api_key: str = None, base_url: str = None, 
                 model: str = "gpt-4", max_retries: int = 3):
        """
        Args:
            api_key: API密钥（支持 ${ENV_VAR} 格式的环境变量占位符）
            base_url: API基础URL
            model: 模型名称
            max_retries: 最大重试次数
        """
        self.api_key = _expand_env_var(api_key) if api_key else None
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.model = model
        self.max_retries = max_retries
    
    def generate(self, prompt: str, system_prompt: str = None,
                 max_tokens: int = 1000, temperature: float = 0.8,
                 **kwargs) -> str:
        """调用LLM生成"""
        import urllib.request
        import urllib.error
        
        if not self.api_key:
            return "[Error] API key not configured"
        
        # 构建消息
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # 构建请求
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 发送请求
        for attempt in range(self.max_retries):
            try:
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(url, data=data, headers=headers, method="POST")
                
                with urllib.request.urlopen(req, timeout=60) as response:
                    result = json.loads(response.read().decode("utf-8"))
                    content = result["choices"][0]["message"]["content"]
                    
                    # 去除 <think>...</think> 标签和其中的思考内容
                    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                    return content
                    
            except urllib.error.HTTPError as e:
                error_body = e.read().decode("utf-8") if e.fp else ""
                if attempt == self.max_retries - 1:
                    return f"[HTTP Error {e.code}]: {error_body}"
                continue
            except Exception as e:
                if attempt == self.max_retries - 1:
                    return f"[Error]: {str(e)}"
                continue
        
        return "[Max retries exceeded]"


class MiniMaxClient(OpenAICompatibleClient):
    """
    MiniMax专用客户端
    API格式: https://api.minimaxi.com/v1/chat/completions (OpenAI兼容)
    """
    
    def __init__(self, api_key: str = None, model: str = "MiniMax-M2.7"):
        # 先展开环境变量，再传给父类
        expanded_key = _expand_env_var(api_key) if api_key else None
        super().__init__(
            api_key=expanded_key,
            base_url="https://api.minimaxi.com/v1",
            model=model
        )
    
    @classmethod
    def from_config(cls, config: dict = None):
        """从配置创建（自动展开环境变量占位符）"""
        if config is None:
            config = {}
        
        raw_key = config.get("api_key", "")
        # 展开 ${VAR} 格式的占位符
        api_key = _expand_env_var(raw_key) if raw_key else None
        
        # 如果展开后为空，尝试从环境变量获取
        if not api_key:
            api_key = os.environ.get("MINIMAX_API_KEY")
        
        model = config.get("model", "MiniMax-M2.7")
        
        if not api_key:
            return None
        
        return cls(api_key=api_key, model=model)


class OllamaClient(BaseLLMClient):
    """
    Ollama本地模型客户端
    默认地址: http://localhost:11434
    """
    
    def __init__(self, model: str = "llama3", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip("/")
    
    def generate(self, prompt: str, system_prompt: str = None,
                 max_tokens: int = 1000, temperature: float = 0.8,
                 **kwargs) -> str:
        """调用Ollama生成"""
        import urllib.request
        import urllib.error
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        url = f"{self.base_url}/api/chat"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            },
            "stream": False
        }
        
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST")
            
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result.get("message", {}).get("content", "")
                
        except Exception as e:
            return f"[Ollama Error]: {str(e)}"


def create_llm_client(client_type: str = "auto", config: dict = None) -> Optional[BaseLLMClient]:
    """
    创建LLM客户端
    
    Args:
        client_type: 
            - "minimax": MiniMax模型
            - "openai": OpenAI官方API  
            - "ollama": 本地Ollama
            - "auto": 自动检测
        config: 配置字典（支持 ${ENV_VAR} 格式的环境变量占位符）
        
    Returns:
        LLM客户端实例
    """
    if client_type == "minimax":
        return MiniMaxClient.from_config(config)
    
    elif client_type == "ollama":
        model = config.get("model", "llama3") if config else "llama3"
        base_url = config.get("base_url", "http://localhost:11434") if config else "http://localhost:11434"
        return OllamaClient(model=model, base_url=base_url)
    
    elif client_type == "openai":
        raw_key = config.get("api_key", "") if config else ""
        api_key = _expand_env_var(raw_key) if raw_key else None
        base_url = config.get("base_url") if config else None
        model = config.get("model", "gpt-4") if config else "gpt-4"
        return OpenAICompatibleClient(api_key=api_key, base_url=base_url, model=model)
    
    elif client_type == "auto":
        # 自动检测可用客户端
        # 优先检查MiniMax
        minimax = MiniMaxClient.from_config(config)
        if minimax and minimax.api_key:
            return minimax
        
        # 检查OpenAI
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            return OpenAICompatibleClient(api_key=openai_key)
        
        return None
    
    return None
