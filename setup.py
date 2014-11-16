from distutils.core import setup

setup(
    name='hamms',
    packages=['hamms'],
    version='0.4',
    description='Malformed servers to test your HTTP client',
    author='Kevin Burke',
    author_email='kev@inburke.com',
    url='https://github.com/kevinburke/hamms',
    keywords=['testing', 'server', 'http',],
    # XXX, pin these down
    requires=['flask', 'httpbin', 'twisted'],
)
