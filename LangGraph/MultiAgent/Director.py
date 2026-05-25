from operator import add
from typing import TypedDict, Annotated
from langgraph.constants import END, START
from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.config import get_stream_writer
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import InMemorySaver
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
import asyncio

from langchain_community.chat_models import ChatTongyi

nodes= ["supervisor", "travel", "joke", "couplet", "other"]

# 构建阿⾥云百炼⼤模型客户端
model = ChatTongyi(
    api_key="sk-0e1e78cdb7034f8babefc27516eaedf2",
    base_url="https://api.aliyun.com/v1",
    model="qwen-max"
)

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add]
    type: str


def other_node(state: State):
    print(">>> other_node")
    writer = get_stream_writer()
    writer({"node": ">>> other_node"})
    return {"messages": [HumanMessage(content="我暂时无法回答这个问题")], "type": "other"}


def supervisor_node(state: State):
    print(">>> supervisor_node")
    writer = get_stream_writer()
    writer({"node": ">>> supervisor_node"})
    # 根据用户的问题进行分类，分类结果保存在type中，用于判断应该进入哪个节点
    prompt = """你是一个专业的客服助手，负责对用户的问题进行分类，并将任务分给其他Agent执行。
    如果用户的问题是和旅游路线规划相关的，那就返回 travel 。
    如果用户的问题是希望讲一个笑话，那就返回 joke 。
    如果用户的问题是希望对一个对联，那就返回 couplet 。
    如果是其他的问题，返回 other 。
    除了这几个选项外，不要返回任何其他的内容。
    """

    prompts = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": state["messages"][0]}
    ]

    # 如果已经有分类结果了，就直接返回，不需要再调用模型了
    if "type" in state:
        writer({"supervisor_step": f"已获得{state['type']}智能体分类结果"})
        return {"type": END}
    else:
        response = model.invoke(prompts)
        typeRes= response.content
        print(f"【DEBUG】模型原始返回: '{typeRes}'")
        writer({"supervisor_step": f"模型返回的分类结果是: {typeRes}"})
        if typeRes in nodes:
            return {"type": typeRes}
        else:
            raise ValueError(f"模型返回了一个未知的分类结果: {typeRes}")

    return {}


def travel_node(state: State):
    print(">>> travel_node")
    writer = get_stream_writer()
    writer({"node": ">>> travel_node"})

    system_prompt = "你是一个专业的旅行规划助手，根据用户的问题，生成一个旅游路线规划。请用中文回答，并返回一个不超过100字的规划结果。"

    prompts = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": state["messages"][0]}
    ]

    #高德mcp
    # 相比Cline客户端配置，只要增加transport属性即可。不过测试stremaable_http有问题。不知道是不是版本的原因。
    client = MultiServerMCPClient(
        {
            # "amap-amap-sse": {
            #     "url": "https://mcp.amap.com/sse?key=451ad40d0e39453600f2a305e31eabe4",
            #     "transport":"streamable_http"
            # },
            "amap-maps": {
                "command": "npx",
                "args": [
                    "-y",
                    "@amap/amap-maps-mcp-server"
                ],
                "env": {
                    "AMAP_MAPS_API_KEY": "451ad40d0e39453600f2a305e31eabe4"
                },
                "transport":"stdio"
            }
        }
    )

    #同步调用工具
    tools = asyncio.run(client.get_tools())
    agent = create_agent(
        model=model,
        tools=tools
    )
    response = asyncio.run(agent.ainvoke({"messages": prompts}))
    writer({"travel_result": response["messages"][-1].content})
    return {"messages": [HumanMessage(content=response["messages"][-1].content)], "type": "travel"}

    return {"messages": [HumanMessage(content="travel_node")], "type": "travel"}


def joke_node(state: State):
    print(">>> joke_node")
    writer = get_stream_writer()
    writer({"node": ">>> joke_node"})
    
    SystemPrompt = "你是一个笑话大师，请根据用户的提问，讲一个不超过100字的笑话。"

    prompts = [
        {"role": "system", "content": SystemPrompt},
        {"role": "user", "content": state["messages"][0]}
    ]

    response = model.invoke(prompts)
    writer({"joke_response": f"模型返回的笑话是: {response.content}"})

    return {"messages": [HumanMessage(content=response.content)], "type": "joke"}

def couplet_node(state: State):
    print(">>> couplet_node")
    writer = get_stream_writer()
    writer({"node": ">>> couplet_node"})

    return {"messages": [HumanMessage(content="couplet_node")], "type": "couplet"}


# 定义路由函数，根据state中的type字段来判断应该进入哪个节点
def routing_func(state: State):
    if state["type"] == "travel":
        return "travel_node"
    elif state["type"] == "joke":
        return "joke_node"
    elif state["type"] == "couplet":
        return "couplet_node"
    elif state["type"] == END:
        return END
    else:
        return "other_node"

# 构建图
builder = StateGraph(State)

# 添加节点
builder.add_node("supervisor_node", supervisor_node)
builder.add_node("travel_node", travel_node)
builder.add_node("joke_node", joke_node)
builder.add_node("couplet_node", couplet_node)
builder.add_node("other_node", other_node)

# 添加边
builder.add_edge(START,"supervisor_node")
builder.add_conditional_edges("supervisor_node", routing_func, ["travel_node", "joke_node", "couplet_node", "other_node",END])
builder.add_edge("travel_node", "supervisor_node")
builder.add_edge("joke_node", "supervisor_node")
builder.add_edge("couplet_node", "supervisor_node")
builder.add_edge("other_node", "supervisor_node")

# 构建Graph
checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)

if __name__ == "__main__":
    config={
        "configurable": {
            "thread_id": 1
        }
    }

    for chunk in graph.stream({"messages": ["给我规划一条广州到肇庆的驾车路线"]},
                config,
                stream_mode="custom"):
        print(chunk)

    # res = graph.invoke({"messages": ["今天的天气怎么样？"]},
    #             config,
    #             stream_mode="values")
    # print(res["messages"][-1].content)