#!/usr/bin/env python3
"""
Model Context Protocol (MCP) Server for Prolog Reasoning.

Wraps SemanticPrologSkill as an MCP server for use with LM Studio and other MCP clients.

Usage:
    python src/mcp_server.py --kb-path prolog/core.pl
    
For LM Studio, configure in settings.json:
    {
        "mcpServers": {
            "prolog": {
                "command": "python",
                "args": ["path/to/mcp_server.py"]
            }
        }
    }
"""

import json
import sys
import argparse
from typing import Any, Dict, Optional
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from parser.semantic import SemanticPrologSkill


class PrologMCPServer:
    """MCP Server exposing Prolog reasoning capabilities."""

    SUPPORTED_PROTOCOL_VERSIONS = [
        "2025-11-25",
        "2025-06-18",
        "2025-03-26",
        "2024-11-05",
    ]
    
    def __init__(self, kb_path: str = "prolog/core.pl"):
        """Initialize the MCP server with a knowledge base."""
        self.kb_path = self._resolve_kb_path(kb_path)
        self.skill = SemanticPrologSkill(kb_path=str(self.kb_path))
        self._request_id = 0

    def _resolve_kb_path(self, kb_path: str) -> Path:
        """Resolve KB paths relative to the repo root when needed."""
        candidate = Path(kb_path)
        if candidate.is_absolute():
            return candidate

        repo_root = Path(__file__).resolve().parent.parent
        return (repo_root / candidate).resolve()
        
    def get_tools(self) -> list:
        """Return available tools for MCP."""
        return [
            {
                "name": "query_prolog",
                "description": "Query the Prolog knowledge base using natural language. The system will parse your question, validate it against the known facts, and return a logical answer with explanation.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language query (e.g., 'Who is John's parent?' or 'Is Alice allergic to peanuts?')"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "list_known_facts",
                "description": "Show all known entities and relationships in the knowledge base. Useful for understanding what the system knows about.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "explain_error",
                "description": "Get a detailed explanation of what went wrong with a query. Provides 'Did you mean?' suggestions if relevant.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "error_message": {
                            "type": "string",
                            "description": "The error message or issue description"
                        }
                    },
                    "required": ["error_message"]
                }
            },
            {
                "name": "show_system_info",
                "description": "Display information about this Prolog MCP server, capabilities, and how to use it.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
    
    def query_prolog(self, query: str) -> Dict[str, Any]:
        """Execute a natural language query against the Prolog KB."""
        result = self.skill.query_nl(query)
        
        # Format the response for better readability
        if result.get("success"):
            return {
                "status": "success",
                "answer": result.get("explanation", "Query succeeded"),
                "confidence": result.get("validation_confidence", 0.0),
                "parsing_confidence": result.get("parsing_confidence", 0.0),
                "domain": result.get("domain", "general"),
                "nl_query": query,
                "metadata": {
                    "parsed_ir": result.get("parsed_ir"),
                    "proof_trace": result.get("explanation", "")
                }
            }
        else:
            # Return validation or query failure
            if result.get("validation_errors"):
                return {
                    "status": "validation_error",
                    "errors": result.get("validation_errors", []),
                    "validation_confidence": result.get("validation_confidence", 0.0),
                    "parsing_confidence": result.get("parsing_confidence", 0.0),
                    "nl_query": query,
                    "message": "The system found issues with your query. See errors for details and suggestions."
                }
            else:
                return {
                    "status": "no_results",
                    "message": result.get("why_it_failed", "No results found for this query"),
                    "suggestion": result.get("what_to_try", "Try rephrasing your question or adding more facts"),
                    "failure_explanation": result.get("failure_explanation"),
                    "nl_query": query
                }
    
    def list_known_facts(self) -> Dict[str, Any]:
        """List all known entities and relationships."""
        kb_entities = self.skill.validator.kb_entities if hasattr(self.skill, 'validator') else set()
        
        return {
            "status": "success",
            "known_entities": sorted(list(kb_entities)),
            "known_relationships": [
                "parent", "sibling", "ancestor", "child",
                "allergic_to", "takes_medication",
                "user", "role", "permission", "access_level",
                "can_access", "granted_permission"
            ],
            "note": (
                "This is a summary view of known entities plus supported relationship names. "
                "It is not a full dump of every stored fact."
            ),
            "knowledge_base_path": str(self.kb_path)
        }
    
    def explain_error(self, error_message: str) -> Dict[str, Any]:
        """Provide explanation for an error message."""
        return {
            "status": "success",
            "error_input": error_message,
            "explanation": f"Common issues: undefined entities (name not in KB), ungrounded predicates (unknown relationships), or no results (facts don't exist).",
            "suggestions": [
                "Check spelling of entity names",
                "Verify the relationship type exists",
                "Try asking about entities you know exist",
                "Use 'list_known_facts' to see available entities",
                "Run 'query_prolog' with a simpler question first"
            ],
            "learn_more": "See the training materials at training/03-learning-from-failures.md"
        }
    
    def show_system_info(self) -> Dict[str, Any]:
        """Show system information and capabilities."""
        return {
            "status": "success",
            "system": "Prolog Reasoning v2",
            "version": "0.5",
            "description": (
                "A local-first neuro-symbolic reliability layer for LLM agents. "
                "Natural language helps express intent; symbolic reasoning decides truth."
            ),
            "knowledge_base_path": str(self.kb_path),
            "core_idea": "Memories are timestamped. Facts are not.",
            "capabilities": [
                "Natural language query processing",
                "Deterministic knowledge-base reasoning",
                "Semantic validation before query execution",
                "Friendly failure explanations with suggestions",
                "Proof-trace generation"
            ],
            "supported_domains": [
                "Family relationships (parent, sibling, ancestor)",
                "Access control (permissions, roles, users)",
                "General knowledge representations"
            ],
            "example_queries": [
                "Who is John's parent?",
                "Is Alice an ancestor of Bob?",
                "Can admin read files?",
                "What is Bob allergic to?"
            ],
            "learn_more": {
                "getting_started": "See training/01-llm-memory-magic.md",
                "kb_design": "See training/02-knowledge-bases-101.md",
                "error_handling": "See training/03-learning-from-failures.md",
                "lm_studio": "See docs/lm-studio-mcp-guide.md",
                "github": "https://github.com/dr3d/prolog-reasoning-v2"
            }
        }
    
    def handle_tool_call(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Route tool calls to appropriate handler."""
        handlers = {
            "query_prolog": lambda: self.query_prolog(tool_input.get("query", "")),
            "list_known_facts": lambda: self.list_known_facts(),
            "explain_error": lambda: self.explain_error(tool_input.get("error_message", "")),
            "show_system_info": lambda: self.show_system_info()
        }
        
        handler = handlers.get(tool_name)
        if handler:
            try:
                return handler()
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "tool": tool_name
                }
        else:
            return {
                "status": "error",
                "error": f"Unknown tool: {tool_name}",
                "available_tools": list(handlers.keys())
            }
    
    def _negotiate_protocol_version(self, requested: Optional[str]) -> str:
        """Return the requested protocol version if supported, else our default."""
        if requested in self.SUPPORTED_PROTOCOL_VERSIONS:
            return requested
        return self.SUPPORTED_PROTOCOL_VERSIONS[0]

    def _format_tool_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Wrap tool output in MCP CallToolResult shape."""
        is_error = result.get("status") in {"error", "validation_error", "no_results"}
        pretty = json.dumps(result, indent=2)
        return {
            "content": [
                {
                    "type": "text",
                    "text": pretty
                }
            ],
            "structuredContent": result,
            "isError": is_error
        }

    def process_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process an MCP request (simplified for stdio protocol)."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id", self._request_id)
        self._request_id = request_id + 1

        # MCP clients typically begin with initialize, followed by
        # notifications/initialized before tool discovery.
        if method == "initialize":
            client_info = params.get("clientInfo", {})
            requested_protocol = params.get("protocolVersion")
            negotiated_protocol = self._negotiate_protocol_version(requested_protocol)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": negotiated_protocol,
                    "capabilities": {
                        "tools": {
                            "listChanged": False
                        }
                    },
                    "serverInfo": {
                        "name": "prolog-reasoning",
                        "version": "0.5"
                    },
                    "instructions": (
                        "Use query_prolog for natural-language queries against the "
                        "deterministic Prolog knowledge base. Use list_known_facts "
                        "first if you need to inspect available entities."
                    ),
                    "clientInfoEcho": client_info
                }
            }

        elif method == "notifications/initialized":
            return None

        elif method == "ping":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {}
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": self.get_tools()
                }
            }
        
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_input = params.get("arguments", {})
            result = self.handle_tool_call(tool_name, tool_input)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": self._format_tool_result(result)
            }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }


def main():
    """Run the MCP server."""
    parser = argparse.ArgumentParser(description="Prolog Reasoning MCP Server")
    parser.add_argument("--kb-path", default="prolog/core.pl", help="Path to Prolog knowledge base")
    parser.add_argument("--stdio", action="store_true", help="Use stdio transport (for LM Studio)")
    parser.add_argument("--test", action="store_true", help="Run in test mode (show available tools)")
    args = parser.parse_args()
    
    # Initialize server
    server = PrologMCPServer(kb_path=args.kb_path)
    
    if args.test:
        # Test mode: show available tools and exit
        print("MCP Server initialized successfully\n")
        print("Available Tools:")
        for tool in server.get_tools():
            print(f"  - {tool['name']}: {tool['description']}")
        print("\nExample usage:")
        print('  query_prolog({"query": "Who is John\'s parent?"})')
        sys.exit(0)
    
    if args.stdio:
        # Stdio transport for LM Studio
        print("Prolog Reasoning MCP Server ready", file=sys.stderr)
        print("Reading from stdin, writing to stdout", file=sys.stderr)
        
        try:
            for line in sys.stdin:
                try:
                    payload = json.loads(line)

                    # JSON-RPC batch support: respond with an array of
                    # responses, skipping notifications that return None.
                    if isinstance(payload, list):
                        responses = []
                        for request in payload:
                            response = server.process_request(request)
                            if response is not None:
                                responses.append(response)
                        if responses:
                            print(json.dumps(responses))
                            sys.stdout.flush()
                    else:
                        response = server.process_request(payload)
                        if response is not None:
                            print(json.dumps(response))
                            sys.stdout.flush()
                except json.JSONDecodeError:
                    print(json.dumps({
                        "error": "Invalid JSON",
                        "received": line.strip()
                    }))
                    sys.stdout.flush()
        except KeyboardInterrupt:
            print("Server shutting down", file=sys.stderr)
            sys.exit(0)
    else:
        # Interactive mode for testing
        print("Prolog Reasoning MCP Server (Interactive Mode)")
        print("Available tools:", [t["name"] for t in server.get_tools()])
        print("\nType 'help' for commands, 'quit' to exit\n")
        
        while True:
            try:
                user_input = input("> ").strip()
                
                if user_input.lower() == "quit":
                    print("Goodbye!")
                    break
                elif user_input.lower() == "help":
                    print("\nAvailable commands:")
                    print("  query <natural language>  - Query the knowledge base")
                    print("  list                     - Show known facts")
                    print("  info                     - System information")
                    print("  help                     - Show this help")
                    print("  quit                     - Exit")
                    print()
                elif user_input.lower().startswith("query "):
                    query = user_input[6:].strip()
                    result = server.query_prolog(query)
                    print(json.dumps(result, indent=2))
                elif user_input.lower() == "list":
                    result = server.list_known_facts()
                    print(json.dumps(result, indent=2))
                elif user_input.lower() == "info":
                    result = server.show_system_info()
                    print(json.dumps(result, indent=2))
                else:
                    print("Unknown command. Type 'help' for options.")
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")


if __name__ == "__main__":
    main()
