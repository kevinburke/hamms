from setuptools import setup
import hamms

setup(
    name='hamms',
    packages=['hamms'],
    version=hamms.__version__,
    description='Malformed servers to test your HTTP client',
    author='Kevin Burke',
    author_email='kev@inburke.com',
    url='https://github.com/kevinburke/hamms',
    keywords=['testing', 'server', 'http',],
    # XXX, pin these down
    install_requires=['flask', 'httpbin', 'twisted'],
)
