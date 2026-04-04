"""
Módulo de compatibilidad — redirige a knowledge.api_knowledge_base
"""

from knowledge.api_knowledge_base import *  # noqa: F401,F403
from knowledge.api_knowledge_base import APIKnowledgeBase, ClientCapabilitiesAnnouncer

try:
    from knowledge.api_knowledge_base import create_example_knowledge_base
except ImportError:
    pass
