# Use the official Python image as a base
FROM python:3.10-slim

# Set environment variables
# Prevents Python from creating .pyc files, reducing unnecessary file writes and keeping the container filesystem cleaner.
# Forces Python to flush output directly to the console or logs for real-time monitoring.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files to the container
COPY . /app/

# Run migrations and the custom import command
RUN python manage.py makemigrations
RUN python manage.py migrate
RUN python manage.py import_restaurants

# Expose port 8000 to the outside world
EXPOSE 8000

# Run the Django development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
