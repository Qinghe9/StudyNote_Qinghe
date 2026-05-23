from mcp import StdioServerParameters, stdio_client, ClientSession
import mcp.types as types
server_params = StdioServerParameters(
    command="python",
    args=["E:\Code\AIProgect\LangGraph\MCP\mcp_server.py"],
    env=None
)
async def handle_sampling_message(message: types.CreateMessageRequestParams) -> types.CreateMessageResult :
    print(f"sampling message: {message}")
    return types.CreateMessageResult(
        role="assistant",
        content=types.TextContent(
            type="text",
            text="Hello,world! from model"
        ),
        model="qwen-plus",
        stopReason="endTurn"
    )
async def run():
    async with stdio_client(server_params) as (read,write):
        async with ClientSession(read,write,sampling_callback=handle_sampling_message) as session:
            await session.initialize()
            prompts = await session.list_prompts()
            print(f"prompts: {prompts}")
            tools = await  session.list_tools()
            print(f"tools: {tools}")
            resources = await session.list_resources()
            print(f"resources: {resources}")
            result = await session.call_tool("weather",{"city":"北京"})
            print(f"result: {result}")
if __name__ == "__main__":
    import asyncio
    asyncio.run(run())