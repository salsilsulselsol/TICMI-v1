"""
LLM Provider Module for TICMI AI Agents.

Supports multiple LLM backends:
- Google Gemini 1.5 Pro
- Ollama (Llama 3 and other local models)

Provides both standard and structured output LLM instances.
"""

from typing import Type, Optional, Any
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from ..core.config import settings


def get_llm() -> BaseChatModel:
    """
    Get the configured LLM instance.
    
    Returns:
        Configured BaseChatModel instance
    """
    model_name = settings.DEFAULT_LLM_MODEL
    
    if model_name.startswith("ollama"):
        # Use Ollama for local inference
        from langchain_community.chat_models import ChatOllama
        
        return ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=model_name.split("/")[-1] if "/" in model_name else "llama3",
            temperature=0.7,
        )
    else:
        # Use Google Gemini
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.7,
        )


def get_llm_with_structured_output(
    output_schema: Type[BaseModel]
) -> Any:
    """
    Get an LLM instance configured for structured output.
    
    This uses LangChain's with_structured_output method when available,
    or falls back to PydanticOutputParser for older versions.
    
    Args:
        output_schema: Pydantic model defining the expected output structure
        
    Returns:
        Runnable LLM instance that outputs structured data
    """
    llm = get_llm()
    
    try:
        # Try the modern with_structured_output approach (LangChain 0.1+)
        if hasattr(llm, "with_structured_output"):
            return llm.with_structured_output(output_schema)
    except Exception:
        pass
    
    # Fallback: Use PydanticOutputParser
    parser = PydanticOutputParser(pydantic_object=output_schema)
    
    # Create a chain with the parser
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant. Respond ONLY with valid JSON matching the schema."),
        ("human", "{input}"),
    ])
    
    # Return a runnable sequence
    from langchain_core.runnables import RunnableSequence
    
    return RunnableSequence(
        lambda x: parser.format_instructions() + "\n\n" + str(x),
        llm,
        parser,
    )


def get_embedding_model():
    """
    Get embedding model for RAG operations.
    
    Returns:
        Embeddings instance for vector database operations
    """
    # Default to Google embeddings for Gemini users
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    
    return GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=settings.GOOGLE_API_KEY,
    )
