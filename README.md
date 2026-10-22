# Thyroid Disease Clinical Decision Support Module

A machine learning web application that classifies thyroid disease into five diagnostic categories, suggests a matching treatment plan, and manages patient records in one place. Built as my final year project for the Bachelor of Science with Honours (Decision Science) at Universiti Utara Malaysia.

> **Disclaimer:** This is an academic prototype. It was tested only on a public dataset and six scenario patients, and it is not approved for real clinical use.

## What it does

- **Diagnoses** one of five categories from hormone test results and medical history: Negative, Hyperthyroid, Primary Hypothyroid, Compensated Hypothyroid, or Other Thyroid Condition
- **Shows a confidence score and a risk level** (low, medium, high, or refer now) with each diagnosis
- **Recommends treatment** (medication, dosage, lifestyle advice and follow-up time) retrieved from a database
- **Stores patient records** in SQLite, using the IC number to link repeat visits and avoid duplicate patients
- **Exports** a PDF medical report for each diagnosis and an Excel file of filtered patient records
- **Dashboards** with diagnosis distribution, monthly trend and age group charts
- **Role-based access** for Doctor, Nurse and System Administrator, with an activity log, user management and database backup for administrators

## Model results

I compared three classifiers on the UCI thyroid0387 dataset (9,172 patient records, 29 features), using default hyperparameters and the same random seed.

| Model | Test accuracy |
|---|---|
| Logistic Regression | 80.52% |
| Random Forest | 98.07% |
| **XGBoost (selected)** | **98.11%** (macro-F1 0.98) |

XGBoost was best overall, with near-perfect scores on four of the five classes. The Negative and Other Thyroid Condition classes scored slightly lower (F1 of 0.96 each). The most important features were FTI, on_thyroxine, T3 and TSH.

## Method

1. Grouped the original diagnostic codes into five categories
2. Dropped the TBG column (96% missing), set impossible age values to missing, and imputed missing values (median for numeric features, mode for sex)
3. Encoded the binary features and the target labels
4. Balanced the classes with SMOTE (k_neighbors = 1, because the smallest classes were tiny)
5. Split the balanced data 80/20 (stratified, random_state = 42) and trained the three models
6. Evaluated them with accuracy, precision, recall and F1, then saved the best model with joblib

## Limitations

- Trained and evaluated on one public dataset, so the model may not generalise to other populations or laboratories
- SMOTE was applied before the train/test split, so the test set is balanced and contains synthetic samples. The reported accuracy is likely higher than on real, imbalanced data. Applying SMOTE to the training data only would be a fairer evaluation.
- The module was tested with six scenario patients, not real clinical cases
- The Other Thyroid Condition class is heterogeneous and the hardest to classify
- No integration with hospital information systems or laboratory interfaces

## Tech stack

Python, XGBoost, scikit-learn, imbalanced-learn, Pandas, Streamlit, SQLite, Plotly, ReportLab, openpyxl, joblib, JupyterLab

## How to run

1. Clone or download this repository.
2. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create the database:
   ```
   python setup_database.py
   ```
4. If the `models/` folder has no trained model file, run the notebook in `notebooks/` first to train and save one.
5. Start the app:
   ```
   streamlit run app/app.py
   ```

The setup script creates demonstration accounts for the Doctor, Nurse and Administrator roles. They are for testing only, so change the passwords before using the app for anything else.

## Project structure

- `app.py` - Streamlit entry point
- `pages_ui.py` - page layouts
- `model.py` - loads the model and makes predictions
- `database.py` - database functions
- `report.py` - PDF report generation
- `setup_database.py` - creates the database tables
- `reset_patients.py` - helper script for resetting demo patient records
- `01_data_exploration.ipynb`, `02_data_preprocessing.ipynb`, `03_model_development.ipynb` - analysis and model training
- `xgb_model.pkl`, `label_encoder.pkl`, `feature_columns.pkl` - trained model files
- `thyroid0387.data`, `processed_balanced.csv` - dataset and processed data

## Database

Five SQLite tables: `patients`, `diagnoses`, `treatments`, `users` and `activity_log`. Passwords are stored as SHA-256 hashes. No database file or patient data is included in this repository.

## Data source

UCI Machine Learning Repository, thyroid disease dataset (thyroid0387), originally compiled by the Garvan Institute of Medical Research: https://archive.ics.uci.edu/dataset/102/thyroid+disease

## Author

Caitlyn Chan Rou Qian
[LinkedIn](https://linkedin.com/in/caitlyn-chan-385584384)
