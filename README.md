# Store Recommendation Service

A containerized product recommendation API built with FastAPI and Docker.

## Project Description

This service provides product recommendations to users based on content-based filtering. It analyzes product attributes like name, category, and description to suggest similar items.

## Prerequisites

- Docker
- Python 3.9+ (for local development)

## Quick Start

### Using Docker

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/store_rec_service.git
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
   git clone https://github.com/your-username/store_rec_service.git
   cd store_rec_service
   ```

2. Create and activate a virtual environment:
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   uv pip install -r requirements.txt
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
└── requirements.txt
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

## Future Improvements

- Add user interaction data for collaborative filtering
- Implement A/B testing framework
- Add caching for frequently requested recommendations
- Set up monitoring and logging
