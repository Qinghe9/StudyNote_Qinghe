from mcp.server.fastmcp import FastMCP
mcp = FastMCP("roymcpdemo")
@mcp.tool()
def add(a: int, b: int) -> int :


    """Add two numbers together."""
    print(f"roy mcp demo called : add({a}, {b})")
    return a + b
@mcp.tool()
def weather(city: str):
    """获取某个城市的天⽓
        Args:
            city: 具体城市
        """
    return "城市" + city + ",今天天⽓不错"
@mcp.resource("greeting://{name}")
def greeting(name: str) -> str:
    """Greet a person by name."""
    print(f"roy mcp demo called : greeting({name})")
    return f"Hello, {name}!"
if __name__ == "__main__":
    # 以sse协议暴露服务。
    # mcp.run(transport='sse')
    # 以stdio协议暴露服务。
    mcp.run(transport='stdio')