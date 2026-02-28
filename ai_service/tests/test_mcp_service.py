"""Tests for MCP service tool loading."""

import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock
from services.mcp_service import load_all_tools, load_mcp_tools


@pytest.mark.asyncio
async def test_load_mcp_tools():
    """Test loading tools from MCP session."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.tools = [{"name": "tool1"}, {"name": "tool2"}]
    mock_session.list_tools.return_value = mock_result
    
    tools = await load_mcp_tools(mock_session)
    
    assert len(tools) == 2
    assert tools[0]["name"] == "tool1"
    assert tools[1]["name"] == "tool2"
    mock_session.list_tools.assert_called_once()


@pytest.mark.asyncio
async def test_load_all_tools_no_env():
    """Test load_all_tools returns empty list when no env vars set."""
    with patch.dict(os.environ, {}, clear=True):
        tools = await load_all_tools()
        assert tools == []


@pytest.mark.asyncio
async def test_load_all_tools_with_neo4j():
    """Test load_all_tools with NEO4J_MCP_URL configured."""
    mock_tools = [{"name": "neo4j_tool"}]
    
    with patch.dict(os.environ, {"NEO4J_MCP_URL": "http://neo4j-mcp:8000"}):
        with patch("services.mcp_service.sse_client") as mock_client:
            with patch("services.mcp_service.load_mcp_tools", return_value=mock_tools):
                mock_session = AsyncMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session.initialize = AsyncMock()
                
                mock_streams = AsyncMock()
                mock_streams.__aenter__ = AsyncMock(return_value=(None, None))
                mock_streams.__aexit__ = AsyncMock(return_value=None)
                mock_client.return_value = mock_streams
                
                with patch("services.mcp_service.ClientSession", return_value=mock_session):
                    tools = await load_all_tools()
                    assert len(tools) == 1
                    assert tools[0]["name"] == "neo4j_tool"


@pytest.mark.asyncio
async def test_load_all_tools_multiple_servers():
    """Test load_all_tools with multiple MCP servers configured."""
    mock_tools_1 = [{"name": "tool1"}]
    mock_tools_2 = [{"name": "tool2"}]
    
    with patch.dict(os.environ, {"NEO4J_MCP_URL": "http://neo4j:8000", "ANOTHER_MCP_URL": "http://other:8000"}):
        with patch("services.mcp_service.sse_client") as mock_client:
            call_count = [0]
            
            async def mock_load_tools(session):
                call_count[0] += 1
                return mock_tools_1 if call_count[0] == 1 else mock_tools_2
            
            with patch("services.mcp_service.load_mcp_tools", side_effect=mock_load_tools):
                mock_session = AsyncMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session.initialize = AsyncMock()
                
                mock_streams = AsyncMock()
                mock_streams.__aenter__ = AsyncMock(return_value=(None, None))
                mock_streams.__aexit__ = AsyncMock(return_value=None)
                mock_client.return_value = mock_streams
                
                with patch("services.mcp_service.ClientSession", return_value=mock_session):
                    tools = await load_all_tools()
                    assert len(tools) == 2
                    assert tools[0]["name"] == "tool1"
                    assert tools[1]["name"] == "tool2"


def test_mcp_service_structure():
    """Test MCP service has required functions."""
    from services import mcp_service
    assert hasattr(mcp_service, "load_all_tools")
    assert hasattr(mcp_service, "load_mcp_tools")
