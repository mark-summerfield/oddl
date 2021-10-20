import pathlib
import re

import setuptools

ROOT = pathlib.Path(__file__).parent

README = (ROOT / 'README.md').read_text()
INIT = (ROOT / 'oddl.py').read_text()
match = re.search(r"__version__\s*=\s*'(?P<version>.*?)'", INIT)
VERSION = match.group('version')

setuptools.setup(
    name='oddl',
    version=VERSION,
    author='Mark Summerfield',
    author_email='mark@qtrac.eu',
    description='A pure Python library for working with OpenDDL files.',
    long_description=README,
    long_description_content_type='text/markdown',
    url='https://github.com/mark-summerfield/oddl',
    license='GPLv3',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Topic :: Artistic Software',
        'Topic :: Multimedia :: Graphics',
        'Topic :: Software Development :: Libraries',
    ],
    packages=['oddl'],
    python_requires='>=3.8',
)
