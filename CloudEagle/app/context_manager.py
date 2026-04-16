"""Context management service for handling conversation history."""
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import structlog
from langchain_core.messages import HumanMessage
from langsmith import traceable

from app.database import MongoDB
from app.config import settings
from app.utils.token_counter import TokenCounter, estimate_tokens
from app.services.llm_service import llm_service

logger = structlog.get_logger()


class ContextManager:
    """Manages conversation context storage and retrieval with MongoDB."""
    
    def __init__(self):
        """Initialize the context manager."""
        self.collection_name = settings.context_collection_name
    
    def _get_collection(self):
        """Get the MongoDB collection for conversations."""
        return MongoDB.get_collection(self.collection_name)
    
    @traceable(
        name="get_context",
        run_type="retriever",
        tags=["context", "retrieval"]
    )
    async def get_context(self, session_id: str) -> str:
        """
        Retrieve and format conversation context for LLM.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Formatted context string for the LLM prompt
        """
        try:
            collection = self._get_collection()
            session = await collection.find_one({"session_id": session_id})
            
            if not session or not session.get('conversations'):
                logger.info("context_not_found", session_id=session_id)
                return ""
            
            # Get recent messages (last N full conversations)
            recent_count = settings.recent_messages_count
            conversations = session.get('conversations', [])
            recent_messages = conversations[-recent_count:] if len(conversations) > recent_count else conversations
            
            # Get summary if it exists
            summary = session.get('summary', {}).get('compressed_context', '')
            
            # Build context prompt
            context_prompt = self._format_context(summary, recent_messages)
            
            # Estimate tokens
            token_count = TokenCounter.estimate_tokens(context_prompt)
            logger.info(
                "context_retrieved",
                session_id=session_id,
                messages_count=len(conversations),
                recent_count=len(recent_messages),
                has_summary=bool(summary),
                token_count=token_count
            )
            
            return context_prompt
            
        except Exception as e:
            logger.error("context_retrieval_error", session_id=session_id, error=str(e))
            return ""
    
    def _format_context(self, summary: str, recent_messages: List[Dict]) -> str:
        """
        Format context into a readable prompt for the LLM.
        
        Args:
            summary: Compressed summary of older conversations
            recent_messages: List of recent conversation dictionaries
            
        Returns:
            Formatted context string
        """
        if not summary and not recent_messages:
            return ""
        
        context_parts = []
        
        if summary:
            context_parts.append("=== Previous Conversation Summary ===")
            context_parts.append(summary)
            context_parts.append("")
        
        if recent_messages:
            context_parts.append("=== Recent Conversation History ===")
            for idx, msg in enumerate(recent_messages, 1):
                question = msg.get('question', '')
                answer = msg.get('graph_state', {}).get('final_answer', '')
                country = msg.get('graph_state', {}).get('country_name', '')
                
                if question and answer:
                    context_parts.append(f"{idx}. User asked: {question}")
                    if country:
                        context_parts.append(f"   Country: {country}")
                    context_parts.append(f"   Answer: {answer}")
                    context_parts.append("")
        
        return "\n".join(context_parts)
    
    @traceable(
        name="save_conversation",
        run_type="chain",
        tags=["context", "storage"]
    )
    async def save_conversation(
        self,
        session_id: str,
        message_id: str,
        question: str,
        result: Dict[str, Any],
        llm_cost: float = 0.0,
        llm_provider: str = "gemini"
    ):
        """
        Save a conversation to MongoDB asynchronously.
        
        Args:
            session_id: Unique session identifier
            message_id: Unique message identifier
            question: User's question
            result: Agent execution result
            llm_cost: Total cost of LLM calls for this conversation
            llm_provider: Which provider was primarily used
        """
        try:
            collection = self._get_collection()
            
            # Calculate token count
            answer = result.get('final_answer', '')
            token_count = estimate_tokens(question + " " + answer)
            
            # Build conversation data
            conversation_data = {
                "message_id": message_id,
                "timestamp": datetime.now(timezone.utc),
                "question": question,
                "graph_state": {
                    "country_name": result.get("country_name"),
                    "requested_fields": result.get("requested_fields"),
                    "query_type": result.get("query_type"),
                    "extracted_data": result.get("extracted_data"),
                    "final_answer": answer,
                    "out_of_scope": result.get("out_of_scope", False)
                },
                "token_count": token_count,
                "llm_cost_usd": llm_cost,
                "llm_provider": llm_provider
            }
            
            # Prepare incremental updates for provider usage
            provider_field = f"metadata.provider_usage.{llm_provider}_calls"
            
            # Upsert session document
            await collection.update_one(
                {"session_id": session_id},
                {
                    "$push": {"conversations": conversation_data},
                    "$set": {
                        "last_accessed": datetime.now(timezone.utc)
                    },
                    "$inc": {
                        "metadata.total_messages": 1,
                        "metadata.total_tokens_used": token_count,
                        "metadata.total_cost_usd": llm_cost,
                        provider_field: 1
                    },
                    "$setOnInsert": {
                        "created_at": datetime.now(timezone.utc)
                    }
                },
                upsert=True
            )
            
            logger.info(
                "conversation_saved",
                session_id=session_id,
                message_id=message_id,
                token_count=token_count,
                cost=llm_cost,
                provider=llm_provider
            )
            
            # Check if summarization is needed
            await self._check_and_summarize(session_id)
            
        except Exception as e:
            logger.error(
                "conversation_save_error",
                session_id=session_id,
                error=str(e)
            )
    
    async def _check_and_summarize(self, session_id: str):
        """
        Check if summarization is needed and perform it if necessary.
        
        Args:
            session_id: Unique session identifier
        """
        try:
            collection = self._get_collection()
            session = await collection.find_one({"session_id": session_id})
            
            if not session:
                return
            
            total_messages = session.get('metadata', {}).get('total_messages', 0)
            trigger_count = settings.summary_trigger_count
            
            # Summarize every N messages
            if total_messages > 0 and total_messages % trigger_count == 0:
                logger.info(
                    "summarization_triggered",
                    session_id=session_id,
                    total_messages=total_messages
                )
                
                conversations = session.get('conversations', [])
                
                # Keep recent messages full, summarize the rest
                recent_count = settings.recent_messages_count
                messages_to_summarize = conversations[:-recent_count] if len(conversations) > recent_count else []
                
                if messages_to_summarize:
                    summary = await self._summarize_with_llm(messages_to_summarize)
                    
                    # Calculate tokens saved
                    old_tokens = sum(msg.get('token_count', 0) for msg in messages_to_summarize)
                    new_tokens = estimate_tokens(summary)
                    tokens_saved = old_tokens - new_tokens
                    
                    # Update session with summary
                    await collection.update_one(
                        {"session_id": session_id},
                        {
                            "$set": {
                                "summary.compressed_context": summary,
                                "summary.last_summarized_at": datetime.now(timezone.utc),
                                "summary.total_tokens_saved": tokens_saved
                            }
                        }
                    )
                    
                    logger.info(
                        "summarization_complete",
                        session_id=session_id,
                        messages_summarized=len(messages_to_summarize),
                        tokens_saved=tokens_saved
                    )
        
        except Exception as e:
            logger.error(
                "summarization_error",
                session_id=session_id,
                error=str(e)
            )
    
    @traceable(
        name="summarize_with_llm",
        run_type="chain",
        tags=["context", "summarization"]
    )
    async def _summarize_with_llm(self, conversations: List[Dict]) -> str:
        """
        Use LLM to create a compressed summary of conversations.
        
        Args:
            conversations: List of conversation dictionaries
            
        Returns:
            Compressed summary string
        """
        try:
            # Build a concise representation of conversations
            conv_text = []
            countries_mentioned = set()
            
            for conv in conversations:
                question = conv.get('question', '')
                graph_state = conv.get('graph_state', {})
                country = graph_state.get('country_name', '')
                answer = graph_state.get('final_answer', '')
                
                if country:
                    countries_mentioned.add(country)
                
                conv_text.append(f"Q: {question}\nA: {answer}\n")
            
            conversation_history = "\n".join(conv_text)
            
            # Create summarization prompt
            prompt = f"""Summarize the following conversation history into a concise summary (max 3-4 sentences).
Focus on:
1. Countries that were discussed
2. Key facts that were mentioned
3. Main topics of interest

Conversation History:
{conversation_history}

Provide a brief summary:"""
            
            messages = [HumanMessage(content=prompt)]
            
            # Use LLM service with fallback support
            llm_response = await llm_service.invoke(
                messages=messages,
                temperature=0,
                operation="summarization",
                session_id=None  # Summarization not tied to specific session
            )
            
            summary = llm_response.content.strip()
            
            # Log provider and cost
            logger.info(
                "summarization_llm_usage",
                provider=llm_response.provider,
                fallback_used=llm_response.fallback_used,
                cost=llm_response.estimated_cost_usd
            )
            
            # Add countries mentioned
            if countries_mentioned:
                summary = f"Countries discussed: {', '.join(sorted(countries_mentioned))}. {summary}"
            
            return summary
            
        except Exception as e:
            logger.error("llm_summarization_error", error=str(e))
            # Fallback: simple concatenation
            countries = set()
            for conv in conversations:
                country = conv.get('graph_state', {}).get('country_name')
                if country:
                    countries.add(country)
            
            if countries:
                return f"Previous discussion covered: {', '.join(sorted(countries))}"
            return "Previous conversation history available."
    
    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session metadata and statistics.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Session information dictionary or None
        """
        try:
            collection = self._get_collection()
            session = await collection.find_one(
                {"session_id": session_id},
                {"_id": 0, "metadata": 1, "created_at": 1, "last_accessed": 1}
            )
            return session
        except Exception as e:
            logger.error("session_info_error", session_id=session_id, error=str(e))
            return None
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and all its conversations.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            True if deleted successfully
        """
        try:
            collection = self._get_collection()
            result = await collection.delete_one({"session_id": session_id})
            
            if result.deleted_count > 0:
                logger.info("session_deleted", session_id=session_id)
                return True
            return False
            
        except Exception as e:
            logger.error("session_deletion_error", session_id=session_id, error=str(e))
            return False
    
    @traceable(
        name="get_country_from_session",
        run_type="retriever",
        tags=["context", "cache", "retrieval"]
    )
    async def get_country_from_session(self, session_id: str, country_name: str) -> Optional[Dict[str, Any]]:
        """
        Get country data from session cache if it exists.
        
        Args:
            session_id: Unique session identifier
            country_name: Name of the country
            
        Returns:
            Country data dictionary or None if not cached
        """
        try:
            collection = self._get_collection()
            session = await collection.find_one(
                {"session_id": session_id},
                {"countries_cache": 1}
            )
            
            if not session or "countries_cache" not in session:
                return None
            
            # Check if country exists in cache (case-insensitive)
            country_key = country_name.lower()
            countries_cache = session.get("countries_cache", {})
            
            if country_key in countries_cache:
                logger.info("session_country_cache_hit", session_id=session_id, country=country_name)
                return countries_cache[country_key]
            
            return None
            
        except Exception as e:
            logger.error("country_cache_retrieval_error", session_id=session_id, error=str(e))
            return None
    
    @traceable(
        name="save_country_to_session",
        run_type="chain",
        tags=["context", "cache", "storage"]
    )
    async def save_country_to_session(
        self,
        session_id: str,
        country_name: str,
        country_data: Dict[str, Any]
    ):
        """
        Save country data to session cache for future use.
        
        Args:
            session_id: Unique session identifier
            country_name: Name of the country
            country_data: Full country data from API
        """
        try:
            collection = self._get_collection()
            country_key = country_name.lower()
            
            # Update or create the countries cache
            await collection.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        f"countries_cache.{country_key}": country_data,
                        "last_accessed": datetime.now(timezone.utc)
                    },
                    "$setOnInsert": {
                        "created_at": datetime.now(timezone.utc)
                    }
                },
                upsert=True
            )
            
            logger.info("country_cached_in_session", session_id=session_id, country=country_name)
            
        except Exception as e:
            logger.error("country_cache_save_error", session_id=session_id, error=str(e))


# Global instance
context_manager = ContextManager()
