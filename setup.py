"""
Lib package to perform various ops against Ship IT API
"""

from setuptools import setup, find_packages

setup(
    name='shipitapi',
    version='1.0.0',
    description='Lib package to facilitate access to Ship IT API operations',
    url='https://github.com/MihaiTabara/shipitapi',
    author='Mihai Tabara',
    author_email='mtabara@mozilla.com',
    license='MPL',
    classifiers=[],
    keywords='shipit api lib package',
    install_requires=['certifi', 'requests', 'redo'],
    packages=find_packages('src'),
    package_dir={'': 'src'},
    package_data={},
)
