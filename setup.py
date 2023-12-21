from setuptools import setup, find_packages

setup(
    name='eppo_metrics_sync',
    version='0.0.0',
    packages=find_packages(),
    install_requires=[
        'PyYAML', 'jsonschema', 'requests'
    ],
    include_package_data=True
)