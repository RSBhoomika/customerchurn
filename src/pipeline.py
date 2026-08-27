from typing import NamedTuple

from kfp import compiler, dsl
from kfp.dsl import Dataset, Input, Model, Output


@dsl.component(
    base_image="python:3.12-slim",
    packages_to_install=["pandas", "scikit-learn", "pyarrow"],
)
def prepare_data(
    data_url: str,
    train_data: Output[Dataset],
    test_data: Output[Dataset],
):
    import pandas as pd
    from sklearn.model_selection import train_test_split

    df = pd.read_csv(data_url)
    df = df.drop(columns=["customerID"])
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce").fillna(0)
    df["Churn"] = (df["Churn"] == "Yes").astype(int)

    train_df, test_df = train_test_split(
        df, test_size=0.2, random_state=42, stratify=df["Churn"]
    )
    train_df.to_parquet(train_data.path, index=False)
    test_df.to_parquet(test_data.path, index=False)


@dsl.component(
    base_image="python:3.12-slim",
    packages_to_install=["pandas", "scikit-learn", "mlflow", "pyarrow", "boto3"],
)
def train_model(
    train_data: Input[Dataset],
    model_type: str,
    experiment_name: str,
    mlflow_tracking_uri: str,
    mlflow_s3_endpoint_url: str,
    aws_access_key_id: str,
    aws_secret_access_key: str,
    model: Output[Model],
) -> NamedTuple("TrainOut", [("run_id", str)]):
    import os
    from collections import namedtuple

    import joblib
    import mlflow
    import mlflow.sklearn
    import pandas as pd
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    os.environ["MLFLOW_TRACKING_URI"] = mlflow_tracking_uri
    os.environ["MLFLOW_S3_ENDPOINT_URL"] = mlflow_s3_endpoint_url
    os.environ["AWS_ACCESS_KEY_ID"] = aws_access_key_id
    os.environ["AWS_SECRET_ACCESS_KEY"] = aws_secret_access_key
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["MLFLOW_S3_IGNORE_TLS"] = "true"
    os.environ["GIT_PYTHON_REFRESH"] = "quiet"

    mlflow.set_tracking_uri(mlflow_tracking_uri)
    mlflow.set_experiment(experiment_name)

    train_df = pd.read_parquet(train_data.path)
    y = train_df["Churn"]
    X = train_df.drop(columns=["Churn"])

    numeric = X.select_dtypes(include=["int64", "float64"]).columns.tolist()
    categorical = X.select_dtypes(include=["object"]).columns.tolist()
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric),
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
        ]
    )

    if model_type == "logreg":
        clf = LogisticRegression(max_iter=1000)
    elif model_type == "logreg_balanced":
        clf = LogisticRegression(max_iter=1000, class_weight="balanced")
    elif model_type == "rf":
        clf = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    else:
        raise ValueError(model_type)

    pipe = Pipeline([("preprocess", preprocessor), ("clf", clf)])
    pipe.fit(X, y)
    joblib.dump(pipe, model.path)

    with mlflow.start_run(run_name=model_type) as run:
        mlflow.log_param("model_type", model_type)
        mlflow.sklearn.log_model(pipe, name="model",serialization_format="cloudpickle",)
        run_id = run.info.run_id

    return namedtuple("TrainOut", ["run_id"])(run_id)


@dsl.component(
    base_image="python:3.12-slim",
    packages_to_install=["pandas", "scikit-learn", "mlflow", "pyarrow"],
)
def evaluate_model(
    test_data: Input[Dataset],
    model: Input[Model],
    run_id: str,
    experiment_name: str,
    mlflow_tracking_uri: str,
):
    import os

    import joblib
    import mlflow
    import pandas as pd
    from sklearn.metrics import (
        accuracy_score,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    os.environ["MLFLOW_TRACKING_URI"] = mlflow_tracking_uri
    os.environ["GIT_PYTHON_REFRESH"] = "quiet"
    mlflow.set_tracking_uri(mlflow_tracking_uri)
    mlflow.set_experiment(experiment_name)

    test_df = pd.read_parquet(test_data.path)
    y = test_df["Churn"]
    X = test_df.drop(columns=["Churn"])
    pipe = joblib.load(model.path)

    y_pred = pipe.predict(X)
    y_prob = pipe.predict_proba(X)[:, 1]

    with mlflow.start_run(run_id=run_id):
        mlflow.log_metrics(
            {
                "accuracy": float(accuracy_score(y, y_pred)),
                "precision": float(precision_score(y, y_pred)),
                "recall": float(recall_score(y, y_pred)),
                "f1": float(f1_score(y, y_pred)),
                "roc_auc": float(roc_auc_score(y, y_prob)),
            }
        )


@dsl.component(
    base_image="python:3.12-slim",
    packages_to_install=["mlflow", "boto3"],
)
def register_model(
    run_id: str,
    registered_model_name: str,
    mlflow_tracking_uri: str,
    mlflow_s3_endpoint_url: str,
    aws_access_key_id: str,
    aws_secret_access_key: str,
) -> NamedTuple("RegOut", [("version", str)]):
    import os
    from collections import namedtuple

    import mlflow

    os.environ["MLFLOW_TRACKING_URI"] = mlflow_tracking_uri
    os.environ["MLFLOW_S3_ENDPOINT_URL"] = mlflow_s3_endpoint_url
    os.environ["AWS_ACCESS_KEY_ID"] = aws_access_key_id
    os.environ["AWS_SECRET_ACCESS_KEY"] = aws_secret_access_key
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["MLFLOW_S3_IGNORE_TLS"] = "true"
    os.environ["GIT_PYTHON_REFRESH"] = "quiet"

    mlflow.set_tracking_uri(mlflow_tracking_uri)
    mv = mlflow.register_model(f"runs:/{run_id}/model", registered_model_name)
    return namedtuple("RegOut", ["version"])(str(mv.version))


@dsl.component(
    base_image="python:3.12-slim",
    packages_to_install=["mlflow", "pandas", "scikit-learn", "boto3"],
)
def verify_model(
    registered_model_name: str,
    version: str,
    mlflow_tracking_uri: str,
    mlflow_s3_endpoint_url: str,
    aws_access_key_id: str,
    aws_secret_access_key: str,
):
    import os

    import mlflow

    os.environ["MLFLOW_TRACKING_URI"] = mlflow_tracking_uri
    os.environ["MLFLOW_S3_ENDPOINT_URL"] = mlflow_s3_endpoint_url
    os.environ["AWS_ACCESS_KEY_ID"] = aws_access_key_id
    os.environ["AWS_SECRET_ACCESS_KEY"] = aws_secret_access_key
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["MLFLOW_S3_IGNORE_TLS"] = "true"
    os.environ["GIT_PYTHON_REFRESH"] = "quiet"

    mlflow.set_tracking_uri(mlflow_tracking_uri)
    uri = f"models:/{registered_model_name}/{version}"
    loaded = mlflow.pyfunc.load_model(uri)
    print("Loaded", uri, type(loaded))


@dsl.pipeline(name="customer-churn-training")
def customer_churn_pipeline(
    mlflow_tracking_uri: str = "http://<MLFLOW_TRACKING_URI>",
    mlflow_s3_endpoint_url: str = "http://<MINIO_ENDPOINT>",
    aws_access_key_id: str = "****",
    aws_secret_access_key: str = "****",
    model_type: str = "logreg_balanced",
    experiment_name: str = "customer-churn",
    registered_model_name: str = "customer-churn",
    data_url: str = (
        "https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/"
        "master/data/Telco-Customer-Churn.csv"
    ),
):
    prepare = prepare_data(data_url=data_url)

    trained = train_model(
        train_data=prepare.outputs["train_data"],
        model_type=model_type,
        experiment_name=experiment_name,
        mlflow_tracking_uri=mlflow_tracking_uri,
        mlflow_s3_endpoint_url=mlflow_s3_endpoint_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )

    evaluated = evaluate_model(
        test_data=prepare.outputs["test_data"],
        model=trained.outputs["model"],
        run_id=trained.outputs["run_id"],
        experiment_name=experiment_name,
        mlflow_tracking_uri=mlflow_tracking_uri,
    )
    evaluated.after(trained)

    registered = register_model(
        run_id=trained.outputs["run_id"],
        registered_model_name=registered_model_name,
        mlflow_tracking_uri=mlflow_tracking_uri,
        mlflow_s3_endpoint_url=mlflow_s3_endpoint_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )
    registered.after(evaluated)

    verify_model(
        registered_model_name=registered_model_name,
        version=registered.outputs["version"],
        mlflow_tracking_uri=mlflow_tracking_uri,
        mlflow_s3_endpoint_url=mlflow_s3_endpoint_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )


if __name__ == "__main__":
    compiler.Compiler().compile(
        pipeline_func=customer_churn_pipeline,
        package_path="customer_churn_pipeline.yaml",
    )
