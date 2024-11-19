from setuptools import setup, find_packages

setup(
    name='eppo_metrics_sync',
    version='0.1.1',
    packages=find_packages(),
    install_requires=[
        'PyYAML', 'jsonschema', 'requests'
    ],
    include_package_data=True
)
