import pandas as pd
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report


# Load dataset
df = pd.read_csv("data/advanced_train_logs.csv")

# Features and labels
X = df["log_text"].fillna("")
y = df["label"]

# TF-IDF Vectorization
vectorizer = TfidfVectorizer(
    ngram_range=(1, 2),
    max_features=10000
)

X_vectorized = vectorizer.fit_transform(X)

# Split dataset
X_train, X_test, y_train, y_test = train_test_split(
    X_vectorized,
    y,
    test_size=0.2,
    random_state=42
)

# Train model
model = LogisticRegression(max_iter=200)
model.fit(X_train, y_train)

# Predictions
predictions = model.predict(X_test)

# Evaluation
print("\nClassification Report:\n")
print(classification_report(y_test, predictions))

# Save model
joblib.dump(model, "models/model.pkl")
joblib.dump(vectorizer, "models/vectorizer.pkl")

print("\nModel training completed successfully!")
