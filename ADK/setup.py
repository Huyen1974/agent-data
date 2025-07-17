from setuptools import find_packages, setup

setup(
    name="ADK",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "faiss-cpu>=1.11.0",
        "numpy>=2.2.5",
        "google-cloud-firestore>=2.11.0,<3.0.0",
        "google-cloud-storage>=2.19.0",
        "openai>=1.76.0",
        "pytest>=8.3.5",
        "pytest-asyncio>=0.26.0",
    ],
)
