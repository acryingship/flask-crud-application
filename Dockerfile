# Use official Python base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the app directory
COPY basic_crud/ ./basic_crud/

# Set environment variable for Flask
ENV FLASK_APP=basic_crud/app.py

# Expose the default Flask port
EXPOSE 5000

# Run the Flask app
CMD ["flask", "run", "--host=0.0.0.0"]
