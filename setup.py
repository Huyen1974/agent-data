from setuptools import setup, find_packages

setup(
    name="adk_agent_data",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        # Add dependencies from requirements.txt here if they are strictly required by the package itself
        # Or rely on requirements.txt for the application environment setup
    ],
    entry_points={
        "console_scripts": [
            # If you have command-line scripts
        ],
    },
)
