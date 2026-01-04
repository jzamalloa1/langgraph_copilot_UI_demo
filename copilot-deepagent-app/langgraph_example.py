"""
Example LangGraph Agent for Generative UI using create_agent
=============================================================

This example shows how to create a LangGraph agent using the create_agent
framework that works with the CopilotKit Generative UI frontend.

Install dependencies:
    pip install langgraph langchain-openai langchain-anthropic matplotlib numpy

Run this file with:
    langgraph dev
"""

from typing import Literal
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
import base64
from io import BytesIO
import matplotlib.pyplot as plt
import numpy as np


# ============================================================================
# TOOLS DEFINITION
# ============================================================================

@tool
def generate_line_plot(
    x_values: list[float],
    y_values: list[float],
    title: str = "Generated Plot",
    xlabel: str = "X",
    ylabel: str = "Y",
) -> dict:
    """
    Generate a line plot and return it as base64 data URI.

    Use this tool when you need to create a visualization of data.
    The plot will be displayed in the user's interface.

    Args:
        x_values: List of x-axis data points
        y_values: List of y-axis data points
        title: Title for the plot
        xlabel: Label for x-axis
        ylabel: Label for y-axis

    Returns:
        Dictionary with image data and metadata
    """
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(x_values, y_values, marker='o', linestyle='-', linewidth=2, markersize=6)
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)

    # Convert to base64
    buffer = BytesIO()
    fig.savefig(buffer, format='png', bbox_inches='tight', dpi=150)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close(fig)

    data_uri = f"data:image/png;base64,{image_base64}"

    # Return in format expected by Generative UI
    return {
        "type": "image",
        "format": "base64",
        "data": data_uri,
        "title": title,
        "description": f"Line plot with {len(x_values)} data points"
    }


@tool
def generate_scatter_plot(
    x_values: list[float],
    y_values: list[float],
    title: str = "Scatter Plot",
    xlabel: str = "X",
    ylabel: str = "Y",
) -> dict:
    """
    Generate a scatter plot and return it as base64 data URI.

    Use this tool to visualize the relationship between two variables.

    Args:
        x_values: List of x-axis data points
        y_values: List of y-axis data points
        title: Title for the plot
        xlabel: Label for x-axis
        ylabel: Label for y-axis

    Returns:
        Dictionary with image data and metadata
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(x_values, y_values, alpha=0.6, s=50)
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)

    buffer = BytesIO()
    fig.savefig(buffer, format='png', bbox_inches='tight', dpi=150)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close(fig)

    data_uri = f"data:image/png;base64,{image_base64}"

    return {
        "type": "image",
        "format": "base64",
        "data": data_uri,
        "title": title,
        "description": f"Scatter plot with {len(x_values)} data points"
    }


@tool
def analyze_sine_wave(
    frequency: float = 1.0,
    amplitude: float = 1.0,
    num_points: int = 100
) -> dict:
    """
    Generate and analyze a sine wave, then create a visualization.

    Args:
        frequency: Frequency of the sine wave (default: 1.0)
        amplitude: Amplitude of the sine wave (default: 1.0)
        num_points: Number of data points to generate (default: 100)

    Returns:
        Dictionary with analysis results and visualization
    """
    x = np.linspace(0, 4 * np.pi, num_points)
    y = amplitude * np.sin(frequency * x)

    # Create plot
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(x, y, 'b-', linewidth=2, label=f'A={amplitude}, f={frequency}')
    ax.axhline(y=0, color='k', linestyle='--', alpha=0.3)
    ax.set_xlabel('x (radians)', fontsize=12)
    ax.set_ylabel('y = A·sin(f·x)', fontsize=12)
    ax.set_title(f'Sine Wave Analysis (A={amplitude}, f={frequency})', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    buffer = BytesIO()
    fig.savefig(buffer, format='png', bbox_inches='tight', dpi=150)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close(fig)

    data_uri = f"data:image/png;base64,{image_base64}"

    return {
        "type": "image",
        "format": "base64",
        "data": data_uri,
        "title": f"Sine Wave (A={amplitude}, f={frequency})",
        "description": f"Sine wave with amplitude {amplitude} and frequency {frequency}",
        "analysis": {
            "max_value": float(np.max(y)),
            "min_value": float(np.min(y)),
            "mean_value": float(np.mean(y)),
        }
    }


@tool
def create_histogram(
    data: list[float],
    bins: int = 20,
    title: str = "Histogram",
    xlabel: str = "Value",
) -> dict:
    """
    Create a histogram from data.

    Args:
        data: List of numerical values
        bins: Number of bins for the histogram
        title: Title for the plot
        xlabel: Label for x-axis

    Returns:
        Dictionary with histogram image
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(data, bins=bins, alpha=0.7, color='blue', edgecolor='black')
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')

    buffer = BytesIO()
    fig.savefig(buffer, format='png', bbox_inches='tight', dpi=150)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close(fig)

    data_uri = f"data:image/png;base64,{image_base64}"

    return {
        "type": "image",
        "format": "base64",
        "data": data_uri,
        "title": title,
        "description": f"Histogram with {bins} bins from {len(data)} data points"
    }


# ============================================================================
# STATE ANNOTATION (for Generative UI)
# ============================================================================

# Custom state annotation to include UI fields
from typing import Annotated
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

class State(TypedDict):
    """Extended state with Generative UI fields"""
    messages: Annotated[list, add_messages]

    # Generative UI fields
    current_step: str
    progress: float
    message: str
    status: str
    image_url: str
    image_title: str


# ============================================================================
# AGENT CREATION
# ============================================================================

def create_visualization_agent(llm):
    """
    Create a ReAct agent with visualization tools using create_react_agent.

    Args:
        llm: Language model to use (e.g., ChatOpenAI, ChatAnthropic)

    Returns:
        Compiled agent graph
    """
    # Define tools
    tools = [
        generate_line_plot,
        generate_scatter_plot,
        analyze_sine_wave,
        create_histogram,
    ]

    # System message for the agent
    system_message = """You are a helpful data visualization and analysis assistant.

When users ask you to create plots or visualizations:
1. Use the appropriate tool to generate the visualization
2. After generating a plot, call the 'display_image' frontend tool to show it to the user
3. Explain what the visualization shows

Available tools:
- generate_line_plot: Create line plots for continuous data
- generate_scatter_plot: Create scatter plots to show relationships
- analyze_sine_wave: Generate and visualize sine waves
- create_histogram: Create histograms for data distribution

The tools return image data in a special format. When you receive the result,
look for the 'data' field which contains a base64 data URI, and use the
'display_image' tool (available in the frontend) to show it to the user.

Example workflow:
1. User: "Show me a sine wave"
2. You: Call analyze_sine_wave tool
3. Tool returns: {"data": "data:image/png;base64,...", "title": "Sine Wave"}
4. You: Call display_image with the data URI
5. You: Explain the visualization to the user
"""

    # Create memory checkpointer
    memory = MemorySaver()

    # Create the agent
    agent = create_react_agent(
        llm,
        tools=tools,
        checkpointer=memory,
        state_schema=State,
        state_modifier=system_message,
    )

    return agent


# ============================================================================
# EXAMPLE USAGE WITH DIFFERENT LLM PROVIDERS
# ============================================================================

def create_agent_with_openai():
    """Create agent with OpenAI"""
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    return create_visualization_agent(llm)


def create_agent_with_anthropic():
    """Create agent with Anthropic"""
    from langchain_anthropic import ChatAnthropic

    llm = ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=0)
    return create_visualization_agent(llm)


# Default agent (use this in your deployment)
# Change based on your preferred LLM provider
def get_agent():
    """Get the default agent - modify to use your preferred LLM"""
    try:
        return create_agent_with_anthropic()
    except Exception:
        # Fallback to OpenAI if Anthropic is not configured
        return create_agent_with_openai()


# Export for LangGraph deployment
graph = get_agent()


# ============================================================================
# TESTING (Optional)
# ============================================================================

if __name__ == "__main__":
    import os

    # Make sure you have API keys set
    # export OPENAI_API_KEY=...
    # or
    # export ANTHROPIC_API_KEY=...

    print("Testing LangGraph agent with create_react_agent...")

    # Get the agent
    agent = graph

    # Test with a simple query
    config = {"configurable": {"thread_id": "test-1"}}

    print("\n🧪 Test 1: Generate sine wave")
    print("-" * 50)

    result = agent.invoke(
        {
            "messages": [
                HumanMessage(content="Generate a sine wave with amplitude 2 and frequency 0.5")
            ]
        },
        config=config
    )

    print("\nAgent response:")
    for msg in result["messages"]:
        if isinstance(msg, AIMessage):
            print(f"  {msg.content}")

    print("\n✅ Test complete!")
    print("\nTo deploy:")
    print("1. Create langgraph.json (see below)")
    print("2. Run: langgraph dev")
    print("3. Agent available at http://localhost:2024")


# ============================================================================
# DEPLOYMENT CONFIGURATION
# ============================================================================

"""
To deploy this agent with LangGraph Platform:

1. Create a langgraph.json file:
{
  "dependencies": ["."],
  "graphs": {
    "my_agent": "./langgraph_example.py:graph"
  },
  "env": ".env"
}

2. Create a .env file with your API keys:
OPENAI_API_KEY=your_key_here
# or
ANTHROPIC_API_KEY=your_key_here

3. Install dependencies:
pip install langgraph langchain-openai langchain-anthropic matplotlib numpy

4. Start the server:
langgraph dev

5. The agent will be available at:
http://localhost:2024

6. Update your Next.js .env.local:
LANGGRAPH_DEPLOYMENT_URL=http://localhost:2024

7. Update app/api/copilotkit/route.ts:
graphId: "my_agent"

8. Start your Next.js app and test!

Example queries to test:
- "Generate a sine wave with amplitude 2"
- "Show me a scatter plot of random data"
- "Create a histogram of normal distribution"
- "Plot a line chart of y = x^2 from 0 to 10"
"""
