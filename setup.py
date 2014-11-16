from distutils.core import setup

with open('requirements.txt') as f:
    reqs = f.read().strip().split('\n')

setup(
    name='hamms',
    packages=['hamms'],
    version='0.3',
    description='Malformed servers to test your HTTP client',
    author='Kevin Burke',
    author_email='kev@inburke.com',
    url='https://github.com/kevinburke/hamms',
    keywords=['testing', 'server', 'http',],
    requires=reqs,
)
