"""
Lib package to perform various ops against Ship IT API
"""

from setuptools import setup, find_packages


def get_requirements():
    with open('requirements.txt') as f:
        return [x.strip() for x in f.read().split('\n') if not x.startswith('#')]


setup(
    name='shipitapi',
    version='3.1.0',
    description='Lib package to facilitate access to Ship IT API operations',
    url='https://github.com/MihaiTabara/shipitapi',
    author='Mihai Tabara',
    author_email='mtabara@mozilla.com',
    install_requires=get_requirements(),
    license='MPL',
    classifiers=[],
    keywords='shipit api lib package',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    package_data={},
)
