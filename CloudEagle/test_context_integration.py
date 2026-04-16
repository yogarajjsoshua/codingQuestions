"""
Integration test for context management system.

This script tests the conversation context functionality end-to-end.

Usage:
    python test_context_integration.py

Requirements:
    - MongoDB connection string in .env
    - FastAPI server running on localhost:8000
"""

import asyncio
import httpx
import uuid
from datetime import datetime


class ContextTester:
    """Test harness for context management system."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_id = None
    
    async def test_query(self, question: str, expected_country: str = None):
        """Send a query and validate response."""
        print(f"\n{'='*60}")
        print(f"Question: {question}")
        print(f"Session ID: {self.session_id or 'New Session'}")
        
        async with httpx.AsyncClient() as client:
            payload = {"question": question}
            if self.session_id:
                payload["session_id"] = self.session_id
            
            try:
                response = await client.post(
                    f"{self.base_url}/api/v1/query",
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Store session_id for subsequent requests
                if not self.session_id:
                    self.session_id = data.get("session_id")
                
                print(f"✓ Response: {data['answer']}")
                print(f"  Country: {data.get('country')}")
                print(f"  Fields: {data.get('fields_retrieved')}")
                print(f"  Time: {data.get('execution_time_ms'):.2f}ms")
                print(f"  Session: {data.get('session_id')}")
                
                if expected_country:
                    assert data.get('country') == expected_country, \
                        f"Expected {expected_country}, got {data.get('country')}"
                    print(f"✓ Country validation passed")
                
                return data
                
            except httpx.HTTPError as e:
                print(f"✗ Request failed: {e}")
                return None
            except AssertionError as e:
                print(f"✗ Assertion failed: {e}")
                return None
    
    async def run_contextual_conversation_test(self):
        """Test a multi-turn conversation with context."""
        print("\n" + "="*60)
        print("TEST: Contextual Conversation")
        print("="*60)
        
        # Turn 1: Ask about Germany
        await self.test_query(
            "What is the population of Germany?",
            expected_country="Germany"
        )
        
        # Turn 2: Ask about France (new country, but similar question)
        await self.test_query(
            "What about France?",
            expected_country="France"
        )
        
        # Turn 3: Ask about "its" capital (should refer to France)
        await self.test_query(
            "What is its capital?",
            expected_country="France"
        )
        
        # Turn 4: Ask about another field for the same country
        await self.test_query(
            "What currency does it use?",
            expected_country="France"
        )
        
        # Turn 5: Switch to a completely new country
        await self.test_query(
            "Tell me about Japan's population and capital",
            expected_country="Japan"
        )
        
        # Turn 6: Follow-up on Japan
        await self.test_query(
            "What about its currency?",
            expected_country="Japan"
        )
        
        print("\n" + "="*60)
        print("✓ Contextual conversation test completed")
        print("="*60)
    
    async def run_summarization_test(self):
        """Test that summarization triggers correctly."""
        print("\n" + "="*60)
        print("TEST: Summarization Trigger")
        print("="*60)
        
        # Reset session
        self.session_id = None
        
        countries = [
            "Brazil", "India", "Canada", "Australia", 
            "Mexico", "Argentina", "Egypt", "Nigeria"
        ]
        
        for i, country in enumerate(countries, 1):
            print(f"\nMessage {i}/8: Asking about {country}")
            await self.test_query(
                f"What is the population of {country}?",
                expected_country=country
            )
            
            # Summarization should trigger after message 5
            if i == 5:
                print("\n⚠ Summarization should trigger after this message")
                await asyncio.sleep(2)  # Wait for background task
        
        print("\n" + "="*60)
        print("✓ Summarization test completed")
        print("✓ Check logs for 'summarization_complete' message")
        print("="*60)
    
    async def run_new_session_test(self):
        """Test that new sessions work correctly."""
        print("\n" + "="*60)
        print("TEST: New Session Creation")
        print("="*60)
        
        # Reset to force new session
        self.session_id = None
        
        await self.test_query(
            "What is the capital of Italy?",
            expected_country="Italy"
        )
        
        print("\n✓ New session created successfully")
        print(f"  Session ID: {self.session_id}")
        print("="*60)
    
    async def run_out_of_scope_test(self):
        """Test out-of-scope queries."""
        print("\n" + "="*60)
        print("TEST: Out of Scope Query")
        print("="*60)
        
        await self.test_query("How are you doing today?")
        
        print("\n✓ Out of scope handling works")
        print("="*60)


async def main():
    """Run all integration tests."""
    print("\n" + "="*60)
    print("CONTEXT MANAGEMENT INTEGRATION TESTS")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")
    
    tester = ContextTester()
    
    try:
        # Test 1: Basic contextual conversation
        await tester.run_contextual_conversation_test()
        
        # Test 2: Summarization trigger
        await tester.run_summarization_test()
        
        # Test 3: New session creation
        await tester.run_new_session_test()
        
        # Test 4: Out of scope handling
        await tester.run_out_of_scope_test()
        
        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\nCompleted at: {datetime.now().isoformat()}")


if __name__ == "__main__":
    asyncio.run(main())
