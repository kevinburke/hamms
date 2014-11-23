from setuptools import setup

# XXX: also update version in setup.py
__version__ = '1.2'

setup(
    name='hamms',
    packages=['hamms'],
    version=__version__,
    description='Malformed servers to test your HTTP client',
    author='Kevin Burke',
    author_email='kev@inburke.com',
    url='https://github.com/kevinburke/hamms',
    keywords=['testing', 'server', 'http',],
    # XXX, pin these down
    install_requires=['flask', 'httpbin', 'twisted'],
)
