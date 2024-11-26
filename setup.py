from setuptools import setup, find_packages
import logging
logger = logging.getLogger(__name__)

version = '2.4.0'

try:
    with open('README.md', 'r') as f:
        long_desc = f.read()
except:
    logger.warning('Could not open README.md.  long_description will be set to None.')
    long_desc = None

setup(
    name = 'drawsvg',
    packages = find_packages(),
    version = version,
    description = 'A Python 3 library for programmatically generating SVG (vector) images and animations.  Drawsvg can also render to PNG, MP4, and display your drawings in Jupyter notebook and Jupyter lab.',
    long_description = long_desc,
    long_description_content_type = 'text/markdown',
    author = 'Casey Duckering',
    #author_email = '',
    url = 'https://github.com/cduck/drawsvg',
    download_url = 'https://github.com/cduck/drawsvg/archive/{}.tar.gz'.format(version),
    keywords = ['SVG', 'draw', 'graphics', 'iPython', 'Jupyter', 'widget', 'animation'],
    classifiers = [
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Framework :: IPython',
        'Framework :: Jupyter',
    ],
    install_requires = [
    ],
    extras_require = {
        'raster': [
            'cairoSVG~=2.3',
            'numpy~=2.1',
            'imageio~=2.5',
            'imageio_ffmpeg~=0.4',
        ],
        'color': [
            'pwkit~=1.0',
            'numpy~=2.1',
        ],
        'all': [
            'cairoSVG~=2.3',
            'numpy~=2.1',
            'imageio~=2.5',
            'imageio_ffmpeg~=0.4',
            'pwkit~=1.0',
        ],
    },
)

