"""
Knowledge module — bases de conocimiento de APIs y conocimiento general
"""

from .api_knowledge_base import APIKnowledgeBase, ClientCapabilitiesAnnouncer
from .knowledge_base_manager import KnowledgeBaseManager

try:
    from .api_knowledge_base import create_example_knowledge_base
except ImportError:
    pass

__all__ = [
    'APIKnowledgeBase',
    'ClientCapabilitiesAnnouncer',
    'KnowledgeBaseManager',
]
