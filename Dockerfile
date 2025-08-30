# Use a official Python image as base
FROM python:3.9-slim

# Set working directory in the container
WORKDIR /code

# Copy requirements file first for better caching
COPY ./requirements.txt /code/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the application code and ML model
COPY ./app /code/app
COPY ./ml_models /code/ml_models

# Expose the port the app will run on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
