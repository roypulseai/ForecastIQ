from setuptools import setup, find_packages

setup(
    name="demand_forecaster",
    version="0.1.0",
    description="Demand forecasting package with weighted moving average, trend factors, and event/promotion adjustments",
    author="Saikat_Roy",
    packages=find_packages(),
    install_requires=[
        "pandas",
        "numpy",
        "click",   # for CLI
        "scikit-learn"
    ],
    entry_points={
        "console_scripts": [
            "forecast-cli=demand_forecaster.cli:cli"
        ]
    },
    python_requires=">=3.8",
)
