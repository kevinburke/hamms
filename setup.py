from setuptools import setup

setup(
    name='hamms',
    packages=['hamms'],
    version='0.6',
    description='Malformed servers to test your HTTP client',
    author='Kevin Burke',
    author_email='kev@inburke.com',
    url='https://github.com/kevinburke/hamms',
    keywords=['testing', 'server', 'http',],
    # XXX, pin these down
    install_requires=['flask', 'httpbin', 'twisted'],
)
