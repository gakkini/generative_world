"""LLM接口封装"""
import os


class LLMInterface:
    """LLM生成接口"""
    
    def __init__(self, client=None):
        self.client = client
    
    def generate(self, prompt, system_prompt=None, **kwargs) -> str:
        """统一生成接口"""
        if self.client:
            return self.client.generate(prompt, system_prompt, **kwargs)
        else:
            return "[LLM未配置]"


class OpenAIClient:
    """OpenAI API客户端"""
    
    def __init__(self, api_key=None, model="gpt-4"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model
    
    def generate(self, prompt, system_prompt=None, max_tokens=1000, temperature=0.8) -> str:
        """
        调用OpenAI API生成文本
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            max_tokens: 最大token数
            temperature: 创造性参数
        
        Returns:
            str: 生成的文本
        """
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response.choices[0].message.content
            
        except ImportError:
            return "[需要安装openai库: pip install openai]"
        except Exception as e:
            return f"[OpenAI API调用失败: {str(e)}]"
