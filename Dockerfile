FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY data/ ./data/
COPY models/ ./models/

# Set up non-root user for Hugging Face Spaces compatibility
RUN useradd -m -u 1000 user && \
    chown -R user:user /app
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# Train anomaly model and save training stats (if training data exists)
RUN python -m backend.ml.train_anomaly || echo "Anomaly model training skipped"
RUN python -m backend.ml.save_training_stats || echo "Training stats skipped"

# Create tables on startup via entrypoint
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
