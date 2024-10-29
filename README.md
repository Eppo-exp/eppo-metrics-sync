### Eppo Metrics Sync

This Python package allows to post a directory of yaml files to Eppo's API. Documentation is available in Eppo's [documentation page](https://docs.geteppo.com/data-management/certified-metrics/).

#### Deploying the package

Note: this section is intended for Eppo package maintainers.
- Bump version in ```setup.py```
- Install required tools:```python3 -m pip install --upgrade setuptools wheel twine``` 
- Generate distribution packages:```python3 setup.py sdist bdist_wheel```
- Use Twine to upload the package:```python3 -m twine upload dist/*```
You'll be prompted for your PyPI username and password as well as the API key that is available in 1Password.