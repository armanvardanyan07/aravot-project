# aravot-project

Armenian news title classification project based on titles from Aravot.am.

The project contains a ready dataset for two categories:

- `politics`
- `sport`

It also includes a parser for rebuilding the dataset and a Telegram bot that can classify Armenian news titles or short sentences.

## Project Structure

```text
aravot-project/
  data/
    train.csv
    test.csv
  src/
    parser.py
    bot.py
  .gitignore
  README.md
  requirements.txt
```

## Dataset

The dataset files are stored in `data/`.

Each CSV file has two columns:

```csv
category,text
```

Current files:

| File | Rows | Description |
| --- | ---: | --- |
| `data/train.csv` | 8000 | Training data |
| `data/test.csv` | 2000 | Test data |

Category labels:

| Label | Meaning |
| --- | --- |
| `politics` | Քաղաքականություն |
| `sport` | Սպորտ |

Example rows:

```csv
category,text
sport,Հայաստանի հավաքականը հաղթեց եզրափակիչ խաղում
politics,Կառավարությունը քննարկել է նոր օրենսդրական նախաձեռնությունը
```

## Installation

Create and activate a virtual environment:

```powershell
python -m venv venv
venv\Scripts\activate
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

## Rebuild Dataset

The parser collects titles from the `politics` and `sport` categories and writes two combined files:

- `data/train.csv`
- `data/test.csv`

Run:

```powershell
python src/parser.py --limit 5000 --workers 24 --output-dir data
```

Useful options:

| Option | Default | Description |
| --- | ---: | --- |
| `--limit` | `5000` | Titles per category |
| `--workers` | `16` | Parallel page requests |
| `--test-ratio` | `0.2` | Test split size |
| `--seed` | `42` | Shuffle seed |
| `--output-dir` | `data` | Output directory |

## Train Model

The repository does not include a trained model file.

Example training code:

```python
import joblib
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier

train_df = pd.read_csv("data/train.csv")

model = Pipeline([
    ("tfidf", TfidfVectorizer()),
    ("classifier", DecisionTreeClassifier(random_state=42)),
])

model.fit(train_df["text"], train_df["category"])

joblib.dump(model, "model.pkl")
```

## Evaluate Model

```python
import joblib
import pandas as pd

from sklearn.metrics import accuracy_score, classification_report

test_df = pd.read_csv("data/test.csv")
model = joblib.load("model.pkl")

y_pred = model.predict(test_df["text"])

print("Accuracy:", accuracy_score(test_df["category"], y_pred))
print(classification_report(test_df["category"], y_pred))
```

## Test Prediction

```python
import joblib

model = joblib.load("model.pkl")

texts = [
    "Հայաստանի հավաքականը հաղթեց եզրափակիչ խաղում և նվաճեց ոսկե մեդալը",
    "Կառավարությունը քննարկել է նոր օրենսդրական նախաձեռնությունը",
]

print(model.predict(texts))
```

Expected labels:

```text
['sport' 'politics']
```

## Telegram Bot

The bot loads `model.pkl` and classifies incoming Telegram messages.

Create a Telegram bot with `@BotFather`, get the token, then run:

```powershell
$env:TELEGRAM_BOT_TOKEN='YOUR_TELEGRAM_BOT_TOKEN'
python src/bot.py
```

By default, the bot looks for:

```text
model.pkl
```

in the project root.

You can use another model path:

```powershell
$env:MODEL_PATH='C:\path\to\model.pkl'
$env:TELEGRAM_BOT_TOKEN='YOUR_TELEGRAM_BOT_TOKEN'
python src/bot.py
```

Bot commands:

| Command | Description |
| --- | --- |
| `/start` | Start message |
| `/help` | Short usage help |

Any other text message is classified as one of:

```text
Սպորտ
Քաղաքականություն
```

## Security

Do not commit Telegram tokens or trained model files.

The `.gitignore` excludes:

```text
model.pkl
*.pkl
.env
venv/
.venv/
__pycache__/
.ipynb_checkpoints/
```

If a token was committed or shared by mistake, revoke it in `@BotFather` and create a new one.

## Notes

- The dataset contains only titles.
- Dates, URLs and article bodies are not included.
- The model file is intentionally excluded from the repository.
- The parser depends on the current HTML structure of Aravot.am.
