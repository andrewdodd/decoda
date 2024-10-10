import codecs
import os
import re

from setuptools import find_packages, setup

###############################################################################

NAME = "decoda"
PACKAGES = find_packages(where="src")
META_PATH = os.path.join("src", "decoda", "__init__.py")
KEYWORDS = ["j1939"]
PROJECT_URLS = {
    "Documentation": "https://www.decoda.cc/",
    "Source Code": "https://github.com/andrewdodd/decoda",
}
CLASSIFIERS = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Natural Language :: English",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.6",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Topic :: Software Development :: Libraries :: Python Modules",
]
INSTALL_REQUIRES = [
    "attrs",
    # Installing pretty_j1939 instead of its dependencies, even
    # though we don't really use it directly (i.e. is it here just so
    # the copied create_j1939db_json.py file works)
    "pretty_j1939",
    "xlrd2",
    "pandas",
]
# I'm not really sure what this is for
EXTRAS_REQUIRE = {}

###############################################################################

HERE = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    """
    Build an absolute path from *parts* and return the contents of the
    resulting file.  Assume UTF-8 encoding.
    """
    with codecs.open(os.path.join(HERE, *parts), "rb", "utf-8") as f:
        return f.read()


META_FILE = read(META_PATH)


def find_meta(meta):
    """
    Extract __*meta*__ from META_FILE.
    """
    meta_match = re.search(
        r"^__{meta}__ = ['\"]([^'\"]*)['\"]".format(meta=meta), META_FILE, re.M
    )
    if meta_match:
        return meta_match.group(1)
    raise RuntimeError("Unable to find __{meta}__ string.".format(meta=meta))


VERSION = find_meta("version")
URL = find_meta("url")
LONG = read("README.md")


if __name__ == "__main__":
    setup(
        name=NAME,
        description=find_meta("description"),
        license=find_meta("license"),
        url=URL,
        project_urls=PROJECT_URLS,
        version=VERSION,
        author=find_meta("author"),
        author_email=find_meta("email"),
        maintainer=find_meta("author"),
        maintainer_email=find_meta("email"),
        keywords=KEYWORDS,
        long_description=LONG,
        long_description_content_type="text/markdown",
        packages=PACKAGES,
        package_dir={"": "src"},
        python_requires=">=3.6",
        zip_safe=False,
        classifiers=CLASSIFIERS,
        install_requires=INSTALL_REQUIRES,
        extras_require=EXTRAS_REQUIRE,
        include_package_data=True,
        options={"bdist_wheel": {"universal": "1"}},
        entry_points={
            "console_scripts": [
                "json_from_digital_annex=decoda.sae_spec_converter.json_from_da:main",
                "json_from_isobus_xlsx=decoda.sae_spec_converter.json_from_isobus_xlsx:main",
                "enrich_spec=decoda.sae_spec_converter.enrich_spec:main",
                "correct_spec=decoda.sae_spec_converter.correct_spec:main",
                "remove_bad_items=decoda.sae_spec_converter.remove_bad_items:main",
            ]
        },
    )
