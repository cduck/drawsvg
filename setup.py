from setuptools import setup, find_packages

version = '1.0.2'

try:
    with open('DESCRIPTION.rst', 'r') as f:
        longDesc = f.read()
except:
    print('Warning: Could not open DESCRIPTION.rst.  long_description will be set to None.')
    longDesc = None

setup(
    name = 'drawSvg',
    packages = find_packages(),
    version = version,
    description = 'This is a Python 3 library for programmatically generating SVG images (vector drawings) and rendering them or displaying them in an iPython notebook.',
    long_description = longDesc,
    author = 'Casey Duckering',
    #author_email = '',
    url = 'https://github.com/cduck/drawSvg',
    download_url = 'https://github.com/cduck/drawSvg/archive/{}.tar.gz'.format(version),
    keywords = ['SVG', 'draw', 'graphics', 'iPython', 'Jupyter'],
    classifiers = [
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Framework :: IPython',
        'Framework :: Jupyter',
    ],
    install_requires = [
        'cairoSVG',
    ],
)

