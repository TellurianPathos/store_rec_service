# AI-Enhanced Store Recommendation Service

A containerized AI-powered product recommendation API built with FastAPI, featuring multiple AI provider integrations and comprehensive testing.

## 🚀 Features

- **AI-Enhanced Recommendations**: Integrate with OpenAI, Anthropic, Ollama, or custom AI APIs
- **Content-Based Filtering**: Traditional recommendation algorithms as fallback
- **Multiple AI Providers**: Support for OpenAI, Anthropic Claude, Ollama, and custom APIs
- **Flexible Configuration**: Easy setup for different environments and AI providers
- **Comprehensive Testing**: Unit tests, integration tests, and CI/CD pipelines
- **Professional Documentation**: OpenAPI/Swagger docs and detailed guides
- **Docker Support**: Containerized for easy deployment

## 🧪 Testing

This project includes comprehensive testing to ensure reliability and quality.

### Test Structure

```
tests/
├── conftest.py              # Test configuration and fixtures
├── test_ai_models.py        # Test AI model classes
├── test_ai_client.py        # Test AI client implementations
├── test_recommender.py      # Test basic recommendation engine
├── test_ai_recommender.py   # Test AI-enhanced recommender
└── test_api.py             # Test FastAPI endpoints
```

### Running Tests

#### Quick Test Run
```bash
# Install dependencies
uv sync --dev

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=term-missing
```

#### Using Test Runner Script
```bash
# Run comprehensive test suite
python run_tests.py
```

#### Test Categories

**Unit Tests**
```bash
# Test specific components
pytest tests/test_ai_models.py -v
pytest tests/test_recommender.py -v
```

**Integration Tests**
```bash
# Test API endpoints
pytest tests/test_api.py -v

# Run integration test script (requires running server)
python integration_tests.py
```

**AI-Specific Tests**
```bash
# Test AI functionality (may require API keys)
pytest tests/ -m ai -v
```

### Test Coverage

The test suite covers:
- ✅ **Model Validation**: Pydantic models and data structures
- ✅ **AI Client Logic**: All AI provider implementations
- ✅ **Recommendation Engines**: Both basic and AI-enhanced
- ✅ **API Endpoints**: All FastAPI routes and error handling
- ✅ **Configuration**: Setup and validation
- ✅ **Error Handling**: Graceful failure scenarios

### Continuous Integration

GitHub Actions automatically run tests on:
- Multiple Python versions (3.9, 3.10, 3.11)
- Different operating systems
- Various configurations (minimal, full AI)

See `.github/workflows/tests.yml` for the complete CI/CD pipeline.

## Project Description

This service provides AI-enhanced product recommendations using:

1. **Content-Based Filtering**: Analyzes product attributes using TF-IDF vectorization
2. **AI Enhancement**: Uses configurable AI providers to improve recommendations
3. **User Profiling**: AI-generated user profiles for better personalization
4. **Flexible Architecture**: Modular design supporting multiple AI providers

## License and Attribution

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Attribution**: If you use this code in your project, please include a reference to this repository and credit TellurianPathos as the original author.

### Quick Attribution Example
```
Recommendation system based on work by TellurianPathos
Repository: https://github.com/TellurianPathos/store_rec_service
```

## Prerequisites

- Docker
- Python 3.9+ (for local development)

## Quick Start

### Using Docker

1. Clone the repository:
   ```bash
   git clone https://github.com/TellurianPathos/store_rec_service.git
   cd store_rec_service
   ```

2. Build the Docker image:
   ```bash
   docker build -t store-rec-service .
   ```

3. Run the container:
   ```bash
   docker run -p 8000:8000 store-rec-service
   ```

4. Access the API at http://localhost:8000

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/TellurianPathos/store_rec_service.git
   cd store_rec_service
   ```

2. Create and activate a virtual environment:
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   uv add fastapi uvicorn[standard] pydantic scikit-learn pandas numpy joblib matplotlib seaborn
   uv add --dev jupyter httpx pytest
   ```

4. Train the recommendation model (if not already done):
   - Open and run the Jupyter notebook: `notebooks/1_data_exploration_and_model_training.ipynb`

5. Start the API server:
   ```bash
   uvicorn app.main:app --reload
   ```

6. Access the API at http://localhost:8000

## API Usage

### Health Check

```bash
curl -X GET "http://localhost:8000/health"
```

Expected response:
```json
{
  "status": "ok"
}
```

### Get Recommendations

```bash
curl -X POST "http://localhost:8000/recommend" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123", "num_recommendations": 3}'
```

Expected response:
```json
{
  "user_id": "user123",
  "recommendations": [
    {
      "id": "1",
      "name": "Stylish T-Shirt"
    },
    {
      "id": "3",
      "name": "Smartphone Case"
    },
    {
      "id": "7",
      "name": "Coffee Mug"
    }
  ]
}
```

## Project Structure

```
store_rec_service/
├── app/
│   ├── __init__.py
│   ├── main.py             # FastAPI application
│   ├── models.py           # Pydantic models for API data
│   └── recommender.py      # Recommendation engine logic
├── data/
│   └── generic_dataset.csv # Example product data
├── ml_models/
│   └── content_model.pkl   # Trained model (created by the notebook)
├── notebooks/
│   └── 1_data_exploration_and_model_training.ipynb # Model training notebook
├── .dockerignore
├── .gitignore
├── Dockerfile
├── README.md
└── pyproject.toml         # Project dependencies and configuration
```

## Technical Details

### Recommendation Algorithm

This service uses a content-based filtering approach:

1. Product text data (name, category, description) is processed using TF-IDF vectorization
2. Cosine similarity is calculated between products to find similar items
3. When a recommendation is requested, the system returns the most similar products

### Built With

- [FastAPI](https://fastapi.tiangolo.com/) - Modern, fast web framework
- [Scikit-learn](https://scikit-learn.org/) - Machine learning library
- [Pandas](https://pandas.pydata.org/) - Data manipulation
- [Docker](https://www.docker.com/) - Containerization
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager and resolver

## Contributing

We welcome contributions to improve this project! Here's how you can contribute:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

**Note:** All contributions must adhere to the license terms above, which require offering changes back to the original repository.

## Copyright

© 2025 TellurianPathos. All rights reserved.

**IMPORTANT**: This software is protected by copyright law. Unauthorized reproduction or distribution may result in civil and criminal penalties.
