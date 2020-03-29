from natls import __version__

import setuptools


with open('README.md') as f:
    long_description = f.read()

setuptools.setup(
    name='natls',
    version=__version__,
    author='Agost Biro',
    author_email='agost.biro+nls@gmail.com',
    description='Natural Language Server',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/aughie/natural-language-server',
    packages=setuptools.find_packages(),
    install_requires=[
        'ftfy==5.5.0',
        'numpy==1.15.4',
        'python-jsonrpc-server==0.0.2',
        'spacy==2.0.18',
        'pip @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-2.0.0/en_core_web_sm-2.0.0.tar.gz#en_core_web_sm-2.0.0',
        'torch==1.0.0'
    ],
    entry_points={
        'console_scripts': ['natls = natls.__main__:main']
    },
    classifiers=[
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Operating System :: OS Independent'
    ]
)
