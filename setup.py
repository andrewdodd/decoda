from setuptools import find_packages, setup

setup(
    name="decoda",
    description="Copyright Andrew Dodd",
    license="Nil",
    version="1.1.0",
    author="Andrew Dodd",
    author_email="andrew.john.dodd@gmail.com",
    maintainer="Andrew Dodd",
    maintainer_email="andrew.john.dodd@gmail.com",
    keywords=["decoda", "j1939"],
    packages=find_packages(
        where="src",
        exclude=["doc", "reference"],
    )
    + ["tests"],
    package_dir={"": "src", "tests": "./tests"},
    zip_safe=False,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "DO NOT UPLOAD to PyPI",
    ],
    install_requires=[
        "attrs",
        # Installing pretty_j1939 instead of its dependencies, even
        # though we don't really use it directly (i.e. is it here just so
        # the copied create_j1939db_json.py file works)
        "pretty_j1939",
    ],
    entry_points={
        "console_scripts": [
            "json_from_digital_annex=decoda.sae_spec_converter.json_from_da:main",
            "enrich_spec=decoda.sae_spec_converter.enrich_spec:main",
            "correct_spec=decoda.sae_spec_converter.correct_spec:main",
            "remove_bad_items=decoda.sae_spec_converter.remove_bad_items:main",
        ]
    },
)
