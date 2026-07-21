# MCP-based Knowledge Graph Construction System

A fully automated knowledge graph construction system built on the Model Context Protocol (MCP), implementing a sophisticated 3-stage data processing pipeline for intelligent knowledge extraction and graph generation.

## Overview

This project implements an advanced knowledge graph construction system that automatically processes raw text data through three intelligent stages:

1. **Data Quality Assessment** - Evaluates completeness, consistency, and relevance
2. **Knowledge Completion** - Enhances low-quality data using LLM and external knowledge bases
3. **Knowledge Graph Construction** - Builds structured knowledge graphs with confidence scoring

The system is built on the MCP (Model Context Protocol) architecture, providing a clean client-server interface for seamless integration and scalability.

## Repository Layout

- `content_enhancement/`: quality analysis and KG enhancement implementation.
- `evaluate_kg/`: KG quality evaluation utilities.
- `data/`: datasets, KG CSV files, and rule-test data.
- `exps/`: experiment scripts and result artifacts for the papers.
- `paper1/`, `paper2/`: LaTeX sources, figures, and references for the two papers.
- `rule_generate_scripts/`: rule generation and rule evaluation scripts.
- `scripts/`: utility scripts, organized by converters, data generation, and monitoring.
- `docs/`: audits, usage notes, paper revision records, and method explanations.
- `outputs/`: generated graph exports and other non-source outputs.

See `docs/README.md` for the detailed file placement guide.

## Key Features

### Fully Automated Processing
- **Zero Manual Intervention**: Automatically detects data quality and processing needs
- **Intelligent Pipeline**: Adapts processing strategy based on input data characteristics
- **Real-time Processing**: Immediate knowledge graph generation from raw text

### 3-Stage Processing Pipeline

#### Stage 1: Data Quality Assessment
- **Completeness Analysis**: Evaluates entity and relationship coverage
- **Consistency Checking**: Detects semantic conflicts and contradictions
- **Relevance Scoring**: Assesses information relevance and meaningfulness
- **Quality Threshold**: Automatically determines if data needs enhancement

#### Stage 2: Knowledge Completion (for low-quality data)
- **Entity Enhancement**: Completes missing entity information
- **Relationship Inference**: Adds missing relationships between entities
- **Conflict Resolution**: Corrects semantic inconsistencies
- **Format Normalization**: Standardizes data format and structure
- **Implicit Knowledge Inference**: Extracts hidden knowledge patterns

#### Stage 3: Knowledge Graph Construction
- **Rule-based Extraction**: Fast, deterministic triple generation
- **LLM-enhanced Processing**: Advanced semantic understanding and relationship inference
- **Confidence Scoring**: Assigns reliability scores to extracted knowledge
- **Interactive Visualization**: Generates beautiful HTML visualizations

### MCP Architecture
- **Client-Server Design**: Clean separation of concerns
- **Standardized Protocol**: Built on MCP for interoperability
- **Tool-based Interface**: Modular, extensible tool system
- **Async Processing**: High-performance asynchronous operations

## Requirements

- **Python**: 3.11 or higher
- **UV Package Manager**: For dependency management
- **OpenAI-compatible API**: For LLM integration (DeepSeek, OpenAI, etc.)

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/turambar928/MCP_based_KG_construction.git
cd MCP_based_KG_construction

# Install dependencies
uv sync
```

### 2. Environment Configuration

Create a `.env` file with your API configuration:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.siliconflow.cn/v1  # or your preferred endpoint
OPENAI_MODEL=Qwen/QwQ-32B                      # or your preferred model
```

**Supported API Providers:**
- OpenAI: `https://api.openai.com/v1`
- DeepSeek: `https://api.deepseek.com`
- SiliconFlow: `https://api.siliconflow.cn/v1`
- Any OpenAI-compatible endpoint

### 3. Start the MCP Server

```bash
uv run kg_server.py
```

The server will start and listen for MCP client connections.

### 4. Running Tests

There are three ways to test the system:

#### a. Using MCP Inspector
```bash
npx -y @modelcontextprotocol/inspector uv run kg_server.py
```
After running this command, click the link that appears after "MCP Inspector is up and running at" to open the MCP Inspector in your browser. Once opened:
1. Click "Connect"
2. Select "Tools" from the top menu
3. Choose "build_knowledge_graph" from the list tools
4. Enter your text in the left panel to generate the knowledge graph

![MCP Inspector](./demo_images/1.png "MCP Inspector")

#### b. Using Client Code
```bash
uv run kg_client.py
```
After the connection is successful, enter your text to view the results.

![Client Code Execution](./demo_images/2.png "Client Code Execution")

#### c. Using Mainstream MCP Tools (Cursor, Cherry Studio, etc.)
Example: Running in Cherry Studio

In settings, select MCP servers, click "Add Server" (import from JSON). Here's the configuration JSON (make sure to modify the local path):

```json
{
  "mcpServers": {
    "kg_server": {
      "command": "uv",
      "args": [
        "--directory",
        "D:/mcp_getting_started",
        "run",
        "kg_server.py"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

After enabling this MCP server, you can use it in Cherry Studio.

![Using in Cherry Studio](./demo_images/3.png "Using in Cherry Studio")

## 🛠️ Usage Guide

### Interactive Client Commands

Once the client is running, you can use these commands:

```bash
# Build knowledge graph from text
build <your_text_here>

# Example usage
build 北京大学是中国著名的高等教育机构，位于北京市海淀区

# Run demonstration examples
demo

# Exit the client
quit
```

### Programmatic Usage

```python
from kg_client import KnowledgeGraphClient

async def main():
    client = KnowledgeGraphClient()
    await client.connect_to_server()

    # Build knowledge graph
    result = await client.build_knowledge_graph(
        "苹果公司的CEO是蒂姆·库克",
        output_file="my_graph.html"
    )

    print(f"Generated graph: {result}")
    await client.cleanup()
```

## Example Outputs

### High-Quality Input
```
Input: "北京大学是中国著名的高等教育机构，位于北京市海淀区。"
Processing: Direct Stage 3 (high quality detected)
Output:
- Entities: [北京大学, 中国, 高等教育机构, 北京市, 海淀区]
- Triples: [(北京大学, 是, 高等教育机构), (北京大学, 位于, 海淀区), ...]
- Visualization: Interactive HTML graph
```

### Low-Quality Input (Incomplete)
```
Input: "李华去巴黎"
Processing:
- Stage 1: Detects incomplete information
- Stage 2: Enhances with "巴黎位于法国", "李华是人"
- Stage 3: Builds enhanced knowledge graph
Output: Enriched knowledge graph with inferred relationships
```

### Low-Quality Input (Conflicting)
```
Input: "巴黎市是德国城市。"
Processing:
- Stage 1: Detects semantic conflict
- Stage 2: Corrects to "巴黎是法国城市"
- Stage 3: Builds corrected knowledge graph
Output: Corrected and enhanced knowledge graph
```

## MCP Tools API

The system exposes the following MCP tools for integration:

### `build_knowledge_graph`
**Description**: Complete pipeline for knowledge graph construction with automatic quality assessment and enhancement.

**Parameters**:
- `text` (string): Input text to process
- `output_file` (string, optional): HTML visualization output filename (default: "knowledge_graph.html")

**Returns**: JSON object containing:
- `success` (boolean): Processing success status
- `entities` (array): Extracted entities
- `triples` (array): Generated knowledge triples
- `confidence_scores` (array): Confidence scores for each triple
- `visualization_file` (string): Path to generated HTML visualization
- `processing_stages` (object): Details of each processing stage

**Example**:
```json
{
  "success": true,
  "entities": ["北京大学", "中国", "高等教育机构"],
  "triples": [
    {
      "subject": "北京大学",
      "predicate": "是",
      "object": "高等教育机构",
      "confidence": 0.95
    }
  ],
  "visualization_file": "knowledge_graph.html"
}
```

## Project Structure

```
├── kg_server.py              # Main MCP server implementation
├── kg_client.py              # Interactive client for testing
├── kg_utils.py               # Core knowledge graph construction utilities
├── kg_visualizer.py          # HTML visualization generator
├── data_quality.py           # Stage 1: Data quality assessment
├── knowledge_completion.py   # Stage 2: Knowledge completion and enhancement
├── pyproject.toml            # Project dependencies and configuration
├── .env                      # Environment variables (API keys)
└── README.md                 # This file
```

### Core Components

- **`kg_server.py`**: MCP server that orchestrates the 3-stage pipeline
- **`kg_client.py`**: Command-line client for interactive testing and batch processing
- **`kg_utils.py`**: Knowledge graph construction engine with rule-based and LLM-enhanced extraction
- **`kg_visualizer.py`**: Generates interactive HTML visualizations using Plotly
- **`data_quality.py`**: Implements quality assessment algorithms for completeness, consistency, and relevance
- **`knowledge_completion.py`**: Handles knowledge enhancement and conflict resolution

## Advanced Features

### Quality Assessment Metrics
- **Completeness Score**: Based on entity coverage and relationship density
- **Consistency Score**: Detects semantic conflicts and contradictions
- **Relevance Score**: Evaluates information meaningfulness
- **Composite Quality Score**: Weighted combination of all metrics

### Knowledge Enhancement Strategies
- **Entity Completion**: Adds missing entity attributes and types
- **Relationship Inference**: Discovers implicit relationships
- **Conflict Resolution**: Corrects factual inconsistencies
- **Format Normalization**: Standardizes entity and relationship representations

### Visualization Features
- **Interactive Network Graph**: Clickable nodes and edges
- **Entity Clustering**: Groups related entities by type
- **Confidence Visualization**: Color-coded confidence levels
- **Export Options**: HTML, PNG, SVG formats

## Technical Details

### Processing Pipeline
1. **Input Validation**: Checks text format and encoding
2. **Quality Assessment**: Multi-dimensional quality scoring
3. **Conditional Enhancement**: Applies enhancement only when needed
4. **Graph Construction**: Rule-based + LLM hybrid approach
5. **Confidence Calculation**: Bayesian confidence scoring
6. **Visualization Generation**: Interactive HTML output

### Performance Characteristics
- **Processing Speed**: ~1-3 seconds per text input
- **Memory Usage**: ~50-100MB for typical workloads
- **Scalability**: Async architecture supports concurrent processing
- **Accuracy**: 85-95% entity extraction, 80-90% relationship accuracy

## Development

### Running Tests

Refer to the "Running Tests" section above for three different testing methods:
- MCP Inspector (recommended for visual testing)
- Client code (for programmatic testing)
- Mainstream MCP tools (for integration testing)

```bash
# Quick test with demonstration examples
uv run kg_client.py
# Then type: demo

# Test with custom input
uv run kg_client.py "Your test text here"
```

### Adding New Features

1. **Custom Quality Metrics**: Extend `data_quality.py`
2. **New Enhancement Strategies**: Modify `knowledge_completion.py`
3. **Additional Visualization**: Enhance `kg_visualizer.py`
4. **New MCP Tools**: Add tools to `kg_server.py`

### Configuration Options

Environment variables in `.env`:
```env
# Required
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=your_api_endpoint
OPENAI_MODEL=your_model_name

# Optional
QUALITY_THRESHOLD=0.5          # Quality threshold for enhancement
MAX_ENTITIES=50                # Maximum entities per graph
VISUALIZATION_WIDTH=1200       # HTML visualization width
VISUALIZATION_HEIGHT=800       # HTML visualization height
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test thoroughly
4. Submit a pull request with detailed description

## Troubleshooting

### Common Issues

1. **Port Occupation Error**
   ```bash
   # Find process using the port
   netstat -ano | findstr :6277
   # Kill the process
   taskkill /PID <process_id> /F
   ```

2. **API Balance Insufficient**
   - Check API configuration in `.env` file
   - Ensure API account has sufficient balance

3. **Dependency Installation Issues**
   ```bash
   uv sync --reinstall
   ```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built on the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- Visualization powered by [Plotly](https://plotly.com/)
- Graph algorithms using [NetworkX](https://networkx.org/)
- LLM integration via [OpenAI API](https://openai.com/api/)

## Support

For questions, issues, or contributions:
- 📧 Email: tzf9282003@163.com
- 🐛 Issues: [GitHub Issues](https://github.com/turambar928/MCP_based_KG_construction/issues)
- 📖 Documentation: See `KNOWLEDGE_GRAPH_README.md` for detailed technical documentation

---
