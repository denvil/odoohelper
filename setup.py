# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='odoohelper',
    version='0.1.0',
    description='ODOO CLI to help common tasks',
    long_description=readme,
    author='Ville Valtokari',
    author_email='ville.valtokari@ecxol.net',
    url='https://github.com/denvil/odoohelper',
    license=license,
    packages=find_packages(exclude=('tests', 'docs')),
    install_requires=[
        'Click',
        'openerp_proxy',
        'termcolor',
        'pyfiglet',
        'colorama'

    ],
    entry_points='''
        [console_scripts]
        odoohelper=odoohelper.odoohelper:main
    '''
)