from setuptools import find_packages, setup  # type: ignore

with open("README.md") as f, open("./requirements.txt", "r+") as fq:
    setup(
        name="openai-ratelimiter",
        version="0.8.2",
        packages=find_packages(exclude=["tests"]),
        description="A Python module that provides rate limiting capabilities for the OpenAI API, utilizing Redis as a caching service. It helps to manage API usage to avoid exceeding OpenAI's rate limits.",
        long_description=f.read(),
        long_description_content_type="text/markdown",
        url="https://github.com/blaze-Youssef/openai-ratelimiter",
        author="Youssef Benhammouda",
        author_email="youssef@benhammouda.ma",
        license="MIT",
        classifiers=[
            "Development Status :: 3 - Alpha",
            "License :: OSI Approved :: MIT License",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
            "Programming Language :: Python :: 3.12",
        ],
        install_requires=[x for x in fq.readlines() if x.strip()],
    )
