import os
from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='adp',
    version='1.0',
    author='David Gadling',
    author_email='dave@toasterwaffles.com',
    description='A basic tool to download your pay stubs from adp.com',
    license='MIT',
    url='https://github.com/dgadling/adp-scrape',
    long_description=read('README.md'),
    py_modules=['adp'],
    install_requires=[
        'Click',
        'requests',
    ],
    entry_points='''
        [console_scripts]
        adp=adp:cli
    '''
)
