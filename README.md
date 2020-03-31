# COVID Modelling

Repository for data and models built

Given the size of this team we should work in branches and merge regularly and separate folders for projects.

**Important Git LFS**
To be able to store data in the repo, and to avoid the problems related to it with git, the repo is configured to use [Git LFS](https://git-lfs.github.com/). Please install it. Every file with a ``.csv`` extension is then automatically dealt with Git LFS. In cosma, you need to

```
load moudle git-lfs
git lfs-install --local
```
the last command should be run in the repo after you clone it. You can then pull normally, if the data is not pulled try ``git lfs pull``.

 

# Ongoing documentation sources

[Main documentation](https://josephpb.github.io/covidmodelling)

[Working Google Doc with meeting notes](https://docs.google.com/document/d/1EwwHZ0s3uVWmkEdhiw94cqrhfoLsTu_Pay2H11LjVOw/edit)<br>

[UML class diagram](https://drive.google.com/file/d/1YMUAePtUvx1xLVObjnz1n5IkDfJOkmD8/view)

# Setup

To install the package, install requisites and

``pip install -e .``

